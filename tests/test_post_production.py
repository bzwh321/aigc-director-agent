import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from test_agent import ROOT, load_workflow


class PostProductionTests(unittest.TestCase):
    def setUp(self):
        self.w=load_workflow()
        self.state=json.loads((ROOT/'examples/production_state.json').read_text(encoding='utf-8'))
        self.spec=json.loads((ROOT/'workflow_manifest.json').read_text(encoding='utf-8'))
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.clips=[]
        for row in self.state['artifacts']['timing_lock']['data']['timeline']:
            path=Path(self.tmp.name)/(row['shot_id']+'.mp4')
            # Fixture tests file identity only, deliberately not a claimed playable video.
            content=b'identity fixture '+row['shot_id'].encode()
            path.write_bytes(content)
            self.clips.append(dict(shot_id=row['shot_id'],path=str(path),sha256=hashlib.sha256(content).hexdigest(),
                                   duration_seconds=row['end']-row['start'],fps=24,width=1280,height=720))

    def put(self,key,data):
        s=next(s for s in self.spec['post_stages'] if s['id']==key)
        a=self.state['artifacts']
        a[key]=dict(revision=1,status='accepted',owner=s['owner'],approved_by='test-director',
                    inputs={d:a[d]['revision'] for d in s['depends_on']},
                    input_hashes={d:self.w.fingerprint(a[d]['data']) for d in s['depends_on']},data=data)

    def delivery(self):
        return dict(clips=copy.deepcopy(self.clips),human_review=dict(passed=True,reviewed_by='test-reviewer'),
                    media_probe='Synthetic registered metadata for unit testing only')

    def video(self):self.put('video_delivery',dict(self.delivery(),generation_completed=True))

    def design(self,key,mode='bypass'):
        shots=[dict(shot_id=c['shot_id'],plan='No effect requested',acceptance='Preserve source',
                    intervals=[] if mode=='bypass' else [dict(start=0,end=c['duration_seconds'])]) for c in self.clips]
        data=dict(treatment=mode,reason='Explicit test decision',shots=shots)
        if key=='color_grading':data['color_pipeline']='Preserve registered source color; test only'
        self.put(key,data)

    def vfx(self):
        self.video();self.design('vfx_design');self.put('vfx_delivery',self.delivery())

    def full(self):
        self.vfx();self.design('color_grading');self.put('post_delivery',self.delivery())

    def test_design_ready_does_not_release_post_agents(self):
        r=self.w.run(self.state)
        self.assertEqual(r['status'],'DESIGN_READY')
        self.assertEqual(r['post_status'],'AWAITING_VIDEO')
        self.assertEqual([s['stage'] for s in r['ready']],['video_delivery'])

    def test_generated_and_reviewed_video_releases_only_vfx(self):
        self.video();r=self.w.run(self.state)
        self.assertEqual([s['owner'] for s in r['ready']],['vfx-design'])
        self.assertEqual(r['stages']['color_grading']['state'],'waiting')

    def test_unfinished_video_blocks_post(self):
        self.video();self.state['artifacts']['video_delivery']['data']['generation_completed']=False
        self.assertEqual(self.w.run(self.state)['stages']['vfx_design']['state'],'waiting')

    def test_unreviewed_video_blocks_post(self):
        self.video();self.state['artifacts']['video_delivery']['data']['human_review']['passed']=False
        self.assertEqual(self.w.run(self.state)['stages']['video_delivery']['state'],'invalid')

    def test_vfx_plan_is_not_vfx_delivery(self):
        self.video();self.design('vfx_design')
        self.assertEqual([s['stage'] for s in self.w.run(self.state)['ready']],['vfx_delivery'])

    def test_explicit_bypass_delivery_releases_grading(self):
        self.vfx()
        self.assertEqual([s['owner'] for s in self.w.run(self.state)['ready']],['color-grading'])

    def test_full_post_still_never_authorizes_execution(self):
        self.full();r=self.w.run(self.state)
        self.assertEqual(r['post_status'],'POST_READY_FOR_HANDOFF')
        self.assertFalse(r['execution_authorized'])
        self.assertTrue(r['example_only'])

    def test_changed_video_invalidates_all_post(self):
        self.full();self.state['artifacts']['video_delivery']['revision']=2
        r=self.w.run(self.state)
        self.assertEqual(r['stages']['vfx_design']['state'],'invalid')
        self.assertEqual(r['stages']['post_delivery']['state'],'stale')

    def test_changed_vfx_invalidates_color_without_version_bump(self):
        self.full();self.state['artifacts']['vfx_delivery']['data']['media_probe']='New report'
        self.assertEqual(self.w.run(self.state)['stages']['color_grading']['state'],'invalid')

    def test_hash_and_missing_file_checks(self):
        self.video();data=self.state['artifacts']['video_delivery']['data']
        self.assertEqual(self.w._post_errors('video_delivery',data,self.state['artifacts'],False),[])
        Path(data['clips'][0]['path']).write_bytes(b'changed')
        self.assertTrue(any('hash mismatch' in e for e in self.w._post_errors('video_delivery',data,self.state['artifacts'],False)))
        data['clips'][0]['path']=str(Path(self.tmp.name)/'missing.mp4')
        self.assertTrue(any('missing' in e for e in self.w._post_errors('video_delivery',data,self.state['artifacts'],False)))

    def test_interval_beyond_actual_duration_rejected(self):
        self.video();self.design('vfx_design','apply')
        self.state['artifacts']['vfx_design']['data']['shots'][0]['intervals'][0]['end']=999
        self.assertEqual(self.w.run(self.state)['stages']['vfx_design']['state'],'invalid')

    def test_bypass_cannot_hide_processing(self):
        self.vfx();self.state['artifacts']['vfx_delivery']['data']['clips'][0]['sha256']='f'*64
        self.assertEqual(self.w.run(self.state)['stages']['vfx_delivery']['state'],'invalid')

    def test_processing_cannot_overwrite_source(self):
        self.video();self.design('vfx_design','apply');self.put('vfx_delivery',self.delivery())
        self.assertTrue(any('overwrite' in e for e in self.w.run(self.state)['stages']['vfx_delivery']['errors']))

    def test_post_cannot_retime_video(self):
        self.vfx();self.state['artifacts']['vfx_delivery']['data']['clips'][0]['duration_seconds']+=1
        self.assertEqual(self.w.run(self.state)['stages']['vfx_delivery']['state'],'invalid')

    def test_registry_entries_exist(self):
        for role in ('vfx-design','color-grading'):
            for key in ('entrypoint','skill'):
                self.assertTrue((ROOT/self.spec['roles'][role][key]).is_file())

    def test_apply_handoffs_accept_new_files_without_mutating_originals(self):
        self.video();self.design('vfx_design','apply')
        for design_key,delivery_key in [('vfx_design','vfx_delivery'),('color_grading','post_delivery')]:
            if design_key=='color_grading':self.design(design_key,'apply')
            data=self.delivery()
            for clip in data['clips']:
                p=Path(self.tmp.name)/(delivery_key+'-'+clip['shot_id']+'.mp4')
                content=(delivery_key+clip['shot_id']).encode()
                p.write_bytes(content);clip.update(path=str(p),sha256=hashlib.sha256(content).hexdigest())
            self.put(delivery_key,data)
            self.assertEqual(self.w._post_errors(delivery_key,data,self.state['artifacts'],False),[])
        self.assertEqual(self.w.run(self.state)['post_status'],'POST_READY_FOR_HANDOFF')
        for c in self.clips:
            self.assertEqual(hashlib.sha256(Path(c['path']).read_bytes()).hexdigest(),c['sha256'])

    def test_prepopulated_post_artifact_cannot_bypass_video_gate(self):
        self.full();del self.state['artifacts']['video_delivery']
        r=self.w.run(self.state)
        self.assertEqual(r['stages']['vfx_design']['state'],'stale')
        self.assertEqual(r['stages']['color_grading']['state'],'stale')
        self.assertEqual([s['stage'] for s in r['ready']],['video_delivery'])


if __name__=='__main__':unittest.main()
