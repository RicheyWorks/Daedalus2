# SPDX-License-Identifier: MIT
"""Battle-screen UI for the two RPG realms — original pixel art, pure numpy.

    python tools/blender/rpg_battle_ui.py OUT_ROOT

Per realm (OUT_ROOT/claude-battle-kit/<realm>/ui/):
  Window_9slice.png   a 24 x 24 window (8 px corners) to stretch as a 9-slice: Portal = black box with a white
                      rounded border; Prismheart = vertical blue gradient with a bevelled silver border
  Cursor.png          pointing-hand cursor, 2-frame bob strip
  Digits.png          0-9 damage digits strip (5 x 7 glyphs; Prismheart adds an outline and a heal-green set
                      Digits_Heal.png), plus Miss.png
  Status_<Name>.png   8 x 8 status icons: Poison, Sleep, Haste, Slow, Protect, KO, Blind, Silence
  Bar_HP / Bar_MP / Bar_ATB.png  3-cap gauges (frame, fill, empty) for 16-bit; Portal shows numbers only
  mockup.png          a full battle screen assembled from the kit: backdrop + enemies + party + windows + numbers
All shown x4 (_1x.png native). mockup.png composes existing battle-kit backdrops and battle sprites when present.
"""
import glob
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pixel_png as P  # noqa: E402

K = 4
DIGITS = {
    "0": [".###.", "#...#", "#..##", "#.#.#", "##..#", "#...#", ".###."],
    "1": ["..#..", ".##..", "..#..", "..#..", "..#..", "..#..", ".###."],
    "2": [".###.", "#...#", "....#", "...#.", "..#..", ".#...", "#####"],
    "3": ["####.", "....#", "....#", ".###.", "....#", "....#", "####."],
    "4": ["...#.", "..##.", ".#.#.", "#..#.", "#####", "...#.", "...#."],
    "5": ["#####", "#....", "####.", "....#", "....#", "#...#", ".###."],
    "6": [".###.", "#....", "#....", "####.", "#...#", "#...#", ".###."],
    "7": ["#####", "....#", "...#.", "..#..", ".#...", ".#...", ".#..."],
    "8": [".###.", "#...#", "#...#", ".###.", "#...#", "#...#", ".###."],
    "9": [".###.", "#...#", "#...#", ".####", "....#", "....#", ".###."],
}
MISS = ["#...#.###..###..###.", "##.##..#..#....#....", "#.#.#..#...###..###.", "#...#..#......#....#",
        "#...#..#......#....#", "#...#..#..#...##...#", "#...#.###..###..###."]
CURSOR = ["##......", "#w#.....", "#ww####.", "#wwwwww#", "#wwwwww#", "#wwwww#.", ".#####..", "........"]
STATUS = {
    "Poison": ("#78b020", [".##.", "#..#", "#..#", ".##."], "bubbles"),
    "Sleep": ("#a8a8f0", ["####", "..#.", ".#..", "####"], "z"),
    "Haste": ("#f8b838", ["..#.", ".##.", "##..", ".#.."], "bolt"),
    "Slow": ("#90a8c0", [".##.", "#.##", "#..#", ".##."], "clock"),
    "Protect": ("#68d0e8", ["####", "#..#", "#..#", ".##."], "shield"),
    "KO": ("#d83838", ["#..#", ".##.", ".##.", "#..#"], "x"),
    "Blind": ("#583080", [".##.", "#.##", "####", ".##."], "eye"),
    "Silence": ("#c0c0c0", ["####", "#..#", "####", "...."], "mouth"),
}
STYLE = {
    "portal": {"bg": "#000000", "border": "#fcfcfc", "border2": "#fcfcfc", "text": "#fcfcfc", "heal": "#58d854", "shade": None, "gauges": False},
    "prism": {"bg": ("#3848b8", "#101858"), "border": "#f0f0f8", "border2": "#9098b0", "text": "#ffffff", "heal": "#78f8a0", "shade": "#202040", "gauges": True},
}


def rgba(hexs, a=1.0):
    return np.array(list(P.hexc(hexs)) + [a], np.float32)


def glyph(rows, col, outline=None):
    h, w = len(rows), len(rows[0])
    pad = 1 if outline else 0
    a = np.zeros((h + 2 * pad, w + 2 * pad, 4), np.float32)
    for y, r in enumerate(rows):
        for x, ch in enumerate(r):
            if ch != ".":
                a[y + pad, x + pad] = rgba(col if ch == "#" else "#ffffff")
    if outline:
        m = a[..., 3] > 0
        d = np.zeros_like(m)
        d[1:] |= m[:-1]
        d[:-1] |= m[1:]
        d[:, 1:] |= m[:, :-1]
        d[:, :-1] |= m[:, 1:]
        a[d & ~m] = rgba(outline)
    return a


def window(st, w=24, h=24):
    a = np.zeros((h, w, 4), np.float32)
    if isinstance(st["bg"], tuple):
        top, bot = np.array(P.hexc(st["bg"][0])), np.array(P.hexc(st["bg"][1]))
        for y in range(h):
            t = y / (h - 1)
            c = top * (1 - t) + bot * t
            a[y, :, :3] = np.round(c * 12) / 12          # banded, the 16-bit look
            a[y, :, 3] = 1
    else:
        a[...] = rgba(st["bg"])
    b, b2 = rgba(st["border"]), rgba(st["border2"])
    for i in range(w):
        a[1, i] = b
        a[h - 2, i] = b2 if st["shade"] else b
    for j in range(h):
        a[j, 1] = b
        a[j, w - 2] = b2 if st["shade"] else b
    if st["shade"]:
        for i in range(w):
            a[2, i, :3] = np.minimum(1, a[2, i, :3] + 0.18)  # bevel highlight under the top edge
    for (x, y) in ((0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1), (1, 1), (w - 2, 1), (1, h - 2), (w - 2, h - 2)):
        a[y, x] = 0                                         # rounded corners
    for (x, y) in ((2, 2), (w - 3, 2), (2, h - 3), (w - 3, h - 3)):
        a[y, x] = b if (x, y) == (2, 2) or not st["shade"] else b2
    a[0, 2:w - 2] = 0
    a[h - 1, 2:w - 2] = 0
    a[2:h - 2, 0] = 0
    a[2:h - 2, w - 1] = 0
    return a


def stretch_window(win, W, H, c=8):
    out = np.zeros((H, W, 4), np.float32)
    h, w = win.shape[:2]
    ys = [(0, c, 0, c), (c, h - c, c, H - c), (h - c, h, H - c, H)]
    xs = [(0, c, 0, c), (c, w - c, c, W - c), (w - c, w, W - c, W)]
    for sy0, sy1, dy0, dy1 in ys:
        for sx0, sx1, dx0, dx1 in xs:
            src = win[sy0:sy1, sx0:sx1]
            ry = np.linspace(0, src.shape[0] - 1, dy1 - dy0).astype(int)
            rx = np.linspace(0, src.shape[1] - 1, dx1 - dx0).astype(int)
            out[dy0:dy1, dx0:dx1] = src[ry][:, rx]
    return out


def status_icon(name, realm):
    col, core, _ = STATUS[name]
    a = np.zeros((8, 8, 4), np.float32)
    ring = rgba("#000000" if realm == "portal" else "#202040")
    for y in range(8):
        for x in range(8):
            d = ((x - 3.5) ** 2 + (y - 3.5) ** 2) ** 0.5
            if d < 3.9:
                a[y, x] = rgba(col)
                if realm == "prism" and x + y < 5:
                    a[y, x, :3] = np.minimum(1, a[y, x, :3] + 0.25)
            elif d < 4.6:
                a[y, x] = ring
    for y, r in enumerate(core):
        for x, ch in enumerate(r):
            if ch == "#":
                a[y + 2, x + 2] = rgba("#000000" if name not in ("KO", "Blind") else "#ffffff")
    return a


def gauge(fill_hex, w=48):
    a = np.zeros((6, w, 4), np.float32)
    a[[0, 5], 1:w - 1] = rgba("#f0f0f8")
    a[1:5, [0, w - 1]] = rgba("#f0f0f8")
    a[1:5, 1:w - 1] = rgba("#181828")
    fill = int((w - 2) * 0.7)
    a[1:5, 1:1 + fill] = rgba(fill_hex)
    a[1, 1:1 + fill, :3] = np.minimum(1, a[1, 1:1 + fill, :3] + 0.3)
    return a


def text_number(n, col, outline=None):
    gl = [glyph(DIGITS[c], col, outline) for c in str(n)]
    return np.concatenate([np.pad(g, ((0, 0), (0, 1), (0, 0))) for g in gl], axis=1)


def blit(dst, src, x, y):
    h, w = src.shape[:2]
    h = min(h, dst.shape[0] - y)
    w = min(w, dst.shape[1] - x)
    if h <= 0 or w <= 0:
        return
    dst[y:y + h, x:x + w] = P.over(dst[y:y + h, x:x + w], src[:h, :w])


def load_png_1x(path):
    """Minimal PNG reader for our own 8-bit RGBA non-interlaced files (pixel_png / Blender writes)."""
    import struct
    import zlib
    with open(path, "rb") as f:
        data = f.read()
    pos, idat = 8, b""
    w = h = 0
    ct = 6
    while pos < len(data):
        ln = struct.unpack(">I", data[pos:pos + 4])[0]
        tag = data[pos + 4:pos + 8]
        body = data[pos + 8:pos + 8 + ln]
        if tag == b"IHDR":
            w, h, bd, ct = struct.unpack(">IIBB", body[:10])
            if bd != 8 or ct not in (2, 6):
                return None
        elif tag == b"IDAT":
            idat += body
        pos += 12 + ln
    ch = 4 if ct == 6 else 3
    raw = zlib.decompress(idat)
    stride = w * ch
    out = np.zeros((h, stride), np.uint8)
    prev = np.zeros(stride, np.int32)
    i = 0
    for y in range(h):
        ft = raw[i]
        line = np.frombuffer(raw[i + 1:i + 1 + stride], np.uint8).astype(np.int32)
        i += 1 + stride
        cur = np.zeros(stride, np.int32)
        if ft == 0:
            cur = line
        elif ft == 2:
            cur = (line + prev) & 255
        else:
            for x in range(stride):
                a = cur[x - ch] if x >= ch else 0
                b = prev[x]
                c = prev[x - ch] if x >= ch else 0
                if ft == 1:
                    cur[x] = (line[x] + a) & 255
                elif ft == 3:
                    cur[x] = (line[x] + (a + b) // 2) & 255
                else:
                    p = a + b - c
                    pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                    cur[x] = (line[x] + (a if pa <= pb and pa <= pc else b if pb <= pc else c)) & 255
        out[y] = cur
        prev = cur
    arr = out.reshape(h, w, ch).astype(np.float32) / 255
    if ch == 3:
        arr = np.concatenate([arr, np.ones((h, w, 1), np.float32)], 2)
    return arr


def mockup(realm, root, st, win, cursor):
    W, H = (256, 224) if realm == "portal" else (320, 224)
    scr = np.zeros((H, W, 4), np.float32)
    scr[..., 3] = 1
    bd = sorted(glob.glob(os.path.join(root, "claude-battle-kit", realm, "Backdrop_*_1x.png")) or
                glob.glob(os.path.join(root, "claude-battle-kit", realm, "*", "Backdrop_*_1x.png")))
    if bd:
        b = load_png_1x(bd[0])
        if b is not None:
            ry = np.linspace(0, b.shape[0] - 1, 144).astype(int)
            rx = np.linspace(0, b.shape[1] - 1, W).astype(int)
            scr[:144] = b[ry][:, rx]
    sp = sorted(glob.glob(os.path.join(root, "claude-battle-sprites", realm, "Battle_*_1x.png")))[:40:9]
    x = 16
    for p in sp[:3]:
        s = load_png_1x(p)
        if s is None:
            continue
        if s.shape[0] > 60:                                                     # enemies ~1/4 of the screen height
            k = -(-s.shape[0] // 56)
            s = s[::k, ::k]
        blit(scr, s, x, 130 - s.shape[0])
        x += s.shape[1] + 4
    party = sorted(glob.glob(os.path.join(root, "claude-battle-kit", realm, "Party_*_1x.png")))[:4]
    for i, p in enumerate(party):
        s = load_png_1x(p)
        if s is None:
            continue
        if s.shape[0] > 34:
            k = -(-s.shape[0] // 32)
            s = s[::k, ::k]
        blit(scr, s, W - 56 + (i % 2) * 10, 8 + i * 32)
    blit(scr, stretch_window(win, W // 2 - 4, 80), 2, H - 82)
    blit(scr, stretch_window(win, W // 2 - 4, 80), W // 2 + 2, H - 82)
    import pixel_font as PF
    tc = st["text"]
    tcol = P.hexc(tc)
    sh = P.hexc(st["shade"]) if st["shade"] else None
    cmds = ("FIGHT", "MAGIC", "ITEM", "RUN") if realm == "portal" else ("ATTACK", "MAGIC", "ITEM", "DEFEND")
    for i, c in enumerate(cmds):
        blit(scr, PF.render(c, tcol, sh), 22, H - 72 + i * 16)
    blit(scr, cursor[:, :8], 10, H - 72)
    names = [os.path.basename(p)[len("Party_"):-len("_1x.png")].split("_")[-1] for p in party] or ["HERO", "SAGE", "SCOUT"]
    for i, (nm, n) in enumerate(zip(names[:3], (412, 96, 1280))):
        y = H - 72 + i * 16
        blit(scr, PF.render(nm[:6 if realm == "portal" else 10], tcol, sh), W // 2 + 8, y)
        num = text_number(n, tc, st["shade"])
        blit(scr, num, W - 10 - num.shape[1], y)                                 # right-aligned inside the frame
        if st["gauges"]:
            blit(scr, gauge("#58d058" if i == 0 else "#f8d038", 40), W - 82, y + 1)
    blit(scr, text_number(999, "#ffffff" if realm == "portal" else "#fff070", st["shade"]), 40, 70)
    return scr


def build(out_root):
    for realm, st in STYLE.items():
        od = os.path.join(out_root, "claude-battle-kit", realm, "ui")
        os.makedirs(od, exist_ok=True)
        save = lambda a, n: (P.save_png(P.upscale(a, K), os.path.join(od, n + ".png")), P.save_png(a, os.path.join(od, n + "_1x.png")))  # noqa: E731
        win = window(st)
        save(win, "Window_9slice")
        cur = glyph([r.replace("w", "w") for r in CURSOR], "#000000")
        cur[..., :3] = np.where((cur[..., 3:] > 0) & (np.array([[[r[x] == "w" for x in range(8)] for r in CURSOR]])[0][..., None]), 1.0, cur[..., :3])
        cur2 = np.zeros_like(cur)
        cur2[:, 1:] = cur[:, :-1]
        cursor = np.concatenate([cur, cur2], axis=1)
        save(cursor, "Cursor")
        ol = st["shade"]
        save(np.concatenate([np.pad(glyph(DIGITS[d], st["text"], ol), ((0, 0), (0, 1), (0, 0))) for d in "0123456789"], axis=1), "Digits")
        save(np.concatenate([np.pad(glyph(DIGITS[d], st["heal"], ol), ((0, 0), (0, 1), (0, 0))) for d in "0123456789"], axis=1), "Digits_Heal")
        save(glyph(MISS, st["text"], ol), "Miss")
        import pixel_font as PF
        at, chars = PF.atlas(P.hexc(st["text"]))
        save(at, "Font_5x7")
        with open(os.path.join(od, "Font_5x7.json"), "w", encoding="utf-8") as f:
            f.write('{"cell": [6, 8], "glyph": [5, 7], "columns": 16, "chars": %s}' % __import__("json").dumps(chars))
        for name in STATUS:
            save(status_icon(name, realm), "Status_" + name)
        if st["gauges"]:
            for n, c in (("HP", "#58d058"), ("MP", "#5890f8"), ("ATB", "#f8d038")):
                save(gauge(c), "Bar_" + n)
        mk = mockup(realm, out_root, st, win, cursor)
        P.save_png(P.upscale(mk, 3), os.path.join(od, "mockup.png"))
    print("UI kit done ->", out_root)


if __name__ == "__main__":
    build(os.path.abspath(sys.argv[1]))
