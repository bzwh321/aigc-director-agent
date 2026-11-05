import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from test_agent import ROOT, load_workflow


class DirectorControlTests(unittest.TestCase):
    def setUp(self):
        spec=importlib.util.spec_from_file_location('test_control_module',ROOT/'director_control.py')
        self.c=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.c)
        self.w=load_workflow()
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.state={'schema_version':'director-production/v3','brief':{
            'request':'已有图片加音频，平移镜头，人物回头','goal':'平移与人物动作分开',
            'audio_mode':'provided','visual_source':'provided','camera_motion':'pan',
            'subject_motion':'required','render_mode':'local_pan','needs_vfx':False,'needs_color':False},
            'shots':[{'shot_id':'S01','summary':'人物回头'}], 'artifacts':{},'reviews':{}}

    def artifact(self,key,shots=None):
        p=Path(self.tmp.name)/(key+'.txt');p.write_text('fixture '+key,encoding='utf-8')
        files=[{'path':str(p),'shot_ids':shots or ['S01']}]
        self.state['artifacts'][key]={'revision':1,'summary':key,'files':files}
        return p

    def approve(self,key):
        packet=self.c.review_packet(self.state,key)
        self.state['reviews'][key]={'decision':'approved','reviewer':'test-human','fingerprint':packet['fingerprint']}

    def reach_contract(self):self.artifact('static_images');self.approve('static_images')
    def reach_execution(self):self.reach_contract();self.artifact('contract');self.approve('contract')

    def test_example_skips_sound_and_vfx_but_keeps_action(self):
        r=self.w.run(self.state);routes={x['role']:x for x in r['routes']['S01']}
        self.assertEqual(routes['sound-design']['decision'],'reuse')
        self.assertEqual(routes['vfx-design']['decision'],'skip')
        self.assertEqual(routes['action-design']['decision'],'call')
        self.assertEqual(routes['prompt-design']['decision'],'call')
        self.assertEqual(routes['node-design']['render_mode'],'generate')

    def test_static_subject_local_pan_needs_no_model_prompt(self):
        self.state['brief']['subject_motion']='none'
        routes=self.c.select_roles(self.state['brief'],self.state['shots'][0])
        self.assertEqual(next(x for x in routes if x['role']=='prompt-design')['decision'],'skip')

    def test_review_order_is_static_contract_final(self):
        self.artifact('static_images');self.artifact('contract');self.artifact('final')
        for key in ('static_images','contract','final'):
            r=self.w.run(self.state)
            self.assertEqual(r['human_review']['checkpoint'],key)
            self.assertEqual(r['ready'],[])
            self.approve(key)
        self.assertEqual(self.w.run(self.state)['status'],'COMPLETE')
        self.assertFalse(self.w.run(self.state)['execution_authorized'])

    def test_first_failure_stops_every_auto_dispatch(self):
        self.reach_contract();self.state['issues']=[{'id':'run-1','status':'failed','evidence':'first failure'}]
        r=self.w.run(self.state)
        self.assertEqual(r['status'],'NEEDS_HUMAN_REVIEW');self.assertEqual(r['ready'],[])
        self.assertFalse(r['automatic_retry'])

    def test_changed_contract_requires_review(self):
        self.reach_execution();self.state['brief']['goal']='new content'
        self.assertEqual(self.w.run(self.state)['human_review']['checkpoint'],'contract')

    def test_audio_change_does_not_invalidate_static(self):
        self.reach_execution();self.state['brief']['audio_mode']='design'
        self.assertTrue(self.c.approved(self.state,'static_images'))
        self.assertFalse(self.c.approved(self.state,'contract'))

    def test_editing_review_file_in_place_invalidates_approval(self):
        p=self.artifact('static_images');self.approve('static_images')
        p.write_text('different sized new fixture',encoding='utf-8')
        self.assertFalse(self.c.approved(self.state,'static_images'))

    def test_post_agents_wait_for_video(self):
        self.state['brief'].update(needs_vfx=True,needs_color=True)
        self.reach_execution()
        self.assertEqual(self.w.run(self.state)['ready'],[])
        self.artifact('video')
        self.assertEqual([x['role'] for x in self.w.run(self.state)['ready']],['vfx-design'])

    def test_unresolved_recipe_cannot_proceed_to_generation(self):
        self.reach_execution()
        result=self.w.run(self.state)
        self.assertEqual(result['status'],'NEEDS_SOLUTION_DECISION')
        self.assertEqual(result['ready'],[])
        self.assertFalse(result['execution_authorized'])

    def test_context_excludes_audio_history_and_other_shots(self):
        self.state['brief']['needs_vfx']=True;self.reach_execution();self.artifact('video')
        self.state['facts']=[
            {'id':'audio-secret','summary':'FULL TTS HISTORY','roles':['sound-design'],'topics':['audio'],'shot_ids':['S01']},
            {'id':'other-shot','summary':'UNRELATED S02','roles':['vfx-design'],'topics':['vfx'],'shot_ids':['S02']},
            {'id':'effect','summary':'S01 light fades','roles':['vfx-design'],'topics':['vfx'],'shot_ids':['S01']}]
        packet=self.w.run(self.state)['ready'][0];text=json.dumps(packet)
        self.assertNotIn('FULL TTS HISTORY',text);self.assertNotIn('UNRELATED S02',text)
        self.assertIn('S01 light fades',text)

    def test_context_budget_and_on_demand_refs(self):
        self.reach_contract();self.state['context_budget_chars']=1800
        self.state['memories']=[{'id':'long-note','summary':'x'*5000,'roles':['action-design'],
                                'topics':['motion'],'shot_ids':[]}]
        packet=next(x for x in self.w.run(self.state)['ready'] if x['role']=='action-design')
        self.assertLessEqual(packet['context_chars'],1800);self.assertIn('long-note',packet['omitted_refs'])

    def test_completed_identical_call_is_reused(self):
        self.reach_contract();r=self.w.run(self.state);call=r['ready'][0]
        self.state['completed_calls']={call['call_id']:{'status':'completed','input_fingerprint':call['input_fingerprint'],
                                                       'output_summary':'Accepted motion description'}}
        self.assertNotIn(call['call_id'],[x['call_id'] for x in self.w.run(self.state)['ready']])

    def test_action_output_precedes_prompt_and_node(self):
        self.reach_contract();first=self.w.run(self.state)['ready']
        self.assertEqual([x['role'] for x in first],['action-design'])
        call=first[0]
        self.state['completed_calls']={call['call_id']:{'status':'completed','input_fingerprint':call['input_fingerprint'],
                                                       'output_summary':'Head turns while camera translates'}}
        following=self.w.run(self.state)['ready']
        self.assertEqual([x['role'] for x in following],['prompt-design'])
        self.assertIn('Head turns while camera translates',json.dumps(following))

    def test_reasons_required_for_manual_override(self):
        self.state['shots'][0]['role_decisions']={'node-design':{'decision':'skip','reason':''}}
        self.assertEqual(self.w.run(self.state)['status'],'NEEDS_HUMAN_REVIEW')

    def test_question_for_unknown_independent_motion(self):
        self.state['brief']['subject_motion']='unknown'
        self.assertEqual(self.w.run(self.state)['status'],'NEEDS_CLARIFICATION')

    def test_explicit_action_design_can_determine_unknown_motion(self):
        self.state['brief'].update(needs_action_design=True,subject_motion='unknown')
        self.reach_contract()
        result=self.w.run(self.state)
        self.assertEqual(result['status'],'DESIGN_TASKS_READY')
        self.assertEqual(result['ready'][0]['role'],'action-design')

    def test_static_image_action_design_is_not_skipped(self):
        self.state['brief'].update(needs_action_design=True,subject_motion='none',camera_motion='none')
        self.reach_contract()
        self.assertEqual(self.w.run(self.state)['ready'][0]['role'],'action-design')

    def test_action_context_is_shot_scoped_and_excludes_sound_history(self):
        self.reach_contract()
        self.state['brief'].update(static_image_ref='shared.png',duration_seconds=8,
                                  audio_production_history='PRIVATE TTS HISTORY')
        self.state['shots'][0].update(static_image_ref='shot01.png',subject_audit_ref='shot01-subjects.json',
                                     narrative_purpose='Raise once then hold',duration_seconds=6)
        result=self.w.run(self.state)
        packet=result['ready'][0]
        self.assertEqual(packet['action_brief']['static_image_ref'],'shot01.png')
        self.assertEqual(packet['action_brief']['duration_seconds'],6)
        self.assertEqual(packet['action_brief']['subject_audit_ref'],'shot01-subjects.json')
        self.assertNotIn('PRIVATE TTS HISTORY',json.dumps(packet))

    def test_action_core_context_over_budget_is_not_silently_dropped(self):
        self.reach_contract()
        self.state['brief']['story_background']='x'*14000
        result=self.w.run(self.state)
        self.assertEqual(result['status'],'NEEDS_HUMAN_REVIEW')
        self.assertEqual(result['ready'],[])

    def test_brief_without_schema_still_uses_adaptive_routing(self):
        del self.state['schema_version'];self.state['assets']=[]
        self.assertIn('routes',self.w.run(self.state))

    def test_existing_image_can_still_require_environment_storytelling(self):
        self.state['brief']['needs_scene_design']=True
        r=self.w.run(self.state)
        self.assertEqual([x['role'] for x in r['ready']],['scene-design'])

    def test_scene_task_routes_narrative_and_preserves_small_context(self):
        self.state['brief'].update(scene_task='narrative_design',story_background='A maintained institution',
                                  narrative_purpose='Show a disruption of order',emotion='unease',
                                  audio_production_history='DO NOT COPY TTS LOGS')
        self.state['shots'][0].update(shot_contract={'shot_size':'wide','camera':'fixed'},
                                    continuity_state={'building':'same accepted facade'})
        call=self.w.run(self.state)['ready'][0]
        self.assertEqual(call['role'],'scene-design')
        self.assertEqual(call['scene_brief']['story_background'],'A maintained institution')
        self.assertEqual(call['scene_brief']['shot_contract']['shot_size'],'wide')
        self.assertNotIn('DO NOT COPY TTS LOGS',json.dumps(call))

    def test_existing_scene_without_new_design_stays_reusable(self):
        route=next(x for x in self.w.run(self.state)['routes']['S01'] if x['role']=='scene-design')
        self.assertEqual(route['decision'],'reuse')

    def test_default_style_is_photoreal_cinema(self):
        r=self.w.run(self.state)
        self.assertEqual(r['visual_styles']['S01']['id'],'photoreal-cinema')
        self.assertTrue(Path(r['visual_styles']['S01']['skill']).is_file())

    def test_styles_can_be_listed_without_a_production_task(self):
        r=self.w.run({'schema_version':'director-production/v3','request_type':'list_styles'})
        self.assertEqual(r['status'],'STYLE_CATALOG')
        self.assertEqual(len(r['style_catalog']['styles']),5)
        self.assertEqual(r['ready'],[])
        self.assertFalse(r['execution_authorized'])

    def test_grading_styles_list_without_video_or_production(self):
        r=self.w.run({'request_type':'list_grading_styles'})
        self.assertEqual(r['status'],'GRADING_STYLE_CATALOG')
        self.assertEqual(len(r['grading_style_catalog']['styles']),5)
        self.assertEqual(r['ready'],[])
        self.assertFalse(r['execution_authorized'])

    def test_grading_style_separate_from_scene_style_and_camera_input(self):
        self.state['brief'].update(needs_color=True,grading_style_id='ARRI',
                                  input_color_interpretation='unknown',protected_colors=['white product'],
                                  audio_production_history='SECRET TTS HISTORY')
        self.reach_execution();self.artifact('video')
        r=self.w.run(self.state);packet=r['ready'][0]
        self.assertEqual(packet['role'],'color-grading')
        self.assertEqual(packet['grading_style']['id'],'arri-inspired')
        self.assertEqual(packet['visual_style']['id'],'photoreal-cinema')
        self.assertEqual(packet['grading_brief']['input_color_interpretation'],'unknown')
        self.assertNotIn('SECRET TTS HISTORY',json.dumps(packet))
        self.assertNotIn('grade-eterna-inspired',json.dumps(packet))

    def test_grading_precedence_and_unknown_style(self):
        p={'grading_style_id':'ETERNA'};b={'grading_style_id':'ARRI'}
        s={'grading_style_id':'S-Cinetone'}
        self.assertEqual(self.c.resolve_grading_style(b,s,p)['id'],'s-cinetone-inspired')
        self.assertEqual(self.c.resolve_grading_style(b,{},p)['id'],'arri-inspired')
        self.assertEqual(self.c.resolve_grading_style({}, {}, p)['id'],'eterna-inspired')
        self.assertEqual(self.c.resolve_grading_style({}, {}, {})['id'],'neutral-match')
        with self.assertRaises(ValueError):self.c.resolve_grading_style({'grading_style_id':'not-a-look'}, {}, {})

    def test_grading_selection_does_not_release_post_before_video(self):
        self.state['brief'].update(needs_color=True,grading_style_id='ETERNA')
        self.reach_execution()
        self.assertEqual(self.w.run(self.state)['ready'],[])

    def test_grading_switch_keeps_static_but_invalidates_final(self):
        self.state['brief'].update(needs_color=True,grading_style_id='neutral-match')
        self.reach_execution();self.artifact('video');self.artifact('final');self.approve('final')
        self.state['brief']['grading_style_id']='cool-industrial'
        self.assertTrue(self.c.approved(self.state,'static_images'))
        self.assertFalse(self.c.approved(self.state,'final'))

    def test_grading_paths_and_content_fingerprints_exist(self):
        for s in self.c.grading_catalog()['styles']:
            resolved=self.c.resolve_grading_style({'grading_style_id':s['id']},{},{})
            self.assertTrue(Path(resolved['skill']).is_file())
            self.assertEqual(len(resolved['skill_fingerprint']),64)

    def test_style_precedence_and_chinese_alias(self):
        project={'style_id':'realistic-game'}
        brief={'style_id':'概念插画','art_direction':'industrial science fiction'}
        shot={'style_id':'二维动画','cinematography':'wide fixed view'}
        s=self.c.resolve_style(brief,shot,project)
        self.assertEqual(s['id'],'animation-2d');self.assertEqual(s['origin'],'shot')
        self.assertEqual(s['art_direction'],'industrial science fiction')
        self.assertEqual(self.c.resolve_style(brief,{},project)['id'],'concept-art')
        self.assertEqual(self.c.resolve_style({}, {},project)['id'],'realistic-game')

    def test_only_selected_style_is_in_context_and_story_is_preserved(self):
        self.state['brief'].update(needs_scene_design=True,style_id='concept-art',story_background='Original story')
        before=copy.deepcopy(self.state)
        call=self.w.run(self.state)['ready'][0]
        self.assertEqual(call['visual_style']['id'],'concept-art')
        self.assertNotIn('style-photoreal-cinema',json.dumps(call))
        self.assertEqual(call['scene_brief']['story_background'],'Original story')
        self.assertEqual(self.state,before)

    def test_sound_does_not_receive_visual_style_skill(self):
        self.state['brief']['audio_mode']='design'
        call=next(c for c in self.w.run(self.state)['ready'] if c['role']=='sound-design')
        self.assertNotIn('visual_style',call)

    def test_unknown_style_is_not_silently_replaced(self):
        self.state['brief']['style_id']='unknown-style'
        r=self.w.run(self.state)
        self.assertEqual(r['status'],'NEEDS_HUMAN_REVIEW');self.assertEqual(r['ready'],[])

    def test_style_switch_invalidates_review_without_touching_files(self):
        self.reach_execution()
        p=Path(self.state['artifacts']['static_images']['files'][0]['path']);old=p.read_bytes()
        self.state['brief'].update(style_id='concept-art',style_change=True)
        r=self.w.run(self.state)
        self.assertEqual(r['human_review']['checkpoint'],'static_images')
        self.assertEqual(p.read_bytes(),old)
        route=next(x for x in r['routes']['S01'] if x['role']=='scene-design')
        self.assertEqual(route['decision'],'call')

    def test_all_style_skill_paths_are_valid(self):
        for style in self.c.style_catalog()['styles']:
            self.assertTrue((ROOT/style['skill']).is_file())

    def test_color_only_uses_current_video_without_vfx_gate(self):
        self.state['brief']['needs_color']=True;self.reach_execution();self.artifact('video')
        self.assertEqual([x['role'] for x in self.w.run(self.state)['ready']],['color-grading'])

    def test_final_cannot_be_marked_not_applicable(self):
        self.reach_execution();self.state['artifacts']['final']={'not_applicable_reason':'skip'}
        self.assertEqual(self.w.run(self.state)['status'],'NEEDS_HUMAN_REVIEW')

    def test_missing_review_file_returns_to_human(self):
        self.state['artifacts']['static_images']={'files':[str(Path(self.tmp.name)/'missing.png')]}
        self.assertEqual(self.w.run(self.state)['status'],'NEEDS_HUMAN_REVIEW')

    def test_project_library_is_loaded_and_selected_assets_only(self):
        library=Path(self.tmp.name)/'assets.json'
        library.write_text(json.dumps({'entries':[
            {'id':'chosen','summary':'CHOSEN','roles':['node-design'],'topics':['assets'],'shot_ids':[]},
            {'id':'unselected','summary':'DO NOT PASS','roles':['node-design'],'topics':['assets'],'shot_ids':[]}]}),encoding='utf-8')
        project=Path(self.tmp.name)/'project.json';project.write_text(json.dumps({'libraries':{'assets':'assets.json'}}),encoding='utf-8')
        self.state['project_file']=str(project);self.state['brief']['asset_ids']=['chosen']
        self.state['shots'][0]['role_decisions']={role:{'decision':'skip','reason':'director provided this simple design'} for role in ['action-design','prompt-design']}
        self.reach_contract()
        call=next(x for x in self.w.run(self.state)['ready'] if x['role']=='node-design')
        self.assertIn('CHOSEN',json.dumps(call));self.assertNotIn('DO NOT PASS',json.dumps(call))


if __name__=='__main__':unittest.main()
