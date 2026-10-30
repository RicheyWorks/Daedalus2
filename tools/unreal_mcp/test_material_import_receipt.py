"""Synthetic structural tests; none are evidence of actual Unreal execution."""
import copy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import tempfile
import struct
import unittest
from unittest.mock import patch
import uuid

from tools.unreal_mcp import material_import_receipt as r


def identity(path, cls, owner):
    return {"path":path,"class":cls,"owner":owner}


def masks(values):
    return dict(zip(("mask","r","g","b","a"), values))


def fixture(root):
    """Small complete synthetic roster. Native acceptance uses the actual roster."""
    path=root+"/"+r.NAME+"."+r.NAME
    source={"path":"unused-in-synthetic-test","bytes":18576,"sha256":r.SOURCE_SHA}
    profile={"base_color":[0.32972902059555054,0.14799802005290985,0.04614884406328201,1],"metallic":0,"roughness":0.6000000238418579}
    policy={"schema":r.POLICY,"root":root,"asset":path,"source":source,"source_md5":"b2e8602b7de26ea154cf88bc839f94d1","profile":profile,
            "function_package":{},"versions":{"engine":"5.8.4-test","producer_sha256":"1"*64,"reader_sha256":"2"*64,"importer_files":[]}}
    policy["policy_id"]=r.sha(r.encode(policy))
    caller=path+":ActualCall"; roster=[]; bindings={}; factors={}; attrs={}; graph_connections={}; root_connections={}; factories={}; inputs={}
    for i,(lane,(output,role,out_index,kind)) in enumerate(r.LANES.items()):
        node_id=str(i+1)*32; node=r.FUNCTION+":"+role
        roster.append({"index":i,"input_name":role,"input_type":"FunctionInput_"+r.TYPES[kind],"input_type_value":kind,
                       "node":identity(node,"/Script/Engine.MaterialExpressionFunctionInput",r.FUNCTION),"node_guid":node_id,"caller_input_guid":node_id,"cached_pointer_equal":True})
        projection=masks(r.ZERO)
        bindings[lane]={"current_input_present":True,"uses_input_constant":False,"current_pointer_equal":True,"expression_path":caller,"output_index":out_index,
                        "selected_output_valid":True,"selected_output_name":output,"raw_masks":projection,"selected_output_masks":projection,"effective_masks":projection}
        leaf_path=path+":Created"+role; cls="MaterialExpression"+("Constant3Vector" if lane=="base_color" else "Constant")
        factor_masks=masks(r.RGB if lane=="base_color" else r.ZERO)
        factors[lane]={"roster_index":i,"input_node_guid":node_id,"caller_input_guid":node_id,"current_pointer_equal":True,
                       "connection":{"expression_present":True,"expression":identity(leaf_path,"/Script/Engine."+cls,path),"output_index":0,"selected_output_valid":True,
                                     "raw_masks":factor_masks,"selected_output_masks":factor_masks,"effective_masks":factor_masks},
                       "leaf":{"expression_path":leaf_path,"value_kind":"FLinearColor" if lane=="base_color" else "float32","value":profile[lane]}}
        attrs[lane]={"role":role,"kind":"LinearColor" if lane=="base_color" else "Float","value":profile[lane]}
        graph_connections[lane]={"uid":"source-function","output":output};root_connections[lane]={"uid":"factory-function","output":output}
        factories[lane]={"uid":"factory-"+role,"class":"/Script/InterchangeFactoryNodes.InterchangeMaterialExpressionFactoryNode","expression_class":cls,"expression_path":leaf_path}
        inputs[lane]={"uid":"factory-"+role,"output":""}
    current={"material":identity(path,"/Script/Engine.Material",path.split('.')[0]),"source_material_name":r.NAME,"two_sided":True,"blend_mode":"BLEND_Opaque","material_domain":"MD_Surface",
             "interface_context":{"interface_path":path,"exact_class":"/Script/Engine.Material","is_instance":False,"parent_chain":[]},
             "current_call":{"caller":identity(caller,"/Script/Engine.MaterialExpressionMaterialFunctionCall",path),"function":identity(r.FUNCTION,"/Script/Engine.MaterialFunction",r.FUNCTION.split('.')[0]),
                             "input_count":3,"input_roster_complete":True,"input_roster":roster,"property_bindings":bindings},"factors":factors}
    metadata={"asset_import_data":identity(path+":ImportData","/Script/InterchangeEngine.InterchangeAssetImportData",path),"source_filename":source['path'],
              "source":{k:source[k] for k in ('bytes','sha256')},"source_md5":policy['source_md5'],"root_uid":r.ROOT_UID,"factory_uid":r.ROOT_UID,
              "factory_class":"/Script/InterchangeFactoryNodes.InterchangeMaterialFactoryNode","factory_target_uids":["source-graph"],"factory_connections":root_connections}
    now=datetime.now(timezone.utc)
    native={"schema":r.NATIVE,"state":"complete","native_invoked":True,"errors":[],"engine_version":policy['versions']['engine'],"editor_pid":123,
            "capture_id":str(uuid.uuid4()),"project_path":r.PROJECT,"world_path":r.WORLD,
            "observed_at_utc":now.isoformat(),"dirty_before":[],"dirty_after":[],"current":current,"metadata":metadata,**{k:0 for k in r.EFFECTS}}
    live={"source_sha256":r.SOURCE_SHA,"root_uid":r.ROOT_UID,"container_path":"/Engine/Transient.ActualJob",
          "boundaries":[{"phase":phase,"container_path":"/Engine/Transient.ActualJob","asset_path":path,"is_reimport":False} for phase in ('post_factory','post_import')],
          "root_targets":["source-graph"],"root_connections":root_connections,
          "shader_graph":{"uid":"source-graph","class":"/Script/InterchangeNodes.InterchangeShaderGraphNode","label":r.NAME,"connections":graph_connections},
          "function_shader":{"uid":"source-function","class":"/Script/InterchangeNodes.InterchangeFunctionCallShaderNode","function_path":r.FUNCTION,"attributes":attrs},
          "factory_function":{"uid":"factory-function","class":"/Script/InterchangeFactoryNodes.InterchangeMaterialFunctionCallExpressionFactoryNode","expression_class":"MaterialExpressionMaterialFunctionCall","expression_path":caller,"inputs":inputs},
          "factor_factories":factories}
    body={"schema":r.SCHEMA,"policy_id":policy['policy_id'],"job_id":str(uuid.uuid4()),"import_started_utc":(now-timedelta(seconds=2)).isoformat(),"created_utc":now.isoformat(),
          "versions":policy['versions'],"live":live,"import_native":native,"reload_native":copy.deepcopy(native),"package":{},
          "preservation":{"before_sha256":"a"*64,"after_sha256":"a"*64,"normal_terminal":True,"dirty_after":[]},"outputs":[path],"fresh_import":True,"replace_existing":False}
    body['reload_native']['capture_id']=str(uuid.uuid4())
    return policy,body


class ReceiptTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.package=Path(self.temp.name)/'new.uasset';self.package.write_bytes(b'synthetic-package')
        self.policy,self.body=fixture(r.PREFIX+'ReceiptTest')
        self.body['package']=r.file_pin(self.package)
        # Only independent file/GLB policy setup is mocked. The changed receipt,
        # graph, GUID, masks, chain, package and current-witness logic runs real.
        self.addCleanup(patch.stopall)
        patch.object(r,'_same_file',lambda _:None).start()
        patch.object(r,'build_policy',return_value=self.policy).start()

    def consume(self,body=None,current=None,raw=None,anchor=None):
        raw=r.encode(self.body if body is None else body) if raw is None else raw
        if current is None:
            current=copy.deepcopy(self.body['reload_native']);current['capture_id']=str(uuid.uuid4());current['observed_at_utc']=datetime.now(timezone.utc).isoformat()
        return r.consume(self.policy,raw,expected_receipt_sha256=r.sha(raw) if anchor is None else anchor,
                         current_native_raw=r.encode(current),expected_editor_pid=123,package_path=self.package)

    def rejected(self,change):
        body=copy.deepcopy(self.body);change(body)
        self.assertFalse(self.consume(body)['receipt_accepted'])

    def test_valid_complete_structural_fixture(self):
        result=self.consume();self.assertTrue(result['receipt_accepted']);self.assertFalse(result['native_runtime_qualified']);self.assertFalse(result['historical_admission'])
    def test_external_hash_anchor_refuses_tampering(self):
        anchor=r.sha(r.encode(self.body));self.body['job_id']=str(uuid.uuid4());self.assertFalse(self.consume(anchor=anchor)['receipt_accepted'])
    def test_missing_receipt(self):self.assertFalse(self.consume(raw=b'')['receipt_accepted'])
    def test_duplicate_json(self):self.assertFalse(self.consume(raw=b'{"schema":1,"schema":2}')['receipt_accepted'])
    def test_unknown_schema(self):self.rejected(lambda b:b.update(schema='old'))
    def test_unknown_extra_receipt_key(self):self.rejected(lambda b:b.update(unsupported=True))
    def test_absent_job_container_identity(self):self.rejected(lambda b:b['live'].update(container_path=None))
    def test_unknown_engine(self):self.rejected(lambda b:b.update(versions={**b['versions'],'engine':'5.8.3'}))
    def test_changed_source_attribute(self):self.rejected(lambda b:b['live']['function_shader']['attributes']['metallic'].update(value=1))
    def test_wrong_source_hash(self):self.rejected(lambda b:b['live'].update(source_sha256='b'*64))
    def test_missing_boundary(self):self.rejected(lambda b:b['live']['boundaries'].pop())
    def test_mismatched_job_container(self):self.rejected(lambda b:b['live']['boundaries'][0].update(container_path='other'))
    def test_reimport_is_not_fresh(self):self.rejected(lambda b:b['live']['boundaries'][0].update(is_reimport=True))
    def test_duplicate_or_extra_outputs(self):self.rejected(lambda b:b['outputs'].append(b['outputs'][0]))
    def test_reference_to_other_material(self):self.rejected(lambda b:b['live']['factory_function'].update(expression_path='other'))
    def test_factor_uid_not_created_expression(self):self.rejected(lambda b:b['live']['factor_factories']['metallic'].update(expression_path='other'))
    def test_factor_chain_wrong_output(self):self.rejected(lambda b:b['live']['factory_function']['inputs']['metallic'].update(output='wrong'))
    def test_source_function_wrong_body(self):self.rejected(lambda b:b['live']['function_shader'].update(function_path='other'))
    def test_role_type_mismatch(self):self.rejected(lambda b:b['import_native']['current']['current_call']['input_roster'][0].update(input_type_value=0))
    def test_duplicate_roster_guid(self):self.rejected(lambda b:b['import_native']['current']['current_call']['input_roster'][1].update(node_guid='1'*32))
    def test_incomplete_roster(self):self.rejected(lambda b:b['import_native']['current']['current_call']['input_roster'].pop())
    def test_bad_effective_mask(self):self.rejected(lambda b:b['import_native']['current']['factors']['base_color']['connection']['effective_masks'].update(a=1))
    def test_invalid_selected_output(self):self.rejected(lambda b:b['import_native']['current']['factors']['metallic']['connection'].update(selected_output_valid=False))
    def test_parameter_fallback_refused(self):self.rejected(lambda b:b['import_native']['current']['factors']['metallic']['connection']['expression'].update(**{'class':'/Script/Engine.MaterialExpressionScalarParameter'}))
    def test_source_filename_mismatch(self):self.rejected(lambda b:b['import_native']['metadata'].update(source_filename='wrong'))
    def test_source_md5_mismatch(self):self.rejected(lambda b:b['import_native']['metadata'].update(source_md5='b'*32))
    def test_changed_reload_graph(self):self.rejected(lambda b:b['reload_native']['current']['factors']['roughness']['leaf'].update(value=0.5))
    def test_unknown_native_field_state(self):self.rejected(lambda b:b['reload_native'].update(state='held'))
    def test_native_error_refused(self):self.rejected(lambda b:b['reload_native']['errors'].append('failure'))
    def test_unexpected_dirty_package(self):self.rejected(lambda b:b['reload_native'].update(dirty_before=['other'],dirty_after=['other']))
    def test_reader_effect_refused(self):self.rejected(lambda b:b['reload_native'].update(compilations=1))
    def test_preservation_mismatch(self):self.rejected(lambda b:b['preservation'].update(after_sha256='b'*64))
    def test_bool_not_output_integer(self):self.rejected(lambda b:b['import_native']['current']['factors']['metallic']['connection'].update(output_index=False))
    def test_naive_time(self):self.rejected(lambda b:b.update(created_utc='2026-10-21T00:00:00'))
    def test_future_time(self):self.rejected(lambda b:b.update(created_utc=(datetime.now(timezone.utc)+timedelta(hours=1)).isoformat()))
    def test_stale_current_witness(self):
        current=copy.deepcopy(self.body['reload_native']);current['observed_at_utc']=(datetime.now(timezone.utc)-timedelta(seconds=301)).isoformat();self.assertFalse(self.consume(current=current)['receipt_accepted'])
    def test_replayed_reload_is_not_current(self):self.assertFalse(self.consume(current=self.body['reload_native'])['receipt_accepted'])
    def test_preseal_current_witness(self):
        current=copy.deepcopy(self.body['reload_native']);current['capture_id']=str(uuid.uuid4());current['observed_at_utc']=self.body['import_started_utc'];self.assertFalse(self.consume(current=current)['receipt_accepted'])
    def test_wrong_current_pid(self):
        current=copy.deepcopy(self.body['reload_native']);current['editor_pid']=456;self.assertFalse(self.consume(current=current)['receipt_accepted'])
    def test_current_graph_modified(self):
        current=copy.deepcopy(self.body['reload_native']);current['current']['factors']['roughness']['leaf']['value']=0.5;self.assertFalse(self.consume(current=current)['receipt_accepted'])
    def test_package_bytes_modified(self):
        self.package.write_bytes(b'tampered-package');self.assertFalse(self.consume()['receipt_accepted'])
    def test_nonfinite_or_oversize(self):
        self.assertFalse(self.consume(raw=b'{"x":NaN}')['receipt_accepted']);self.assertFalse(self.consume(raw=b' '* (r.LIMIT+1))['receipt_accepted'])


class RealFilePolicyTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);folder=Path(self.temp.name)
        self.source=folder/'source.glb';self.function=folder/'function.uasset';self.importer=folder/'importer.bin';self.package=folder/'new.uasset'
        self.function.write_bytes(b'function');self.importer.write_bytes(b'importer');self.package.write_bytes(b'new-package')
        _,model=fixture(r.PREFIX+'RealFiles')
        profile=model['import_native']['current']['factors']
        doc={'materials':[{'name':r.NAME,'doubleSided':True,'pbrMetallicRoughness':{'baseColorFactor':profile['base_color']['leaf']['value'],
              'metallicFactor':profile['metallic']['leaf']['value'],'roughnessFactor':profile['roughness']['leaf']['value']}}]}
        encoded=json.dumps(doc,separators=(',',':')).encode();encoded+=b' '*((-len(encoded))%4)
        binary=b'\0'*(18576-20-len(encoded)-8)
        raw=struct.pack('<4sIII4s',b'glTF',2,18576,len(encoded),b'JSON')+encoded+struct.pack('<I4s',len(binary),b'BIN\0')+binary
        self.source.write_bytes(raw)
        # A synthetic source hash replaces only the closed real-fixture pin so
        # real file/GLB derivation and tamper checks can run without shipping art.
        self.addCleanup(patch.stopall);patch.object(r,'SOURCE_SHA',r.sha(raw)).start()
        self.versions={'engine':'5.8.4-test','producer_sha256':'1'*64,'reader_sha256':'2'*64,'importer_files':[r.file_pin(self.importer)]}
        self.policy=r.build_policy(self.source,r.PREFIX+'RealFiles',self.versions,r.file_pin(self.function))

    def test_real_policy_derives_current_files(self):
        r._policy(self.policy);self.assertEqual(self.policy['source'],r.file_pin(self.source))
    def test_tampered_source(self):
        self.source.write_bytes(self.source.read_bytes()[:-1]+b'x')
        with self.assertRaises(r.Held):r._policy(self.policy)
    def test_tampered_importer(self):
        self.importer.write_bytes(b'changed')
        with self.assertRaises(r.Held):r._policy(self.policy)
    def test_tampered_function_package(self):
        self.function.write_bytes(b'changed')
        with self.assertRaises(r.Held):r._policy(self.policy)
    def test_forged_profile_with_recomputed_policy_hash(self):
        value=copy.deepcopy(self.policy);value['profile']['roughness']=1;value['policy_id']=r.sha(r.encode({k:v for k,v in value.items() if k!='policy_id'}))
        with self.assertRaises(r.Held):r._policy(value)
    def test_bad_version_shape(self):
        with self.assertRaises(r.Held):r.build_policy(self.source,r.PREFIX+'RealFiles',{},r.file_pin(self.function))
    def test_wrong_namespace(self):
        with self.assertRaises(r.Held):r.build_policy(self.source,'/Game/Production',self.versions,r.file_pin(self.function))
    def test_full_real_file_seal_and_consume(self):
        _,body=fixture(self.policy['root']);body['policy_id']=self.policy['policy_id'];body['versions']=self.versions;body['live']['source_sha256']=r.SOURCE_SHA
        for key in ('import_native','reload_native'):
            metadata=body[key]['metadata'];metadata['source_filename']=self.policy['source']['path'];metadata['source_md5']=self.policy['source_md5']
            metadata['source']={k:self.policy['source'][k] for k in ('bytes','sha256')}
        raw=r.seal(self.policy,body,self.package)
        current=copy.deepcopy(body['reload_native']);current['capture_id']=str(uuid.uuid4());current['observed_at_utc']=datetime.now(timezone.utc).isoformat()
        result=r.consume(self.policy,raw,expected_receipt_sha256=r.sha(raw),current_native_raw=r.encode(current),expected_editor_pid=123,package_path=self.package)
        self.assertTrue(result['receipt_accepted'],result)
        self.package.write_bytes(b'tampered')
        result=r.consume(self.policy,raw,expected_receipt_sha256=r.sha(raw),current_native_raw=r.encode(current),expected_editor_pid=123,package_path=self.package)
        self.assertFalse(result['receipt_accepted'])


if __name__=='__main__':unittest.main()
