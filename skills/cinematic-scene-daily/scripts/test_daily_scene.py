"""Offline behavioral checks. Pass --ffmpeg to exercise real media assembly."""
import argparse
import array
import copy
import importlib.util
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import wave

sys.path.insert(0, str(Path(__file__).resolve().parent))
import daily_scene as daily

FFMPEG = None
EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "first-episode.json"


class DailySceneTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="director-daily-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.brief = daily.read(EXAMPLE)
        self.input = self.root / "input.json"
        self.save(self.input, self.brief)

    def save(self, path, value):
        path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")

    def prepare(self, day="2026-10-12"):
        return daily.prepare(self.input, self.root / "episodes", day)

    def test_resume_preserves_progress(self):
        first = self.prepare()
        run_path = Path(first["folder"]) / "run.json"
        state = daily.read(run_path)
        state["status"] = "awaiting_static_review"
        state["requests"]["S01"] = {"task_id": "offline-example", "status": "unknown"}
        self.save(run_path, state)
        second = self.prepare()
        self.assertEqual(second["action"], "resume")
        self.assertEqual(daily.read(run_path), state)
        self.assertEqual(daily.read(Path(first["folder"]) / "director-state.json")["reviews"], {})

    def test_conflict_does_not_overwrite(self):
        first = self.prepare()
        old = (Path(first["folder"]) / "brief.json").read_bytes()
        self.brief["title"] = "changed"
        self.save(self.input, self.brief)
        with self.assertRaises(ValueError):
            self.prepare()
        self.assertEqual((Path(first["folder"]) / "brief.json").read_bytes(), old)

    def test_prior_day_waits_for_review(self):
        first = self.prepare()
        with self.assertRaises(ValueError):
            self.prepare("2026-10-13")
        run_path = Path(first["folder"]) / "run.json"
        state = daily.read(run_path)
        state["status"] = "completed"  # Synthetic test state, not a user approval.
        self.save(run_path, state)
        self.assertEqual(self.prepare("2026-10-13")["action"], "created")

    def test_revision_and_path_safety(self):
        first = self.prepare()
        self.brief["revision"] = 2
        self.save(self.input, self.brief)
        second = self.prepare()
        self.assertNotEqual(first["folder"], second["folder"])
        self.brief["series_id"] = "../escape"
        self.save(self.input, self.brief)
        with self.assertRaises(ValueError):
            self.prepare()

    def test_incomplete_directory_is_not_recreated(self):
        folder = self.root / "episodes" / ("2026-10-12_" + self.brief["series_id"]) / "制作记录" / "r01"
        folder.mkdir(parents=True)
        marker = folder / "unfinished.txt"
        marker.write_text("preserve", encoding="utf-8")
        with self.assertRaises(FileNotFoundError):
            self.prepare()
        self.assertTrue(marker.exists())

    def test_v3_handoff_carries_only_current_shot_design(self):
        result = self.prepare()
        state = daily.read(Path(result["folder"]) / "director-state.json")
        director_root = Path(__file__).resolve().parents[3]
        spec = importlib.util.spec_from_file_location("daily_test_workflow", director_root / "workflow.py")
        workflow = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = workflow
        spec.loader.exec_module(workflow)
        planned = workflow.run(state)
        self.assertEqual(planned["status"], "DESIGN_TASKS_READY")
        self.assertFalse(planned["execution_authorized"])
        self.assertEqual(len(planned["ready"]), 5)
        for packet in planned["ready"]:
            expected = next(s for s in self.brief["shots"] if s["shot_id"] == packet["shot_id"])
            self.assertTrue(any(expected["composition"] in item["summary"] for item in packet["context"]))
            self.assertTrue(all(item["id"].startswith(packet["shot_id"]) for item in packet["context"]))
            self.assertEqual(packet["visual_style"]["id"], "photoreal-cinema")

    def test_director_request_reuses_without_claiming_dispatch(self):
        folder = Path(self.prepare()["folder"])
        first = daily.director_request(folder, "contract")
        second = daily.director_request(folder, "contract")
        self.assertEqual(first["action"], "prepared")
        self.assertEqual(second["action"], "reuse")
        self.assertEqual(first["call_id"], second["call_id"])
        packet = daily.read(first["path"])
        self.assertEqual(packet["dispatch_status"], "prepared_not_dispatched")
        self.assertFalse(packet["execution_authorized"])
        self.assertEqual(packet["origin"], "cinematic-scene-daily")
        self.assertTrue(packet["director_invocation_active"])
        self.assertNotIn("director_calls", daily.read(folder / "run.json"))

    def test_director_request_changes_when_input_changes(self):
        folder = Path(self.prepare()["folder"])
        first = daily.director_request(folder, "contract")
        state = daily.read(folder / "director-state.json")
        state["brief"]["goal"] = "A newly clarified scene intent"
        self.save(folder / "director-state.json", state)
        second = daily.director_request(folder, "contract")
        self.assertNotEqual(first["input_fingerprint"], second["input_fingerprint"])
        self.assertTrue(Path(first["path"]).is_file())

    def test_director_request_rejects_changed_static_asset(self):
        folder = Path(self.prepare()["folder"])
        media = self.root / "accepted-image.bin"
        media.write_bytes(b"original")
        state = daily.read(folder / "director-state.json")
        state["artifacts"]["static_images"] = {"files": [
            {"path": str(media), "shot_ids": ["S01"], "sha256": daily.file_hash(media)}]}
        self.save(folder / "director-state.json", state)
        daily.director_request(folder, "contract")
        media.write_bytes(b"different")
        with self.assertRaisesRegex(ValueError, "Static input changed"):
            daily.director_request(folder, "contract")

    def test_final_review_requires_result_and_tracks_its_bytes(self):
        folder = Path(self.prepare()["folder"])
        with self.assertRaisesRegex(ValueError, "actual video"):
            daily.director_request(folder, "final_review")
        video = self.root / "result.mp4"
        video.write_bytes(b"synthetic artifact identity only, not a decode test")
        state = daily.read(folder / "director-state.json")
        state["artifacts"]["final"] = {"files": [str(video)]}
        self.save(folder / "director-state.json", state)
        first = daily.director_request(folder, "final_review")
        video.write_bytes(b"changed result")
        second = daily.director_request(folder, "final_review")
        self.assertNotEqual(first["input_fingerprint"], second["input_fingerprint"])

    def media(self):
        music = self.root / "tone.wav"
        samples = array.array("h", (round(6000 * math.sin(i * 2 * math.pi * 440 / 48000)) for i in range(96000)))
        with wave.open(str(music), "wb") as handle:
            handle.setparams((1, 2, 48000, 0, "NONE", "not compressed"))
            handle.writeframes(samples.tobytes())
        shots = []
        for i, color in enumerate(((160, 40, 20), (20, 120, 50), (30, 50, 180), (150, 130, 30))):
            image = self.root / f"image{i}.ppm"
            image.write_bytes(b"P6\n320 180\n255\n" + bytes(color) * (320 * 180))
            shots.append({"shot_id": f"S{i}", "path": str(image), "kind": "image", "fit": "pad",
                          "zoom": 1.03, "duration_seconds": 0.4})
        edit = {"output": {"width": 320, "height": 180, "fps": 10},
                "music": {"path": str(music), "fade_seconds": 0.05}, "shots": shots}
        path = self.root / "edit.json"
        self.save(path, edit)
        return path, edit

    def test_audio_shortage_stops_before_render(self):
        if not FFMPEG:
            self.skipTest("Pass --ffmpeg for local integration checks")
        path, edit = self.media()
        edit["music"]["start_seconds"] = 1.5
        self.save(path, edit)
        with self.assertRaisesRegex(ValueError, "Music"):
            daily.assemble(path, self.root / "renders", FFMPEG)
        self.assertFalse((self.root / "renders").exists())

    def test_image_video_assembly_reuse_and_corruption(self):
        if not FFMPEG:
            self.skipTest("Pass --ffmpeg for local integration checks")
        path, edit = self.media()
        result = daily.assemble(path, self.root / "renders", FFMPEG)
        self.assertEqual(result["status"], "awaiting_final_review")
        final = Path(result["path"])
        checksums = daily.command([FFMPEG, "-v", "error", "-i", final, "-map", "0:v:0", "-f", "framemd5", "-"])
        self.assertEqual(len([line for line in checksums.splitlines() if line and not line.startswith("#")]), 16)
        self.assertIn("320x180", checksums)
        audio = subprocess.run([str(FFMPEG), "-v", "error", "-i", str(final), "-map", "0:a:0",
            "-f", "s16le", "-ac", "1", "-ar", "48000", "-"], capture_output=True, check=True).stdout
        self.assertGreater(len(audio), 48000 * 2 * 1.5)
        values = array.array("h", audio)
        self.assertGreater(max(abs(v) for v in values[24000:48000]), 1000)
        self.assertEqual(daily.assemble(path, self.root / "renders", FFMPEG)["action"], "reuse")
        video_edit = copy.deepcopy(edit)
        for shot in video_edit["shots"]:
            shot.update(kind="video", path=str(final), start_seconds=0, zoom=1)
        video_path = self.root / "video-edit.json"
        self.save(video_path, video_edit)
        self.assertEqual(daily.assemble(video_path, self.root / "video-renders", FFMPEG)["action"], "rendered")
        final.write_bytes(final.read_bytes() + b"changed")
        with self.assertRaisesRegex(ValueError, "Unfinished or changed"):
            daily.assemble(path, self.root / "renders", FFMPEG)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--ffmpeg")
    args, rest = parser.parse_known_args()
    FFMPEG = args.ffmpeg
    unittest.main(argv=[__file__, *rest])
