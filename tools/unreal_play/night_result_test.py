# SPDX-License-Identifier: MIT
import unittest
import tempfile
from night_run import assess_run, require_stage, parse_options


class OutcomeTest(unittest.TestCase):
    def test_import_folders_do_not_consume_following_option_values(self):
        with tempfile.TemporaryDirectory() as folder:
            options=parse_options(['--import',folder,'--realms','PARCELS','--no-build'])
            self.assertEqual(options.imports,[folder])
            self.assertEqual(options.realms,['PARCELS'])
            self.assertTrue(options.no_build)

    def test_stage_requires_explicit_successful_terminal_result(self):
        for reply in (None,{}, {'result':{'realm':'WORLD-ZERO'}},
                      {'error':'','result':{'realm':'WORLD-ZERO'}}, {'error':None,'result':{}}):
            with self.assertRaises(RuntimeError): require_stage(reply,'fixture')
        self.assertEqual(require_stage({'error':None,'result':{'realm':'WORLD-ZERO'}},'fixture'),{'realm':'WORLD-ZERO'})

    def test_complete_suite_without_editor_errors_passes(self):
        self.assertEqual(assess_run('TOTAL 47/47\n',0,{'errors':0,'warnings':716})['exit_code'],0)

    def test_missing_total_is_unverified_even_without_fail_lines(self):
        self.assertEqual(assess_run('TOTAL ?\n',0,{'errors':0,'warnings':0})['status'],'unverified')

    def test_failures_and_editor_errors_propagate(self):
        for text,code,report in [('TOTAL 28/47',0,{'errors':0,'warnings':0}),
                                 ('TOTAL 47/47',1,{'errors':0,'warnings':0}),
                                 ('TOTAL 47/47',0,{'errors':5,'warnings':0}),
                                 ('FAIL stale\nTOTAL 47/47',0,{'errors':0,'warnings':0})]:
            self.assertEqual(assess_run(text,code,report)['exit_code'],1)

    def test_invalid_counts_and_unavailable_report_cannot_pass(self):
        for text,report in [('TOTAL 0/0',{'errors':0,'warnings':0}),
                            ('TOTAL 2/1',{'errors':0,'warnings':0}),
                            ('TOTAL 1/1\nTOTAL 1/1',{'errors':0,'warnings':0}),
                            ('TOTAL 1/1',None),('TOTAL 1/1',{'errors':False,'warnings':0})]:
            self.assertEqual(assess_run(text,0,report)['exit_code'],2)


if __name__=='__main__':unittest.main()
