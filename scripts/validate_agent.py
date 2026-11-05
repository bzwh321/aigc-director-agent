from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REQUIRED = [
    "AGENTS.md",
    "SKILL.md",
    "agent.json",
    "workflow.py",
    "workflow_manifest.json",
    "workflows/topology.yaml",
    "workflows/grill-me-protocol.md",
    "prompts/index.py",
    "prompts/versions/v1_0_0.py",
    "prompts/versions/v2_0_0.py",
    "prompts/versions/v3_0_0.py",
    "director_control.py",
    "workflows/director-control-v3.md",
    "workflows/production-v2.md",
    "examples/production_state.json",
    "examples/director-v2-demo.html",
    "memory/index.json",
    "outputs/artifact-map.md",
    "contract_html.py",
    "workflows/contract-v1.md",
]
FORBIDDEN_MEDIA = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".mp4", ".mov", ".mkv", ".webm", ".wav", ".mp3"}


def load_workflow():
    spec = importlib.util.spec_from_file_location("aigc_director_workflow", ROOT / "workflow.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def main() -> int:
    errors = []
    for relative in REQUIRED:
        if not (ROOT / relative).is_file():
            errors.append(f"missing: {relative}")
    for path in ROOT.rglob("*"):
        if path.is_file() and path.suffix.lower() in FORBIDDEN_MEDIA:
            errors.append(f"media not allowed: {path.relative_to(ROOT)}")
    for relative in ["agent.json", "workflow_manifest.json", "memory/index.json"]:
        try:
            json.loads((ROOT / relative).read_text(encoding="utf-8"))
        except Exception as exc:
            errors.append(f"invalid json {relative}: {exc}")
    if not errors:
        manifest=json.loads((ROOT/'workflow_manifest.json').read_text(encoding='utf-8'))
        for role, entry in manifest['roles'].items():
            for field in ['entrypoint','skill']:
                target=(ROOT/entry[field]).resolve()
                if not target.is_relative_to(ROOT.resolve()) or not target.is_file():
                    errors.append(f'invalid {role} {field}: {target}')
        known=set()
        for stage in manifest['stages']:
            if stage['owner'] not in manifest['roles']:errors.append('unregistered role')
            if stage['id'] in known or any(d not in known for d in stage['depends_on']):errors.append('invalid stage dependency order')
            known.add(stage['id'])
        workflow = load_workflow()
        incomplete = workflow.run({})
        if incomplete["status"] != "NEEDS_CLARIFICATION" or len(incomplete.get('questions',[]))>3:
            errors.append("new tasks must use brief clarification, not the legacy G1 questionnaire")
        initial=workflow.run({'schema_version':'director-production/v2','artifacts':{}})
        if [s['stage'] for s in initial['ready']] != ['director_intent']:errors.append('V2 must start at director intent')
    if errors:
        print("\n".join(errors))
        return 1
    print(f"OK: {ROOT}")
    print("required files present; JSON valid; no media; default V3 clarification and explicit V2 compatibility valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
