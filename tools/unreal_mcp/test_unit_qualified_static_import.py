# SPDX-License-Identifier: MIT
"""Offline unit-import regressions using a minimal, fully mocked native API."""
import hashlib
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from tools.unreal_mcp import unit_qualified_static_import as adapter


BINARY_HEADER = b"Kaydara FBX Binary  \x00\x1a\x00"
ASCII_HEADER = b"; FBX 7.4.0 project file\n"
FOLDER = "/Game/CodexToolEvaluation/UnitQualified"
ASSET = "SM_UnitFixture"


class NativeFixture:
    """Only the constructors/constants needed by the existing import wrapper."""

    def __init__(self):
        self.static_type = object()
        self.wrong_type = object()
        self.mesh_options = SimpleNamespace(
            convert_scene=False,
            convert_scene_unit=False,
            import_uniform_scale=100.0,
            combine_meshes=False,
        )
        self.options = SimpleNamespace(
            automated_import_should_detect_type=True,
            import_mesh=False,
            import_as_skeletal=True,
            mesh_type_to_import=self.wrong_type,
            original_import_type=self.wrong_type,
            import_materials=True,
            import_textures=True,
            import_animations=True,
            static_mesh_import_data=self.mesh_options,
        )
        self.factory = object()
        self.unreal = SimpleNamespace(
            FbxImportUI=MagicMock(return_value=self.options),
            FbxFactory=MagicMock(return_value=self.factory),
            FBXImportType=SimpleNamespace(FBXIT_STATIC_MESH=self.static_type),
        )
        self.result = [object()]
        self.import_asset = MagicMock(return_value=self.result)


class UnitQualifiedStaticImportTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.source = Path(self.temporary.name) / "unit-fixture.fbx"
        self.source.write_bytes(ASCII_HEADER + b"native parser validates the full FBX body\n")

    def import_with_fixture(self, source=None, fixture=None, **kwargs):
        fixture = fixture if fixture is not None else NativeFixture()
        source = self.source if source is None else source
        with patch.object(adapter, "_native_api", return_value=(
                fixture.unreal, fixture.import_asset)) as native:
            result = adapter.import_file(FOLDER, ASSET, str(source), **kwargs)
        native.assert_called_once_with()
        return result, fixture

    def assert_original_static_flags(self, fixture, import_materials=False,
                                     import_textures=False, combine_meshes=True):
        self.assertEqual(vars(fixture.options), {
            "automated_import_should_detect_type": False,
            "import_mesh": True,
            "import_as_skeletal": False,
            "mesh_type_to_import": fixture.static_type,
            "original_import_type": fixture.static_type,
            "import_materials": import_materials,
            "import_textures": import_textures,
            "import_animations": False,
            "static_mesh_import_data": fixture.mesh_options,
        })
        self.assertEqual(vars(fixture.mesh_options), {
            "convert_scene": True,
            "convert_scene_unit": True,
            "import_uniform_scale": 1.0,
            "combine_meshes": combine_meshes,
        })

    def test_explicit_units_override_false_and_100_defaults_without_double_scaling(self):
        fixture = NativeFixture()
        self.assertIs(fixture.mesh_options.convert_scene_unit, False)
        self.assertEqual(fixture.mesh_options.import_uniform_scale, 100.0)
        _, fixture = self.import_with_fixture(fixture=fixture)
        self.assertIs(fixture.mesh_options.convert_scene, True)
        self.assertIs(fixture.mesh_options.convert_scene_unit, True)
        self.assertEqual(fixture.mesh_options.import_uniform_scale, 1.0)
        self.assert_original_static_flags(fixture)

    def test_shared_helper_receives_exact_options_factory_and_absolute_input(self):
        result, fixture = self.import_with_fixture()
        fixture.unreal.FbxImportUI.assert_called_once_with()
        fixture.unreal.FbxFactory.assert_called_once_with()
        fixture.import_asset.assert_called_once_with(
            FOLDER, ASSET, str(self.source.resolve()),
            options=fixture.options, factory=fixture.factory)
        self.assertIs(result, fixture.result)

    def test_original_material_texture_and_combine_options_are_preserved(self):
        for materials, textures, combine in ((False, False, False), (True, False, True),
                                              (True, True, False), (False, True, True)):
            with self.subTest(materials=materials, textures=textures, combine=combine):
                _, fixture = self.import_with_fixture(
                    import_materials=materials, import_textures=textures, combine_meshes=combine)
                self.assert_original_static_flags(fixture, materials, textures, combine)

    def test_source_bytes_and_hash_are_unchanged_after_import(self):
        before = self.source.read_bytes()
        digest = hashlib.sha256(before).hexdigest()
        self.import_with_fixture()
        self.assertEqual(self.source.read_bytes(), before)
        self.assertEqual(hashlib.sha256(self.source.read_bytes()).hexdigest(), digest)

    def test_binary_identification_is_accepted_without_requiring_a_synthetic_body(self):
        self.source.write_bytes(BINARY_HEADER + b"\x00\x01native-body")
        _, fixture = self.import_with_fixture()
        fixture.import_asset.assert_called_once()

    def test_ascii_identification_allows_leading_whitespace(self):
        self.source.write_bytes(b" \t\r\n" + ASCII_HEADER + b"native-body")
        _, fixture = self.import_with_fixture()
        fixture.import_asset.assert_called_once()

    def test_fbx_extension_is_case_insensitive(self):
        source = self.source.with_suffix(".FBX")
        source.write_bytes(ASCII_HEADER)
        _, fixture = self.import_with_fixture(source=source)
        fixture.import_asset.assert_called_once()

    def test_missing_file_is_rejected_before_extension_or_native_api_loading(self):
        source = Path(self.temporary.name) / "missing.obj"
        with patch.object(adapter, "_native_api") as native:
            with self.assertRaises(FileNotFoundError):
                adapter.import_file(FOLDER, ASSET, str(source))
        native.assert_not_called()

    def test_directory_is_not_accepted_as_an_fbx_file(self):
        source = Path(self.temporary.name) / "directory.fbx"
        source.mkdir()
        with patch.object(adapter, "_native_api") as native:
            with self.assertRaises(FileNotFoundError):
                adapter.import_file(FOLDER, ASSET, str(source))
        native.assert_not_called()

    def test_wrong_extension_is_rejected_before_native_api_loading(self):
        source = self.source.with_suffix(".obj")
        source.write_bytes(ASCII_HEADER)
        with patch.object(adapter, "_native_api") as native:
            with self.assertRaises(ValueError):
                adapter.import_file(FOLDER, ASSET, str(source))
        native.assert_not_called()

    def test_unrecognized_or_empty_fbx_is_rejected_before_native_api_loading(self):
        for content in (b"", b"not an FBX", b"; fbx 7.4", b"Kaydara FBX Binary",
                        b" " * 256 + ASCII_HEADER):
            with self.subTest(content=content):
                self.source.write_bytes(content)
                with patch.object(adapter, "_native_api") as native:
                    with self.assertRaises(ValueError):
                        adapter.import_file(FOLDER, ASSET, str(self.source))
                native.assert_not_called()
                self.assertEqual(self.source.read_bytes(), content)

    def test_shared_helper_error_propagates_without_retry_or_source_change(self):
        before = self.source.read_bytes()
        fixture = NativeFixture()
        failure = RuntimeError("native FBX body validation failed")
        fixture.import_asset.side_effect = failure
        with patch.object(adapter, "_native_api", return_value=(
                fixture.unreal, fixture.import_asset)):
            with self.assertRaises(RuntimeError) as raised:
                adapter.import_file(FOLDER, ASSET, str(self.source))
        self.assertIs(raised.exception, failure)
        fixture.import_asset.assert_called_once()
        self.assertEqual(self.source.read_bytes(), before)

    def test_native_api_loading_error_propagates_without_import(self):
        failure = ImportError("official native API unavailable")
        with patch.object(adapter, "_native_api", side_effect=failure) as native:
            with self.assertRaises(ImportError) as raised:
                adapter.import_file(FOLDER, ASSET, str(self.source))
        self.assertIs(raised.exception, failure)
        native.assert_called_once_with()

    def test_options_constructor_error_does_not_reach_factory_or_shared_helper(self):
        fixture = NativeFixture()
        failure = RuntimeError("options unavailable")
        fixture.unreal.FbxImportUI.side_effect = failure
        with patch.object(adapter, "_native_api", return_value=(
                fixture.unreal, fixture.import_asset)):
            with self.assertRaises(RuntimeError) as raised:
                adapter.import_file(FOLDER, ASSET, str(self.source))
        self.assertIs(raised.exception, failure)
        fixture.unreal.FbxFactory.assert_not_called()
        fixture.import_asset.assert_not_called()

    def test_factory_constructor_error_does_not_reach_shared_helper(self):
        fixture = NativeFixture()
        failure = RuntimeError("factory unavailable")
        fixture.unreal.FbxFactory.side_effect = failure
        with patch.object(adapter, "_native_api", return_value=(
                fixture.unreal, fixture.import_asset)):
            with self.assertRaises(RuntimeError) as raised:
                adapter.import_file(FOLDER, ASSET, str(self.source))
        self.assertIs(raised.exception, failure)
        fixture.import_asset.assert_not_called()


if __name__ == "__main__":
    unittest.main()
