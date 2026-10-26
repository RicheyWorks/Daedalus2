# SPDX-License-Identifier: MIT
"""Source-only realm integration checks; no compiler, editor, network or Git calls."""
import json
from pathlib import Path
import re
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
MODULE = ROOT / "engines/unreal/DaedalusLink/Source/DaedalusLink"
MANIFEST = ROOT / "docs/realms/dependency-reconciliation-20261026.json"
INCLUDE = re.compile(r'^\s*#\s*include\s*"([^"]+)"', re.MULTILINE)


def project_closure(module, roots):
    """Resolve quoted Daedalus headers, including private helpers, without UHT.

    Engine/system and generated headers are outside this source availability
    check. All branches are inspected; this is not a C++ preprocessor or build.
    """
    found = set()
    pending = [module / root for root in roots]
    while pending:
        path = pending.pop()
        if path in found:
            continue
        if not path.is_file():
            raise AssertionError("Missing source: " + str(path.relative_to(module)))
        found.add(path)
        source = re.sub(r"/\*.*?\*/", "", path.read_text(encoding="utf-8"), flags=re.DOTALL)
        for name in INCLUDE.findall(source):
            if not Path(name).name.startswith("Daedalus") or name.endswith(".generated.h"):
                continue
            candidates = {p for p in (path.parent / name, module / "Public" / name,
                                      module / "Private" / name) if p.is_file()}
            if len(candidates) != 1:
                raise AssertionError("Unresolved project include %s from %s" %
                                     (name, path.relative_to(module)))
            pending.extend(candidates)
    return {path.relative_to(module).as_posix() for path in found}


class RealmDependencies(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(MANIFEST.read_text(encoding="utf-8"))
        cls.packets = {p["id"]: p for p in cls.data["packets"]}

    def closure(self, packet):
        return project_closure(MODULE, self.packets[packet]["source_roots"])

    def test_inventory_preserves_distinct_source_and_integrated_identities(self):
        self.assertEqual(self.data["schema"], "realm-dependency-reconciliation/v1")
        self.assertEqual(len(self.packets), 16, "The audited selection contains sixteen packets")
        self.assertEqual(len(self.packets), len(self.data["packets"]))
        for field in ("source_commit", "integrated_commit"):
            values = [p[field] for p in self.packets.values()]
            self.assertEqual(len(values), len(set(values)))
        for packet in self.packets.values():
            with self.subTest(packet=packet["id"]):
                for field in ("source_commit", "integrated_commit", "merge_commit", "stable_patch_id"):
                    self.assertRegex(packet[field], r"^[0-9a-f]{40}$")
                self.assertNotEqual(packet["source_commit"], packet["integrated_commit"])

    def test_packet_prerequisites_are_known_and_acyclic(self):
        def visit(name, active):
            self.assertIn(name, self.packets)
            self.assertNotIn(name, active, "Cyclic packet prerequisite: " + name)
            for dependency in self.packets[name]["requires_packets"]:
                visit(dependency, active | {name})
        for name in self.packets:
            visit(name, set())

    def test_every_selected_source_has_its_project_include_closure(self):
        for packet in self.packets:
            with self.subTest(packet=packet):
                self.assertTrue(self.closure(packet))

    def test_bridge_walk_has_the_print_snapshot_api_without_trail_or_writer(self):
        paths = self.closure("bridge_walk")
        self.assertIn("Public/DaedalusBricksBridgeCore.h", paths)
        self.assertIn("Public/DaedalusBricksBridgeWorkshop.h", paths)
        self.assertNotIn("Public/DaedalusBricksBlueprintTrail.h", paths)
        self.assertNotIn("Private/DaedalusLocalSvgFiles.h", paths)
        header = (MODULE / "Public/DaedalusBricksBridgeWorkshop.h").read_text(encoding="utf-8")
        caller = (MODULE / "Private/DaedalusBricksBridgeWalk.cpp").read_text(encoding="utf-8")
        self.assertIn("CopyBlueprintSnapshot(", header)
        self.assertIn("CopyBlueprintSnapshot(", caller)
        self.assertIn("blueprint_print", self.packets["bridge_walk"]["requires_packets"])

    def test_prints_need_trail_readiness_apis_but_no_trail_actor(self):
        paths = self.closure("blueprint_print")
        self.assertIn("Public/DaedalusBricksBridgeCore.h", paths)
        self.assertIn("Public/DaedalusBricksSkylineCore.h", paths)
        self.assertNotIn("Public/DaedalusBricksBlueprintTrail.h", paths)
        self.assertEqual(self.packets["blueprint_print"]["requires_packets"],
                         ["bridge", "skyline", "trail"])

    def test_gallery_preserves_study_reader_and_palette_independence(self):
        self.assertEqual(self.packets["artist_tools"]["requires_packets"], ["studio", "study"])
        self.assertEqual(self.packets["rack"]["requires_packets"],
                         ["studio", "study", "artist_tools"])
        self.assertEqual(self.packets["palette"]["requires_packets"],
                         ["studio", "study", "artist_tools"])
        self.assertNotIn("rack", self.packets["palette"]["requires_packets"])
        self.assertIn("Private/DaedalusGalleryMotifNative.h", self.closure("artist_tools"))

    def test_storyboard_and_blueprint_keep_the_complete_shared_writer(self):
        paths = self.closure("storyboard")
        for path in ("Private/DaedalusLocalSvgFiles.h", "Private/DaedalusLocalSvgFiles.cpp",
                     "Private/DaedalusBricksBlueprintPress.cpp",
                     "Private/DaedalusGalleryMotifStoryboardPress.cpp"):
            self.assertIn(path, paths)
        for name in ("DaedalusBricksBlueprintPress.cpp", "DaedalusGalleryMotifStoryboardPress.cpp"):
            self.assertIn("Private/DaedalusLocalSvgFiles.h",
                          project_closure(MODULE, ["Private/" + name]))
        self.assertIn("Public/DaedalusGalleryMotifFlipbookCore.h", paths)

    def test_guide_has_no_flipbook_runtime_dependency(self):
        self.assertFalse(any("Flipbook" in path for path in self.closure("guide")))
        self.assertNotIn("flipbook", self.packets["guide"]["requires_packets"])

    def test_spectrum_and_bridge_are_independent_modules(self):
        self.assertFalse(any("Bricks" in path for path in self.closure("spectrum")))
        self.assertFalse(any("Gallery" in path for path in self.closure("bridge")))

    def test_mail_practice_has_rules_and_rng_without_host_session_or_board(self):
        paths = self.closure("mail_practice")
        self.assertIn("Public/DaedalusMailRouteCore.h", paths)
        self.assertIn("Public/DaedalusTemperForgeCore.h", paths)
        self.assertNotIn("Public/DaedalusMailRouteSession.h", paths)
        self.assertNotIn("Public/DaedalusMailRouteBoard.h", paths)
        self.assertEqual(self.packets["mail_practice"]["requires_packets"], ["mail_core"])

    def test_source_reconciliation_does_not_promote_native_acceptance(self):
        self.assertEqual(self.data["evidence_kind"], "source_reconciliation")
        self.assertIs(self.data["native_acceptance_established"], False)
        self.assertEqual(self.data["integration_owner"], "unreal-epic-boss")
        self.assertEqual(self.data["native_owner"], "codex-play-guard")


class IncludeResolverRegressions(unittest.TestCase):
    def module(self, root, files):
        for path, text in files.items():
            target = root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text, encoding="utf-8")
        return root

    def test_missing_transitive_header_fails_with_the_actual_parent(self):
        with tempfile.TemporaryDirectory() as temp:
            root = self.module(Path(temp), {
                "Private/DaedalusEntry.cpp": '#include "DaedalusRule.h"\n',
                "Public/DaedalusRule.h": '#include "DaedalusMissing.h"\n'})
            with self.assertRaisesRegex(AssertionError, "DaedalusMissing.h from Public[/\\\\]DaedalusRule.h"):
                project_closure(root, ["Private/DaedalusEntry.cpp"])

    def test_engine_and_generated_headers_are_outside_this_check(self):
        with tempfile.TemporaryDirectory() as temp:
            root = self.module(Path(temp), {"Public/DaedalusRule.h":
                '#include "CoreMinimal.h"\n#include "DaedalusRule.generated.h"\n'})
            self.assertEqual(project_closure(root, ["Public/DaedalusRule.h"]),
                             {"Public/DaedalusRule.h"})

    def test_private_helper_and_include_cycles_are_resolved_once(self):
        with tempfile.TemporaryDirectory() as temp:
            root = self.module(Path(temp), {
                "Private/DaedalusEntry.cpp": '#include "DaedalusHelper.h"\n',
                "Private/DaedalusHelper.h": '#include "DaedalusRule.h"\n',
                "Public/DaedalusRule.h": '#include "DaedalusHelper.h"\n'})
            self.assertEqual(len(project_closure(root, ["Private/DaedalusEntry.cpp"])), 3)


if __name__ == "__main__":
    unittest.main()
