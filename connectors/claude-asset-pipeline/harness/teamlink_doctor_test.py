# SPDX-License-Identifier: MIT
import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from asset_pipeline.teamlink import Link

class DoctorTest(unittest.TestCase):
    def link(self, missing=None):
        link=Link("team codex")
        calls=[]
        replies={"/health":{"ok":True,"last":42,"pid":123,"uptime_s":7},"/locks":{"unreal":{"holder":"claude"}},
                 "/inbox?me=team+codex":{"messages":[{"id":5,"body":{"secret":"do not print"}}]},
                 "/pending-summary?me=team+codex":{"count":0,"ids":[],"omitted":0}}
        if missing:replies[missing]=None
        def call(method,path,*args,**kwargs):
            calls.append((method,path));return replies.get(path)
        link._call=call
        return link,calls,replies
    def test_summary_is_read_only_and_omits_bodies(self):
        link,calls,_=self.link();r=link.doctor()
        self.assertTrue(r['ok']);self.assertEqual(r['last_id'],42)
        self.assertEqual(r['unacked_inbox'],{'count':1,'ids':[5],'omitted':0})
        self.assertEqual(r['broker_pid'],123)
        self.assertEqual(len(calls),4);self.assertTrue(all(m=='GET' for m,p in calls))
        self.assertNotIn('secret',str(r))
    def test_broker_summary_matches_pending_without_bodies(self):
        from asset_pipeline.teamlink import Broker
        import tempfile
        with tempfile.TemporaryDirectory() as folder:
            broker=Broker(folder)
            for i in range(15): broker.send("claude", "codex", "note", {"text":"large body"*1000})
            broker.send("claude", "other", "note", {})
            broker.ack("codex",1)
            before=broker.last
            summary=broker.pending_summary("codex")
            expected=[m["id"] for m in broker.pending("codex")]
            self.assertEqual(summary['count'],len(expected))
            self.assertEqual(summary['ids'],expected[-10:])
            self.assertEqual(summary['omitted'],len(expected)-10)
            self.assertEqual(before,broker.last)
            self.assertNotIn('large body',str(summary))

    def test_actual_http_doctor_uses_summary(self):
        from asset_pipeline.teamlink import Broker,make_handler,ThreadingHTTPServer
        import tempfile,threading,json
        with tempfile.TemporaryDirectory() as folder:
            broker=Broker(folder)
            broker.send('claude','codex','request',{'text':'body must not appear'})
            server=ThreadingHTTPServer(('127.0.0.1',0),make_handler(broker))
            thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
            try:
                before=broker.last
                report=Link('codex',server.server_port).doctor()
                self.assertTrue(report['ok'],report)
                self.assertEqual(report['pending_delivery']['count'],1)
                self.assertNotIn('body must not appear',json.dumps(report))
                self.assertEqual(before,broker.last)
            finally:
                server.shutdown();server.server_close();thread.join()

    def test_partial_failure_is_unknown_not_empty(self):
        link,_,_=self.link('/inbox?me=team+codex');r=link.doctor()
        self.assertFalse(r['ok']);self.assertTrue(r['broker_up'])
        self.assertIsNone(r['unacked_inbox']);self.assertIn('inbox',r['unavailable'])
    def test_old_broker_and_down(self):
        link,_,replies=self.link();replies['/health']={'ok':True,'last':1}
        self.assertTrue(link.doctor()['ok']);self.assertIsNone(link.doctor()['broker_pid'])
        replies['/health']=None
        self.assertFalse(link.doctor()['broker_up'])
if __name__=='__main__':unittest.main(verbosity=2)
