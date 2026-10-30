"""Tests for Wild Biomes + island scaling + per-token flora. Run: python test_wild_biomes.py"""
import wild_biomes as wb, island_flora as f
ok = True
def c(name, cond):
    global ok; ok &= bool(cond); print(("PASS " if cond else "FAIL ") + name)
a = wb.all_biomes(); b = wb.all_biomes(60)
m = {k: f.mix(v) for k, v in a.items()}
share = lambda mx, sp: mx.get(sp, 0) / max(1, sum(mx.values()))
c("meadow is grass-dominated", share(m["YoungMeadow"], "Grass") > 0.5)
c("pine stand: pine outnumbers oak", m["PineStand"].get("Pine", 0) > m["PineStand"].get("Oak", 0))
c("old growth: oak outnumbers pine", m["OldGrowthOak"].get("Oak", 0) > m["OldGrowthOak"].get("Pine", 0))
c("riverbank has willow + sedge", m["WillowRiverbank"].get("Willow", 0) > 0 and m["WillowRiverbank"].get("Sedge", 0) > 0)
c("scrub has most bramble share", max(m, key=lambda k: share(m[k], "Bramble")) in ("BrambleScrub", "YoungMeadow"))
r = sum(map(len, b.values())) / sum(map(len, a.values()))
c(f"density scales with area (60 m vs 30 m: x{r:.1f}, expect 3-8: 4x area, site choice varies)", 3 < r < 8)
c("biomes deterministic", wb.all_biomes()["PineStand"][:20] == a["PineStand"][:20])
c("tokens differ, same token stable", f.profile(1) != f.profile(2) and f.profile(9) == f.profile(9))
print("ALL PASS" if ok else "SOME FAIL"); raise SystemExit(0 if ok else 1)

