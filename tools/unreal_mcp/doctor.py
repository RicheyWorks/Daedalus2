# SPDX-License-Identifier: MIT
"""Editor settings that bite unattended bots, read back through the Epic MCP server (02:42: the 3 fps throttle and
the "38 changes to source content files" modal were both settings nobody had read back).

    python tools/unreal_mcp/doctor.py            # prints one line per setting, exit 1 if any is wrong or MCP is down
    python tools/unreal_mcp/doctor.py --fix      # requests wanted values, then verifies a fresh readback
"""
import json
import sys

if __package__:
    from .client import Mcp, ready
else:
    from client import Mcp, ready

TS = "ConfigSettingsToolset.ConfigSettingsToolset"
WANT = {
    ("EditorPerformanceSettings", "bThrottleCPUWhenNotForeground"): (False, "3 fps whenever the editor is not the active window"),
    ("EditorPerformanceSettings", "bAllowSlateThrottling"): (False, "viewports/sim slow down during UI interaction"),
    ("LoadingSaving", "bMonitorContentDirectories"): (False, "the team's pipeline owns imports; monitoring raises modals"),
    ("LoadingSaving", "bPromptBeforeAutoImporting"): (False, "'Would you like to import them?' freezes every bridge call"),
    ("LoadingSaving", "bAutoDeleteAssets"): (False, "a deleted source file must never delete assets"),
    ("LoadingSaving", "bDetectChangesOnStartup"): (False, "no import prompt at editor start"),
    ("LoadingSaving", "autoSaveTimeMinutes"): (30, "autosave collides with proven saves; 30 min, not 10"),
    ("LoadingSaving", "autoSaveWarningInSeconds"): (0, "no autosave warning popup"),
    ("LoadingSaving", "bPromptForCheckoutOnAssetModification"): (False, "no source-control checkout prompts"),
    ("LoadingSaving", "restoreOpenAssetTabsOnRestart"): ("NeverRestore", "no 'restore open assets?' prompt at start"),
    ("EditorPerformanceSettings", "bEnableNotifications"): (False, "no editor performance warning toasts"),
    ("EditorPerformanceSettings", "bMonitorEditorPerformance"): (False, "the editor must not change scalability on its own"),
    ("EditorPerformanceSettings", "bEnableScalabilityWarningIndicator"): (False, "no scalability warning overlay"),
}


def _readback(m, by_section):
    """Return wrong/unverified settings and section read errors; no mutations."""
    bad = []
    errors = []
    for sec, props in by_section.items():
        try:
            reply = m.call(TS, "GetSectionPropertyValues", containerName="Editor", categoryName="General", sectionName=sec, propertyNames=props)
            vals = json.loads(reply) if isinstance(reply, str) else reply
            if not isinstance(vals, dict):
                raise ValueError("settings readback must be a JSON object")
        except Exception as error:
            print("UNKNOWN %s readback: %s" % (sec, error))
            errors.append(sec)
            vals = {}
        else:
            missing = [prop for prop in props if prop not in vals]
            if missing:
                print("UNKNOWN %s readback: missing %s" % (sec, ", ".join(missing)))
                errors.append(sec)
        for prop in props:
            want, why = WANT[(sec, prop)]
            value = vals.get(prop)
            # JSON booleans and numbers are distinct even though False == 0 in Python.
            ok = type(value) is type(want) and value == want
            print("%s %s.%s = %r (want %r) — %s" % ("ok " if ok else "BAD", sec, prop, vals.get(prop), want, why))
            if not ok:
                bad.append((sec, prop, want))
    return bad, errors


def main(argv):
    if not ready():
        print("MCP DOWN: nothing listening at 127.0.0.1:8000/mcp (ModelContextProtocol.StartServer in the editor)")
        return 1
    try:
        m = Mcp(timeout=30)
    except Exception as error:
        print("MCP NOT READY: client initialization failed: %s" % error)
        return 1
    by_section = {}
    for sec, prop in WANT:
        by_section.setdefault(sec, []).append(prop)
    bad, errors = _readback(m, by_section)
    # A failed initial read must not turn an unknown state into blind writes.
    if bad and not errors and "--fix" in argv:
        fix = {}
        for sec, prop, want in bad:
            fix.setdefault(sec, {})[prop] = want
        write_errors = []
        for sec, props in fix.items():
            try:
                r = m.call(TS, "SetSectionProperties", containerName="Editor", categoryName="General", sectionName=sec, propertiesJson=json.dumps(props))
                print("set requested %s %s -> %s" % (sec, sorted(props), r))
                # The native bool is true only if setting AND saving succeeded.
                # A failed save can leave matching in-memory values behind.
                if r is False:
                    raise RuntimeError("native setter returned false; setting or config save failed")
                if r is not True:
                    raise RuntimeError("native setter did not return Boolean true; outcome is unverified")
            except Exception as error:
                print("FIX FAILED %s: %s (not retried; outcome may be unknown)" % (sec, error))
                write_errors.append(sec)
                break
        # Even a successful setter reply is not proof of the observed configuration.
        # Re-read every intended setting, including those that were initially correct.
        bad, errors = _readback(m, by_section)
        errors.extend(write_errors)
    failed = bool(bad or errors)
    print("%s, %d setting(s) wrong or unverified, %d error(s)" % ("MCP NOT READY" if failed else "MCP READY", len(bad), len(errors)))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
