# SPDX-License-Identifier: MIT
"""Title and name-entry screens for the two RPG realms. Pure numpy, original art.

    python tools/blender/rpg_title.py OUT_ROOT [ROOT_FOR_DATA]

Title (8 frames, 6 fps): a layered night scene (sky gradient, twinkling stars, far mountains, a castle silhouette,
near hills; Prismheart adds a crystal glow on the horizon), the realm emblem (Portal: a ring gate; Prismheart: a
faceted crystal heart), the logo in the 5x7 font scaled x3 with an outline (16-bit: banded gradient fill and a shine
sweep across the frames), a NEW GAME / CONTINUE / OPTIONS menu with the cursor, and a blinking PRESS START.
Name entry: the lead hero's sprite, the name field with a blinking caret, a letter grid (A-Z, 0-9, space, - .),
and BACK / END. title.json's menu_geometry says where the baked menu sits so a live menu draws on the same pixels.
Outputs OUT_ROOT/claude-battle-kit/<realm>/title/Title.png (8-frame strip, x3) + Title_1x.png, Title_F0.png,
TitleBg_1x.png (the same frames without menu, prompt or credit, for a live title menu), NameEntry.png; data/rpg/title.json: logo, menu items, frame count / fps, the music cue (TITLE) and the name grid.
"""
import json
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pixel_png as P  # noqa: E402
import pixel_font as PF  # noqa: E402
import rpg_battle_ui as UI  # noqa: E402
import rpg_menus as RM  # noqa: E402

SCREEN = RM.SCREEN
FRAMES = 8
LOGO = {"portal": ("PORTAL", "REALM"), "prism": ("PRISMHEART", "")}
SKY = {"portal": ("#000020", "#202878", "#5850b8"), "prism": ("#0c0828", "#382878", "#c06898")}
NAME_GRID = ["ABCDEFGHIJ", "KLMNOPQRST", "UVWXYZ0123", "456789 -. "]


def hexa(h):
    return np.array(P.hexc(h))


def scene(realm, f):
    W, H = SCREEN[realm]
    img = np.zeros((H, W, 4), np.float32)
    img[..., 3] = 1
    top, mid, low = [hexa(c) for c in SKY[realm]]
    for y in range(H):
        t = y / (H - 1)
        c = top * (1 - t * 1.6) + mid * (t * 1.6) if t < 0.62 else mid * (1 - (t - 0.62) / 0.38) + low * ((t - 0.62) / 0.38)
        img[y, :, :3] = np.round(np.clip(c, 0, 1) * (6 if realm == "portal" else 14)) / (6 if realm == "portal" else 14)
    rng = np.random.default_rng(42)
    for i in range(70 if realm == "prism" else 45):                                 # stars
        x, y = rng.integers(0, W), rng.integers(0, int(H * 0.55))
        tw = (i + f) % 5 == 0
        c = np.array([1, 1, 1]) if tw else np.array([0.7, 0.75, 0.9])
        img[y, x, :3] = c
        if tw and realm == "prism" and 0 < x < W - 1 and 0 < y < H - 1:
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                img[y + dy, x + dx, :3] = np.maximum(img[y + dy, x + dx, :3], c * 0.6)
    if realm == "prism":                                                            # crystal glow on the horizon
        for y in range(int(H * 0.45), int(H * 0.75)):
            for x in range(W):
                d = math.hypot((x - W * 0.72) / 60, (y - H * 0.66) / 22)
                if d < 1:
                    img[y, x, :3] = np.clip(img[y, x, :3] + np.array([0.35, 0.2, 0.45]) * (1 - d) ** 2, 0, 1)

    def ridge(base, amp, freq, phase, col):
        for x in range(W):
            h = base + amp * (math.sin(x * freq + phase) * 0.6 + math.sin(x * freq * 2.7 + phase * 1.3) * 0.4)
            img[int(max(0, h)):, x, :3] = col
    ridge(H * 0.62, 14, 0.035, 1.0, hexa("#282050") if realm == "prism" else hexa("#181848"))
    # castle silhouette
    cx, cy = int(W * 0.74), int(H * 0.68)
    sil = hexa("#100c24") if realm == "prism" else hexa("#080820")
    img[cy - 20:int(H * 0.8), cx - 14:cx + 14, :3] = sil                         # walls reach down into the hills
    for tx in (cx - 16, cx - 2, cx + 12):
        img[cy - 30:cy, tx:tx + 5, :3] = sil
        img[cy - 34:cy - 30, tx + 1:tx + 4, :3] = sil
    for wx in (cx - 8, cx + 4):                                                     # lit windows
        img[cy - 14:cy - 11, wx:wx + 2, :3] = hexa("#f8d878")
    ridge(H * 0.74, 9, 0.05, 2.2, hexa("#18143a") if realm == "prism" else hexa("#000018"))
    ridge(H * 0.86, 6, 0.08, 0.4, hexa("#0c0a20") if realm == "prism" else hexa("#000000"))
    return img


def emblem(realm, f):
    s = 40
    a = np.zeros((s, s, 4), np.float32)
    c = s / 2 - 0.5
    for y in range(s):
        for x in range(s):
            dx, dy = x - c, y - c
            if realm == "portal":                                                   # a ring gate with a swirl inside
                r = math.hypot(dx, dy)
                if 14 <= r < 19:
                    a[y, x] = list(P.hexc("#a8a8a8" if (int(math.atan2(dy, dx) * 6 / math.pi) % 2) else "#fcfcfc")) + [1]
                elif r < 14:
                    sw = (math.atan2(dy, dx) + r * 0.35 - f * 0.8) % (2 * math.pi)
                    a[y, x] = list(P.hexc("#3cbcfc" if sw < math.pi else "#0058f8")) + [1]
                elif r < 20:
                    a[y, x] = [0, 0, 0, 1]
            else:                                                                   # faceted crystal heart
                xn, yn = dx / 16, -(dy + 2) / 16
                heart = (xn * xn + yn * yn - 1) ** 3 - xn * xn * yn ** 3 <= 0
                if heart:
                    ang = (math.atan2(dy - 2, dx) + math.pi) / (2 * math.pi)          # 8 cut faces around the centre, lit from top-left
                    sector = int(ang * 8) % 8
                    inner = math.hypot(dx, dy - 2) < 7
                    col = ("#f0d8ff", "#e0c0ff", "#c890f8", "#a070e0", "#7058c8", "#8868d8", "#b088f0", "#d8b0ff")[sector]
                    if inner:
                        col = "#ffffff" if sector in (0, 1, 7) else "#e8d0ff"
                    if abs(dx - (f - 4) * 4) < 2:                                    # shine sweep
                        col = "#ffffff"
                    a[y, x] = list(P.hexc(col)) + [1]
    m = a[..., 3] > 0
    d = np.zeros_like(m)
    d[1:] |= m[:-1]
    d[:-1] |= m[1:]
    d[:, 1:] |= m[:, :-1]
    d[:, :-1] |= m[:, 1:]
    a[d & ~m] = [0.05, 0.03, 0.1, 1]
    return a


def logo(realm, text, f, scale=3):
    g = PF.render(text, (1, 1, 1))
    g = P.upscale(g, scale)
    h, w = g.shape[:2]
    out = np.zeros((h + 2, w + 2, 4), np.float32)
    m = g[..., 3] > 0
    for y in range(h):
        t = y / max(1, h - 1)
        if realm == "portal":
            col = hexa("#f8b800") if t < 0.5 else hexa("#d82800")
        else:
            col = np.round((hexa("#fff4c0") * (1 - t) + hexa("#e07828") * t) * 10) / 10
        for x in range(w):
            if m[y, x]:
                c = col
                if realm == "prism" and abs((x - y) - (f * w / FRAMES - 10)) < 3:
                    c = np.array([1.0, 1.0, 1.0])
                out[y + 1, x + 1, :3] = c
                out[y + 1, x + 1, 3] = 1
    mm = out[..., 3] > 0
    d = np.zeros_like(mm)
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1)):
        d |= np.roll(np.roll(mm, dy, 0), dx, 1)
    out[d & ~mm] = [0.04, 0.02, 0.08, 1]
    return out


def title_backdrop(realm, f):
    """The title without its menu, prompt or credit: the layer a live title screen draws its own menu over."""
    W, H = SCREEN[realm]
    img = scene(realm, f)
    e = emblem(realm, f)
    UI.blit(img, e, W // 2 - e.shape[1] // 2, 10)
    l1, l2 = LOGO[realm]
    a = logo(realm, l1, f, 3 if realm == "portal" else 3)
    UI.blit(img, a, W // 2 - a.shape[1] // 2, 56)
    y = 56 + a.shape[0] + 2
    if l2:
        b = logo(realm, l2, f, 2)
        UI.blit(img, b, W // 2 - b.shape[1] // 2, y)
        y += b.shape[0]
    tag = "A TALE OF THE SKY ISLES" if realm == "portal" else "THE SHATTERED CRYSTAL"
    t = PF.render(tag, P.hexc("#c8c8f0"), (0.05, 0.03, 0.1))
    UI.blit(img, t, W // 2 - t.shape[1] // 2, y + 4)
    return img


def menu_geometry(realm):
    """Where the baked menu sits, so a live menu lands on exactly the same pixels."""
    W, H = SCREEN[realm]
    return {"window": [W // 2 - 52, H - 82, 104, 56], "item_x": W // 2 - 30, "item_y": H - 72, "item_step": 14,
            "cursor_x": W // 2 - 44, "cursor_y": H - 73, "press_y": H - 20, "credit": "2026 RICHEYWORKS", "credit_xy": [W - 6, H - 9]}


def title_frame(realm, f):
    W, H = SCREEN[realm]
    img = title_backdrop(realm, f)
    st = UI.STYLE[realm]
    win = UI.stretch_window(UI.window(st), 104, 56)
    UI.blit(img, win, W // 2 - 52, H - 82)
    for i, item in enumerate(("NEW GAME", "CONTINUE", "OPTIONS")):
        UI.blit(img, PF.render(item, P.hexc(st["text"]), P.hexc(st["shade"]) if st["shade"] else None), W // 2 - 30, H - 72 + i * 14)
    cur = UI.glyph(UI.CURSOR, "#000000")
    cur[..., :3] = np.where((cur[..., 3:] > 0) & (np.array([[r[i] == "w" for i in range(8)] for r in UI.CURSOR])[..., None]), 1.0, cur[..., :3])
    UI.blit(img, cur, W // 2 - 44 + (f % 2), H - 73)
    if f % 4 < 2:
        ps = PF.render("PRESS START", P.hexc("#ffffff"), (0.05, 0.03, 0.1))
        UI.blit(img, ps, W // 2 - ps.shape[1] // 2, H - 20)
    c = PF.render("2026 RICHEYWORKS", P.hexc("#8080a8"))
    UI.blit(img, c, W - c.shape[1] - 6, H - 9)
    return img


def name_entry(realm, sprites, party):
    s = RM.Screen(realm)
    W, H = SCREEN[realm]
    lead = party["members"][0]
    s.window("who", 0, 0, W, 48)
    s.sprite(sprites.get(lead["job"]), 10, 6, 36)
    s.text("NAME YOUR " + lead["job"].upper() + ":" if realm == "prism" else "NAME YOUR HERO:", 50, 10, col=RM.hi(realm))
    nm = lead["name"].upper()
    s.text(nm + "_", 50, 26, field="name")
    s.window("grid", 0, 48, W, H - 48)
    cw = (W - 40) // 10
    for r, row in enumerate(NAME_GRID):
        for c, ch in enumerate(row):
            if ch != " " or (r == 3 and c == 6):
                s.text(ch if ch != " " else "SP", 26 + c * cw, 64 + r * 22)
    s.text("BACK", 26, H - 30)
    s.text("END", W - 60, H - 30, col=RM.hi(realm))
    s.cursor(14, 64)
    return s


def build(out_root, data_root=None):
    root = data_root or RM.REPO
    party = RM.party_data(root)
    meta = {}
    for realm in ("portal", "prism"):
        od = os.path.join(out_root, "claude-battle-kit", realm, "title")
        os.makedirs(od, exist_ok=True)
        frames = [title_frame(realm, f) for f in range(FRAMES)]
        strip = np.concatenate(frames, axis=1)
        P.save_png(P.upscale(strip, 3), os.path.join(od, "Title.png"))
        P.save_png(strip, os.path.join(od, "Title_1x.png"))
        P.save_png(P.upscale(frames[0], 3), os.path.join(od, "Title_F0.png"))
        bg = np.concatenate([title_backdrop(realm, f) for f in range(FRAMES)], axis=1)
        P.save_png(bg, os.path.join(od, "TitleBg_1x.png"))
        ne = name_entry(realm, RM.party_sprites(out_root, realm), party[realm])
        P.save_png(P.upscale(ne.img, 3), os.path.join(od, "NameEntry.png"))
        meta[realm] = {"logo": " ".join(x for x in LOGO[realm] if x), "frames": FRAMES, "fps": 6, "screen": SCREEN[realm],
                       "menu": ["NEW GAME", "CONTINUE", "OPTIONS"], "music_cue": "TITLE", "menu_geometry": menu_geometry(realm),
                       "backdrop": "engines/unreal/art/claude-battle-kit/%s/title/TitleBg_1x.png" % realm,
                       "strip": "engines/unreal/art/claude-battle-kit/%s/title/Title.png" % realm,
                       "name_entry": {"grid": NAME_GRID, "max_len": 6 if realm == "portal" else 9, "windows": ne.windows}}
    if data_root:
        with open(os.path.join(data_root, "data", "rpg", "title.json"), "w", encoding="utf-8") as f:
            json.dump({"schema": "daedalus.title/v1", "source": "tools/blender/rpg_title.py", "realms": meta}, f, indent=1)
    return meta


if __name__ == "__main__":
    out = os.path.abspath(sys.argv[1])
    dr = os.path.abspath(sys.argv[2]) if len(sys.argv) > 2 else None
    print("TITLE", list(build(out, dr)))
