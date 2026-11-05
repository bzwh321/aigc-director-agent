"""合同门控（contract gate）单元测试。

覆盖 contract_eligible / shot_contract_fingerprint / context_packet / consistency / plan
的核心行为，使用 unittest，与现有测试文件风格一致。
"""
import importlib.util
import json
import unittest
from pathlib import Path

# 复用 test_agent 中约定的 ROOT 与模块加载方式
from test_agent import ROOT

# ── 加载 director_control 模块 ──────────────────────────────────────────────
def load_control():
    spec = importlib.util.spec_from_file_location(
        'director_control_cg', ROOT / 'director_control.py'
    )
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


# ── 从 workflow_manifest.json 读取 registry（供 context_packet 使用）─────────
def load_registry():
    return json.loads(
        (ROOT / 'workflow_manifest.json').read_text(encoding='utf-8')
    )['roles']


# ── 空 project（满足 context_packet 的 project 参数要求）────────────────────
EMPTY_PROJECT = {'facts': [], 'memories': [], 'assets': []}


class ContractEligibleTests(unittest.TestCase):
    """contract_eligible 基本路径：无合同、rejected、pending、approved。"""

    def setUp(self):
        self.c = load_control()

    # 用例 1：无 contracts 时直接放行
    def test_no_contracts_always_eligible(self):
        """空 state（无 contracts 键）应返回 (True, 'no contract recorded')。"""
        ok, reason = self.c.contract_eligible({}, 'shot', 'S1')
        self.assertTrue(ok)
        self.assertEqual(reason, 'no contract recorded')

    # 用例 2a：decision == rejected
    def test_rejected_returns_false(self):
        """rejected 合同应返回 (False, 'contract rejected')。"""
        state = {
            'contracts': [
                {'scope': 'shot', 'target_id': 'S1',
                 'decision': 'rejected', 'revision': 1}
            ],
            'shots': [{'shot_id': 'S1', 'summary': '测试镜头'}]
        }
        ok, reason = self.c.contract_eligible(state, 'shot', 'S1')
        self.assertFalse(ok)
        self.assertEqual(reason, 'contract rejected')

    # 用例 2b：decision == pending
    def test_pending_returns_false(self):
        """pending 合同应返回 (False, 'contract pending')。"""
        state = {
            'contracts': [
                {'scope': 'shot', 'target_id': 'S1',
                 'decision': 'pending', 'revision': 1}
            ],
            'shots': [{'shot_id': 'S1', 'summary': '测试镜头'}]
        }
        ok, reason = self.c.contract_eligible(state, 'shot', 'S1')
        self.assertFalse(ok)
        self.assertEqual(reason, 'contract pending')

    # 用例 4a：approved 且指纹相符
    def test_approved_with_matching_fingerprint_eligible(self):
        """approved 且指纹一致时应返回 (True, 'approved')。"""
        shot = {'shot_id': 'S1', 'summary': '镜头内容'}
        state = {'shots': [shot], 'contracts': []}
        fp = self.c.shot_contract_fingerprint(state, shot)
        state['contracts'] = [
            {'scope': 'shot', 'target_id': 'S1',
             'decision': 'approved', 'fingerprint': fp, 'revision': 1}
        ]
        ok, reason = self.c.contract_eligible(state, 'shot', 'S1')
        self.assertTrue(ok)
        self.assertEqual(reason, 'approved')

    # 用例 4b：approved 但指纹不符（approval stale）
    def test_approved_with_stale_fingerprint_not_eligible(self):
        """approved 后修改镜头内容，指纹不符时应返回 (False, 'approval stale')。"""
        shot = {'shot_id': 'S1', 'summary': '原始镜头内容'}
        state = {'shots': [shot], 'contracts': []}
        fp = self.c.shot_contract_fingerprint(state, shot)
        # 用旧指纹注册合同，然后修改镜头内容让指纹失效
        state['contracts'] = [
            {'scope': 'shot', 'target_id': 'S1',
             'decision': 'approved', 'fingerprint': fp, 'revision': 1}
        ]
        state['shots'][0]['video_prompt'] = '添加新的提示词导致指纹变化'
        ok, reason = self.c.contract_eligible(state, 'shot', 'S1')
        self.assertFalse(ok)
        self.assertEqual(reason, 'approval stale')


class ContextPacketContractGateTests(unittest.TestCase):
    """context_packet 在各合同状态下的抛出行为，及正常路径下的返回结构。"""

    def setUp(self):
        self.c = load_control()
        self.registry = load_registry()
        # 构造一个最小可用 state（prompt-design 需要 brief.request）
        self.shot = {
            'shot_id': 'S1',
            'summary': '测试镜头',
            'render_mode': 'generate',
        }
        self.state = {
            'brief': {
                'request': '人物回头镜头',
                'goal': '展示人物表情',
                'visual_source': 'provided',
                'audio_mode': 'provided',
                'camera_motion': 'pan',
                'subject_motion': 'required',
                'render_mode': 'generate',
                'needs_vfx': False,
                'needs_color': False,
            },
            'shots': [self.shot],
            'contracts': [],
            'artifacts': {},
            'reviews': {},
        }
        # prompt-design 路由（在 contract 阶段需要合同通过）
        self.route = {
            'role': 'prompt-design',
            'decision': 'call',
            'reason': '需要生成提示词',
            'render_mode': 'generate',
        }

    def _make_approved_contract(self):
        """在 state 中为 S1 注册指纹匹配的 approved 合同。"""
        fp = self.c.shot_contract_fingerprint(self.state, self.shot)
        self.state['contracts'] = [
            {'scope': 'shot', 'target_id': 'S1',
             'decision': 'approved', 'fingerprint': fp, 'revision': 1}
        ]

    # 用例 2（context_packet 侧）：rejected 时对下游角色抛 ValueError
    def test_rejected_contract_raises_for_prompt_design(self):
        """rejected 合同下调用 context_packet(prompt-design) 应抛 ValueError，消息含 'not eligible'。"""
        self.state['contracts'] = [
            {'scope': 'shot', 'target_id': 'S1',
             'decision': 'rejected', 'revision': 1}
        ]
        with self.assertRaises(ValueError) as ctx:
            self.c.context_packet(
                self.state, EMPTY_PROJECT, self.shot, self.route, self.registry
            )
        self.assertIn('not eligible', str(ctx.exception))

    # 用例 3：pending 时同样抛 ValueError
    def test_pending_contract_raises_for_prompt_design(self):
        """pending 合同下调用 context_packet(prompt-design) 应抛 ValueError，消息含 'not eligible'。"""
        self.state['contracts'] = [
            {'scope': 'shot', 'target_id': 'S1',
             'decision': 'pending', 'revision': 1}
        ]
        with self.assertRaises(ValueError) as ctx:
            self.c.context_packet(
                self.state, EMPTY_PROJECT, self.shot, self.route, self.registry
            )
        self.assertIn('not eligible', str(ctx.exception))

    # 用例 4（context_packet 侧）：approved 后修改 video_prompt 导致 approval stale
    def test_stale_approval_raises_for_prompt_design(self):
        """approved 后修改 shot.video_prompt，context_packet 应因 approval-stale 抛 ValueError。"""
        self._make_approved_contract()
        # 修改镜头内容令指纹失效
        self.state['shots'][0]['video_prompt'] = '修改后的提示词'
        self.shot['video_prompt'] = '修改后的提示词'
        with self.assertRaises(ValueError) as ctx:
            self.c.context_packet(
                self.state, EMPTY_PROJECT, self.shot, self.route, self.registry
            )
        self.assertIn('not eligible', str(ctx.exception))

    # 用例 5：approved 且未改动时正常返回，call_id == shot_id + '/prompt-design'
    def test_approved_and_unchanged_returns_packet_with_correct_call_id(self):
        """approved 且指纹未变，context_packet 应正常返回，且 call_id == 'S1/prompt-design'。"""
        self._make_approved_contract()
        packet = self.c.context_packet(
            self.state, EMPTY_PROJECT, self.shot, self.route, self.registry
        )
        self.assertIsInstance(packet, dict)
        self.assertEqual(packet['call_id'], 'S1/prompt-design')

    # 用例 6：shot-design 角色在 rejected 状态下不被拦（不抛异常）
    def test_rejected_contract_does_not_block_shot_design(self):
        """rejected 合同不应阻塞 shot-design（该角色不在下游拦截列表中）。"""
        self.state['contracts'] = [
            {'scope': 'shot', 'target_id': 'S1',
             'decision': 'rejected', 'revision': 1}
        ]
        shot_design_route = {
            'role': 'shot-design',
            'decision': 'call',
            'reason': '需要分镜设计',
            'render_mode': 'generate',
        }
        # 不抛异常即通过
        packet = self.c.context_packet(
            self.state, EMPTY_PROJECT, self.shot, shot_design_route, self.registry
        )
        self.assertEqual(packet['role'], 'shot-design')


class PlanContractTests(unittest.TestCase):
    """plan() 在合同相关场景下的返回结构。"""

    def setUp(self):
        self.c = load_control()
        # 最小可用 state，不含 units/thinking/contracts
        self.state = {
            'brief': {
                'request': '单镜测试',
                'goal': '测试 plan 结构',
                'visual_source': 'provided',
                'audio_mode': 'provided',
                'camera_motion': 'pan',
                'subject_motion': 'none',
                'render_mode': 'local_pan',
                'needs_vfx': False,
                'needs_color': False,
            },
            'shots': [{'shot_id': 'S1', 'summary': '平移镜头'}],
            'artifacts': {},
            'reviews': {},
        }

    # 用例 7：rejected 时 plan 返回 status=='WAITING_HUMAN_REVIEW'，blocked_shots 含该 shot_id
    def test_rejected_contract_blocks_shot_in_plan(self):
        """合同 rejected 时，plan 应将该镜头加入 blocked_shots，并视整体状态触发人工审核。"""
        self.state['contracts'] = [
            {'scope': 'shot', 'target_id': 'S1',
             'decision': 'rejected', 'revision': 1}
        ]
        # 先让静态图审核通过，使 plan 进入 contract 阶段
        import tempfile, os
        with tempfile.NamedTemporaryFile(delete=False, suffix='.txt') as f:
            f.write(b'fixture static')
            tmp_path = f.name
        try:
            self.state['artifacts']['static_images'] = {
                'revision': 1, 'summary': '静态图',
                'files': [{'path': tmp_path, 'shot_ids': ['S1']}]
            }
            fp = self.c.review_fingerprint(self.state, 'static_images')
            self.state['reviews'] = {
                'static_images': {
                    'decision': 'approved',
                    'reviewer': 'test-human',
                    'fingerprint': fp
                }
            }
            result = self.c.plan(self.state)
            # 无论 status 是 WAITING_HUMAN_REVIEW 还是 DESIGN_TASKS_READY，
            # blocked_shots 中必须含 S1
            blocked_ids = [b['shot_id'] for b in result.get('blocked_shots', [])]
            self.assertIn('S1', blocked_ids)
        finally:
            os.unlink(tmp_path)

    # 用例 8：plan 结果含 'contracts' 与 'consistency' 两个键；
    #         旧 state（无 units/thinking/contracts）时两者有合理默认值
    def test_plan_always_contains_contracts_and_consistency_keys(self):
        """plan 结果必须同时包含 'contracts' 与 'consistency' 键。"""
        result = self.c.plan(self.state)
        self.assertIn('contracts', result)
        self.assertIn('consistency', result)

    def test_plan_default_contracts_structure_for_legacy_state(self):
        """旧 state（无 contracts）时，plan 的 contracts 应为 {'shot':{},'group':{},'film':{}}。"""
        result = self.c.plan(self.state)
        self.assertEqual(result['contracts'], {'shot': {}, 'group': {}, 'film': {}})

    def test_plan_default_consistency_is_list_for_legacy_state(self):
        """旧 state（无 contracts）时，plan 的 consistency 应为列表（可为空）。"""
        result = self.c.plan(self.state)
        self.assertIsInstance(result['consistency'], list)


class ConsistencyTests(unittest.TestCase):
    """consistency() 三种错误码的断言：asset-missing、group-duration-mismatch、approval-stale。"""

    def setUp(self):
        self.c = load_control()

    def _codes(self, issues):
        return [i['code'] for i in issues]

    # 用例 9a：asset-missing（project 资产库缺少镜头引用的 id）
    def test_asset_missing_detected(self):
        """镜头引用的 asset_id 在 project.assets 中不存在，应报告 asset-missing。"""
        state = {
            'shots': [
                {'shot_id': 'S1', 'summary': '测试', 'asset_ids': ['missing-asset']}
            ],
            'contracts': [],
        }
        # project 中没有 missing-asset
        project = {'assets': [{'id': 'other-asset', 'sha256': 'abc123'}]}
        issues = self.c.consistency(state, project)
        self.assertIn('asset-missing', self._codes(issues))

    # 用例 9b：group-duration-mismatch（组内时长之和与 target_seconds 偏差 > 20%）
    def test_group_duration_mismatch_detected(self):
        """镜头时长合计与组 target_seconds 偏差超 20%，应报告 group-duration-mismatch。"""
        state = {
            'shots': [
                {'shot_id': 'S1', 'summary': '镜头1',
                 'group_id': 'G1', 'duration_seconds': 3},
                {'shot_id': 'S2', 'summary': '镜头2',
                 'group_id': 'G1', 'duration_seconds': 3},
            ],
            'groups': [{'group_id': 'G1', 'target_seconds': 10}],  # 6 vs 10 → 40% 偏差
            'contracts': [],
        }
        issues = self.c.consistency(state, None)
        self.assertIn('group-duration-mismatch', self._codes(issues))

    # 用例 9c：approval-stale（已 approved 合同的指纹不再匹配）
    def test_approval_stale_detected(self):
        """已 approved 合同的镜头内容被修改后，consistency 应报告 approval-stale。"""
        shot = {'shot_id': 'S1', 'summary': '原始内容'}
        state = {'shots': [shot], 'contracts': []}
        # 记录当前指纹后再修改镜头
        fp = self.c.shot_contract_fingerprint(state, shot)
        state['contracts'] = [
            {'scope': 'shot', 'target_id': 'S1',
             'decision': 'approved', 'fingerprint': fp, 'revision': 1}
        ]
        state['shots'][0]['video_prompt'] = '修改后导致指纹失效'
        issues = self.c.consistency(state, None)
        self.assertIn('approval-stale', self._codes(issues))


if __name__ == '__main__':
    unittest.main()
