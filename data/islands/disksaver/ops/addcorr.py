f=r'C:\Users\730ri\projects\bot-team\BOARD\LESSONS-LEARNED-UNREAL.md'
C={"Multi-part Blender assets":("generators join parts before export + fix script loads exact asset path and finds actors by mesh path (Daedalus2 32643875, 5d62ba51)","FIXED"),
"Art-queue watcher exported":("one .blend per asset with a collection named after it before READY; verify.ps1 checks SHIPPED tris and size (4d39a7dd)","FIXED"),
"Parent materials without":("own tint parents M_DS_Tint / M_DS_TintWater with Color/Roughness/Opacity params, instances re-parented (32643875)","FIXED"),
"RAM guard stopped the hook pass":("ds_canopy_ue.py + run_canopy.py batched, resumable reimport; idempotent ds_finish_ue.py hook pass (5d62ba51); verified in round 4","FIXED"),
"Nested powershell -Command":("all disk-saver commands now run from files (-File / python file); link posts via disk-saver-post.py","FIXED"),
"Night lighting made the hero":("ds_capture_ue.py + ds_capture_cleanup_ue.py + turn5.ps1 (206dc781, c0523deb, 13acf17d) written and dry-run; not yet run in an editor turn","OPEN")}
raw=open(f,'rb').read(); crlf=b'\r\n' in raw; t=raw.decode('utf-8'); nl='\r\n' if crlf else '\n'
lines=t.split(nl); out=[]; cur=None; n=0
for i,l in enumerate(lines):
    out.append(l)
    if l.startswith('## disk-saver |'):
        cur=next((k for k in C if k in l),None)
    elif cur and l.startswith('- Evidence') and not (i+1<len(lines) and lines[i+1].startswith('- Correction applied')):
        out.append('- Correction applied: '+C[cur][0]); out.append('- Status: '+C[cur][1]); cur=None; n+=1
    elif l.startswith('## '): cur=None
open(f,'wb').write(nl.join(out).encode('utf-8')); print('added',n)
