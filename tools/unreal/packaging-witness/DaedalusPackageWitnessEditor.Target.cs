using UnrealBuildTool;

public class DaedalusPackageWitnessEditorTarget : TargetRules
{
    public DaedalusPackageWitnessEditorTarget(TargetInfo Target) : base(Target)
    {
        Type = TargetType.Editor;
        DefaultBuildSettings = BuildSettingsVersion.Latest;
        IncludeOrderVersion = EngineIncludeOrderVersion.Latest;
        ExtraModuleNames.Add("DaedalusPackageWitness");
    }
}
