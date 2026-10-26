# adds the island's six animals (hephaestus.json resources.animals) to layout.json as a pen by the hot springs
import json
P = r"C:\Users\730ri\projects\Daedalus2\data\islands\hephaestus\layout.json"
l = json.load(open(P))
l["placements"] = [p for p in l["placements"] if p.get("zone") != "livestock_pens"]
herd = [("emberhen", "Mob_Chicken", 3, 1.0), ("ashgoat", "Mob_Goat", 3, 1.0), ("forgeox", "Mob_Cow", 2, 1.1),
        ("lavaboar", "Mob_Boar_Wild", 3, 1.0), ("cinderwool", "Mob_Sheep", 3, 1.0), ("vent_bees", "Mob_Bee", 2, 1.5)]
x0, y0 = -130, 150  # pens just east of the hot springs (-180, 200), downhill of the water chain
for row, (animal, asset, n, sc) in enumerate(herd):
    for i in range(n):
        l["placements"].append({"asset": asset, "x": x0 + i * 6, "y": y0 + row * 8, "z": 0, "yaw": (row * 47 + i * 73) % 360,
                                "scale": sc, "zone": "livestock_pens", "animal": animal})
l["placements"].append({"asset": "Prop_WaterTrough_Iron", "x": x0 - 8, "y": y0 + 20, "z": 0, "yaw": 90, "scale": 1.2, "zone": "livestock_pens"})
l["zones"] = l["zones"] + ["livestock_pens"] if "livestock_pens" not in l["zones"] else l["zones"]
json.dump(l, open(P, "w"), indent=1)
print(len(l["placements"]), "placements")
