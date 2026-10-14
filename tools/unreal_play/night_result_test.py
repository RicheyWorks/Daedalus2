# SPDX-License-Identifier: MIT
import unittest
import tempfile
from unittest.mock import patch
import subprocess
import json
from pathlib import Path
import night_run
from night_run import assess_run, require_stage, parse_options


class OutcomeTest(unittest.TestCase):
    def test_receipt_archives_do_not_collide_and_latest_matches(self):
        with tempfile.TemporaryDirectory() as folder:
            latest=Path(folder)/'latest.json'
            one=night_run.publish_receipt({'total':'TOTAL 1/1'},folder,str(latest))
            two=night_run.publish_receipt({'total':'TOTAL 2/2'},folder,str(latest))
            self.assertNotEqual(one,two)
            self.assertEqual(json.loads(Path(one).read_text())['total'],'TOTAL 1/1')
            self.assertEqual(json.loads(latest.read_text()),json.loads(Path(two).read_text()))

    def test_powershell_failure_cannot_be_read_as_successful_output(self):
        with patch.object(night_run.subprocess,'run',return_value=subprocess.CompletedProcess([],7,'BUILD OK stale','failed')):
            with self.assertRaises(RuntimeError):night_run.ps('fixture')

    def test_copy_failure_prevents_reload_dispatch(self):
        with patch.object(night_run,'ps',side_effect=RuntimeError('copy failed')), patch.object(night_run.wire,'call') as call:
            with self.assertRaises(RuntimeError):night_run.hot_copy()
            call.assert_not_called()

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
