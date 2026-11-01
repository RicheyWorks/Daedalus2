# SPDX-License-Identifier: MIT
"""Golden file for DaedalusDiskSaverPyJsonCore.h (json.dumps, ensure_ascii=True, sort_keys=True).

Python is the authority. Each line is one call. Inputs and the dumped text are hex so spaces,
quotes and non-ASCII bytes survive the fixture. RAW lines are the header's rule for malformed
UTF-8: one bad or truncated sequence becomes U+FFFD, then json.dumps of that string.

  python tools/streaming/disksaver_pyjson_parity.py            # print the golden file
  python tools/streaming/disksaver_pyjson_parity.py --check    # exit 1 if the checked-in file is stale
  python tools/streaming/disksaver_pyjson_parity.py --write    # rewrite it
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
GOLDEN = os.path.join(ROOT, "engines", "unreal", "core-test", "disksaver_pyjson_parity.txt")

STRINGS = (
    "", "a", " ", "  ", '"', "\\", "/", "\n", "\r", "\t", "\b", "\f",
    "\x00", "\x1f", "\x7f", "line\nnext", "a b", "say \"hi\"",
    "é", "λ", "☃", "😀", "a😀b", "\ud800", "\udfff", "éλ",
)
INTS = (0, 1, -1, 42, -42, 2 ** 31 - 1, -(2 ** 31), 2 ** 62, -(2 ** 62))
OBJECTS = (
    {"b": 1, "a": 2},
    {"z": "x", "a": "y"},
    {"é": 1, "a": 2, "λ": 3},
    {"m": None, "k": True, "j": False},
    {'quote"': "a b", " ": 0},
    {"\u0080": 1, "A": 2},
)
LISTS = (
    [],
    [1, "a", None],
    [True, False, "é"],
    [" ", "\n", 0],
)
# One bad or truncated UTF-8 sequence becomes one U+FFFD, then the rest of the bytes.
RAWS = (
    b"\xff",
    b"\x80",
    b"\xc3",
    b"\xe2\x82",
    b"\xf0\x9f\x98",
    b"A\xffB",
    b"\xc3\xa9",
)


def hx(text):
    if isinstance(text, str):
        text = text.encode("utf-8", "surrogatepass")
    return text.hex() or "-"


def as_header(raw):
    """The header's read: a bad or truncated sequence is one U+FFFD and one byte."""
    out = []
    i = 0
    while i < len(raw):
        c = raw[i]
        if c < 0x80:
            length = 1
        elif c >> 5 == 6:
            length = 2
        elif c >> 4 == 14:
            length = 3
        elif c >> 3 == 30:
            length = 4
        else:
            length = 0
        if length == 0 or i + length > len(raw):
            out.append("\ufffd")
            i += 1
            continue
        value = c if length == 1 else c & {2: 0x1F, 3: 0x0F, 4: 0x07}[length]
        ok = True
        for k in range(1, length):
            d = raw[i + k]
            if (d & 0xC0) != 0x80:
                ok = False
                break
            value = (value << 6) | (d & 0x3F)
        if not ok:
            out.append("\ufffd")
            i += 1
            continue
        out.append(chr(value))
        i += length
    return "".join(out)


def dumped(value, compact=False):
    if compact:
        return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    return json.dumps(value, ensure_ascii=True, sort_keys=True)


def lines():
    out = ["# disksaver_pyjson_parity.txt: json.dumps(ensure_ascii=True, sort_keys=True) via "
           "tools/streaming/disksaver_pyjson_parity.py. Do not hand-edit."]
    for text in STRINGS:
        raw = text.encode("utf-8", "surrogatepass")
        out.append("STR %s %s" % (hx(raw), hx(json.dumps(text, ensure_ascii=True))))
    for number in INTS:
        out.append("INT %d %s" % (number, hx(json.dumps(number))))
    for flag in (False, True):
        out.append("BOOL %d %s" % (int(flag), hx(json.dumps(flag))))
    out.append("NULL %s" % hx(json.dumps(None)))
    for raw in RAWS:
        out.append("RAW %s %s" % (raw.hex(), hx(json.dumps(as_header(raw), ensure_ascii=True))))
    for obj in OBJECTS:
        for compact in (False, True):
            parts = ["OBJ", "1" if compact else "0", str(len(obj))]
            for key, value in obj.items():
                parts.append(hx(key))
                parts.append(hx(json.dumps(value, ensure_ascii=True)))
            parts.append(hx(dumped(obj, compact)))
            out.append(" ".join(parts))
    for values in LISTS:
        for compact in (False, True):
            parts = ["LIST", "1" if compact else "0", str(len(values))]
            for value in values:
                parts.append(hx(json.dumps(value, ensure_ascii=True)))
            parts.append(hx(dumped(values, compact)))
            out.append(" ".join(parts))
    return out


def text():
    return "\n".join(lines()) + "\n"


def main(argv):
    body = text()
    if "--write" in argv:
        with open(GOLDEN, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(body)
        return 0
    if "--check" in argv:
        try:
            with open(GOLDEN, encoding="utf-8") as handle:
                stale = handle.read() != body
        except OSError:
            stale = True
        print("pyjson parity " + ("STALE" if stale else "up to date"))
        return 1 if stale else 0
    sys.stdout.write(body)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
