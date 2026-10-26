# SPDX-License-Identifier: MIT
"""Bounded read-only XML/pixel verification of fresh storyboard artifacts.

This verifies static artifact semantics, not native or visual colour matching.
"""
import json
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET

SVG = "{http://www.w3.org/2000/svg}"
SB = "{urn:daedalus:motif-storyboard:1}"
LIMIT = 64 * 1024


def flag(value):
    return "1" if value else "0"


def parent(value):
    return value or "-none"


def valid_id(value):
    return bool(re.fullmatch(r"[0-9a-f]{32}", value)) and bool(int(value, 16))


def bounded_read(path, maximum):
    with path.open("rb") as stream:
        data = stream.read(maximum + 1)
    assert len(data) <= maximum, "oversized fixture"
    return data


def parse_static(data, count):
    assert 0 < len(data) <= LIMIT
    assert all(32 <= value <= 126 or value == 10 for value in data), "non-ASCII/control content"
    upper = data.upper()
    assert not any(token in upper for token in (b"<!DOCTYPE", b"<!ENTITY", b"<?")), "active XML declaration"
    root = ET.fromstring(data)
    height = 900 if count == 2 else 1410
    assert root.tag == SVG + "svg" and root.attrib == {
        "version": "1.1", "width": "1200", "height": str(height), "viewBox": f"0 0 1200 {height}",
        "role": "img", "aria-labelledby": "sheet-title sheet-desc"}
    allowed = {SVG + name for name in ("svg", "title", "desc", "metadata", "g", "rect", "text")}
    allowed |= {SB + name for name in ("storyboard", "playback", "palette", "colour", "frames", "frame")}
    numbers = {"x", "y", "width", "height", "font-size", "stroke-width"}
    attributes = numbers | {"version", "viewBox", "role", "aria-labelledby", "id", "fill", "stroke", "text-anchor",
                            "data-frame", "data-order", "data-current", "data-pixels", "data-cell", "data-index", "data-palette"}
    for node in root.iter():
        assert node.tag in allowed, "unexpected or active element"
        for name, value in node.attrib.items():
            assert not name.lower().startswith("on") and "href" not in name.lower()
            assert not re.search(r"url\s*\(|javascript:|data:|file:|://", value, re.IGNORECASE), "active/external reference"
            if node.tag.startswith(SVG):
                assert name in attributes, "unapproved SVG attribute/font reference"
                if name in numbers:
                    assert re.fullmatch(r"\d+", value), "non-integer or negative coordinate"
        if node.tag == SVG + "rect":
            x, y, width, box_height = (int(node.get(name)) for name in ("x", "y", "width", "height"))
            assert width > 0 and box_height > 0 and x + width <= 1200 and y + box_height <= height
    title, desc = root.findall(SVG + "title"), root.findall(SVG + "desc")
    assert len(title) == len(desc) == 1 and title[0].text and desc[0].text
    assert title[0].get("id") == "sheet-title" and desc[0].get("id") == "sheet-desc"
    metadata = root.findall(SVG + "metadata")
    assert len(metadata) == 1 and len(metadata[0]) == 1 and metadata[0][0].tag == SB + "storyboard"
    return root, metadata[0][0]


def verify(case):
    count, index = case["Count"], case["Index"]
    assert count in (2, 3, 4) and 0 <= index < count and case["Fps"] in (2, 4) and case["Direction"] in (-1, 1)
    assert type(case["Playing"]) is bool and valid_id(case["Id"])
    assert not case["Parent"] or (valid_id(case["Parent"]) and case["Parent"] != case["Id"])
    colours, documents = case["Palette"], case["Frames"]
    assert len(colours) == 8 and all(re.fullmatch(r"#[0-9a-fA-F]{6}", colour) for colour in colours)
    assert len(documents) == count and len({doc["Id"] for doc in documents}) == count
    for doc in documents:
        assert valid_id(doc["Id"]) and re.fullmatch(r"[0-7]{64}", doc["Pixels"])
        assert not doc["Parent"] or (valid_id(doc["Parent"]) and doc["Parent"] != doc["Id"])
    root, metadata = parse_static(case["Svg"].encode("ascii"), count)
    assert metadata.attrib == {"version": "1", "artifact-id": case["Id"], "artifact-parent": parent(case["Parent"]), "frame-count": str(count)}
    assert len(metadata) == 3
    playback, palette, frames = (metadata.find(SB + name) for name in ("playback", "palette", "frames"))
    assert playback is not None and not len(playback) and playback.attrib == {
        "current-index": str(index), "fps": str(case["Fps"]), "direction": str(case["Direction"]),
        "playing": flag(case["Playing"]), "state-label": "at capture"}
    assert palette is not None and palette.attrib == {"version": "1", "space": "srgb", "encoding": "#RRGGBB"} and len(palette) == 8
    for slot, colour in enumerate(palette):
        assert colour.tag == SB + "colour" and not len(colour) and colour.attrib == {"index": str(slot), "value": colours[slot]}
    assert frames is not None and not frames.attrib and len(frames) == count
    for slot, frame in enumerate(frames):
        document = documents[slot]
        assert frame.tag == SB + "frame" and not len(frame) and frame.attrib == {
            "index": str(slot), "order": str(slot + 1), "dgm-id": document["Id"], "dgm-parent": parent(document["Parent"]),
            "palette-indices": document["Pixels"]}
    cards = [node for node in root.iter(SVG + "g") if "data-frame" in node.attrib]
    assert len(cards) == count
    positions = []
    for slot, card in enumerate(cards):
        assert card.attrib == {"data-frame": str(slot), "data-order": str(slot + 1), "data-current": flag(slot == index)}, "document order changed"
        panel = card.find(SVG + "rect")
        assert panel is not None and int(panel.get("stroke-width")) == (4 if slot == index else 1)
        left, top, width, height = (int(panel.get(name)) for name in ("x", "y", "width", "height"))
        positions.append((left, top))
        groups = card.findall(SVG + "g")
        assert len(groups) == 1 and groups[0].attrib == {"data-pixels": "1"}
        pixels = list(groups[0])
        assert len(pixels) == 64 and all(pixel.tag == SVG + "rect" for pixel in pixels)
        assert {int(pixel.get("data-cell")) for pixel in pixels} == set(range(64))
        first_x = min(int(pixel.get("x")) for pixel in pixels)
        first_y = min(int(pixel.get("y")) for pixel in pixels)
        size = int(pixels[0].get("width"))
        assert size > 0 and left <= first_x and top <= first_y and first_x + 8 * size <= left + width and first_y + 8 * size <= top + height
        for pixel in pixels:
            cell = int(pixel.get("data-cell"))
            expected = documents[slot]["Pixels"][cell]
            assert pixel.attrib == {"data-cell": str(cell), "data-index": expected,
                                    "x": str(first_x + (cell % 8) * size), "y": str(first_y + (cell // 8) * size),
                                    "width": str(size), "height": str(size), "fill": colours[int(expected)]}, "row-major pixel/palette mismatch"
        words = " ".join(node.text or "" for node in card.findall(SVG + "text"))
        assert f"FRAME {slot + 1}" in words and ("CURRENT AT CAPTURE" in words) == (slot == index)
        assert f"DGM ID: {documents[slot]['Id']}" in words and f"DGM parent: {parent(documents[slot]['Parent'])}" in words
    assert positions[0][0] < positions[1][0] and positions[0][1] == positions[1][1]
    if count > 2:
        assert positions[2][0] == positions[0][0] and positions[2][1] > positions[0][1]
    if count == 4:
        assert positions[3][0] == positions[1][0] and positions[3][1] == positions[2][1]
    swatches = [node for node in root.iter(SVG + "g") if "data-palette" in node.attrib]
    assert len(swatches) == 8 and {int(node.get("data-palette")) for node in swatches} == set(range(8))
    for node in swatches:
        slot = int(node.get("data-palette"))
        assert node.find(SVG + "rect").get("fill") == colours[slot]
        assert f"{slot} {colours[slot]}" in (node.find(SVG + "text").text or "")
    all_words = " ".join(node.text or "" for node in root.iter(SVG + "text"))
    state = f"At capture: frame {index + 1} of {count} / {case['Fps']} fps / {'forward' if case['Direction'] == 1 else 'reverse'} / {'playing' if case['Playing'] else 'paused'}"
    assert state in all_words and f"Artifact ID: {case['Id']}" in all_words and f"Artifact parent: {parent(case['Parent'])}" in all_words
    assert "not a saved flipbook or profile" in all_words
    return count * 64


def main():
    assert len(sys.argv) == 2, "pass only the fresh check directory"
    directory = Path(sys.argv[1])
    report = json.loads(bounded_read(directory / "cases.json", 1024 * 1024))
    assert report["Schema"] == 1 and report["MaxSvgBytes"] == LIMIT and len(report["Cases"]) == 8
    cases = report["Cases"]
    assert len({case["Id"] for case in cases}) == len(cases)
    assert {case["Count"] for case in cases} == {2, 3, 4}
    assert any(case["Count"] == 4 and case["Index"] == 3 and case["Fps"] == 4 and case["Direction"] == -1 and case["Playing"] for case in cases)
    assert any(len({doc["Pixels"] for doc in case["Frames"]}) == 1 and case["Count"] > 2 for case in cases)
    assert any(case["Id"] == case["Frames"][0]["Id"] for case in cases), "separate identity namespaces need no cross-domain value restriction"
    pixels = sum(verify(case) for case in cases)
    assert report["MaximumObserved"] == max(len(case["Svg"].encode("ascii")) for case in cases) <= LIMIT
    assert set(report["Examples"]) == {"two_frames.svg", "four_frames_reverse.svg"}
    for filename, identity in report["Examples"].items():
        case = next(case for case in cases if case["Id"] == identity)
        assert bounded_read(directory / filename, LIMIT) == case["Svg"].encode("ascii")
    print(f"8 XML storyboard snapshots verified;{pixels} exact row-major pixel rectangles;2/3/4 original frame order and capture metadata;visual/native colours untested.")


if __name__ == "__main__":
    main()
