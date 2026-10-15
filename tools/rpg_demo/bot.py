# SPDX-License-Identifier: MIT
"""A plain RPG player for the Prismheart demo's tests (Playwright page + the PRISM_DEMO hooks).

It plays like a careful person, not a cheat: the Lightmender heals anyone under half health, the Runecaster casts
the best spell she knows (the boss's weakness first), the rest attack, a Herb Tonic goes to anyone in trouble.
buy_spell() walks into the magic shop and buys like a player would.
"""
CM = ["ATTACK", "MAGIC", "ITEM", "DEFEND", "RUN"]


class Bot:
    def __init__(self, pg, data):
        self.pg, self.D = pg, data
        self.spells = {s["name"]: s for s in data["spells"]}

    def ev(self, js):
        return self.pg.evaluate(js)

    def st(self):
        return self.ev("PRISM_DEMO.state()")

    def press(self, k, wait=90):
        self.ev("PRISM_DEMO.press('%s')" % k)
        self.pg.wait_for_timeout(wait)

    def face(self, d):
        self.ev("PRISM_DEMO.hold('%s',true)" % d); self.pg.wait_for_timeout(50)
        self.ev("PRISM_DEMO.hold('%s',false)" % d); self.pg.wait_for_timeout(250)

    def clear(self):
        for _ in range(16):
            s = self.st()
            if s["mode"] == "field" and not s["dialog"]:
                return
            self.press("a" if s["dialog"] else "b", 250)

    def best_spell(self, me, weak):
        known = [self.spells[n] for n in me[6] if n in self.spells and self.spells[n]["target"] != "ally" and self.spells[n]["power"] > 0]
        ok = [s for s in known if s["mp"] <= me[4]]
        if not ok:
            return None
        elem = {"tide": "water", "gale": "air", "stone": "earth", "shade": "dark"}.get(weak or "", weak)
        return max(ok, key=lambda s: s["power"] * (2 if elem and s["element"] == elem else 1))["name"]

    def fight(self, limit=4000):
        plan, last = None, None
        for _ in range(limit):
            s = self.st()
            if s["mode"] != "battle":
                return last
            b = s["battle"]
            last = b
            if b["phase"] != "cmd":
                self.press("a", 60); plan = None; continue
            pt = s["party"]; me = pt[b["who"]]
            if b["sub"] is None:
                low = min((m for m in pt if m[2] > 0), key=lambda m: m[2] / m[3])
                heal = next((n for n in ("Restore", "Mend") if n in me[6] and me[4] >= self.spells[n]["mp"]), None)
                weak = next((f[2] for f in b["foes"] if f[1] > 0), None)
                spell = self.best_spell(me, weak) if me[0] != "Ysolde" or not heal else None
                if heal and low[2] / low[3] < 0.5:
                    plan = ("MAGIC", heal, low[0])
                elif spell and me[0] == "Tamsin":
                    plan = ("MAGIC", spell, None)
                elif low[2] / low[3] < 0.3 and s["bag"].get("Herb Tonic"):
                    plan = ("ITEM", "Herb Tonic", low[0])
                else:
                    plan = ("ATTACK", None, None)
                if b["cmd"] != CM.index(plan[0]):
                    self.press("down", 40); continue
                self.press("a", 50); continue
            if b["sub"] == "magic":
                want = me[6].index(plan[1]) if plan and plan[1] in me[6] else 0
                if b["oi"] != want:
                    self.press("down", 40); continue
                self.press("a", 50); continue
            if b["sub"] == "item":
                self.press("a", 50); continue
            if b["sub"] == "target":
                if plan and plan[2] and plan[2] in b["list"] and b["list"][b["target"]] != plan[2]:
                    self.press("down", 40); continue
                self.press("a", 50); continue
        return last

    def buy_spell(self, name):
        """Walk into the magic shop, talk to the mage, buy the spell. Returns True if Tamsin knows it after."""
        stock = [x["name"] for x in self.D["interiors"]["Magic"]["stock"]]
        self.ev("PRISM_DEMO.warp('Magic',5,5)"); self.pg.wait_for_timeout(300)
        self.face("up")
        for _ in range(12):
            if self.st()["mode"] == "shop":
                break
            self.press("a", 250)
        for _ in range(stock.index(name)):
            self.press("down", 70)
        self.press("a", 250)
        for _ in range(8):
            s = self.st()
            if s["mode"] == "field" and not s["dialog"]:
                break
            self.press("b", 200)
        sp = self.spells.get(name, {})
        return any(name in m[6] for m in self.st()["party"]) if sp else False

    def rest(self):
        """Pay for a night at the inn, like a player between dungeons (it also saves the journey)."""
        self.ev("PRISM_DEMO.warp('Inn',3,6)"); self.pg.wait_for_timeout(300)
        self.face("up")
        self.press("a", 500)
        for _ in range(10):
            s = self.st()
            if s["dialog"] and "REST" in s["dialog"]:
                break
            self.press("a", 300)
        self.press("a", 1200)
        self.clear()

    def to_boss(self, di):
        """Stand under dungeon di's boss gate, answer YES, and wait for the battle."""
        fl = self.D["dungeons"][di]["floors"][-1]
        gate = fl["boss"]["gate"]
        self.ev("PRISM_DEMO.warp('dungeon',%d,%d,%d,%d)" % (gate["x"], gate["y"] + 1, len(self.D["dungeons"][di]["floors"]) - 1, di))
        self.pg.wait_for_timeout(350)
        self.face("up")
        self.press("a", 900)
        for _ in range(8):
            if self.st()["mode"] == "battle":
                break
            self.press("a", 600)
        self.pg.wait_for_timeout(400)
        return self.st()["mode"] == "battle"
