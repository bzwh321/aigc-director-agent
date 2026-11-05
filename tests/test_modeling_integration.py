import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from test_agent import ROOT, load_workflow


class ModelingIntegrationTests(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.spec_from_file_location('model_control', ROOT / 'director_control.py')
        self.control = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.control)
        self.workflow = load_workflow()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.state = {'request_type': 'modeling', 'brief': {
            'request': '建立参考图中的可编辑白模',
            'modeling_brief': {'mode': 'build', 'prompt': '保留主轮廓与真实开口',
                               'output_root': str(Path(self.tmp.name) / 'model-output')}
        }}

    def test_standalone_modeling_does_not_require_video_pipeline(self):
        before = copy.deepcopy(self.state)
        with patch.object(self.control, 'solution_decisions', side_effect=AssertionError('video router called')):
            result = self.control.plan(self.state)
        self.assertEqual(result['status'], 'MODELING_TASKS_READY')
        self.assertEqual([c['role'] for c in result['ready']], ['modeling-design'])
        self.assertEqual(result['fixed_human_checkpoints'], [])
        self.assertNotIn('solution_decisions', result)
        self.assertFalse(result['execution_authorized'])
        self.assertEqual(self.state, before)

    def test_workflow_entry_reaches_modeling(self):
        result = self.workflow.run(self.state)
        self.assertEqual(result['ready'][0]['role'], 'modeling-design')
        self.assertTrue(Path(result['ready'][0]['skill']).is_file())

    def test_no_default_lookdev_or_audio_history_in_modeling_packet(self):
        self.state['brief'].update(style_id='irrelevant-style', audio_history='UNRELATED TTS', subject_motion='unknown')
        result = self.workflow.run(self.state)
        self.assertEqual(result['status'], 'MODELING_TASKS_READY')
        packet = result['ready'][0]
        self.assertNotIn('visual_style', packet)
        self.assertNotIn('UNRELATED TTS', json.dumps(packet))

    def test_categories_are_not_hardwired_to_previous_scene(self):
        for category in ('product', 'stylized-creature', 'architecture', 'unfamiliar-shape'):
            with self.subTest(category=category):
                self.state['brief']['modeling_brief']['object_category'] = category
                result = self.workflow.run(self.state)
                self.assertEqual(result['ready'][0]['modeling_brief']['object_category'], category)

    def test_unit_context_wins_and_unrelated_unit_stays_out(self):
        self.state['brief']['modeling_brief']['known_dimensions'] = {'x': 1}
        self.state['shots'] = [{'shot_id': 'A1', 'known_dimensions': {'x': 2},
                               'modeling_brief': {'prompt': 'A1 SHAPE'}},
                              {'shot_id': 'A2', 'modeling_brief': {'prompt': 'A2 DIFFERENT'}}]
        calls = self.workflow.run(self.state)['ready']
        self.assertEqual(calls[0]['modeling_brief']['known_dimensions'], {'x': 2})
        self.assertNotIn('A2 DIFFERENT', json.dumps(calls[0]))

    def test_missing_reference_stops_without_claiming_a_model(self):
        self.state['brief']['modeling_brief']['reference_images'] = [{'path': str(Path(self.tmp.name) / 'missing.png'), 'role': 'shape'}]
        result = self.workflow.run(self.state)
        self.assertEqual(result['status'], 'NEEDS_HUMAN_REVIEW')
        self.assertEqual(result['ready'], [])

    def test_replaced_reference_content_changes_fingerprint(self):
        source = Path(self.tmp.name) / 'reference.bin'
        source.write_bytes(b'fixture input; not a real image')
        self.state['brief']['modeling_brief']['reference_images'] = [{'path': str(source), 'role': 'shape'}]
        first = self.workflow.run(self.state)['ready'][0]
        source.write_bytes(b'changed content at same path')
        second = self.workflow.run(self.state)['ready'][0]
        self.assertNotEqual(first['input_fingerprint'], second['input_fingerprint'])

    def test_completed_modeling_reuses_only_existing_outputs(self):
        call = self.workflow.run(self.state)['ready'][0]
        output = Path(self.tmp.name) / 'result-fixture.txt'
        output.write_text('test evidence reference, not an actual 3D output', encoding='utf-8')
        self.state['completed_calls'] = {call['call_id']: {
            'status': 'completed', 'input_fingerprint': call['input_fingerprint'], 'outputs': [str(output)]}}
        result = self.workflow.run(self.state)
        self.assertEqual(result['status'], 'MODELING_REVIEW_NEEDED')
        self.assertEqual(result['ready'], [])
        self.assertFalse(result['execution_authorized'])
        output.unlink()
        self.assertEqual(self.workflow.run(self.state)['status'], 'NEEDS_HUMAN_REVIEW')

    def test_completion_without_output_is_not_reused(self):
        call = self.workflow.run(self.state)['ready'][0]
        self.state['completed_calls'] = {call['call_id']: {
            'status': 'completed', 'input_fingerprint': call['input_fingerprint'], 'output_summary': 'done'}}
        self.assertEqual(self.workflow.run(self.state)['status'], 'NEEDS_HUMAN_REVIEW')

    def test_problem_stops_modeling_dispatch(self):
        self.state['issues'] = [{'id': 'first-failure', 'status': 'failed'}]
        result = self.workflow.run(self.state)
        self.assertEqual(result['status'], 'NEEDS_HUMAN_REVIEW')
        self.assertEqual(result['ready'], [])

    def test_ordinary_video_does_not_require_modeling(self):
        routes = self.control.select_roles({'request': 'image pan', 'render_mode': 'local_pan',
                                            'subject_motion': 'none', 'visual_source': 'provided'}, {})
        modeling = next(r for r in routes if r['role'] == 'modeling-design')
        self.assertEqual(modeling['decision'], 'skip')

    def test_video_routes_scene_then_modeling_when_explicitly_needed(self):
        state = {'brief': {'request': '视频需要三维空间资产', 'visual_source': 'provided',
                           'needs_modeling': True, 'modeling_brief': {'mode': 'plan'}}}
        first = self.workflow.run(state)['ready'][0]
        self.assertEqual(first['role'], 'modeling-design')
        state['brief']['needs_scene_design'] = True
        self.assertEqual(self.workflow.run(state)['ready'][0]['role'], 'scene-design')

    def test_modeling_core_context_is_not_silently_truncated(self):
        self.state['brief']['modeling_brief']['prompt'] = 'x' * 15000
        result = self.workflow.run(self.state)
        self.assertEqual(result['status'], 'NEEDS_HUMAN_REVIEW')
        self.assertEqual(result['ready'], [])


if __name__ == '__main__':
    unittest.main()
