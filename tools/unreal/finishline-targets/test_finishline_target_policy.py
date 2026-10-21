"""Tiny offline synthetic contract tests; no Unreal, provider, build, or native calls."""
import copy
import hashlib
from pathlib import Path
import types
import unittest

import finishline_target_policy as p
import ue_finishline_target_facts as adapter

ROOT = Path(__file__).parent


def contract():
    return p.parse_json((ROOT / "fixtures/daedalus_finishline_targets_20261021.json").read_bytes())


def observed(config, capture="synthetic-before"):
    # Explicit synthetic actuals, never represented as real native measurements.
    meshes = []
    for target in config["meshes"]:
        meshes.append({k: target[k] for k in ("id", "object_path", "class_path", "asset_file_sha256")})
        meshes[-1].update(state="OBSERVED", lods=[{"index": 0, "triangles": 2048, "vertices": 1200,
                          "screen_size": 1.0, "build_settings": {key:False for key in p.BUILD_FIELDS}}])
    return {"schema": p.FACTS_SCHEMA, "contract_sha256": p.fingerprint(config), "capture_id": capture,
            "reader_sha256": "a" * 64, "policy_sha256": "b" * 64,
            "observation":{"phase":"preflight","unit_id":None,"operation_id":None,"package_overrides":{}},
            "world": dict(config["world"], state="OBSERVED", partitioned=False),
            "meshes": meshes, "pcg": {"graph": {"state": "UNKNOWN"}, "component": {"state": "UNKNOWN"}},
            "hlod": {"state": "UNKNOWN"}, "release": dict(config["release"], state="OBSERVED"), "errors": []}


def completion(config, before, after, unit):
    target = config["units"][unit]["target_id"]
    overrides = {}
    if unit == p.UNITS[0]:
        selected = config["units"][unit].get("desired_policy", {})
        selected = selected.get("mesh_id") if isinstance(selected,dict) else None
        if selected:
            for row in after["meshes"]:
                if row["id"] == selected:
                    row["asset_file_sha256"] = "e"*64
                    overrides[selected] = "e"*64
    after["observation"]={"phase":"reopen","unit_id":unit,
                          "operation_id":"synthetic-op-1","package_overrides":overrides}
    result = {"unit_id": unit, "target_id": target, "operation_id": "synthetic-op-1",
              "contract_sha256": p.fingerprint(config), "before_sha256": p.fingerprint(before),
              "after_sha256": p.fingerprint(after), "changed": True, "observed_output_count": 1}
    for stage in ("operation", "save", "reopen", "consumer"):
        result[stage] = {"unit_id": unit, "target_id": target, "operation_id": result["operation_id"],
                         "completed": True, "receipt_sha256": "c" * 64, "record_path": "$.$synthetic." + stage}
    return result


def build_case():
    cfg = contract(); unit = p.UNITS[0]
    cfg["units"][unit]["desired_policy"] = {"kind": "build_settings", "mesh_id": "willow_mature",
                                           "changes": {"recompute_normals": True}}
    before = observed(cfg); after = copy.deepcopy(before); after["capture_id"] = "synthetic-after"
    after["meshes"][0]["lods"][0]["build_settings"]["recompute_normals"] = True
    ev = completion(cfg, before, after, unit)
    ev["applied_policy_sha256"] = p.fingerprint(cfg["units"][unit]["desired_policy"])
    return cfg, before, after, ev


def pcg_case():
    cfg = contract(); unit = p.UNITS[1]
    cfg["pcg"]["component_path"] = cfg["world"]["object_path"] + ":PersistentLevel.PYTH_PCG_Ecology.PCGComponent"
    cfg["pcg"]["expected_output_sha256"] = "d" * 64
    a = observed(cfg)
    a["pcg"] = {"graph": {"state": "OBSERVED", "object_path": cfg["pcg"]["graph_path"],
                "class_path": cfg["pcg"]["graph_class"], "asset_file_sha256": cfg["pcg"]["graph_file_sha256"]},
                "component": {"state": "OBSERVED", "object_path": cfg["pcg"]["component_path"],
                "class_path": cfg["pcg"]["component_class"], "world_path": cfg["world"]["object_path"],
                "graph_path": cfg["pcg"]["graph_path"], "seed": 7, "raw_generated_flag": False}}
    b = copy.deepcopy(a); b["capture_id"] = "synthetic-after"
    ev = completion(cfg, a, b, unit)
    ev.update(generated_by_pcg=True, manual_fallback=False, observed_output_sha256="d"*64,
              repeat_seed_output_sha256="d"*64, descriptor_mesh_paths=cfg["pcg"]["descriptor_mesh_paths"])
    return cfg, a, b, ev


def hlod_case():
    cfg = contract(); unit = p.UNITS[2]
    actor = cfg["world"]["object_path"] + ":PersistentLevel.SyntheticSource"
    cfg["hlod"].update(source_actor_paths=[actor], source_actor_classes={actor:"/Script/Engine.StaticMeshActor"},
                       layer_path="/Game/SyntheticLayer.SyntheticLayer")
    a = observed(cfg)
    a["hlod"] = dict(cfg["hlod"], state="OBSERVED", world_path=cfg["world"]["object_path"])
    b = copy.deepcopy(a); b["capture_id"] = "synthetic-after"
    ev = completion(cfg, a, b, unit)
    ev.update(map_migrated=False, source_actor_paths=[actor], proxy_state_changed=True,
              proxy_paths=["/Game/SyntheticProxy.SyntheticProxy"], supported_builder_route="standalone_nonpartitioned")
    return cfg, a, b, ev


def release_case():
    cfg = contract(); unit = p.UNITS[3]; a=observed(cfg); b=observed(cfg,"synthetic-after")
    ev=completion(cfg,a,b,unit)
    ev.update(fresh_archive=True,launched_packaged_executable=True,executable_sha256="1"*64,
              container_manifest_sha256="2"*64,custom_payload_sha256="3"*64,
              launched_map=cfg["world"]["object_path"],archive_path=cfg["release"]["fresh_archive_path"],
              executable_path=cfg["release"]["packaged_executable"],process_id=12345,process_terminal=True,exit_code=0)
    return cfg,a,b,ev


class TargetPolicyTests(unittest.TestCase):
    def test_actual_fixture_keeps_unbound_fields_and_no_adoption(self):
        cfg = contract(); result = p.inspect(cfg, observed(cfg))
        self.assertEqual(result["state"], "VALID_TARGET_FACTS")
        self.assertEqual(result["units"][p.UNITS[0]]["state"], "FACTS_READY_POLICY_SELECTION")
        self.assertEqual(result["units"][p.UNITS[1]]["state"], "PENDING")
        self.assertEqual(result["units"][p.UNITS[2]]["state"], "PENDING")
        self.assertTrue(all(not v["adopted"] for v in result["units"].values()))

    def test_duplicate_json_keys_and_nonfinite_constants_refused(self):
        for raw in (b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":Infinity}'):
            with self.subTest(raw=raw), self.assertRaises(p.ContractError): p.parse_json(raw)

    def test_oversized_payload_refused(self):
        with self.assertRaises(p.ContractError): p.parse_json(b' ' * (p.MAX_BYTES + 1))

    def test_exact_four_units_required(self):
        cfg = contract(); cfg["units"]["invented"] = {}
        self.assertEqual(p.inspect(cfg, observed(cfg))["state"], "REJECTED")

    def test_world_and_class_mismatch_refused(self):
        cfg = contract()
        for key, value in (("object_path", "/Game/Other.Other"), ("class_path", "/Script/Engine.Actor")):
            f = observed(cfg); f["world"][key] = value
            self.assertEqual(p.inspect(cfg, f)["state"], "REJECTED")

    def test_wrong_source_and_contract_pin_refused(self):
        cfg = contract()
        for field in ("contract_sha256", "mesh_source"):
            f = observed(cfg)
            if field == "mesh_source": f["meshes"][0]["asset_file_sha256"] = "0" * 64
            else: f[field] = "0" * 64
            self.assertEqual(p.inspect(cfg, f)["state"], "REJECTED")

    def test_bool_is_not_a_triangle_or_screen_measurement(self):
        cfg = contract()
        for key in ("triangles", "vertices", "screen_size"):
            f = observed(cfg); f["meshes"][0]["lods"][0][key] = True
            self.assertEqual(p.inspect(cfg, f)["state"], "REJECTED")

    def test_empty_and_excess_lods_refused(self):
        cfg = contract()
        for lods in ([], [observed(cfg)["meshes"][0]["lods"][0]] * 9):
            f = observed(cfg); f["meshes"][0]["lods"] = lods
            self.assertEqual(p.inspect(cfg, f)["state"], "REJECTED")

    def test_unreadable_mesh_facts_stay_pending(self):
        cfg = contract(); f = observed(cfg); f["meshes"][0] = {"id": "willow_mature", "state": "UNKNOWN"}
        self.assertEqual(p.inspect(cfg, f)["units"][p.UNITS[0]]["state"], "PENDING")

    def test_nonpartitioned_support_is_not_a_useful_hlod_source_set(self):
        cfg = contract(); f = observed(cfg)
        self.assertFalse(f["world"]["partitioned"])
        self.assertEqual(p.inspect(cfg, f)["units"][p.UNITS[2]]["state"], "PENDING")

    def test_reference_qualification_does_not_assert_adoption(self):
        cfg, a, b, ev = build_case(); result = p.qualify(cfg, a, b, ev)
        self.assertEqual(result["state"], "QUALIFIED_REFERENCED_EVIDENCE")
        self.assertFalse(result["adopted"])
        self.assertTrue(result["requires_owner_receipt_verification"])

    def test_noop_empty_output_and_stale_reopen_refused(self):
        for field, value in (("changed", False), ("observed_output_count", 0), ("observed_output_count", True)):
            cfg, a, b, ev = build_case(); ev[field] = value
            self.assertEqual(p.qualify(cfg, a, b, ev)["state"], "HELD")
        cfg, a, b, ev = build_case(); b["capture_id"] = a["capture_id"]; ev["after_sha256"] = p.fingerprint(b)
        self.assertEqual(p.qualify(cfg, a, b, ev)["state"], "HELD")

    def test_unrelated_mesh_or_geometry_change_refused(self):
        for mesh in (0, 1):
            cfg, a, b, ev = build_case(); b["meshes"][mesh]["lods"][0]["triangles"] -= 1
            ev["after_sha256"] = p.fingerprint(b)
            self.assertEqual(p.qualify(cfg, a, b, ev)["state"], "HELD")

    def test_stage_cross_target_or_missing_save_refused(self):
        for change in ("cross", "save", "record"):
            cfg, a, b, ev = build_case()
            if change == "cross": ev["consumer"]["target_id"] = "another-target"
            elif change == "save": ev["save"]["completed"] = False
            else: ev["save"]["record_path"] = ev["operation"]["record_path"]
            self.assertEqual(p.qualify(cfg, a, b, ev)["state"], "HELD")

    def test_repeated_metadata_cannot_fake_build_delta(self):
        cfg, a, b, ev = build_case(); b["meshes"] = copy.deepcopy(a["meshes"])
        b["meshes"][0]["nonce"] = "changed-label-only"; ev["after_sha256"] = p.fingerprint(b)
        self.assertEqual(p.qualify(cfg, a, b, ev)["state"], "HELD")

    def test_unbound_policy_is_not_completed_by_measured_facts(self):
        cfg = contract(); a = observed(cfg); b = observed(cfg, "later")
        self.assertEqual(p.qualify(cfg, a, b, completion(cfg, a, b, p.UNITS[0]))["state"], "HELD")

    def test_path_traversal_and_unrelated_descriptors_refused(self):
        for field in ("path", "descriptors"):
            cfg = contract()
            if field == "path": cfg["meshes"][0]["object_path"] = "/Game/../Private.Private"
            else: cfg["pcg"]["descriptor_mesh_paths"] = ["/Game/Cube.Cube"]
            self.assertEqual(p.inspect(cfg, observed(cfg))["state"], "REJECTED")

    def test_adapter_import_has_no_unreal_import_or_execution(self):
        self.assertNotIn("unreal", adapter.__dict__)

    def test_adapter_unknown_world_stops_before_target_queries(self):
        class Fake:
            UnrealEditorSubsystem = object()
            def __init__(self): self.calls = 0
            def get_editor_subsystem(self, _): self.calls += 1; raise AttributeError("Unavailable")
            def find_object(self, *_): raise AssertionError("Must not query after unknown world")
        fake = Fake()
        reader = hashlib.sha256(Path(adapter.__file__).read_bytes()).hexdigest()
        policy = hashlib.sha256(Path(p.__file__).read_bytes()).hexdigest()
        f = adapter.collect(contract(), "synthetic-capture", reader, policy, unreal_module=fake)
        self.assertEqual(fake.calls, 1); self.assertEqual(f["world"]["state"], "UNKNOWN")
        self.assertNotIn("partitioned", f["world"])
        self.assertTrue(all(x["state"] == "UNKNOWN" for x in f["meshes"]))

    def test_reader_pin_mismatch_refuses_before_unreal(self):
        class Fake:
            def __getattr__(self, _): raise AssertionError("No native access allowed")
        with self.assertRaises(p.ContractError):
            adapter.collect(contract(), "synthetic", "0"*64, "0"*64, unreal_module=Fake())

    def test_pcg_false_generated_flag_does_not_substitute_for_completion(self):
        cfg,a,b,ev=pcg_case()
        self.assertEqual(p.inspect(cfg,a)["units"][p.UNITS[1]]["state"],"TARGET_FACTS_READY")
        self.assertEqual(p.qualify(cfg,a,b,ev)["state"],"QUALIFIED_REFERENCED_EVIDENCE")
        ev["manual_fallback"]=True
        self.assertEqual(p.qualify(cfg,a,b,ev)["state"],"HELD")

    def test_pcg_seed_world_descriptor_and_expected_output_edges(self):
        for change in ("seed","world","descriptor","expected","repeat"):
            cfg,a,b,ev=pcg_case()
            if change=="seed":b["pcg"]["component"]["seed"]=15
            elif change=="world":b["pcg"]["component"]["world_path"]="/Game/Other.Other"
            elif change=="descriptor":ev["descriptor_mesh_paths"]=["/Game/Cube.Cube"]
            elif change=="expected":ev["observed_output_sha256"]="0"*64
            else:ev["repeat_seed_output_sha256"]="0"*64
            ev["after_sha256"]=p.fingerprint(b)
            self.assertEqual(p.qualify(cfg,a,b,ev)["state"],"HELD")

    def test_hlod_nonpartitioned_route_requires_nonempty_real_delta(self):
        cfg,a,b,ev=hlod_case()
        self.assertEqual(p.qualify(cfg,a,b,ev)["state"],"QUALIFIED_REFERENCED_EVIDENCE")
        for field,value in (("map_migrated",True),("proxy_state_changed",False),("proxy_paths",[]),
                            ("supported_builder_route","partitioned")):
            wrong=copy.deepcopy(ev);wrong[field]=value
            self.assertEqual(p.qualify(cfg,a,b,wrong)["state"],"HELD")

    def test_release_requires_fresh_artifacts_exact_realm_and_terminal(self):
        cfg,a,b,ev=release_case()
        self.assertEqual(p.qualify(cfg,a,b,ev)["state"],"QUALIFIED_REFERENCED_EVIDENCE")
        for field,value in (("fresh_archive",False),("launched_map","/Game/Other.Other"),
                            ("process_terminal",False),("process_id",True),("exit_code",True),
                            ("archive_path",cfg["release"]["historic_archive_not_current"]),
                            ("executable_sha256",None)):
            wrong=copy.deepcopy(ev);wrong[field]=value
            self.assertEqual(p.qualify(cfg,a,b,wrong)["state"],"HELD")

    def test_reader_and_policy_revision_changes_held(self):
        for field in ("reader_sha256","policy_sha256"):
            cfg,a,b,ev=build_case();b[field]="0"*64;ev["after_sha256"]=p.fingerprint(b)
            self.assertEqual(p.qualify(cfg,a,b,ev)["state"],"HELD")

    def test_unknown_prestate_cannot_be_replaced_by_after_success(self):
        cfg,a,b,ev=build_case();a["meshes"][0]={"id":"willow_mature","state":"UNKNOWN"}
        ev["before_sha256"]=p.fingerprint(a)
        self.assertEqual(p.qualify(cfg,a,b,ev)["state"],"HELD")

    def test_saved_lod_package_has_separate_bound_post_witness(self):
        cfg,a,b,ev=build_case()
        self.assertNotEqual(a["meshes"][0]["asset_file_sha256"],b["meshes"][0]["asset_file_sha256"])
        self.assertEqual(p.qualify(cfg,a,b,ev)["state"],"QUALIFIED_REFERENCED_EVIDENCE")
        b["observation"]["package_overrides"]={};ev["after_sha256"]=p.fingerprint(b)
        self.assertEqual(p.qualify(cfg,a,b,ev)["state"],"HELD")

    def test_unrelated_package_override_is_rejected(self):
        cfg,a,b,ev=build_case();b["observation"]["package_overrides"]["willow_young"]="f"*64
        ev["after_sha256"]=p.fingerprint(b)
        self.assertEqual(p.qualify(cfg,a,b,ev)["state"],"HELD")

    def test_unknown_or_missing_build_flags_rejected(self):
        cfg=contract()
        for change in ("extra","missing"):
            f=observed(cfg);flags=f["meshes"][0]["lods"][0]["build_settings"]
            if change=="extra":flags["invented_reflected_flag"]=False
            else:del flags["recompute_normals"]
            self.assertEqual(p.inspect(cfg,f)["state"],"REJECTED")

    def test_observed_partition_migration_overrides_false_evidence_claim(self):
        cfg,a,b,ev=hlod_case();b["world"]["partitioned"]=True
        ev["supported_builder_route"]="partitioned";ev["after_sha256"]=p.fingerprint(b)
        self.assertEqual(p.qualify(cfg,a,b,ev)["state"],"HELD")

    def test_authored_lod_pair_preserves_lod0_build_and_declared_lod1(self):
        cfg=contract();unit=p.UNITS[0]
        flags={key:False for key in p.BUILD_FIELDS}
        cfg["units"][unit]["desired_policy"]={"kind":"authored_lod_pair","mesh_id":"willow_mature",
            "lod1_source_sha256":"d"*64,"lod1_triangles":512,"lod1_vertices":400,
            "screen_sizes":[1.0,0.4],"lod1_build_settings":flags}
        a=observed(cfg);b=copy.deepcopy(a);b["capture_id"]="synthetic-after"
        b["meshes"][0]["lods"].append({"index":1,"triangles":512,"vertices":400,
                                       "screen_size":0.4,"build_settings":copy.deepcopy(flags)})
        ev=completion(cfg,a,b,unit);ev["applied_policy_sha256"]=p.fingerprint(cfg["units"][unit]["desired_policy"])
        self.assertEqual(p.qualify(cfg,a,b,ev)["state"],"QUALIFIED_REFERENCED_EVIDENCE")
        for index in (0,1):
            wrong=copy.deepcopy(b);wrong["meshes"][0]["lods"][index]["build_settings"]["recompute_normals"]=True
            bad=copy.deepcopy(ev);bad["after_sha256"]=p.fingerprint(wrong)
            self.assertEqual(p.qualify(cfg,a,wrong,bad)["state"],"HELD")

    def test_release_archive_cannot_be_external_or_historical(self):
        for archive in ("https://example.invalid/package", "C:/Unreal/DaedalusRealm/Saved/Packages/../private",
                        contract()["release"]["historic_archive_not_current"]):
            cfg=contract();cfg["release"]["fresh_archive_path"]=archive
            self.assertEqual(p.inspect(cfg,observed(cfg))["state"],"REJECTED")

    def test_adapter_reads_admitted_post_package_and_keeps_reflection_unknown(self):
        cfg,_,_,_=build_case()
        cfg_original=copy.deepcopy(cfg)
        class Obj:
            def __init__(self,path,cls):self.path=path;self.cls=cls
            def get_path_name(self):return self.path
            def get_class(self):return types.SimpleNamespace(get_path_name=lambda:self.cls)
            def get_num_triangles(self,_):return 2048
            def get_num_vertices(self,_):return 1200
        class Settings:
            def get_editor_property(self,key):
                if key=="world_partition":raise AttributeError("Not exposed")
                return False
        class World(Obj):
            def get_world_settings(self):return Settings()
            def get_editor_property(self,_):return []
        world=World(cfg["world"]["object_path"],cfg["world"]["class_path"])
        class UE:
            UnrealEditorSubsystem="world";StaticMeshEditorSubsystem="mesh"
            def get_editor_subsystem(self,which):
                if which=="world":return types.SimpleNamespace(get_editor_world=lambda:world)
                return types.SimpleNamespace(get_lod_count=lambda _:1,get_lod_screen_sizes=lambda _:[1.0],
                                              get_lod_build_settings=lambda *_:Settings())
            def find_object(self,_,path):
                if path==cfg["pcg"]["graph_path"]:return Obj(path,cfg["pcg"]["graph_class"])
                for target in cfg["meshes"]:
                    if path==target["object_path"]:return Obj(path,target["class_path"])
                raise AssertionError("Unexpected target lookup")
        def file_read(path,*_):
            if path.endswith(".uproject"):return cfg["release"]["project_file_sha256"]
            if "PCG_Ecology" in path:return cfg["pcg"]["graph_file_sha256"]
            if "Mature" in path:return "e"*64
            return cfg["meshes"][1]["asset_file_sha256"]
        observation={"phase":"reopen","unit_id":p.UNITS[0],"operation_id":"synthetic-op-1",
                     "package_overrides":{"willow_mature":"e"*64}}
        f=adapter.collect(cfg,"synthetic-capture",hashlib.sha256(Path(adapter.__file__).read_bytes()).hexdigest(),
                          hashlib.sha256(Path(p.__file__).read_bytes()).hexdigest(),observation=observation,
                          unreal_module=UE(),file_reader=file_read)
        self.assertEqual(f["meshes"][0]["asset_file_sha256"],"e"*64)
        self.assertEqual(f["meshes"][0]["state"],"OBSERVED")
        self.assertIsNone(f["world"]["partitioned"])
        self.assertEqual(p.inspect(cfg,f)["units"][p.UNITS[2]]["state"],"PENDING")
        self.assertEqual(cfg,cfg_original)


if __name__ == "__main__":
    unittest.main()
