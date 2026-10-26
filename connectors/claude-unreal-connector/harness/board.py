# SPDX-License-Identifier: MIT
"""docs/board.html, rendered from the ledgers alone: nothing on it is typed by hand. (CSRBT tools/harness_board.py.)
--check exits 1 if the file on disk differs from what the ledgers say now, so a stale board is a red build.

    python -m harness.board [--check]
"""
import argparse
import html
import io
import os
import sys
import time

from harness import ledger

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "docs", "board.html")
MARK = {"ok": "ok", "killed": "ok", "driven": "ok", "excluded": "warn", "declined": "warn", "refused": "warn"}


def cls(v):
    return MARK.get(v, "bad")


def render():
    runs = ledger.load("runs").get("entries", {})
    walks = ledger.load("walk").get("entries", {})
    muts = ledger.load("mutants").get("entries", {})
    e = html.escape
    parts = ["<!doctype html><meta charset=utf-8><title>Connector harness board</title><style>",
             ":root{--bg:#fff;--fg:#1a1a1a;--mut:#666;--ok:#1a7f37;--warn:#9a6700;--bad:#cf222e;--line:#ddd}",
             "@media (prefers-color-scheme:dark){:root{--bg:#0d1117;--fg:#e6edf3;--mut:#8b949e;--ok:#3fb950;--warn:#d29922;--bad:#f85149;--line:#30363d}}",
             "body{font:14px/1.45 system-ui,sans-serif;background:var(--bg);color:var(--fg);max-width:960px;margin:24px auto;padding:0 16px}",
             "table{border-collapse:collapse;width:100%;margin:8px 0 24px}td,th{border-bottom:1px solid var(--line);padding:4px 8px;text-align:left;vertical-align:top}",
             ".ok{color:var(--ok)}.warn{color:var(--warn)}.bad{color:var(--bad)}small{color:var(--mut)}</style>",
             "<h1>claude-unreal-connector harness</h1><p><small>Rendered by harness/board.py from ledgers/*.json.</small></p>"]
    for key, r in sorted(runs.items()):
        parts.append("<h2>Suites (%s): %d/%d ok</h2><table><tr><th>suite</th><th>mark</th><th>checks</th><th>floor</th></tr>"
                     % (e(key), r["ok"], r["of"]))
        for s in r["suites"]:
            parts.append("<tr><td>%s</td><td class=%s>%s</td><td>%s/%s</td><td>%s</td></tr>"
                         % (e(s["name"]), cls(s["mark"]), e(s["mark"]), s["got"], s["total"], s["floor"]))
        parts.append("</table>")
    for key, w in sorted(walks.items()):
        b = w["buckets"]
        parts.append("<h2>Walk (%s): %d commands</h2><p>%s</p><table><tr><th>command</th><th>risk</th><th>bucket</th><th>detail</th></tr>"
                     % (e(key), w["discovered"], e(", ".join("%s %d" % kv for kv in sorted(b.items())))))
        for r in w["rows"]:
            parts.append("<tr><td>%s</td><td>%s</td><td class=%s>%s</td><td><small>%s</small></td></tr>"
                         % (e(r["command"]), e(r["risk"]), cls(r["bucket"]), e(r["bucket"]), e(r["detail"])))
        parts.append("</table>")
    for key, m in sorted(muts.items()):
        parts.append("<h2>Mutants (%s): %d killed, %d survived, %d inconclusive</h2><table><tr><th>mutant</th><th>verdict</th><th>detail</th></tr>"
                     % (e(key), m["killed"], m["survived"], m["inconclusive"]))
        for r in m["rows"]:
            parts.append("<tr><td>%s</td><td class=%s>%s</td><td><small>%s</small></td></tr>"
                         % (e(r["name"]), cls(r["verdict"]), e(r["verdict"]), e(r["detail"])))
        parts.append("</table>")
    return "\n".join(parts) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args(argv)
    page = render()
    if a.check:
        cur = io.open(OUT, encoding="utf-8").read() if os.path.isfile(OUT) else ""
        if cur != page:
            print("FAIL docs/board.html is stale: run python -m harness.board")
            print("0/1")
            return 1
        print("PASS the board matches the ledgers")
        print("1/1")
        return 0
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with io.open(OUT, "w", encoding="utf-8") as f:
        f.write(page)
    print("wrote %s" % OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
