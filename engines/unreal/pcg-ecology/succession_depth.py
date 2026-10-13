"""SUCCESSION depth: island biogeography species pool, seed rain between linked islands, windthrow storms,
nurse-pine facilitation for oak, and Climax Seed quest progress. Builds on succession_sim.Island."""
import math, json, random
import succession_sim as ss
POOL_ALL = ["Fireweed", "Grass", "Sedge", "Bramble", "Willow", "Pine", "Oak"]
def species_pool(dist_km, area_ha, seed=0):
    """MacArthur-Wilson flavour: richness rises with area, falls with isolation. Pioneers always arrive (wind)."""
    k = max(2, min(len(POOL_ALL), round(2 + 2.2 * math.log10(1 + area_ha) - 1.2 * math.log10(1 + dist_km))))
    return POOL_ALL[:k]
def seed_rain(src_pool, dst_pool, dist_km, wind_aligned, rng):
    """Each source species not yet on the target arrives with p = exp(-d/L); heavy seeds (Oak) travel worse."""
    got = []
    for sp in src_pool:
        if sp in dst_pool: continue
        L = (0.6 if sp == "Oak" else 3.0) * (2.0 if wind_aligned else 1.0)
        if sp == "Oak": L = 0.6   # acorns need an Ark or jays, not wind
        if rng.random() < math.exp(-dist_km / L): got.append(sp)
    return got
def windthrow(island, rng, p_old=0.08):
    """Storm: tiles at stage 3 (tall, shallow-rooted canopy) fall with p_old; gaps reset to 0."""
    n = 0
    for y in range(island.n):
        for x in range(island.n):
            if island.stage(x, y) == 3 and rng.random() < p_old: island.t[y][x] = 0.0; n += 1
    return n
def oak_can_establish(island, x, y):
    """Facilitation: oak seedlings establish only next to a stage>=2 tile (nurse pine/scrub shade + jay caching)."""
    for j in range(max(0, y - 1), min(island.n, y + 2)):
        for i in range(max(0, x - 1), min(island.n, x + 2)):
            if (i, j) != (x, y) and island.stage(i, j) >= 2: return True
    return False
def colonise(src_pool, dst_pool, dist_km, rng, ark=(), jays=0, wind_aligned=False):
    """Chapter 7: settle the bare islet. Wind seed rain as usual; each Ark cargo species arrives for sure;
    each jay feeder adds an independent 50% chance per crossing that acorns get cached on the islet (jays carry acorns km-scale)."""
    got = set(seed_rain(src_pool, dst_pool, dist_km, wind_aligned, rng))
    got |= {sp for sp in ark if sp in src_pool and sp not in dst_pool}
    if "Oak" in src_pool and "Oak" not in dst_pool and any(rng.random() < 0.5 for _ in range(jays)): got.add("Oak")
    return sorted(got)
def quest_progress(island, flags):
    """flags: dict of world facts from UE (livestock count, hives, drinkable, survived windthrow, brewed teas, grazed/dug tiles)."""
    Q = json.load(open(__file__.replace("succession_depth.py", "climax_seed_quest.json"), encoding="utf-8"))
    st = island.stages(); done = []
    for ch in Q["chapters"]:
        ok = True
        for g in ch["goals"]:
            t = g["type"]
            if t == "stage_tiles": ok &= st[g["stage"]] >= g["n"]
            elif t == "graze_tiles": ok &= len(island.grazed) >= g["n"]
            elif t == "dig_tiles": ok &= len(island.water) >= g["n"]
            elif t == "climax_mosaic": ok &= island.climax_ready()
            elif t == "brew": ok &= g["tea"] in flags.get("teas", ())
            elif t == "actor": ok &= flags.get(g["tag"], 0) >= g["n"]
            elif t == "place": ok &= flags.get(g["asset"], 0) >= g["n"]
            elif t == "survive_event": ok &= g["event"] in flags.get("survived", ())
            elif t == "species": ok &= flags.get("oaks", 0) >= g["min"]
            elif t == "colonised": ok &= len(flags.get("islet_species", ())) >= g["n"] and (not g.get("need_oak") or "Oak" in flags.get("islet_species", ()))
            elif t == "fire_rate":
                import fire_keeper; ok &= fire_keeper.fire_regime(flags.get("burn_rate", 0.0), seed=flags.get("seed", 0)) >= g["min_h"]
            elif t == "beaver_dams":
                import keystone_beaver as KB; o = KB.outcome([tuple(d) for d in flags.get("dam_cells", ())]); ok &= o["H"] >= g["min_h"] and o["old_growth"] >= g["min_old"]
            elif t == "choice": ok &= flags.get("bramble_choice") in g["options"]
        done.append((ch["id"], ok))
        if not ok: break   # chapters unlock in order
    return done
if __name__ == "__main__":
    ok = True
    def c(n, v):
        global ok; ok &= bool(v); print(("PASS " if v else "FAIL ") + n)
    import random as _r
    c("ark guarantees cargo species", "Willow" in colonise(["Willow", "Oak"], [], 50, _r.Random(1), ark=["Willow"]))
    c("acorns never make 20 km by wind alone", not any("Oak" in colonise(["Oak"], [], 20, _r.Random(i)) for i in range(200)))
    c("jays carry acorns across", sum("Oak" in colonise(["Oak"], [], 20, _r.Random(i), jays=2) for i in range(400)) > 250)
    c("big near island richer than small far one", len(species_pool(0.5, 200)) > len(species_pool(20, 2)))
    c("pioneers always present", "Fireweed" in species_pool(50, 0.5))
    rng = random.Random(1); arr = [seed_rain(POOL_ALL, ["Fireweed"], 1.0, True, rng) for _ in range(400)]
    c("wind seeds (pine) arrive far more often than acorns", sum("Pine" in a for a in arr) > 3 * sum("Oak" in a for a in arr))
    I = ss.Island(10, 200); n = windthrow(I, random.Random(3)); c("windthrow opens gaps in old forest (%d)" % n, 0 < n < 30 and I.stages()[0] == n)
    J = ss.Island(5, 0); c("no oak on open scar (no nurse)", not oak_can_establish(J, 2, 2))
    J.t[2][1] = 30; c("oak establishes beside a nurse pine", oak_can_establish(J, 2, 2))
    K = ss.Island(12, 0); c("chapter 1 needs the first tea", quest_progress(K, {})[0] == ("ash_field", False))
    K2 = ss.Island(12, 100); K2.disturb(2, 2, 2); K2.step(1)
    pr = quest_progress(K2, {"teas": ["ladder"]}); c("chapter 1 done with pioneer patch + first tea: %s" % pr[:2], pr[0] == ("ash_field", True))
    print("ALL PASS" if ok else "SOME FAIL"); raise SystemExit(0 if ok else 1)

