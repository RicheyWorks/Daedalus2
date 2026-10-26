"""Create a fresh isolated host from every tracked DaedalusLink file, without overlays."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

def snapshot(repo, destination):
    repo=repo.resolve();destination=destination.resolve()
    if destination.exists(): raise ValueError('Destination must be fresh; existing hosts are never reset')
    prefix='engines/unreal/DaedalusLink/'
    if subprocess.run(['git','diff','--quiet','HEAD','--',prefix],cwd=repo).returncode:
        raise ValueError('Commit plugin edits before recording an exact-head build')
    if subprocess.check_output(['git','ls-files','--others','--exclude-standard','--',prefix],cwd=repo):
        raise ValueError('Untracked plugin files would be omitted; commit them first')
    paths=subprocess.check_output(['git','ls-files','-z',prefix],cwd=repo).decode().split('\0')
    paths=[p for p in paths if p]
    assert paths and any(p.endswith('/DaedalusLink.uplugin') for p in paths)
    sha=subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip()
    plugin=destination/'Plugins/DaedalusLink'
    inputs={}
    for name in paths:
        source=(repo/name).resolve();relative=Path(name[len(prefix):])
        source.relative_to(repo)
        target=(plugin/relative).resolve();target.relative_to(plugin)
        target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(source,target)
        digest=hashlib.sha256(source.read_bytes()).hexdigest()
        assert hashlib.sha256(target.read_bytes()).hexdigest()==digest
        inputs[name]=digest
    project=destination/'HostProject.uproject'
    project.write_text(json.dumps({'FileVersion':3,'Plugins':[{'Name':'DaedalusLink','Enabled':True}]},indent=2))
    (destination/'source-manifest.json').write_text(json.dumps({'source_head':sha,'files':inputs,
        'tracked_file_count':len(inputs),'overlays':[]},indent=2))
    print(json.dumps({'project':str(project),'source_head':sha,'files':len(inputs)}))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('repo',type=Path);parser.add_argument('destination',type=Path)
    args=parser.parse_args();snapshot(args.repo,args.destination)
