"""Exercise real CLI commands in a disposable directory, never live host config."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
SCRIPT=ROOT/'plugins/skill-role-manager/skills/manage-skills/scripts/manager.py'
SOURCE=ROOT/'plugins/building-practices'

def run(*args):
    proc=subprocess.run([sys.executable,'-B',str(SCRIPT),*args],capture_output=True,text=True)
    if proc.returncode:
        raise RuntimeError(proc.stderr)
    return json.loads(proc.stdout)

with tempfile.TemporaryDirectory(prefix='skill-role-demo-') as temp:
    target=Path(temp)
    checked=run('validate','--source',str(SOURCE))
    planned=run('plan','--source',str(SOURCE),'--target',temp)
    assert not list(target.iterdir()), 'Plan unexpectedly wrote target'
    applied=run('register','--source',str(SOURCE),'--target',temp,'--apply','--plan-digest',planned['plan_digest'])
    listed=run('list','--target',temp)
    assert listed['catalog']['plugins'][0]['name']=='building-practices'
    noop=run('register','--source',str(SOURCE),'--target',temp)
    assert noop['noop']
    removed_plan=run('unregister','--id','building-practices','--target',temp)
    removed=run('unregister','--id','building-practices','--target',temp,'--apply','--plan-digest',removed_plan['plan_digest'])
    assert not run('list','--target',temp)['catalog']['plugins']
    run('rollback','--target',temp,'--transaction',removed['transaction'],'--apply')
    assert len(run('list','--target',temp)['catalog']['plugins'])==1
    run('rollback','--target',temp,'--transaction',applied['transaction'],'--apply')
    assert not (target/'.agents/plugins/marketplace.json').exists()
    print(json.dumps({'package':checked['id'],'validate':'pass','read_only_plan':'pass',
                      'register_list_noop':'pass','unregister_rollback':'pass',
                      'original_absent_catalog_restored':'pass','native_host_activation':'not tested'},indent=2))
