// SPDX-License-Identifier: MIT

using UnrealBuildTool;
using System.IO;

public class DaedalusLink : ModuleRules
{
	public DaedalusLink(ReadOnlyTargetRules Target) : base(Target)
	{
		PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;

		PublicDependencyModuleNames.AddRange(new string[]
		{
			"Core",
			"CoreUObject",
			"Engine",
			"ProceduralMeshComponent",
			"InputCore",
			"EnhancedInput",
			"WebBrowser",
		});

		PrivateDependencyModuleNames.AddRange(new string[]
		{
			"AssetRegistry",
			"HTTP",
			"ImageCore",
			"RHI",
			"Json",
			"Slate",
			"SlateCore",
			"WebSockets",
		});

		if (Target.bBuildEditor)
		{
			PrivateDependencyModuleNames.AddRange(new string[]
			{
				"DataValidation", "UnrealEd", "LevelEditor", "SlateInspectorToolset",
				"AnimationBlueprintLibrary", "InterchangeCore", "InterchangeEngine",
				"InterchangeFactoryNodes", "InterchangeNodes", "InterchangePipelines",
				"InterchangeImport", "InterchangeCommonParser", "PCG", "HierarchicalLODUtilities",
			});
			// One canonical serializer in the repository. setup-unreal.ps1 stages
			// those exact bytes for projects whose plugin lives outside the repo.
			string CanonicalContracts = Path.GetFullPath(Path.Combine(PluginDirectory, "../../../tools/unreal_mcp"));
			string StagedContracts = Path.Combine(PluginDirectory, "Build", "AcceptedContracts");
			string Contracts = File.Exists(Path.Combine(CanonicalContracts, "native_validation_result_snapshot.h"))
				? CanonicalContracts : StagedContracts;
			if (!File.Exists(Path.Combine(Contracts, "native_validation_result_snapshot.h")))
			{
				throw new BuildException("Missing canonical validation contract. Stage the exact tools/unreal_mcp/native_validation_result_snapshot.h with setup-unreal.ps1.");
			}
			PrivateIncludePaths.Add(Contracts);
		}

		// A bounded direct-loopback client must disable HTTP redirects before sending credentials.
		AddEngineThirdPartyPrivateStaticDependencies(Target, "libcurl", "nghttp2", "OpenSSL", "zlib");

		// Runtime readers use FFileHelper: these custom formats must survive cooking/staging.
		// Keep the patterns in the receipt so newly added catalogs/casts are included too.
		RuntimeDependencies.Add(Path.Combine(PluginDirectory, "Content", "Inventory", "*.dic"), StagedFileType.UFS);
		RuntimeDependencies.Add(Path.Combine(PluginDirectory, "Content", "Casts", "*.dcs"), StagedFileType.UFS);
		RuntimeDependencies.Add(Path.Combine(PluginDirectory, "Content", "Realm", "*.drr"), StagedFileType.UFS);
		// G33 Seed-Song Spring tunes (ADaedalusSeedSong reads them at BeginPlay).
		RuntimeDependencies.Add(Path.Combine(PluginDirectory, "Content", "YTM", "found_tunes.csv"), StagedFileType.UFS);
		// Sprite packs are optional (procedural sprites remain the existing fallback).
		string RealmDirectory = Path.Combine(PluginDirectory, "Content", "Realm");
		if (Directory.Exists(RealmDirectory))
		{
			foreach (string Pack in Directory.GetFiles(RealmDirectory, "*.dsp"))
			{
				RuntimeDependencies.Add(Pack, StagedFileType.UFS);
			}
		}
	}
}
