import ntpath
import unittest

from tools.unreal_mcp.material_capture_paths import (
    PROJECT, ProjectPathHeld, canonical_project_path,
)


class MaterialCapturePathTests(unittest.TestCase):
    def test_absolute_project(self):
        self.assertEqual(canonical_project_path(PROJECT, lambda value: value), PROJECT)

    def test_actual_unreal_relative_profile(self):
        reported = "../../../../../../Unreal/DaedalusRealm/DaedalusRealm.uproject"
        base = "C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64"
        seen = []

        def resolve(value):
            seen.append(value)
            return ntpath.normpath(ntpath.join(base, value))

        self.assertEqual(canonical_project_path(reported, resolve), PROJECT)
        self.assertEqual(seen, [reported])

    def test_windows_separators(self):
        self.assertEqual(canonical_project_path(PROJECT, lambda _: PROJECT.replace("/", "\\")), PROJECT)

    def test_other_project_and_wrong_base_refuse(self):
        for path in ("C:/Other/DaedalusRealm.uproject", "D:/Unreal/DaedalusRealm/DaedalusRealm.uproject"):
            with self.subTest(path=path), self.assertRaises(ProjectPathHeld):
                canonical_project_path(PROJECT, lambda _: path)

    def test_unresolved_relative_refuses(self):
        with self.assertRaises(ProjectPathHeld):
            canonical_project_path("../DaedalusRealm.uproject", lambda value: value)

    def test_invalid_input_does_not_call_resolver(self):
        for value in (None, True, "", "x" * 1025, "a\x00b"):
            with self.subTest(value=repr(value)), self.assertRaises(ProjectPathHeld):
                canonical_project_path(value, lambda _: self.fail("Invalid input reached resolver"))

    def test_invalid_resolver_result_refuses(self):
        for value in (None, True, "", "x" * 1025, "a\x00b"):
            with self.subTest(value=repr(value)), self.assertRaises(ProjectPathHeld):
                canonical_project_path(PROJECT, lambda _: value)

    def test_missing_or_failed_resolver_refuses(self):
        with self.assertRaises(ProjectPathHeld):
            canonical_project_path(PROJECT, None)

        def fail(_):
            raise OSError("unavailable")

        with self.assertRaises(ProjectPathHeld):
            canonical_project_path(PROJECT, fail)


if __name__ == "__main__":
    unittest.main()
