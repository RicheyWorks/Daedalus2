# SPDX-License-Identifier: MIT
"""AST-only builder projection check. No builder import, Pillow, assets, main(), or generated output."""
import ast
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
source = (HERE / "build_demo.py").read_text(encoding="utf-8")
tree = ast.parse(source, filename="build_demo.py")
compile(tree, "build_demo.py", "exec")  # Compile only; never execute the module/imports.
scope = {}
for node in tree.body:
    if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name) and node.targets[0].id in {
        "QUEST", "OPTIONAL_QUEST", "FINAL", "FINAL_SCALE", "BOSS_BACKDROP"
    }:
        scope[node.targets[0].id] = ast.literal_eval(node.value)
main = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "main")
assignments = {n.targets[0].id: n.value for n in main.body if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name)}
data_expr = assignments["data"]
dungeon_expr = next(value for key, value in zip(data_expr.keys, data_expr.values) if isinstance(key, ast.Constant) and key.value == "dungeons")


def evaluate(expr, **extra):
    return eval(compile(ast.Expression(expr), "build_demo.py:projection", "eval"), {**scope, **extra})


def catalog(name):
    return json.loads((HERE / "../../data/rpg" / (name + ".json")).read_text(encoding="utf-8"))


original = [("Cave", "Cinder Forge"), ("Tower", "Windcut Aerie"), ("Ruins", "Sunwell Sanctum"), ("CrystalShrine", "The Shattered Heart")]
assert scope["QUEST"] == original
quest_spec = evaluate(assignments["quest_spec"], projection=None)
assert quest_spec == original + [("AirshipPad", "Gearwright's Folly")]
assert scope["FINAL_SCALE"] == {"hp": 0.33, "attack": 0.7, "why": "three of six shards: the Devourer only half-forms in this demo"}
dungeons = catalog("dungeons")["dungeons"]["prism"]
bosses = catalog("prism-bosses")["bosses"]
quest = [next(d for d in dungeons if d["name"] == name) for _, name in quest_spec]
quest_bosses = {d["name"]: next(b for b in bosses if b["dungeon"] == d["name"]) for d in quest}
projected = evaluate(dungeon_expr, projection=None, quest_spec=quest_spec, quest=quest, quest_bosses=quest_bosses)
assert [d["name"] for d in projected[:4]] == [name for _, name in original]
assert [d["optional"] for d in projected] == [False, False, False, False, True]
folly = projected[4]
assert folly["floors"] == quest[4]["floors"] and len(folly["floors"]) == 3
assert folly["boss_data"] == quest_bosses[folly["name"]] and folly["boss_data"]["shard"] == "-"
assert folly["boss_backdrop"] == "ruins" and not folly["final"]
assert len([d for d in projected if not d["final"] and d["boss_data"]["shard"] != "-"]) == 3

# Exercise the real conditional/comprehension with a bossless Portal projection. The supplied
# projection owns its route list and dungeon objects exactly as before; no optional property leaks.
portal_dungeon = catalog("dungeons")["dungeons"]["portal"][0]
portal = {"quest": [("PortalRoute", portal_dungeon["name"])], "dungeons": [portal_dungeon]}
portal_spec = evaluate(assignments["quest_spec"], projection=portal)
assert portal_spec is portal["quest"]
portal_output = evaluate(dungeon_expr, projection=portal, quest_spec=portal_spec, quest=portal["dungeons"], quest_bosses={portal_dungeon["name"]: None})
assert len(portal_output) == 1 and portal_output[0]["landmark"] == "PortalRoute"
assert portal_output[0]["boss_data"] is None and "optional" not in portal_output[0]
print("Prismheart Folly builder projection: original routes, optional catalog, final scaling and Portal isolation passed; AST compile only.")
