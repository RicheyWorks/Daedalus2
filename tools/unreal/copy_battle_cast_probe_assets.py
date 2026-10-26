"""Copy existing cast assets to a fresh private probe destination, preserving source bytes."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('project',type=Path)
a=p.parse_args();source=a.source.resolve();host=a.project.resolve().parent
destination=host/'Content/Daedalus/Art/Cast'
if destination.exists():raise ValueError('Probe cast destination must be fresh; no assets are overwritten')
folders=sorted(path for path in source.iterdir() if path.is_dir() and path.name.startswith('Mob_Gallery_'))
if not folders:raise ValueError('No imported Gallery casts found')
files={};mesh_packages={}
for folder in folders:
    meshes=list(folder.rglob(folder.name+'.uasset'))
    if len(meshes)!=1:raise ValueError('Expected exactly one cast mesh asset: '+folder.name)
    relative=meshes[0].relative_to(source).with_suffix('').as_posix()
    mesh_packages[folder.name]='/Game/Daedalus/Art/Cast/'+relative
    for path in sorted(folder.rglob('*')):
        if not path.is_file() or path.suffix not in ('.uasset','.uexp','.ubulk'):continue
        path.resolve().relative_to(source)
        target=destination/path.relative_to(source)
        target.parent.mkdir(parents=True,exist_ok=True)
        before=hashlib.sha256(path.read_bytes()).hexdigest()
        shutil.copy2(path,target)
        if before!=hashlib.sha256(target.read_bytes()).hexdigest() or before!=hashlib.sha256(path.read_bytes()).hexdigest():
            raise ValueError('Source changed during copy: '+str(path))
        files[target.relative_to(host/'Content').as_posix()]=before
manifest={'source':str(source),'cast_ids':[path.name for path in folders],'mesh_packages':mesh_packages,'files':files}
(host/'cast-art-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
print('CAST_ART_COPY_PASS',len(folders),len(files),'source files untouched')
