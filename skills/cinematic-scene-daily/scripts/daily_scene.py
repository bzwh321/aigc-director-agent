"""Local daily episode preparation and deterministic assembly; no network calls."""
from __future__ import annotations

import argparse
from datetime import date
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess

DEFAULT_ROOT = Path("<PROJECT_ROOT>/b站巨构自动更新")
DIRECTOR_ROOT = Path(__file__).resolve().parents[3]


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def write(path, value):
    with Path(path).open("x", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def file_hash(path):
    with Path(path).open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def number(value, low, high, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not low <= value <= high:
        raise ValueError(f"Invalid {name}: expected {low}..{high}")
    return value


def output_spec(value):
    width, height, fps = (value[k] for k in ("width", "height", "fps"))
    for key, val in (("width", width), ("height", height)):
        number(val, 64, 4096, key)
        if type(val) is not int or val % 2:
            raise ValueError(f"{key} must be an even integer")
    number(fps, 1, 60, "fps")
    if type(fps) is not int:
        raise ValueError("fps must be an integer")
    return width, height, fps


def shot_list(shots):
    if not isinstance(shots, list) or len(shots) not in (4, 5):
        raise ValueError("An episode needs 4 or 5 shots")
    identifiers = [s["shot_id"] for s in shots]
    if len(set(identifiers)) != len(identifiers) or any(not re.fullmatch(r"[A-Za-z0-9_-]+", s) for s in identifiers):
        raise ValueError("shot_id must be unique and path-safe")
    for shot in shots:
        number(shot["duration_seconds"], 0.1, 60, "duration_seconds")


def prepare(brief_path, root, day):
    date.fromisoformat(day)
    brief = read(brief_path)
    series, revision = brief["series_id"], brief["revision"]
    if not re.fullmatch(r"[a-z][a-z0-9-]{0,63}", series):
        raise ValueError("series_id must be a lowercase path-safe name")
    if type(revision) is not int or not 1 <= revision <= 999:
        raise ValueError("revision must be 1..999")
    if brief["organization"] not in ("shared_world", "anthology"):
        raise ValueError("Unknown organization")
    output_spec(brief["output"])
    shot_list(brief["shots"])
    for key in ("title", "world_premise", "style_id"):
        if not isinstance(brief.get(key), str) or not brief[key].strip():
            raise ValueError(f"Missing {key}")
    for shot in brief["shots"]:
        for key in ("story", "composition", "lighting", "image_prompt", "motion"):
            if not shot.get(key):
                raise ValueError(f"Missing {shot['shot_id']}.{key}")
    series_root = Path(root).resolve()
    episode = series_root / f"{day}_{series}"
    folder = episode / "制作记录" / f"r{revision:02d}"
    fingerprint = digest(brief)
    if folder.exists():
        state = read(folder / "run.json")
        if state["brief_fingerprint"] != fingerprint or digest(read(folder / "brief.json")) != fingerprint:
            raise ValueError("Same day/revision has different input; review changes and increment revision")
        for name in ("director-state.json", "edit.json"):
            if not (folder / name).is_file():
                raise ValueError("Incomplete preparation; inspect existing files before recovery")
        return {"action": "resume", "folder": str(folder), "status": state["status"]}
    for prior in series_root.glob("*/制作记录/r*/run.json"):
        prior_state = read(prior)
        if prior_state.get("series_id") == series and prior_state.get("date", day) < day and prior_state.get("status") not in ("completed", "cancelled"):
            raise ValueError(f"Previous episode unresolved: {prior}")
    folder.mkdir(parents=True, exist_ok=False)
    media_dirs = {name: str(episode / name) for name in ("图片", "音频", "镜头视频", "成片")}
    for directory in media_dirs.values():
        Path(directory).mkdir(exist_ok=True)
    write(folder / "brief.json", brief)
    write(folder / "director-state.json", {
        "schema_version": "director-production/v3",
        "brief": {"request": brief["title"], "goal": brief["world_premise"],
                  "style_id": brief["style_id"], "audio_mode": "provided",
                  "visual_source": "create", "subject_motion": brief.get("subject_motion", "unknown"),
                  "camera_motion": "unknown", "render_mode": "generate",
                  "needs_scene_design": True, "needs_vfx": False, "needs_color": False,
                  "asset_ids": []},
        "shots": [{"shot_id": s["shot_id"], "summary": s["story"],
                   "story_background": s["story"], "emotion": s.get("emotion", ""),
                   "shot_contract": {"composition": s["composition"], "lighting": s["lighting"],
                                     "duration_seconds": s["duration_seconds"]},
                   "composition": s["composition"], "lighting": s["lighting"],
                   "duration_seconds": s["duration_seconds"], "motion": s["motion"]}
                  for s in brief["shots"]],
        "facts": [{"id": s["shot_id"] + "-proposed-design", "shot_ids": [s["shot_id"]],
                   "roles": ["shot-design", "scene-design", "action-design", "prompt-design", "node-design"],
                   "topics": ["story", "visual", "motion", "camera", "timing"],
                   "summary": json.dumps({k: s[k] for k in ("composition", "lighting", "motion", "image_prompt")}, ensure_ascii=False),
                   "source": str(folder / "brief.json"), "status": "proposed_not_accepted"}
                  for s in brief["shots"]],
        "artifacts": {}, "reviews": {}, "completed_calls": {}, "issues": []})
    write(folder / "edit.json", {
        "output": brief["output"],
        "music": {"path": brief["music"].get("path"), "start_seconds": brief["music"].get("start_seconds", 0),
                  "gain_db": 0, "fade_seconds": 0.25},
        "shots": [{"shot_id": s["shot_id"], "kind": "image", "path": None,
                   "duration_seconds": s["duration_seconds"], "start_seconds": 0,
                   "fit": "pad", "zoom": 1.03} for s in brief["shots"]]})
    write(folder / "run.json", {"schema": "cinematic-scene-daily/v1", "series_id": series,
        "date": day, "timezone": "Asia/Shanghai", "revision": revision,
        "episode_folder": str(episode), "media_directories": media_dirs,
        "brief_fingerprint": fingerprint, "status": "planned", "requests": {},
        "authorization": "none_recorded", "schedule": "not_enabled"})
    return {"action": "created", "folder": str(folder), "status": "planned"}


def command(args, log=None):
    result = subprocess.run([str(a) for a in args], capture_output=True, encoding="utf-8", errors="replace")
    if log:
        Path(log).write_text(result.stdout + result.stderr, encoding="utf-8")
    if result.returncode:
        raise RuntimeError(f"Local command failed; no retry. {str(log) if log else result.stderr[-1500:]}")
    return result.stdout + result.stderr


def director_request(run_dir, phase):
    """Build a content-addressed handoff; the host must actually invoke the agent."""
    if phase not in ("design", "contract", "final_review"):
        raise ValueError("Unknown director phase")
    folder = Path(run_dir).resolve()
    run = read(folder / "run.json")
    state = read(folder / "director-state.json")
    brief = read(folder / "brief.json")
    music_paths = [brief.get("music", {}).get("path")]
    inputs = [{"path": str(folder / name), "sha256": file_hash(folder / name)}
              for name in ("brief.json", "director-state.json")]
    for item in state.get("artifacts", {}).get("static_images", {}).get("files", []):
        path = real_file(item["path"] if isinstance(item, dict) else item)
        actual_hash = file_hash(path)
        if isinstance(item, dict) and item.get("sha256") and item["sha256"] != actual_hash:
            raise ValueError("Static input changed; recheck its review before director handoff")
        inputs.append({"path": str(path), "sha256": actual_hash,
                       "shot_ids": item.get("shot_ids", []) if isinstance(item, dict) else []})
    for item in state.get("artifacts", {}).get("contract", {}).get("files", []):
        path = real_file(item["path"] if isinstance(item, dict) else item)
        inputs.append({"path": str(path), "sha256": file_hash(path), "role": "previous_contract"})
        if path.suffix.lower() == ".json":
            music_paths.append(read(path).get("final", {}).get("music"))
    for value in dict.fromkeys(p for p in music_paths if isinstance(p, str) and p):
        path = Path(value)
        if path.is_absolute() and path.is_file():
            inputs.append({"path": str(path.resolve()), "sha256": file_hash(path), "role": "music_input"})
        else:
            inputs.append({"path": value, "available": False, "role": "music_input"})
    if phase == "final_review":
        media = []
        for kind in ("video", "vfx_video", "final"):
            for item in state.get("artifacts", {}).get(kind, {}).get("files", []):
                path = real_file(item["path"] if isinstance(item, dict) else item)
                media.append({"path": str(path), "sha256": file_hash(path), "role": kind})
        if not media:
            raise ValueError("Final review requires actual video/result artifacts")
        inputs.extend(media)
    for name in ("AGENTS.md", "SKILL.md", "workflow_manifest.json",
                 "workflows/director-control-v3.md", "方案库/SKILL.md",
                 "references/subject-intent-motion-review.md",
                 "agents/action-design/skills/action-design/SKILL.md"):
        path = DIRECTOR_ROOT / name
        inputs.append({"path": str(path), "sha256": file_hash(path), "role": "director_method"})
    identity = {"series_id": run["series_id"], "date": run["date"],
                "revision": run["revision"], "phase": phase, "inputs": inputs}
    fingerprint = digest(identity)
    packet = {"schema": "cinematic-daily-director-request/v1", **identity,
        "call_id": f"{run['series_id']}/{run['date']}/r{run['revision']:02d}/{phase}/{fingerprint[:16]}",
        "input_fingerprint": fingerprint,
        "origin": "cinematic-scene-daily", "director_invocation_active": True,
        "entrypoint": str(DIRECTOR_ROOT / "AGENTS.md"),
        "skill": str(DIRECTOR_ROOT / "SKILL.md"),
        "state_file": str(folder / "director-state.json"),
        "run_file": str(folder / "run.json"),
        "episode_folder": run.get("episode_folder", str(folder.parents[1])),
        "task": {"design": "由导演理解本集故事，按需组织场景等能力形成静态设计。",
                 "contract": "由导演核对已认可图片、整体运动因果与生命节律，形成可执行制作合同和人可阅读的合同。",
                 "final_review": "由导演对照当前合同检查实际视频与声音，返回验收证据和结果状态。"}[phase],
        "review_evidence": state.get("reviews", {}),
        "creative_delegation": state.get("contract_review_delegation", {}),
        "execution_authorized": False, "dispatch_status": "prepared_not_dispatched",
        "host_action": "Use the host agent invocation mechanism with this packet; record actual invocation ID and returned files. Reading this packet or running workflow.py is not an agent invocation.",
        "return_contract": ["director expression intent", "subject_audit: actual drawing review, every subject's movement or stillness decision and reason, including distant/occluded subjects; temporal form, start/end states, phases, repetition and post-motion hold",
                            "per-shot causal motion and hold regions",
                            "solution decisions", "timing and music", "validation limitations",
                            "versioned output paths", "budget authorization remains separate"],
        "recursion_guard": "Already inside a director invocation from cinematic-scene-daily: do not call the automation skill to spawn another director."}
    path = folder / f"director-request-{phase}-{fingerprint[:16]}.json"
    if path.exists():
        if read(path) != packet:
            raise ValueError("Existing director request differs; inspect before reusing")
        action = "reuse"
    else:
        write(path, packet)
        action = "prepared"
    return {"action": action, "path": str(path), "call_id": packet["call_id"],
            "input_fingerprint": fingerprint, "dispatch_status": "prepared_not_dispatched"}


def probe(ffmpeg, path):
    result = subprocess.run([str(ffmpeg), "-hide_banner", "-i", str(path)], capture_output=True,
                            encoding="utf-8", errors="replace")
    info = result.stderr
    match = re.search(r"Duration: (\d+):(\d+):(\d+(?:\.\d+)?)", info)
    duration = sum(float(v) * weight for v, weight in zip(match.groups(), (3600, 60, 1))) if match else None
    return {"duration": duration, "audio": "Audio:" in info, "video": "Video:" in info}


def real_file(value):
    if not isinstance(value, str) or not Path(value).is_absolute() or not Path(value).is_file():
        raise ValueError("Media must be an existing absolute file path")
    return Path(value).resolve()


def assemble(edit_path, output_root, ffmpeg):
    edit = read(edit_path)
    ffmpeg = real_file(str(ffmpeg))
    width, height, fps = output_spec(edit["output"])
    shot_list(edit["shots"])
    music = edit["music"]
    audio_path = real_file(music["path"])
    start_audio = number(music.get("start_seconds", 0), 0, 86400, "music start")
    gain = number(music.get("gain_db", 0), -60, 12, "gain_db")
    fade = number(music.get("fade_seconds", 0.25), 0, 10, "fade_seconds")
    prepared, hashes = [], {str(audio_path): file_hash(audio_path)}
    for shot in edit["shots"]:
        path = real_file(shot["path"])
        hashes[str(path)] = file_hash(path)
        if shot["kind"] not in ("image", "video") or shot["fit"] not in ("pad", "crop"):
            raise ValueError("kind must be image/video; fit must be pad/crop")
        zoom = number(shot.get("zoom", 1), 1, 1.08, "zoom")
        start = number(shot.get("start_seconds", 0), 0, 86400, "shot start")
        frames = round(shot["duration_seconds"] * fps)
        if frames < 1:
            raise ValueError("Shot shorter than one output frame")
        duration = frames / fps
        metadata = probe(ffmpeg, path)
        if not metadata["video"]:
            raise ValueError(f"Not a visual input: {path}")
        if shot["kind"] == "video":
            if metadata["duration"] is None or metadata["duration"] + 0.015 < start + duration:
                raise ValueError(f"Video too short: {shot['shot_id']}")
        elif start != 0:
            raise ValueError("Image start_seconds must be zero")
        prepared.append({**shot, "path": str(path), "frames": frames, "actual_seconds": duration,
                         "zoom": zoom, "start_seconds": start})
    total = sum(s["actual_seconds"] for s in prepared)
    metadata = probe(ffmpeg, audio_path)
    if not metadata["audio"] or metadata["duration"] is None or metadata["duration"] + 0.015 < start_audio + total:
        raise ValueError("Music missing or too short; do not auto-loop or add silence")
    version = command([ffmpeg, "-version"]).splitlines()[0]
    fingerprint = digest({"edit": edit, "media_sha256": hashes, "ffmpeg": version,
                          "assembler_sha256": file_hash(__file__)})
    folder = Path(output_root).resolve() / fingerprint[:20]
    final = folder / "film.mp4"
    if folder.exists():
        receipt = folder / "result.json"
        if receipt.is_file() and final.is_file():
            info = read(receipt)
            if info["fingerprint"] == fingerprint and info["output_sha256"] == file_hash(final):
                return {"action": "reuse", "path": str(final), "status": "awaiting_final_review"}
        raise ValueError("Unfinished or changed render exists; inspect it, do not automatically retry")
    folder.mkdir(parents=True, exist_ok=False)
    write(folder / "request.json", {"fingerprint": fingerprint, "edit": edit,
                                   "media_sha256": hashes, "ffmpeg": version})
    common = [ffmpeg, "-hide_banner", "-nostdin", "-n"]
    try:
        for index, shot in enumerate(prepared):
            if shot["fit"] == "pad":
                fit = f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2"
            else:
                fit = f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height}"
            filters = fit + ",setsar=1"
            if shot["kind"] == "image":
                filters += (f",zoompan=z='1+{shot['zoom']-1}*on/{max(1,shot['frames']-1)}'"
                            f":x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2':d={shot['frames']}"
                            f":s={width}x{height}:fps={fps}")
                source = ["-i", shot["path"]]
            else:
                filters += f",fps={fps},setpts=PTS-STARTPTS"
                source = ["-ss", shot["start_seconds"], "-i", shot["path"]]
            command(common + source + ["-map", "0:v:0", "-an", "-vf", filters,
                "-frames:v", shot["frames"], "-c:v", "libx264", "-preset", "fast", "-crf", "18",
                "-pix_fmt", "yuv420p", folder / f"clip-{index:02d}.mp4"], folder / f"clip-{index:02d}.log")
        (folder / "concat.txt").write_text("".join(f"file 'clip-{i:02d}.mp4'\n" for i in range(len(prepared))), encoding="utf-8")
        fade = min(fade, total / 2)
        audio_filter = f"volume={gain}dB,afade=t=in:st=0:d={fade},afade=t=out:st={total-fade}:d={fade}"
        command(common + ["-f", "concat", "-safe", "1", "-i", folder / "concat.txt",
            "-ss", start_audio, "-i", audio_path, "-map", "0:v:0", "-map", "1:a:0",
            "-c:v", "copy", "-af", audio_filter, "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
            "-t", total, "-movflags", "+faststart", final], folder / "assembly.log")
        command([ffmpeg, "-hide_banner", "-v", "error", "-xerror", "-i", final,
                 "-map", "0:v:0", "-map", "0:a:0", "-f", "null", "-"], folder / "decode.log")
        result_meta = probe(ffmpeg, final)
        if not result_meta["audio"] or not result_meta["video"] or abs(result_meta["duration"] - total) > 0.15:
            raise ValueError("Final media duration/streams mismatch")
        write(folder / "result.json", {"fingerprint": fingerprint, "path": str(final),
            "output_sha256": file_hash(final), "duration_seconds": total, "output": edit["output"],
            "status": "awaiting_final_review", "full_decode": "passed", "human_review": "pending"})
        return {"action": "rendered", "path": str(final), "status": "awaiting_final_review"}
    except Exception as exc:
        write(folder / "failure.json", {"status": "blocked", "error": str(exc), "automatic_retry": False})
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    init = commands.add_parser("prepare")
    init.add_argument("--brief", required=True)
    init.add_argument("--root", default=str(DEFAULT_ROOT))
    init.add_argument("--date", required=True, help="Local Asia/Shanghai date, YYYY-MM-DD")
    render = commands.add_parser("assemble")
    render.add_argument("--edit", required=True)
    render.add_argument("--output-root", required=True)
    render.add_argument("--ffmpeg", required=True)
    handoff = commands.add_parser("director-request")
    handoff.add_argument("--run-dir", required=True)
    handoff.add_argument("--phase", choices=("design", "contract", "final_review"), required=True)
    args = parser.parse_args()
    try:
        if args.command == "prepare":
            result = prepare(args.brief, args.root, args.date)
        elif args.command == "director-request":
            result = director_request(args.run_dir, args.phase)
        else:
            result = assemble(args.edit, args.output_root, args.ffmpeg)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, KeyError, TypeError, OSError, RuntimeError) as exc:
        print(json.dumps({"status": "blocked", "error": str(exc), "automatic_retry": False}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
