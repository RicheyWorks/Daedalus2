# SPDX-License-Identifier: MIT
"""Dry-run the wake relay against a fake log. No network, no state writes."""
from pathlib import Path
import json,os,shutil,subprocess,tempfile,unittest
PS=shutil.which('powershell.exe') or shutil.which('pwsh')
RELAY=Path(__file__).resolve().parents[1]/'wake-relay'/'wake-relay.ps1'
@unittest.skipUnless(PS,'requires PowerShell')
class WakeRelayTest(unittest.TestCase):
    def test_direct_messages_to_wake_bots_are_relayed_from_any_sender(self):
        lines=[
            {'id':'1','ts':'t','from':'pootscoot-coordination','to':'blender-boss','type':'note','body':{'text':'ping'}},
            {'id':'2','ts':'t','from':'buffffff','to':'hephaestus','type':'note','body':{'text':'grok to grok'}},
            {'id':'3','ts':'t','from':'codex-play-guard','to':'team-codex','type':'note','body':{'text':'codex to codex'}},
            {'id':'4','ts':'t','from':'unreal-team','to':'2hot2trot-x','type':'note','body':{'text':'wildcard'}},
            {'id':'5','ts':'t','from':'prometheus','to':'prometheus','type':'note','body':{'text':'self'}},
            {'id':'6','ts':'t','from':'blender-boss-linktest','to':'blender-boss','type':'note','body':{'text':'linktest'}},
            {'id':'7','ts':'t','from':'ruffff-relay-test','to':'ruffff','type':'note','body':{'text':'relay test'}},
            {'id':'8','ts':'t','from':'pootscoot-coordination','to':'*','type':'note','body':{'text':'broadcast'}},
            {'id':'9','ts':'t','from':'pythagoras','to':'prometheus','type':'note','body':{'text':'grok to grok'}},
        ]
        with tempfile.TemporaryDirectory() as folder:
            Path(folder,'log.jsonl').write_text(''.join(json.dumps(l)+'\n' for l in lines)+'not json\n',encoding='utf-8')
            out=subprocess.run([PS,'-NoProfile','-ExecutionPolicy','Bypass','-File',str(RELAY),'-LinkFolder',folder,'-DryRun'],capture_output=True,text=True,timeout=60).stdout
            payload=json.loads([l for l in out.splitlines() if l.startswith('{')][-1])
            self.assertEqual([m['id'] for m in payload['messages']],['1','2','4','9'])
            self.assertFalse(Path(folder,'grok-relay.state').exists())
    def test_overrides_route_to_own_webhook_and_flat_config_still_works(self):
        lines=[{'id':'1','ts':'t','from':'codex','to':'blender-boss','type':'note','body':{'text':'a'}},
               {'id':'2','ts':'t','from':'codex','to':'2hot2trot','type':'note','body':{'text':'b'}}]
        for cfg,want in [({'url':'u','key':'k','header':'h','prefix':''},{'default':['1','2']}),
                         ({'url':'u','key':'k','header':'h','prefix':'','overrides':{'2hot2trot':{'url':'v','key':'k','header':'h','prefix':''}}},{'default':['1'],'2hot2trot':['2']})]:
            with tempfile.TemporaryDirectory() as folder:
                Path(folder,'log.jsonl').write_text(''.join(json.dumps(l)+'\n' for l in lines),encoding='utf-8')
                Path(folder,'relay-webhook.json').write_text(json.dumps(cfg),encoding='utf-8')
                out=subprocess.run([PS,'-NoProfile','-ExecutionPolicy','Bypass','-File',str(RELAY),'-LinkFolder',folder,'-DryRun'],capture_output=True,text=True,timeout=60).stdout
                routes=json.loads([l for l in out.splitlines() if l.startswith('{')][-1])['routes']
                self.assertEqual({k:(v if isinstance(v,list) else [v]) for k,v in routes.items()},want)
if __name__=='__main__': unittest.main()