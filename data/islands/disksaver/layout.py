import sys, json
from unittest.mock import MagicMock
class V:
    def __init__(s,x=0,y=0,z=0): s.x,s.y,s.z=x,y,z
    def __add__(s,o): return V(s.x+o.x,s.y+o.y,s.z+o.z)
u=MagicMock(); u.Vector=V; sys.modules['unreal']=u
pts=[]
u.StaticMesh=MagicMock; u.EditorAssetLibrary.list_assets.side_effect=lambda d,*a: [d+"/"+d.rstrip("/").split("/")[-1]]
def _la(p):
    m=MagicMock(); m.get_name.return_value=str(p).split("/")[-1].split(".")[0]; return m
u.load_asset.side_effect=_la
L=MagicMock(); L.get_path_name.return_value="/Game/DiskSaver/Maps/Island_DiskSaver"; u.EditorLevelUtils.get_levels.return_value=[L]
eas=MagicMock()
def spawn(sm,loc,rot):
    a=MagicMock(); a._loc=loc
    def lab(l): pts.append((str(l),loc.x-4000000,loc.y-4000000))
    a.set_actor_label.side_effect=lab; return a
eas.spawn_actor_from_object.side_effect=spawn
eas.get_all_level_actors.return_value=[]
u.get_editor_subsystem.return_value=eas
eas.is_in_play_in_editor.return_value=False
eas.get_editor_world.return_value.get_path_name.return_value="/Game/Daedalus/DaedalusWorld"
import builtins,io
_o=builtins.open
builtins.open=lambda p,*a,**k: io.StringIO('') if str(p).startswith('C:') else _o(p,*a,**k)
src=_o('ds_island_ue.py').read()
try: exec(src,{})
except SystemExit as e: print("exit",e)
except Exception as e: print("err",type(e).__name__,e)
json.dump(pts,_o('layout.json','w')); print(len(pts))
