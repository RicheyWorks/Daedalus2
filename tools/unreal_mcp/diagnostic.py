# SPDX-License-Identifier: MIT
"""Connector diagnostic (Richey 02:46: "have you run a diagnostic to test your new capabilities... we need to learn
more"): inventory every toolset and tool, run one SAFE read-only probe per area, time each call, and write
docs/production/mcp-diagnostic.json + .md. Nothing here mutates the project (no set_*, no spawn, no save).

    python tools/unreal_mcp/diagnostic.py [--out docs/production]
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from client import Mcp, ready  # noqa: E402

# (toolset, tool, arguments, what it proves)
PROBES = [
    ("EditorToolset.EditorAppToolset", "IsPIERunning", {}, "PIE state"),
    ("EditorToolset.EditorAppToolset", "GetCameraTransform", {}, "viewport camera"),
    ("EditorToolset.EditorAppToolset", "GetVisibleActors", {}, "frustum query"),
    ("EditorToolset.EditorAppToolset", "SearchCVars", {"name": "r.Shadow.DistanceScale"}, "cvar search"),
    ("EditorToolset.EditorAppToolset", "GetSelectedActors", {}, "selection"),
    ("EditorToolset.EditorAppToolset", "GetOpenAssets", {}, "open asset editors"),
    ("EditorToolset.LogsToolset", None, {}, "log reading (tool picked from describe)"),
    ("editor_toolset.toolsets.scene.SceneTools", "get_current_level", {}, "level path"),
    ("editor_toolset.toolsets.scene.SceneTools", "get_folders", {}, "outliner folders"),
    ("editor_toolset.toolsets.scene.SceneTools", "find_actors", {"name": "Lands_WORLDZERO_D", "tag": "Realm:WORLD-ZERO", "collision_channels": []}, "tag query"),
    ("editor_toolset.toolsets.scene.SceneTools", "trace_world", {"start": {"x": 14850, "y": -9500, "z": 20000}, "end": {"x": 14850, "y": -9500, "z": -20000}}, "line trace at the hub"),
    ("editor_toolset.toolsets.asset.AssetTools", None, {}, "asset listing (tool picked from describe)"),
    ("editor_toolset.toolsets.object.ObjectTools", None, {}, "class discovery (tool picked from describe)"),
    ("ConfigSettingsToolset.ConfigSettingsToolset", "ListContainers", {}, "settings containers"),
    ("ConfigSettingsToolset.ConfigSettingsToolset", "GetSectionPropertyValues", {"containerName": "Editor", "categoryName": "General", "sectionName": "EditorPerformanceSettings", "propertyNames": ["bThrottleCPUWhenNotForeground"]}, "settings read-back"),
    ("GameplayTagsToolset.GameplayTagsToolset", None, {}, "gameplay tags (tool picked from describe)"),
    ("AutomationTestToolset.AutomationTestToolset", "DiscoverTests", {}, "automation test discovery"),
    ("AutomationTestToolset.AutomationTestToolset", "ListTests", {}, "automation test list"),
    ("PluginToolset.PluginToolset", None, {}, "plugin listing (tool picked from describe)"),
    ("SlateInspectorToolset.SlateInspectorToolset", None, {}, "editor UI snapshot (tool picked from describe)"),
    ("SemanticSearchToolset.SemanticSearchToolset", None, {}, "asset semantic search (tool picked from describe)"),
    ("editor_toolset.toolsets.static_mesh.StaticMeshTools", None, {}, "static mesh inspection (tool picked from describe)"),
]
READ_ONLY_HINTS = ("get", "list", "find", "is", "search", "describe", "discover", "read", "query", "snapshot", "trace", "export_json", "summary", "info", "count")


def pick_read_only(spec, want_args=None):
    """First tool whose short name reads like a query and whose required inputs are all optional/empty."""
    for t in spec.get("tools", []):
        short = t["name"].split(".")[-1]
        low = short.lower()
        if not low.startswith(READ_ONLY_HINTS):
            continue
        req = (t.get("inputSchema") or {}).get("required") or []
        if not req:
            return short, {}
    return None, None


def main(argv):
    out_dir = argv[argv.index("--out") + 1] if "--out" in argv else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "docs", "production")
    t_all = time.time()
    if not ready():
        print("MCP DOWN")
        return 1
    m = Mcp(timeout=120)
    report = {"when": time.strftime("%Y-%m-%dT%H:%M:%S"), "toolsets": {}, "probes": []}
    t0 = time.time()
    listing = m.toolsets()
    report["list_toolsets_s"] = round(time.time() - t0, 3)
    names = [l.split(":")[0].lstrip("- ").strip() for l in str(listing).splitlines() if l.startswith("- ")]
    total_tools = 0
    for name in names:
        t0 = time.time()
        try:
            spec = m.describe(name)
            tools = spec.get("tools", []) if isinstance(spec, dict) else []
            kinds = {"read": 0, "write": 0}
            for t in tools:
                kinds["read" if t["name"].split(".")[-1].lower().startswith(READ_ONLY_HINTS) else "write"] += 1
            report["toolsets"][name] = {"tools": len(tools), "read_like": kinds["read"], "write_like": kinds["write"], "describe_s": round(time.time() - t0, 3),
                                       "names": [t["name"].split(".")[-1] for t in tools][:60]}
            total_tools += len(tools)
        except Exception as e:
            report["toolsets"][name] = {"error": str(e)[:200], "describe_s": round(time.time() - t0, 3)}
    for toolset, tool, args, why in PROBES:
        if toolset not in report["toolsets"] or "error" in report["toolsets"][toolset]:
            report["probes"].append({"toolset": toolset, "tool": tool, "why": why, "skipped": "toolset not described"})
            continue
        if tool is None:
            spec = m.describe(toolset)
            tool, args = pick_read_only(spec)
            if tool is None:
                report["probes"].append({"toolset": toolset, "tool": None, "why": why, "skipped": "no argument-free read-only tool"})
                continue
        t0 = time.time()
        row = {"toolset": toolset, "tool": tool, "args": args, "why": why}
        try:
            r = m.call(toolset, tool, **args)
            txt = json.dumps(r) if not isinstance(r, str) else r
            row.update(ok=True, seconds=round(time.time() - t0, 3), reply_bytes=len(txt), sample=txt[:160])
            if isinstance(r, list):
                row["count"] = len(r)
        except Exception as e:
            row.update(ok=False, seconds=round(time.time() - t0, 3), error=str(e)[:300])
        report["probes"].append(row)
    report["total_toolsets"] = len(names)
    report["total_tools"] = total_tools
    report["seconds"] = round(time.time() - t_all, 1)
    os.makedirs(out_dir, exist_ok=True)
    jp = os.path.join(out_dir, "mcp-diagnostic.json")
    with open(jp, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=1)
    lines = ["# Epic Unreal MCP diagnostic — %s" % report["when"], "",
             "%d toolsets, %d tools, inventory in %.1f s. Probes: %d ok, %d failed, %d skipped." % (
                 len(names), total_tools, report["seconds"], sum(1 for p in report["probes"] if p.get("ok")),
                 sum(1 for p in report["probes"] if p.get("ok") is False), sum(1 for p in report["probes"] if "skipped" in p)), "",
             "| toolset | tools | read-like | write-like | describe s |", "|---|---|---|---|---|"]
    for name, info in sorted(report["toolsets"].items()):
        lines.append("| %s | %s | %s | %s | %s |" % (name, info.get("tools", "-"), info.get("read_like", "-"), info.get("write_like", "-"), info.get("describe_s")))
    lines += ["", "| probe | tool | ok | s | bytes | note |", "|---|---|---|---|---|---|"]
    for p in report["probes"]:
        note = p.get("skipped") or p.get("error") or ("count=%s" % p["count"] if "count" in p else (p.get("sample") or "")[:60])
        lines.append("| %s | %s | %s | %s | %s | %s |" % (p["why"], p.get("tool"), p.get("ok", "-"), p.get("seconds", "-"), p.get("reply_bytes", "-"), str(note).replace("|", "/")))
    with open(os.path.join(out_dir, "mcp-diagnostic.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines[:3]))
    for p in report["probes"]:
        print("%-5s %6ss %-50s %s" % ("ok" if p.get("ok") else ("skip" if "skipped" in p else "FAIL"), p.get("seconds", "-"), p["why"], (p.get("error") or p.get("skipped") or "")[:80]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
