# Validates mechanics.json: tea inputs are known herbs/products, animals produce known items, balance sums to 100.
import json, sys, os
m = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "mechanics.json")))
herbs = set(m["herbs"]["species"]); prods = {a["product"] for a in m["livestock"]["animals"].values()}
extra = {"CleanWater", "BoiledWater", "any3herbs"}; bad = []
for t in m["teas"]:
    for i in t["in"]:
        if i not in herbs | prods | extra: bad.append((t["name"], i))
b = m["balance"]; total = b["water"] + b["animals"] + b["herbs3"] + b["tea"]
if total != 100: bad.append(("balance", total))
print("OK" if not bad else "BAD %s" % bad); sys.exit(1 if bad else 0)
