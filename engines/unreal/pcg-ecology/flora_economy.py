"""Flora -> economy bridge (board #5/#7 support).
Reads the economy data (data/economy/*.json, prometheus) read-only.
- DROPS: what each ecology species yields when harvested (tool, items).
- validate(): every recipe input/output is a known item, no cycles.
- raw_cost(): roll a recipe down to raw (non-craftable) inputs.
- island_craftable(token): which recipes an island's own flora can fully feed."""
import json, os, sys
import island_flora

ECON = os.environ.get("DAEDALUS_ECON", r"C:\Users\730ri\projects\Daedalus2\data\economy")
DROPS = {  # species: (tool, [(item, n)])
    "Oak":     ("axe",    [("hardwood", 4)]),
    "Pine":    ("axe",    [("hardwood", 2), ("resin", 2)]),
    "Willow":  ("axe",    [("hardwood", 1), ("willow_bark", 3)]),
    "Bramble": ("sickle", [("fiber", 2)]),
    "Sedge":   ("sickle", [("fiber", 1)]),
    "Grass":   ("sickle", [("fiber", 1)]),
    "Fern":    ("sickle", []),  # understory filler, no yield yet (candidate: yarrow forage)
}

def load():
    j = lambda f: json.load(open(os.path.join(ECON, f), encoding="utf-8"))
    return {i["id"] for i in j("items.json")["items"]}, j("recipes.json")["recipes"]

def producers(recipes):
    p = {}
    for r in recipes:
        for o in r["out"]:
            p.setdefault(o["item"], r)
    return p

def validate(items, recipes):
    errs = []
    for r in recipes:
        for x in r["in"] + r["out"]:
            if x["item"] not in items:
                errs.append(f"{r['id']}: unknown item {x['item']}")
    for _, ds in DROPS.values():
        for it, _n in ds:
            if it not in items:
                errs.append(f"drop: unknown item {it}")
    prod = producers(recipes)
    def walk(it, seen):
        if it in seen: errs.append(f"cycle via {it}"); return
        r = prod.get(it)
        if r:
            for x in r["in"]: walk(x["item"], seen | {it})
    for it in prod: walk(it, set())
    return errs

def raw_cost(item, n, prod, acc=None):
    acc = {} if acc is None else acc
    r = prod.get(item)
    if not r:
        acc[item] = acc.get(item, 0) + n; return acc
    out_n = next(o["n"] for o in r["out"] if o["item"] == item)
    batches = -(-n // out_n)
    for x in r["in"]:
        raw_cost(x["item"], x["n"] * batches, prod, acc)
    return acc

def island_yield(token):
    _, out = island_flora.generate(token)
    placed = out[0] if isinstance(out, tuple) else out
    y = {}
    for sp, c in island_flora.mix(placed).items():
        for it, n in DROPS.get(sp, ("", []))[1]:
            y[it] = y.get(it, 0) + n * c
    return y

def island_craftable(token, items, recipes):
    y, prod = island_yield(token), producers(recipes)
    res = {}
    for r in recipes:
        o = r["out"][0]
        need = raw_cost(o["item"], o["n"], prod)
        res[r["id"]] = all(k in y for k in need)  # every raw input grows on this island
    return y, res

if __name__ == "__main__":
    items, recipes = load()
    errs = validate(items, recipes)
    prod = producers(recipes)
    print("validate:", "OK" if not errs else errs)
    print("raw ark_hull_plank x1:", raw_cost("ark_hull_plank", 1, prod))
    for t in (1, 2, 3):
        y, c = island_craftable(t, items, recipes)
        print(f"token {t} yield {y} | flora-only craftable: {[k for k, v in c.items() if v]}")
    ok = not errs and raw_cost("charcoal", 2, prod) == {"hardwood": 4}
    print("PASS" if ok else "FAIL"); sys.exit(0 if ok else 1)
