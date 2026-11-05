import importlib.util
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_workflow():
    spec = importlib.util.spec_from_file_location("aigc_director_workflow", ROOT / "workflow.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class AIGCDirectorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workflow = load_workflow()

    def test_empty_stops_at_intent(self):
        result = self.workflow.run({})
        self.assertEqual(result["status"], "NEEDS_CLARIFICATION")
        self.assertLessEqual(len(result['questions']),3)

    def test_sample_does_not_jump_to_workflow(self):
        payload = json.loads((ROOT / "prompts/tests/sample_input.json").read_text(encoding="utf-8"))
        result = self.workflow.run(payload)
        self.assertEqual(result["status"], "GRILL_ME")
        self.assertNotIn("paid_workflow", result["allowed_outputs"])

    def test_complete_payload_is_design_ready(self):
        payload = {
            "intent": {"audience_feeling": "紧张后温暖", "narrative_function": "接纳", "start_state": "相隔", "end_state": "围拢"},
            "timing": {"duration_seconds": 12, "structure": "三段", "cut_policy": "动作匹配"},
            "cast": {"characters": ["H", "G"], "count_lock": 2, "identity_policy": "独立参考"},
            "space": {"scene": "月面", "axis": "H左G右", "anchors": ["飞船"], "prop_state": {"杯": "桌上"}},
            "motion": {"actions": ["G靠近"], "contact_order": ["接近", "停步"], "physics": "脚底接地", "failure_fallback": "停顿"},
            "camera": {"shot_design": "中景", "path": "侧移", "focus": "H到G", "transition": "遮挡"},
            "assets": {"task_type": "reference", "motion_reference": "previs.mp4", "reference_roles": {"image1": "H"}, "missing_assets": [], "inventory_complete": True},
            "delivery": {"resolution": "720p", "max_paid_tasks": 1, "budget_cny": 20, "acceptance": ["人数稳定"], "stop_condition": "第一条失败即停"}
        }
        result = self.workflow.run(payload)
        self.assertEqual(result["status"], "DESIGN_READY")


if __name__ == "__main__":
    unittest.main()
