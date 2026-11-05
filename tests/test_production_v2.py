import copy
import json
import unittest
from test_agent import ROOT, load_workflow


class ProductionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.w=load_workflow()
        cls.template=json.loads((ROOT/'examples/production_state.json').read_text(encoding='utf-8'))

    def setUp(self): self.state=copy.deepcopy(self.template)

    def refresh(self):
        for a in self.state['artifacts'].values():
            a['input_hashes']={d:self.w.fingerprint(self.state['artifacts'][d]['data']) for d in a['inputs']}
            a['inputs']={d:self.state['artifacts'][d]['revision'] for d in a['inputs']}

    def test_only_director_is_initially_ready(self):
        self.state['artifacts']={}
        self.assertEqual([r['stage'] for r in self.w.run(self.state)['ready']],['director_intent'])

    def test_storyboard_and_sound_fork_after_intent(self):
        self.state['artifacts']={k:v for k,v in self.state['artifacts'].items() if k=='director_intent'}
        self.assertEqual([r['stage'] for r in self.w.run(self.state)['ready']],['shot_design','sound_design'])

    def test_full_design_is_not_execution_authority(self):
        r=self.w.run(self.state)
        self.assertEqual(r['status'],'DESIGN_READY')
        self.assertFalse(r['execution_authorized'])

    def test_estimated_speech_cannot_freeze_timing(self):
        self.state['artifacts']['sound_design']['data']['dialogue'][0]['measured']=False
        self.refresh()
        r=self.w.run(self.state)
        self.assertEqual(r['stages']['sound_design']['state'],'valid')
        self.assertEqual(r['stages']['timing_lock']['state'],'invalid')
        self.assertEqual(r['stages']['scene_design']['state'],'stale')

    def test_audio_change_without_version_bump_invalidates_downstream(self):
        self.state['artifacts']['sound_design']['data']['dialogue'][0]['duration_seconds']=3.7
        r=self.w.run(self.state)
        self.assertIn('stale content: sound_design',r['stages']['timing_lock']['errors'])
        self.assertEqual(r['stages']['node_design']['state'],'stale')

    def test_scene_version_change_keeps_upstream(self):
        self.state['artifacts']['scene_design']['revision']=2
        r=self.w.run(self.state)
        self.assertEqual(r['stages']['timing_lock']['state'],'valid')
        self.assertEqual(r['stages']['action_design']['state'],'invalid')
        self.assertEqual(r['stages']['prompt_design']['state'],'stale')

    def test_long_speech_requires_longer_shot(self):
        self.state['artifacts']['sound_design']['data']['dialogue'][0]['duration_seconds']=5
        self.refresh()
        self.assertTrue(any('dialogue longer' in e for e in self.w.run(self.state)['stages']['timing_lock']['errors']))

    def test_no_dialogue_branch(self):
        a=self.state['artifacts']
        a['director_intent']['data']['has_dialogue']=False
        for shot in a['shot_design']['data']['shots']:shot['has_dialogue']=False
        a['sound_design']['data'].update(has_dialogue=False,dialogue=[])
        a['timing_lock']['data']['basis']='no_dialogue'
        for shot in a['timing_lock']['data']['timeline']:shot['dialogue_ids']=[]
        self.refresh()
        self.assertEqual(self.w.run(self.state)['status'],'DESIGN_READY')

    def test_unlocked_timing_is_not_present_true(self):
        self.state['artifacts']['timing_lock']['data']['locked']=False
        self.assertEqual(self.w.run(self.state)['stages']['timing_lock']['state'],'invalid')

    def test_shot_mapping_drift_fails(self):
        self.state['artifacts']['prompt_design']['data']['shots'][0]['shot_id']='NEW'
        self.assertEqual(self.w.run(self.state)['stages']['prompt_design']['state'],'invalid')

    def test_action_timeline_cannot_exceed_locked_shot(self):
        self.state['artifacts']['action_design']['data']['shots'][0]['beats'][-1]['end']=5
        self.assertEqual(self.w.run(self.state)['stages']['action_design']['state'],'invalid')

    def test_node_role_cannot_select_itself(self):
        self.state['artifacts']['node_design']['data']['selected_by']='node-design'
        self.assertEqual(self.w.run(self.state)['stages']['node_design']['state'],'invalid')

    def test_real_state_cannot_use_demo_audio(self):
        self.state['example_only']=False
        self.assertEqual(self.w.run(self.state)['stages']['sound_design']['state'],'invalid')

    def test_unknown_schema_is_rejected(self):
        self.assertEqual(self.w.run({'schema_version':'other'})['status'],'UNSUPPORTED_SCHEMA')

    def test_automatic_retry_is_rejected(self):
        self.state['artifacts']['node_design']['data']['auto_retry']=1
        self.assertEqual(self.w.run(self.state)['stages']['node_design']['state'],'invalid')

    def test_malformed_dependency_map_is_reported(self):
        self.state['artifacts']['shot_design']['inputs']=None
        self.assertEqual(self.w.run(self.state)['stages']['shot_design']['state'],'invalid')

    def test_nonfinite_content_does_not_crash_fingerprint(self):
        self.state['artifacts']['director_intent']['data']['invalid_number']=float('nan')
        self.assertEqual(self.w.run(self.state)['stages']['director_intent']['state'],'invalid')

if __name__=='__main__':unittest.main()
