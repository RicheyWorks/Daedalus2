# SPDX-License-Identifier: MIT
"""One settings schema for every Daedalus client, laid out like Halo Infinite's settings.

    python tools/settings/build_schema.py           # write data/settings/settings-schema.json (+ web copy)
    python tools/settings/build_schema.py --check   # fail if the schema and the native C++ disagree

Source of truth for every row the Unreal client already has is the C++ itself: the Add(...) rows in
engines/unreal/.../DaedalusSettings.cpp (ids, kinds, defaults, ranges, choices, help) and the button / thumbstick
layout tables in DaedalusHero.cpp (PadButtons, the RebuildBindings stick switch). Nothing there is retyped here.
New rows (the Audio tab, trigger and outer/axial stick dead zones, confirm button, text size ...) live in
schema_source.py with the consumers that read them. Tabs, their order and their sections follow Halo Infinite:
Controller, Keyboard/Mouse, Video, Audio, Gameplay, Accessibility.

Saved values use the native format everywhere: a flat {"Id": number} object (Saved/Config/DaedalusSettings.json in
Unreal, localStorage "daedalus.settings" on the web), so a settings file moves between clients unchanged.
"""
import json
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
import schema_source as SS  # noqa: E402

NATIVE = os.path.join(REPO, "engines", "unreal", "DaedalusLink", "Source", "DaedalusLink", "Private")
OUT = os.path.join(REPO, "data", "settings", "settings-schema.json")
WEB = os.path.join(REPO, "daedalus-server", "src", "main", "resources", "static", "settings", "settings-schema.json")


def split_args(s):
    """Split a C++ argument list at top-level commas (quotes, braces and parentheses respected)."""
    out, depth, cur, q = [], 0, "", False
    i = 0
    while i < len(s):
        c = s[i]
        if q:
            cur += c
            if c == "\\":
                cur += s[i + 1]; i += 1
            elif c == '"':
                q = False
        elif c == '"':
            q = True; cur += c
        elif c in "({":
            depth += 1; cur += c
        elif c in ")}":
            depth -= 1; cur += c
        elif c == "," and depth == 0:
            out.append(cur.strip()); cur = ""
        else:
            cur += c
        i += 1
    if cur.strip():
        out.append(cur.strip())
    return out


def cstr(tok, consts):
    tok = tok.strip()
    if tok in consts:
        return consts[tok]
    m = re.fullmatch(r'(?:TEXT\()?"(.*)"\)?', tok, re.S)
    if not m:
        raise ValueError("not a string: " + tok)
    return m.group(1).replace('\\"', '"')


def num(tok):
    return float(tok.strip().rstrip("f"))


def native_rows():
    src = open(os.path.join(NATIVE, "DaedalusSettings.cpp"), encoding="utf-8").read()
    body = src[src.index("FDaedalusSettings::FDaedalusSettings()"):]
    body = body[:body.index("Load();")]
    consts = {m.group(1): m.group(2) for m in re.finditer(r'const TCHAR\* (\w+) = TEXT\("([^"]*)"\);', body)}
    tabs = re.search(r"Tabs = \{(.*?)\};", body, re.S)
    native_tabs = [cstr(t, consts) for t in split_args(tabs.group(1))]
    rows = []
    for m in re.finditer(r'\n\s*Add\((.*?)\);\s*(?=\n)', body, re.S):
        a = split_args(m.group(1))
        kind = a[5].split("::")[-1].lower()
        r = {"id": cstr(a[0], consts), "tab": cstr(a[1], consts), "section": cstr(a[2], consts), "label": cstr(a[3], consts),
             "help": cstr(a[4], consts), "kind": kind, "default": num(a[6])}
        r["min"], r["max"], r["step"] = (num(a[7]) if len(a) > 7 else 0.0), (num(a[8]) if len(a) > 8 else 1.0), (num(a[9]) if len(a) > 9 else 1.0)
        r["unit"] = cstr(a[10], consts) if len(a) > 10 else ""
        r["choices"] = [cstr(c, consts) for c in split_args(a[11].strip()[1:-1])] if len(a) > 11 else []
        rows.append(r)
    return native_tabs, rows


def native_layouts():
    src = open(os.path.join(NATIVE, "DaedalusHero.cpp"), encoding="utf-8").read()
    fn = src[src.index("TMap<FName, TArray<FString>> PadButtons(int32 Layout)"):]
    fn = fn[:fn.index("return M;")]
    keys = lambda s: re.findall(r'TEXT\("([^"]+)"\)', s)
    base = {m.group(1): keys(m.group(2)) for m in re.finditer(r'M\.Add\("(\w+)", \{(.*?)\}\);', fn)}
    buttons = {0: dict(base)}
    for m in re.finditer(r"case (\d+):.*?\n(.*?)break;", fn, re.S):
        lay = dict(base)
        for o in re.finditer(r'M\["(\w+)"\] = \{(.*?)\};', m.group(2)):
            lay[o.group(1)] = keys(o.group(2))
        buttons[int(m.group(1))] = lay
    rb = src[src.index("void ADaedalusHero::RebuildBindings()"):]
    sw = rb[rb.index("switch (AppliedStickLayout)"):rb.index("MapSpec(MoveAction, MoveX.Key")]
    sticks = {0: {"MoveX": "Gamepad_LeftX", "MoveY": "Gamepad_LeftY", "LookX": "Gamepad_RightX", "LookY": "Gamepad_RightY"}}
    for m in re.finditer(r"case (\d+):.*?\n(.*?)break;", sw, re.S):
        lay = dict(sticks[0])
        for o in re.finditer(r'(MoveX|MoveY|LookX|LookY) = \{TEXT\("(\w+)"\)', m.group(2)):
            lay[o.group(1)] = o.group(2)
        sticks[int(m.group(1))] = lay
    extra = re.findall(r'MapSpec\((\w+)Action, TEXT\("(Gamepad_[A-Za-z_]+)"\)\)', rb)
    return buttons, sticks, extra


# Unreal key name -> the web pad module's positional name
UE_TO_POS = {"Gamepad_FaceButton_Bottom": "a", "Gamepad_FaceButton_Right": "b", "Gamepad_FaceButton_Left": "x", "Gamepad_FaceButton_Top": "y",
             "Gamepad_LeftShoulder": "l", "Gamepad_RightShoulder": "r", "Gamepad_LeftTriggerAxis": "zl", "Gamepad_RightTriggerAxis": "zr",
             "Gamepad_LeftThumbstick": "l3", "Gamepad_RightThumbstick": "r3", "Gamepad_DPad_Up": "up", "Gamepad_DPad_Down": "down",
             "Gamepad_DPad_Left": "left", "Gamepad_DPad_Right": "right", "Gamepad_Special_Right": "start", "Gamepad_Special_Left": "back",
             "Gamepad_LeftX": "lx", "Gamepad_LeftY": "ly", "Gamepad_RightX": "rx", "Gamepad_RightY": "ry"}


def build():
    native_tabs, nrows = native_rows()
    nat = {r["id"]: r for r in nrows}
    rows, problems = [], []
    for tab in SS.TABS:
        for section in tab["sections"]:
            for rid in section["rows"]:
                if rid in nat:
                    r = dict(nat[rid])
                    r["native"] = True
                    if (r["tab"], r["section"]) != (tab["id"], section["name"]):
                        r["native_place"] = [r["tab"], r["section"]]
                elif rid in SS.NEW:
                    r = dict(SS.NEW[rid]); r["id"] = rid; r["native"] = False
                else:
                    problems.append("row %s is placed but defined nowhere" % rid); continue
                r["tab"], r["section"] = tab["id"], section["name"]
                r["consumers"] = SS.CONSUMERS.get(rid, ["unreal"] if r["native"] else [])
                rows.append(r)
    placed = {r["id"] for r in rows}
    for rid in nat:
        if rid not in placed:
            problems.append("native row %s is not placed on any tab" % rid)
    for rid in SS.NEW:
        if rid not in placed:
            problems.append("new row %s is not placed on any tab" % rid)
    for r in rows:
        if not r["native"] and not r["consumers"]:
            problems.append("new row %s has no consumer (rows are only added when something reads them)" % r["id"])
    buttons, sticks, extra = native_layouts()
    layouts = {
        "buttons": {nat["ButtonLayout"]["choices"][k]: {a: [UE_TO_POS.get(x, x) for x in ks] for a, ks in v.items()} for k, v in sorted(buttons.items())},
        "sticks": {nat["ThumbstickLayout"]["choices"][k]: {a: UE_TO_POS.get(x, x) for a, x in v.items()} for k, v in sorted(sticks.items())},
        "fixed": {a: UE_TO_POS.get(k, k) for a, k in extra},
        "source": "DaedalusHero.cpp PadButtons() and RebuildBindings()",
    }
    schema = {"schema": "daedalus.settings-schema/v1", "layout_of": "Halo Infinite (Controller, Keyboard/Mouse, Video, Audio, Gameplay, Accessibility)",
              "storage": {"unreal": "Saved/Config/DaedalusSettings.json", "web": "localStorage daedalus.settings", "format": "flat {\"Id\": number}"},
              "tabs": [{"id": t["id"], "sections": [s["name"] for s in t["sections"]]} for t in SS.TABS],
              "native_tabs": native_tabs, "rows": rows, "layouts": layouts, "research": SS.RESEARCH}
    return schema, problems


def main():
    schema, problems = build()
    check = "--check" in sys.argv
    text = json.dumps(schema, indent=1)
    if check:
        old = open(OUT, encoding="utf-8").read() if os.path.exists(OUT) else ""
        if old != text:
            problems.append("settings-schema.json is stale: run tools/settings/build_schema.py")
        if os.path.exists(WEB) and open(WEB, encoding="utf-8").read() != text:
            problems.append("web copy of settings-schema.json is stale")
    else:
        os.makedirs(os.path.dirname(OUT), exist_ok=True)
        open(OUT, "w", encoding="utf-8").write(text)
        os.makedirs(os.path.dirname(WEB), exist_ok=True)
        shutil.copy(OUT, WEB)
    rows = schema["rows"]
    per_tab = {t["id"]: sum(1 for r in rows if r["tab"] == t["id"]) for t in schema["tabs"]}
    moved = [r["id"] + " " + "/".join(r["native_place"]) + " -> " + r["tab"] + "/" + r["section"] for r in rows if r.get("native_place")]
    print("rows %d (native %d, new %d) per tab %s" % (len(rows), sum(r["native"] for r in rows), sum(not r["native"] for r in rows), per_tab))
    print("native tabs %s; Infinite tabs %s" % (schema["native_tabs"], [t["id"] for t in schema["tabs"]]))
    print("button layouts %s; stick layouts %s" % (list(schema["layouts"]["buttons"]), list(schema["layouts"]["sticks"])))
    if moved:
        print("native rows placed differently from the C++ (Infinite placement):", moved)
    for p in problems:
        print("PROBLEM", p)
    print("SETTINGS SCHEMA", "OK" if not problems else "FAIL")
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
