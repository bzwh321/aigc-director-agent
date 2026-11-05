"""Offline recipe selection. No network, credentials, writes or execution."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parent
ENUMS = {
    'input_kind': {'image', 'video', 'none', 'unknown'},
    'operation': {'generate', 'edit', 'extend', 'post', 'lipsync', 'unknown'},
    'subject_motion': {'none', 'required', 'unknown'},
    'camera_motion': {'none', 'pan', 'tilt', 'zoom', 'reframe', 'translate', 'complex', 'unknown'},
}
BOOLS = {'needs_new_pixels', 'real_motion_verified', 'source_accepted',
         'hard_end_frame', 'endpoints_compatible', 'simple_middle_action',
         'multiple_reference_roles', 'dynamic_reference_verified',
         'locked_background', 'crop_margin_verified', 'visible_speaker',
         'audio_ready'}


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode('utf-8')).hexdigest()


def decide(raw, catalog=None):
    catalog = catalog if catalog is not None else json.loads((ROOT/'catalog.json').read_text(encoding='utf-8'))
    result = {'library_version': catalog['version'], 'execution_authorized': False,
              'automatic_retry': False, 'recipe_id': None, 'candidates': [],
              'questions': [], 'rejected': [], 'status': 'NEEDS_FACTS'}
    if not isinstance(raw, dict):
        return {**result, 'status': 'INVALID_FACTS', 'questions': ['方案事实应为对象。']}
    facts = {k: v for k, v in raw.items() if k in ENUMS or k in BOOLS}
    for key, value in facts.items():
        valid = (isinstance(value, str) and value in ENUMS[key]) if key in ENUMS else (type(value) is bool or value == 'unknown')
        if not valid:
            return {**result, 'status': 'INVALID_FACTS', 'questions': [f'请修正字段 {key} 的类型或取值。']}
    result['decision_fingerprint'] = fingerprint({'catalog': catalog, 'facts': facts})
    recipes = {r['id']: r for r in catalog['recipes']}

    def ask(message):
        result['questions'] = [message]
        return result

    def select(recipe_id, reason):
        recipe = recipes[recipe_id]
        return {**result, 'status': 'SELECTED', 'recipe_id': recipe_id,
                'mode': recipe['mode'], 'reason': reason,
                'service_candidates': recipe['services'],
                'evidence_status': recipe['status'],
                'strategy_ref': 'catalog.json#'+recipe['strategy'],
                'next_step': '核对当前服务/节点能力和输入版本后写入合同；选型不是执行或付费授权。'}

    kind = facts.get('input_kind', 'unknown')
    op = facts.get('operation', 'unknown')
    if kind == 'unknown':
        return ask('本镜可用输入是图片、视频还是尚无素材？')
    if op == 'unknown':
        return ask('本次要新生成、编辑原片、续写、后期合成还是修复口型？')
    if op in ('post', 'lipsync', 'edit', 'extend') and kind != 'video':
        return ask('所选操作需要已有视频；请提供视频或明确改为从图片生成。')
    if op == 'post':
        if facts.get('needs_new_pixels') is False:
            return select('local-post', '已有视频只需确定性剪接、音轨或图文合成。')
        return {**result, 'status': 'DIRECTOR_CHOICE', 'questions': ['后期是否需要生成新像素？需生成式特效/提质时由总控补具体方案与当前能力。']}
    if op == 'lipsync':
        if facts.get('visible_speaker') is False:
            return {**result, 'status': 'NOT_NEEDED', 'reason': '无可见说话人，不安排口型修复。'}
        if not all(facts.get(k) is True for k in ('source_accepted', 'visible_speaker', 'audio_ready')):
            return ask('口型修复前请确认画面已通过、嘴巴可见且原干声已确定。')
        return select('dialogue-lipsync', '已接受画面与原干声齐备；执行前仍需识别本片真实 faceId。')
    if op == 'edit':
        if facts.get('real_motion_verified') is not True or facts.get('needs_new_pixels') == 'unknown':
            result['rejected'] = [{'recipe_id': 'video-edit', 'reason': '未证实源视频具备需要保留的运动，不能靠 Edit 发明缺失动作。'}]
            return ask('源视频是否实际包含目标运动？若要创造新动作，请明确改为生成方案。')
        return select('video-edit', '已检查源中运动，目标是保留运动并修改指定内容。')
    if op == 'extend':
        if facts.get('source_accepted') is not True:
            return ask('请先确认作为续写起点的片段已被接受。')
        return select('video-extend', '已接受视频需要续写；服务支持与连续性仍须核对。')
    if kind == 'none':
        return {**result, 'status': 'DIRECTOR_CHOICE', 'questions': ['尚无素材：先设计静态锚点，或由总控补充当前可验证的文生视频方案。']}
    if facts.get('hard_end_frame') is True:
        if facts.get('endpoints_compatible') is not True or facts.get('simple_middle_action') is not True:
            return ask('首尾是否兼容且中间动作简单？有硬尾帧不能默默改成普通参考模式。')
        return select('first-last-frame', '首尾为明确硬约束，端点兼容且中间动作简单。')
    if facts.get('hard_end_frame') is not False:
        return ask('是否有必须精确锁定的尾帧？普通参考图不算硬尾帧。')
    if kind == 'video':
        if facts.get('dynamic_reference_verified') is True:
            return select('multimodal-reference', '已有经检查的动态样本，用于新画面生成而非保留原时间线。')
        return ask('视频作为动态样本时，是否已检查实际运动？只提供描述不算已验证。')
    motion = facts.get('subject_motion', 'unknown')
    camera = facts.get('camera_motion', 'unknown')
    if motion == 'unknown' or camera == 'unknown':
        return ask('请分别确认主体运动和摄影机运动，未知不能默认静止。')
    if facts.get('needs_new_pixels') is False and motion == 'none' and camera in ('none', 'pan', 'zoom', 'reframe'):
        return select('local-still-pan', '主体明确静止，只需二维重构图，不要求生成新画面。')
    if facts.get('needs_new_pixels') is False:
        return ask('主体动作/三维运镜与“不生成新画面”冲突，请确认要求。')
    if facts.get('locked_background') is True:
        if camera not in ('none', 'pan', 'zoom', 'reframe'):
            return {**result, 'status': 'DIRECTOR_CHOICE', 'questions': ['背景锁定与真实三维运镜需联合评估，不能用本地平移冒充。']}
        if facts.get('crop_margin_verified') is not True:
            return ask('固定底片加本地裁切前，请确认分辨率和裁切余量。')
        return select('fixed-plate-local-reframe', '生成主体运动与确定性重构图分工，优先稳定背景。')
    if facts.get('multiple_reference_roles') is True:
        return select('multimodal-reference', '多源身份/场景参考需要各自分工，不承担硬时间戳。')
    if facts.get('needs_new_pixels') is True or motion == 'required' or camera in ('tilt', 'translate', 'complex'):
        return select('image-to-video', '由图片锚定，模型生成所需运动，无硬尾帧约束。')
    return ask('是否需要生成新像素或真实运动？明确后可区分本地平移和图生视频。')


def plan_shots(brief, shots):
    """Bridge existing V3 fields conservatively; never infer an unseen asset's modality."""
    catalog = json.loads((ROOT/'catalog.json').read_text(encoding='utf-8'))
    decisions = {}
    for shot in shots:
        merged = {**brief, **shot}
        base_facts = brief.get('solution_facts', {})
        shot_facts = shot.get('solution_facts', {})
        if not isinstance(base_facts, dict) or not isinstance(shot_facts, dict):
            raise ValueError('solution_facts must be an object')
        facts = {k: merged[k] for k in ('subject_motion', 'camera_motion') if k in merged}
        render = merged.get('render_mode')
        if render == 'local_pan':
            facts.update(input_kind='image', operation='generate')
            if merged.get('subject_motion') == 'none':
                facts.update(needs_new_pixels=False, hard_end_frame=False)
        elif render == 'local_edit':
            facts.update(input_kind='video', operation='post', needs_new_pixels=False)
        elif render == 'generate':
            facts['operation'] = 'generate'
        facts.update(base_facts)
        facts.update(shot_facts)
        for key in ('subject_motion','camera_motion'):
            if key in merged and key in facts and facts[key] != merged[key]:
                raise ValueError(f'{shot["shot_id"]}: {key} conflicts with solution_facts; reconcile before routing')
        decisions[shot['shot_id']] = decide(facts, catalog)
    return decisions


if __name__ == '__main__':
    import argparse
    import sys
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, help='UTF-8 JSON facts; omitted means stdin')
    args = parser.parse_args()
    payload = json.loads(args.input.read_text(encoding='utf-8-sig')) if args.input else json.load(sys.stdin)
    json.dump(decide(payload), sys.stdout, ensure_ascii=False, indent=2)
