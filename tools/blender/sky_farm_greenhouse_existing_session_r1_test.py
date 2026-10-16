"""PR170 caller integration contracts. Fixture bytes are synthetic, never art proof."""
import builtins
import contextlib
import copy
import io
import json
import os
from pathlib import Path
import tempfile
import types
import unittest
from unittest import mock

SOURCE = Path(__file__).with_name("sky_farm_greenhouse_existing_session_r1.py")


def load(path, name):
    module = types.ModuleType(name); module.__file__ = str(path.resolve())
    exec(compile(path.read_bytes(), str(path), "exec"), module.__dict__)
    return module


CALLER = load(SOURCE, "greenhouse_adopted_caller")
STAGES = load(CALLER.STAGES, "greenhouse_adopted_stages")
OBSERVED = "2026-10-16T15:00:00+00:00"


def write(path, value):
    path.write_text(json.dumps(value, allow_nan=False), encoding="utf-8")
    return CALLER.pin(path)


def fixture(root):
    context = dict(scene="Scene", view_layer="ViewLayer", active="Cube", selected=["Cube"], mode="OBJECT", filepath="")
    baseline = dict(read_only=True, run_called=False, pid=12580, observed_at_utc="2026-10-16T07:00:56.288243+00:00",
                    scene_hashes={"Scene":"a"*64, "Retained_R1":"b"*64, "Retained_R2":"c"*64}, context=context)
    baseline_path = root/"baseline.json"; baseline_pin = write(baseline_path, baseline)
    inputs=[]
    for name in (CALLER.GENERATOR.name, CALLER.RECIPE.name, SOURCE.name):
        path=root/name; path.write_bytes(b"EXPLICITLY SYNTHETIC producer input, not actual source"); inputs.append(CALLER.pin(path))
    inputs.append(baseline_pin)
    outputs={}
    for role in ("source","glb","hero","manifest","startup_backup"):
        path=root/(role+".fixture");path.write_bytes(("SYNTHETIC "+role+", not Blender/GLB/PNG evidence").encode());outputs[role]=CALLER.pin(path)
    terminal=dict(schema="daedalus.sky-farm.existing-session.v1",operation_id="sky-farm-greenhouse-r1-32880",
        accepted_allocation_hub=32880,inputs=inputs,started_at_utc="2026-10-16T07:20:41.035766+00:00",
        finished_at_utc="2026-10-16T07:21:12.045565+00:00",state="TERMINAL_SOURCE_HERO_CREATED_REVIEW_PENDING",
        process_launched=False,process_exit_code=None,existing_blender_pid=12580,original_context=copy.deepcopy(context),
        retained_scene_hashes=copy.deepcopy(baseline["scene_hashes"]),retained_scenes_preserved=True,original_context_restored=True,
        startup_copy_result=["FINISHED"],source_copy_result=["FINISHED"],glb_operator_result=["FINISHED"],render_operator_result=["FINISHED"],
        scene="Bld_SkyFarm_GreenhouseBay_R1",**outputs)
    release=dict(grant=32880,observed_at_utc="2026-10-16T07:22:45.7198146+00:00",
        before=dict(compute=dict(holder="pootscoot")),unlock=dict(ok=True,lock=None),after={})
    terminal_path=root/"terminal.json";release_path=root/"release.json";write(terminal_path,terminal);write(release_path,release)
    return dict(root=root,terminal_path=terminal_path,baseline_path=baseline_path,release_path=release_path,
                terminal=terminal,baseline=baseline,release=release)


def qualify(f, release=True, output=None):
    return CALLER.stage_completion(f["terminal_path"],f["baseline_path"],f["release_path"] if release else None,
                                  "pootscoot" if release else None,OBSERVED,output)


def refresh(f):
    baseline_pin=write(f["baseline_path"],f["baseline"])
    f["terminal"]["inputs"][-1]=baseline_pin
    write(f["terminal_path"],f["terminal"]);write(f["release_path"],f["release"])


class GreenhouseStageAdoption(unittest.TestCase):
    def test_retained_success_uses_real_helper_and_all_pinned_roles(self):
        with tempfile.TemporaryDirectory() as temp:
            f=fixture(Path(temp));result=qualify(f)
            self.assertTrue(result["operation_completed"]);self.assertTrue(result["stage_completed"])
            self.assertTrue(result["compute_release_verified"]);self.assertIsNone(result["process_exit_code"])
            self.assertFalse(result["native_qualified"]);self.assertFalse(result["execution"])
            self.assertEqual({"blend","glb","hero","manifest"},set(result["report"]["stages"][0]["verified_outputs"]))
            inputs=result["document"]["stages"][0]["attempts"][0]["inputs"]
            self.assertEqual({"producer_source","producer_recipe","producer_caller","session_baseline","stage_helper"},set(inputs))
            self.assertEqual(CALLER.pin(CALLER.STAGES),result["stage_helper"])
            self.assertEqual(13,result["report"]["pins_checked"])

    def test_gui_return_boundary_is_pending_separate_release_not_success(self):
        with tempfile.TemporaryDirectory() as temp:
            f=fixture(Path(temp));result=CALLER.returned_operation(f["terminal"],CALLER.pin(f["terminal_path"]),f["baseline_path"])
            self.assertFalse(result["stage_completed"]);self.assertTrue(result["stage_evidence"]["operation_completed"])
            self.assertFalse(result["stage_evidence"]["compute_release_verified"])
            self.assertEqual("RETURNED_OPERATION_REQUIRES_SEPARATE_RELEASE_QUALIFICATION",result["completion_state"])
            self.assertEqual("operator-reconciliation-only-no-replay",result["stage_evidence"]["report"]["stages"][0]["advice"])

    def test_missing_release_cannot_be_hidden_by_successful_publication(self):
        with tempfile.TemporaryDirectory() as temp:
            f=fixture(Path(temp));path=Path(temp)/"pending-stage.json";result=qualify(f,False,path)
            self.assertTrue(path.is_file());self.assertIsNotNone(result["published_receipt"])
            self.assertFalse(result["stage_completed"]);self.assertIsNone(result["process_exit_code"])
            self.assertFalse(STAGES.inspect(STAGES.read_json(path),now=OBSERVED)["complete"])

    def test_failed_unknown_and_incomplete_retained_witnesses_require_reconciliation(self):
        for kind in ("failed","unknown","missing-output","missing-glb-finished"):
            with self.subTest(kind=kind),tempfile.TemporaryDirectory() as temp:
                f=fixture(Path(temp));t=f["terminal"]
                if kind=="failed":t["state"]="TERMINAL_FAILED_PARTIAL_OUTPUTS_RECONCILE";t["error"]="fixture guard failed"
                if kind=="unknown":t["state"]="SOURCE_EXPORTED_HERO_RUNNING";del t["finished_at_utc"]
                if kind=="missing-output":del t["hero"]
                if kind=="missing-glb-finished":del t["glb_operator_result"]
                refresh(f);result=qualify(f)
                self.assertFalse(result["stage_completed"]);self.assertFalse(result["operation_completed"])
                self.assertIsNone(result["process_exit_code"])
                self.assertEqual("reconciliation-required",result["report"]["stages"][0]["status"])

    def test_greenhouse_does_not_invent_copperfall_restore_flag_or_ignore_false_one(self):
        with tempfile.TemporaryDirectory() as temp:
            f=fixture(Path(temp));self.assertNotIn("startup_objects_preserved",f["terminal"]);self.assertTrue(qualify(f)["stage_completed"])
            f["terminal"]["startup_objects_preserved"]=False;refresh(f);self.assertFalse(qualify(f)["stage_completed"])
        for key in ("original_context_restored","retained_scenes_preserved"):
            with self.subTest(key=key),tempfile.TemporaryDirectory() as temp:
                f=fixture(Path(temp));f["terminal"][key]=1;refresh(f);self.assertFalse(qualify(f)["stage_completed"])

    def test_nested_context_scene_hashes_and_baseline_time_all_remain_protected(self):
        for kind in ("active","view_layer","filepath","selected","hash","pid","later-baseline"):
            with self.subTest(kind=kind),tempfile.TemporaryDirectory() as temp:
                f=fixture(Path(temp));t=f["terminal"]
                if kind in ("active","view_layer","filepath"):t["original_context"][kind]="Other"
                if kind=="selected":t["original_context"]["selected"]=[]
                if kind=="hash":t["retained_scene_hashes"]["Scene"]="f"*64
                if kind=="pid":t["existing_blender_pid"]=9
                if kind=="later-baseline":f["baseline"]["observed_at_utc"]="2026-10-16T08:00:00Z"
                refresh(f);result=qualify(f);self.assertFalse(result["stage_completed"])
                self.assertFalse(result["report"]["stages"][0]["gui_operation"]["restoration_verified"])

    def test_exact_release_allocation_owner_boolean_and_nanosecond_order(self):
        for kind in ("allocation","owner","integer-unlock","still-held","before-finish"):
            with self.subTest(kind=kind),tempfile.TemporaryDirectory() as temp:
                f=fixture(Path(temp));r=f["release"]
                if kind=="allocation":r["grant"]=32881
                if kind=="owner":r["before"]["compute"]["holder"]="someone-else"
                if kind=="integer-unlock":r["unlock"]["ok"]=1
                if kind=="still-held":r["after"]["compute"]={"holder":"pootscoot"}
                if kind=="before-finish":r["observed_at_utc"]="2026-10-16T07:21:12.0455649+00:00"
                refresh(f);self.assertFalse(qualify(f)["stage_completed"])

    def test_fabricated_process_exit_or_wrong_producer_identity_is_malformed(self):
        for key,value in (("process_exit_code",0),("schema","unrelated.v1"),("operation_id","sky-farm-greenhouse-r1-32881"),("accepted_allocation_hub",True)):
            with self.subTest(key=key),tempfile.TemporaryDirectory() as temp:
                f=fixture(Path(temp));f["terminal"][key]=value;refresh(f)
                with self.assertRaises(ValueError):qualify(f)

    def test_output_and_producer_source_hash_drift_are_refused(self):
        for target in ("glb","producer"):
            with self.subTest(target=target),tempfile.TemporaryDirectory() as temp:
                f=fixture(Path(temp));path=f["terminal"]["glb"]["path"] if target=="glb" else f["terminal"]["inputs"][0]["path"]
                Path(path).write_bytes(b"changed fixture")
                with self.assertRaises(ValueError):qualify(f)

    def test_baseline_input_cannot_be_substituted_or_inputs_omitted(self):
        with tempfile.TemporaryDirectory() as temp:
            f=fixture(Path(temp));f["baseline"]["context"]["active"]="Other";write(f["baseline_path"],f["baseline"])
            with self.assertRaisesRegex(ValueError,"baseline pin"):qualify(f)
        with tempfile.TemporaryDirectory() as temp:
            f=fixture(Path(temp));f["terminal"]["inputs"]=[];write(f["terminal_path"],f["terminal"])
            with self.assertRaisesRegex(ValueError,"four explicit"):qualify(f)

    def test_returned_snapshot_pin_is_checked_before_qualification(self):
        with tempfile.TemporaryDirectory() as temp:
            f=fixture(Path(temp));snapshot=CALLER.pin(f["terminal_path"]);f["terminal_path"].write_bytes(b"changed")
            with self.assertRaisesRegex(ValueError,"snapshot changed"):CALLER.returned_operation(f["terminal"],snapshot,f["baseline_path"])

    def test_immutable_publication_readback_and_no_overwrite_or_fallback(self):
        with tempfile.TemporaryDirectory() as temp:
            f=fixture(Path(temp));path=Path(temp)/"complete.json";result=qualify(f,True,path);self.assertTrue(result["stage_completed"])
            original=path.read_bytes();self.assertTrue(STAGES.inspect(STAGES.read_json(path),now=OBSERVED)["complete"])
            with self.assertRaises(FileExistsError):qualify(f,True,path)
            self.assertEqual(original,path.read_bytes())
            other=Path(temp)/"unpublished.json"
            with mock.patch.object(os,"link",side_effect=OSError("unsupported hard link")),self.assertRaises(OSError):qualify(f,True,other)
            self.assertFalse(other.exists());self.assertFalse(list(Path(temp).glob('.stage-*.tmp')))

    def test_copperfall_profile_still_requires_its_original_three_flags_and_flat_baseline(self):
        with tempfile.TemporaryDirectory() as temp:
            f=fixture(Path(temp));t=f["terminal"];t["schema"]=STAGES.GUI_SCHEMA
            t["original_context"]["active_object"]=t["original_context"].pop("active")
            b=f["baseline"];context=b.pop("context");b.update(original_scene=context["scene"],mode=context["mode"],active=context["active"],selected=context["selected"],filepath=context["filepath"])
            def inspect():
                refresh(f)
                d=STAGES.adapt_gui(f["terminal_path"],"copperfall-regression","source-export-hero",t["operation_id"],CALLER.OUTPUT_FIELDS,OBSERVED,f["baseline_path"],f["release_path"],"pootscoot")
                return STAGES.inspect(d,now=OBSERVED)
            self.assertFalse(inspect()["complete"])
            t["startup_objects_preserved"]=False;self.assertFalse(inspect()["complete"])
            t["startup_objects_preserved"]=True;self.assertTrue(inspect()["complete"])
            del b["original_scene"];self.assertFalse(inspect()["complete"])

    def test_import_and_inert_default_do_not_load_helper_or_call_apps_or_write(self):
        original_import=builtins.__import__
        def guarded(name,*args,**kwargs):
            if name.split('.')[0] in {"bpy","socket","http","urllib","requests","subprocess"}:raise AssertionError("app/network/process import")
            return original_import(name,*args,**kwargs)
        raw=SOURCE.read_bytes();code=compile(raw,str(SOURCE),'exec');s=types.ModuleType('inert_caller');s.__file__=str(SOURCE.resolve());output=io.StringIO()
        with mock.patch('builtins.__import__',side_effect=guarded):
            exec(code,s.__dict__)
            with mock.patch.object(s,'stage_completion',side_effect=AssertionError('helper invoked')),mock.patch.object(s,'run',side_effect=AssertionError('GUI invoked')),mock.patch.object(Path,'open',side_effect=AssertionError('file access')),contextlib.redirect_stdout(output):
                self.assertEqual(0,s.main([]))
        value=json.loads(output.getvalue());self.assertEqual('INERT_NO_OPERATION_OR_FILE_WRITES',value['state']);self.assertEqual(0,value['app_calls'])

    def test_explicit_file_only_cli_returns_zero_two_three_at_caller_boundary(self):
        with tempfile.TemporaryDirectory() as temp:
            f=fixture(Path(temp));args=['--terminal',str(f['terminal_path']),'--baseline',str(f['baseline_path']),'--release',str(f['release_path']),'--release-owner','pootscoot','--observed-at-utc',OBSERVED]
            with mock.patch.object(CALLER,'run',side_effect=AssertionError('GUI')),mock.patch.object(CALLER,'observe',side_effect=AssertionError('GUI')):
                output=io.StringIO()
                with contextlib.redirect_stdout(output):self.assertEqual(0,CALLER.main(args))
                self.assertTrue(json.loads(output.getvalue())['stage_completed'])
                f['terminal']['state']='TERMINAL_FAILED_PARTIAL_OUTPUTS_RECONCILE';refresh(f);output=io.StringIO()
                with contextlib.redirect_stdout(output):self.assertEqual(2,CALLER.main(args))
                self.assertFalse(json.loads(output.getvalue())['stage_completed'])
                f['terminal_path'].write_text('{"schema":1,"schema":2}');output=io.StringIO()
                with contextlib.redirect_stdout(output):self.assertEqual(3,CALLER.main(args))
                self.assertFalse(json.loads(output.getvalue())['stage_completed'])


if __name__ == '__main__':
    unittest.main()
