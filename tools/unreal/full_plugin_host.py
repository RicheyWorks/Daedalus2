"""Create a fresh isolated host from every tracked DaedalusLink file, without overlays."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

def read_blobs(repo, entries):
    # Stream object records through one Git process; no whole-corpus buffer.
    with subprocess.Popen(['git','cat-file','--batch'],cwd=repo,
                          stdin=subprocess.PIPE,stdout=subprocess.PIPE) as process:
        for name,blob in entries:
            process.stdin.write((blob+'\n').encode('ascii'))
            process.stdin.flush()
            fields=process.stdout.readline().split()
            if len(fields)!=3 or fields[0]!=blob.encode('ascii') or fields[1]!=b'blob' or not fields[2].isdigit():
                raise ValueError('Git batch object identity/type mismatch')
            size=int(fields[2]);raw=process.stdout.read(size)
            if len(raw)!=size or process.stdout.read(1)!=b'\n':
                raise ValueError('Truncated Git batch object')
            yield name,raw
        process.stdin.close()
        if process.stdout.read(1): raise ValueError('Unexpected trailing Git batch data')
        if process.wait()!=0: raise ValueError('Git batch reader failed')

def snapshot(repo, destination):
    repo=repo.resolve();destination=destination.resolve()
    if destination.exists(): raise ValueError('Destination must be fresh; existing hosts are never reset')
    prefix='engines/unreal/DaedalusLink/'
    if subprocess.run(['git','diff','--quiet','HEAD','--',prefix],cwd=repo).returncode:
        raise ValueError('Commit plugin edits before recording an exact-head build')
    if subprocess.check_output(['git','ls-files','--others','--exclude-standard','--',prefix],cwd=repo):
        raise ValueError('Untracked plugin files would be omitted; commit them first')
    sha=subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip()
    # Pin both names and bytes to this commit. Working files can change while
    # another agent is building; a clean check alone is not a frozen snapshot.
    tree=subprocess.check_output(['git','ls-tree','-r','-z',sha,'--',prefix],cwd=repo)
    entries=[]
    for row in tree.split(b'\0'):
        if not row: continue
        metadata,name=row.split(b'\t',1)
        mode,kind,blob=metadata.decode('ascii').split()
        if kind!='blob' or mode not in ('100644','100755'):
            raise ValueError('Plugin snapshot requires regular tracked files')
        entries.append((name.decode('utf-8'),blob))
    if not entries or not any(name.endswith('/DaedalusLink.uplugin') for name,_ in entries):
        raise ValueError('Pinned plugin descriptor missing')
    plugin=destination/'Plugins/DaedalusLink'
    inputs={}
    for name,raw in read_blobs(repo,entries):
        relative=Path(name[len(prefix):])
        target=(plugin/relative).resolve();target.relative_to(plugin)
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(raw)
        digest=hashlib.sha256(raw).hexdigest()
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
