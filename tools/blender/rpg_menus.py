# SPDX-License-Identifier: MIT
"""Field menu screens for the two RPG realms + the starting party data they show. Pure numpy.

    python tools/blender/rpg_menus.py OUT_ROOT [ROOT_FOR_DATA]

Writes data/rpg/party.json first (original names for every job: base stats, growth per level, starting gear from the
shop stock in interiors.json, starting spells from spells.json, and when each member joins), then renders six
screens per realm from the battle UI kit (9-slice window, 5x7 font, cursor, gauges) and the party sprites:
  Menu      party list (sprite, name, job, LV, HP, MP) + commands (ITEM MAGIC EQUIP STATUS ORDER SAVE) + gold/time
  Status    one member: sprite, LV/EXP/next, HP/MP, seven stats, equipped gear
  Equip     slots (WEAPON SHIELD HELM ARMOR ACCESSORY) and a candidate list with the stat change (+n / -n)
  Items     two-column item list with counts and type icons + a description line
  Shop      buy list with prices from the item shop, gold, and which members can equip a highlighted piece
  Save      three save slots: lead sprites, location, playtime, gold
Also 8 x 8 item-type icons (potion, herb, feather, sword, staff, bow, axe, lance, shield, helm, armor, ring, key,
tent, pouch, scroll) as Icon_<Type>.png. Outputs OUT_ROOT/claude-battle-kit/<realm>/menus/Menu_<Screen>.png (x3),
sheet-menus.png; data/rpg/menus.json lists every screen's windows (x, y, w, h) and fields so the engine can lay
the same screens out natively.
"""
import glob
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pixel_png as P  # noqa: E402
import pixel_font as PF  # noqa: E402
import rpg_battle_ui as UI  # noqa: E402

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
SCREEN = {"portal": (256, 224), "prism": (320, 224)}

# ---- party data -------------------------------------------------------------------------------------------------
#        job: (name, hp, mp, str, agi, vit, int, spr, growth hp/mp, weapon kind, armour kind, joins)
PRISM_PARTY = {
    "Bladeward":   ("Corin",  42, 0,  12, 7, 11, 4, 5,  (14, 0), "sword", "heavy", "start"),
    "Lightmender": ("Ysolde", 30, 18, 5, 7, 6, 8, 12,   (8, 5),  "staff", "robe", "start"),
    "Runecaster":  ("Tamsin", 26, 22, 4, 8, 5, 13, 8,   (7, 6),  "staff", "robe", "start"),
    "Shadowstep":  ("Rook",   34, 4,  9, 13, 7, 5, 6,   (10, 1), "dagger", "light", "start"),
    "Beastcaller": ("Fennick", 36, 10, 9, 10, 9, 7, 8,  (11, 3), "bow", "light", "after Cinder Forge"),
    "Gearwright":  ("Brannoc", 40, 6, 11, 6, 12, 9, 5,  (13, 2), "axe", "heavy", "after Gearwright's Folly"),
    "Starlancer":  ("Aveline", 38, 4, 12, 11, 9, 4, 6,  (12, 1), "lance", "heavy", "after Windcut Aerie"),
    "Chronoseer":  ("Quill",  28, 20, 4, 9, 6, 12, 11,  (7, 6),  "staff", "robe", "after Sunwell Sanctum"),
}
PORTAL_PARTY = {
    "Hero":  ("Arden", 40, 6, 11, 8, 10, 5, 6, (13, 2), "sword", "heavy", "start"),
    "Sage":  ("Mirel", 28, 20, 4, 7, 6, 12, 11, (7, 6), "staff", "robe", "start"),
    "Scout": ("Pike",  34, 4, 9, 12, 8, 5, 6, (10, 1), "bow", "light", "start"),
}
JOB_ELEMENTS = {"Lightmender": ["heal", "shield"], "Runecaster": ["fire", "ice", "bolt"], "Chronoseer": ["haste", "slow", "sleep"],
                "Beastcaller": ["wind"], "Sage": ["fire", "heal", "sleep"]}
WEAPON_OF = {"sword": "Copper Blade", "staff": "Oak Staff", "bow": "Hunter Bow", "axe": "Iron Axe", "lance": "Silver Lance", "dagger": "Copper Blade"}
ARMOR_OF = {"heavy": ["Ring Mail", "Iron Helm", "Kite Shield"], "light": ["Padded Vest"], "robe": ["Padded Vest"]}


def party_data(root):
    spells = json.load(open(os.path.join(root, "data", "rpg", "spells.json"), encoding="utf-8"))["spells"]
    out = {}
    for realm, table in (("portal", PORTAL_PARTY), ("prism", PRISM_PARTY)):
        members = []
        for job, (name, hp, mp, st, ag, vi, it, sp, gr, wk, ak, joins) in table.items():
            fx = JOB_ELEMENTS.get(job, [])
            known = [s["name"] for s in spells if s["realm"] == realm and s["tier"] == 1 and s["effect"] in fx]
            members.append({"name": name, "job": job, "level": 1, "exp": 0, "next": 30, "hp": hp, "mp": mp,
                            "stats": {"str": st, "agi": ag, "vit": vi, "int": it, "spr": sp}, "growth": {"hp": gr[0], "mp": gr[1], "stats": "+1 main stat per level, +1 others every 2"},
                            "equip": {"weapon": WEAPON_OF[wk], "armor": ARMOR_OF[ak][0], "helm": ARMOR_OF[ak][1] if len(ARMOR_OF[ak]) > 1 else None,
                                      "shield": ARMOR_OF[ak][2] if len(ARMOR_OF[ak]) > 2 else None, "accessory": None},
                            "weapon_kinds": [wk], "armor_kind": ak, "spells": known, "joins": joins,
                            "sprite": "engines/unreal/art/claude-battle-kit/%s/Party_%s_%s.png" % (realm, realm.title(), job)})
        out[realm] = {"members": members, "start_gold": 120 if realm == "portal" else 300,
                      "start_items": {"Herb Tonic": 5, "Antidote Leaf": 2, "Smoke Pouch": 1}}
    return out


# ---- icons ------------------------------------------------------------------------------------------------------
ICONS = {   # 8x8, '#' = main colour, '+' = light, '-' = dark
    "potion": ("#d83838", ["..--....", "..++....", ".####...", "#+####..", "#+####..", "######..", ".####...", "........"]),
    "herb":   ("#58b048", ["....#...", "...##...", "..###.#.", ".####.#.", "..######", "...###..", "....-...", "....-..."]),
    "feather": ("#f0f0f8", [".....##.", "....###.", "...###..", "..###...", ".###....", ".##.....", "-#......", "-......."]),
    "sword":  ("#c8d0d8", [".......+", "......#.", ".....#..", "....#...", "-.-#....", ".-#.....", "-.-.....", "........"]),
    "staff":  ("#a87040", [".....++.", "....+##.", ".....#..", "....#...", "...#....", "..#.....", ".#......", "#......."]),
    "bow":    ("#a87040", ["..##....", ".#..+...", "#....+..", "#.....+.", "#.....+.", "#....+..", ".#..+...", "..##...."]),
    "axe":    ("#a8a8b0", [".###....", "#####...", "###-....", ".#.-....", "...-....", "...-....", "...-....", "........"]),
    "lance":  ("#c8d0d8", [".......+", "......#.", ".....-..", "....-...", "...-....", "..-.....", ".-......", "-......."]),
    "shield": ("#4870c0", ["########", "#++++++#", "#+####+#", "#+#++#+#", ".#+##+#.", ".#+##+#.", "..#++#..", "...##..."]),
    "helm":   ("#a8a8b0", ["..####..", ".#++++#.", "#++++++#", "#+#--#+#", "#+#..#+#", "##....##", "........", "........"]),
    "armor":  ("#a8a8b0", ["##....##", "#+#..#+#", "#++##++#", ".#++++#.", ".#+--+#.", ".#++++#.", ".######.", "........"]),
    "ring":   ("#f0c040", ["...++...", "..#--#..", ".#....#.", ".#....#.", ".#....#.", "..#..#..", "...##...", "........"]),
    "key":    ("#f0c040", [".###....", "#+..#...", "#...#...", ".###....", "...#....", "...##...", "...#....", "...##..."]),
    "tent":   ("#c88848", ["...#....", "..###...", ".##+##..", ".#+-+#..", "##+-+##.", "#+---+##", "########", "........"]),
    "pouch":  ("#806048", ["..-..-..", "...--...", "..####..", ".#++###.", "#+#####.", "#######.", ".#####..", "........"]),
    "scroll": ("#e8d8b0", ["-######-", ".#++++#.", ".#----#.", ".#++++#.", ".#----#.", ".#++++#.", "-######-", "........"]),
}
TYPE_OF = {"Herb Tonic": "herb", "Clear Draught": "potion", "Antidote Leaf": "herb", "Wake Bell": "ring", "Feather of Waking": "feather",
           "Smoke Pouch": "pouch", "Camp Tent": "tent", "Copper Blade": "sword", "Oak Staff": "staff", "Hunter Bow": "bow", "Iron Axe": "axe",
           "Steel Saber": "sword", "Silver Lance": "lance", "Padded Vest": "armor", "Ring Mail": "armor", "Iron Helm": "helm",
           "Kite Shield": "shield", "Scale Coat": "armor", "Tower Shield": "shield"}


def icon(kind):
    c, rows = ICONS[kind]
    base = np.array(P.hexc(c))
    a = np.zeros((8, 8, 4), np.float32)
    for y, r in enumerate(rows):
        for x, ch in enumerate(r):
            if ch != ".":
                a[y, x, :3] = np.clip(base * (1.35 if ch == "+" else 0.55 if ch == "-" else 1.0), 0, 1)
                a[y, x, 3] = 1
    return a


# ---- drawing helpers --------------------------------------------------------------------------------------------
class Screen:
    def __init__(self, realm):
        self.realm = realm
        self.st = UI.STYLE[realm]
        self.win = UI.window(self.st)
        W, H = SCREEN[realm]
        self.img = np.zeros((H, W, 4), np.float32)
        self.img[..., 3] = 1
        self.windows = []
        self.fields = []
        self.tc = P.hexc(self.st["text"])
        self.sh = P.hexc(self.st["shade"]) if self.st["shade"] else None

    def window(self, name, x, y, w, h):
        UI.blit(self.img, UI.stretch_window(self.win, w, h), x, y)
        self.windows.append({"name": name, "x": x, "y": y, "w": w, "h": h})

    def text(self, s, x, y, col=None, field=None):
        UI.blit(self.img, PF.render(str(s), col or self.tc, self.sh), x, y)
        if field:
            self.fields.append({"field": field, "x": x, "y": y, "text": str(s)})

    def num(self, n, x_right, y, col=None):
        a = PF.render(str(n), col or self.tc, self.sh)
        UI.blit(self.img, a, x_right - a.shape[1], y)

    def sprite(self, s, x, y, max_h=24):
        if s is None:
            return
        if s.shape[0] > max_h:
            k = -(-s.shape[0] // max_h)
            s = s[::k, ::k]
        UI.blit(self.img, s, x, y)

    def gauge(self, frac, x, y, w, hexc):
        if not self.st["gauges"]:
            return
        g = UI.gauge(hexc, w)
        fill = int((w - 2) * max(0.0, min(1.0, frac)))
        g[1:5, 1 + fill:w - 1] = UI.rgba("#181828")
        UI.blit(self.img, g, x, y)

    def cursor(self, x, y):
        cur = UI.glyph(UI.CURSOR, "#000000")
        cur[..., :3] = np.where((cur[..., 3:] > 0) & (np.array([[r[i] == "w" for i in range(8)] for r in UI.CURSOR])[..., None]), 1.0, cur[..., :3])
        UI.blit(self.img, cur, x, y)

    def icon(self, kind, x, y):
        UI.blit(self.img, icon(kind), x, y)


def party_sprites(art_root, realm):
    out = {}
    for p in glob.glob(os.path.join(art_root, "claude-battle-kit", realm, "Party_*_1x.png")):
        job = os.path.basename(p)[:-len("_1x.png")].split("_")[-1]
        out[job] = UI.load_png_1x(p)
    return out


def hi(realm):
    return P.hexc("#f8d878" if realm == "portal" else "#fff070")


def scr_menu(realm, party, sprites, gold):
    s = Screen(realm)
    W, H = SCREEN[realm]
    cw = 72
    s.window("party", 0, 0, W - cw, H)
    s.window("commands", W - cw, 0, cw, H - 64)
    s.window("gold", W - cw, H - 64, cw, 64)
    mem = [m for m in party["members"] if m["joins"] == "start"][:4]
    for i, m in enumerate(mem):
        y = 10 + i * 52
        s.sprite(sprites.get(m["job"]), 10, y, 32)
        x = 50
        s.text(m["name"].upper(), x, y, field="member%d.name" % i)
        s.text(m["job"].upper()[:12], x, y + 10, col=P.hexc("#a0a8c0") if realm == "prism" else None)
        s.text("LV", x + 70 if realm == "prism" else x + 56, y, field=None)
        s.num(m["level"] + 4 * i + 7, W - cw - 12, y)
        hp, mp = m["hp"] + 60 + i * 9, m["mp"] + 12
        s.text("HP", x, y + 22)
        s.num("%d/%d" % (hp - 7 * i, hp), W - cw - 12, y + 22)
        s.gauge((hp - 7 * i) / hp, x + 16, y + 32, 64, "#58d058")
        s.text("MP", x, y + 34 if not s.st["gauges"] else y + 38) if m["mp"] else None
        if m["mp"]:
            s.num("%d/%d" % (mp, mp), W - cw - 12, y + 34 if not s.st["gauges"] else y + 38)
    for i, c in enumerate(("ITEM", "MAGIC", "EQUIP", "STATUS", "ORDER", "SAVE")):
        s.text(c, W - cw + 18, 10 + i * 16, field="command%d" % i)
    s.cursor(W - cw + 6, 10)
    s.text("G", W - cw + 10, H - 54)
    s.num(gold, W - 12, H - 54)
    s.text("TIME", W - cw + 10, H - 38)
    s.num("12:47", W - 12, H - 24)
    return s


def scr_status(realm, party, sprites):
    s = Screen(realm)
    W, H = SCREEN[realm]
    m = party["members"][0]
    s.window("header", 0, 0, W, 56)
    s.window("stats", 0, 56, W // 2, H - 56)
    s.window("equip", W // 2, 56, W - W // 2, H - 56)
    s.sprite(sprites.get(m["job"]), 10, 8, 40)
    s.text(m["name"].upper(), 56, 10, field="name")
    s.text(m["job"].upper(), 56, 22, col=hi(realm))
    s.text("LV 12", 56, 36, field="level")
    s.text("EXP", W // 2, 10)
    s.num(4280, W - 12, 10)
    s.text("NEXT", W // 2, 22)
    s.num(612, W - 12, 22)
    s.text("HP", W // 2, 36)
    s.num("%d/%d" % (m["hp"] + 150, m["hp"] + 150), W - 12, 36)
    st = dict(m["stats"])
    rows = [("STR", st["str"] + 11), ("AGI", st["agi"] + 8), ("VIT", st["vit"] + 10), ("INT", st["int"] + 5), ("SPR", st["spr"] + 6), ("ATK", 64), ("DEF", 38)]
    for i, (k, v) in enumerate(rows):
        s.text(k, 12, 68 + i * 20, field="stat." + k.lower())
        s.num(v, W // 2 - 12, 68 + i * 20)
    for i, (slot, item) in enumerate(m["equip"].items()):
        y = 68 + i * 28
        s.text(slot.upper(), W // 2 + 10, y, col=P.hexc("#a0a8c0") if realm == "prism" else hi(realm))
        if item:
            s.icon(TYPE_OF.get(item, "ring"), W // 2 + 10, y + 11)
            s.text(item.upper()[:20 if realm == "prism" else 16], W // 2 + 22, y + 11)
        else:
            s.text("-", W // 2 + 22, y + 11)
    return s


def scr_equip(realm, party, sprites, stock):
    s = Screen(realm)
    W, H = SCREEN[realm]
    m = party["members"][0]
    s.window("who", 0, 0, W, 36)
    s.window("slots", 0, 36, W // 2 + 8, 92)
    s.window("compare", W // 2 + 8, 36, W - W // 2 - 8, 92)
    s.window("candidates", 0, 128, W, H - 128)
    s.sprite(sprites.get(m["job"]), 8, 4, 28)
    s.text(m["name"].upper(), 40, 14)
    s.text("EQUIP", W - 60, 14, col=hi(realm))
    for i, (slot, item) in enumerate(m["equip"].items()):
        y = 46 + i * 15
        s.text(slot.upper()[:6] if realm == "prism" else {"weapon": "WPN", "armor": "ARM", "helm": "HLM", "shield": "SHD", "accessory": "ACC"}[slot], 22, y)
        s.text((item or "-").upper()[:14 if realm == "prism" else 13], 70 if realm == "prism" else 46, y)
    s.cursor(8, 46)
    s.text("ATK", W // 2 + 18, 48)
    s.num(64, W // 2 + 82 if realm == "prism" else W // 2 + 70, 48)
    s.text(">", W // 2 + (88 if realm == "prism" else 74), 48, col=hi(realm))
    s.num(78, W - 34 if realm == "prism" else W - 20, 48, col=P.hexc("#78f878"))
    s.text("DEF", W // 2 + 18, 64)
    s.num(38, W // 2 + 82 if realm == "prism" else W // 2 + 70, 64)
    s.text(">", W // 2 + (88 if realm == "prism" else 74), 64, col=hi(realm))
    s.num(38, W - 34 if realm == "prism" else W - 20, 64)
    weapons = [w for w in stock.get("Weapon", [])]
    for i, w in enumerate(weapons[:6]):
        x, y = (14 if i % 2 == 0 else W // 2 + 8), 140 + (i // 2) * 24
        s.icon(TYPE_OF.get(w["name"], "sword"), x, y)
        s.text(w["name"].upper()[:16 if realm == "prism" else 12], x + 12, y)
        d = w.get("attack", 0) - 6
        s.text(("+%d" % d) if d >= 0 else str(d), x + 12, y + 10, col=P.hexc("#78f878") if d > 0 else P.hexc("#f87878") if d < 0 else None)
    return s


def scr_items(realm, party, stock):
    s = Screen(realm)
    W, H = SCREEN[realm]
    s.window("title", 0, 0, 80, 28)
    s.window("help", 80, 0, W - 80, 28)
    s.window("list", 0, 28, W, H - 28)
    s.text("ITEM", 14, 10, col=hi(realm))
    items = [(it["name"], n) for it, n in zip(stock.get("Item", []), (5, 3, 2, 4, 1, 1, 1))]
    items += [(w["name"], 1) for w in stock.get("Weapon", [])[:2]] + [(a["name"], 1) for a in stock.get("Armor", [])[:3]]
    desc = {it["name"]: it.get("effect", "") for it in stock.get("Item", [])}
    s.text(desc.get(items[0][0], "").upper()[:34 if realm == "prism" else 26], 88, 10)
    for i, (n, c) in enumerate(items):
        x, y = (10 if i % 2 == 0 else W // 2 + 4), 40 + (i // 2) * 18
        s.icon(TYPE_OF.get(n, "ring"), x + 10, y)
        s.text(n.upper()[:17 if realm == "prism" else 11], x + 22, y)
        s.num(":%d" % c, x + W // 2 - 14, y)
    s.cursor(4, 40)
    return s


def scr_shop(realm, party, sprites, stock, gold):
    s = Screen(realm)
    W, H = SCREEN[realm]
    s.window("title", 0, 0, W, 28)
    s.window("list", 0, 28, W - 88, H - 28)
    s.window("gold", W - 88, 28, 88, 32)
    s.window("who_can", W - 88, 60, 88, H - 60)
    s.text("WEAPON SHOP" if realm == "portal" else "WEAPONS - BUY", 12, 10, col=hi(realm))
    wl = stock.get("Weapon", [])
    for i, w in enumerate(wl):
        y = 40 + i * 18
        s.icon(TYPE_OF.get(w["name"], "sword"), 16, y)
        s.text(w["name"].upper()[:16 if realm == "prism" else 14], 28, y)
        s.num(w["price"], W - 100, y, col=None if w["price"] <= gold else P.hexc("#808080"))
    s.cursor(4, 40 + 18)
    s.text("G", W - 80, 40)
    s.num(gold, W - 10, 40)
    pick = wl[1]["name"] if len(wl) > 1 else ""
    kind = next((k for k, v in WEAPON_OF.items() if v == pick), "staff")
    for i, m in enumerate([m for m in party["members"] if m["joins"] == "start"][:4]):
        y = 70 + i * 34
        spr = sprites.get(m["job"])
        s.sprite(spr, W - 80, y, 26)
        ok = kind in m["weapon_kinds"]
        s.text("OK" if ok else "--", W - 40, y + 8, col=P.hexc("#78f878") if ok else P.hexc("#808080"))
    return s


def scr_save(realm, party, sprites, gold):
    s = Screen(realm)
    W, H = SCREEN[realm]
    s.window("title", 0, 0, W, 28)
    s.text("SAVE" if realm == "portal" else "SAVE - CHOOSE A SLOT", 12, 10, col=hi(realm))
    places = (("DEMO TOWN", "4:12", gold), ("OLD MINE B2" if realm == "portal" else "CINDER FORGE B3", "12:47", gold * 3), ("EMPTY", "", 0))
    for i, (loc, t, g) in enumerate(places):
        y = 30 + i * 64
        s.window("slot%d" % i, 0, y, W, 62)
        s.text(str(i + 1), 10, y + 10, col=hi(realm))
        if loc == "EMPTY":
            s.text("- EMPTY -", W // 2 - 27, y + 26, col=P.hexc("#808080"))
            continue
        for k, m in enumerate([m for m in party["members"] if m["joins"] == "start"][:4]):
            s.sprite(sprites.get(m["job"]), 24 + k * 26, y + 14, 30)
        x = 24 + 4 * 26 + 6 if realm == "prism" else 24 + 3 * 26 + 6
        s.text(loc, x, y + 10)
        s.text("LV 12", x, y + 24)
        s.text("TIME %s" % t, x, y + 38)
        s.num("%dG" % g, W - 12, y + 38)
    s.cursor(2, 40)
    return s


def build(out_root, data_root=None):
    root = data_root or REPO
    party = party_data(root)
    if data_root:
        with open(os.path.join(data_root, "data", "rpg", "party.json"), "w", encoding="utf-8") as f:
            json.dump({"schema": "daedalus.party/v1", "source": "tools/blender/rpg_menus.py", "party": party}, f, indent=1)
    inter = json.load(open(os.path.join(root, "data", "rpg", "interiors.json"), encoding="utf-8"))["interiors"]
    layouts = {}
    for realm in ("portal", "prism"):
        od = os.path.join(out_root, "claude-battle-kit", realm, "menus")
        os.makedirs(od, exist_ok=True)
        for k in ICONS:
            P.save_png(P.upscale(icon(k), 4), os.path.join(od, "Icon_%s.png" % k.title()))
            P.save_png(icon(k), os.path.join(od, "Icon_%s_1x.png" % k.title()))
        sprites = party_sprites(out_root, realm)
        stock = {k: inter["portal"][k]["stock"] for k in ("Item", "Weapon", "Armor")}       # same goods in both realms
        gold = party[realm]["start_gold"] * 4
        screens = {"Menu": scr_menu(realm, party[realm], sprites, gold), "Status": scr_status(realm, party[realm], sprites),
                   "Equip": scr_equip(realm, party[realm], sprites, stock), "Items": scr_items(realm, party[realm], stock),
                   "Shop": scr_shop(realm, party[realm], sprites, stock, gold), "Save": scr_save(realm, party[realm], sprites, gold)}
        thumbs = []
        layouts[realm] = {"screen": SCREEN[realm], "font": "ui/Font_5x7.png", "window": "ui/Window_9slice.png", "screens": {}}
        for name, sc in screens.items():
            P.save_png(P.upscale(sc.img, 3), os.path.join(od, "Menu_%s.png" % name))
            P.save_png(sc.img, os.path.join(od, "Menu_%s_1x.png" % name))
            thumbs.append(sc.img)
            layouts[realm]["screens"][name] = {"windows": sc.windows, "fields": sc.fields}
        P.save_png(P.upscale(P.grid_sheet(thumbs, 3), 2), os.path.join(od, "sheet-menus.png"))
    if data_root:
        with open(os.path.join(data_root, "data", "rpg", "menus.json"), "w", encoding="utf-8") as f:
            json.dump({"schema": "daedalus.menus/v1", "source": "tools/blender/rpg_menus.py", "layouts": layouts}, f, indent=1)
    return layouts


if __name__ == "__main__":
    out = os.path.abspath(sys.argv[1])
    dr = os.path.abspath(sys.argv[2]) if len(sys.argv) > 2 else None
    r = build(out, dr)
    print("MENUS", {k: list(v["screens"]) for k, v in r.items()})
