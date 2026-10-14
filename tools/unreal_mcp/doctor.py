# SPDX-License-Identifier: MIT
"""Editor settings that bite unattended bots, read back through the Epic MCP server (02:42: the 3 fps throttle and
the "38 changes to source content files" modal were both settings nobody had read back).

    python tools/unreal_mcp/doctor.py            # prints one line per setting, exit 1 if any is wrong or MCP is down
    python tools/unreal_mcp/doctor.py --fix      # sets the wanted values (saved to the editor's config)
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from client import Mcp, ready  # noqa: E402

TS = "ConfigSettingsToolset.ConfigSettingsToolset"
WANT = {
    ("EditorPerformanceSettings", "bThrottleCPUWhenNotForeground"): (False, "3 fps whenever the editor is not the active window"),
    ("EditorPerformanceSettings", "bAllowSlateThrottling"): (False, "viewports/sim slow down during UI interaction"),
    ("LoadingSaving", "bMonitorContentDirectories"): (False, "the team's pipeline owns imports; monitoring raises modals"),
    ("LoadingSaving", "bPromptBeforeAutoImporting"): (False, "'Would you like to import them?' freezes every bridge call"),
    ("LoadingSaving", "bAutoDeleteAssets"): (False, "a deleted source file must never delete assets"),
    ("LoadingSaving", "bDetectChangesOnStartup"): (False, "no import prompt at editor start"),
    ("LoadingSaving", "autoSaveTimeMinutes"): (30, "autosave collides with proven saves; 30 min, not 10"),
}


def main(argv):
    if not ready():
        print("MCP DOWN: nothing listening at 127.0.0.1:8000/mcp (ModelContextProtocol.StartServer in the editor)")
        return 1
    m = Mcp(timeout=30)
    bad = []
    by_section = {}
    for (sec, prop), (want, why) in WANT.items():
        by_section.setdefault(sec, []).append(prop)
    for sec, props in by_section.items():
        vals = json.loads(m.call(TS, "GetSectionPropertyValues", containerName="Editor", categoryName="General", sectionName=sec, propertyNames=props))
        for prop in props:
            want, why = WANT[(sec, prop)]
            ok = vals.get(prop) == want
            print("%s %s.%s = %r (want %r) — %s" % ("ok " if ok else "BAD", sec, prop, vals.get(prop), want, why))
            if not ok:
                bad.append((sec, prop, want))
    if bad and "--fix" in argv:
        fix = {}
        for sec, prop, want in bad:
            fix.setdefault(sec, {})[prop] = want
        for sec, props in fix.items():
            r = m.call(TS, "SetSectionProperties", containerName="Editor", categoryName="General", sectionName=sec, propertiesJson=json.dumps(props))
            print("fixed %s %s -> %s" % (sec, sorted(props), r))
        bad = []
    print("MCP READY, %d setting(s) wrong" % len(bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
