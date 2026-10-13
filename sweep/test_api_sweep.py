"""Readiness retries must not turn real API errors into passing checks."""
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("api_sweep", Path(__file__).with_name("api-sweep.py"))
sweep = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sweep)


class FingerprintReadinessTest(unittest.TestCase):
    def test_warming_then_success(self):
        with patch.object(sweep, "call", side_effect=[
                (503, {"kind": "classifier-warming"}), (200, {"agrees": True})]) as call, \
                patch.object(sweep.time, "sleep") as sleep:
            self.assertEqual((200, {"agrees": True}), sweep.fingerprint_when_ready("/fingerprint"))
            self.assertEqual(2, call.call_count)
            sleep.assert_called_once_with(0.5)

    def test_unready_classifier_still_fails_after_bounded_attempts(self):
        response = (503, {"kind": "classifier-warming"})
        with patch.object(sweep, "call", return_value=response) as call, \
                patch.object(sweep.time, "sleep") as sleep:
            self.assertEqual(response, sweep.fingerprint_when_ready("/fingerprint"))
            self.assertEqual(20, call.call_count)
            self.assertEqual(19, sleep.call_count)

    def test_other_errors_are_not_retried(self):
        for response in [(503, {"kind": "unavailable"}), (503, "unavailable"),
                         (500, {"kind": "classifier-warming"}), (404, {})]:
            with self.subTest(response=response), \
                    patch.object(sweep, "call", return_value=response) as call, \
                    patch.object(sweep.time, "sleep") as sleep:
                self.assertEqual(response, sweep.fingerprint_when_ready("/fingerprint"))
                call.assert_called_once()
                sleep.assert_not_called()


if __name__ == "__main__":
    unittest.main()
