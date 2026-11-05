"""Validate a blockout brief without importing Blender or generating any geometry."""
import argparse
import hashlib
import json
import math
from pathlib import Path

FACT_STATES = {'source_observed', 'user_confirmed', 'design_assumption', 'external_reference'}


def fingerprint_file(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def positive_number(value):
    return type(value) in (int, float) and math.isfinite(value) and value > 0


def validate_contract(data, base_dir=None, check_files=False):
    errors = []
    if not isinstance(data, dict):
        return {'valid': False, 'errors': ['contract must be an object']}
    if data.get('schema_version') != 'blender-blockout/v1':
        errors.append('unsupported schema_version')
    for name in ('asset_id', 'request', 'output_root'):
        if not isinstance(data.get(name), str) or not data[name].strip():
            errors.append(name + ' must be a nonempty string')
    if data.get('mode') not in ('plan', 'build', 'review', 'revise'):
        errors.append('mode must be plan/build/review/revise')
    base = Path(base_dir or Path.cwd()).resolve()
    refs = data.get('reference_images', [])
    refs_ids = set()
    checked_refs = []
    if not isinstance(refs, list):
        errors.append('reference_images must be an array')
        refs = []
    for ref in refs:
        if not isinstance(ref, dict):
            errors.append('reference image must be an object')
            continue
        rid = ref.get('id')
        if not isinstance(rid, str) or not rid or rid in refs_ids:
            errors.append('reference image ID missing or duplicate')
        elif rid:
            refs_ids.add(rid)
        if ref.get('role') not in ('shape', 'identity', 'layout', 'detail', 'style', 'quality'):
            errors.append('reference image role missing or unsupported')
        if not isinstance(ref.get('path'), str) or not ref['path']:
            errors.append('reference image path required')
            continue
        if check_files:
            path = (base / ref['path']).resolve()
            if not path.is_file():
                errors.append('reference image file missing: ' + ref['path'])
                continue
            actual = fingerprint_file(path)
            checked_refs.append({'id': rid, 'sha256': actual})
            if ref.get('sha256') and (not isinstance(ref['sha256'], str) or ref['sha256'].lower() != actual):
                errors.append('reference image changed: ' + ref['path'])

    scale = data.get('scale')
    if not isinstance(scale, dict):
        errors.append('scale object required')
    else:
        value = scale.get('meters_per_unit')
        if value is not None and not positive_number(value):
            errors.append('meters_per_unit must be null or finite positive number')
        if scale.get('source') not in ('user_confirmed', 'measured', 'design_assumption', 'relative_only'):
            errors.append('scale source missing or unsupported')
        if value is None and scale.get('source') != 'relative_only':
            errors.append('unknown absolute scale must be labeled relative_only')
        if not isinstance(scale.get('basis'), str) or not scale['basis'].strip():
            errors.append('scale basis required')

    facts = data.get('facts', [])
    if not isinstance(facts, list):
        errors.append('facts must be an array')
        facts = []
    for fact in facts:
        if not isinstance(fact, dict):
            errors.append('fact must be an object')
            continue
        if not isinstance(fact.get('status'), str) or fact['status'] not in FACT_STATES:
            errors.append('fact status missing or unsupported')
        for key in ('id', 'statement', 'source'):
            if not isinstance(fact.get(key), str) or not fact[key].strip():
                errors.append('fact ' + key + ' required')

    components = data.get('components')
    if not isinstance(components, list) or not components:
        errors.append('nonempty components array required')
        components = []
    parents = {}
    for component in components:
        if not isinstance(component, dict):
            errors.append('component must be an object')
            continue
        cid = component.get('id')
        if not isinstance(cid, str) or not cid:
            errors.append('component ID required')
            continue
        if cid in parents:
            errors.append('duplicate component ID: ' + cid)
        parent = component.get('parent')
        if parent is not None and not isinstance(parent, str):
            errors.append('component parent must be a string or null: ' + cid)
            parent = None
        parents[cid] = parent
        if not isinstance(component.get('method'), str) or not component['method'].strip():
            errors.append('component method required: ' + cid)
        dims = component.get('dimensions', {})
        if not isinstance(dims, dict):
            errors.append('component dimensions must be an object: ' + cid)
        else:
            for axis, value in dims.items():
                if axis not in ('x', 'y', 'z') or (value is not None and not positive_number(value)):
                    errors.append('component dimensions must be null or finite positive xyz: ' + cid)
        if (not isinstance(component.get('dimension_source'), str)
                or component['dimension_source'] not in FACT_STATES | {'relative_only', 'measured'}):
            errors.append('component dimension_source required: ' + cid)
    for cid, parent in parents.items():
        if parent is not None and parent not in parents:
            errors.append('unknown parent for ' + cid)
        seen = set()
        current = cid
        while current in parents:
            if current in seen:
                errors.append('component parent cycle: ' + cid)
                break
            seen.add(current)
            current = parents[current]

    root = data.get('output_root')
    deliverables = data.get('deliverables')
    if not isinstance(deliverables, list) or not deliverables:
        errors.append('nonempty deliverables array required')
        deliverables = []
    if isinstance(root, str) and root:
        output_root = (base / root).resolve()
        for deliverable in deliverables:
            if not isinstance(deliverable, str) or not deliverable:
                errors.append('deliverable must be a path string')
            elif not (output_root / deliverable).resolve().is_relative_to(output_root):
                errors.append('deliverable escapes output_root: ' + deliverable)
    views = data.get('review_views')
    if not isinstance(views, list) or not views or any(not isinstance(v, str) or not v for v in views):
        errors.append('nonempty review_views array required')
    return {'valid': not errors, 'errors': errors, 'checked_input_files': checked_refs,
            'claim_boundary': 'Contract/file checks only, not image understanding, geometry quality or user approval.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('contract', type=Path)
    parser.add_argument('--check-files', action='store_true')
    args = parser.parse_args()
    try:
        data = json.loads(args.contract.read_text(encoding='utf-8-sig'))
        result = validate_contract(data, args.contract.parent, args.check_files)
    except (OSError, ValueError, TypeError) as exc:
        result = {'valid': False, 'errors': [str(exc)]}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result['valid'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
