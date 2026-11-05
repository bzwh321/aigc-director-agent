"""Read-only teaching run. Does not generate media, submit requests or save state."""
import copy
import importlib.util
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('director_workflow',ROOT/'workflow.py')
w=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=w
spec.loader.exec_module(w)

def main():
    sample=json.loads((ROOT/'examples/production_state.json').read_text(encoding='utf-8'))
    steps=json.loads((ROOT/'workflow_manifest.json').read_text(encoding='utf-8'))['stages']
    state={**sample,'artifacts':{}}
    print('TEACHING DATA: no real media generated or paid request submitted')
    for stage in steps:
        r=w.run(state)
        print('READY:', ', '.join(s['stage'] for s in r['ready']))
        key=stage['id'];state['artifacts'][key]=copy.deepcopy(sample['artifacts'][key])
    result=w.run(state)
    print('COMPLETE:',result['status'],'execution_authorized=',result['execution_authorized'])
    if result['status']!='DESIGN_READY':
        print(json.dumps(result,ensure_ascii=False,indent=2));return 1
    state['artifacts']['sound_design']['data']['dialogue'][0]['duration_seconds']=4.5
    result=w.run(state)
    print('AUDIO CHANGED:',','.join(result['invalidated']))
    return 0

if __name__=='__main__':raise SystemExit(main())
