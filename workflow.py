"""Deterministic gatekeeper for the AIGC Director agent."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any
import hashlib
import json
from pathlib import Path
import math


WORKFLOW_VERSION = "3.0.0"
LAST_VALIDATED = "2026-10-11"


@dataclass(frozen=True)
class Gate:
    gate_id: str
    label: str
    required: tuple[str, ...]
    questions: tuple[str, ...]


GATES = (
    Gate(
        "G1",
        "导演意图",
        ("intent.audience_feeling", "intent.narrative_function", "intent.start_state", "intent.end_state"),
        (
            "观众在这段结束时应感受到什么？",
            "这段镜头在故事中承担什么作用？",
            "镜头开始与结束时，人物和关键道具分别处于什么状态？",
        ),
    ),
    Gate(
        "G2",
        "时间与结构",
        ("timing.duration_seconds", "timing.structure", "timing.cut_policy"),
        (
            "目标时长是多少秒？",
            "它是一镜到底、少量切镜，还是明确多镜结构？",
            "允许在哪里切，哪些动作绝不能被切断？",
        ),
    ),
    Gate(
        "G3",
        "角色台账",
        ("cast.characters", "cast.count_lock", "cast.identity_policy"),
        (
            "画面中固定有哪些角色，总人数是多少？",
            "每个人的起点、目标、路线、表情和离场方式是什么？",
            "哪些角色必须独立身份图，哪些共享群体名册？",
        ),
    ),
    Gate(
        "G4",
        "空间与连续性",
        ("space.scene", "space.axis", "space.anchors", "space.prop_state"),
        (
            "场景轴线、屏幕方向和前中后景关系是什么？",
            "哪些建筑、道具、光源和地形是绝对锚点？",
            "关键道具在开头和结尾分别在哪里？",
        ),
    ),
    Gate(
        "G5",
        "动作与物理",
        ("motion.actions", "motion.contact_order", "motion.physics", "motion.failure_fallback"),
        (
            "谁先动、谁后动，每个动作有哪些可见中间过程？",
            "接触点、受力方向、延迟、回弹和停止如何发生？",
            "动作太复杂时，允许怎样降级而不破坏故事？",
        ),
    ),
    Gate(
        "G6",
        "摄影与转场",
        ("camera.shot_design", "camera.path", "camera.focus", "camera.transition"),
        (
            "景别、焦段、机位和摄影机路径是什么？",
            "焦点怎样交接？",
            "转场依靠动作、遮挡、视线、光线还是声音？",
        ),
    ),
    Gate(
        "G7",
        "素材与任务类型",
        ("assets.task_type", "assets.motion_reference", "assets.reference_roles", "assets.inventory_complete"),
        (
            "应该使用 reference、edit、extend 还是首尾帧？",
            "是否已有真实运动预演；没有的话由什么方式制作？",
            "每张图、每段视频分别只负责什么？",
        ),
    ),
    Gate(
        "G8",
        "成本与验收",
        ("delivery.resolution", "delivery.max_paid_tasks", "delivery.budget_cny", "delivery.acceptance", "delivery.stop_condition"),
        (
            "本轮最多允许几次付费任务，预算是多少？",
            "必须看见哪些动作和连续性证据才算通过？",
            "第一条失败后，什么条件下停止而不是继续抽卡？",
        ),
    ),
)


def _get(payload: dict[str, Any], dotted: str) -> Any:
    value: Any = payload
    for key in dotted.split("."):
        if not isinstance(value, dict) or key not in value:
            return None
        value = value[key]
    return value


def _present(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, dict, set)):
        return bool(value)
    return True


def evaluate(payload: dict[str, Any]) -> dict[str, Any]:
    gate_results = []
    for gate in GATES:
        missing = [field for field in gate.required if not _present(_get(payload, field))]
        gate_results.append(
            {
                "gate_id": gate.gate_id,
                "label": gate.label,
                "passed": not missing,
                "missing": missing,
            }
        )
    first_failed = next((result for result in gate_results if not result["passed"]), None)
    score = sum(result["passed"] for result in gate_results)
    return {
        "workflow_version": WORKFLOW_VERSION,
        "evaluated_at": date.today().isoformat(),
        "score": score,
        "total_gates": len(GATES),
        "ready_for_workflow_design": first_failed is None,
        "first_failed_gate": first_failed,
        "gates": gate_results,
    }


def next_questions(payload: dict[str, Any], max_questions: int = 5) -> list[str]:
    assessment = evaluate(payload)
    if assessment["ready_for_workflow_design"]:
        return []
    failed_id = assessment["first_failed_gate"]["gate_id"]
    gate = next(item for item in GATES if item.gate_id == failed_id)
    return list(gate.questions[: max(1, max_questions)])


def run(input_payload: dict[str, Any]) -> dict[str, Any]:
    """Return the next safe agent action without performing external work."""
    if not isinstance(input_payload, dict):
        return {"status": "INVALID_INPUT", "execution_authorized": False}
    schema=input_payload.get('schema_version')
    legacy_keys={'intent','timing','cast','space','motion','camera','assets','delivery'}
    if schema=='director-production/v3' or (schema is None and ('brief' in input_payload or not legacy_keys.intersection(input_payload))):
        import importlib.util
        spec=importlib.util.spec_from_file_location('aigc_director_control',Path(__file__).with_name('director_control.py'))
        module=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.plan(input_payload)
    if "schema_version" in input_payload:
        if input_payload["schema_version"] != "director-production/v2":
            return {"status": "UNSUPPORTED_SCHEMA", "execution_authorized": False}
        return _with_legacy_solutions(plan_production(input_payload), input_payload)
    assessment = evaluate(input_payload)
    if not assessment["ready_for_workflow_design"]:
        return {
            "status": "GRILL_ME",
            "assessment": assessment,
            "questions": next_questions(input_payload),
            "allowed_outputs": ["confirmed_facts", "open_questions", "assumptions", "next_question_batch"],
            "forbidden_outputs": ["paid_workflow", "submission", "final_execution_prompt"],
        }
    return _with_legacy_solutions({
        "status": "DESIGN_READY",
        "assessment": assessment,
        "questions": [],
        "allowed_outputs": [
            "director_contract",
            "asset_plan",
            "workflow_design",
            "cost_preview",
            "acceptance_plan",
            "execution_prompt_draft",
        ],
        "requires_confirmation_before": ["external_upload", "paid_generation", "retry", "additional_variant"],
        "execution_authorized": False,
        "compatibility": "legacy_G1_G8; new production uses director-production/v2",
    }, input_payload)


def _with_legacy_solutions(result: dict, payload: dict) -> dict:
    """Legacy design stages remain compatible, but cannot silently skip the library."""
    import importlib.util
    try:
        spec=importlib.util.spec_from_file_location('aigc_solution_legacy',Path(__file__).parent/'方案库/decide.py')
        module=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        shots=payload.get('artifacts',{}).get('shot_design',{}).get('data',{}).get('shots') or [{'shot_id':'S01'}]
        decisions=module.plan_shots({'solution_facts':payload.get('solution_facts',{})}, shots)
        return {**result,'solution_decisions':decisions,'execution_authorized':False,
                'solution_boundary':'旧状态保留；开工前补齐方案事实和当前能力，不以旧阶段通过代替方案决策。'}
    except (ValueError,TypeError,KeyError,AttributeError,OSError) as exc:
        return {**result,'status':'NEEDS_HUMAN_REVIEW','ready':[],
                'execution_authorized':False,'problem':str(exc)}


def fingerprint(data: Any) -> str:
    return hashlib.sha256(json.dumps(data, ensure_ascii=False, sort_keys=True,
                                    separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()


def _positive(v: Any) -> bool:
    return type(v) in (int, float) and math.isfinite(v) and v > 0


def _number(v: Any) -> bool:
    return type(v) in (int, float) and math.isfinite(v)


def _production_errors(stage: str, data: dict, artifacts: dict, example: bool) -> list[str]:
    errors = []
    def need(obj, fields, label):
        if not isinstance(obj, dict):
            errors.append(label + ': expected object')
            return
        for field in fields:
            if field not in obj or not _present(obj[field]):
                errors.append(label + ': missing ' + field)
    def upstream(key):
        return artifacts.get(key, {}).get('data', {})
    intent = upstream('director_intent')
    if stage == 'director_intent':
        if type(data.get('has_dialogue')) is not bool: errors.append('has_dialogue must be boolean')
    if stage in ('shot_design','scene_design','action_design','prompt_design','node_design'):
        shots = data.get('shots')
        if not isinstance(shots,list) or not shots: return ['shots must be a nonempty list']
        ids = [s.get('shot_id') if isinstance(s,dict) else None for s in shots]
        if any(not isinstance(i,str) or not i for i in ids) or len(set(ids)) != len(ids):
            return ['shot_id values must be nonempty and unique']
        expected = [s['shot_id'] for s in upstream('shot_design').get('shots',[])]
        if stage != 'shot_design' and ids != expected: errors.append('shot order/ids differ from storyboard')
        fields = {
            'shot_design':['purpose','shot_size','perspective','transition'],
            'scene_design':['space','asset_ids'],
            'action_design':['beats','previs'],
            'prompt_design':['reference_roles','prompt','negative','acceptance'],
            'node_design':['mode','node_class','inputs'],
        }[stage]
        for s in shots:
            need(s,fields,s['shot_id'])
            if stage=='shot_design':
                if not _positive(s.get('duration_seconds')): errors.append('shot duration must be positive')
                if type(s.get('has_dialogue')) is not bool: errors.append('shot dialogue flag must be boolean')
        if stage=='shot_design' and any(s.get('has_dialogue') for s in shots)!=intent.get('has_dialogue'):
            errors.append('storyboard dialogue contradicts director intent')
    if stage=='sound_design':
        if type(data.get('has_dialogue')) is not bool or data.get('has_dialogue')!=intent.get('has_dialogue'):
            errors.append('sound dialogue flag contradicts intent')
        lines=data.get('dialogue')
        if not isinstance(lines,list):return errors+['dialogue must be a list']
        if bool(lines)!=data.get('has_dialogue'):errors.append('dialogue list contradicts flag')
        ids=[]
        for line in lines:
            need(line,['line_id','speaker','text'],'dialogue')
            if not isinstance(line,dict):continue
            ids.append(line.get('line_id'))
            if not _positive(line.get('duration_seconds')): errors.append('dialogue duration must be positive')
            if type(line.get('measured')) is not bool:errors.append('measured must be boolean')
            if line.get('measured') is True:
                if not line.get('audio_path'):errors.append('measured dialogue requires audio_path')
                elif not example and not Path(line['audio_path']).is_file():errors.append('measured audio file missing')
        if len(ids)!=len(set(ids)):errors.append('duplicate dialogue line_id')
        if not isinstance(data.get('sound_cues'),list):errors.append('sound_cues must be a list')
    if stage=='timing_lock':
        sound=upstream('sound_design');shots=upstream('shot_design').get('shots',[])
        if data.get('locked') is not True:errors.append('timing not locked')
        if not _positive(data.get('duration_seconds')):errors.append('total duration must be positive')
        if sound.get('has_dialogue') and (data.get('basis')!='measured_dialogue' or any(l.get('measured') is not True for l in sound.get('dialogue',[]))):
            errors.append('dialogue timing requires measured accepted dry audio, not estimated text length')
        if not sound.get('has_dialogue') and data.get('basis')!='no_dialogue':errors.append('no-dialogue basis required')
        timeline=data.get('timeline')
        if not isinstance(timeline,list) or not timeline:return errors+['timeline required']
        if [t.get('shot_id') for t in timeline]!=[s.get('shot_id') for s in shots]:errors.append('timeline shot order differs')
        line_map={l['line_id']:l for l in sound.get('dialogue',[])}
        used=[];end=0.0
        for t in timeline:
            a,b=t.get('start'),t.get('end')
            if not _number(a) or not _number(b) or b<=a or abs(a-end)>.01:
                errors.append('timeline must be contiguous, ordered and positive from zero');continue
            end=b
            lids=t.get('dialogue_ids',[])
            if not isinstance(lids,list):errors.append('dialogue_ids must be a list');continue
            used+=lids
            if any(i not in line_map for i in lids):errors.append('unknown dialogue reference');continue
            if sum(line_map[i]['duration_seconds'] for i in lids)>b-a+.01:errors.append('dialogue longer than shot; revise timing without accelerating speech')
        if sorted(used)!=sorted(line_map):errors.append('every dialogue interval must occur exactly once')
        if _number(data.get('duration_seconds')) and abs(end-data['duration_seconds'])>.01:errors.append('timeline total mismatch')
    if stage=='scene_design':
        assets=data.get('assets',[])
        if not isinstance(assets,list):return errors+['assets must be a list']
        asset_ids=[]
        for a in assets:
            need(a,['asset_id','path','role','status'],'asset')
            if not isinstance(a,dict):continue
            asset_ids.append(a.get('asset_id'))
            if a.get('status') not in ['proposed','available']:errors.append('invalid asset status')
            if a.get('status')=='available' and not example and not Path(a['path']).is_file():errors.append('available asset file missing')
        if len(asset_ids)!=len(set(asset_ids)):errors.append('duplicate asset id')
        for s in data['shots']:
            if any(i not in asset_ids for i in s.get('asset_ids',[])):errors.append('unknown scene asset reference')
    if stage=='action_design':
        durations={t['shot_id']:t['end']-t['start'] for t in upstream('timing_lock')['timeline']}
        for s in data['shots']:
            end=0.0; beats=s.get('beats',[])
            if not isinstance(beats,list):errors.append('beats must be a list');continue
            for b in beats:
                need(b,['subject','camera','contact'],'beat')
                if not isinstance(b,dict):continue
                a,z=b.get('start'),b.get('end')
                if not _number(a) or not _number(z) or z<=a or abs(a-end)>.01:errors.append('beats must be ordered, contiguous and positive');continue
                end=z
            if s['shot_id'] in durations and abs(end-durations[s['shot_id']])>.01:errors.append('action beats do not cover locked duration')
    if stage=='node_design':
        if data.get('selected_by')!='director':errors.append('node selection belongs to director')
        if type(data.get('auto_retry')) is not int or data['auto_retry']!=0:errors.append('auto_retry must be zero')
    return errors


def _post_errors(stage: str, data: dict, artifacts: dict, example: bool) -> list[str]:
    """Check recorded media and handoff contracts; never render or certify visual QA."""
    errors=[]
    def upstream(key): return artifacts[key]['data']
    expected=[s['shot_id'] for s in upstream('shot_design')['shots']]
    design_stage=stage in ('vfx_design','color_grading')
    items=data.get('shots' if design_stage else 'clips')
    if not isinstance(items,list) or any(not isinstance(c,dict) for c in items):
        return ['shots/clips must be a list of objects']
    if [c.get('shot_id') for c in items]!=expected:
        return ['post-production shot order/ids differ from storyboard']
    if design_stage:
        source=upstream('video_delivery' if stage=='vfx_design' else 'vfx_delivery')
        durations={c['shot_id']:c['duration_seconds'] for c in source['clips']}
        mode=data.get('treatment');count=0
        if mode not in ('apply','bypass'):errors.append('treatment must be apply or bypass')
        for shot in items:
            if not _present(shot.get('plan')) or not _present(shot.get('acceptance')):
                errors.append('post design requires plan and acceptance per shot')
            spans=shot.get('intervals')
            if not isinstance(spans,list):errors.append('intervals must be a list');continue
            count+=len(spans)
            for span in spans:
                if not isinstance(span,dict):errors.append('interval must be object');continue
                a,b=span.get('start'),span.get('end')
                if not _number(a) or not _number(b) or not 0<=a<b<=durations[shot['shot_id']]:
                    errors.append('post interval outside actual video duration')
        if mode=='apply' and not count:errors.append('apply requires an effect interval')
        if mode=='bypass' and count:errors.append('bypass cannot contain effect intervals')
        return errors
    review=data.get('human_review')
    if not isinstance(review,dict) or review.get('passed') is not True or not _present(review.get('reviewed_by')):
        errors.append('accepted human video review required')
    if stage=='video_delivery' and data.get('generation_completed') is not True:
        errors.append('video generation must be completed')
    original={t['shot_id']:t['end']-t['start'] for t in upstream('timing_lock')['timeline']}
    source_key={'vfx_delivery':'video_delivery','post_delivery':'vfx_delivery'}.get(stage)
    sources={c['shot_id']:c for c in upstream(source_key)['clips']} if source_key else {}
    design=upstream('vfx_design' if stage=='vfx_delivery' else 'color_grading') if source_key else {}
    protected_keys=() if not source_key else ('video_delivery',) if stage=='vfx_delivery' else ('video_delivery','vfx_delivery')
    protected_paths={str(Path(c['path']).resolve()).casefold() for k in protected_keys
                     for c in upstream(k)['clips']}
    for clip in items:
        sid=clip['shot_id'];digest=clip.get('sha256');p=clip.get('path')
        if not isinstance(digest,str) or len(digest)!=64 or any(c not in '0123456789abcdef' for c in digest):
            errors.append('video sha256 must be 64 lowercase hex characters')
        if not isinstance(p,str) or not Path(p).is_absolute():errors.append('absolute video path required')
        elif not example:
            try:
                with Path(p).open('rb') as stream:
                    actual=hashlib.file_digest(stream,'sha256').hexdigest()
                if actual!=digest:errors.append('video file hash mismatch: '+sid)
            except OSError:errors.append('video file missing or unreadable: '+sid)
        if not _positive(clip.get('duration_seconds')) or not _positive(clip.get('fps')):
            errors.append('positive measured video duration and fps required');continue
        if any(type(clip.get(k)) is not int or clip[k]<=0 for k in ('width','height')):
            errors.append('positive integer video dimensions required')
        if not source_key:
            if abs(clip['duration_seconds']-original[sid])>max(.01,1/clip['fps']):
                errors.append('generated video duration differs from locked timeline')
        else:
            prev=sources[sid]
            if any(clip.get(k)!=prev[k] for k in ('duration_seconds','fps','width','height')):
                errors.append('post-processing must preserve timing and image geometry')
            affected=next(s for s in design['shots'] if s['shot_id']==sid)['intervals']
            if design['treatment']=='bypass' or not affected:
                if digest!=prev['sha256']:errors.append('bypass/unaffected clip must preserve source bytes')
            elif isinstance(p,str) and str(Path(p).resolve()).casefold() in protected_paths:
                errors.append('processed output must not overwrite accepted source')
    return errors


def plan_production(payload: dict[str, Any]) -> dict[str, Any]:
    manifest=json.loads((Path(__file__).parent/'workflow_manifest.json').read_text(encoding='utf-8'))
    artifacts=payload.get('artifacts',{})
    if not isinstance(artifacts,dict):return {'status':'INVALID_INPUT','execution_authorized':False}
    states={};ready=[];invalid=[]
    for stage in manifest['stages']+manifest.get('post_stages',[]):
        key=stage['id'];deps=stage['depends_on'];record=artifacts.get(key)
        blocked=[d for d in deps if states[d]['state']!='valid']
        errors=[]
        if blocked:
            state='stale' if record else 'waiting'
            errors=['upstream not valid: '+','.join(blocked)]
        elif record is None:
            state='ready'
        elif not isinstance(record,dict):
            state='invalid';errors=['artifact must be object']
        else:
            data=record.get('data',{})
            if record.get('status')!='accepted':errors.append('design not accepted')
            if type(record.get('revision')) is not int or record['revision']<1:errors.append('positive integer revision required')
            if record.get('owner')!=stage['owner']:errors.append('wrong role owner')
            if not record.get('approved_by'):errors.append('design acceptance owner required')
            versions=record.get('inputs',{})
            hashes=record.get('input_hashes',{})
            if not isinstance(versions,dict) or not isinstance(hashes,dict):
                errors.append('inputs and input_hashes must be objects')
                versions={};hashes={}
            for d in deps:
                if versions.get(d)!=artifacts[d].get('revision'):errors.append('stale version: '+d)
                if hashes.get(d)!=fingerprint(artifacts[d]['data']):errors.append('stale content: '+d)
            if not isinstance(data,dict):errors.append('data must be object')
            else:
                try:fingerprint(data)
                except (ValueError,TypeError):errors.append('data must be finite JSON')
                for field in stage['required']:
                    if field not in data:errors.append('missing '+field)
                    elif field not in ['has_dialogue','dialogue','sound_cues','auto_retry'] and not _present(data[field]):errors.append('empty '+field)
                if not errors:
                    try:
                        checker=_post_errors if stage in manifest.get('post_stages',[]) else _production_errors
                        errors+=checker(key,data,artifacts,payload.get('example_only') is True)
                    except (TypeError,ValueError,KeyError,AttributeError):errors.append('malformed stage data')
            state='valid' if not errors else 'invalid'
        states[key]={'state':state,'owner':stage['owner'],'errors':errors}
        if state in ['ready','invalid'] and not blocked:
            ready.append({'stage':key,'owner':stage['owner'],**manifest['roles'][stage['owner']], 'inputs':deps})
        if state in ['stale','invalid']:invalid.append(key)
    complete=all(states[s['id']]['state']=='valid' for s in manifest['stages'])
    post_complete=all(states[s['id']]['state']=='valid' for s in manifest['post_stages'])
    post_status=('WAITING_FOR_DESIGN' if not complete else 'POST_READY_FOR_HANDOFF' if post_complete
                 else 'AWAITING_VIDEO' if states['video_delivery']['state']!='valid' else 'POST_IN_PROGRESS')
    return {'workflow_version':WORKFLOW_VERSION,'status':'DESIGN_READY' if complete else 'DESIGN_IN_PROGRESS',
            'example_only':payload.get('example_only') is True,'ready':ready,'stages':states,'post_status':post_status,
            'invalidated':invalid,'execution_authorized':False,
            'next_action':'director reviews final delivery; confirm actual media QA' if post_complete else 'dispatch only ready stages; video generation and review precede post-production',
            'claim_boundary':'Offline dependency and contract checks only. No model launched, no paid request submitted.'}


if __name__ == "__main__":
    import json
    import sys

    source = json.load(sys.stdin)
    json.dump(run(source), sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
