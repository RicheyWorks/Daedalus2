"""One isolated Mine import; injected config/policy, no startup side effects."""
import copy,hashlib,json
from pathlib import Path
import unreal

done=False
errors=[]
paths=[]
source_proof=None
source_qualification=None
container=None
params=None
pipeline=None
observer=None
source_data=None
asset=None

def write(name,value):
 raw=json.dumps(value,indent=2,allow_nan=False).encode()
 if len(raw)>524288:raise RuntimeError('Mine receipt cap')
 with (Path(config['output'])/name).open('xb') as stream:stream.write(raw)

def source_equal():
 raw=Path(config['source']).read_bytes()
 if len(raw)!=212424 or hashlib.sha256(raw).hexdigest()!=policy.SOURCE_SHA:raise RuntimeError('Exact copied source changed')

@unreal.uclass()
class DaedalusFreshMineObserverV1(unreal.InterchangePythonPipelineBase):
 @unreal.ufunction(override=True)
 def scripted_execute_pipeline(self,base_node_container,source_datas,content_base_path):
  global source_proof,source_qualification,container
  container=base_node_container
  try:
   source_equal()
   if len(source_datas)!=1 or Path(source_datas[0].get_filename()).resolve()!=Path(config['source']).resolve():raise RuntimeError('Exact source-data identity differs')
   if content_base_path.rstrip('/')!=config['destination']:raise RuntimeError('Private destination differs')
   uids=list(container.get_nodes(unreal.InterchangeFactoryBaseNode))
   if not 2<=len(uids)<=64:raise RuntimeError('Factory inventory outside bound')
   root=container.get_node(policy.UID)
   if not isinstance(root,unreal.InterchangeAnimSequenceFactoryNode) or not root.is_enabled():raise RuntimeError('Exact Mine factory absent/disabled')
   # No Skeleton curve metadata writes; only the selected fresh clip is created.
   root.set_custom_add_curve_metadata_to_skeleton(False)
   disabled=[]
   for uid in uids:
    if uid not in (policy.UID,'CommonPipelineDataFactoryNode'):
     node=container.get_node(uid);node.set_enabled(False)
     if node.is_enabled():raise RuntimeError('Non-Mine factory remains enabled')
     disabled.append(uid)
   write('isolation.json',{'enabled_asset_factory':policy.UID,'disabled_factories':disabled,'replace_existing':False,'skeleton_path':policy.SKELETON})
   write('source-proof-intent.json',{'stage':'after_generic_before_factories','container':container.get_path_name(),'pid':config['pid']})
   text=unreal.DaedalusProspectorMineReadLibrary.read_fresh_mine_source(container)
   write('source-proof-raw.json',{'text':text,'utf8_sha256':hashlib.sha256(text.encode()).hexdigest()})
   source_proof=json.loads(text)
   source_qualification=policy.qualify_source(source_proof,expected_pid=config['pid'])
   write('source-qualification.json',source_qualification)
   # Explicit incompatible-hierarchy counterexample runs BEFORE asset factories.
   bad=copy.deepcopy(source_proof);bad['source_oracle']['bone_parents']['foot_L']='spine'
   try:policy.qualify_source(bad,expected_pid=config['pid'])
   except policy.Refused as error:write('synthetic-incompatible-skeleton-refusal.json',{'kind':'synthetic_mutation_of_actual_proof','reason':str(error),'asset_factory_started':False})
   else:raise RuntimeError('Incompatible hierarchy was admitted')
   source_equal()
  except Exception as error:
   errors.append('pre_factory: '+str(error))
   for uid in base_node_container.get_nodes(unreal.InterchangeFactoryBaseNode):base_node_container.get_node(uid).set_enabled(False)
   write('pre-factory-refused.json',{'error':str(error),'all_asset_factories_disabled':True})

 @unreal.ufunction(override=True)
 def scripted_execute_post_import_pipeline(self,base_node_container,factory_node_key,created_asset,is_reimport):
  try:
   if base_node_container!=container or factory_node_key!=policy.UID or created_asset.get_path_name()!=policy.ASSET or is_reimport:raise RuntimeError('Fresh post-import identity differs')
   root=base_node_container.get_node(policy.UID);common=base_node_container.get_node('CommonPipelineDataFactoryNode')
   profile=source_proof['live_profile']
   observed={'sample_rate':root.get_custom_import_bone_tracks_sample_rate(),'range_start':root.get_custom_import_bone_tracks_range_start(),'range_stop':root.get_custom_import_bone_tracks_range_stop(),'bake_meshes':common.get_bake_meshes()}
   if any(observed[key]!=profile[key] for key in observed):raise RuntimeError('Final same-job profile changed')
   write('post-import-profile.json',observed)
  except Exception as error:errors.append('post_import: '+str(error));write('post-import-error.json',{'error':str(error)})

def on_done(objects):
 global done,paths,asset
 paths=[x.get_path_name() for x in objects]
 try:
  if errors:raise RuntimeError('Earlier pipeline refusal: '+str(errors))
  if paths!=[policy.ASSET] or source_proof is None:raise RuntimeError('Exact one-Mine completion required')
  asset=objects[0]
  write('completed-native-intent.json',{'path':policy.ASSET,'reader':'ReadFreshMineClip'})
  current=json.loads(unreal.DaedalusProspectorMineReadLibrary.read_fresh_mine_clip(policy.ASSET))
  write('completed-native.json',current)
  decision=policy.qualify_clip(source_proof,current,expected_pid=config['pid'],expected_source_path=config['source'])
  write('completed-decision.json',decision);source_equal()
 except Exception as error:errors.append('completion: '+str(error))
 done=True;write('import-terminal.json',{'done':True,'paths':paths,'errors':errors,'fresh_only':True})
