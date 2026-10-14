"""Record successful land API verification; no deployment or Unreal acceptance claim."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import xml.etree.ElementTree as ET

p=argparse.ArgumentParser()
p.add_argument('--verify',required=True,type=Path)
p.add_argument('--output',required=True,type=Path)
a=p.parse_args();repo=Path(__file__).resolve().parents[2]
paths=['daedalus-server/src/main/java/com/daedalus/server/'+s for s in (
    'controller/RealmLandController.java','service/RealmLandService.java','config/ProdSecurityConfig.java')]
paths+=['daedalus-server/src/test/java/com/daedalus/server/'+s for s in (
    'controller/RealmLandControllerTest.java','service/RealmLandServiceTest.java',
    'service/RealmLandHttpRestartTest.java','config/ProdAuthPostureTest.java')]
paths+=['daedalus-server/src/main/resources/application.yml']
if subprocess.run(['git','ls-files','--error-unmatch',*paths],cwd=repo,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode \
        or subprocess.run(['git','diff','--quiet','HEAD','--',*paths],cwd=repo).returncode:
    raise ValueError('Commit verified source before recording proof')
text=a.verify.read_text(encoding='utf-8-sig',errors='replace')
if '[INFO] BUILD SUCCESS' not in text or '[INFO] BUILD FAILURE' in text:raise ValueError('Verification did not pass')
rows=re.findall(r'^\[INFO\] Tests run: (\d+), Failures: (\d+), Errors: (\d+), Skipped: (\d+)\s*$',text,re.M)
if not rows or any(int(f) or int(e) or int(s) for _,f,e,s in rows):raise ValueError('Missing clean summaries')
timing=re.search(r'Total time:\s*(?:(\d+):)?([\d.]+)\s*(min|s)',text)
if not timing:raise ValueError('Missing timing')
seconds=int(timing[1])*60+float(timing[2]) if timing[1] else float(timing[2])*(60 if timing[3]=='min' else 1)
report=repo/'daedalus-server/target/surefire-reports/TEST-com.daedalus.server.service.RealmLandHttpRestartTest.xml'
suite=ET.parse(report).getroot()
if suite.get('tests')!='1' or any(int(suite.get(k,'0')) for k in ('errors','failures','skipped')):
    raise ValueError('HTTP restart test did not pass')
proof={'source_head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip(),
       'source_sha256':{s:hashlib.sha256((repo/s).read_bytes()).hexdigest() for s in paths},
       'scope':'Single-server JWT district reads, restart, stable identity after move, quotas and corrupt-file refusal. No Unreal import, ownership, mint or deployment proof.',
       'verify':{'seconds':seconds,'test_summary_counts':[int(row[0]) for row in rows],
                 'log_sha256':hashlib.sha256(a.verify.read_bytes()).hexdigest()},
       'http_restart_report_sha256':hashlib.sha256(report.read_bytes()).hexdigest(),
       'district_row_bound':100,'seed_encoding':'signed decimal int64 string'}
a.output.write_text(json.dumps(proof,indent=2)+'\n',encoding='utf-8')
print('LAND_API_PROOF_PASS',json.dumps(proof['verify']))
