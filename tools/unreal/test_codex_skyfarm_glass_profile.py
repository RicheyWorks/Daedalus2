# SPDX-License-Identifier: MIT
"""Tiny offline32971 contract checks. No Unreal, network, engine or child process."""
from copy import deepcopy
import importlib.util
import math
from pathlib import Path
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import patch
import codex_skyfarm_glass_delivery as host

path=Path(__file__).resolve().parents[2]/'engines/unreal/DaedalusLink/Content/Python/daedalus_codex_skyfarm_glass.py'
spec=importlib.util.spec_from_file_location('_tested_glass_contract',path)
p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)


def reference(node=None,index=0,input_name=''):
    return dict(Expression=node,OutputIndex=index,InputName=input_name,Mask=0,MaskR=0,MaskG=0,MaskB=0,MaskA=0)


def observation():
    c=p.source_contract(deepcopy(p.RAW));call=p.MATERIAL+':Call';prefix='/Script/Engine.MaterialExpression'
    g=dict(call=call,function=p.FUNCTION,nodes={call:prefix+'MaterialFunctionCall'},factor_inputs={},
        function_outputs=list(p.OUTPUTS.values())+['TransmissionColor'],
        omitted_defaults={k:dict(value=list(v),use_preview_default=True,preview_connected=False) for k,v in p.DEFAULTS.items()},
        default_roots={k:reference() for k in p.ROOTS},roots={k:reference() for k in p.ROOTS})
    for name,value in c['factor_inputs'].items():
        node=p.MATERIAL+':'+name;g['nodes'][node]=prefix+('Constant3Vector' if len(value)==3 else 'Constant')
        g['factor_inputs'][name]=dict(node=node,value=list(value),reference=reference(node,0,name))
    g['function_input_names']=list(c['factor_inputs'])+list(p.DEFAULTS)
    g['function_inputs']={name:(g['factor_inputs'][name]['reference'] if name in g['factor_inputs'] else None) for name in g['function_input_names']}
    for name,out in p.OUTPUTS.items():g['roots'][name]=reference(call,g['function_outputs'].index(out))
    node=p.MATERIAL+':TransmissionOutput';g['nodes'][node]=prefix+'ThinTranslucentMaterialOutput'
    g['custom_outputs']=[dict(node=node,TransmittanceColor=reference(call,g['function_outputs'].index('TransmissionColor')),
                              SurfaceCoverage=reference(),default_SurfaceCoverage=reference())]
    g['proofs']={k:dict(bytes=100,sha256='a'*64) for k in ['root_default','root_delta','custom_default','custom_delta']}
    g['proofs']['function_body_package']=dict(p.FUNCTION_BODY)
    return dict(material=p.MATERIAL,mesh=p.MESH,material_class='/Script/Engine.Material',mesh_class='/Script/Engine.StaticMesh',
        slot_materials=[p.MATERIAL],physical=c['physical'],active_customized_uvs=0,
        geometry=dict(triangles=48,build_scale=[1.,1.,1.],nanite=False,generate_lightmap_uvs=False,
                      simple_collision_count=0,import_data_class='InterchangeAssetImportData',bounds=deepcopy(p.BOUNDS)),graph=g)


class SourceTests(unittest.TestCase):
    def test_raw_input_is_preserved_and_alpha_is_independent(self):
        raw=deepcopy(p.RAW);before=deepcopy(raw);c=p.source_contract(raw)
        self.assertEqual(raw,before);self.assertEqual(c['factor_inputs']['TransmissionFactor'],[.25])
        self.assertEqual(c['factor_inputs']['BaseColorFactor_A'],[.1599999964237213])
        self.assertNotEqual(c['factor_inputs']['BaseColorFactor_A'],c['factor_inputs']['TransmissionFactor'])
        c['raw_material']['pbrMetallicRoughness']['baseColorFactor'][0]=0
        self.assertEqual(raw,before)

    def test_changed_or_extra_raw_semantics_are_rejected(self):
        mutations=[lambda r:r.update(alphaMode='OPAQUE'),lambda r:r.update(doubleSided=1),
            lambda r:r.update(emissiveFactor=[0.,0.,0.]),lambda r:r['extensions'].update(KHR_materials_ior={'ior':1.5}),
            lambda r:r['extensions']['KHR_materials_transmission'].update(transmissionTexture={'index':0}),
            lambda r:r['pbrMetallicRoughness']['baseColorFactor'].__setitem__(3,.25),
            lambda r:r['pbrMetallicRoughness'].update(metallicFactor=False),
            lambda r:r['extensions']['KHR_materials_transmission'].update(transmissionFactor=math.nan)]
        for mutate in mutations:
            with self.subTest(mutation=mutate):
                raw=deepcopy(p.RAW);mutate(raw)
                with self.assertRaises(ValueError):p.source_contract(raw)

    def test_host_cannot_qualify_a_vacuously_empty_installed_pin_set(self):
        args=SimpleNamespace(glb=Path('a.glb'),manifest=Path('manifest.json'),baseline=Path('baseline.json'),evidence=Path('evidence.json'),output=Path('never-written.json'))
        pins={'a.glb':dict(bytes=88052,sha256=host.GLB_SHA),'manifest.json':dict(bytes=5639,sha256=host.MANIFEST_SHA),
              'baseline.json':dict(bytes=1,sha256=host.BASE_SHA),'evidence.json':dict(bytes=10224,sha256=host.EVIDENCE_SHA)}
        bounds={edge:[p.BOUNDS[edge][axis]/100 for axis in (0,2,1)] for edge in ('min','max')}
        node=dict(name='SFG_R1_glass_glass',authored_transform_fields={},primitives=[dict(
            triangles_decoded_from_index_count=48,position_count_decoded=96,attributes={'POSITION':0,'NORMAL':1},
            material_index=1,position_bounds_decoded_node_world=bounds)])
        decoded=dict(nodes=[node],materials=[{},deepcopy(p.RAW)],images=0,textures=0)
        evidence=dict(stage='SOURCE_MAPPING_AVAILABLE_NATIVE_HELD',native_calls=0,compute_claims=0,installed_file_pins=[])
        with patch.object(host,'pin',side_effect=lambda v:pins[str(v)]),patch.object(host,'glb',return_value=decoded),patch.object(host,'load',return_value=evidence),patch.object(host,'write') as write:
            with self.assertRaises(ValueError):host.prepare(args)
            write.assert_not_called()


class ObservationTests(unittest.TestCase):
    def test_complete_synthetic_record_still_does_not_grant_admission(self):
        result=p.check_observation(observation())
        self.assertFalse(result['native_ready']);self.assertFalse(result['runtime_authorized'])
        self.assertTrue(result['glass_must_remain_held_until_admitted'])

    def test_alpha_only_graph_without_custom_output_is_rejected(self):
        x=observation();x['graph']['custom_outputs']=[]
        with self.assertRaises(ValueError):p.check_observation(x)

    def test_explicit_alphamode_two_is_a_supported_factory_shape(self):
        x=observation();g=x['graph'];node=p.MATERIAL+':AlphaMode'
        g['nodes'][node]='/Script/Engine.MaterialExpressionConstant'
        row=dict(node=node,value=[2.],reference=reference(node,0,'AlphaMode'))
        g['factor_inputs']['AlphaMode']=row;g['function_inputs']['AlphaMode']=row['reference']
        del g['omitted_defaults']['AlphaMode']
        self.assertFalse(p.check_observation(x)['native_ready'])

    def test_masked_factor_or_hidden_extra_connection_is_rejected(self):
        for change in ['mask','extra']:
            x=observation();g=x['graph']
            if change=='mask':g['factor_inputs']['TransmissionFactor']['reference']['Mask']=1
            else:
                g['function_input_names'].append('UnreportedTexture');g['function_inputs']['UnreportedTexture']=reference(g['call'],0,'UnreportedTexture')
            with self.subTest(change=change),self.assertRaises(ValueError):p.check_observation(x)

    def test_typed_root_constant_switch_cannot_override_connection(self):
        x=observation();g=x['graph'];g['default_roots']['Opacity']['UseConstant']=False
        g['default_roots']['Opacity']['Constant']=0.;g['roots']['Opacity']['UseConstant']=True;g['roots']['Opacity']['Constant']=0.
        with self.assertRaises(ValueError):p.check_observation(x)

    def test_opacity_cannot_stand_in_for_transmission_output(self):
        x=observation();g=x['graph'];g['custom_outputs'][0]['TransmittanceColor']['OutputIndex']=g['function_outputs'].index('Opacity')
        with self.assertRaises(ValueError):p.check_observation(x)

    def test_raw_alpha_and_transmission_cannot_be_swapped(self):
        x=observation();a=x['graph']['factor_inputs'];a['BaseColorFactor_A']['value'],a['TransmissionFactor']['value']=a['TransmissionFactor']['value'],a['BaseColorFactor_A']['value']
        with self.assertRaises(ValueError):p.check_observation(x)

    def test_unexpected_coverage_or_mask_is_rejected(self):
        for key in ['SurfaceCoverage','TransmittanceColor']:
            x=observation();x['graph']['custom_outputs'][0][key]['Mask']=1
            with self.subTest(input=key),self.assertRaises(ValueError):p.check_observation(x)

    def test_extra_node_or_unknown_function_is_rejected(self):
        for change in ['node','function']:
            x=observation()
            if change=='node':x['graph']['nodes'][p.MATERIAL+':Extra']='/Script/Engine.MaterialExpressionPower'
            else:x['graph']['function']='/InterchangeAssets/gltf/MaterialBodies/MF_Default_Body.MF_Default_Body'
            with self.subTest(change=change),self.assertRaises(ValueError):p.check_observation(x)

    def test_all30_roots_and_separate_custom_witnesses_are_required(self):
        for change in ['root','proof']:
            x=observation()
            if change=='root':del x['graph']['roots']['Refraction']
            else:del x['graph']['proofs']['custom_delta']
            with self.subTest(change=change),self.assertRaises(ValueError):p.check_observation(x)

    def test_geometry_scale_nonfinite_and_boolean_counts_are_rejected(self):
        for change in ['scale','bounds','triangles','collision','uv']:
            x=observation()
            if change=='scale':x['geometry']['build_scale']=[100.,100.,100.]
            elif change=='bounds':x['geometry']['bounds']['max'][0]=math.inf
            elif change=='triangles':x['geometry']['triangles']=47
            elif change=='collision':x['geometry']['simple_collision_count']=False
            else:x['active_customized_uvs']=False
            with self.subTest(change=change),self.assertRaises(ValueError):p.check_observation(x)

    def test_reviewed_body_and_output_names_are_required(self):
        for change in ['package','names']:
            x=observation()
            if change=='package':x['graph']['proofs']['function_body_package']['sha256']='b'*64
            else:x['graph']['function_outputs'].append('TransmissionColor')
            with self.subTest(change=change),self.assertRaises(ValueError):p.check_observation(x)

    def test_preview_defaults_and_material_physical_contract_are_required(self):
        for change in ['preview','opaque','sided']:
            x=observation()
            if change=='preview':x['graph']['omitted_defaults']['AlphaMode']['preview_connected']=True
            elif change=='opaque':x['physical']['BlendMode']='BLEND_Opaque'
            else:x['physical']['TwoSided']=1
            with self.subTest(change=change),self.assertRaises(ValueError):p.check_observation(x)


class UE58ProfileTests(unittest.TestCase):
    """33041 changed-contract checks only; run this class, not the old suite.

    Fixtures are small synthetic normalized facts, never actual native proof.
    Even the complete top-level receiver fixture must remain intrinsically held.
    """
    @classmethod
    def setUpClass(cls):
        path58=path.with_name('daedalus_codex_skyfarm_glass_ue58_profile.py')
        spec58=importlib.util.spec_from_file_location('_tested_ue58_profile',path58)
        cls.v=importlib.util.module_from_spec(spec58);spec58.loader.exec_module(cls.v)

    def modern(self):
        x=observation();g=x['graph'];v=self.v
        node=p.MATERIAL+':AlphaMode'
        g['nodes'][node]='/Script/Engine.MaterialExpressionConstant'
        g['factor_inputs']['AlphaMode']=dict(node=node,value=[2.],reference=reference(node,0,'AlphaMode'))
        g['function_input_names']=list(v.INPUTS);g['function_outputs']=list(v.OUTPUTS)
        rgb=g['factor_inputs']['BaseColorFactor_RGB']['reference']
        rgb.update(Mask=1,MaskR=1,MaskG=1,MaskB=1)
        g['function_inputs']={name:(g['factor_inputs'][name]['reference'] if name in g['factor_inputs'] else None) for name in v.INPUTS}
        g['omitted_defaults']={name:dict(missing_function_input=True,matches=0) for name in ('EmissiveFactor','EmissiveStrength')}
        for name,out in p.OUTPUTS.items():g['roots'][name]=reference(g['call'],v.OUTPUTS.index(out))
        g['custom_outputs'][0]['TransmittanceColor']=reference(g['call'],0)
        return x

    def check(self,x,body=None,source=None):
        return self.v.check_observation(x,deepcopy(self.v.BODY_TEXT) if body is None else body,
            deepcopy(self.v.SOURCE_PINS) if source is None else source)

    def test_complete_top_level_receiver_stays_intrinsically_held_and_unmodified(self):
        x=self.modern();before=deepcopy(x);result=self.check(x)
        self.assertEqual(x,before);self.assertEqual(result['top_level_abi'],'VALID')
        self.assertEqual(result['stage'],'HOLD_INTRINSIC_TRANSMISSION_MODEL_UNPROVEN')
        self.assertFalse(result['native_ready']);self.assertFalse(result['runtime_authorized'])
        self.assertIsNone(result['intrinsic_transport']['intrinsic_proof'])
        self.assertEqual(result['intrinsic_transport']['missing_evidence'],list(self.v.MISSING))

    def test_historical_policy_is_unchanged_and_still_refuses_modern_shape(self):
        import hashlib
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),self.v.GENERIC_SHA)
        with self.assertRaises(ValueError):p.check_observation(self.modern())

    def test_only_exact_rgb_output0_mask_is_recognized(self):
        for key,value in [('Mask',0),('MaskR',0),('MaskA',1),('OutputIndex',1),('MaskB',True)]:
            x=self.modern();x['graph']['factor_inputs']['BaseColorFactor_RGB']['reference'][key]=value
            with self.subTest(key=key,value=value),self.assertRaises(ValueError):self.check(x)

    def test_scalar_custom_and_root_masks_are_not_relaxed(self):
        for which in ['alpha','transmission','custom','root']:
            x=self.modern();g=x['graph']
            row={'alpha':g['factor_inputs']['BaseColorFactor_A']['reference'],
                'transmission':g['factor_inputs']['TransmissionFactor']['reference'],
                'custom':g['custom_outputs'][0]['TransmittanceColor'],'root':g['roots']['BaseColor']}[which]
            row['Mask']=1
            with self.subTest(which=which),self.assertRaises(ValueError):self.check(x)

    def test_alpha_mode_alpha_and_output_indices_are_exact(self):
        for which in ['alpha','mode','scalar-index','custom-index']:
            x=self.modern();g=x['graph']
            if which=='alpha':g['factor_inputs']['BaseColorFactor_A']['value']=[.25]
            elif which=='mode':g['factor_inputs']['AlphaMode']['value']=[1.]
            elif which=='scalar-index':g['factor_inputs']['TransmissionFactor']['reference']['OutputIndex']=1
            else:g['custom_outputs'][0]['TransmittanceColor']['OutputIndex']=7
            with self.subTest(which=which),self.assertRaises(ValueError):self.check(x)

    def test_exact_source_body_pins_and_complete_abi_are_required(self):
        for which in ['body-text','package','source','input','output']:
            x=self.modern();body=deepcopy(self.v.BODY_TEXT);source=deepcopy(self.v.SOURCE_PINS)
            if which=='body-text':body['sha256']='b'*64
            elif which=='package':x['graph']['proofs']['function_body_package']['sha256']='b'*64
            elif which=='source':source['qualification']['sha256']='b'*64
            elif which=='input':x['graph']['function_input_names'][0]='ForeignMode'
            else:x['graph']['function_outputs'][0]='ForeignTransmission'
            with self.subTest(which=which),self.assertRaises(ValueError):self.check(x,body,source)

    def test_extra_edge_node_and_altered_geometry_remain_rejected(self):
        for which in ['edge','node','triangles','scale','uv','normal-provenance']:
            x=self.modern();source=deepcopy(self.v.SOURCE_PINS)
            if which=='edge':x['graph']['function_inputs']['IOR']=reference(x['graph']['call'])
            elif which=='node':x['graph']['nodes'][p.MATERIAL+':Extra']='/Script/Engine.MaterialExpressionPower'
            elif which=='triangles':x['geometry']['triangles']=49
            elif which=='scale':x['geometry']['build_scale']=[.01,.01,.01]
            elif which=='uv':x['geometry']['generate_lightmap_uvs']=True
            else:source['source']['sha256']='b'*64
            with self.subTest(which=which),self.assertRaises(ValueError):self.check(x,source=source)

    def test_missing_repointed_or_fabricated_intrinsic_proof_never_clears(self):
        x=self.modern()
        self.assertEqual(self.check(x)['stage'],'HOLD_INTRINSIC_TRANSMISSION_MODEL_UNPROVEN')
        request=self.v.intrinsic_transport(self.v.BODY_TEXT)
        x['graph']['intrinsic_transport']=deepcopy(request)
        self.assertEqual(self.check(x)['stage'],'HOLD_INTRINSIC_TRANSMISSION_MODEL_UNPROVEN')
        for which in ['flag','repoint','missing','defaults']:
            x=self.modern();claim=deepcopy(request)
            if which=='flag':claim['intrinsic_proof']={'proven':True,'active_branch':'Normal'}
            elif which=='repoint':claim['body_text']['sha256']='b'*64
            elif which=='missing':claim['missing_evidence']=[]
            else:claim['emission']=[0.,0.,0.]
            x['graph']['intrinsic_transport']=claim
            with self.subTest(which=which),self.assertRaises(ValueError):self.check(x)

    def test_missing_default_cannot_be_forged_as_zero_or_boolean_count(self):
        for which in ['zero','bool']:
            x=self.modern();row=x['graph']['omitted_defaults']['EmissiveFactor']
            if which=='zero':row.update(value=[0.,0.,0.],use_preview_default=True)
            else:row['matches']=False
            with self.subTest(which=which),self.assertRaises(ValueError):self.check(x)

    def test_collector_request_matches_profile_without_importing_unreal(self):
        import ast
        source=path.with_name('daedalus_codex_skyfarm_glass_witness.py').read_text()
        tree=ast.parse(source);fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='intrinsic_transport_request')
        scope={};exec(compile(ast.Module(body=[fn],type_ignores=[]),'<pure-request-only>','exec'),scope)
        self.assertEqual(scope['intrinsic_transport_request'](self.v.BODY_TEXT),self.v.intrinsic_transport(self.v.BODY_TEXT))
        plan=self.v.future_witness_plan()
        self.assertFalse(plan['executable']);self.assertFalse(plan['native_authorized'])
        self.assertTrue(plan['unresolved_before_native'])


if __name__=='__main__':unittest.main()
