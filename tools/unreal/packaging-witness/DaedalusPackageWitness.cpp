// SPDX-License-Identifier: MIT
// Isolated Development fixture only. No server, transaction or production actor edits.
#include "CoreMinimal.h"
#include "Modules/ModuleManager.h"
#include "Engine/World.h"
#include "Engine/StaticMesh.h"
#include "Engine/StaticMeshActor.h"
#include "EngineUtils.h"
#include "Components/StaticMeshComponent.h"
#include "Dom/JsonObject.h"
#include "Interfaces/IPluginManager.h"
#include "HAL/PlatformProcess.h"
#include "Misc/CommandLine.h"
#include "Misc/Crc.h"
#include "Misc/FileHelper.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"
#include "Policies/CondensedJsonPrintPolicy.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonWriter.h"
#include "UObject/UObjectGlobals.h"
#include "DaedalusProspectorMineReadLibrary.h"
#include "FixturePayloadExpectations.h" // generated from pinned public test payloads

class FDaedalusPackageWitnessModule final : public FDefaultGameModuleImpl
{
public:
    virtual void StartupModule() override
    {
        FParse::Value(FCommandLine::Get(), TEXT("DaedalusPackageWitness="), Nonce);
        if (!Nonce.IsEmpty() && Nonce.Len() <= 64)
            Handle = FCoreUObjectDelegates::PostLoadMapWithWorld.AddRaw(this, &FDaedalusPackageWitnessModule::MapLoaded);
    }
    virtual void ShutdownModule() override
    {
        FCoreUObjectDelegates::PostLoadMapWithWorld.Remove(Handle);
    }
private:
    void MapLoaded(UWorld* World)
    {
        if (bObserved || !World) return;
        bObserved = true;
        const FString Map = World->GetOutermost()->GetName();
        bool bPass = World->IsGameWorld() && Map == TEXT("/Game/CodexToolEvaluation/HLODMinimal/R1/HLOD_Fixture")
            && FModuleManager::Get().IsModuleLoaded(TEXT("DaedalusLink"));
        const bool bEditorMineApiAbsent = UDaedalusProspectorMineReadLibrary::StaticClass()->FindFunctionByName(TEXT("ReadFreshMineSource")) == nullptr;
        bPass &= bEditorMineApiAbsent;
        TArray<FString> Names;
        TArray<TSharedPtr<FJsonValue>> Actors;
        for (TActorIterator<AStaticMeshActor> It(World); It; ++It)
        {
            AStaticMeshActor* Actor = *It;
            UStaticMesh* Mesh = Actor->GetStaticMeshComponent()->GetStaticMesh();
            const FString Name = Actor->GetName();
            Names.Add(Name);
            const bool bMesh = Mesh && Mesh->GetPathName() == TEXT("/Game/CodexToolEvaluation/LODSourceRoundtrip/RasterR2/Prop_Realm_Cave_Floor.Prop_Realm_Cave_Floor")
                && Mesh->GetNumLODs() == 2;
            bPass &= bMesh;
            TSharedRef<FJsonObject> Row = MakeShared<FJsonObject>();
            Row->SetStringField(TEXT("actor"), Actor->GetPathName());
            Row->SetStringField(TEXT("mesh"), Mesh ? Mesh->GetPathName() : TEXT(""));
            Row->SetNumberField(TEXT("render_lods"), Mesh ? Mesh->GetNumLODs() : 0);
            Row->SetBoolField(TEXT("expected_mesh"), bMesh);
            Actors.Add(MakeShared<FJsonValueObject>(Row));
        }
        Names.Sort();
        bPass &= Names == TArray<FString>{TEXT("HLSourceA"), TEXT("HLSourceB")};
        const TSharedPtr<IPlugin> Plugin = IPluginManager::Get().FindPlugin(TEXT("DaedalusLink"));
        bPass &= Plugin.IsValid();
        TArray<TSharedPtr<FJsonValue>> Payloads;
        if (Plugin.IsValid()) for (const FFixturePayloadExpectation& Expected : GFixturePayloads)
        {
            TArray<uint8> Bytes;
            const bool bLoaded = FFileHelper::LoadFileToArray(Bytes, *FPaths::Combine(Plugin->GetContentDir(), Expected.Relative));
            const uint32 Crc = bLoaded ? FCrc::MemCrc32(Bytes.GetData(), Bytes.Num()) : 0;
            const bool bMatch = bLoaded && Bytes.Num() == Expected.Size && Crc == Expected.Crc;
            bPass &= bMatch;
            TSharedRef<FJsonObject> Row = MakeShared<FJsonObject>();
            Row->SetStringField(TEXT("relative"), Expected.Relative);
            Row->SetNumberField(TEXT("bytes"), Bytes.Num());
            Row->SetNumberField(TEXT("crc32_diagnostic_not_crypto"), static_cast<double>(Crc));
            Row->SetBoolField(TEXT("matched"), bMatch);
            Payloads.Add(MakeShared<FJsonValueObject>(Row));
        }
        TSharedRef<FJsonObject> Result = MakeShared<FJsonObject>();
        Result->SetStringField(TEXT("scope"), TEXT("isolated_development_map_and_custom_ufs_read"));
        Result->SetStringField(TEXT("nonce"), Nonce);
        Result->SetNumberField(TEXT("pid"), FPlatformProcess::GetCurrentProcessId());
        Result->SetStringField(TEXT("map"), Map);
        Result->SetBoolField(TEXT("game_world"), World->IsGameWorld());
        Result->SetBoolField(TEXT("editor_only_mine_api_absent"), bEditorMineApiAbsent);
        Result->SetArrayField(TEXT("actors"), Actors);
        Result->SetArrayField(TEXT("payloads"), Payloads);
        Result->SetBoolField(TEXT("passed"), bPass);
        Result->SetBoolField(TEXT("visual_or_production_acceptance"), false);
        FString Text;
        FJsonSerializer::Serialize(Result, TJsonWriterFactory<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>::Create(&Text));
        UE_LOG(LogTemp, Display, TEXT("DAEDALUS_PACKAGE_WITNESS_V1 %s"), *Text);
    }
    FString Nonce;
    FDelegateHandle Handle;
    bool bObserved = false;
};

IMPLEMENT_PRIMARY_GAME_MODULE(FDaedalusPackageWitnessModule, DaedalusPackageWitness, "DaedalusPackageWitness");
