#if WITH_EDITOR && WITH_DEV_AUTOMATION_TESTS
#include "DaedalusProspectorMineReadLibrary.h"
#include "Misc/AutomationTest.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDaedalusMineFreshScopeTest,"Daedalus.Editor.Animation.MineFreshScopeRefusal",EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FDaedalusMineFreshScopeTest::RunTest(const FString&)
{
    const TArray<FString> Results={UDaedalusProspectorMineReadLibrary::ReadFreshMineSource(nullptr),UDaedalusProspectorMineReadLibrary::ReadFreshMineClip(TEXT("/Game/Other.Other"))};
    for(const FString& Text:Results){TSharedPtr<FJsonObject> O;const bool Parsed=FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),O);TestTrue(TEXT("Refusal is valid JSON"),Parsed&&O.IsValid());if(!Parsed||!O)continue;
        TestEqual(TEXT("Invalid scope held"),O->GetStringField(TEXT("state")),FString(TEXT("held")));
        TestEqual(TEXT("No independent source translation"),O->GetIntegerField(TEXT("source_translations")),0);
        TestTrue(TEXT("Refusal has diagnostics"),O->GetArrayField(TEXT("errors")).Num()>0);}
    return true;
}
#endif
