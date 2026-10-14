# SPDX-License-Identifier: MIT
"""The Colony Ledger (ADR-066): the M.U.L.E. loop, advanced, driven by each realm's chemistry and ecology.

Pure, clock-free core (the `ArkFleet` shape): every call takes the round/day number; nothing here touches a server,
Blender or Unreal. The server will drive it; tests drive it faster; the Java port follows the same names.

    from colony_ledger import Ledger
    L = Ledger("WORLD-ZERO", seed=1)
    L.claim("richey", deed=240)                      # a plot = a deed; its profile is island_chemistry.profile(deed, realm)
    L.outfit("richey", deed=240, family="FOOD", worker="mule")      # consumes the parts the chemistry names
    L.produce(round_no=1, ecology={240: {"seral": 1, "biodiversity": 1.4, "season": "summer"}})
    L.market_day(round_no=1, orders=[...])           # double auction per item; shop + inn are standing buyers
    L.event(round_no=1)                              # one event per realm per round, rolled from the chemistry
    L.day_book(deed=240, day=12, hour=9, ecology=...)# Animal-Crossing finds: fish, bugs, fossils, ripe fruit
    L.raid(...) / L.defend(...)                      # Arc-Raiders scavenging with cargo interception
    L.score()                                        # colony wealth per player

Items are the realm's catalog (`catalog(realm)`), derived from the chemistry tables: every ore, herb, fruit, crop,
livestock yield, crystal, power-unit part and salvage is its own line, grouped into the four price families.
"""
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "blender"))
import island_chemistry as CH  # noqa: E402

FAMILIES = ("FOOD", "ENERGY", "ORE", "CRYSTAL")
PART_COST = {   # outfitting a worker for a family consumes these parts (from the island's own goods or the market)
    "FOOD": {"iron": 1, "plank": 2},                 # plough and cart
    "ENERGY": {"iron": 2, "copper": 1},              # rotor + shaft (the Codex PowerUnit minus the battery)
    "ORE": {"iron": 2, "plank": 1},                  # pick and rails
    "CRYSTAL": {"copper": 1, "crystal": 1},          # lamp and cutter
}
WORKER_KINDS = ("mule", "power_unit")                # pack mule (REALM-CASTS) or Codex PowerUnit
SPOILAGE = 0.15                                      # FOOD lost per round if unsold
ENERGY_PER_WORKER = 1.0
FLOOR = {"FOOD": 2.0, "ENERGY": 3.0, "ORE": 4.0, "CRYSTAL": 8.0}     # shop/inn standing bids, per unit
FISH_SEASON = {"rillperch": ("spring", "summer"), "glassfin": ("summer", "autumn"), "skytrout": ("autumn", "winter"), "ember_koi": ("winter", "spring")}
BUGS_BY_SERAL = {0: ("fireweed_moth", "yarrow_beetle"), 1: ("meadow_bee", "blue_butterfly"), 2: ("scrub_cricket", "hen_thief_wasp"), 3: ("stag_beetle", "oak_lanternfly")}
FOSSILS = ("shard_fossil", "ammonite", "starmetal_shard", "old_ark_plank")
EVENTS = ("meteor", "blight", "raiders", "wampus", "festival", "quiet")


NPC_WANTS = {   # cast roles (data/art/<realm>/population-plan.json friendly types) -> the items they ask for
    "Baker": ("wheat", "egg", "milk"), "Cook": ("carrot", "cabbage", "egg"), "Smith": ("iron", "copper", "coal"), "Miner": ("coal", "plank"),
    "Herbalist": ("dawnleaf", "rillprism", "cinderbud", "stillmoss", "stridefern", "clearbell"), "Apothecary": ("clearbell", "stillmoss", "honey"),
    "Healer": ("honey", "clearbell"), "Jeweller": ("gold", "crystal", "silver"), "Tinker": ("gearbox", "rotor", "copper"), "Carpenter": ("plank",),
    "Farmer": ("wheat", "corn"), "Shepherd": ("wool",), "Miller": ("wheat",), "Innkeeper": ("apple", "cherry", "plum", "egg", "milk"),
    "Fisher": ("rillperch", "glassfin", "skytrout", "ember_koi"), "Weaver": ("wool",), "Tailor": ("wool",), "Keymaker": ("iron", "gold"),
    "DragonKeeper": ("coal", "gold"), "UnicornGuide": ("clearbell", "dawnleaf", "apple"), "UnicornMedic": ("stillmoss", "honey"),
    "UnicornQuestgiver": ("rillprism", "clearbell", "starmetal"), "UnicornSentinel": ("crystal",), "RainbowWarden": ("crystal", "gold"),
    "WellKeeper": ("plank", "iron"), "King": ("gold", "starmetal"), "Queen": ("cherry", "crystal"), "Steward": ("wheat", "gold"),
}


def population(realm):
    """The realm's cast (friendly NPC types with individuals) and its quests, if the art plan exists."""
    import json
    name = {"PORTAL": "portal", "GALLERY-CITY": "gallery", "PARCELS": "parcels", "BRICKS": "bricks", "LABYRINTH": "labyrinth"}.get(realm.upper(), realm.lower())
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "art", name, "population-plan.json")
    try:
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
    except OSError:
        return {"types": [], "quests": []}
    types = sorted({p["type"] for p in d.get("population", []) if p.get("faction") == "friendly"})
    return {"types": types, "quests": d.get("quests", [])}


def family_of(item):
    if item in ("coal", "copper", "iron", "gold", "starmetal", "silver", "tin", "cobalt"):
        return "ORE"
    if item in ("crystal", "crystal2", "geode"):
        return "CRYSTAL"
    if item in ("energy", "rotor", "gearbox", "battery", "shaft", "torch_oil", "plane_fuel"):
        return "ENERGY"
    return "FOOD"


def catalog(realm="WORLD-ZERO"):
    """Every collectible line the realm trades, derived from its chemistry table."""
    R = CH.REALMS[realm.upper()]
    items = set(R["ores"]) | set(R["herbs"]) | set(R["crops"]) | {"crystal", "plank", "energy"}
    for s in R["orchard"]:
        items.add(CH.ORCHARD[s][0])
    for k in R["livestock"]:
        items.add(CH.LIVESTOCK[k].split("@")[0])
    items |= {"gearbox", "rotor", "shaft", "battery"}           # power-unit parts (Codex) are tradeable salvage
    return sorted(items)


class Plot:
    def __init__(self, deed, realm, owner):
        self.deed, self.realm, self.owner = deed, realm, owner
        self.chem = CH.profile(deed, realm)
        self.workers = []            # [(kind, family)]
        self.store = {}              # item -> units on the island
        self.defence = 0             # fences/towers/traps/patrols
        self.collection = set()      # first-of-kind finds (the museum)
        self.charm = 0.0

    def add(self, item, n):
        self.store[item] = self.store.get(item, 0.0) + n

    def take(self, item, n):
        have = self.store.get(item, 0.0)
        if have < n:
            return False
        self.store[item] = have - n
        return True


class Ledger:
    def __init__(self, realm="WORLD-ZERO", seed=1):
        self.realm = realm.upper()
        self.rng = random.Random(seed * 7 + 3)
        self.plots = {}              # deed -> Plot
        self.prices = {it: FLOOR[family_of(it)] * 1.5 for it in catalog(self.realm)}
        self.log = []
        self.hulks = {}              # deed -> {item: n} salvage sites (events drop them)
        self.cargo_in_air = []       # [(owner, from_deed, to_deed, item, n, arrive_round)]

    # ---- plots and workers ------------------------------------------------------------------------------------
    def claim(self, owner, deed):
        if deed in self.plots:
            return "TAKEN"
        self.plots[deed] = Plot(deed, self.realm, owner)
        return "CLAIMED"

    def outfit(self, owner, deed, family, worker="mule"):
        p = self.plots.get(deed)
        if p is None or p.owner != owner or family not in FAMILIES or worker not in WORKER_KINDS:
            return "REFUSED"
        cost = PART_COST[family]
        if not all(p.store.get(it, 0.0) >= n for it, n in cost.items()):
            return "NO_PARTS"
        for it, n in cost.items():
            p.take(it, n)
        p.workers.append((worker, family))
        return "OUTFITTED"

    def adjacency(self, deed, family):
        """M.U.L.E. bonus: same-owner neighbours (deed±1, ±100 on the 100-wide grid) with a worker of the same family."""
        p = self.plots[deed]
        n = 0
        for d in (deed - 1, deed + 1, deed - 100, deed + 100):
            q = self.plots.get(d)
            if q and q.owner == p.owner and any(f == family for _, f in q.workers):
                n += 1
        return min(n, 3)

    # ---- production: chemistry x ecology ----------------------------------------------------------------------
    def produce(self, round_no, ecology=None):
        """Each worker makes its family's items; chemistry sets what and how much, ecology (seral stage,
        biodiversity, season) sets the FOOD multiplier; every worker burns one ENERGY or halts."""
        ecology = ecology or {}
        out = {}
        for deed, p in self.plots.items():
            eco = ecology.get(deed, {"seral": 1, "biodiversity": 1.0, "season": "summer"})
            c = p.chem
            # energy first: the island's own power source yields energy_per_unit per round, stored as 'energy'
            p.add("energy", c["power_unit"]["energy_per_unit"])
            made = {}
            for kind, fam in p.workers:
                if not p.take("energy", ENERGY_PER_WORKER):
                    made["halted"] = made.get("halted", 0) + 1
                    continue
                mult = (1.0 + self.adjacency(deed, fam)) * (1.25 if kind == "power_unit" else 1.0)
                if fam == "FOOD":
                    fert = c["soil"]["fertility"]
                    eco_mult = {0: 0.6, 1: 1.3, 2: 0.9, 3: 0.8}.get(int(eco.get("seral", 1)), 1.0) * min(1.5, 0.7 + 0.3 * float(eco.get("biodiversity", 1.0)))
                    season = {"spring": 1.0, "summer": 1.2, "autumn": 1.4, "winter": 0.4}.get(eco.get("season", "summer"), 1.0)
                    for crop in c["soil"]["crops"]:
                        made[crop] = made.get(crop, 0.0) + 2.0 * fert * eco_mult * season * mult
                    for sp, info in c["flora"]["orchard"].items():
                        if eco.get("season", "summer") in ("summer", "autumn"):
                            made[info["fruit"]] = made.get(info["fruit"], 0.0) + 1.5 * fert * mult
                    for k, y in c["fauna"]["livestock"].items():
                        made[y.split("@")[0]] = made.get(y.split("@")[0], 0.0) + 1.0 * mult
                    for h in c["flora"]["herbs"]:
                        if BUGS_BY_SERAL.get(int(eco.get("seral", 1))):
                            made[h] = made.get(h, 0.0) + 0.5 * mult     # herbs are stage-locked: a mosaic pays
                elif fam == "ORE":
                    g = c["geology"]
                    for ore in c["ores_here"]:
                        base = {"coal": 2.0, "copper": 1.5, "iron": 1.5, "gold": 0.4, "starmetal": 0.0, "silver": 0.5, "tin": 1.0, "cobalt": 0.6}.get(ore, 0.5)
                        if ore == "gold":
                            base *= g["gold_mult"]
                        if ore == "starmetal" and g["starmetal_crater"]:
                            base = 0.3
                        made[ore] = made.get(ore, 0.0) + base * g["ore_mult"] * mult
                elif fam == "CRYSTAL":
                    made["crystal"] = made.get("crystal", 0.0) + c["economy"]["goods"]["CRYSTAL"] * 2.0 * mult
                elif fam == "ENERGY":
                    made["energy"] = made.get("energy", 0.0) + c["economy"]["goods"]["ENERGY"] * 2.0 * mult
            # spoilage on unsold FOOD from earlier rounds
            for it in list(p.store):
                if family_of(it) == "FOOD" and it not in ("plank",) and p.store[it] > 0:
                    p.store[it] *= (1.0 - SPOILAGE)
            for it, n in made.items():
                if it != "halted":
                    p.add(it, n)
            out[deed] = made
        self.log.append(("produce", round_no, out))
        return out

    # ---- market day: a double auction per item, walking toward the crossing ------------------------------------
    def market_day(self, round_no, orders):
        """orders: [(owner, deed, 'ask'|'bid', item, units, price)]. Returns fills; unfilled asks sell to the
        shop/inn at the family floor. Prices move toward each item's crossing (M.U.L.E.'s price lines)."""
        fills = []
        by_item = {}
        for o in orders:
            by_item.setdefault(o[3], []).append(o)
        for item, os_ in by_item.items():
            asks = sorted([o for o in os_ if o[2] == "ask"], key=lambda o: o[5])
            bids = sorted([o for o in os_ if o[2] == "bid"], key=lambda o: -o[5])
            while asks and bids and bids[0][5] >= asks[0][5]:
                a, b = asks[0], bids[0]
                n = min(a[4], b[4])
                price = (a[5] + b[5]) / 2.0
                seller, buyer = self.plots.get(a[1]), self.plots.get(b[1])
                if seller is None or not seller.take(item, n):
                    asks.pop(0)
                    continue
                arrive = round_no + 1 + abs(a[1] - b[1]) // 100      # arks haul: distance in district rows
                self.cargo_in_air.append((b[0], a[1], b[1], item, n, arrive))
                fills.append((a[0], b[0], item, n, price))
                self.prices[item] = 0.7 * self.prices.get(item, price) + 0.3 * price
                asks[0] = a[:4] + (a[4] - n,) + a[5:]
                bids[0] = b[:4] + (b[4] - n,) + b[5:]
                if asks[0][4] <= 0:
                    asks.pop(0)
                if bids[0][4] <= 0:
                    bids.pop(0)
            for a in asks:                       # the shop and the inn always buy, at the floor
                seller = self.plots.get(a[1])
                if seller and a[4] > 0 and seller.take(item, a[4]):
                    fl = FLOOR[family_of(item)]
                    fills.append((a[0], "shop", item, a[4], fl))
                    self.prices[item] = 0.8 * self.prices.get(item, fl) + 0.2 * fl
        self.settle_cargo(round_no)
        self.log.append(("market", round_no, fills))
        return fills

    def settle_cargo(self, round_no):
        """Cargo in the air lands when its ark arrives; cargo still flying can be intercepted (raid)."""
        landed = []
        for c in list(self.cargo_in_air):
            owner, frm, to, item, n, arrive = c
            if arrive <= round_no:
                dest = self.plots.get(to)
                if dest:
                    dest.add(item, n)
                landed.append(c)
                self.cargo_in_air.remove(c)
        return landed

    # ---- events: rolled from the chemistry, one per realm per round --------------------------------------------
    def event(self, round_no):
        if not self.plots:
            return ("quiet", None)
        kind = self.rng.choice(EVENTS)
        deed = self.rng.choice(sorted(self.plots))
        p = self.plots[deed]
        detail = None
        if kind == "meteor":
            p.chem["geology"]["starmetal_crater"] = True
            p.chem["geology"]["grade"] = "LEGENDARY"
            p.chem["geology"]["ore_mult"] = 3.0
            detail = "starmetal crater on deed %d" % deed
        elif kind == "blight" and p.chem["flora"]["orchard"]:
            sp = self.rng.choice(sorted(p.chem["flora"]["orchard"]))
            fruit = p.chem["flora"]["orchard"][sp]["fruit"]
            p.store[fruit] = p.store.get(fruit, 0.0) * 0.5
            detail = "%s blight on deed %d" % (sp, deed)
        elif kind == "raiders":
            rich = max(self.plots.values(), key=lambda q: q.store.get("energy", 0.0))
            stolen = rich.store.get("energy", 0.0) * 0.5
            rich.store["energy"] = rich.store.get("energy", 0.0) - stolen
            far = min(self.plots, key=lambda d: -abs(d - rich.deed))
            self.hulks.setdefault(far, {})
            self.hulks[far]["rotor"] = self.hulks[far].get("rotor", 0) + 1       # the stolen unit becomes salvage
            self.hulks[far]["energy"] = self.hulks[far].get("energy", 0.0) + stolen
            detail = "raiders took %.1f energy from deed %d; a hulk drifted to deed %d" % (stolen, rich.deed, far)
        elif kind == "wampus":
            detail = "a creature hides on deed %d" % deed
            p.add("bounty", 1)
        elif kind == "festival":
            fam = self.rng.choice(FAMILIES)
            for it in self.prices:
                if family_of(it) == fam:
                    self.prices[it] *= 1.5
            detail = "festival doubles demand for %s" % fam
        self.log.append(("event", round_no, kind, detail))
        return (kind, detail)

    # ---- Animal Crossing: the day book ------------------------------------------------------------------------
    def day_book(self, deed, day, hour, ecology=None):
        """What can be found on this island today: fish by season and hour, bugs by seral stage, fossils in the
        keel, ripe fruit. First-of-kind goes to the collection (museum) with a bonus."""
        p = self.plots[deed]
        eco = ecology or {"seral": 1, "biodiversity": 1.0, "season": "summer"}
        season = eco.get("season", "summer")
        rng = random.Random(deed * 100003 + day)
        finds = []
        for f in p.chem["water"]["fish"]:
            if season in FISH_SEASON[f] and (6 <= hour <= 10 or 17 <= hour <= 21):
                finds.append(f)
        finds.extend(BUGS_BY_SERAL.get(int(eco.get("seral", 1)), ()))
        if rng.random() < 0.3:
            finds.append("starmetal_shard" if p.chem["geology"]["starmetal_crater"] else rng.choice(FOSSILS[:2]))
        if season in ("summer", "autumn"):
            finds.extend(info["fruit"] for info in p.chem["flora"]["orchard"].values())
        new = [f for f in finds if f not in p.collection]
        p.collection.update(new)
        for f in finds:
            p.add(f, 1)
        bonus = 5.0 * len(new)
        p.charm += 0.1 * len(new)
        return {"finds": finds, "new_in_collection": new, "bonus": bonus, "requests": self.requests(deed, day)}

    # ---- fishing spots and the sky-sea water network --------------------------------------------------------
    FISHING_SPOTS = ("lake", "stream", "pier", "sky_river", "ocean_basin")

    def fishing(self, deed, day, hour, season="summer"):
        """What bites where: each spot has a subset of the island's fish; the sky river is where the rare one is."""
        p = self.plots[deed]
        fish = p.chem["water"]["fish"]
        rng = random.Random(deed * 31 + day * 7 + hour)
        table = {}
        for spot in self.FISHING_SPOTS:
            pool = [f for f in fish if season in FISH_SEASON[f]]
            if spot == "sky_river":
                pool = pool + ["rainbow_eel"] if 17 <= hour <= 21 else pool
            if spot == "ocean_basin":
                pool = pool + ["basin_ray"]
            table[spot] = rng.choice(pool) if pool and (6 <= hour <= 10 or 17 <= hour <= 21) else None
        return table

    def water_network(self):
        """Sky-sea boats: islands whose water connects (same district row = shared sky river / basin lane). A boat
        can only sail between connected deeds; arks fly anywhere. Returns {deed: [reachable deeds]}."""
        lanes = {}
        for d in self.plots:
            lanes[d] = sorted(e for e in self.plots if e != d and abs(e - d) < 100 and (e // 100) == (d // 100))
        return lanes

    def requests(self, deed, day):
        """News-board requests from the realm's cast (population plan: kings, unicorn guides, bakers...): each asks
        for items from NPC_WANTS that this island's chemistry can grow or dig, and pays in an item the island
        cannot make (the cross-realm pull). Quest-giver roles also surface their quest from the plan (PORT09)."""
        p = self.plots[deed]
        rng = random.Random(deed * 7 + day * 13)
        pop = population(self.realm)
        roles = [t for t in pop["types"] if t in NPC_WANTS] or sorted(NPC_WANTS)
        cat = catalog(self.realm)
        cannot = [it for it in cat if it not in p.store and family_of(it) == p.chem["economy"]["need"]]
        makeable = set(p.chem["soil"]["crops"]) | set(p.chem["flora"]["herbs"]) | set(p.chem["ores_here"]) | {"crystal", "plank"}
        makeable |= {i["fruit"] for i in p.chem["flora"]["orchard"].values()} | {y.split("@")[0] for y in p.chem["fauna"]["livestock"].values()}
        out = []
        for role in rng.sample(roles, min(3, len(roles))):
            wants = [it for it in NPC_WANTS[role] if it in makeable] or [NPC_WANTS[role][0]]
            quest = next((q for q in pop["quests"] if q.get("giver_type") == role), None)
            out.append({"npc": role, "wants": wants[:2], "pays": rng.choice(cannot) if cannot else "gold",
                        "quest": quest["id"] if quest else None})
        return out

    # ---- Arc Raiders: scavenge and defend -------------------------------------------------------------------
    def raid(self, raider, from_deed, target_deed, round_no):
        """Land on a hulk or a rich land and loot; the owner's defence sets the time-to-loot; loot flies home as
        cargo that can be intercepted. Returns the loot or a refusal."""
        if target_deed in self.hulks:
            loot = self.hulks.pop(target_deed)
        else:
            t = self.plots.get(target_deed)
            if t is None or t.chem["geology"]["grade"] == "COMMON":
                return ("NOTHING_THERE", {})
            if self.rng.random() < min(0.9, 0.2 * t.defence):          # caught: defenders take the raider's cargo
                mine = [c for c in self.cargo_in_air if c[0] == raider]
                for c in mine:
                    self.cargo_in_air.remove(c)
                    t.add(c[3], c[4])
                return ("CAUGHT", {c[3]: c[4] for c in mine})
            loot = {}
            for it in ("gearbox", "rotor", "battery"):
                if self.rng.random() < 0.5:
                    loot[it] = 1
            for ore in t.chem["ores_here"][-2:]:
                loot[ore] = loot.get(ore, 0) + 1
        for it, n in loot.items():
            self.cargo_in_air.append((raider, target_deed, from_deed, it, n, round_no + 1 + abs(target_deed - from_deed) // 100))
        self.log.append(("raid", round_no, raider, target_deed, loot))
        return ("LOOTED", loot)

    def defend(self, owner, deed, kind):
        """fence/lantern/watchtower/patrol/trap: each raises defence; traps consume a crystal."""
        p = self.plots.get(deed)
        if p is None or p.owner != owner:
            return "REFUSED"
        if kind == "trap" and not p.take("crystal", 1):
            return "NO_CRYSTAL"
        p.defence += {"fence": 1, "lantern": 1, "watchtower": 2, "patrol": 2, "trap": 3}.get(kind, 0)
        return "BUILT"

    # ---- score -------------------------------------------------------------------------------------------------
    def score(self):
        wealth = {}
        for p in self.plots.values():
            v = 100.0 + 25.0 * len(p.workers) + 5.0 * p.defence + 2.0 * len(p.collection) + 10.0 * p.charm
            for it, n in p.store.items():
                v += n * self.prices.get(it, FLOOR[family_of(it)])
            wealth[p.owner] = wealth.get(p.owner, 0.0) + v
        return {k: round(v, 1) for k, v in wealth.items()}
