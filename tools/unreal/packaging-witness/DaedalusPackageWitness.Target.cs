using UnrealBuildTool;

public class DaedalusPackageWitnessTarget : TargetRules
{
    public DaedalusPackageWitnessTarget(TargetInfo Target) : base(Target)
    {
        Type = TargetType.Game;
        DefaultBuildSettings = BuildSettingsVersion.Latest;
        IncludeOrderVersion = EngineIncludeOrderVersion.Latest;
        ExtraModuleNames.Add("DaedalusPackageWitness");
    }
}
