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

		// A bounded direct-loopback client must disable HTTP redirects before sending credentials.
		AddEngineThirdPartyPrivateStaticDependencies(Target, "libcurl", "nghttp2", "OpenSSL", "zlib");

		// Runtime readers use FFileHelper: these custom formats must survive cooking/staging.
		// Keep the patterns in the receipt so newly added catalogs/casts are included too.
		RuntimeDependencies.Add(Path.Combine(PluginDirectory, "Content", "Inventory", "*.dic"), StagedFileType.UFS);
		RuntimeDependencies.Add(Path.Combine(PluginDirectory, "Content", "Casts", "*.dcs"), StagedFileType.UFS);
		RuntimeDependencies.Add(Path.Combine(PluginDirectory, "Content", "Realm", "*.drr"), StagedFileType.UFS);
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
