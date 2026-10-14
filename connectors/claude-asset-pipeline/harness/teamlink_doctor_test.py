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
                 "/pending?me=team+codex":{"messages":[]}}
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
    def test_large_history_is_bounded(self):
        link,_,replies=self.link()
        replies['/pending?me=team+codex']={'messages':[{'id':i} for i in range(15000)]}
        r=link.doctor()['pending_outgoing']
        self.assertEqual(r['count'],15000);self.assertEqual(len(r['ids']),10)
        self.assertEqual(r['omitted'],14990)

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
