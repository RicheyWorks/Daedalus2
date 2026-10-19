# SPDX-License-Identifier: MIT
"""A fresh-project Epic ToolsetRegistry filter for the owned Blueprint flow.

This module performs no I/O, registration, settings changes, or native calls.
Its fragment belongs only in a separately admitted disposable project's
Config/DefaultEditorPerProjectUserSettings.ini before editor startup. Preserve
existing project filters. It does not modify engine or user-wide settings.

Epic's NamePatternFilter strips surrounding slashes and uses regex FindNext.
Toolset.cpp applies BlockedNames independently to the toolset name and each
fully qualified method, then GetJsonSchema omits disabled methods. The anchored
pattern below leaves the toolset itself enabled and blocks only its methods
outside this finite flow. All other toolsets keep their existing filters.

The filter addresses descriptor size; it does not diagnose or repair the
underlying truncated HTTP transfer. Live filtered-schema qualification remains
necessary. Existing consumed requests and profiles must never be replayed or
rewritten to adopt this fragment.
"""

TOOLSET = "editor_toolset.toolsets.blueprint.BlueprintTools"
REQUIRED_METHODS = (
    "create", "compile_blueprint", "add_variable", "list_variables",
    "list_graphs", "get_default_object",
)
BLOCKED_NAMES_PATTERN = (
    "/^editor_toolset[.]toolsets[.]blueprint[.]BlueprintTools[.]"
    "(?!(" + "|".join(REQUIRED_METHODS) + ")$).+$/"
)
SETTINGS_SECTION = "[/Script/ToolsetRegistry.ToolsetRegistrySettings]"


def fresh_project_ini_fragment():
    """Return one append-only BlockedNames directive; do not apply it here."""
    return SETTINGS_SECTION + '\n+BlockedNames="' + BLOCKED_NAMES_PATTERN + '"\n'
