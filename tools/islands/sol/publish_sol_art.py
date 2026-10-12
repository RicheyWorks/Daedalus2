"""Stage owned files and add only SOL rows using the existing queue parser.

Refuses conflicting names/files or a concurrent queue edit; never ships into an editor.
"""
import hashlib
import json
import pathlib
import shutil
import sys
from validate_sol_art import validate, ROOT
from asset_pipeline import artqueue

folder = pathlib.Path(sys.argv[1]); art = folder.parent
manifest = validate(folder)
source = json.loads((folder/'blend-source-validation.json').read_text())
if source['passed'] != 20: raise ValueError('source verification incomplete')
queue = art/'QUEUE.md'; before = queue.read_bytes(); text = before.decode('utf8')
existing, _ = artqueue.parse(text); names={r['asset'] for r in existing}
if any(a['asset'] in names for a in manifest['assets']):
    raise ValueError('SOL rows already exist; inspect rather than replay')
for a in manifest['assets']:
    for src, dest in [(pathlib.Path(a['blend']),art/a['kind']/(a['asset']+'.blend')),
                      (pathlib.Path(a['glb']),art/'glb'/(a['asset']+'.glb'))]:
        dest.parent.mkdir(exist_ok=True)
        if dest.exists():
            if dest.read_bytes()!=src.read_bytes(): raise ValueError('conflicting owned path '+str(dest))
        else:
            with src.open('rb') as inp, dest.open('xb') as out: shutil.copyfileobj(inp,out)
    text = artqueue.add_row(text,a['asset'],'READY',
         f"Sol Island / Sol Reach; {a['archetype']} variant {a['variant']}/25; {a['triangles']} tris; {a['materials']} slots; validated Blender/file only")
if queue.read_bytes()!=before: raise RuntimeError('Queue changed concurrently; files staged, rows not written. Wait and retry.')
temporary=art/'QUEUE.sol-staging.tmp'
temporary.write_text(text,encoding='utf8',newline='')
if queue.read_bytes()!=before: raise RuntimeError('Queue changed before replace; no overwrite')
temporary.replace(queue)
after=queue.read_bytes()
receipt={'assets':500,'status':'READY_NOT_IMPORTED','queue_before_sha256':hashlib.sha256(before).hexdigest(),
         'queue_after_sha256':hashlib.sha256(after).hexdigest(),'folder':str(folder)}
(folder/'queue-receipt.json').write_text(json.dumps(receipt,indent=2))
print(json.dumps(receipt))
