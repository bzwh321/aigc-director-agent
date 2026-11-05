import importlib.util
import json
from pathlib import Path
import unittest
from test_agent import ROOT, load_workflow


def load_library():
    spec = importlib.util.spec_from_file_location('test_solutions', ROOT/'方案库/decide.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SolutionLibraryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lib = load_library()

    def facts(self, **changes):
        return dict({'input_kind':'image', 'operation':'generate', 'subject_motion':'none',
                     'camera_motion':'pan', 'hard_end_frame':False, 'needs_new_pixels':False}, **changes)

    def test_local_pan(self):
        result = self.lib.decide(self.facts())
        self.assertEqual(result['recipe_id'], 'local-still-pan')
        self.assertFalse(result['execution_authorized'])

    def test_body_action_not_local_pan(self):
        result = self.lib.decide(self.facts(subject_motion='required', needs_new_pixels=True))
        self.assertEqual(result['recipe_id'], 'image-to-video')

    def test_conflicting_no_new_pixels(self):
        self.assertEqual(self.lib.decide(self.facts(subject_motion='required'))['status'], 'NEEDS_FACTS')

    def test_unknown_not_assumed_static(self):
        self.assertEqual(self.lib.decide(self.facts(subject_motion='unknown'))['status'], 'NEEDS_FACTS')

    def test_missing_hard_end_not_assumed_false(self):
        f=self.facts();del f['hard_end_frame']
        self.assertEqual(self.lib.decide(f)['status'], 'NEEDS_FACTS')

    def test_first_last_requires_compatible_endpoints(self):
        f=self.facts(hard_end_frame=True,needs_new_pixels=True)
        self.assertEqual(self.lib.decide(f)['status'], 'NEEDS_FACTS')
        f.update(endpoints_compatible=True,simple_middle_action=True)
        self.assertEqual(self.lib.decide(f)['recipe_id'], 'first-last-frame')

    def test_edit_needs_motion_evidence(self):
        f={'input_kind':'video','operation':'edit','real_motion_verified':False}
        self.assertIsNone(self.lib.decide(f)['recipe_id'])
        f['real_motion_verified']=True
        self.assertEqual(self.lib.decide(f)['recipe_id'], 'video-edit')

    def test_extend_requires_accepted_source(self):
        f={'input_kind':'video','operation':'extend'}
        self.assertEqual(self.lib.decide(f)['status'], 'NEEDS_FACTS')
        f['source_accepted']=True
        self.assertEqual(self.lib.decide(f)['recipe_id'], 'video-extend')

    def test_video_reference_not_slideshow(self):
        f={'input_kind':'video','operation':'generate','hard_end_frame':False}
        self.assertEqual(self.lib.decide(f)['status'], 'NEEDS_FACTS')
        f['dynamic_reference_verified']=True
        self.assertEqual(self.lib.decide(f)['recipe_id'], 'multimodal-reference')

    def test_stable_background_needs_crop_margin(self):
        f=self.facts(subject_motion='required',needs_new_pixels=True,locked_background=True)
        self.assertEqual(self.lib.decide(f)['status'], 'NEEDS_FACTS')
        f['crop_margin_verified']=True
        self.assertEqual(self.lib.decide(f)['recipe_id'], 'fixed-plate-local-reframe')

    def test_three_dimensional_move_not_fake_pan(self):
        f=self.facts(subject_motion='required',needs_new_pixels=True,locked_background=True,crop_margin_verified=True,camera_motion='translate')
        self.assertEqual(self.lib.decide(f)['status'], 'DIRECTOR_CHOICE')

    def test_offscreen_voice_no_lipsync(self):
        f={'input_kind':'video','operation':'lipsync','visible_speaker':False}
        self.assertEqual(self.lib.decide(f)['status'], 'NOT_NEEDED')

    def test_accepted_lipsync(self):
        f={'input_kind':'video','operation':'lipsync','visible_speaker':True,'source_accepted':True,'audio_ready':True}
        self.assertEqual(self.lib.decide(f)['recipe_id'], 'dialogue-lipsync')

    def test_no_truthy_string(self):
        self.assertEqual(self.lib.decide(self.facts(needs_new_pixels='false'))['status'], 'INVALID_FACTS')

    def test_no_unknown_field_or_secret_echo(self):
        f=self.facts();f['api_key']='TEST_CANARY_DO_NOT_ECHO'
        self.assertNotIn('TEST_CANARY', json.dumps(self.lib.decide(f)))

    def test_fingerprint_changes_with_fact_or_catalog(self):
        f=self.facts();a=self.lib.decide(f)['decision_fingerprint']
        self.assertEqual(a,self.lib.decide(f)['decision_fingerprint'])
        self.assertNotEqual(a,self.lib.decide(self.facts(camera_motion='zoom'))['decision_fingerprint'])
        catalog=json.loads((self.lib.ROOT/'catalog.json').read_text(encoding='utf-8'))
        catalog['version']='test-new-version'
        self.assertNotEqual(a,self.lib.decide(f,catalog)['decision_fingerprint'])

    def test_v3_uses_library_and_skips_prompt_for_local_pan(self):
        w=load_workflow()
        result=w.run({'brief':{'request':'picture pan','render_mode':'generate','subject_motion':'none',
                              'solution_facts':self.facts()}})
        self.assertEqual(result['solution_decisions']['S01']['recipe_id'],'local-still-pan')
        prompt=next(x for x in result['routes']['S01'] if x['role']=='prompt-design')
        self.assertEqual(prompt['decision'],'skip')

    def test_shot_override_and_isolation(self):
        decisions=self.lib.plan_shots({'solution_facts':self.facts()},[
            {'shot_id':'S1'}, {'shot_id':'S2','solution_facts':{'subject_motion':'required','needs_new_pixels':True}}])
        self.assertEqual(decisions['S1']['recipe_id'],'local-still-pan')
        self.assertEqual(decisions['S2']['recipe_id'],'image-to-video')

    def test_legacy_plan_also_consults_library(self):
        result=load_workflow().run({'schema_version':'director-production/v2','artifacts':{}})
        self.assertEqual(result['solution_decisions']['S01']['status'],'NEEDS_FACTS')
        self.assertFalse(result['execution_authorized'])

    def test_conflicting_role_and_solution_facts_stop(self):
        with self.assertRaises(ValueError):
            self.lib.plan_shots({'subject_motion':'required','solution_facts':self.facts()},[{'shot_id':'S01'}])

    def test_catalog_sources_and_service_references(self):
        root=self.lib.ROOT
        catalog=json.loads((root/'catalog.json').read_text(encoding='utf-8'))
        services=json.loads((root/'services.json').read_text(encoding='utf-8'))['services']
        creds=json.loads((root/'credentials.json').read_text(encoding='utf-8'))['entries']
        self.assertEqual(len({r['id'] for r in catalog['recipes']}),len(catalog['recipes']))
        for r in catalog['recipes']:
            self.assertTrue(set(r['services']) <= {s['id'] for s in services})
            for src in r['evidence']:
                self.assertTrue((root/src).is_file(),src)
        for s in services:
            self.assertTrue(set(s['credential_refs']) <= {c['id'] for c in creds})
        for c in creds:
            self.assertFalse({'api_key','apiKey','token','password','value'} & set(c))


if __name__ == '__main__':
    unittest.main()
