# SPDX-License-Identifier: MIT
"""Channel Chart (G536, disk-saver): a static chart of the tools/streaming code.

Python dev tooling only; nothing here runs inside Unreal and no charted code is executed
(sources are parsed with ast). Reads, read-only, tools/streaming/*.py, .github/workflows
and data/islands/disk-saver, and charts per tool (non-test module):

  * local imports (other tools/streaming modules, by plain or tools.streaming.* import),
  * external imports (neither stdlib nor local),
  * the disk-saver data files it or its test names (string constants),
  * its test file (<tool>_test.py or test_<tool>.py) and the CI workflows that name it.

Findings:
  errors (uncharted):   syntax_error, import_cycle, missing_module (tools.streaming.X that does not exist);
  advisories (shoals):  no_test, no_workflow, external_import, unnamed_data (a disk-saver data
                        file that no tool, test or workflow names).

Also a run order: every tool after the local tools it imports (ties by name).
Verdict charted / shoals / uncharted. Stdlib only, deterministic, no clock.

  python tools/streaming/channel_chart.py [--root DIR] [--json] [--fail-on shoals|uncharted]

Exit 0 = chart printed, 1 = --fail-on and the verdict is at least that bad, 2 = refusal.
"""
import argparse
import ast
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
FORMAT = "daedalus-channel-chart"
ERRORS = ("syntax_error", "import_cycle", "missing_module")
ADVISORIES = ("no_test", "no_workflow", "external_import", "unnamed_data")
RANK = {"charted": 0, "shoals": 1, "uncharted": 2}
STDLIB = set(getattr(sys, "stdlib_module_names", ())) | {"__future__"}


class ChartError(ValueError):
    pass


def is_test(stem):
    return stem.endswith("_test") or stem.startswith("test_")


def parse(src):
    """(imports [(name, via_package)], string constants) or raises SyntaxError."""
    tree = ast.parse(src)
    imports, strings = [], set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                imports.append(a.name)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            if node.module == "tools.streaming":
                imports += [f"tools.streaming.{a.name}" for a in node.names]
            else:
                imports.append(node.module)
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            strings.add(node.value)
    return imports, strings


def _cycles(graph):
    """Strongly connected components with more than one node or a self loop (Tarjan, iterative order)."""
    index, low, stack, on, out, n = {}, {}, [], set(), [], [0]

    def visit(v):
        index[v] = low[v] = n[0]
        n[0] += 1
        stack.append(v)
        on.add(v)
        for w in sorted(graph[v]):
            if w not in index:
                visit(w)
                low[v] = min(low[v], low[w])
            elif w in on:
                low[v] = min(low[v], index[w])
        if low[v] == index[v]:
            comp = []
            while True:
                w = stack.pop()
                on.discard(w)
                comp.append(w)
                if w == v:
                    break
            if len(comp) > 1 or v in graph[v]:
                out.append(sorted(comp))

    for v in sorted(graph):
        if v not in index:
            visit(v)
    return sorted(out)


def run_order(graph):
    done, order = set(), []
    remaining = set(graph)
    while remaining:
        ready = sorted(v for v in remaining if graph[v] <= done)
        if not ready:
            ready = [min(remaining)]  # break a cycle deterministically
        v = ready[0]
        order.append(v)
        done.add(v)
        remaining.discard(v)
    return order


def chart(root):
    tools_dir = os.path.join(root, "tools", "streaming")
    if not os.path.isdir(tools_dir):
        raise ChartError(f"{tools_dir}: not a directory")
    wf_dir = os.path.join(root, ".github", "workflows")
    data_dir = os.path.join(root, "data", "islands", "disk-saver")
    workflows = {}
    if os.path.isdir(wf_dir):
        for n in sorted(os.listdir(wf_dir)):
            if n.endswith((".yml", ".yaml")):
                with open(os.path.join(wf_dir, n), encoding="utf-8", errors="replace") as f:
                    workflows[n] = f.read()
    data_files = sorted(n for n in os.listdir(data_dir)) if os.path.isdir(data_dir) else []
    stems = sorted(n[:-3] for n in os.listdir(tools_dir) if n.endswith(".py"))
    local = set(stems)
    parsed, findings = {}, []
    for s in stems:
        with open(os.path.join(tools_dir, s + ".py"), encoding="utf-8", errors="replace") as f:
            src = f.read()
        try:
            parsed[s] = parse(src)
        except SyntaxError as e:
            findings.append({"tool": s, "kind": "syntax_error", "line": e.lineno})
    named_data = set()
    for _, strings in parsed.values():
        named_data |= {os.path.basename(x) for x in strings}
    for text in workflows.values():
        named_data |= {d for d in data_files if d in text}
    graph, rows = {}, []
    for s in [x for x in stems if not is_test(x) and x in parsed]:
        imports, strings = parsed[s]
        loc, ext = set(), set()
        for name in imports:
            top = name.split(".")[0]
            if name.startswith("tools.streaming."):
                mod = name.split(".")[2]
                if mod in local:
                    loc.add(mod)
                else:
                    findings.append({"tool": s, "kind": "missing_module", "module": name})
            elif top in local:
                loc.add(top)
            elif top not in STDLIB and top != "tools":
                ext.add(top)
        test = next((t for t in (f"{s}_test", f"test_{s}") if t in parsed or t in local), None)
        test_strings = parsed[test][1] if test in parsed else set()
        data = sorted(d for d in data_files if d in {os.path.basename(x) for x in strings | test_strings})
        wfs = sorted(n for n, t in workflows.items() if f"tools/streaming/{s}.py" in t or (test and f"{test}.py" in t))
        graph[s] = loc
        rows.append({"tool": s, "imports": sorted(loc), "external": sorted(ext), "data": data,
                     "test": f"tools/streaming/{test}.py" if test else None, "workflows": wfs})
        if not test:
            findings.append({"tool": s, "kind": "no_test"})
        if not wfs:
            findings.append({"tool": s, "kind": "no_workflow"})
        for e in sorted(ext):
            findings.append({"tool": s, "kind": "external_import", "module": e})
    for g in graph:
        graph[g] = {x for x in graph[g] if x in graph}
    for comp in _cycles(graph):
        findings.append({"tool": None, "kind": "import_cycle", "tools": comp})
    for d in data_files:
        if d not in named_data:
            findings.append({"tool": None, "kind": "unnamed_data", "file": d})
    order = {k: i for i, k in enumerate(ERRORS + ADVISORIES)}
    findings.sort(key=lambda x: (order[x["kind"]], x["tool"] or "", json.dumps(x, sort_keys=True)))
    counts = {k: sum(1 for x in findings if x["kind"] == k) for k in ERRORS + ADVISORIES}
    verdict = "uncharted" if any(counts[k] for k in ERRORS) else "shoals" if findings else "charted"
    importers = {s: sorted(t for t in graph if s in graph[t]) for s in graph}
    for r in rows:
        r["imported_by"] = importers[r["tool"]]
    return {"format": FORMAT, "version": 1, "tools": rows, "run_order": run_order(graph),
            "findings": findings, "counts": counts, "verdict": verdict}


def text(r):
    out = [f"channel chart: {r['verdict']} ({len(r['tools'])} tools; "
           f"{sum(r['counts'][k] for k in ERRORS)} errors, {sum(r['counts'][k] for k in ADVISORIES)} advisories)"]
    hubs = sorted((x for x in r["tools"] if x["imported_by"]), key=lambda x: (-len(x["imported_by"]), x["tool"]))
    for h in hubs[:5]:
        out.append(f"  hub {h['tool']}: imported by {len(h['imported_by'])} ({', '.join(h['imported_by'])})")
    for x in r["findings"]:
        bits = " ".join(f"{k}={json.dumps(v)}" for k, v in sorted(x.items()) if k not in ("kind", "tool"))
        out.append(f"  {'!' if x['kind'] in ERRORS else '-'} {x['kind']} {x['tool'] or '*'} {bits}".rstrip())
    return "\n".join(out) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description="Channel Chart: static chart of tools/streaming.")
    ap.add_argument("--root", default=ROOT)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--fail-on", choices=("shoals", "uncharted"))
    a = ap.parse_args(argv)
    try:
        r = chart(a.root)
    except ChartError as e:
        print(f"channel_chart: refused: {e}", file=sys.stderr)
        return 2
    sys.stdout.write(json.dumps(r, indent=2, sort_keys=True) + "\n" if a.json else text(r))
    return 1 if a.fail_on and RANK[r["verdict"]] >= RANK[a.fail_on] else 0


if __name__ == "__main__":
    sys.exit(main())