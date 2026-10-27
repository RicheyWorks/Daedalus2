"""Decode captured forearm channels; no engine calls, writes or admission rule.

UE's AnimationSequencerDataModel stores constant controls as explicit channel
defaults, not legacy BoneAnimationTracks. The model rebuilds quaternion controls
with FQuat::MakeFromEuler (X=roll,Y=pitch,Z=yaw in degrees). Decoding those stored
values is distinct from executing its FK rig to obtain a Source pose.
"""
import math

class Refused(ValueError):
 pass

def need(ok,message):
 if not ok:raise Refused(message)

def finite(value):
 need(type(value) in (int,float) and math.isfinite(value),'finite scalar required')
 return value

def quaternion_from_euler_degrees(euler):
 need(type(euler) is list and len(euler)==3,'three Euler components required')
 roll,pitch,yaw=[math.radians(finite(v))/2 for v in euler]
 sr,cr=math.sin(roll),math.cos(roll);sp,cp=math.sin(pitch),math.cos(pitch);sy,cy=math.sin(yaw),math.cos(yaw)
 return [cr*sp*sy-sr*cp*cy,-cr*sp*cy-sr*cp*sy,cr*cp*sy-sr*sp*cy,cr*cp*cy+sr*sp*sy]

def decode_forearm_channels(channels,bone,frame):
 need(bone in ('forearm_L','forearm_R'),'closed forearm name required')
 need(type(frame) is int and frame in (0,24),'exact frame0or24 required')
 need(type(channels) is list and len(channels)==18,'exact18 captured channels required')
 prefix=bone.casefold()+'_control.';values={}
 for row in channels:
  name=row.get('name');need(type(name) is str,'explicit channel name required')
  if not name.casefold().startswith(prefix):continue
  component=name[len(prefix):]
  need(component not in values,'duplicate component refused')
  need(row.get('class')=='/Script/SequencerScripting.MovieSceneScriptingFloatChannel','actual float channel required')
  count=row.get('key_count');need(type(count) is int and 0<=count<=64,'bounded key count required')
  keys=row.get('keys');need(type(keys) is list,'captured key list required')
  if count==0:
   need(keys==[] and row.get('stored_default_present') is True,'explicit stored default required; no identity fallback')
   result=finite(row.get('stored_default'))
  else:
   found=[k for k in keys if type(k.get('frame')) is int and k['frame']==frame and type(k.get('sub_frame')) in (int,float) and k['sub_frame']==0]
   need(len(found)==1,'one exact requested key required; no interpolation guess')
   result=finite(found[0].get('value'))
  values[component]=result
 need(set(values)=={kind+'.'+axis for kind in ('Location','Rotation','Scale') for axis in 'XYZ'},'complete nine components required')
 return {'translation_cm':[values['Location.'+axis] for axis in 'XYZ'],
         'rotation_xyzw':quaternion_from_euler_degrees([values['Rotation.'+axis] for axis in 'XYZ']),
         'scale':[values['Scale.'+axis] for axis in 'XYZ']}
