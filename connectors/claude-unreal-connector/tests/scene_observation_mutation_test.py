# SPDX-License-Identifier: MIT
"""Seven source-only mutants must fail the actual scene observation fixtures.

Production source is changed only in memory. A mutant is rejected only through
assertion failures, never through import errors or broken fixture execution.
"""
import importlib.util
from pathlib import Path
import types
import unittest
from unittest import mock


UNIT_PATH = Path(__file__).with_name("scene_observation_test.py")
SPEC = importlib.util.spec_from_file_location("scene_observation_fixtures", UNIT_PATH)
FIXTURES = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(FIXTURES)

MUTANTS = (
    ("legacy_rounding", FIXTURES.BRIDGE,
     "nd = None if precise else 2", "nd = 2",
     "test_precise_004_drift_regression_rejects_legacy_rounding_mutant"),
    ("strict_json_gate_removed", FIXTURES.SCENE,
     "json.dumps(value, allow_nan=False)", "pass",
     "test_nonfinite_native_values_are_unavailable_and_strict_json_safe"),
    ("native_world_repr_ignored", FIXTURES.SCENE,
     "repr(world)", "'same-repr'",
     "test_same_path_new_native_repr_changes_epoch_and_retains_only_values"),
    ("folder_prefix_collision", FIXTURES.SCENE,
     'actor_folder.startswith(folder.rstrip("/") + "/")',
     "actor_folder.startswith(folder)",
     "test_snapshot_folder_boundary_and_page_sequence"),
    ("last_page_claims_complete", FIXTURES.SCENE,
     "complete=offset == 0 and len(values) == len(matches) and not errors",
     "complete=end == len(matches) and not errors",
     "test_snapshot_folder_boundary_and_page_sequence"),
    ("stale_context_guard_removed", FIXTURES.SCENE,
     'if context != params["context"]:', "if False:",
     "test_each_context_field_is_required_to_match_exactly"),
    ("numeric_bool_allowed", FIXTURES.SCENE,
     "isinstance(value, bool) or ", "",
     "test_verify_schema_errors_precede_all_native_reads"),
)


class SceneObservationMutationTests(unittest.TestCase):
    def reject_mutant(self, label, target, before, after, fixture_method):
        source = target.read_text(encoding="utf-8")
        self.assertEqual(source.count(before), 1,
                         "%s must replace exactly one production expression" % label)
        changed = source.replace(before, after)
        original_load = FIXTURES.load_file

        def mutated_load(path, name):
            if Path(path) != target:
                return original_load(path, name)
            module = types.ModuleType(name)
            module.__file__ = str(path)
            exec(compile(changed, str(path), "exec"), module.__dict__)
            return module

        result = unittest.TestResult()
        suite = unittest.TestSuite([FIXTURES.SceneObservationTests(fixture_method)])
        with mock.patch.object(FIXTURES, "load_file", mutated_load):
            suite.run(result)
        self.assertEqual(result.testsRun, 1, label + ": fixture did not execute")
        self.assertEqual(result.errors, [], label + ": fixture errors cannot reject a mutant")
        self.assertTrue(result.failures, label + ": mutant survived the fixture assertions")


def mutant_test(mutant):
    def test(self):
        self.reject_mutant(*mutant)
    return test


for mutant in MUTANTS:
    setattr(SceneObservationMutationTests, "test_" + mutant[0], mutant_test(mutant))


if __name__ == "__main__":
    unittest.main(verbosity=2)
