# SPDX-License-Identifier: MIT
"""Run the Daedalus controller contract against every implementation and print a conformance table.

    python tools/controllers/contract_check.py [--native-header PATH]

Writes data/controllers/controller-contract.json (from contract_source.py; version 1 is frozen, so the file must
not change once committed: --check-frozen compares). Runs the web vectors on daedalus-pad.js with node, and the
native vectors on DaedalusPortalControls.h (Codex's translator; on main once merged, else taken from the branch
codex/portal-controller-intents-20261014) by generating a C++ program, compiling it with g++ -std=c++20 and running it.
Exit 1 if any implementation fails a vector it claims.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
import contract_source as CS  # noqa: E402

OUT = os.path.join(REPO, "data", "controllers", "controller-contract.json")
PUBLIC = os.path.join(REPO, "engines", "unreal", "DaedalusLink", "Source", "DaedalusLink", "Public")
BRANCH = "origin/codex/portal-controller-intents-20261014"
NATIVE_KEY = {"south": "Gamepad_FaceButton_Bottom", "east": "Gamepad_FaceButton_Right", "start": "Gamepad_Special_Right",
              "dpad_up": "Gamepad_DPad_Up", "dpad_down": "Gamepad_DPad_Down", "dpad_left": "Gamepad_DPad_Left", "dpad_right": "Gamepad_DPad_Right",
              "south@2": "Enter", "dpad_down@2": "S", "dpad_right@2": "D", "dpad_up@2": "W"}
NATIVE_AXIS = {"lx": "Gamepad_LeftX", "ly": "Gamepad_LeftY"}
NATIVE_BTN = {"up": "Up", "down": "Down", "left": "Left", "right": "Right", "confirm": "A", "cancel": "B", "menu": "Start"}


def write_contract():
    doc = dict(CS.CONTRACT, vectors=CS.VECTORS)
    text = json.dumps(doc, indent=1)
    if "--check-frozen" in sys.argv and os.path.exists(OUT) and open(OUT, encoding="utf-8").read() != text:
        print("CONTRACT FROZEN: controller-contract.json differs from contract_source.py; behaviour changes need version 2")
        sys.exit(1)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, "w", encoding="utf-8").write(text)
    return doc


def run_web(doc):
    out = subprocess.run(["node", os.path.join(HERE, "contract_web.js"), OUT], capture_output=True, text=True)
    if out.returncode:
        return {"error": out.stderr[-2000:]}
    return {r["id"]: r for r in json.loads(out.stdout.strip().splitlines()[-1])}


def cpp_for(doc):
    L = ['#include "DaedalusPortalControls.h"', "#include <cstdio>", "#include <set>", "#include <string>",
         "namespace PC = daedalus::portal_controls; using B = PC::Button;",
         'static const char* nm(int b) { switch (b) { case (int)B::Up: return "up"; case (int)B::Down: return "down"; case (int)B::Left: return "left";'
         ' case (int)B::Right: return "right"; case (int)B::A: return "confirm"; case (int)B::B: return "cancel"; case (int)B::Start: return "menu"; } return "?"; }',
         "struct Run { PC::Translator T; std::set<int> held; int edges = 0;",
         "  void apply(const std::vector<PC::Edge>& e) { for (auto& x : e) { edges++; if (x.Pressed) held.insert((int)x.Intent); else held.erase((int)x.Intent); } }",
         "  std::string got() { std::string s; for (int h : held) { if (!s.empty()) s += \",\"; s += nm(h); } return s; } };",
         "int main() { int fails = 0;"]
    for v in doc["vectors"]:
        if "native" not in v["scope"]:
            continue
        lay = "PC::Layout::EastConfirm" if v["layout"] == "east" else "PC::Layout::ExistingBottomConfirm"
        L.append("  { Run R; std::vector<PC::Edge> rel; std::string err; bool ok = R.T.Replace(PC::Profile::Preset(%s), rel, err); std::string why;" % lay)
        L.append("    double X = 0, Y = 0; (void)X; (void)Y;")
        for i, st in enumerate(v["steps"]):
            if st.get("release_all"):
                L.append("    R.apply(R.T.ReleaseAll());")
            for k in st.get("down", []):
                L.append('    R.apply(R.T.KeyDown("%s").Edges);' % NATIVE_KEY[k])
            for k in st.get("up", []):
                L.append('    R.apply(R.T.KeyUp("%s").Edges);' % NATIVE_KEY[k])
            if "repeat" in st:
                L.append("    { int before = R.edges;")
                for k in st["repeat"]:
                    L.append('      R.apply(R.T.KeyDown("%s", true).Edges);' % NATIVE_KEY[k])
                L.append('      if (R.edges - before != %d) { ok = false; why += "step %d: repeat made edges; "; } }' % (st.get("edges", 0), i))
            for ax, val in (st.get("axes") or {}).items():
                if ax in NATIVE_AXIS:
                    L.append('    R.apply(R.T.Axis("%s", %r).Edges);' % (NATIVE_AXIS[ax], float(val)))
            if "held" in st:
                want = ",".join(sorted(NATIVE_BTN[h] for h in st["held"]))
                order = {"up": 0, "down": 1, "left": 2, "right": 3, "confirm": 4, "cancel": 5, "menu": 6}
                want_names = ",".join(h for h in sorted(st["held"], key=lambda h: list(NATIVE_BTN).index(h)))
                L.append('    if (R.got() != "%s") { ok = false; why += "step %d: held [" + R.got() + "] expected [%s]; "; }' % (want_names, i, want_names))
        L.append('    std::printf("%%s\\t%%s\\t%%s\\n", "%s", ok ? "ok" : "FAIL", why.c_str()); if (!ok) fails++; }' % v["id"])
    L.append("  return fails ? 1 : 0; }")
    return "\n".join(L)


def run_native(doc, header):
    tmp = tempfile.mkdtemp(prefix="contract_")
    shutil.copy(header, os.path.join(tmp, "DaedalusPortalControls.h"))
    src = os.path.join(tmp, "contract_native.cpp")
    open(src, "w").write(cpp_for(doc))
    exe = os.path.join(tmp, "contract_native")
    c = subprocess.run(["g++", "-std=c++20", "-Wall", "-Wextra", "-I", tmp, "-I", PUBLIC, src, "-o", exe], capture_output=True, text=True)
    if c.returncode:
        return {"error": c.stderr[-3000:]}
    r = subprocess.run([exe], capture_output=True, text=True)
    res = {}
    for line in r.stdout.splitlines():
        vid, status, why = (line.split("\t") + ["", ""])[:3]
        res[vid] = {"id": vid, "ok": status == "ok", "fails": [why] if why else []}
    res["_warnings"] = c.stderr.strip()
    return res


def native_header():
    if "--native-header" in sys.argv:
        return sys.argv[sys.argv.index("--native-header") + 1]
    local = os.path.join(PUBLIC, "DaedalusPortalControls.h")
    if os.path.exists(local):
        return local
    tmp = os.path.join(tempfile.mkdtemp(prefix="pch_"), "DaedalusPortalControls.h")
    blob = subprocess.run(["git", "-C", REPO, "show", BRANCH + ":engines/unreal/DaedalusLink/Source/DaedalusLink/Public/DaedalusPortalControls.h"],
                          capture_output=True, text=True)
    if blob.returncode:
        return None
    open(tmp, "w").write(blob.stdout)
    return tmp


def main():
    doc = write_contract()
    web = run_web(doc)
    hdr = native_header()
    nat = run_native(doc, hdr) if hdr else {"error": "native header not found (main or %s)" % BRANCH}
    bad = 0
    print("%-24s %-8s %-8s" % ("vector", "web", "native"))
    for v in doc["vectors"]:
        cells = []
        for name, res in (("web", web), ("native", nat)):
            if name not in v["scope"]:
                cells.append("-"); continue
            if "error" in res:
                cells.append("ERROR"); bad += 1; continue
            r = res.get(v["id"])
            cells.append("ok" if r and r["ok"] else "FAIL")
            if not (r and r["ok"]):
                bad += 1
        print("%-24s %-8s %-8s" % (v["id"], cells[0], cells[1]))
    for name, res in (("web", web), ("native", nat)):
        if "error" in res:
            print("%s ERROR: %s" % (name, res["error"]))
        else:
            for vid, r in res.items():
                if vid != "_warnings" and not r["ok"]:
                    print("%s %s: %s" % (name, vid, "; ".join(r["fails"])))
    if nat.get("_warnings"):
        print("native compiler warnings:", nat["_warnings"][:500])
    print("CONTRACT", doc["schema"], "PASS" if not bad else "FAIL (%d)" % bad)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
