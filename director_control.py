"""Small offline helper for director-selected routes, context and human review packets."""
from pathlib import Path
import hashlib
import json
import importlib.util

ROOT = Path(__file__).parent
CHECKPOINTS = ('static_images', 'contract', 'final')
POST = ('vfx-design', 'color-grading')
STYLE_CATALOG = ROOT/'agents/scene-design/styles/catalog.json'
SOLUTION_CATALOG = ROOT/'方案库/catalog.json'
GRADING_CATALOG = ROOT/'agents/color-grading/styles/catalog.json'
MAX_GROUP_SECONDS = 15
UPSTREAM = {
    'scene-design':('shot-design',),
    'modeling-design':('shot-design','scene-design'),
    'action-design':('shot-design','scene-design','modeling-design'),
    'prompt-design':('shot-design','scene-design','modeling-design','action-design'),
    'node-design':('shot-design','action-design','prompt-design'),
}


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    allow_nan=False).encode('utf-8')).hexdigest()


def solution_decisions(brief, shots):
    spec = importlib.util.spec_from_file_location('director_solution_library', ROOT/'方案库/decide.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.plan_shots(brief, shots)


def load_project(project_file=None):
    if not project_file:
        return {'facts': [], 'memories': [], 'assets': []}
    p = Path(project_file)
    result = json.loads(p.read_text(encoding='utf-8'))
    for key in ('facts', 'memories', 'assets'):
        ref = result.get('libraries', {}).get(key)
        if ref:
            result[key] = json.loads((p.parent / ref).read_text(encoding='utf-8'))['entries']
        result.setdefault(key, [])
    return result


def style_catalog():
    return json.loads(STYLE_CATALOG.read_text(encoding='utf-8'))


def grading_catalog():
    return json.loads(GRADING_CATALOG.read_text(encoding='utf-8'))


def resolve_grading_style(brief, shot, project):
    catalog=grading_catalog();choice=catalog['default_style_id'];origin='default'
    for label,source in (('shot',shot),('brief',brief),('project',project)):
        if source.get('grading_style_id') is not None:
            choice=source['grading_style_id'];origin=label;break
    if not isinstance(choice,str):raise ValueError('grading_style_id must be a registered ID or name')
    match=next((s for s in catalog['styles'] if choice.strip().casefold() in
                [v.casefold() for v in [s['id'],s['name']]+s.get('aliases',[])]),None)
    if match is None:raise ValueError('Unknown grading style; choose from the grading catalog: '+choice)
    skill=(ROOT/match['skill']).resolve()
    if not skill.is_relative_to(ROOT.resolve()) or not skill.is_file():
        raise ValueError('Registered grading Skill missing or outside director package')
    return {'id':match['id'],'name':match['name'],'version':match['version'],
            'skill':str(skill),'skill_fingerprint':hashlib.sha256(skill.read_bytes()).hexdigest(),
            'origin':origin,'kind':match['kind'],
            'scope':'post-production look only; does not set input color space or authorize processing'}


def resolve_style(brief, shot, project):
    catalog=style_catalog();choice=catalog['default_style_id'];origin='default'
    for label, source in (('shot',shot),('brief',brief),('project',project)):
        if source.get('style_id') is not None:
            choice=source['style_id'];origin=label;break
    if not isinstance(choice,str):raise ValueError('style_id must be a style ID or registered name')
    match=next((s for s in catalog['styles'] if choice.strip().casefold() in
                [v.casefold() for v in [s['id'],s['name']]+s.get('aliases',[])]),None)
    if match is None:
        raise ValueError('Unknown visual style; choose from the style catalog or ask to add one: '+choice)
    skill=(ROOT/match['skill']).resolve()
    if not skill.is_relative_to(ROOT.resolve()) or not skill.is_file():
        raise ValueError('Registered style Skill missing or outside director package')
    result={'id':match['id'],'name':match['name'],'version':match['version'],
            'skill':str(skill),'origin':origin,'scope':'presentation_only; preserve accepted story and assets'}
    for key in ('art_direction','cinematography'):
        value=shot.get(key,brief.get(key,project.get(key)))
        if value is not None:result[key]=value
    return result


def select_roles(brief, shot, count=1):
    """Suggested route from explicit director facts, with reasoned director overrides."""
    b = {**brief, **shot}
    render = b.get('render_mode', 'generate')
    # A photo pan alone cannot supply a requested independent subject action.
    if render == 'local_pan' and b.get('subject_motion') not in ('none', None):
        render = 'generate'
    flags = {
        'shot-design': b.get('needs_storyboard', count > 1),
        'sound-design': b.get('audio_mode') == 'design',
        'scene-design': (b.get('visual_source') == 'create' or b.get('scene_change', False)
                         or b.get('needs_scene_design', False)
                         or b.get('style_change', False)
                         or b.get('scene_task') in ('narrative_design','spatial_layout','continuity_check','reference_study')),
        'modeling-design': b.get('needs_modeling', False),
        'action-design': b.get('needs_action_design', False) or b.get('subject_motion', 'none') != 'none' or b.get('camera_motion', 'none') != 'none',
        'prompt-design': render not in ('local_pan', 'local_edit'),
        'node-design': not b.get('reuse_verified_workflow', False),
        'vfx-design': b.get('needs_vfx', False),
        'color-grading': b.get('needs_color', False),
    }
    routes=[]
    registry=json.loads((ROOT/'workflow_manifest.json').read_text(encoding='utf-8'))['roles']
    overrides=b.get('role_decisions', {})
    if set(overrides)-set(flags):
        raise ValueError('unknown role in director decisions')
    for role, selected in flags.items():
        decision='call' if selected else 'skip'
        if role=='scene-design' and b.get('visual_source')=='provided' and not selected:decision='reuse'
        if role=='sound-design' and b.get('audio_mode')=='provided' and not selected:decision='reuse'
        if role=='node-design' and not selected:decision='reuse'
        reason=registry[role]['call_when' if selected else 'skip_when']
        if role in overrides:
            decision=overrides[role]['decision'];reason=overrides[role]['reason']
            if decision not in ('call','reuse','skip') or not str(reason).strip():
                raise ValueError('director override requires call/reuse/skip and a reason')
        routes.append({'role':role,'decision':decision,'reason':reason,'render_mode':render})
    return routes


def _files(artifact):
    return [x['path'] if isinstance(x,dict) else x for x in artifact.get('files',[])]


def review_fingerprint(state, checkpoint):
    artifacts=state.get('artifacts',{})
    # Scope approval to material impacts. Audio does not invalidate unchanged static pictures.
    shared={'artifact':artifacts.get(checkpoint),
            'basis':state.get('review_basis',{}).get(checkpoint)}
    shared['file_versions']=[{'path':p,'size':Path(p).stat().st_size,'mtime_ns':Path(p).stat().st_mtime_ns}
                             for p in _files(artifacts.get(checkpoint,{})) if Path(p).is_file()]
    if checkpoint=='static_images':
        project=load_project(state.get('project_file'));brief=state.get('brief',{})
        shared['visual_styles']=[{k:v for k,v in resolve_style(brief,s,project).items()
                                  if k in ('id','version','art_direction','cinematography')}
                                 for s in (state.get('shots') or [{}])]
    if checkpoint in ('contract','final'):
        shared['solution_catalog_fingerprint']=digest(json.loads(SOLUTION_CATALOG.read_text(encoding='utf-8')))
        shared.update(brief=state.get('brief'),shots=state.get('shots'),
                      static_images=review_fingerprint(state,'static_images'))
    if checkpoint=='final':
        shared.update(contract=artifacts.get('contract'),video=artifacts.get('video'),
                      vfx=artifacts.get('vfx_video'))
        brief=state.get('brief',{});shots=state.get('shots') or [{}]
        if any(s.get('needs_color',brief.get('needs_color',False)) for s in shots):
            project=load_project(state.get('project_file'))
            shared['grading_styles']=[resolve_grading_style(brief,s,project) for s in shots
                                      if s.get('needs_color',brief.get('needs_color',False))]
    return digest(shared)


def review_packet(state, checkpoint):
    artifact=state.get('artifacts',{}).get(checkpoint)
    if not artifact:return None
    paths=_files(artifact)
    if checkpoint!='static_images' and not paths:
        raise ValueError(checkpoint+': actual contract/final files are required')
    if not paths and not artifact.get('not_applicable_reason'):
        raise ValueError(checkpoint+': return actual files or explain non-applicability for human review')
    missing=[p for p in paths if not Path(p).is_file()]
    if missing:raise ValueError('review files missing: '+', '.join(missing))
    return {'checkpoint':checkpoint,'files':paths,'summary':artifact.get('summary',''),
            'fingerprint':review_fingerprint(state,checkpoint),
            'not_applicable_reason':artifact.get('not_applicable_reason'),
            'ask':'请查看本轮产物，确认通过或指出需要修改的部分。'}


def approved(state, checkpoint):
    review=state.get('reviews',{}).get(checkpoint,{})
    return (review.get('decision')=='approved' and bool(review.get('reviewer'))
            and review.get('fingerprint')==review_fingerprint(state,checkpoint))


def context_packet(state, project, shot, route, registry, budget=6000):
    role=route['role'];sid=shot['shot_id'];entry=registry[role]
    if role in ('shot-design','sound-design','modeling-design','action-design','prompt-design','node-design','vfx-design','color-grading'):
        eligible,reason=contract_eligible(state,'shot',sid)
        if not eligible and role in ('action-design','prompt-design','node-design','vfx-design','color-grading'):
            raise ValueError('shot contract not eligible for downstream context: '+sid+' ('+reason+')')
    budget=max(1500, min(int(budget),12000))
    packet={'call_id':sid+'/'+role,'shot_id':sid,'role':role,
            'agent':str(ROOT/entry['entrypoint']),'skill':str(ROOT/entry['skill']),
            'goal':state['brief'].get('goal',state['brief'].get('request','')),
            'shot':shot.get('summary',''),'constraints':shot.get('constraints',state['brief'].get('constraints',[])),
            'task':entry['deliverable'],'reason':route['reason'],'render_mode':route['render_mode'],
            'context':[],'omitted_refs':[],'problem_policy':'遇到问题返回总控并等待人工决定，不自行重试'}
    if role not in ('sound-design','modeling-design'):
        packet['visual_style']=resolve_style(state['brief'],shot,project)
    if role=='modeling-design':
        modeling_input={**state['brief'],**state['brief'].get('modeling_brief',{}),
                        **shot,**shot.get('modeling_brief',{})}
        modeling_keys=('prompt','reference_images','known_dimensions','scale_policy',
                       'object_category','preserve','assumptions','output_root','mode',
                       'modeling_contract_ref','input_versions','review_views')
        packet['modeling_brief']={k:modeling_input[k] for k in modeling_keys if k in modeling_input}
        packet['presentation_scope']='white_blockout; look development is not implicit'
        refs=modeling_input.get('reference_images',[])
        if not isinstance(refs,list):raise ValueError('reference_images must be a list')
        file_refs=list(refs)
        if modeling_input.get('modeling_contract_ref'):
            file_refs.append(modeling_input['modeling_contract_ref'])
        packet['modeling_input_files']=[]
        for ref in file_refs:
            path=ref.get('path') if isinstance(ref,dict) else ref
            if path is None:continue  # An attachment may be provided by the host, without a path.
            if not isinstance(path,str):raise ValueError('modeling reference path must be a string')
            source=Path(path)
            if not source.is_file():raise ValueError('modeling reference file missing: '+path)
            hasher=hashlib.sha256()
            with source.open('rb') as stream:
                for block in iter(lambda:stream.read(1024*1024),b''):hasher.update(block)
            packet['modeling_input_files'].append({'path':path,'sha256':hasher.hexdigest()})
    if role=='scene-design':
        scene_input={**state['brief'],**shot}
        scene_keys=('story_background','narrative_purpose','emotion','world_rules',
                    'shot_contract','continuity_state','visible_clues','scene_questions')
        packet['scene_brief']={k:scene_input[k] for k in scene_keys if k in scene_input}
    if role=='action-design':
        action_input={**state['brief'],**shot}
        action_keys=('static_image_ref','static_image_version','subject_audit_ref',
                     'narrative_purpose','story_background','emotion','world_rules',
                     'duration_seconds','shot_contract','continuity_state','sync_cues')
        packet['action_brief']={k:action_input[k] for k in action_keys if k in action_input}
    if role=='color-grading':
        grading_input={**state['brief'],**shot}
        packet['grading_style']=resolve_grading_style(state['brief'],shot,project)
        grading_keys=('media_probe_ref','input_color_interpretation','color_pipeline',
                      'output_color_target','viewing_conditions','grade_reference_ref',
                      'match_reference_shot_id','protected_colors','look_intent','existing_transforms')
        packet['grading_brief']={k:grading_input[k] for k in grading_keys if k in grading_input}
    if role in ('node-design','prompt-design') and sid in state.get('_solution_decisions',{}):
        decision=state['_solution_decisions'][sid]
        packet['solution_decision']={k:decision[k] for k in
            ('status','recipe_id','mode','decision_fingerprint','reason','questions','service_candidates','strategy_ref') if k in decision}
    if len(json.dumps(packet,ensure_ascii=False))>budget:
        raise ValueError(sid+': core context too long; director must summarize/split it without dropping constraints')
    allowed=set(entry['context_topics']);selected=set(shot.get('asset_ids',state['brief'].get('asset_ids',[])))
    records=[]
    for upstream_role in UPSTREAM.get(role,()):
        completed=state.get('completed_calls',{}).get(sid+'/'+upstream_role,{})
        if completed.get('status')=='completed':
            if not completed.get('output_summary') and not completed.get('outputs'):
                raise ValueError(sid+'/'+upstream_role+': completed but deliverable missing; director must recover it, not rerun automatically')
            records.append({'id':sid+'/'+upstream_role,'summary':completed.get('output_summary',''),
                            'source':completed.get('outputs',[]),'status':'upstream_completed'})
    for kind in ('facts','memories','assets'):
        for item in project.get(kind,[])+state.get(kind,[]):
            if role not in item.get('roles',[]):continue
            if item.get('shot_ids') and sid not in item['shot_ids']:continue
            if not allowed.intersection(item.get('topics',[])):continue
            if kind=='assets' and item.get('id') not in selected:continue
            records.append({k:item[k] for k in ('id','summary','source','path','status','topics','verified_at') if k in item})
    # Pass only this shot's current rendered video, never all other roles' artifacts.
    source_key=route.get('video_source','video')
    if role in POST:
        found=False
        for item in state.get('artifacts',{}).get(source_key,{}).get('files',[]):
            if isinstance(item,dict):
                if sid not in item.get('shot_ids',[]):continue
                item_path=item['path']
            elif len(state.get('shots',[]))==1:item_path=item
            else:continue
            found=True
            records.insert(0,{'id':source_key+':'+sid,'path':item_path,'status':'current_video'})
        if not found:raise ValueError(sid+': no shot-scoped video input; ask director to map the actual clip')
    for item in records:
        candidate={**packet,'context':packet['context']+[item]}
        if len(json.dumps(candidate,ensure_ascii=False))<=budget-500:
            packet['context'].append(item)
        else:
            # A bounded index only; do not defeat the budget with thousands of omitted paths.
            if len(packet['omitted_refs'])<3:packet['omitted_refs'].append(str(item.get('id','unnamed'))[:80])
    packet['input_fingerprint']=digest(packet)
    packet['context_chars']=len(json.dumps(packet,ensure_ascii=False))
    if packet['context_chars']>budget:raise ValueError(sid+': context requires a smaller director summary')
    return packet


def plan_modeling(state, project, result):
    """Standalone modeling context only: no video recipes, renderers or scene mutation."""
    registry=json.loads((ROOT/'workflow_manifest.json').read_text(encoding='utf-8'))['roles']
    brief=state['brief']
    units=state.get('shots') or [{'shot_id':'M01','summary':brief.get('goal',brief['request'])}]
    ids=[unit['shot_id'] for unit in units]
    if len(ids)!=len(set(ids)):raise ValueError('duplicate modeling unit ID')
    result={**result,'fixed_human_checkpoints':[],'ready':[],
            'request_type':'modeling','routes':{}}
    for unit in units:
        route={'role':'modeling-design','decision':'call',
               'reason':registry['modeling-design']['call_when'],'render_mode':'blender_blockout'}
        result['routes'][unit['shot_id']]=[route]
        packet=context_packet(state,project,unit,route,registry,state.get('context_budget_chars',6000))
        previous=state.get('completed_calls',{}).get(packet['call_id'],{})
        if previous.get('status')=='completed' and previous.get('input_fingerprint')==packet['input_fingerprint']:
            if not isinstance(previous.get('outputs'),list) or not previous['outputs']:
                raise ValueError(packet['call_id']+': completed modeling call requires actual output references')
            for item in previous['outputs']:
                path=item.get('path') if isinstance(item,dict) else item
                if not isinstance(path,str) or not Path(path).is_file():
                    raise ValueError(packet['call_id']+': actual modeling output missing; recover it before claiming completion')
            continue
        result['ready'].append(packet)
    result['status']='MODELING_TASKS_READY' if result['ready'] else 'MODELING_REVIEW_NEEDED'
    result['next_action']='按当前授权制作/检查白模，返回真实工程、多视图与限制；本程序未执行建模或代填认可。'
    return result


def shot_contract_fingerprint(state, shot):
    """用 digest() 对镜头关键字段计算内容指纹，用于合同审批一致性校验。"""
    keys = ('shot_id', 'summary', 'duration_seconds', 'static_frames',
            'video_prompt', 'final_prompt', 'dialogue', 'sound_effects',
            'video_node', 'video_mode')
    return digest({k: shot.get(k) for k in keys})


def contract_state(state, scope, target_id):
    """返回 state['contracts'] 中 scope 与 target_id 匹配的最新合同（revision 最大），无则 None。"""
    if scope not in ('shot', 'group', 'film'):
        raise ValueError('unknown contract scope: ' + str(scope))
    contracts = state.get('contracts') or []
    matches = [c for c in contracts
               if c.get('scope') == scope and c.get('target_id') == target_id]
    if not matches:
        return None
    return max(matches, key=lambda c: c.get('revision', 0))


def contract_eligible(state, scope, target_id):
    """返回 (bool, reason)，判断指定合同是否允许进入执行阶段。"""
    record = contract_state(state, scope, target_id)
    if record is None:
        return (True, 'no contract recorded')
    decision = record.get('decision')
    if decision == 'pending':
        return (False, 'contract pending')
    if decision == 'rejected':
        return (False, 'contract rejected')
    if decision != 'approved':
        return (False, 'unknown decision: ' + str(decision))
    # 已 approved，核对内容指纹
    stored_fp = record.get('fingerprint')
    if scope == 'shot':
        shots = state.get('shots') or []
        shot = next((s for s in shots if s.get('shot_id') == target_id), None)
        current_fp = shot_contract_fingerprint(state, shot) if shot is not None else None
    else:
        # group / film：从 state 的 contract_fingerprint 字典取当前指纹
        current_fp = state.get('contract_fingerprint', {}).get(scope + ':' + target_id)
        if current_fp is None:
            # 取不到视作相符，不判定过期
            return (True, 'approved')
    if current_fp != stored_fp:
        return (False, 'approval stale')
    return (True, 'approved')


def consistency(state, project):
    """检查当前状态的一致性，返回问题列表，每项包含 code/target/detail。"""
    issues = []
    shots = state.get('shots') or []
    groups = {}
    for _unit in (state.get('units') or []):
        for g in (_unit.get('groups') or []):
            gid = g.get('group_id')
            if gid:
                groups[gid] = g
    for g in (state.get('groups') or []):
        gid = g.get('group_id')
        if gid and gid not in groups:
            groups[gid] = g

    # 资产相关检查（project 为 None 时跳过）
    if project is not None:
        # 构建项目资产索引：id -> sha256
        project_assets = {}
        for a in (project.get('assets') or []):
            aid = a.get('id') or a.get('asset_id')
            if aid:
                project_assets[aid] = a.get('sha256') or a.get('fingerprint')

        # asset-missing：镜头 asset_ids 或 assets 里引用的 id 在项目资产库找不到
        for shot in shots:
            sid = shot.get('shot_id', '')
            for aid in (shot.get('asset_ids') or []):
                if aid not in project_assets:
                    issues.append({'code': 'asset-missing', 'target': sid,
                                   'detail': 'asset_id not in project: ' + str(aid)})
            for a in (shot.get('assets') or []):
                aid = a.get('id') or a.get('asset_id')
                if aid and aid not in project_assets:
                    issues.append({'code': 'asset-missing', 'target': sid,
                                   'detail': 'asset_id not in project: ' + str(aid)})

        # asset-drift：同 asset_id 在不同镜头 sha256 不一致
        asset_shot_fp = {}  # aid -> (first_sha256, first_shot_id)
        for shot in shots:
            sid = shot.get('shot_id', '')
            all_assets = list(shot.get('assets') or [])
            for aid in (shot.get('asset_ids') or []):
                all_assets.append({'id': aid})
            for a in all_assets:
                aid = a.get('id') or a.get('asset_id')
                sha = a.get('sha256') or a.get('fingerprint') or project_assets.get(aid)
                if not aid or sha is None:
                    continue
                if aid in asset_shot_fp:
                    prev_sha, prev_sid = asset_shot_fp[aid]
                    if prev_sha != sha:
                        issues.append({'code': 'asset-drift', 'target': aid,
                                       'detail': 'sha256 differs between shot ' + prev_sid + ' and ' + sid})
                else:
                    asset_shot_fp[aid] = (sha, sid)

    # group-missing：镜头 group_id 指向不存在的组
    for shot in shots:
        gid = shot.get('group_id')
        if gid and gid not in groups:
            issues.append({'code': 'group-missing', 'target': shot.get('shot_id', ''),
                           'detail': 'group_id not found: ' + str(gid)})

    # group-too-long / group-duration-mismatch：组内镜头时长之和的硬上限与账目核查
    group_shots = {}
    for shot in shots:
        gid = shot.get('group_id')
        if gid:
            group_shots.setdefault(gid, []).append(shot)

    for gid, gshots in group_shots.items():
        group = groups.get(gid)
        if group is None:
            continue
        total = sum(s.get('duration_seconds') or 0 for s in gshots)
        if total > MAX_GROUP_SECONDS:
            issues.append({'code': 'group-too-long', 'target': gid,
                           'detail': 'group total ' + str(total) + 's exceeds hard limit 15s'})
        else:
            target = group.get('target_seconds')
            if target and abs(total - target) / target > 0.2:
                issues.append({'code': 'group-duration-mismatch', 'target': gid,
                               'detail': 'declared target ' + str(target) + 's vs shots total ' + str(total) + 's'})

    # approval-stale：已 approved 合同的内容指纹不再匹配
    for c in (state.get('contracts') or []):
        if c.get('decision') == 'approved':
            scope = c.get('scope')
            tid = c.get('target_id', '')
            if scope in ('shot', 'group', 'film'):
                _, reason = contract_eligible(state, scope, tid)
                if reason == 'approval stale':
                    issues.append({'code': 'approval-stale', 'target': tid,
                                   'detail': 'contract fingerprint does not match current content'})

    # dialogue-unmeasured：dialogue 里 source 不是 measured 或 estimated
    for shot in shots:
        for line in (shot.get('dialogue') or []):
            src = line.get('source')
            if src not in ('measured', 'estimated'):
                issues.append({'code': 'dialogue-unmeasured',
                               'target': shot.get('shot_id', ''),
                               'detail': 'dialogue line source=' + repr(src)})

    return issues


def plan(state):
    """No model calls or mutations. Human approval records are not payment credentials."""
    result={'workflow_version':'3.0.0','execution_authorized':False,'automatic_retry':False,
            'fixed_human_checkpoints':list(CHECKPOINTS),'ready':[],'blocked_shots':[],
            'contracts':{'shot':{},'group':{},'film':{}},'consistency':[],
            'claim_boundary':'Offline route/context suggestions only; no model, rendering or payment executed.'}
    try:
        if state.get('request_type')=='list_styles':
            return {**result,'status':'STYLE_CATALOG','style_catalog':style_catalog()}
        if state.get('request_type')=='list_grading_styles':
            return {**result,'status':'GRADING_STYLE_CATALOG','grading_style_catalog':grading_catalog()}
        brief=state.get('brief',{})
        if not brief.get('request'):
            return {**result,'status':'NEEDS_CLARIFICATION','questions':['这次想做什么画面，已有图片、音频或视频有哪些？']}
        issues=[i for i in state.get('issues',[]) if i.get('status')!='resolved']
        if issues:return {**result,'status':'NEEDS_HUMAN_REVIEW','issues':issues,'next_action':'展示问题证据与建议，等待用户决定；不自动重试'}
        questions=[q for q in state.get('open_questions',[]) if q.get('blocking') and not q.get('answer')]
        standalone_modeling=state.get('request_type')=='modeling'
        if not standalone_modeling and brief.get('subject_motion')=='unknown' and not brief.get('needs_action_design',False):
            questions.append({'question':'画面中的人物/物体要独立运动，还是保持静止、只移动镜头？','blocking':True})
        if questions:return {**result,'status':'NEEDS_CLARIFICATION','questions':questions[:3]}
        project=load_project(state.get('project_file'))
        if standalone_modeling:
            return plan_modeling(state,project,result)
        shots=state.get('shots') or [{'shot_id':'S01','summary':brief.get('goal',brief['request'])}]
        state={**state,'shots':shots}
        ids=[s['shot_id'] for s in shots]
        if len(set(ids))!=len(ids):raise ValueError('duplicate shot_id')
        decisions=solution_decisions(brief,shots)
        result['solution_decisions']=decisions
        state={**state,'_solution_decisions':decisions}
        registry=json.loads((ROOT/'workflow_manifest.json').read_text(encoding='utf-8'))['roles']
        route_map={}
        for s in shots:
            decision=decisions[s['shot_id']]
            route_shot=s
            if decision['status']=='SELECTED':
                mode=decision['mode']
                route_shot={**s,'render_mode':mode if mode in ('local_pan','local_edit') else 'generate'}
            route_map[s['shot_id']]=select_roles(brief,route_shot,len(shots))
        result['routes']=route_map
        result['visual_styles']={s['shot_id']:resolve_style(brief,s,project) for s in shots}
        result['context_libraries']=state.get('project_file')
        for scope in ('shot','group','film'):
            for item in state.get('contracts',[]):
                if item.get('scope')!=scope:continue
                tid=item.get('target_id')
                if tid is None:continue
                previous=result['contracts'][scope].get(tid)
                if previous is None or item.get('revision',0)>previous.get('revision',0):
                    result['contracts'][scope][tid]=item
        result['consistency']=consistency(state,project)
        phase=None
        for cp in CHECKPOINTS:
            packet=review_packet(state,cp)
            if packet and not approved(state,cp):
                return {**result,'status':'WAITING_HUMAN_REVIEW','human_review':packet}
            if not packet:
                phase=cp;break
        if phase is None:return {**result,'status':'COMPLETE','files':_files(state['artifacts']['final'])}
        phase_roles={'static_images':('shot-design','scene-design','modeling-design','sound-design'),
                     'contract':('shot-design','sound-design','modeling-design','action-design','prompt-design','node-design'),
                     'final':POST}[phase]
        artifacts=state.get('artifacts',{})
        # Existing rendered media may proceed to post/review. New generation cannot
        # treat an unresolved recipe as an executable plan, even after contract review.
        unresolved=[{'shot_id':sid,**d} for sid,d in decisions.items() if d['status']!='SELECTED']
        if phase=='final' and not _files(artifacts.get('video',{})) and unresolved:
            return {**result,'status':'NEEDS_SOLUTION_DECISION','solution_gaps':unresolved,
                    'next_action':'按方案库补齐关键事实或由总控确定新方案；不得提交生成任务。'}
        for shot in shots:
            sid=shot['shot_id']
            pending=False
            for route in route_map[sid]:
                role=route['role']
                if route['decision']!='call' or role not in phase_roles:continue
                if phase in ('contract','final'):
                    ok,why=contract_eligible(state,'shot',sid)
                    if not ok:
                        if not any(b['shot_id']==sid for b in result['blocked_shots']):
                            result['blocked_shots'].append({'shot_id':sid,'reason':why})
                        continue
                # Sound may be designed alongside shots; other selected tasks follow their
                # necessary predecessor. Skipped roles never create mandatory empty stages.
                if pending and role!='sound-design':continue
                if role in POST:
                    video=artifacts.get('video')
                    if not video or not _files(video):continue
                    if any(not Path(p).is_file() for p in _files(video)):raise ValueError('actual video missing; ask user before post-production')
                    has_vfx=any(r['role']=='vfx-design' and r['decision']=='call' for r in route_map[shot['shot_id']])
                    if role=='color-grading' and has_vfx and not artifacts.get('vfx_video'):continue
                    if role=='color-grading' and has_vfx and (not _files(artifacts['vfx_video']) or any(not Path(p).is_file() for p in _files(artifacts['vfx_video']))):
                        raise ValueError('VFX result missing; grading waits for actual output')
                    route={**route,'video_source':'vfx_video' if role=='color-grading' and has_vfx else 'video'}
                packet=context_packet(state,project,shot,route,registry,state.get('context_budget_chars',6000))
                previous=state.get('completed_calls',{}).get(packet['call_id'],{})
                if previous.get('input_fingerprint')==packet['input_fingerprint'] and previous.get('status')=='completed':continue
                result['ready'].append(packet)
                pending=True
        result['status']='DESIGN_TASKS_READY' if result['ready'] else 'DIRECTOR_OUTPUT_NEEDED'
        result['next_action']={'static_images':'返回现有或新制作的静态图/代表帧，请用户审核，不强制重生图',
                               'contract':'总控汇总简明合同，请用户审核；不要求每个角色单独人审',
                               'final':'按具体授权执行所选方案，返回结果供用户审核；没有授权则等待，不提交任务'}[phase]
        if result['blocked_shots'] or any(i.get('code') in ('approval-stale', 'group-too-long') for i in result['consistency']):
            blocked_summary=', '.join(b['shot_id']+': '+b['reason'] for b in result['blocked_shots'])
            result['status']='WAITING_HUMAN_REVIEW'
            result['review']={'checkpoint':'contract',
                              'summary':'以下镜头合同未通过或已过期，不进上下文：'+blocked_summary,
                              'ask':'请查看合同版本，确认通过或指出需要修改的部分。'}
        return result
    except (ValueError,TypeError,KeyError,AttributeError,OSError) as exc:
        return {**result,'status':'NEEDS_HUMAN_REVIEW','problem':str(exc),
                'next_action':'总控解释缺口并请求人工决定，不循环自动补齐'}


if __name__=='__main__':
    import sys
    json.dump(plan(json.load(sys.stdin)),sys.stdout,ensure_ascii=False,indent=2)
