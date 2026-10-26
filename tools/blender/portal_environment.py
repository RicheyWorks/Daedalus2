"""Original Portal field/town/castle/cave kit. One metre tile units; static art only."""
from pathlib import Path
exec(compile(Path(__file__).with_name('portal_common.py').read_text(),__file__,'exec'))
grass=mat('Portal grass',(.18,.50,.16));stone=mat('Portal stone',(.27,.33,.46));water=mat('Portal water',(.05,.25,.63));sand=mat('Portal sand',(.74,.59,.28));wood=mat('Portal wood',(.36,.17,.08));red=mat('Portal tile roofs',(.48,.075,.08))
KIT=[('GrassTile','Field tile'),('ForestTile','Forest tile marker'),('MountainTile','Impassable terrain marker'),('WaterTile','Water terrain'),('SwampTile','Swamp terrain'),('SandTile','Coastal sand'),('RoadTile','Town approach road'),('TownWall','Town facade wall'),('TownDoor','Building entry frame'),('ShopCounter','Shop interaction station'),('InnBed','Inn rest presentation'),('SmithAnvil','Equipment upgrade station'),('CastleWall','Castle boundary'),('CastleGate','Castle entry frame'),('Throne','Queen quest presentation'),('CaveWall','Dungeon boundary'),('CaveFloor','Dungeon tile'),('StairsDown','Dungeon depth transition'),('KeyChest','Existing depth loot/key presentation'),('BronzeGate','Bronze lock presentation'),('SilverGate','Silver lock presentation'),('StarGate','Star lock presentation'),('PortalArch','Discovered rainbow entry presentation'),('DragonEggNest','Land-included egg presentation'),('StagePlatform','Touring jukebox/concert staging'),('DragonEggIntact','Egg state: intact'),('DragonEggCracked','Egg state: cracked')]
records=[]
for i,(name,role) in enumerate(KIT):
    parts=[]
    if name.endswith('Tile') or name=='CaveFloor':
        m=grass if name in ['GrassTile','ForestTile'] else water if name=='WaterTile' else sand if name=='SandTile' else wood if name=='SwampTile' else stone
        box((0,0,.08),(1,1,.16),m,bevel=0)
        if name=='ForestTile':
            cone((0,0,.65),.08,.08,1,wood);cone((0,0,1.25),.42,0,1.2,grass, n=6)
        elif name=='MountainTile':cone((0,0,.62),.48,0,1.1,stone,n=4)
        elif name=='RoadTile':
            for y in [-.25,.15]:box((0,y,.18),(.75,.22,.04),cream,bevel=0)
    elif name in ['TownWall','CastleWall','CaveWall']:
        box((0,0,1),(2,.25,2),stone)
        if name=='TownWall':
            box((0,-.15,1.45),(.45,.04,.5),wood);box((0,-.18,1.45),(.32,.025,.37),water)
            box((0,0,2.03),(2.2,.5,.13),red)
        elif name=='CastleWall':
            for x in [-.75,-.25,.25,.75]:box((x,0,2.13),(.28,.28,.3),cream)
        else:
            for x in [-.7,.65]:cone((x,-.18,.45),.15,0,.65,stone,n=5)
    elif name in ['TownDoor','CastleGate','PortalArch','BronzeGate','SilverGate','StarGate']:
        m=brass if name in ['BronzeGate','StarGate'] else white if name=='SilverGate' else wood if name=='TownDoor' else stone
        for x in [-.55,.55]:box((x,0,.9),(.18,.28,1.8),m)
        box((0,0,1.8),(1.28,.28,.16),m)
        if name.endswith('Gate') and name!='CastleGate':
            for x in [-.35,-.12,.12,.35]:box((x,0,.87),(.04,.1,1.6),m)
            box((0,-.09,.87),(.18,.05,.16),brass)
        if name=='PortalArch':
            for x in [-.5,0,.5]:cone((x,0,1.98),.08,0,.2,water,n=4)
    elif name=='ShopCounter':box((0,0,.45),(1.2,.55,.8),wood);box((0,0,.9),(1.3,.65,.1),cream)
    elif name=='InnBed':
        box((0,0,.30),(.7,1.2,.4),wood);box((0,0,.54),(.65,1.1,.12),cream);box((0,-.35,.65),(.55,.28,.14),white)
        box((0,.58,.70),(.75,.08,.7),wood)
    elif name=='SmithAnvil':box((0,0,.25),(.6,.5,.5),wood);box((0,0,.63),(.6,.38,.25),stone);box((0,0,.79),(.82,.40,.08),white)
    elif name=='Throne':
        box((0,0,.38),(.6,.55,.12),red);box((0,.24,.9),(.6,.12,1.2),red)
        for x in [-.27,.27]:box((x,0,.61),(.10,.55,.55),brass)
        cone((0,.23,1.6),.10,0,.22,brass,n=4)
    elif name=='StairsDown':
        for k in range(5):box((0,-.4+k*.2,.1+k*.1),(1,.2,.2+k*.2),stone,bevel=0)
    elif name=='KeyChest':
        box((0,0,.32),(.6,.42,.5),wood);box((0,0,.59),(.64,.46,.08),brass)
        box((0,-.23,.44),(.10,.04,.15),brass)
    elif name=='StagePlatform':
        box((0,0,.23),(4,3,.46),wood);box((0,1.3,1.1),(4,.13,1.6),red)
        for x in [-1.6,1.6]:box((x,1.1,.85),(.3,.3,1.6),brass)
    elif name=='DragonEggNest':
        ring((0,0,.12),.45,.09,wood);box((0,0,.08),(.7,.7,.12),sand)
    elif name in ['DragonEggIntact','DragonEggCracked']:
        ball((0,0,.46),(.28,.28,.43),cream,'spine')
        for x,y,z in [(-.18,-.18,.5),(.18,-.18,.35),(0,.20,.60)]:box((x,y,z),(.08,.05,.09),water)
        if name=='DragonEggCracked':
            for x,z in [(-.16,.55),(-.05,.62),(.06,.52),(.16,.61)]:box((x,-.27,z),(.035,.025,.13),ink,bevel=0)
    bpy.ops.object.select_all(action='DESELECT')
    for o in parts:o.select_set(True)
    bpy.context.view_layer.objects.active=parts[0];bpy.ops.object.join();o=bpy.context.object;o.name=('Item_Portal_' if name.startswith('DragonEgg') and name!='DragonEggNest' else 'Prop_Portal_')+name
    bpy.context.scene.cursor.location=(0,0,0);bpy.ops.object.origin_set(type='ORIGIN_CURSOR');path=OUT/(o.name+'.glb');bpy.ops.export_scene.gltf(filepath=str(path),export_format='GLB',use_selection=True)
    tri=sum(len(p.vertices)-2 for p in o.data.polygons);radius=math.ceil(max(Vector(c).length for c in o.bound_box)*100)
    records.append(dict(id=o.name,role=role,file=path.name,triangles=tri,rig='static',bones=0,radius_cm=radius,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),role_count=0))
    o.location=((i%5)*4,(i//5)*4,0);label(name,i,5,4)
finish_scene(records,5,4,'portal-environment',[])
