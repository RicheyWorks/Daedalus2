// SPDX-License-Identifier: MIT

using UnrealBuildTool;

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
		AddEngineThirdPartyPrivateStaticDependencies(Target, "libcurl");
	}
}
