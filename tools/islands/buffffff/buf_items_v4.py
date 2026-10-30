# Buffffff v4: original gap-fill items (story, Six-F stacking, food loop, water chain). Appends to manifest.json.
import os, json
SRC=open(r"C:\Users\730ri\projects\bot-team\art\buffffff\buf_items.py").read().split("# ---- HERBS")[0]
exec(SRC); SAVE_BLEND=False
old=json.load(open(os.path.join(ROOT,"manifest.json"))); have={x["asset"] for x in old}
FAMC={"Fire":"#E8473C","Frost":"#7FD4F2","Flora":"#5CCB4A","Flux":"#B05CE0","Fog":"#B8BCC8","Fang":"#D68A2E"}
SHARD=mat("PlanetShard","#4A2A6A"); CORE=mat("CoreGlow","#FF7A30"); BONE=mat("Bone","#E8E0C8"); PIPE=mat("Pipe","#7A6A5A"); MANURE=mat("Manure","#4A3220")
A=[]
LIV=[(s,0,0) for s in ("Buffalo","Fluffhen","Puffgoat","Muffpig","Tuffox","Snuffduck","Gruffsheep","Ruffrabbit")]
def add(n,k,b,g):
    if n in have: return
    A.append(n); asset(n,k,b,g)
# STORY: fragments of the shattered world, journals, relics (24)
for i,nm in enumerate(["Heartstone","Crustplate","Mantlechip","Orbitglass","Skyscar","Ringdust"]):
    add(f"Item_BUF_Lore_Shard_{nm}","item",lambda col,i=i:(box(col,0.2+0.03*i,0.15,0.3,0,0,0,SHARD,i*0.4),ball(col,0.05,0,0,0.3,CORE)),"story")
for i in range(1,9): add(f"Item_BUF_Lore_Journal_P{i}","item",lambda col,i=i:(box(col,0.22,0.16,0.03+0.005*i,0,0,0,mat("Jour"+str(i%3),["#6A3A2A","#3A4A6A","#5A5A2A"][i%3])),box(col,0.02,0.16,0.035,0.1,0,0,GOLD)),"story")
for nm,h in (("FirstHerder",2.0),("WellKeeper",1.8),("StackSage",1.9),("Shardfall",2.6)):
    add(f"Prop_BUF_Lore_Statue_{nm}","prop",lambda col,h=h:(box(col,1,1,0.4,0,0,0,STONE),cyl(col,0.25,h,0,0,0.4,STONE,8),ball(col,0.2,0,0,0.4+h,GOLD)),"story")
for nm in ("ImpactCrater","FallenOrbitRing","CoreVent","SkyAnchor","StarMap","QuestBoard"):
    add(f"Prop_BUF_Lore_{nm}","prop",lambda col,nm=nm:(cyl(col,2.5,0.4,0,0,0,STONE,14),cone(col,0.6,1.8,0,0,0.4,SHARD,5),ball(col,0.25,0,0,2.2,CORE)),"story")
# SIX-F STACKING gaps: overcharge cures, catalysts, stack charms, recipe tablets (36)
for f,c in FAMC.items():
    m=mat("Tonic_"+f,c)
    add(f"Item_BUF_Catalyst_{f}","item",lambda col,m=m:(ball(col,0.06,0,0,0,m),box(col,0.12,0.12,0.02,0,0,0,DARK)),"tonic")
    add(f"Item_BUF_Overcharge_Cure_{f}","item",lambda col,m=m:(cyl(col,0.05,0.12,0,0,0,CLEAN,8),cyl(col,0.03,0.04,0,0,0.12,m,8)),"tonic")
    add(f"Item_BUF_StackCharm_{f}","item",lambda col,m=m:(cyl(col,0.08,0.02,0,0,0,GOLD,12),ball(col,0.03,0,0,0.02,m)),"tonic")
    add(f"Prop_BUF_RecipeTablet_{f}","prop",lambda col,m=m:(box(col,0.6,0.12,0.8,0,0,0,STONE),box(col,0.4,0.02,0.5,0,-0.06,0.15,m)),"tonic")
    add(f"Item_BUF_HerbPouch_{f}","item",lambda col,m=m:(ball(col,0.1,0,0,0,m,0.8),cyl(col,0.03,0.04,0,0,0.15,DARK,6)),"herb")
    add(f"Prop_BUF_WildPatch_{f}","prop",lambda col,m=m:[cone(col,0.05,0.3,0.15*k-0.3,0.1*(k%2),0,m,5) for k in range(5)],"herb")
# FOOD LOOP gaps: manure->compost->fertilizer, shearing/milking tools, nests, feed sacks per species (32)
for st,c in (("Manure","#4A3220"),("Compost","#3A2A18"),("Fertilizer","#6A5A2A"),("Mulch","#7A5A3A")):
    add(f"Item_BUF_Loop_{st}","item",lambda col,c=c:box(col,0.4,0.3,0.25,0,0,0,mat("Loop_"+c,c)),"food")
for t in ("Shears","MilkPail","EggBasket","Brush","Hoof Pick","Halter","Crook","Spindle"):
    t=t.replace(" ","")
    add(f"Item_BUF_FarmTool_{t}","item",lambda col:(cyl(col,0.03,0.4,0,0,0,WOOD,6),box(col,0.15,0.04,0.1,0,0,0.4,DARK)),"livestock")
for sp,_,_ in LIV:
    add(f"Prop_BUF_Nest_{sp}","prop",lambda col:(cyl(col,0.4,0.15,0,0,0,mat("Straw","#D8C070"),10),ball(col,0.08,0,0,0.12,mat("P_Egg","#F4EFE2"))),"livestock")
    add(f"Item_BUF_FeedSack_{sp}","item",lambda col:(box(col,0.35,0.25,0.5,0,0,0,mat("Sack","#C9A36A")),box(col,0.36,0.26,0.05,0,0,0.35,GOLD)),"livestock")
for t in ("Spinner","Loom","SaltCure","Hatchery"):
    add(f"Prop_BUF_Workshop_{t}","prop",lambda col:(box(col,1.4,1,1,0,0,0,WOOD),cyl(col,0.3,0.1,0,0,1,DARK,12)),"food")
# WATER CHAIN gaps: pipes, valves, test kit, tablets, sickness/cure (26)
for p in ("Straight","Elbow","Tee","Valve","Spigot","Junction"):
    add(f"Prop_BUF_Pipe_{p}","prop",lambda col,p=p:(cyl(col,0.1,1.5 if p=="Straight" else 0.6,0,0,0,PIPE,8),ball(col,0.15,0,0,0.6,GOLD) if p!="Straight" else None),"water")
for i in ("PurifyTablet","PurityTestKit","Gutter","Downspout","RainBarrel","SettlingTank","UVLantern","CharcoalBrick","SandSack","Ladle"):
    add(f"Item_BUF_Water_{i}","item",lambda col:(cyl(col,0.12,0.2,0,0,0,CLAY,10),cyl(col,0.1,0.02,0,0,0.19,CLEAN,10)),"water")
for s,c in (("Murky","#6A6A3A"),("Brackish","#5A8A7A"),("Clean","#8FE3FF"),("Blessed","#F2E8A0")):
    add(f"Item_BUF_WaterGrade_{s}","item",lambda col,c=c:(cyl(col,0.06,0.18,0,0,0,GLASS,8),cyl(col,0.05,0.12,0,0,0.01,mat("WG_"+c,c),8)),"water")
add("Item_BUF_Cure_GutSickness","item",lambda col:(cyl(col,0.05,0.12,0,0,0,GLASS,8),ball(col,0.04,0,0,0.12,mat("Herb_Flora0","#5CCB4A"))),"water")
add("Prop_BUF_Lore_ShardSpring","prop",lambda col:(cyl(col,3,0.5,0,0,0,STONE,14),cyl(col,2.7,0.05,0,0,0.47,CLEAN,14),cone(col,0.5,2.5,0,0,0.5,SHARD,5)),"story")
json.dump(old+made,open(os.path.join(ROOT,"manifest.json"),"w"),indent=1); print("V4ADDED",len(made),"TOTAL",len(old)+len(made))

