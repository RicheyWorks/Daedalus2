# SPDX-License-Identifier: MIT
"""Healthy baseline, then five assertion-only source mutants, all in memory.

Import, compile, fixture, and baseline failures cannot count as mutant rejection.
The actual remote-outcome fixtures use stand-ins and create no socket or editor.
"""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest import mock

UNIT_PATH = Path(__file__).with_name("remote_outcome_unknown_test.py")
SPEC = importlib.util.spec_from_file_location("remote_outcome_fixtures", UNIT_PATH)
FIXTURES = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(FIXTURES)

MUTANTS = (
    ("automatic_local_replay", 'if box.get("dispatch_attempted"):', "if False:",
     "test_oserror_after_remote_effect_never_replays_locally"),
    ("attempt_before_wrap", 'wrapped = _wrap(code)\n        box["dispatch_attempted"] = True',
     'box["dispatch_attempted"] = True\n        wrapped = _wrap(code)',
     "test_wrap_failure_occurs_before_attempt_and_can_fall_back"),
    ("cleanup_without_lock_ownership", 'if got_lock:\n            try:\n                if _remote["rx"] is not None:',
     'if True:\n            try:\n                if _remote["rx"] is not None:',
     "test_remote_lock_error_falls_back_without_touching_another_owners_client"),
    ("timeout_validation_removed", "if not math.isfinite(timeout) or timeout < 0:", "if False:",
     "test_invalid_timeout_is_rejected_before_starting_worker"),
    ("uncertainty_not_cached", 'reply.get("status") == "ok" or\n                            reply.get("code") == RemoteExecutionUncertain.code',
     'reply.get("status") == "ok"',
     "test_uncertain_request_id_retry_returns_terminal_without_new_remote_effect"),
)


class MutationInfrastructureError(RuntimeError):
    pass


class RemoteOutcomeMutationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        baseline = unittest.TestResult()
        unittest.defaultTestLoader.loadTestsFromTestCase(FIXTURES.RemoteOutcomeTests).run(baseline)
        if baseline.errors:
            raise MutationInfrastructureError("healthy baseline infrastructure failed: %s" % baseline.errors)
        if baseline.testsRun < 20 or baseline.skipped or not baseline.wasSuccessful():
            raise AssertionError("unhealthy baseline: %d tests, failures=%s, skipped=%s" %
                                 (baseline.testsRun, baseline.failures, baseline.skipped))
        print("PASS healthy baseline %d/%d" % (baseline.testsRun, baseline.testsRun))

    def reject_mutant(self, label, before, after, fixture_method):
        source = FIXTURES.BRIDGE.read_text(encoding="utf-8")
        count = source.count(before)
        if count != 1:
            raise MutationInfrastructureError("%s: expected exactly one source replacement, found %d" % (label, count))
        changed = source.replace(before, after)
        original_load = FIXTURES.load_file

        def mutated_load(path, name):
            if Path(path) != FIXTURES.BRIDGE:
                return original_load(path, name)
            module = types.ModuleType(name)
            module.__file__ = str(path)
            exec(compile(changed, str(path), "exec"), module.__dict__)
            return module

        result = unittest.TestResult()
        with mock.patch.object(FIXTURES, "load_file", mutated_load):
            unittest.TestSuite([FIXTURES.RemoteOutcomeTests(fixture_method)]).run(result)
        if result.testsRun != 1 or result.errors or result.skipped:
            raise MutationInfrastructureError("%s: fixture infrastructure failed: tests=%d, errors=%s, skipped=%s" %
                                              (label, result.testsRun, result.errors, result.skipped))
        self.assertTrue(result.failures, label + ": mutant survived the actual fixture assertions")


def mutant_test(mutant):
    def test(self):
        self.reject_mutant(*mutant)
    return test


for mutant in MUTANTS:
    setattr(RemoteOutcomeMutationTests, "test_" + mutant[0], mutant_test(mutant))


if __name__ == "__main__":
    program = unittest.main(verbosity=2, exit=False)
    result = program.result
    passed = max(0, result.testsRun - len(result.failures) - len(result.errors))
    print("%d/%d" % (passed, result.testsRun))
    sys.exit(0 if result.wasSuccessful() else 1)
