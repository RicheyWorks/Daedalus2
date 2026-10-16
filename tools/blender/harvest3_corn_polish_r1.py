"""Source-only successor for one pinned Harvest3 decorative corn mesh.

Pure functions inspect only the named original and prepare deterministic geometry.
build() populates a caller-owned new scene; it never resets, saves, exports,
renders, launches a process, contacts an editor or changes a world binding.
"""
import hashlib
import json
import math
from pathlib import Path
import struct

TARGET = "Octet_Harvest_3_Plot0_Meadow_Crop_corn"
ASSET = "Prop_Harvest3_Corn_Polish_R1"
SOURCE_SHA = "12eb0bcfb57e3070520328c236debc8de30461b5e4b48164ddb640b6b292d140"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def bounds(points):
    return [[min(p[k] for p in points) for k in range(3)],
            [max(p[k] for p in points) for k in range(3)]]


def inspect_original(path):
    """Read only target node492/mesh109 data; never use the unrelated node109."""
    raw = Path(path).read_bytes()
    require(len(raw) == 2212076 and hashlib.sha256(raw).hexdigest() == SOURCE_SHA, "original GLB pin changed")
    require(struct.unpack_from("<4sII", raw) == (b"glTF",2,len(raw)), "invalid GLB header")
    size, kind = struct.unpack_from("<I4s", raw, 12)
    require(kind == b"JSON", "missing JSON chunk")
    doc = json.loads(raw[20:20+size])
    offset = 20+size
    length, kind = struct.unpack_from("<I4s",raw,offset)
    require(kind == b"BIN\0" and offset+8+length == len(raw), "missing embedded BIN")
    binary = raw[offset+8:]
    matches = [(i,n) for i,n in enumerate(doc["nodes"]) if n.get("name") == TARGET]
    require(len(matches) == 1, "corn name must resolve uniquely")
    index, node = matches[0]
    require(index == 492 and node["mesh"] == 109 and set(node) == {"name","mesh"}, "source identity/transform differs")
    require(not any(index in n.get("children",[]) for n in doc["nodes"]), "unexpected source parent transform")
    mesh = doc["meshes"][node["mesh"]]
    require(mesh["name"] == TARGET and len(mesh["primitives"]) == 1, "source primitive contract changed")
    primitive = mesh["primitives"][0]

    def decode(accessor_index):
        a = doc["accessors"][accessor_index]
        v = doc["bufferViews"][a["bufferView"]]
        require(a["componentType"] in (5123,5126) and a["type"] in ("SCALAR","VEC3")
                and 0 < a["count"] <= 9000 and not a.get("sparse"), "unsupported target accessor")
        width = {"SCALAR":1,"VEC3":3}[a["type"]]
        fmt = "<"+({5123:"H",5126:"f"}[a["componentType"]]*width)
        step = struct.calcsize(fmt)
        stride = v.get("byteStride",step)
        start = v.get("byteOffset",0)+a.get("byteOffset",0)
        require(v.get("buffer",0) == 0 and stride >= step and start >= 0
                and start+(a["count"]-1)*stride+step <= len(binary), "target accessor exceeds BIN")
        values = [struct.unpack_from(fmt,binary,start+i*stride) for i in range(a["count"])]
        require(all(math.isfinite(x) for row in values for x in row), "nonfinite source value")
        return values

    positions = decode(primitive["attributes"]["POSITION"])
    normals = decode(primitive["attributes"]["NORMAL"])
    indices = [r[0] for r in decode(primitive["indices"])]
    require(len(positions) == len(normals) == 360 and len(indices) == 1944
            and all(0 <= i < len(positions) for i in indices), "source topology changed")
    # glTF Y-up -> authored Blender Z-up. Positions already bake plot placement.
    points = [(x,-z,y) for x,y,z in positions]
    normals = [(x,-z,y) for x,y,z in normals]
    low, high = bounds(points)
    anchor = [(low[0]+high[0])/2,(low[1]+high[1])/2,low[2]]
    adjacency = {i:set() for i in range(len(points))}
    faces = list(zip(indices[::3],indices[1::3],indices[2::3]))
    for face in faces:
        for i in face:
            adjacency[i].update(face)
    components, seen = [], set()
    for first in adjacency:
        if first in seen:
            continue
        todo, group = [first], set()
        while todo:
            i = todo.pop()
            if i not in group:
                group.add(i)
                todo.extend(adjacency[i]-group)
        seen.update(group)
        lo,hi = bounds([points[i] for i in group])
        components.append({"vertices":len(group),"centre_m":[(lo[0]+hi[0])/2-anchor[0],(lo[1]+hi[1])/2-anchor[1],lo[2]-anchor[2]]})
    require(len(components) == 18 and all(c["vertices"] == 20 for c in components), "source plant layout changed")
    centres = sorted((c["centre_m"] for c in components),key=lambda p:(p[1],p[0]))
    return {"target_name":TARGET,"node_index":index,"mesh_index":109,"node_transform":"identity; plot placement baked in POSITION",
            "units":"metres","source_anchor_blender_m":anchor,"source_bounds_blender_m":[low,high],
            "height_m":high[2]-low[2],"plant_centres_m":centres,"plant_count":18,"triangles":648,
            "material":doc["materials"][primitive["material"]],
            "vertices_rebased_m":[tuple(p[k]-anchor[k] for k in range(3)) for p in points],
            "normals_z_up":normals,"faces":faces}


def load_recipe(path):
    r = json.loads(Path(path).read_text(encoding="utf-8"))
    require(r.get("schema") == "daedalus.harvest3-corn-polish.recipe.v1" and r["asset_id"] == ASSET, "unknown recipe")
    require(r["world_binding"] is None and r["units"] == "metres" and len(r["plant_centres_m"]) == 18, "invalid layout binding")
    require(type(r["height_m"]) in (int,float) and 1.39 < r["height_m"] < 1.41, "height must preserve original")
    require(set(r["materials"]) == {"stalk","leaf","cob"}, "require exactly three material slots")
    for material in r["materials"].values():
        color=material.get("base_color_factor")
        require(isinstance(color,list) and len(color)==4 and all(type(v) in (int,float) and math.isfinite(v) and 0<=v<=1 for v in color)
                and color[3]==1 and type(material.get("roughness")) in (int,float)
                and math.isfinite(material["roughness"]) and 0<=material["roughness"]<=1,"invalid opaque farm palette")
    require(all(len(p)==3 and all(type(v) in (int,float) and math.isfinite(v) for v in p)
                for p in r["plant_centres_m"]), "invalid plant centre")
    return r


def geometry(r):
    """18 preserved source centres, each with stalk, curved leaves, ear/husks/tassel."""
    parts=[]
    h=r["height_m"]

    def add(name,role,material,vertices,faces,plant):
        parts.append({"name":name,"role":role,"material":material,"plant":plant,"vertices":vertices,"faces":faces})

    def tube(name,role,material,rings,plant):
        vertices=[(cx+radius*math.cos(i*math.tau/6),cy+radius*math.sin(i*math.tau/6),z)
                  for cx,cy,z,radius in rings for i in range(6)]
        faces=[]
        for ring in range(len(rings)-1):
            for i in range(6):
                a,b=ring*6+i,ring*6+(i+1)%6;c,d=b+6,a+6
                faces.extend(((a,b,c),(a,c,d)))
        for i in range(1,5):
            faces.append((0,i+1,i));base=(len(rings)-1)*6;faces.append((base,base+i,base+i+1))
        add(name,role,material,vertices,faces,plant)

    def blade(name,role,x,y,z,angle,length,rise,plant):
        profile=[(0,-.012*h,0),(.48*length,-.068*h,rise),(length,0,.35*rise),
                 (.48*length,.068*h,rise),(0,.012*h,0)]
        cs,sn=math.cos(angle),math.sin(angle)
        vertices=[(x+u*cs-v*sn,y+u*sn+v*cs,z+w-thickness)
                  for thickness in (0,.008*h) for u,v,w in profile]
        top=[(0,1,4),(1,3,4),(1,2,3)]
        faces=top+[tuple(i+5 for i in reversed(t)) for t in top]
        for i in range(5):
            j=(i+1)%5;faces.extend(((i,i+5,j+5),(i,j+5,j)))
        add(name,role,"leaf",vertices,faces,plant)

    for plant,(x,y,base) in enumerate(r["plant_centres_m"]):
        start=len(parts)
        tube(f"Stalk_{plant}","stalk","stalk",[(x,y,base,.025*h),(x,y,base+.82*h,.016*h)],plant)
        phase=(int(round(abs(x)))%3)*.08
        for i,height in enumerate((.20,.38,.56)):
            blade(f"Leaf_{plant}_{i}","leaf",x,y,base+height*h,phase+i*math.tau/3,.35*h,.12*h,plant)
        phi=math.pi/2+phase
        rings=[]
        for t,radius in ((0,.018),(.5,.054),(1,.013)):
            offset=(.025+.09*t)*h
            rings.append((x+offset*math.cos(phi),y+offset*math.sin(phi),base+(.46+.23*t)*h,radius*h))
        tube(f"Ear_{plant}","ear","cob",rings,plant)
        for i,delta in enumerate((-.30,.30)):
            blade(f"Husk_{plant}_{i}","husk",x,y,base+.45*h,phi+delta,.17*h,.07*h,plant)
        for i in range(3):
            angle=phase+i*math.tau/3
            vertices=[(x-.008*h,y,base+.81*h),(x+.008*h,y,base+.81*h),
                      (x,y+.011*h,base+.81*h),(x+.07*h*math.cos(angle),y+.07*h*math.sin(angle),base+h)]
            add(f"Tassel_{plant}_{i}","tassel","cob",vertices,[(0,2,1),(0,1,3),(1,2,3),(2,0,3)],plant)
        # Mirror paired plants about the ORIGINAL layout centre; preserve its
        # bottom-centred pivot without translating any source planting position.
        sx,sy=(-1 if x<0 else 1),(-1 if y<0 else 1)
        for p in parts[start:]:
            p["vertices"]=[(x+sx*(a-x),y+sy*(b-y),z) for a,b,z in p["vertices"]]
            if sx*sy<0:
                p["faces"]=[tuple(reversed(f)) for f in p["faces"]]
    return parts


def validate_geometry(r,parts):
    require(len({p["name"] for p in parts}) == len(parts) and len(parts)>0,"duplicate/empty geometry")
    triangles=0
    for p in parts:
        require(p["material"] in r["materials"] and all(math.isfinite(v) for xyz in p["vertices"] for v in xyz),"invalid material/vertex")
        for face in p["faces"]:
            require(len(face)==3 and all(type(i) is int and 0<=i<len(p["vertices"]) for i in face),"invalid triangle index")
            a,b,c=(p["vertices"][i] for i in face);u=[b[k]-a[k] for k in range(3)];v=[c[k]-a[k] for k in range(3)]
            cross=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]]
            require(sum(x*x for x in cross)>1e-16,"degenerate triangle")
            triangles+=1
    lo,hi=bounds([xyz for p in parts for xyz in p["vertices"]])
    require(0<=lo[2]<1e-8 and abs(hi[2]-r["height_m"])<1e-8,"original base/height not preserved")
    require(type(r["budgets"]["max_triangles"]) is int and 0<r["budgets"]["max_triangles"]<=3000
            and triangles<=r["budgets"]["max_triangles"] and len({p["material"] for p in parts})<=3,"prop budget exceeded")
    require(abs(lo[0]+hi[0])<1e-8 and abs(lo[1]+hi[1])<1e-8,"bottom-centred pivot drift")
    source_lo,source_hi=r["source_bounds_blender_m"];anchor=r["source_anchor_blender_m"]
    require(all(source_lo[k]-1e-8<=lo[k]+anchor[k] and hi[k]+anchor[k]<=source_hi[k]+1e-8 for k in range(3)),"source envelope exceeded")
    for plant in range(18):
        roles=[p["role"] for p in parts if p["plant"]==plant]
        require(roles.count("stalk")==1 and roles.count("leaf")==3 and roles.count("ear")==1
                and roles.count("husk")==2 and roles.count("tassel")==3,"incomplete corn silhouette")
    return {"plant_count":18,"triangles":triangles,"material_slots":3,"export_meshes":1,
            "bounds_m":[lo,hi],"world_binding":None,"visual_accepted":False,"native_accepted":False}


def build(scene,r,variant="after",original=None):
    """Future preserved-session route supplies a NEW scene; no scene operators."""
    import bpy
    require(variant in ("before","after"),"unknown matched-view variant")
    require(scene.name.startswith(r["asset_id"]),"caller must provide named isolated scene")
    if variant=="before":
        require(original is not None and original["target_name"]==TARGET,"pinned original inspection required")
        vertices,faces=original["vertices_rebased_m"],original["faces"]
        indices=[0]*len(faces);materials={"leaf":r["materials"]["leaf"]};name=r["future_selected_allowlist"]["before"][0]
    else:
        parts=geometry(r);validate_geometry(r,parts);vertices,faces,indices=[],[],[]
        materials=r["materials"]
        for p in parts:
            offset=len(vertices);vertices.extend(p["vertices"]);faces.extend(tuple(i+offset for i in f) for f in p["faces"])
            indices.extend([list(materials).index(p["material"])]*len(p["faces"]))
        name=ASSET
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(vertices,[],faces);mesh.update()
    obj=bpy.data.objects.new(name,mesh);collection=bpy.data.collections.new(name);scene.collection.children.link(collection);collection.objects.link(obj)
    for key,values in materials.items():
        mat=bpy.data.materials.new("H3C_R1_"+variant.upper()+"_"+key);mat.diffuse_color=values["base_color_factor"];mat.use_nodes=True
        mat.use_backface_culling=False
        bsdf=mat.node_tree.nodes.get("Principled BSDF");bsdf.inputs["Base Color"].default_value=values["base_color_factor"]
        bsdf.inputs["Roughness"].default_value=values["roughness"];bsdf.inputs["Metallic"].default_value=0
        mesh.materials.append(mat)
    for polygon,index in zip(mesh.polygons,indices):
        polygon.material_index=index
    if variant=="before":
        setter=getattr(mesh,"normals_split_custom_set_from_vertices",None)
        require(callable(setter),"installed API must support exact retained BEFORE normals")
        for polygon in mesh.polygons:polygon.use_smooth=True
        setter(original["normals_z_up"])
    obj["source_target"]=TARGET;obj["units"]="metres";obj["source_node_index"]=492;obj["source_mesh_index"]=109
    obj["world_binding"]="UNBOUND";obj["provenance_anchor_m"]=r["source_anchor_blender_m"]
    obj["material_role_order"]=json.dumps(list(materials))
    return [obj]
