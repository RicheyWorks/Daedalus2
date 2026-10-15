# SPDX-License-Identifier: MIT
"""A plain RPG player for the Prismheart demo's tests (Playwright page + the PRISM_DEMO hooks).

It plays like a careful person, not a cheat: the Lightmender heals anyone under half health, the Runecaster casts
the best spell she knows (the boss's weakness first), the rest attack, a Herb Tonic goes to anyone in trouble,
a Feather of Waking brings back whoever falls (the Runecaster first).
buy_spell(), gear_up() and stock_up() walk into the shops and buy like a player would.
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
                down = [m for m in pt if m[2] <= 0]
                if down and s["bag"].get("Feather of Waking") and (not heal or low[2] / low[3] >= 0.3):
                    plan = ("ITEM", "Feather of Waking", next((m for m in down if m[0] == "Tamsin"), down[0])[0])
                elif heal and low[2] / low[3] < 0.5:
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
                opts = [k for k, n in s["bag"].items() if n > 0 and (self.D.get("gear", {}).get(k) or {}).get("effect")]
                want = opts.index(plan[1]) if plan and plan[1] in opts else 0
                if b["oi"] != want:
                    self.press("down", 40); continue
                self.press("a", 50); continue
            if b["sub"] == "target":
                if plan and plan[2] and plan[2] in b["list"] and b["list"][b["target"]] != plan[2]:
                    self.press("down", 40); continue
                self.press("a", 50); continue
        return last

    def shop(self, kind, buys):
        """Walk into an interior shop (Magic, Item, ...), buy each name in buys once, in order, and walk out."""
        stock = [x["name"] for x in self.D["interiors"][kind]["stock"]]
        self.ev("PRISM_DEMO.warp('%s',5,5)" % kind); self.pg.wait_for_timeout(300)
        self.face("up")
        for _ in range(12):
            if self.st()["mode"] == "shop":
                break
            self.press("a", 250)
        at = 0
        for name in buys:
            want = stock.index(name)
            for _ in range((want - at) % len(stock)):
                self.press("down", 70)
            at = want
            self.press("a", 250)
        for _ in range(8):
            s = self.st()
            if s["mode"] == "field" and not s["dialog"]:
                break
            self.press("b", 200)

    def buy_spell(self, name):
        """Walk into the magic shop, talk to the mage, buy the spell. Returns True if Tamsin knows it after."""
        self.shop("Magic", [name])
        sp = self.spells.get(name, {})
        return any(name in m[6] for m in self.st()["party"]) if sp else False

    def gear_up(self, reserve=300):
        """Buy the best weapon each starting hero can hold, if it beats what they carry and leaves `reserve` gold."""
        kinds = {"Copper Blade": "sword", "Oak Staff": "staff", "Hunter Bow": "bow", "Iron Axe": "axe", "Steel Saber": "sword", "Silver Lance": "lance"}
        stock = sorted(self.D["interiors"]["Weapon"]["stock"], key=lambda x: -x["attack"])
        atk = {x["name"]: x["attack"] for x in stock}
        members = {m["name"]: m for m in self.D["party"]["members"]}
        s = self.st(); gold, buys = s["gold"], []
        for m in sorted(s["party"], key=lambda m: m[0] != "Corin"):
            mk = members[m[0]]["weapon_kinds"]
            fits = [x for x in stock if kinds.get(x["name"]) in mk or (kinds.get(x["name"]) == "sword" and "dagger" in mk)]
            best = next((x for x in fits if x["price"] <= gold - reserve and x["attack"] > atk.get(m[5], 0)), None)
            if best:
                gold -= best["price"]; buys.append(best["name"])
        if buys:
            self.shop("Weapon", buys)
        return buys

    def stock_up(self, feathers=3, tonics=6):
        """Before a boss, spend spare gold like a player would: Feathers of Waking first, then Herb Tonics."""
        price = {x["name"]: x["price"] for x in self.D["interiors"]["Item"]["stock"]}
        s = self.st(); gold, bag, buys = s["gold"], s["bag"], []
        for name, want in (("Feather of Waking", feathers), ("Herb Tonic", tonics)):
            for _ in range(max(0, want - bag.get(name, 0))):
                if gold < price[name]:
                    break
                gold -= price[name]; buys.append(name)
        if buys:
            self.shop("Item", buys)
        return buys

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
