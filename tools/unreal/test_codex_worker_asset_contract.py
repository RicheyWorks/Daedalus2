"""Focused pure-data tests; passing does not prove a native import succeeded."""

import copy
import json
import unittest

from codex_worker_asset_contract import CLIP_LENGTH_TOLERANCE_S, qualify


def fixture():
    root = "/Game/Daedalus/Art/Workers/ProspectorQualificationR1"
    path = lambda name: root + "/" + name + "." + name
    names = ("Idle", "Walk", "Attack", "Hurt", "Mine", "Trade", "Repair")
    bones = [
        {"source_name": "rig:root", "native_name": "rig_root", "parent": None}
    ] + [
        {"source_name": "rig:joint%d" % i, "native_name": "rig_joint%d" % i,
         "parent": "rig_root" if i == 1 else "rig_joint%d" % (i - 1)}
        for i in range(1, 14)
    ]
    expected = {
        "asset_id": "prospector_pinned_fixture",
        "root": root,
        "clips": {name: {"span_s": 2.0 + i / 10.0, "first_key_s": 0.0,
                         "last_key_s": 2.0 + i / 10.0, "playback_origin_s": 0.0}
                  for i, name in enumerate(names)},
        "bones": bones,
    }
    observed = {
        "objects": [
            {"path": path("Worker"), "class": "SkeletalMesh"},
            {"path": path("Worker_Skeleton"), "class": "Skeleton"},
        ] + [{"path": path(name), "class": "AnimSequence"} for name in names] + [
            {"path": path("Worker_Physics"), "class": "PhysicsAsset"},
            {"path": path("Palette"), "class": "Material"},
            {"path": path("PaletteInstance"), "class": "MaterialInstanceConstant"},
        ],
        "mesh_path": path("Worker"),
        "skeleton_path": path("Worker_Skeleton"),
        "mesh_skeleton_path": path("Worker_Skeleton"),
        "clips": [
            {"source_name": name, "path": path(name), "skeleton_path": path("Worker_Skeleton"),
             "length_s": expected["clips"][name]["span_s"]}
            for name in names
        ],
        "bones": [dict(row, exists_in_all_clips=True) for row in bones],
        "saved_files": [],
    }
    return expected, observed


class WorkerAssetContractTests(unittest.TestCase):
    def assert_rejected(self, mutate_expected=None, mutate_observed=None):
        expected, observed = fixture()
        if mutate_expected:
            mutate_expected(expected)
        if mutate_observed:
            mutate_observed(observed)
        with self.assertRaises(ValueError):
            qualify(expected, observed)

    def test_valid_readback_returns_compact_json_mapping_without_mutating_inputs(self):
        expected, observed = fixture()
        before = copy.deepcopy((expected, observed))
        result = qualify(expected, observed)
        self.assertEqual(result["asset_id"], expected["asset_id"])
        self.assertEqual(result["mesh_path"], observed["mesh_path"])
        self.assertEqual(result["skeleton_path"], observed["skeleton_path"])
        self.assertEqual(result["clips"], {row["source_name"]: row["path"] for row in observed["clips"]})
        self.assertEqual(result["bones"]["rig:root"], "rig_root")
        self.assertEqual(len(result["material_paths"]), 2)
        self.assertIsNotNone(result["physics_asset_path"])
        self.assertEqual(json.loads(json.dumps(result)), result)
        self.assertEqual((expected, observed), before)

    def test_valid_without_optional_materials_or_physics_and_with_reordered_rows(self):
        expected, observed = fixture()
        observed["objects"] = [row for row in reversed(observed["objects"])
                               if row["class"] in {"SkeletalMesh", "Skeleton", "AnimSequence"}]
        observed["clips"].reverse()
        observed["bones"].reverse()
        result = qualify(expected, observed)
        self.assertIsNone(result["physics_asset_path"])
        self.assertEqual(result["material_paths"], [])

    def test_one_frame_length_tolerance_accepts_both_directions(self):
        for sign in (-1, 1):
            with self.subTest(sign=sign):
                expected, observed = fixture()
                observed["clips"][0]["length_s"] += sign * (CLIP_LENGTH_TOLERANCE_S - 0.000001)
                qualify(expected, observed)

    def test_offset_is_not_a_blanket_duration_allowance(self):
        # The old fixture described zero-origin keys but native lengths longer
        # by 1/24. That remains invalid; only evidenced source key times change
        # the expected playback length.
        expected, observed = fixture()
        spans = dict(Idle=2.0, Walk=1.0, Attack=1.0, Hurt=1.0,
                     Mine=1.5, Trade=2.0, Repair=1.5)
        actual = {name: (2.0416667461395264 if span == 2.0 else
                        1.5416666269302368 if span == 1.5 else 1.0416666269302368)
                  for name, span in spans.items()}
        for name, span in spans.items():
            expected["clips"][name].update(span_s=span, last_key_s=span)
        for row in observed["clips"]:
            row["length_s"] = actual[row["source_name"]]
        with self.assertRaisesRegex(ValueError, "clip length differs"):
            qualify(expected, observed)

    def test_known_source_offset_uses_zero_to_last_playback(self):
        expected, observed = fixture()
        first = 0.0416666679084301
        ends = dict(Idle=2.0416667461395264, Walk=1.0416666269302368,
                    Attack=1.0416666269302368, Hurt=1.0416666269302368,
                    Mine=1.5416666269302368, Trade=2.0416667461395264,
                    Repair=1.5416666269302368)
        for name, last in ends.items():
            expected["clips"][name] = dict(first_key_s=first, last_key_s=last,
                                          span_s=last-first, playback_origin_s=0.0)
        for row in observed["clips"]:
            row["length_s"] = ends[row["source_name"]]
        result = qualify(expected, observed)
        for name, timeline in result["clip_timelines"].items():
            self.assertEqual(timeline["first_key_s"], first)
            self.assertEqual(timeline["span_s"], ends[name]-first)
            self.assertEqual(timeline["playback_origin_s"], 0.0)
            self.assertEqual(timeline["playback_length_s"], ends[name])
            self.assertEqual(timeline["native_length_s"], ends[name])
        # The unchanged tolerance applies to playback, in both directions.
        self.assertEqual(CLIP_LENGTH_TOLERANCE_S, 1.0/30.0 + 0.0001)
        for sign in (-1, 1):
            bad = copy.deepcopy(observed)
            bad["clips"][0]["length_s"] += sign * (CLIP_LENGTH_TOLERANCE_S + 0.000001)
            with self.subTest(sign=sign), self.assertRaisesRegex(ValueError, "clip length differs"):
                qualify(expected, bad)

    def test_missing_inconsistent_or_invalid_source_timelines_fail(self):
        for field in ("first_key_s", "last_key_s", "span_s", "playback_origin_s"):
            with self.subTest(missing=field):
                self.assert_rejected(mutate_expected=lambda e: e["clips"]["Idle"].pop(field))
            for value in (float("nan"), float("inf"), -float("inf"), True, "0", None, 10**400):
                with self.subTest(field=field, value=str(value)):
                    self.assert_rejected(mutate_expected=lambda e: e["clips"]["Idle"].update({field: value}))
        for field, value in (("first_key_s", -0.1), ("first_key_s", 2.0),
                             ("last_key_s", 0.0), ("last_key_s", -1.0),
                             ("span_s", 1.0), ("playback_origin_s", -0.1),
                             ("playback_origin_s", 0.0416666679084301)):
            with self.subTest(field=field, value=value):
                self.assert_rejected(mutate_expected=lambda e: e["clips"]["Idle"].update({field: value}))
        # Span-only historical packets require explicit re-preparation.
        self.assert_rejected(mutate_expected=lambda e: e["clips"].update(
            Idle={"span_s": e["clips"]["Idle"]["span_s"]}))

    def test_missing_extra_duplicate_and_disallowed_objects_fail(self):
        cases = {
            "missing_mesh": lambda o: o["objects"].pop(0),
            "missing_skeleton": lambda o: o["objects"].pop(1),
            "missing_clip": lambda o: o["objects"].pop(2),
            "duplicate_path": lambda o: o["objects"].append(dict(o["objects"][0])),
            "case_collision": lambda o: o["objects"].append(
                {"path": o["objects"][0]["path"].replace("Worker.Worker", "WORKER.WORKER"),
                 "class": "Material"}),
            "extra_mesh": lambda o: o["objects"].append(
                {"path": o["mesh_path"] + "Extra", "class": "SkeletalMesh"}),
            "extra_skeleton": lambda o: o["objects"].append(
                {"path": o["skeleton_path"] + "Extra", "class": "Skeleton"}),
            "extra_clip": lambda o: o["objects"].append(
                {"path": o["mesh_path"] + "Extra", "class": "AnimSequence"}),
            "second_physics": lambda o: o["objects"].append(
                {"path": o["mesh_path"] + "Extra", "class": "PhysicsAsset"}),
            "static_mesh": lambda o: o["objects"][0].update({"class": "StaticMesh"}),
        }
        for name, mutate in cases.items():
            with self.subTest(name=name):
                self.assert_rejected(mutate_observed=mutate)

    def test_path_escape_wrong_namespace_and_malformed_paths_fail(self):
        paths = (
            "/Game/Elsewhere/Mesh.Mesh", "/Game/Daedalus/Art/Workers/ProspectorQualificationR1Extra/M.M",
            "/Game/Daedalus/Art/Workers/ProspectorQualificationR1/../Else/M.M",
            "/Game/Daedalus/Art/Workers/ProspectorQualificationR1//M.M",
            "/Game/Daedalus/Art/Workers/ProspectorQualificationR1/./M.M",
            "/Game/Daedalus/Art/Workers/ProspectorQualificationR1/Bad\\M.M",
            "/Game/Daedalus/Art/Workers/ProspectorQualificationR1/M\n.M", "", None,
        )
        for path in paths:
            with self.subTest(path=path):
                self.assert_rejected(mutate_observed=lambda o: o["objects"][0].update({"path": path}))

    def test_mesh_and_clip_skeleton_and_object_mapping_failures(self):
        cases = {
            "mesh_identity": lambda o: o.update(mesh_path=o["skeleton_path"]),
            "skeleton_identity": lambda o: o.update(skeleton_path=o["mesh_path"]),
            "mesh_skeleton": lambda o: o.update(mesh_skeleton_path=o["mesh_path"]),
            "clip_skeleton": lambda o: o["clips"][0].update(skeleton_path=o["mesh_path"]),
            "clip_not_imported": lambda o: o["clips"][0].update(path=o["mesh_path"] + "Absent"),
            "clip_reuses_path": lambda o: o["clips"][1].update(path=o["clips"][0]["path"]),
        }
        for name, mutate in cases.items():
            with self.subTest(name=name):
                self.assert_rejected(mutate_observed=mutate)

    def test_exact_seven_source_clip_names_required_on_both_sides(self):
        self.assert_rejected(mutate_expected=lambda e: e["clips"].pop("Mine"))
        self.assert_rejected(mutate_expected=lambda e: e["clips"].update(Dance={"span_s": 2.0}))
        self.assert_rejected(mutate_observed=lambda o: o["clips"].pop())
        self.assert_rejected(mutate_observed=lambda o: o["clips"].append(dict(o["clips"][0])))
        self.assert_rejected(mutate_observed=lambda o: o["clips"][0].update(source_name="Dance"))
        self.assert_rejected(mutate_observed=lambda o: o["clips"][0].update(source_name="Walk"))

    def test_invalid_lengths_and_spans_fail(self):
        for value in (float("nan"), float("inf"), -float("inf"), 0, -1, True, "2.0", None, 10 ** 400):
            with self.subTest(value=str(value)):
                self.assert_rejected(mutate_expected=lambda e: e["clips"]["Idle"].update(span_s=value))
                self.assert_rejected(mutate_observed=lambda o: o["clips"][0].update(length_s=value))
        for sign in (-1, 1):
            self.assert_rejected(mutate_observed=lambda o: o["clips"][0].update(
                length_s=o["clips"][0]["length_s"] + sign * (CLIP_LENGTH_TOLERANCE_S + 0.000001)))

    def test_exact_bone_count_unique_names_and_parent_tree_required(self):
        cases = {
            "missing": lambda e: e["bones"].pop(),
            "extra": lambda e: e["bones"].append(dict(e["bones"][0])),
            "duplicate_source": lambda e: e["bones"][1].update(source_name="rig:root"),
            "duplicate_native": lambda e: e["bones"][1].update(native_name="rig_root"),
            "case_native": lambda e: e["bones"][1].update(native_name="RIG_ROOT"),
            "empty_native": lambda e: e["bones"][1].update(native_name=""),
            "missing_parent": lambda e: e["bones"][1].pop("parent"),
            "unknown_parent": lambda e: e["bones"][1].update(parent="unknown"),
            "distant_unknown_parent": lambda e: e["bones"][13].update(parent="unknown"),
            "second_root": lambda e: e["bones"][1].update(parent=None),
            "self_cycle": lambda e: e["bones"][1].update(parent="rig_joint1"),
            "disconnected_cycle": lambda e: e["bones"][1].update(parent="rig_joint2"),
            "no_root": lambda e: e["bones"][0].update(parent="rig_joint13"),
        }
        for name, mutate in cases.items():
            with self.subTest(name=name):
                self.assert_rejected(mutate_expected=mutate)

    def test_observed_bone_bijection_parent_and_all_clip_presence_failures(self):
        cases = {
            "missing": lambda o: o["bones"].pop(),
            "extra": lambda o: o["bones"].append(dict(o["bones"][0])),
            "duplicate_source": lambda o: o["bones"][1].update(source_name="rig:root"),
            "extra_source": lambda o: o["bones"][1].update(source_name="unknown"),
            "wrong_native": lambda o: o["bones"][1].update(native_name="rig_root"),
            "wrong_parent": lambda o: o["bones"][2].update(parent="rig_root"),
            "root_parent": lambda o: o["bones"][0].update(parent="rig_joint1"),
            "missing_parent": lambda o: o["bones"][0].pop("parent"),
            "absent_clip": lambda o: o["bones"][0].update(exists_in_all_clips=False),
            "truthy_not_true": lambda o: o["bones"][0].update(exists_in_all_clips=1),
            "missing_presence": lambda o: o["bones"][0].pop("exists_in_all_clips"),
        }
        for name, mutate in cases.items():
            with self.subTest(name=name):
                self.assert_rejected(mutate_observed=mutate)

    def test_any_saved_file_or_missing_save_witness_fails(self):
        self.assert_rejected(mutate_observed=lambda o: o.update(saved_files=["Worker.uasset"]))
        self.assert_rejected(mutate_observed=lambda o: o.update(saved_files=None))
        self.assert_rejected(mutate_observed=lambda o: o.pop("saved_files"))

    def test_malformed_required_json_shapes_raise_value_error(self):
        for field in ("objects", "clips", "bones"):
            for value in (None, {}, "not a list"):
                with self.subTest(field=field, value=value):
                    self.assert_rejected(mutate_observed=lambda o: o.update({field: value}))
        for field in ("asset_id", "root", "clips", "bones"):
            with self.subTest(missing_expected=field):
                self.assert_rejected(mutate_expected=lambda e: e.pop(field))
        for expected, observed in ((None, {}), ({}, None), ([], [])):
            with self.assertRaises(ValueError):
                qualify(expected, observed)


if __name__ == "__main__":
    unittest.main()
