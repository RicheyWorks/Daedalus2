// SPDX-License-Identifier: MIT
#include "DaedalusLegacyHlodFixture.h"
#include "DaedalusEditorAcceptanceLibrary.h"
#if WITH_EDITOR
#include "DaedalusMineSourceHash.h"
#include "Editor.h"
#include "Engine/World.h"
#include "Engine/Level.h"
#include "Engine/LODActor.h"
#include "Engine/HLODProxy.h"
#include "Engine/StaticMesh.h"
#include "Engine/StaticMeshActor.h"
#include "Engine/Selection.h"
#include "EngineUtils.h"
#include "Components/StaticMeshComponent.h"
#include "GameFramework/WorldSettings.h"
#include "HLOD/HLODSetup.h"
#include "HierarchicalLOD.h"
#include "HierarchicalLODUtilitiesModule.h"
#include "IHierarchicalLODUtilities.h"
#include "Factories/WorldFactory.h"
#include "FileHelpers.h"
#include "Misc/PackageName.h"
#include "Misc/Paths.h"
#include "HAL/FileManager.h"
#include "Modules/ModuleManager.h"
#include "StaticMeshResources.h"
#include "Subsystems/UnrealEditorSubsystem.h"
#include "UObject/Package.h"
#include "UObject/SavePackage.h"
#include "UObject/StrongObjectPtr.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonWriter.h"
#include "Policies/CondensedJsonPrintPolicy.h"

namespace DaedalusLegacyHlodFixture
{
namespace
{
constexpr TCHAR ProductionWorld[] = TEXT("/Game/Daedalus/DaedalusWorld.DaedalusWorld");
constexpr TCHAR WorldPackage[] = TEXT("/Game/CodexToolEvaluation/HLODMinimal/R1/HLOD_Fixture");
constexpr TCHAR WorldObject[] = TEXT("/Game/CodexToolEvaluation/HLODMinimal/R1/HLOD_Fixture.HLOD_Fixture");
constexpr TCHAR ProxyPackage[] = TEXT("/Game/CodexToolEvaluation/HLODMinimal/R1/HLOD/HLOD_Fixture_0_HLOD");
constexpr TCHAR ProxyName[] = TEXT("HLOD_Fixture_0_HLOD");
constexpr TCHAR SourceMesh[] = TEXT("/Game/CodexToolEvaluation/LODSourceRoundtrip/RasterR2/Prop_Realm_Cave_Floor.Prop_Realm_Cave_Floor");
TStrongObjectPtr<UWorld> CreatedWorld;

using JObject = TSharedRef<FJsonObject>;

FString Text(const JObject& Object)
{
    FString Result;
    auto Writer = TJsonWriterFactory<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>::Create(&Result);
    return FJsonSerializer::Serialize(Object, Writer) ? Result : TEXT("{\"ok\":false,\"diagnostic\":\"Serialization failed\"}");
}

TArray<TSharedPtr<FJsonValue>> Vector(const FVector& Value)
{
    return { MakeShared<FJsonValueNumber>(Value.X), MakeShared<FJsonValueNumber>(Value.Y), MakeShared<FJsonValueNumber>(Value.Z) };
}

JObject Identity(UObject* Value)
{
    auto Object = MakeShared<FJsonObject>();
    if (Value)
    {
        Object->SetStringField(TEXT("path"), Value->GetPathName());
        Object->SetStringField(TEXT("class"), Value->GetClass()->GetPathName());
        Object->SetStringField(TEXT("package"), Value->GetOutermost()->GetName());
    }
    return Object;
}

TArray<TSharedPtr<FJsonValue>> PackageNames(const TArray<UPackage*>& Packages)
{
    TArray<FString> Names;
    for (UPackage* Package : Packages) if (Package) Names.Add(Package->GetName());
    Names.Sort();
    TArray<TSharedPtr<FJsonValue>> Values;
    for (const FString& Name : Names) Values.Add(MakeShared<FJsonValueString>(Name));
    return Values;
}

bool Snapshot(JObject& Result, FString& Error)
{
    if (!IsInGameThread() || !GEditor || GEditor->PlayWorld || GUndo)
    {
        Error = TEXT("Exact editor/game-thread/no-PIE/no-transaction context required");
        return false;
    }
    UWorld* Current = GEditor->GetEditorWorldContext().World();
    if (!Current || Current->GetPathName() != ProductionWorld || Current->GetWorldPartition())
    {
        Error = TEXT("Exact current nonpartitioned DaedalusWorld required");
        return false;
    }
    Result->SetStringField(TEXT("project"), FPaths::GetProjectFilePath());
    Result->SetStringField(TEXT("world"), Current->GetPathName());
    Result->SetBoolField(TEXT("pie"), false);
    if (GEditor->GetPIEWorldContext())
    {
        Error = TEXT("Game/PIE context remains present");
        return false;
    }
    Result->SetField(TEXT("game_world"), MakeShared<FJsonValueNull>());
    TArray<UPackage*> Maps, Content;
    FEditorFileUtils::GetDirtyWorldPackages(Maps);
    FEditorFileUtils::GetDirtyContentPackages(Content);
    Result->SetArrayField(TEXT("dirty_maps"), PackageNames(Maps));
    Result->SetArrayField(TEXT("dirty_content"), PackageNames(Content));

    TArray<AActor*> Actors;
    for (TActorIterator<AActor> It(Current, AActor::StaticClass(), EActorIteratorFlags::SkipPendingKill); It; ++It)
    {
        if (Actors.Num() >= 50000) { Error = TEXT("Native scene actor cap exceeded"); return false; }
        Actors.Add(*It);
    }
    Actors.Sort([](const AActor& A, const AActor& B) { return A.GetPathName() < B.GetPathName(); });
    TArray<TSharedPtr<FJsonValue>> Rows;
    for (AActor* Actor : Actors)
    {
        const FVector Location = Actor->GetActorLocation(), Scale = Actor->GetActorScale3D();
        const FRotator Rotation = Actor->GetActorRotation();
        if (Location.ContainsNaN() || Scale.ContainsNaN() || Rotation.ContainsNaN())
        { Error = TEXT("Nonfinite scene transform"); return false; }
        auto Row = MakeShared<FJsonObject>();
        Row->SetStringField(TEXT("path"), Actor->GetPathName());
        Row->SetStringField(TEXT("class"), Actor->GetClass()->GetPathName());
        Row->SetStringField(TEXT("label"), Actor->GetActorLabel(false));
        Row->SetArrayField(TEXT("location"), Vector(Location));
        Row->SetArrayField(TEXT("rotation"), Vector(FVector(Rotation.Pitch, Rotation.Yaw, Rotation.Roll)));
        Row->SetArrayField(TEXT("scale"), Vector(Scale));
        Rows.Add(MakeShared<FJsonValueObject>(Row));
    }
    auto SceneRows = MakeShared<FJsonObject>();
    SceneRows->SetArrayField(TEXT("actors"), Rows);
    const FString SceneText = Text(SceneRows);
    FTCHARToUTF8 Utf8(*SceneText);
    FString Digest;
    if (Utf8.Length() > 64 * 1024 * 1024 || !DaedalusMineSourceHash::Compute(
        reinterpret_cast<const uint8*>(Utf8.Get()), static_cast<uint32>(Utf8.Length()), Digest))
    { Error = TEXT("Native scene serialization/hash cap failed"); return false; }
    auto Scene = MakeShared<FJsonObject>();
    Scene->SetNumberField(TEXT("actors"), Actors.Num());
    Scene->SetStringField(TEXT("sha256"), Digest);
    Scene->SetStringField(TEXT("scope"), TEXT("native-hlod-context-v1: sorted path/class/label/location/rotation/scale; distinct from historical Python JSON encoding"));
    Result->SetObjectField(TEXT("scene"), Scene);

    TArray<FString> Selected;
    for (FSelectionIterator It = GEditor->GetSelectedActorIterator(); It; ++It)
        if (AActor* Actor = Cast<AActor>(*It)) Selected.Add(Actor->GetPathName());
    Selected.Sort();
    TArray<TSharedPtr<FJsonValue>> Selection;
    for (const FString& Path : Selected) Selection.Add(MakeShared<FJsonValueString>(Path));
    Result->SetArrayField(TEXT("selection"), Selection);
    FVector Location;
    FRotator Rotation;
    UUnrealEditorSubsystem* Editor = GEditor->GetEditorSubsystem<UUnrealEditorSubsystem>();
    if (!Editor || !Editor->GetLevelViewportCameraInfo(Location, Rotation))
    { Error = TEXT("Actual level viewport camera unavailable"); return false; }
    auto Camera = MakeShared<FJsonObject>();
    Camera->SetArrayField(TEXT("location"), Vector(Location));
    Camera->SetArrayField(TEXT("rotation"), Vector(FVector(Rotation.Pitch, Rotation.Yaw, Rotation.Roll)));
    Result->SetObjectField(TEXT("camera"), Camera);
    return true;
}

bool Clean(const JObject& Snapshot)
{
    return Snapshot->GetArrayField(TEXT("dirty_maps")).IsEmpty()
        && Snapshot->GetArrayField(TEXT("dirty_content")).IsEmpty();
}

JObject Reply(const TCHAR* Stage, bool bOK, const FString& Diagnostic)
{
    auto Result = MakeShared<FJsonObject>();
    Result->SetStringField(TEXT("schema"), TEXT("daedalus.legacy-hlod-private-fixture.v1"));
    Result->SetStringField(TEXT("stage"), Stage);
    Result->SetBoolField(TEXT("ok"), bOK);
    Result->SetStringField(TEXT("diagnostic"), Diagnostic);
    Result->SetBoolField(TEXT("native_runtime_qualified"), false);
    Result->SetBoolField(TEXT("production_HLOD_accepted"), false);
    Result->SetBoolField(TEXT("python_crash_root_cause_fixed"), false);
    return Result;
}

bool Vacant()
{
    return !FindPackage(nullptr, WorldPackage) && !FindPackage(nullptr, ProxyPackage)
        && !FPackageName::DoesPackageExist(WorldPackage) && !FPackageName::DoesPackageExist(ProxyPackage);
}

bool DirtyOutsideFixture()
{
    TArray<UPackage*> Packages, Content;
    FEditorFileUtils::GetDirtyWorldPackages(Packages);
    FEditorFileUtils::GetDirtyContentPackages(Content);
    Packages.Append(Content);
    for (UPackage* Package : Packages)
        if (Package && Package->GetName() != WorldPackage && Package->GetName() != ProxyPackage) return true;
    return false;
}

bool SaveNew(UPackage* Package, UObject* Asset, bool bMap)
{
    if (!Package || !Asset || (Package->GetName() != WorldPackage && Package->GetName() != ProxyPackage)) return false;
    const FString Filename = FPackageName::LongPackageNameToFilename(Package->GetName(),
        bMap ? FPackageName::GetMapPackageExtension() : FPackageName::GetAssetPackageExtension());
    if (IFileManager::Get().FileExists(*Filename)) return false;
    if (!IFileManager::Get().MakeDirectory(*FPaths::GetPath(Filename), true)) return false;
    FSavePackageArgs Args;
    Args.TopLevelFlags = RF_Public | RF_Standalone;
    Args.SaveFlags = SAVE_None;
    Args.Error = GWarn;
    return UPackage::SavePackage(Package, Asset, *Filename, Args);
}

JObject Describe(UWorld* World)
{
    auto Result = MakeShared<FJsonObject>();
    Result->SetObjectField(TEXT("world"), Identity(World));
    Result->SetBoolField(TEXT("partitioned"), World->GetWorldPartition() != nullptr);
    Result->SetBoolField(TEXT("is_current_editor_world"), World == GEditor->GetEditorWorldContext().World());
    TArray<TSharedPtr<FJsonValue>> Sources;
    TArray<ALODActor*> Clusters;
    for (AActor* Actor : World->PersistentLevel->Actors)
    {
        if (ALODActor* Cluster = Cast<ALODActor>(Actor)) Clusters.Add(Cluster);
        else if (AStaticMeshActor* MeshActor = Cast<AStaticMeshActor>(Actor))
        {
            auto Source = Identity(MeshActor);
            Source->SetObjectField(TEXT("mesh"), Identity(MeshActor->GetStaticMeshComponent()->GetStaticMesh()));
            Source->SetArrayField(TEXT("location"), Vector(MeshActor->GetActorLocation()));
            Sources.Add(MakeShared<FJsonValueObject>(Source));
        }
    }
    Result->SetArrayField(TEXT("sources"), Sources);
    Result->SetNumberField(TEXT("cluster_count"), Clusters.Num());
    Result->SetNumberField(TEXT("source_count"), Sources.Num());
    bool bSettings = false;
    const AWorldSettings* Settings = World->GetWorldSettings();
    const UHierarchicalLODSettings* Defaults = GetDefault<UHierarchicalLODSettings>();
    if (Settings && Settings->HLODSetupAsset.IsNull() && !Defaults->bForceSettingsInAllMaps
        && !Defaults->bSaveLODActorsToHLODPackages)
    {
        const auto& Hierarchy = Settings->GetHierarchicalLODSetup();
        if (Hierarchy.Num() == 1)
        {
            const FHierarchicalSimplification& Setup = Hierarchy[0];
            auto Observed = MakeShared<FJsonObject>();
            Observed->SetNumberField(TEXT("simplification_method"), static_cast<int32>(Setup.SimplificationMethod));
            Observed->SetNumberField(TEXT("lod_selection"), static_cast<int32>(Setup.MergeSetting.LODSelectionType));
            Observed->SetNumberField(TEXT("specific_lod"), Setup.MergeSetting.SpecificLOD);
            Observed->SetBoolField(TEXT("merge_materials"), Setup.MergeSetting.bMergeMaterials);
            Observed->SetBoolField(TEXT("merge_physics"), Setup.MergeSetting.bMergePhysicsData);
            Observed->SetBoolField(TEXT("include_imposters"), Setup.MergeSetting.bIncludeImposters);
            Observed->SetBoolField(TEXT("landscape_culling"), Setup.MergeSetting.bUseLandscapeCulling);
            Observed->SetBoolField(TEXT("generate_lightmap_uv"), Setup.MergeSetting.bGenerateLightMapUV);
            Observed->SetBoolField(TEXT("nanite_enabled"), Setup.MergeSetting.NaniteSettings.bEnabled);
            Result->SetObjectField(TEXT("actual_local_settings"), Observed);
            bSettings = Setup.SimplificationMethod == EHierarchicalSimplificationMethod::Merge
                && Setup.MergeSetting.LODSelectionType == EMeshLODSelectionType::SpecificLOD
                && Setup.MergeSetting.SpecificLOD == 0 && !Setup.MergeSetting.bMergeMaterials
                && !Setup.MergeSetting.bMergePhysicsData && !Setup.MergeSetting.bIncludeImposters
                && !Setup.MergeSetting.bUseLandscapeCulling && !Setup.MergeSetting.bGenerateLightMapUV
                && !Setup.MergeSetting.NaniteSettings.bEnabled;
        }
    }
    Result->SetBoolField(TEXT("actual_settings_verified"), bSettings);
    if (Clusters.Num() == 1)
    {
        ALODActor* Cluster = Clusters[0];
        Result->SetObjectField(TEXT("cluster"), Identity(Cluster));
        Result->SetNumberField(TEXT("tier_one_based"), Cluster->LODLevel);
        Result->SetNumberField(TEXT("cluster_source_count"), Cluster->SubActors.Num());
        UStaticMesh* Mesh = Cluster->GetStaticMeshComponent()->GetStaticMesh();
        UHLODProxy* Proxy = const_cast<UHLODProxy*>(Cluster->GetProxy());
        Result->SetObjectField(TEXT("mesh"), Identity(Mesh));
        Result->SetObjectField(TEXT("proxy"), Identity(Proxy));
        Result->SetObjectField(TEXT("proxy_map"), Identity(Proxy ? Proxy->GetMap().Get() : nullptr));
        Result->SetBoolField(TEXT("cluster_transient"), Cluster->HasAnyFlags(RF_Transient));
        const bool bMesh = Mesh && Mesh->GetRenderData() && Mesh->GetRenderData()->LODResources.Num() == 1;
        Result->SetNumberField(TEXT("mesh_lod_count"), Mesh ? Mesh->GetNumLODs() : 0);
        Result->SetNumberField(TEXT("mesh_lod0_triangles"), bMesh ? Mesh->GetRenderData()->LODResources[0].GetNumTriangles() : 0);
        Result->SetBoolField(TEXT("mesh_nanite_enabled"), Mesh && Mesh->GetNaniteSettings().bEnabled);
        AStaticMeshActor* A = FindObject<AStaticMeshActor>(World->PersistentLevel, TEXT("HLSourceA"));
        AStaticMeshActor* B = FindObject<AStaticMeshActor>(World->PersistentLevel, TEXT("HLSourceB"));
        const bool bSources = A && B && A != B && A->GetWorld() == World && B->GetWorld() == World
            && A->GetLevel() == World->PersistentLevel && B->GetLevel() == World->PersistentLevel
            && Cluster->SubActors.Contains(A) && Cluster->SubActors.Contains(B)
            && A->GetStaticMeshComponent()->GetStaticMesh() && B->GetStaticMeshComponent()->GetStaticMesh()
            && A->GetStaticMeshComponent()->GetStaticMesh()->GetPathName() == SourceMesh
            && B->GetStaticMeshComponent()->GetStaticMesh() == A->GetStaticMeshComponent()->GetStaticMesh();
        const bool bOwn = bSettings && bSources && Mesh && Proxy && Mesh->GetOutermost()->GetName() == ProxyPackage
            && Proxy->GetOutermost()->GetName() == ProxyPackage && Proxy->GetFName() == FName(ProxyName)
            && Proxy->GetMap().Get() == World && Cluster->GetLevel() == World->PersistentLevel
            && Cluster->LODLevel == 1 && Cluster->SubActors.Num() == 2 && Sources.Num() == 2
            && !Cluster->HasAnyFlags(RF_Transient) && bMesh && !Mesh->GetNaniteSettings().bEnabled
            && Mesh->GetRenderData()->LODResources[0].GetNumTriangles() == 3520;
        Result->SetBoolField(TEXT("owned_closure_verified"), bOwn);
    }
    else Result->SetBoolField(TEXT("owned_closure_verified"), false);
    return Result;
}
}

FString ReadContext()
{
    auto Result = Reply(TEXT("CONTEXT"), false, TEXT("Read only; no fixture creation"));
    auto State = MakeShared<FJsonObject>();
    FString Error;
    if (!Snapshot(State, Error)) { Result->SetStringField(TEXT("diagnostic"), Error); return Text(Result); }
    Result->SetBoolField(TEXT("ok"), true);
    Result->SetObjectField(TEXT("snapshot"), State);
    const UHierarchicalLODSettings* Settings = GetDefault<UHierarchicalLODSettings>();
    auto Policy = MakeShared<FJsonObject>();
    Policy->SetBoolField(TEXT("force_settings"), Settings->bForceSettingsInAllMaps);
    Policy->SetBoolField(TEXT("description_actors"), Settings->bSaveLODActorsToHLODPackages);
    Policy->SetStringField(TEXT("default_setup_path"), Settings->DefaultSetup.ToSoftObjectPath().ToString());
    Policy->SetBoolField(TEXT("owned_packages_vacant"), Vacant());
    Policy->SetBoolField(TEXT("creation_policy_admitted"), Clean(State) && CheckPolicy(
        Settings->bForceSettingsInAllMaps, Settings->bSaveLODActorsToHLODPackages, false, Vacant(), 2, 0));
    Result->SetObjectField(TEXT("policy"), Policy);
    return Text(Result);
}

FString CreateBuildSave()
{
    auto Result = Reply(TEXT("CREATE_BUILD_SAVE"), false, TEXT("Check before ownership; retain partial owned work on failure"));
    auto Before = MakeShared<FJsonObject>();
    FString Error;
    if (!Snapshot(Before, Error) || !Clean(Before))
    { Result->SetStringField(TEXT("diagnostic"), Error.IsEmpty() ? TEXT("Clean context required") : Error); return Text(Result); }
    const UHierarchicalLODSettings* Defaults = GetDefault<UHierarchicalLODSettings>();
    if (!CheckPolicy(Defaults->bForceSettingsInAllMaps, Defaults->bSaveLODActorsToHLODPackages, false, Vacant(), 2, 0))
    { Result->SetStringField(TEXT("diagnostic"), TEXT("New owned packages/local setup/non-description mode required; never change defaults or replace")); return Text(Result); }
    UStaticMesh* Source = LoadObject<UStaticMesh>(nullptr, SourceMesh);
    if (!Source || Source->GetOutermost()->IsDirty() || Source->GetNaniteSettings().bEnabled
        || !Source->GetRenderData() || Source->GetRenderData()->LODResources.Num() != 2
        || Source->GetRenderData()->LODResources[0].GetNumTriangles() != 1760
        || Source->GetRenderData()->LODResources[1].GetNumTriangles() != 1496)
    { Result->SetStringField(TEXT("diagnostic"), TEXT("Pinned qualified raster source geometry/settings not observed")); return Text(Result); }
    const FBoxSphereBounds Bounds = Source->GetBounds();
    if (Bounds.Origin.ContainsNaN() || Bounds.BoxExtent.ContainsNaN() || Bounds.BoxExtent.X <= 0)
    { Result->SetStringField(TEXT("diagnostic"), TEXT("Finite source bounds required")); return Text(Result); }
    if (!Source->GetMaterial(0))
    { Result->SetStringField(TEXT("diagnostic"), TEXT("Loaded source material required")); return Text(Result); }
    UPackage* Package = CreatePackage(WorldPackage);
    UWorldFactory* Factory = NewObject<UWorldFactory>();
    Factory->WorldType = EWorldType::Inactive;
    Factory->bInformEngineOfWorld = false;
    Factory->bCreateWorldPartition = false;
    Factory->bEnableWorldPartitionStreaming = false;
    // MinimalAPI factory override is invoked through its exported virtual base.
    UFactory* CreateFactory = Factory;
    UWorld* World = Cast<UWorld>(CreateFactory->FactoryCreateNew(UWorld::StaticClass(), Package,
        TEXT("HLOD_Fixture"), RF_Public | RF_Standalone, nullptr, GWarn));
    CreatedWorld.Reset(World);
    if (!World || World->GetPathName() != WorldObject || World->GetWorldPartition()
        || World == GEditor->GetEditorWorldContext().World() || !World->PersistentLevel)
    { Result->SetStringField(TEXT("diagnostic"), TEXT("Private inactive world creation mismatch; retained")); return Text(Result); }
    AWorldSettings* Settings = World->GetWorldSettings();
    if (!Settings || !Settings->HLODSetupAsset.IsNull())
    { Result->SetStringField(TEXT("diagnostic"), TEXT("Unexpected setup asset on new private world; retained")); return Text(Result); }
    FHierarchicalSimplification Setup;
    Setup.SimplificationMethod = EHierarchicalSimplificationMethod::Merge;
    Setup.MergeSetting.LODSelectionType = EMeshLODSelectionType::SpecificLOD;
    Setup.MergeSetting.SpecificLOD = 0;
    Setup.MergeSetting.bMergeMaterials = false;
    Setup.MergeSetting.bMergePhysicsData = false;
    Setup.MergeSetting.bIncludeImposters = false;
    Setup.MergeSetting.bUseLandscapeCulling = false;
    Setup.MergeSetting.bGenerateLightMapUV = false;
    Setup.MergeSetting.NaniteSettings.bEnabled = false;
    Settings->GetHierarchicalLODSetup() = { Setup };
    TArray<AActor*> Actors;
    for (int32 Index = 0; Index < 2; ++Index)
    {
        FActorSpawnParameters Params;
        Params.Name = FName(Index == 0 ? TEXT("HLSourceA") : TEXT("HLSourceB"));
        Params.OverrideLevel = World->PersistentLevel;
        Params.ObjectFlags = RF_NoFlags;
        Params.bCreateActorPackage = false;
        Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
        AStaticMeshActor* Actor = World->SpawnActor<AStaticMeshActor>(AStaticMeshActor::StaticClass(),
            FVector(Index * (2 * Bounds.BoxExtent.X + 100), 0, 0), FRotator::ZeroRotator, Params);
        if (!Actor || Actor->GetLevel() != World->PersistentLevel)
        { Result->SetStringField(TEXT("diagnostic"), TEXT("Owned source creation mismatch; retained")); return Text(Result); }
        Actor->GetStaticMeshComponent()->SetStaticMesh(Source);
        Actor->GetStaticMeshComponent()->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        Actor->GetStaticMeshComponent()->SetGenerateOverlapEvents(false);
        Actors.Add(Actor);
    }
    auto& Module = FModuleManager::LoadModuleChecked<FHierarchicalLODUtilitiesModule>(TEXT("HierarchicalLODUtilities"));
    IHierarchicalLODUtilities* Utilities = Module.GetUtilities();
    ALODActor* Cluster = Utilities->CreateNewClusterFromActors(World, Settings, Actors, 0);
    if (!Cluster || Cluster->GetLevel() != World->PersistentLevel || Cluster->SubActors.Num() != 2)
    { Result->SetStringField(TEXT("diagnostic"), TEXT("Owned cluster creation mismatch; retained")); return Text(Result); }
    UHLODProxy* Proxy = Utilities->CreateOrRetrieveLevelHLODProxy(World->PersistentLevel, 0);
    if (!Proxy || Proxy->GetOutermost()->GetName() != ProxyPackage || Proxy->GetMap().Get() != World)
    { Result->SetStringField(TEXT("diagnostic"), TEXT("Owned level/tier proxy mismatch; retained")); return Text(Result); }
    // Exactly one synchronous Merge cluster. No broad Build/BuildMeshes, Simplify or Approximate.
    const bool bBuilt = Utilities->BuildStaticMeshForLODActor(Cluster, Proxy, Setup, Source->GetMaterial(0));
    auto Fixture = Describe(World);
    Result->SetBoolField(TEXT("single_cluster_build_return"), bBuilt);
    Result->SetObjectField(TEXT("fixture"), Fixture);
    if (!bBuilt || !Fixture->GetBoolField(TEXT("owned_closure_verified")) || DirtyOutsideFixture())
    { Result->SetStringField(TEXT("diagnostic"), TEXT("Build/ownership/dirty-package check held; no saves, retained")); return Text(Result); }
    const bool bProxySaved = SaveNew(Proxy->GetOutermost(), Proxy, false);
    const bool bWorldSaved = bProxySaved && SaveNew(Package, World, true);
    Result->SetBoolField(TEXT("proxy_saved"), bProxySaved);
    Result->SetBoolField(TEXT("world_saved"), bWorldSaved);
    Result->SetObjectField(TEXT("fixture"), Describe(World));
    auto After = MakeShared<FJsonObject>();
    const bool bSnapshot = Snapshot(After, Error);
    Result->SetObjectField(TEXT("before"), Before);
    Result->SetObjectField(TEXT("after"), After);
    const bool bPreserved = bSnapshot && Text(Before) == Text(After);
    Result->SetBoolField(TEXT("production_context_preserved"), bPreserved);
    Result->SetBoolField(TEXT("fresh_process_reopen"), false);
    Result->SetBoolField(TEXT("ok"), bProxySaved && bWorldSaved && bPreserved);
    Result->SetStringField(TEXT("diagnostic"), TEXT("Only private one-cluster Merge/save witness; fresh reopen and consumer acceptance remain separate"));
    return Text(Result);
}

FString ReadSaved()
{
    auto Result = Reply(TEXT("READ_SAVED"), false, TEXT("Only explicit saved private world load; no map activation/build/save"));
    auto Before = MakeShared<FJsonObject>();
    FString Error;
    if (!Snapshot(Before, Error) || !Clean(Before))
    { Result->SetStringField(TEXT("diagnostic"), TEXT("Clean exact context required")); return Text(Result); }
    if (!FPackageName::DoesPackageExist(WorldPackage) || !FPackageName::DoesPackageExist(ProxyPackage))
    { Result->SetStringField(TEXT("diagnostic"), TEXT("Both actual saved fixture packages required")); return Text(Result); }
    const bool bAlreadyLoaded = FindObject<UWorld>(nullptr, WorldObject) != nullptr;
    UWorld* World = LoadObject<UWorld>(nullptr, WorldObject);
    if (!World || !World->PersistentLevel || World->GetWorldPartition() || World == GEditor->GetEditorWorldContext().World())
    { Result->SetStringField(TEXT("diagnostic"), TEXT("Saved isolated world identity mismatch")); return Text(Result); }
    auto Fixture = Describe(World);
    auto After = MakeShared<FJsonObject>();
    const bool bSnapshot = Snapshot(After, Error);
    const bool bPreserved = bSnapshot && Text(Before) == Text(After);
    Result->SetObjectField(TEXT("fixture"), Fixture);
    Result->SetObjectField(TEXT("before"), Before);
    Result->SetObjectField(TEXT("after"), After);
    Result->SetBoolField(TEXT("already_loaded_before_read"), bAlreadyLoaded);
    Result->SetBoolField(TEXT("created_this_process"), CreatedWorld.IsValid());
    Result->SetBoolField(TEXT("production_context_preserved"), bPreserved);
    Result->SetBoolField(TEXT("ok"), bPreserved && Fixture->GetBoolField(TEXT("owned_closure_verified")));
    return Text(Result);
}
}
#endif

FString UDaedalusEditorAcceptanceLibrary::ReadLegacyHlodFixtureContext()
{
#if WITH_EDITOR
    return DaedalusLegacyHlodFixture::ReadContext();
#else
    return TEXT("{\"ok\":false,\"diagnostic\":\"Editor only\",\"native_runtime_qualified\":false}");
#endif
}

FString UDaedalusEditorAcceptanceLibrary::CreateBuildSaveLegacyHlodFixture()
{
#if WITH_EDITOR
    return DaedalusLegacyHlodFixture::CreateBuildSave();
#else
    return TEXT("{\"ok\":false,\"diagnostic\":\"Editor only\",\"native_runtime_qualified\":false}");
#endif
}

FString UDaedalusEditorAcceptanceLibrary::ReadSavedLegacyHlodFixture()
{
#if WITH_EDITOR
    return DaedalusLegacyHlodFixture::ReadSaved();
#else
    return TEXT("{\"ok\":false,\"diagnostic\":\"Editor only\",\"native_runtime_qualified\":false}");
#endif
}
