# SPDX-License-Identifier: MIT
"""Read-only bounded validation of freshly emitted blueprint print fixtures.

Uses stdlib XML parsing and independent literal graph/visibility rules. This
checks artifact semantics and static content, not rendered visual acceptance.
"""
import itertools
import json
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET

SVG = "{http://www.w3.org/2000/svg}"
BP = "{urn:daedalus:blueprint-print:1}"
LIMIT = 64 * 1024
LINKS = ((0, 1), (1, 2), (3, 4), (4, 5), (6, 7), (7, 8),
         (0, 3), (1, 4), (2, 5), (3, 6), (4, 7), (5, 8))
BRIDGES = (
    ("Open Spans", (0, 2, 5), (0, 1, 4), 4095, 16),
    ("Side Repair", (0, 2, 5), (0, 1, 4), 3067, 16),
    ("Long Crossing", (0, 1, 4), (0, 2, 5), 3838, 18),
)
SKYLINES = (
    ("First Towers", (4, 3, 2, 1), (1, 2, 2, 2), (4, 3, 2, 1), (1, 2, 2, 2), "1000000000000003"),
    ("Courtyard View", (2, 2, 1, 3), (2, 2, 3, 1), (3, 1, 2, 2), (2, 2, 3, 1), "0000010000300000"),
    ("Open Skyline", (2, 1, 3, 2), (0, 0, 0, 0), (2, 4, 1, 2), (0, 0, 0, 0), "0000000000000000"),
)


def csv(values):
    return ",".join(map(str, values))


def flags(values):
    return "".join("1" if value else "0" for value in values)


def bounded_read(path, maximum):
    with path.open("rb") as stream:
        data = stream.read(maximum + 1)
    assert len(data) <= maximum, "oversized fixture"
    return data


def static_xml(data):
    assert 0 < len(data) <= LIMIT
    assert all(32 <= value <= 126 or value == 10 for value in data), "non-ASCII/control bytes"
    upper = data.upper()
    assert not any(token in upper for token in (b"<!DOCTYPE", b"<!ENTITY", b"<?")), "active XML declaration"
    root = ET.fromstring(data)
    assert root.tag == SVG + "svg"
    assert root.attrib == {"version": "1.1", "width": "1000", "height": "800", "viewBox": "0 0 1000 800",
                           "role": "img", "aria-labelledby": "print-title print-desc"}
    allowed = {SVG + name for name in ("svg", "title", "desc", "metadata", "g", "rect", "circle", "line", "text")}
    allowed |= {BP + name for name in ("print", "snapshot", "metrics", "bridge-rule", "link", "skyline-rule")}
    numeric = {"x", "y", "x1", "y1", "x2", "y2", "cx", "cy", "r", "width", "height", "rx", "font-size", "stroke-width"}
    attributes = numeric | {"version", "viewBox", "role", "aria-labelledby", "id", "fill", "stroke", "text-anchor", "stroke-dasharray",
                            "data-link", "data-state", "data-length", "data-pad", "data-linked", "data-cell", "data-height", "data-fixed",
                            "data-conflict", "data-side", "data-line", "data-clue"}
    for element in root.iter():
        assert element.tag in allowed, "unexpected or active element"
        for name, value in element.attrib.items():
            assert not name.lower().startswith("on") and "href" not in name.lower()
            assert not re.search(r"url\s*\(|javascript:|data:|file:|://", value, re.IGNORECASE), "external/active attribute"
            if element.tag.startswith(SVG):
                assert name in attributes, "unapproved SVG attribute/font/resource reference"
                if name in numeric:
                    assert re.fullmatch(r"-?\d+", value), "non-integer coordinate"
    titles, descriptions = root.findall(SVG + "title"), root.findall(SVG + "desc")
    assert len(titles) == len(descriptions) == 1 and titles[0].text and descriptions[0].text
    assert titles[0].get("id") == "print-title" and descriptions[0].get("id") == "print-desc"
    metadata = root.findall(SVG + "metadata")
    assert len(metadata) == 1 and len(metadata[0]) == 1 and metadata[0][0].tag == BP + "print"
    return root, metadata[0][0]


def bridge_oracle(rule, mask):
    _, columns, rows, allowed, allowance = BRIDGES[rule]
    assert 0 <= mask < 4096 and not mask & ~allowed
    lengths = [abs(columns[a % 3] - columns[b % 3]) + abs(rows[a // 3] - rows[b // 3]) for a, b in LINKS]
    adjacency = [set() for _ in range(9)]
    used = 0
    for index, (a, b) in enumerate(LINKS):
        if mask & (1 << index):
            adjacency[a].add(b)
            adjacency[b].add(a)
            used += lengths[index]
    assert used <= allowance
    groups = []
    remaining = set(range(9))
    while remaining:
        component = {min(remaining)}
        frontier = list(component)
        while frontier:
            for node in adjacency[frontier.pop()]:
                if node not in component:
                    component.add(node)
                    frontier.append(node)
        remaining -= component
        groups.append(component)
    home = next(group for group in groups if 0 in group)
    return {"used-length": str(used), "pads-connected": str(len(home)), "components": str(len(groups)),
            "selected-count": str(mask.bit_count()), "within-length": "1", "linked-to-home": flags(i in home for i in range(9))}, lengths, len(home) == 9


def sight(line):
    return sum(height > 0 and all(previous < height for previous in line[:index]) for index, height in enumerate(line))


def skyline_oracle(rule, digits):
    assert re.fullmatch(r"[0-4]{16}", digits)
    _, left, right, top, bottom, givens = SKYLINES[rule]
    cells = list(map(int, digits))
    assert all(fixed == "0" or fixed == current for fixed, current in zip(givens, digits)), "wrong fixed height"
    rows = [cells[row * 4:(row + 1) * 4] for row in range(4)]
    columns = [cells[column::4] for column in range(4)]
    conflicts = [False] * 16
    for a in range(16):
        for b in range(a + 1, 16):
            if cells[a] and cells[a] == cells[b] and (a // 4 == b // 4 or a % 4 == b % 4):
                conflicts[a] = conflicts[b] = True
    seen = ([sight(row) for row in rows], [sight(row[::-1]) for row in rows],
            [sight(column) for column in columns], [sight(column[::-1]) for column in columns])
    matches = 0
    for expected, actual, lines in zip((left, right, top, bottom), seen, (rows, rows, columns, columns)):
        matches += sum(bool(clue) and all(line) and len(set(line)) == 4 and clue == count
                       for clue, count, line in zip(expected, actual, lines))
    count = sum(bool(clue) for edge in (left, right, top, bottom) for clue in edge)
    filled = sum(bool(height) for height in cells)
    metrics = {"filled": str(filled), "clue-matches": str(matches), "clue-count": str(count), "givens-match": "1",
               "latin-possible": "0" if any(conflicts) else "1", "conflicts": flags(conflicts),
               "left": csv(seen[0]), "right": csv(seen[1]), "top": csv(seen[2]), "bottom": csv(seen[3]),
               "row-full": flags(all(row) for row in rows), "column-full": flags(all(column) for column in columns)}
    return metrics, conflicts, filled == 16 and not any(conflicts) and matches == count


def verify_case(case):
    root, metadata = static_xml(case["Svg"].encode("ascii"))
    kind, rule = case["Kind"], case["Rule"]
    assert kind in ("bridge", "skyline") and type(rule) is int and 0 <= rule < 3
    assert re.fullmatch(r"[0-9a-f]{32}", case["Id"]) and int(case["Id"], 16)
    parent = case["Parent"]
    assert not parent or (re.fullmatch(r"[0-9a-f]{32}", parent) and int(parent, 16) and parent != case["Id"])
    plan = (BRIDGES if kind == "bridge" else SKYLINES)[rule]
    if kind == "bridge":
        metrics, lengths, complete = bridge_oracle(rule, case["Mask"])
        snapshot = {"mask": str(case["Mask"])}
        definition = metadata.find(BP + "bridge-rule")
        assert definition is not None and definition.attrib == {
            "columns": csv(plan[1]), "rows": csv(plan[2]), "allowed-mask": str(plan[3]), "allowance": str(plan[4]),
            "pads": "9", "links": "12", "length": "manhattan", "goal": "connect-all-within-allowance"}
        links = definition.findall(BP + "link")
        assert len(links) == 12 and len(definition) == 12
        for index, (a, b) in enumerate(LINKS):
            assert links[index].attrib == {"index": str(index), "from": str(a), "to": str(b), "length": str(lengths[index])}
        groups = [node for node in root.iter(SVG + "g") if "data-link" in node.attrib]
        assert len(groups) == 12 and {int(node.get("data-link")) for node in groups} == set(range(12))
        for node in groups:
            index = int(node.get("data-link"))
            state = "closed" if not plan[3] & (1 << index) else "in" if case["Mask"] & (1 << index) else "out"
            assert node.get("data-state") == state and node.get("data-length") == str(lengths[index])
            assert node.find(SVG + "text").text == f"{index + 1}:{lengths[index]}"
        pads = [node for node in root.iter(SVG + "g") if "data-pad" in node.attrib]
        assert len(pads) == 9 and {int(node.get("data-pad")) for node in pads} == set(range(9))
        for pad in pads:
            assert pad.get("data-linked") == metrics["linked-to-home"][int(pad.get("data-pad"))]
    else:
        metrics, conflicts, complete = skyline_oracle(rule, case["Heights"])
        snapshot = {"heights": case["Heights"]}
        definition = metadata.find(BP + "skyline-rule")
        assert definition is not None and not len(definition) and definition.attrib == {
            "side": "4", "heights": "1,2,3,4", "empty": "0", "uniqueness": "rows-and-columns", "clue": "record-highs",
            "left": csv(plan[1]), "right": csv(plan[2]), "top": csv(plan[3]), "bottom": csv(plan[4]), "givens": plan[5]}
        cells = [node for node in root.iter(SVG + "g") if "data-cell" in node.attrib]
        assert len(cells) == 16 and {int(node.get("data-cell")) for node in cells} == set(range(16))
        for node in cells:
            index = int(node.get("data-cell"))
            height, fixed, conflict = case["Heights"][index], plan[5][index] != "0", conflicts[index]
            assert node.get("data-height") == height and node.get("data-fixed") == flags([fixed]) and node.get("data-conflict") == flags([conflict])
            words = [text.text for text in node.findall(SVG + "text")]
            assert height in words and ("F" in words) == fixed and ("!" in words) == conflict
            assert len(node.findall(SVG + "rect")) == 1 + int(height), "tower layer count differs from height"
        clues = [node for node in root.iter(SVG + "g") if "data-side" in node.attrib]
        assert len(clues) == 16 and {(node.get("data-side"), int(node.get("data-line"))) for node in clues} == set(itertools.product(("left", "right", "top", "bottom"), range(4)))
        for node in clues:
            side = ("left", "right", "top", "bottom").index(node.get("data-side"))
            number = plan[side + 1][int(node.get("data-line"))]
            assert node.get("data-clue") == str(number) and node.find(SVG + "text").text == (str(number) if number else "0 OPEN")
    assert len(metadata) == 3
    assert metadata.attrib == {"version": "1", "kind": kind, "rule": str(rule), "name": plan[0], "id": case["Id"],
                               "parent": parent or "-none", "current-complete": flags([complete])}
    assert metadata.find(BP + "snapshot").attrib == snapshot and metadata.find(BP + "metrics").attrib == metrics
    all_text = " ".join(node.text or "" for node in root.iter(SVG + "text"))
    assert case["Id"] in all_text and (parent or "-none") in all_text and "not a saved game" in all_text
    assert ("CURRENT SNAPSHOT: COMPLETE" in all_text) == complete
    return complete


def main():
    assert len(sys.argv) == 2, "pass only the fresh check directory"
    directory = Path(sys.argv[1])
    report = json.loads(bounded_read(directory / "cases.json", 1024 * 1024))
    assert report["Schema"] == 1 and report["MaxSvgBytes"] == LIMIT and len(report["Cases"]) == 19
    cases = report["Cases"]
    assert len({case["Id"] for case in cases}) == len(cases)
    completed = [set(), set(), set()]
    for case in cases:
        complete = verify_case(case)
        if case["Kind"] == "skyline" and complete:
            completed[case["Rule"]].add(case["Heights"])
    # Independent whole-row permutation/column-set enumeration proves that the
    # exported examples include EVERY valid alternative, not an authored answer.
    expected = [set(), set(), set()]
    rows = tuple(itertools.permutations(range(1, 5)))
    for grid in itertools.product(rows, repeat=4):
        if any(len({grid[row][column] for row in range(4)}) != 4 for column in range(4)):
            continue
        digits = "".join(str(height) for row in grid for height in row)
        for rule in range(3):
            if any(fixed != "0" and fixed != current for fixed, current in zip(SKYLINES[rule][5], digits)):
                continue
            if skyline_oracle(rule, digits)[2]:
                expected[rule].add(digits)
    assert [len(group) for group in expected] == [1, 2, 3] and completed == expected
    assert report["MaximumObserved"] == max(len(case["Svg"].encode("ascii")) for case in cases) <= LIMIT
    assert set(report["Examples"]) == {"bridge.svg", "skyline.svg"}
    for filename, identity in report["Examples"].items():
        case = next(case for case in cases if case["Id"] == identity)
        assert bounded_read(directory / filename, LIMIT) == case["Svg"].encode("ascii")
    for hostile in (b"x" * (LIMIT + 1), b'<!DOCTYPE svg><svg/>', b'<svg xmlns="http://www.w3.org/2000/svg"><script/></svg>'):
        try:
            static_xml(hostile)
        except (AssertionError, ET.ParseError):
            pass
        else:
            raise AssertionError("verifier admitted active or oversized content")
    print("19 XML snapshots verified: full specs/current metrics, static ASCII content, all6 skyline alternatives, exact2 example files; visuals untested.")


if __name__ == "__main__":
    main()
