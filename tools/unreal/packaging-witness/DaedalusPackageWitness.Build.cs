using UnrealBuildTool;

public class DaedalusPackageWitness : ModuleRules
{
    public DaedalusPackageWitness(ReadOnlyTargetRules Target) : base(Target)
    {
        PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;
        PrivateDependencyModuleNames.AddRange(new[]
        {
            "Core", "CoreUObject", "Engine", "Projects", "Json", "DaedalusLink"
        });
    }
}
