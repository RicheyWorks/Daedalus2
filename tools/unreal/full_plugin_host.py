"""Create a fresh isolated host from every tracked DaedalusLink file, without overlays."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

def verify(destination):
    """Recheck a recorded host; never mutate it or accept unrecorded overlays."""
    destination=destination.resolve()
    manifest=json.loads((destination/'source-manifest.json').read_text())
    if manifest.get('overlays')!=[]:
        raise ValueError('Exact-source verification refuses overlays')
    files=manifest['files']; generated=manifest['generated_host_files']
    scaffold_names={'Source/HostProject.Target.cs','Source/HostProjectEditor.Target.cs',
                    'Source/HostProject/HostProject.Build.cs','Source/HostProject/HostProject.cpp'}
    if set(generated)!=scaffold_names:raise ValueError('Invalid host scaffold paths')
    if not files or manifest['tracked_file_count']!=len(files):
        raise ValueError('Invalid recorded file count')
    expected={}
    prefix='engines/unreal/DaedalusLink/'
    for name,digest in files.items():
        if not name.startswith(prefix): raise ValueError('Invalid plugin path')
        expected['Plugins/DaedalusLink/'+name[len(prefix):]]=digest
    expected.update(generated)
    expected['HostProject.uproject']=manifest['project_sha256']
    for name,digest in expected.items():
        parts=name.split('/')
        if any(x in ('','..','.') for x in parts) or '\\' in name or ':' in name:
            raise ValueError('Unsafe manifest path')
        path=destination.joinpath(*parts)
        path.resolve().relative_to(destination)
        if path.is_symlink() or any(parent.is_symlink() for parent in path.parents if parent!=destination and destination in parent.parents):
            raise ValueError('Symlink input refused')
        if not isinstance(digest,str) or len(digest)!=64 or any(c not in '0123456789abcdef' for c in digest):
            raise ValueError('Invalid input digest')
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=digest:
            raise ValueError('Missing or changed input: '+name)
    # Build outputs are expected; additional source/content inputs are not.
    for base in ('Plugins/DaedalusLink','Source'):
        for path in (destination/base).rglob('*'):
            relative=path.relative_to(destination).as_posix()
            parts=path.relative_to(destination/base).parts
            if any(x in ('Binaries','Intermediate','Saved','__pycache__') for x in parts):continue
            if path.is_file() and relative not in expected:
                raise ValueError('Unrecorded input: '+relative)
    return {'source_head':manifest['source_head'],'plugin_files':len(files),
            'generated_host_files':len(generated),'verified':True}

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
    project.write_text(json.dumps({'FileVersion':3,'Modules':[{'Name':'HostProject','Type':'Runtime','LoadingPhase':'Default'}],
                                  'Plugins':[{'Name':'DaedalusLink','Enabled':True}]},indent=2))
    scaffold={
        'Source/HostProject.Target.cs':'using UnrealBuildTool; public class HostProjectTarget:TargetRules { public HostProjectTarget(TargetInfo Target):base(Target) { Type=TargetType.Game; DefaultBuildSettings=BuildSettingsVersion.Latest; IncludeOrderVersion=EngineIncludeOrderVersion.Latest; ExtraModuleNames.Add("HostProject"); } }\n',
        'Source/HostProjectEditor.Target.cs':'using UnrealBuildTool; public class HostProjectEditorTarget:TargetRules { public HostProjectEditorTarget(TargetInfo Target):base(Target) { Type=TargetType.Editor; DefaultBuildSettings=BuildSettingsVersion.Latest; IncludeOrderVersion=EngineIncludeOrderVersion.Latest; ExtraModuleNames.Add("HostProject"); } }\n',
        'Source/HostProject/HostProject.Build.cs':'using UnrealBuildTool; public class HostProject:ModuleRules { public HostProject(ReadOnlyTargetRules Target):base(Target) { PCHUsage=PCHUsageMode.UseExplicitOrSharedPCHs; PublicDependencyModuleNames.AddRange(new string[]{"Core","CoreUObject","Engine","DaedalusLink"}); } }\n',
        'Source/HostProject/HostProject.cpp':'#include "Modules/ModuleManager.h"\nIMPLEMENT_PRIMARY_GAME_MODULE(FDefaultGameModuleImpl,HostProject,"HostProject");\n'
    }
    generated={}
    for relative,text in scaffold.items():
        target=destination/relative;target.parent.mkdir(parents=True,exist_ok=True)
        raw=text.encode('utf-8');target.write_bytes(raw);generated[relative]=hashlib.sha256(raw).hexdigest()
    (destination/'source-manifest.json').write_text(json.dumps({'source_head':sha,'files':inputs,
        'tracked_file_count':len(inputs),'overlays':[],'generated_host_files':generated,
        'project_sha256':hashlib.sha256(project.read_bytes()).hexdigest()},indent=2))
    print(json.dumps({'project':str(project),'source_head':sha,'files':len(inputs),
                      'editor_target':'HostProjectEditor','game_target':'HostProject'}))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('repo',type=Path,nargs='?');parser.add_argument('destination',type=Path,nargs='?')
    parser.add_argument('--verify',type=Path,metavar='HOST')
    args=parser.parse_args()
    if args.verify:
        if args.repo or args.destination:parser.error('--verify takes no positional arguments')
        print(json.dumps(verify(args.verify)))
    else:
        if not args.repo or not args.destination:parser.error('repo and fresh destination required')
        snapshot(args.repo,args.destination)
