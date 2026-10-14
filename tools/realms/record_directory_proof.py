"""Record successful realm-discovery checks with source and log hashes, not release claims."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

p=argparse.ArgumentParser()
for name in ('focused','verify','output'):p.add_argument('--'+name,required=True,type=Path)
a=p.parse_args();repo=Path(__file__).resolve().parents[2]
paths=['daedalus-server/src/main/java/com/daedalus/server/'+name for name in (
    'service/RealmDirectoryService.java','controller/RealmDirectoryController.java','config/ProdSecurityConfig.java')]
paths += ['daedalus-server/src/test/java/com/daedalus/server/'+name for name in (
    'service/RealmDirectoryServiceTest.java','controller/RealmDirectoryControllerTest.java',
    'service/OceanHostHttpRestartTest.java','config/ProdAuthPostureTest.java')]
if subprocess.run(['git','ls-files','--error-unmatch',*paths],cwd=repo,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode \
        or subprocess.run(['git','diff','--quiet','HEAD','--',*paths],cwd=repo).returncode:
    raise ValueError('Commit checked source before recording proof')
proof={'source_head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip(),
       'source_sha256':{name:hashlib.sha256((repo/name).read_bytes()).hexdigest() for name in paths},
       'scope':'Authenticated single-server provider discovery and advertised Ocean chunk read. No travel, Unreal load or public hosting claim.'}
for key,path in [('focused',a.focused),('verify',a.verify)]:
    text=path.read_text(encoding='utf-8-sig',errors='replace')
    if '[INFO] BUILD SUCCESS' not in text or '[INFO] BUILD FAILURE' in text:
        raise ValueError('Run did not pass: '+key)
    summary=re.findall(r'^\[INFO\] Tests run: (\d+), Failures: (\d+), Errors: (\d+), Skipped: (\d+)\s*$',text,re.M)
    if not summary or any(int(failure) or int(error) for _,failure,error,_ in summary):
        raise ValueError('Missing clean test summaries: '+key)
    match=re.search(r'Total time:\s*(?:(\d+):)?([\d.]+)\s*(min|s)',text)
    if not match:raise ValueError('Missing run timing: '+key)
    seconds=(int(match[1])*60+float(match[2])) if match[1] else float(match[2])*(60 if match[3]=='min' else 1)
    proof[key]={'seconds':seconds,'test_summary_counts':[int(row[0]) for row in summary],
                'log_sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
a.output.write_text(json.dumps(proof,indent=2)+'\n',encoding='utf-8')
print('REALM_DIRECTORY_PROOF_PASS',json.dumps({key:proof[key]['seconds'] for key in ('focused','verify')}))
