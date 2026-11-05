"""unittest for contract_html.py — invokes via subprocess + tempfile."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = str(HERE.parent / 'contract_html.py')
PYTHON = sys.executable


def _run(state_data, extra_args=(), project_data=None, out_suffix='.html'):
    """Run contract_html.py in a temp dir; returns (returncode, stdout, stderr, out_path)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        state_path = os.path.join(tmpdir, 'state.json')
        with open(state_path, 'w', encoding='utf-8') as f:
            json.dump(state_data, f, ensure_ascii=False)
        out_path = os.path.join(tmpdir, 'output' + out_suffix)
        cmd = [PYTHON, SCRIPT, state_path, '--out', out_path]
        if project_data is not None:
            proj_path = os.path.join(tmpdir, 'project.json')
            with open(proj_path, 'w', encoding='utf-8') as f:
                json.dump(project_data, f, ensure_ascii=False)
            cmd += ['--project', proj_path]
        cmd += list(extra_args)
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
        html_content = ''
        if os.path.exists(out_path):
            with open(out_path, encoding='utf-8') as f:
                html_content = f.read()
        return result.returncode, result.stdout, result.stderr, html_content


def _min_state(shots=None):
    shots = shots or [
        {'shot_id': 'S01', 'summary': '第一镜'},
        {'shot_id': 'S02', 'summary': '第二镜'},
        {'shot_id': 'S03', 'summary': '第三镜'},
    ]
    return {
        'schema_version': 'director-production/v3',
        'project_id': 'test-project',
        'brief': {'request': '测试'},
        'shots': shots,
    }


class TestMinimalState(unittest.TestCase):
    def test_renders_single_merged_table_with_all_columns(self):
        """一张合并表：每个镜头一行，设计列与生成列同表。"""
        rc, stdout, stderr, html = _run(_min_state())
        self.assertEqual(rc, 0, msg=f'exit {rc}\nstderr: {stderr}')
        self.assertIn('id="design"', html)
        for col in ('镜头描述', '时长', '静态帧', '视频提示词', '完整提示词', '入上下文'):
            self.assertIn(f'<th>{col}</th>', html, msg=f'缺少列 {col}')

    def test_all_three_shot_ids_appear(self):
        rc, _, _, html = _run(_min_state())
        self.assertEqual(rc, 0)
        self.assertIn('S01', html)
        self.assertIn('S02', html)
        self.assertIn('S03', html)


class TestGroupHeaders(unittest.TestCase):
    def test_group_title_row_with_colspan(self):
        state = _min_state([
            {'shot_id': 'S01', 'summary': '镜一', 'group_id': 'G01'},
            {'shot_id': 'S02', 'summary': '镜二', 'group_id': 'G01'},
        ])
        state['groups'] = [{'group_id': 'G01', 'target_seconds': 6}]
        rc, _, _, html = _run(state)
        self.assertEqual(rc, 0)
        self.assertIn('G01', html)
        self.assertIn('colspan', html)


class TestStaticFrameThumbnails(unittest.TestCase):
    def test_two_frames_produce_two_img_or_placeholder_elements(self):
        state = _min_state([{
            'shot_id': 'S01',
            'summary': '含两张静态帧的镜头',
            'static_frames': [
                {'path': 'nonexistent_a.png', 'revision': 'v001', 'role': '首帧'},
                {'path': 'nonexistent_b.png', 'revision': 'v002', 'role': '尾帧'},
            ],
        }])
        rc, _, _, html = _run(state)
        self.assertEqual(rc, 0)
        # Both frames should render (img or placeholder)
        count = html.count('nonexistent_a') + html.count('nonexistent_b')
        self.assertGreaterEqual(count, 2, msg='两张帧的路径均应出现在 HTML 中')


class TestRejectedContractRendering(unittest.TestCase):
    def test_rejected_row_has_class_and_cross_mark(self):
        state = _min_state([{'shot_id': 'S01', 'summary': '被拒镜头'}])
        state['contracts'] = [{
            'contract_id': 'S01-v001',
            'scope': 'shot',
            'target_id': 'S01',
            'revision': 1,
            'decision': 'rejected',
            'reviewer': 'user',
            'decided_at': '2026-11-01T10:00:00+08:00',
            'reason': '质量不足',
            'context_eligible': False,
        }]
        rc, _, _, html = _run(state)
        self.assertEqual(rc, 0)
        self.assertIn('class="rejected"', html)
        self.assertIn('✗', html)


class TestThinkingSection(unittest.TestCase):
    def test_chosen_option_text_appears(self):
        state = _min_state()
        state['thinking'] = [{
            'thinking_id': 'T001',
            'scope': 'group',
            'target_id': 'G01',
            'question': '如何切分？',
            'understood': '需要三镜',
            'options': [
                {'option': '一镜到底', 'chosen': False, 'why': '缺停顿'},
                {'option': '三镜方案已选', 'chosen': True, 'why': '最优'},
            ],
            'decision': '三镜',
        }]
        rc, _, _, html = _run(state)
        self.assertEqual(rc, 0)
        self.assertIn('三镜方案已选', html)
        self.assertIn('opt-chosen', html)


class TestOmitProject(unittest.TestCase):
    def test_omitting_project_does_not_crash(self):
        rc, stdout, stderr, html = _run(_min_state(), project_data=None)
        self.assertEqual(rc, 0, msg=f'stderr: {stderr}')
        self.assertIn('id="design"', html)


class TestMissingOutputDirectory(unittest.TestCase):
    def test_nonexistent_out_dir_exits_nonzero(self):
        state = _min_state()
        with tempfile.TemporaryDirectory() as tmpdir:
            state_path = os.path.join(tmpdir, 'state.json')
            with open(state_path, 'w', encoding='utf-8') as f:
                json.dump(state, f)
            missing_dir = os.path.join(tmpdir, 'does_not_exist', 'output.html')
            cmd = [PYTHON, SCRIPT, state_path, '--out', missing_dir]
            result = subprocess.run(cmd, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)


class TestUnitRows(unittest.TestCase):
    def _unit_state(self, shots, unit):
        state = _min_state(shots)
        state['units'] = [unit]
        return state

    def test_unit_row_appears_once(self):
        """units[].groups[] 且 shots 带 group_id → 合并表里单元 U01 恰好一行。"""
        state = self._unit_state(
            [
                {'shot_id': 'S01', 'summary': '镜一', 'group_id': 'G01'},
                {'shot_id': 'S02', 'summary': '镜二', 'group_id': 'G01'},
            ],
            {'unit_id': 'U01', 'name': '测试单元',
             'groups': [{'group_id': 'G01', 'target_seconds': 6}]},
        )
        rc, _, stderr, html = _run(state)
        self.assertEqual(rc, 0, msg=f'stderr: {stderr}')
        self.assertEqual(html.count('单元 U01'), 1,
                         msg='合并表里单元 U01 只有一行')
        self.assertIn('<tr class="unit-row"', html)

    def test_unit_row_not_duplicated_per_group(self):
        """同一单元下两个组 → 单元 U01 仍然只出现 1 次。"""
        state = self._unit_state(
            [
                {'shot_id': 'S01', 'summary': '镜一', 'group_id': 'G01'},
                {'shot_id': 'S02', 'summary': '镜二', 'group_id': 'G02'},
            ],
            {'unit_id': 'U01', 'name': '测试单元',
             'groups': [
                 {'group_id': 'G01', 'target_seconds': 6},
                 {'group_id': 'G02', 'target_seconds': 4},
             ]},
        )
        rc, _, stderr, html = _run(state)
        self.assertEqual(rc, 0, msg=f'stderr: {stderr}')
        self.assertEqual(html.count('单元 U01'), 1,
                         msg='单元行不按组重复')

    def test_no_units_key_no_unit_row(self):
        """没有 units 键（平铺 shots 无 group_id）→ 无 unit-row，不报错。"""
        rc, _, stderr, html = _run(_min_state())
        self.assertEqual(rc, 0, msg=f'stderr: {stderr}')
        self.assertNotIn('<tr class="unit-row"', html)

    def test_unit_goal_appears_only_when_present(self):
        """unit 有 goal → 出现"目标："；没有 goal → 不出现。"""
        base_unit = {'unit_id': 'U01', 'name': '测试单元',
                     'groups': [{'group_id': 'G01', 'target_seconds': 6}]}
        shots = [{'shot_id': 'S01', 'summary': '镜一', 'group_id': 'G01'}]

        with_goal = self._unit_state(shots, {**base_unit, 'goal': '展现细节'})
        rc, _, stderr, html_w = _run(with_goal)
        self.assertEqual(rc, 0, msg=f'stderr: {stderr}')
        self.assertIn('目标：', html_w)

        no_goal = self._unit_state(shots, dict(base_unit))
        rc, _, stderr, html_n = _run(no_goal)
        self.assertEqual(rc, 0, msg=f'stderr: {stderr}')
        self.assertNotIn('目标：', html_n)


if __name__ == '__main__':
    unittest.main()
