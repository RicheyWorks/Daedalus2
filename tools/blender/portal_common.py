"""Shared original Portal art helpers. Reuses the owned, verified cast primitive/rig code."""
import bpy,sys,json,math,hashlib
from pathlib import Path
from mathutils import Vector
exec(compile(Path(__file__).with_name('labyrinth_cast.py').read_text().split('records=[]')[0],__file__,'exec'))
ink=mat('Portal ink',(.025,.035,.09)); cream=mat('Portal cream',(.83,.72,.49)); brass=mat('Portal brass',(.72,.46,.08),.3)
face=mat('Portal warm skin',(.58,.31,.17)); white=mat('Portal white',(.87,.9,.93))

def animate_humanoid(rig):
    rig.animation_data_clear()
    for clip,length in [('Idle',48),('Walk',24),('Attack',24),('Hurt',24)]:
        rig.animation_data_create();act=bpy.data.actions.new(clip);rig.animation_data.action=act
        frames=range(1,length+2,6) if clip=='Walk' else range(1,length+2,3)
        for f in frames:
            phase=(f-1)/length*2*math.pi
            for p in rig.pose.bones:p.rotation_euler=(0,0,0);p.location=(0,0,0)
            rig.pose.bones['spine'].rotation_euler.x=.015*math.sin(phase)
            if clip=='Walk':
                for side,sign in [('L',1),('R',-1)]:
                    rig.pose.bones['thigh.'+side].rotation_euler.x=.30*math.sin(phase)*sign
                    rig.pose.bones['arm.'+side].rotation_euler.x=-.24*math.sin(phase)*sign
            elif clip=='Attack':
                rig.pose.bones['arm.R'].rotation_euler.x=-.9*(1-math.cos(phase))/2
                rig.pose.bones['spine'].rotation_euler.z=.16*math.sin(phase)
            elif clip=='Hurt':
                rig.pose.bones['spine'].rotation_euler.x=.2*(1-math.cos(phase))/2
                rig.pose.bones['head'].rotation_euler.x=-.10*(1-math.cos(phase))/2
            for p in rig.pose.bones:p.keyframe_insert(data_path='rotation_euler',frame=f);p.keyframe_insert(data_path='location',frame=f)
        if clip=='Walk':
            for curve in act.fcurves:
                for key in curve.keyframe_points:key.interpolation='CONSTANT'
        tr=rig.animation_data.nla_tracks.new();tr.name=clip;tr.strips.new(clip,1,act);rig.animation_data.action=None
    for tr in rig.animation_data.nla_tracks:tr.mute=True
    for p in rig.pose.bones:p.rotation_euler=(0,0,0);p.location=(0,0,0)

def export_character(mesh,rig,role,rig_name,extra=None):
    unknown={group.name for group in mesh.vertex_groups}-set(rig.data.bones.keys())
    if unknown:raise ValueError('Vertex weights reference missing rig bones: '+str(unknown))
    bpy.ops.object.select_all(action='DESELECT');mesh.select_set(True);rig.select_set(True)
    for tr in rig.animation_data.nla_tracks:tr.mute=False
    path=OUT/(mesh.name+'.glb');bpy.ops.export_scene.gltf(filepath=str(path),export_format='GLB',use_selection=True,export_animations=True,export_animation_mode='NLA_TRACKS')
    for tr in rig.animation_data.nla_tracks:tr.mute=True
    for p in rig.pose.bones:p.rotation_euler=(0,0,0);p.location=(0,0,0)
    tri=sum(len(p.vertices)-2 for p in mesh.data.polygons);radius=math.ceil(max(Vector(c).length for c in mesh.bound_box)*100)
    return dict(id=mesh.name,role=role,file=path.name,triangles=tri,bones=len(rig.data.bones),rig=rig_name,radius_cm=radius,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),**(extra or {}))

def finish_scene(records,columns,spacing,filename,clips):
    rows=math.ceil(len(records)/columns);cx=(columns-1)*spacing/2;cy=(rows-1)*spacing/2
    bpy.ops.mesh.primitive_plane_add(size=250,location=(0,0,-.001));bpy.context.object.data.materials.append(ink)
    bpy.ops.object.camera_add(location=(cx+12,cy-18,22));c=bpy.context.object;c.rotation_euler=(Vector((cx,cy,.8))-c.location).to_track_quat('-Z','Y').to_euler();c.data.type='ORTHO';c.data.ortho_scale=max(columns*spacing,rows*spacing)*1.5+3;bpy.context.scene.camera=c
    if len(records)==1:
        c.location=(3,-6,3.2);c.rotation_euler=(Vector((0,0,1.0))-c.location).to_track_quat('-Z','Y').to_euler();c.data.ortho_scale=2.8
    for loc in [(cx-3,cy-8,15),(cx+8,cy+8,16)]:
        bpy.ops.object.light_add(type='AREA',location=loc);l=bpy.context.object;l.data.energy=5500;l.data.size=12;l.rotation_euler=(Vector((cx,cy,0))-l.location).to_track_quat('-Z','Y').to_euler()
    s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.device='CPU';s.cycles.samples=24;s.render.threads_mode='FIXED';s.render.threads=4;s.render.fps=24;s.render.resolution_x=1900;s.render.resolution_y=1500;s.render.resolution_percentage=100;s.world.color=(.18,.18,.18);s.render.filepath=str(OUT/'contact-sheet.png')
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT/(filename+'.blend')));bpy.ops.render.render(write_still=True)
    (OUT/'manifest.json').write_text(json.dumps({'assets':records,'clips':clips,'status':'art prototype; native integration pending','realm':'Portal'},indent=2))
    (OUT/'portal.bba').write_text('BBA 1\n'+''.join(f"asset {r['id']} lod0 {r['triangles']} lod1 - radius {r['radius_cm']} switch {max(500,20*r['radius_cm'])}\n" for r in records))

def label(text,index,columns,spacing):
    bpy.ops.object.text_add(location=((index%columns)*spacing-.65,(index//columns)*spacing-.65,.01));t=bpy.context.object;t.data.body=text;t.data.size=.14 if spacing<3 else .24;t.data.materials.append(cream)
