# SPDX-License-Identifier: MIT
import copy
import unittest
from import_cast import terminal_counts


class TerminalTest(unittest.TestCase):
    def fixture(self,count=500):
        plan=[('Mob_Test_%d'%i,'unused','a'*64) for i in range(count)]
        reply={'error':None,'yielded':['tail']*200,'result':{'planned':count,
               'counts':{'imported':count,'skipped':0,'failed':0},
               'assets':[{'id':row[0],'sha256':row[2],'status':'imported'} for row in plan]}}
        return plan,reply

    def test_500_terminal_rows_are_independent_of_200_progress_lines(self):
        plan,reply=self.fixture()
        self.assertEqual(terminal_counts(reply,plan)['imported'],500)

    def test_missing_or_reordered_identities_refused(self):
        plan,reply=self.fixture(2)
        for rows in (reply['result']['assets'][:1],list(reversed(reply['result']['assets']))):
            malformed=copy.deepcopy(reply);malformed['result']['assets']=rows
            with self.assertRaises(ValueError):terminal_counts(malformed,plan)

    def test_hash_or_count_mismatch_refused(self):
        plan,reply=self.fixture(2)
        reply['result']['assets'][0]['sha256']='b'*64
        with self.assertRaises(ValueError):terminal_counts(reply,plan)
        plan,reply=self.fixture(2);reply['result']['counts']['imported']=True
        with self.assertRaises(ValueError):terminal_counts(reply,plan)


if __name__=='__main__':unittest.main()
