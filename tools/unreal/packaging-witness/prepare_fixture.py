#!/usr/bin/env python3
"""Copy the exact private two-object fixture into a NEW Development test project.

Standard library only. No process, network, environment/credential, editor or
source-project writes. Asset/package inputs come from the retained registry read.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import zlib

MAP = "/Game/CodexToolEvaluation/HLODMinimal/R1/HLOD_Fixture"
PROJECT = "DaedalusPackageWitness"
CANONICAL_SHA = "8bde83421c0c7c0c1913cf6c9a9c6614e089ca78b84479a3b5e8ab9d869edfe7"


def pin(path):
    raw = path.read_bytes()
    return {"path": str(path), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def prepare(plugin, content, closure_path, output):
    plugin, content, output = plugin.resolve(), content.resolve(), output.resolve()
    if output.exists() or output.is_relative_to(plugin) or output.is_relative_to(content):
        raise ValueError("Require a new owned output outside source plugin/content")
    raw_closure = json.loads(closure_path.read_bytes())
    result = raw_closure["result"]
    if result.get("preserved") is not True or not result["action"].get("normal_close_ready"):
        raise ValueError("Known preserved, clean native closure required")
    closure = result["action"]["closure"]
    names = [row["package"] for row in closure]
    if len(names) != len(set(names)) or not 1 <= len(names) <= 8 or names[0] != MAP:
        raise ValueError("Exact private map and at most eight unique game packages required")
    expected_prefixes = ("/Game/CodexToolEvaluation/HLODMinimal/R1/",
                         "/Game/CodexToolEvaluation/LODSourceRoundtrip/RasterR2/",
                         "/Game/Daedalus/Art/Prop/Prop_Realm_Cave_Floor/")
    source_assets = []
    for name in names:
        if not name.startswith(expected_prefixes) or any(x in name for x in ("..", "\\", ":")):
            raise ValueError("Package outside the bounded fixture closure")
        relative = Path(name.removeprefix("/Game/"))
        base = content / relative
        asset = base.with_suffix(".umap" if name == MAP else ".uasset")
        if not asset.is_file() or asset.is_symlink() or not asset.resolve().is_relative_to(content):
            raise ValueError("Exact saved package missing or unsafe")
        source_assets.append(asset)
        source_assets += [base.with_suffix(ext) for ext in (".uexp", ".ubulk") if base.with_suffix(ext).is_file()]
    if sum(x.stat().st_size for x in source_assets) > 100 * 1024**2:
        raise ValueError("Private game-asset copy exceeds100MiB")
    canonical = plugin / "Build/AcceptedContracts/native_validation_result_snapshot.h"
    if pin(canonical)["sha256"] != CANONICAL_SHA:
        raise ValueError("Canonical contract does not match the accepted bytes")
    source_files = [p for p in (plugin / "Source").rglob("*") if p.is_file()]
    if any(p.is_symlink() for p in source_files) or sum(p.stat().st_size for p in source_files) > 10 * 1024**2:
        raise ValueError("Unexpected plugin-source copy size or link")
    payload_files = []
    for folder, suffix in (("Inventory", ".dic"), ("Casts", ".dcs"), ("Realm", ".drr")):
        files = sorted((plugin / "Content" / folder).glob("*" + suffix))
        if not files: raise ValueError("Required runtime payload family absent")
        payload_files.extend(files)
    payload_files.append(plugin / "Content/YTM/found_tunes.csv")
    if any(not p.is_file() or p.is_symlink() for p in payload_files):
        raise ValueError("Runtime payload absent or unsafe")
    expected = [next(p for p in payload_files if p.parent.name == folder)
                for folder in ("Inventory", "Casts", "Realm", "YTM")]
    if any(p.stat().st_size > 65536 for p in expected):
        raise ValueError("Runtime witness payload cap exceeded")
    before = [pin(x) for x in source_assets + source_files + payload_files + [canonical, plugin / "DaedalusLink.uplugin"]]
    output.mkdir(parents=True)
    copied = []
    def copy(src, dst):
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
        a, b = pin(src), pin(dst)
        if (a["bytes"], a["sha256"]) != (b["bytes"], b["sha256"]):
            raise ValueError("Copied bytes differ")
        copied.append({"source": a, "copy": b})
    target_plugin = output / "Plugins/DaedalusLink"
    for src in source_files:
        copy(src, target_plugin / src.relative_to(plugin))
    for src in payload_files + [canonical, plugin / "DaedalusLink.uplugin"]:
        copy(src, target_plugin / src.relative_to(plugin))
    for src in source_assets:
        copy(src, output / "Content" / src.relative_to(content))
    templates = Path(__file__).resolve().parent
    src_dir = output / "Source" / PROJECT
    copy(templates / (PROJECT + ".Target.cs"), output / "Source" / (PROJECT + ".Target.cs"))
    copy(templates / (PROJECT + "Editor.Target.cs"), output / "Source" / (PROJECT + "Editor.Target.cs"))
    copy(templates / (PROJECT + ".Build.cs"), src_dir / (PROJECT + ".Build.cs"))
    copy(templates / (PROJECT + ".cpp"), src_dir / "Private" / (PROJECT + ".cpp"))
    expectations = []
    header = "#pragma once\n#include \"CoreMinimal.h\"\nstruct FFixturePayloadExpectation { const TCHAR* Relative; int32 Size; uint32 Crc; };\nstatic const FFixturePayloadExpectation GFixturePayloads[] = {\n"
    for src in expected:
        data = src.read_bytes(); relative = src.relative_to(plugin / "Content").as_posix()
        crc = zlib.crc32(data)
        header += '    {TEXT("' + relative + '"), ' + str(len(data)) + ', ' + str(crc) + 'u},\n'
        expectations.append({"relative": relative, **pin(src), "crc32_diagnostic_not_crypto": crc})
    header += "};\n"
    (src_dir / "Private/FixturePayloadExpectations.h").write_bytes(header.encode())
    project = {"FileVersion": 3, "EngineAssociation": "5.8", "Description": "Owned minimal Development packaging witness; no production release.",
        "Modules": [{"Name": PROJECT, "Type": "Runtime", "LoadingPhase": "Default"}],
        "Plugins": [{"Name": x, "Enabled": True} for x in ("DaedalusLink", "ProceduralMeshComponent", "EnhancedInput", "RawInput", "InterchangeAssets")]
                   + [{"Name": x, "Enabled": False} for x in ("PythonScriptPlugin", "ClaudeUnrealBridge", "AllToolsets", "AndroidFileServer")]}
    (output / (PROJECT + ".uproject")).write_bytes((json.dumps(project, indent=2) + "\n").encode())
    config = output / "Config"; config.mkdir()
    engine = "[/Script/EngineSettings.GameMapsSettings]\nGameDefaultMap=" + MAP + ".HLOD_Fixture\nEditorStartupMap=" + MAP + ".HLOD_Fixture\n\n[/Script/WindowsTargetPlatform.WindowsTargetSettings]\nDefaultGraphicsRHI=DefaultGraphicsRHI_DX11\n-D3D12TargetedShaderFormats=PCD3D_SM6\n+D3D11TargetedShaderFormats=PCD3D_SM5\n"
    (config / "DefaultEngine.ini").write_bytes(engine.encode())
    (config / "DefaultGame.ini").write_bytes(b"[/Script/UnrealEd.ProjectPackagingSettings]\nbCookAll=False\nbUsePakFile=True\nbUseIoStore=False\nbUseZenStore=False\nbShareMaterialShaderCode=True\nFullRebuild=False\n")
    if before != [pin(x) for x in source_assets + source_files + payload_files + [canonical, plugin / "DaedalusLink.uplugin"]]:
        raise ValueError("Source changed during fixture preparation")
    manifest = {"schema": "daedalus.minimal-development-package-fixture.v1", "project": str(output / (PROJECT + ".uproject")),
        "map": MAP, "game_packages": names, "closure": pin(closure_path), "copies": copied, "payload_expectations": expectations,
        "canonical_contract_sha256": CANONICAL_SHA, "source_writes": 0, "process_or_network_calls": 0,
        "original_project_config_copied": False, "configuration": "Development", "shipping_or_release_accepted": False}
    (output / "fixture-source-manifest.json").write_bytes((json.dumps(manifest, indent=2) + "\n").encode())
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plugin", type=Path, required=True)
    parser.add_argument("--content", type=Path, required=True)
    parser.add_argument("--closure", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = prepare(args.plugin, args.content, args.closure, args.output)
    print(json.dumps({"project": result["project"], "game_packages": len(result["game_packages"]), "copied_files": len(result["copies"]), "configuration": "Development"}))
