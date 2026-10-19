# SPDX-License-Identifier: MIT
"""Unexecuted, pure regex fixtures for the fresh disposable project filter."""
import re
import unittest

from tools.unreal_mcp import blueprint_descriptor_scope as scope


class BlueprintDescriptorScopeTests(unittest.TestCase):
    def blocked(self, name):
        pattern = scope.BLOCKED_NAMES_PATTERN
        self.assertTrue(pattern.startswith("/") and pattern.endswith("/"))
        # Match Epic's slash-delimited regex FindNext behavior, not fullmatch.
        return re.search(pattern[1:-1], name) is not None

    def test_exact_six_flow_methods_and_toolset_class_remain_enabled(self):
        expected = {"create", "compile_blueprint", "add_variable", "list_variables",
                    "list_graphs", "get_default_object"}
        self.assertEqual(expected, set(scope.REQUIRED_METHODS))
        self.assertEqual(6, len(scope.REQUIRED_METHODS))
        self.assertFalse(self.blocked(scope.TOOLSET))
        for method in expected:
            with self.subTest(method=method):
                self.assertFalse(self.blocked(scope.TOOLSET + "." + method))

    def test_unrelated_toolsets_and_methods_keep_their_existing_scope(self):
        for name in (
            "editor_toolset.toolsets.asset.AssetTools",
            "editor_toolset.toolsets.asset.AssetTools.save_assets",
            "editor_toolset.toolsets.object.ObjectTools.get_properties",
            "editor_toolset.toolsets.object.ObjectTools.set_properties",
            "codex_diagnostics.BlueprintCDODiagnostics.inspect_context",
            "codex_diagnostics.BlueprintCDODiagnostics.set_properties",
            "automation_toolset.toolsets.automation.AutomationTools.run_tests",
        ):
            with self.subTest(name=name):
                self.assertFalse(self.blocked(name))

    def test_other_blueprint_methods_and_required_name_extensions_are_blocked(self):
        for method in ("remove_variable", "remove_graph", "get_function",
                       "create_extra", "create.more", "Create",
                       "compile_blueprint_extra", "add_variable2",
                       "list_variables_extra", "list_graphs_extra",
                       "get_default_object_extra"):
            with self.subTest(method=method):
                self.assertTrue(self.blocked(scope.TOOLSET + "." + method))

    def test_anchors_preserve_prefixes_similar_classes_and_empty_method_suffix(self):
        for name in (
            "prefix." + scope.TOOLSET + ".remove_variable",
            scope.TOOLSET + "Extra.remove_variable",
            scope.TOOLSET.replace(".blueprint.", ".blueprints.") + ".remove_variable",
            scope.TOOLSET.replace(".BlueprintTools", ".OtherBlueprintTools") + ".remove_variable",
            scope.TOOLSET.replace("editor_toolset.", "editor_toolsetX") + ".remove_variable",
            scope.TOOLSET + ".",
        ):
            with self.subTest(name=name):
                self.assertFalse(self.blocked(name))

    def test_fragment_contains_only_the_project_section_and_one_quoted_append(self):
        fragment = scope.fresh_project_ini_fragment()
        self.assertEqual(
            ["[/Script/ToolsetRegistry.ToolsetRegistrySettings]",
             '+BlockedNames="' + scope.BLOCKED_NAMES_PATTERN + '"'],
            fragment.splitlines(),
        )
        self.assertTrue(fragment.endswith("\n"))
        self.assertEqual(1, fragment.count("+BlockedNames="))
        self.assertNotIn("AllowedNames", fragment)
        self.assertNotRegex(fragment, r"(?i)timeout|global|http|endpoint")


if __name__ == "__main__":
    unittest.main()
