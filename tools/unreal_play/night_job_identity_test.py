# SPDX-License-Identifier: MIT
import tempfile
from pathlib import Path
import unittest
import night_run


class JobIdentityTest(unittest.TestCase):
    def test_previous_success_cannot_complete_new_job(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            (root/'build-old.exit').write_text('done 0')
            with self.assertRaises(TimeoutError):
                night_run.wait_terminal('build-new',0,root)
            (root/'build-new.exit').write_text('done 7')
            self.assertEqual(night_run.wait_terminal('build-new',0,root),7)

    def test_log_words_are_not_terminal_evidence(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            (root/'job-new.log').write_text('DONE 0\nBUILD OK build-new\n')
            with self.assertRaises(TimeoutError):
                night_run.wait_terminal('job-new',0,root)
            (root/'job-new.exit').write_text('done rubbish')
            with self.assertRaises(RuntimeError):
                night_run.wait_terminal('job-new',0,root)

    def test_job_id_cannot_escape_marker_directory(self):
        with self.assertRaises(ValueError):
            night_run.wait_terminal('../other',0,Path('.'))


if __name__=='__main__':
    unittest.main()
