// SPDX-License-Identifier: MIT
#pragma once

// Editor-source prerequisite, not installed or compiled by the source lane.
// Include from the existing native owner's editor module (Engine/UnrealEd).
// No UCLASS/plugin/transport, builder, actor/asset edit, save, explicit loading or GC is added.
#if WITH_EDITOR
#include <initializer_list>
#include "CoreMinimal.h"
#include "Containers/StringConv.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/HLODProxy.h"
#include "Engine/Level.h"
#include "Engine/LevelStreaming.h"
#include "Engine/LODActor.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/WorldSettings.h"
#include "HierarchicalLOD.h"
#include "LevelUtils.h"
#include "HLOD/HLODSetup.h"
#include "Materials/MaterialInterface.h"
#include "Dom/JsonObject.h"
#include "Misc/PackageName.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonWriter.h"
#include "UObject/Package.h"
#include "UObject/UObjectHash.h"
#include "UObject/UObjectIterator.h"
#include "UObject/UnrealType.h"

namespace DaedalusLegacyHlod
{
struct FReadRequest
{
    FString WorldPath = TEXT("/Game/Daedalus/DaedalusWorld.DaedalusWorld");
    FString LodActorPath; // Empty requests bounded identities, never an arbitrary choice.
    int32 MaxCandidates = 128;
    int32 MaxSources = 128;
    int32 MaxComponents = 512;
    int32 MaxPackageObjects = 4096;
    int32 MaxReferenceComponents = 32768;
};

struct FIdentity
{
    FString Path;
    FString ClassPath;
    FString OuterPackage;
    FString SavePackage; // Includes an external actor package when applicable.
    uint32 Flags = 0;
};

struct FComponentRead
{
    FIdentity Component;
    FIdentity Mesh;
    FTransform WorldTransform = FTransform::Identity;
    TArray<FIdentity> Materials;
};

struct FPackageRead
{
    FString Name;
    bool bDirty = false;
    bool bFullyLoaded = false;
};

struct FClosureRead
{
    FString State = TEXT("REJECTED");
    FString Reason;
    bool bReadOnly = true;
    bool bLoadedInventoryComplete = false;
    bool bBuildAdmitted = false; // Facts never grant build/resource/ownership authority.
    FString CandidateScope = TEXT("Current-world PersistentLevel/GetLevels() LODActor class candidates, including invisible loaded member levels; configured/unloaded/nonmember levels are not inventoried");
    FIdentity World;
    FIdentity LodActor;
    FIdentity Level;
    FIdentity WorldSettings;
    FIdentity Proxy;
    FIdentity ExistingProxyComponent;
    FIdentity ExistingProxyMesh;
    FTransform ExistingProxyTransform = FTransform::Identity;
    bool bExistingProxyTransformObserved = false;
    FString ProxyMapPath;
    FString ExpectedProxyName;
    FString ExpectedProxyPackage;
    int32 LodLevelOneBased = 0;
    int32 LodIndex = INDEX_NONE;
    FString SettingsSource;
    bool bSettingsObserved = false;
    FString EffectiveSettingsText; // Selected level policy only; actor overrides remain separate below.
    uint8 SimplificationMethod = 0;
    bool bActorOverrideMaterialMergeSettings = false;
    bool bActorOverrideScreenSize = false;
    bool bActorOverrideTransitionScreenSize = false;
    int32 ActorScreenSize = 0;
    float ActorTransitionScreenSize = 0;
    FString ActorMaterialSettingsText;
    bool bActorOverridesObserved = false;
    FString EffectiveBaseMaterialPath;
    FTransform BakingTransform = FTransform::Identity;
    bool bSaveLodActorsToProxyPackage = false;
    TArray<FIdentity> Candidates;
    TArray<FIdentity> Sources;
    TArray<FComponentRead> Components;
    TArray<FIdentity> SharedProxyPackageObjects;
    TArray<FIdentity> ReferencedProxyMeshes;
    TArray<FIdentity> LoadedSharedMeshUsers;
    TArray<FPackageRead> Packages;
    TArray<FString> RequiredLoadedObjects;
    TArray<FString> RequiredExistingDefaultObjectClasses;
    TArray<FString> RequiredFullyLoadedPackages;
    // String budget bounds native output, not JSON overhead. Existing caller must
    // also reject serialized JSON >262144 bytes rather than truncate success.
    int32 IdentityCharacters = 0;
};

inline bool Fail(FClosureRead& Out, const TCHAR* Reason)
{
    Out.State = TEXT("HELD");
    Out.Reason = Reason;
    Out.bLoadedInventoryComplete = false;
    return false;
}

inline bool Identity(const UObject* Object, FIdentity& Value, FClosureRead& Out)
{
    if (!IsValid(Object)) return Fail(Out, TEXT("Null/invalid loaded object"));
    Value.Path = Object->GetPathName();
    Value.ClassPath = Object->GetClass()->GetPathName();
    Value.OuterPackage = Object->GetOutermost()->GetName();
    Value.SavePackage = Object->GetPackage()->GetName();
    Value.Flags = static_cast<uint32>(Object->GetFlags());
    const int32 Added = Value.Path.Len() + Value.ClassPath.Len() +
        Value.OuterPackage.Len() + Value.SavePackage.Len();
    if (Value.Path.Len() > 512 || Value.ClassPath.Len() > 512 ||
        Value.OuterPackage.Len() > 512 || Value.SavePackage.Len() > 512 ||
        Added > 65536 - Out.IdentityCharacters)
        return Fail(Out, TEXT("Native identity payload exceeds bound"));
    Out.IdentityCharacters += Added;
    return true;
}

inline void Package(UPackage* Value, FClosureRead& Out)
{
    if (!Value) return;
    const FString Name = Value->GetName();
    if (Out.Packages.ContainsByPredicate([&](const FPackageRead& X) { return X.Name == Name; })) return;
    FPackageRead Row;
    Row.Name = Name;
    Row.bDirty = Value->IsDirty();
    Row.bFullyLoaded = Value->IsFullyLoaded();
    Out.Packages.Add(MoveTemp(Row));
}

inline const UHierarchicalLODSetup* LoadedSetup(
    const TSoftClassPtr<UHierarchicalLODSetup>& SoftClass, FClosureRead& Out)
{
    UClass* Class = SoftClass.Get(); // Never LoadSynchronous or create a CDO.
    if (!Class)
    {
        Out.RequiredLoadedObjects.AddUnique(SoftClass.ToSoftObjectPath().ToString());
        Fail(Out, TEXT("Exact setup class must be explicitly loaded by the native owner"));
        return nullptr;
    }
    const UHierarchicalLODSetup* Setup = Cast<UHierarchicalLODSetup>(Class->GetDefaultObject(false));
    if (!Setup)
    {
        Out.RequiredExistingDefaultObjectClasses.AddUnique(Class->GetPathName());
        Fail(Out, TEXT("Typed setup default object is unavailable; no implicit creation"));
    }
    return Setup;
}

inline bool Settings(AWorldSettings* WorldSettings, FClosureRead& Out)
{
    const FArrayProperty* LocalArray = FindFProperty<FArrayProperty>(
        AWorldSettings::StaticClass(), TEXT("HierarchicalLODSetup"));
    const FStructProperty* LocalInner = LocalArray ? CastField<FStructProperty>(LocalArray->Inner) : nullptr;
    if (!LocalInner || !LocalInner->Struct ||
        LocalInner->Struct->GetPathName() != TEXT("/Script/Engine.HierarchicalSimplification"))
        return Fail(Out, TEXT("Reflected local HLOD array type is unknown"));
    const UHierarchicalLODSettings* Global = Cast<UHierarchicalLODSettings>(
        UHierarchicalLODSettings::StaticClass()->GetDefaultObject(false));
    if (!Global)
    {
        Out.RequiredExistingDefaultObjectClasses.AddUnique(UHierarchicalLODSettings::StaticClass()->GetPathName());
        return Fail(Out, TEXT("Loaded global HLOD settings default object is unavailable"));
    }
    Out.bSaveLodActorsToProxyPackage = Global->bSaveLODActorsToHLODPackages;
    const UHierarchicalLODSetup* LocalSetup = nullptr;
    const TArray<FHierarchicalSimplification>* Levels = nullptr;
    // Follow the non-const builder getter precedence without its synchronous loads.
    if (!WorldSettings->HLODSetupAsset.IsNull())
    {
        LocalSetup = LoadedSetup(WorldSettings->HLODSetupAsset, Out);
        if (!LocalSetup) return false;
        Levels = &LocalSetup->HierarchicalLODSetup;
        Out.SettingsSource = WorldSettings->HLODSetupAsset.ToSoftObjectPath().ToString();
    }
    else if (Global->bForceSettingsInAllMaps && !Global->DefaultSetup.IsNull())
    {
        const UHierarchicalLODSetup* Setup = LoadedSetup(Global->DefaultSetup, Out);
        if (!Setup) return false;
        Levels = &Setup->HierarchicalLODSetup;
        Out.SettingsSource = Global->DefaultSetup.ToSoftObjectPath().ToString();
    }
    else
    {
        Levels = LocalArray->ContainerPtrToValuePtr<TArray<FHierarchicalSimplification>>(WorldSettings);
        Out.SettingsSource = WorldSettings->GetPathName() + TEXT(":HierarchicalLODSetup");
    }
    if (!Levels || Levels->Num() > 8 || !Levels->IsValidIndex(Out.LodIndex))
        return Fail(Out, TEXT("One-based actor tier does not address an admitted effective settings entry"));
    const FHierarchicalSimplification& Selected = (*Levels)[Out.LodIndex];
    Out.SimplificationMethod = static_cast<uint8>(Selected.SimplificationMethod);
    if (!FMath::IsFinite(Selected.TransitionScreenSize) || Selected.TransitionScreenSize <= 0 ||
        Selected.TransitionScreenSize > 1 || WorldSettings->HLODBakingTransform.ContainsNaN())
        return Fail(Out, TEXT("Invalid HLOD transition field or baking transform"));
    // Use the reflected struct, avoiding an unexported struct StaticStruct symbol.
    LocalInner->Struct->ExportText(
        Out.EffectiveSettingsText, &(*Levels)[Out.LodIndex], nullptr, WorldSettings, PPF_None, nullptr, false);
    if (Out.EffectiveSettingsText.Len() > 65536)
        return Fail(Out, TEXT("Effective settings export exceeds bound"));
    // Base-material precedence differs from effective hierarchy precedence.
    auto Material = Global->BaseMaterial;
    if (!WorldSettings->OverrideBaseMaterial.IsNull()) Material = WorldSettings->OverrideBaseMaterial;
    if (LocalSetup && !LocalSetup->OverrideBaseMaterial.IsNull()) Material = LocalSetup->OverrideBaseMaterial;
    Out.EffectiveBaseMaterialPath = Material.ToSoftObjectPath().ToString();
    if (!Material.IsNull() && !Material.Get())
    {
        Out.RequiredLoadedObjects.AddUnique(Out.EffectiveBaseMaterialPath);
        return Fail(Out, TEXT("Exact effective base material is not loaded"));
    }
    Out.BakingTransform = WorldSettings->HLODBakingTransform;
    Out.bSettingsObserved = true;
    return true;
}

inline bool ActorOverrides(ALODActor* Actor, FClosureRead& Out)
{
    Out.bActorOverrideMaterialMergeSettings = Actor->bOverrideMaterialMergeSettings;
    Out.bActorOverrideScreenSize = Actor->bOverrideScreenSize;
    Out.bActorOverrideTransitionScreenSize = Actor->bOverrideTransitionScreenSize;
    Out.ActorScreenSize = Actor->ScreenSize;
    Out.ActorTransitionScreenSize = Actor->TransitionScreenSize;
    if ((Out.bActorOverrideScreenSize && Out.ActorScreenSize <= 0) ||
        (Out.bActorOverrideTransitionScreenSize &&
            (!FMath::IsFinite(Out.ActorTransitionScreenSize) || Out.ActorTransitionScreenSize <= 0)))
        return Fail(Out, TEXT("Invalid enabled actor screen override"));
    const FStructProperty* Material = FindFProperty<FStructProperty>(
        ALODActor::StaticClass(), TEXT("MaterialSettings"));
    if (!Material || !Material->Struct ||
        Material->Struct->GetPathName() != TEXT("/Script/Engine.MaterialProxySettings"))
        return Fail(Out, TEXT("Unknown actor material override struct"));
    Material->Struct->ExportText(Out.ActorMaterialSettingsText,
        Material->ContainerPtrToValuePtr<void>(Actor), nullptr, Actor, PPF_None, nullptr, false);
    if (Out.ActorMaterialSettingsText.Len() > 65536)
        return Fail(Out, TEXT("Actor material override export exceeds bound"));
    // Installed Simplify applies all three overrides; Merge applies material
    // settings. These raw facts are not silently folded into every method.
    Out.bActorOverridesObserved = true;
    return true;
}

// Native owner supplies the actual current editor world. No GEditor singleton,
// realm switch, async task processing, cluster creation or build is invoked here.
inline FClosureRead ReadLoadedClosure(UWorld* CurrentWorld, const FReadRequest& Request)
{
    FClosureRead Out;
    if (!IsInGameThread() || !IsValid(CurrentWorld) || CurrentWorld->IsPlayInEditor() ||
        Request.WorldPath != TEXT("/Game/Daedalus/DaedalusWorld.DaedalusWorld") ||
        Request.LodActorPath.Len() > 512 ||
        CurrentWorld->GetPathName() != Request.WorldPath || CurrentWorld->GetWorldPartition() != nullptr ||
        Request.MaxCandidates < 1 || Request.MaxCandidates > 128 ||
        Request.MaxSources < 1 || Request.MaxSources > 128 ||
        Request.MaxComponents < 2 || Request.MaxComponents > 512 ||
        Request.MaxPackageObjects < 1 || Request.MaxPackageObjects > 4096 ||
        Request.MaxReferenceComponents < 1 || Request.MaxReferenceComponents > 32768)
    {
        Fail(Out, TEXT("Wrong world/mode/thread or read bounds"));
        return Out;
    }
    if (!Identity(CurrentWorld, Out.World, Out)) return Out;
    if (Request.LodActorPath.IsEmpty())
    {
        // Explicitly omit OnlyActiveLevels. The installed iterator constructs
        // temporary world/class pointer arrays and registers a scoped spawn
        // delegate; this output cap is not a bound on that internal setup work.
        for (TActorIterator<ALODActor> It(CurrentWorld, ALODActor::StaticClass(), EActorIteratorFlags::SkipPendingKill); It; ++It)
        {
            if (Out.Candidates.Num() >= Request.MaxCandidates)
            {
                Fail(Out, TEXT("Existing LODActor candidate count exceeds bound"));
                return Out;
            }
            FIdentity Candidate;
            if (!Identity(*It, Candidate, Out)) return Out;
            Out.Candidates.Add(MoveTemp(Candidate));
        }
        Out.Candidates.Sort([](const FIdentity& A, const FIdentity& B) { return A.Path < B.Path; });
        Out.State = TEXT("EXACT_EXISTING_TARGET_REQUIRED");
        Out.Reason = Out.Candidates.IsEmpty() ? TEXT("No candidate observed in the current world's loaded member levels; configured/unloaded/nonmember levels remain outside this inventory") :
            TEXT("Bind one useful owned existing candidate; no automatic cluster selection");
        return Out;
    }
    ALODActor* Actor = FindObject<ALODActor>(nullptr, *Request.LodActorPath);
    if (!IsValid(Actor) || Actor->GetPathName() != Request.LodActorPath || Actor->GetWorld() != CurrentWorld ||
        !Identity(Actor, Out.LodActor, Out))
    {
        Fail(Out, TEXT("Exact existing loaded LODActor is unavailable in the current world"));
        return Out;
    }
    ULevel* Level = Actor->GetLevel();
    AWorldSettings* WorldSettings = Level ? Level->GetWorldSettings(false) : nullptr;
    if (!WorldSettings || WorldSettings->GetLevel() != Level ||
        !Identity(Level, Out.Level, Out) || !Identity(WorldSettings, Out.WorldSettings, Out))
    {
        Fail(Out, TEXT("Exact cluster level/WorldSettings is unavailable"));
        return Out;
    }
    Out.LodLevelOneBased = Actor->LODLevel;
    Out.LodIndex = Actor->LODLevel - 1;
    if (Out.LodIndex < 0 || Actor->SubActors.IsEmpty() || Actor->SubActors.Num() > Request.MaxSources)
    {
        Fail(Out, TEXT("Invalid legacy actor tier or finite source count"));
        return Out;
    }
    if (!Settings(WorldSettings, Out) || !ActorOverrides(Actor, Out)) return Out;
    TSet<FString> Seen;
    for (AActor* Source : Actor->SubActors)
    {
        if (!IsValid(Source) || Source->IsA<ALODActor>() || Source->GetWorld() != CurrentWorld ||
            Source->GetLevel() != Level || Seen.Contains(Source->GetPathName()))
        {
            Fail(Out, TEXT("Null/duplicate/foreign/nested source requires a separate exact leaf closure"));
            return Out;
        }
        Seen.Add(Source->GetPathName());
        FIdentity Row;
        if (!Identity(Source, Row, Out)) return Out;
        Out.Sources.Add(MoveTemp(Row));
        Package(Source->GetPackage(), Out);
    }
    TArray<UPrimitiveComponent*> Components;
    UHLODProxy::ExtractComponents(Actor, Components); // Native source filters actual ShouldGenerateAutoLOD.
    if (Components.Num() < 2 || Components.Num() > Request.MaxComponents)
    {
        Fail(Out, TEXT("Actual legacy source components are empty/insufficient/unbounded"));
        return Out;
    }
    for (UPrimitiveComponent* Primitive : Components)
    {
        UStaticMeshComponent* Component = Cast<UStaticMeshComponent>(Primitive);
        if (!Component || !Component->GetStaticMesh() || Component->GetNumMaterials() > 64)
        {
            Fail(Out, TEXT("Unknown source mesh/material component"));
            return Out;
        }
        FComponentRead Row;
        if (!Identity(Component, Row.Component, Out) || !Identity(Component->GetStaticMesh(), Row.Mesh, Out)) return Out;
        Row.WorldTransform = Component->GetComponentTransform();
        if (Row.WorldTransform.ContainsNaN())
        {
            Fail(Out, TEXT("Invalid source component transform"));
            return Out;
        }
        for (int32 Index = 0; Index < Component->GetNumMaterials(); ++Index)
        {
            FIdentity Material;
            // Editor assignment only: avoid runtime Nanite material resolution.
            if (!Identity(Component->GetEditorMaterial(Index), Material, Out)) return Out;
            Row.Materials.Add(MoveTemp(Material));
        }
        Out.Components.Add(MoveTemp(Row));
    }
    UHLODProxy* Proxy = Actor->GetProxy();
    if (!Proxy || !Identity(Proxy, Out.Proxy, Out))
    {
        Fail(Out, TEXT("Existing proxy is missing; no asset/package is created by this read"));
        return Out;
    }
    UStaticMeshComponent* ProxyComponent = Actor->GetStaticMeshComponent();
    if (!ProxyComponent || !Identity(ProxyComponent, Out.ExistingProxyComponent, Out)) return Out;
    Out.ExistingProxyTransform = ProxyComponent->GetComponentTransform();
    if (Out.ExistingProxyTransform.ContainsNaN())
    {
        Fail(Out, TEXT("Invalid existing proxy component transform"));
        return Out;
    }
    Out.bExistingProxyTransformObserved = true;
    if (ProxyComponent->GetStaticMesh() && !Identity(ProxyComponent->GetStaticMesh(), Out.ExistingProxyMesh, Out)) return Out;
    Out.ProxyMapPath = Proxy->GetMap().ToSoftObjectPath().ToString();
    UWorld* LevelWorld = Cast<UWorld>(Level->GetOuter());
    if (!LevelWorld || Proxy->GetMap().Get() != LevelWorld)
    {
        Fail(Out, TEXT("Proxy owner map is wrong or not loaded"));
        return Out;
    }
    // Mirror installed package-name projection, without loading any level.
    const FString OuterLevelPackage = Level->GetOutermost()->GetName();
    FString LoadLevelPackage = OuterLevelPackage;
    if (ULevelStreaming* Streaming = FLevelUtils::FindStreamingLevel(Level))
        LoadLevelPackage = Streaming->PackageNameToLoad != NAME_None ?
            Streaming->PackageNameToLoad.ToString() : Streaming->GetWorldAssetPackageName();
    if (!FPackageName::IsValidLongPackageName(LoadLevelPackage))
    {
        Fail(Out, TEXT("Unknown canonical source level package"));
        return Out;
    }
    // Engine uses outer-level short name for the object but the source load
    // package for the package path (relevant to existing level instances).
    Out.ExpectedProxyName = FString::Printf(TEXT("%s_%d_HLOD"), *FPackageName::GetShortName(OuterLevelPackage), Out.LodIndex);
    const FString PackageBase = FString::Printf(TEXT("%s_%d_HLOD"), *FPackageName::GetShortName(LoadLevelPackage), Out.LodIndex);
    Out.ExpectedProxyPackage = FPackageName::GetLongPackagePath(LoadLevelPackage) + TEXT("/HLOD/") + PackageBase;
    UPackage* Shared = Proxy->GetOutermost();
    if (Shared->GetName() != Out.ExpectedProxyPackage || Proxy->GetName() != Out.ExpectedProxyName)
    {
        Fail(Out, TEXT("Actor proxy differs from the builder's existing canonical level/tier proxy"));
        return Out;
    }
    Package(Actor->GetPackage(), Out);
    Package(Level->GetOutermost(), Out);
    Package(Shared, Out);
    if (!Shared->IsFullyLoaded())
    {
        Out.RequiredFullyLoadedPackages.Add(Shared->GetName());
        Fail(Out, TEXT("Shared proxy package is partially loaded; no complete cleanup inventory claim"));
        return Out;
    }
    bool bComplete = true;
    TSet<UStaticMesh*> SharedMeshes;
    // Private reflected containers can refer to meshes outside this package.
    // Inspect their native typed values without resolving soft references.
    const FArrayProperty* MeshArray = FindFProperty<FArrayProperty>(UHLODProxy::StaticClass(), TEXT("ProxyMeshes"));
    const FMapProperty* ActorMap = FindFProperty<FMapProperty>(UHLODProxy::StaticClass(), TEXT("HLODActors"));
    const FStructProperty* ArrayInner = MeshArray ? CastField<FStructProperty>(MeshArray->Inner) : nullptr;
    const FStructProperty* MapValue = ActorMap ? CastField<FStructProperty>(ActorMap->ValueProp) : nullptr;
    if (!ArrayInner || !MapValue || !ArrayInner->Struct || !MapValue->Struct ||
        ArrayInner->Struct != MapValue->Struct ||
        ArrayInner->Struct->GetPathName() != TEXT("/Script/Engine.HLODProxyMesh"))
    {
        Fail(Out, TEXT("Unknown reflected proxy membership container types"));
        return Out;
    }
    const FObjectProperty* MeshMember = FindFProperty<FObjectProperty>(ArrayInner->Struct, TEXT("StaticMesh"));
    if (!MeshMember || MeshMember->PropertyClass != UStaticMesh::StaticClass() || MeshMember->HasGetter())
    {
        Fail(Out, TEXT("Proxy membership is not the expected native hard StaticMesh property"));
        return Out;
    }
    // GetStaticMesh is out-of-line without ENGINE_API on FHLODProxyMesh.
    // Read the checked native hard object property instead of that DLL symbol.
    auto AddReferencedMesh = [&](const void* Membership)
    {
        // The _InContainer accessor routes through a resolving UObject* getter.
        // The checked native property's address + value accessor preserves the
        // TObjectPtr handle so the unresolved guard runs before Pointer.Get().
        const void* MemberAddress = MeshMember->ContainerPtrToValuePtr<void>(Membership);
        const TObjectPtr<UObject> Pointer = MeshMember->GetObjectPtrPropertyValue(MemberAddress);
        if (!Pointer.IsResolved())
            return Fail(Out, TEXT("Proxy membership hard object handle is unresolved"));
        UStaticMesh* Mesh = Cast<UStaticMesh>(Pointer.Get());
        if (!Mesh || SharedMeshes.Contains(Mesh)) return true;
        if (SharedMeshes.Num() >= Request.MaxPackageObjects)
            return Fail(Out, TEXT("Proxy mesh membership exceeds bound"));
        FIdentity Row;
        if (!Identity(Mesh, Row, Out)) return false;
        SharedMeshes.Add(Mesh);
        Out.ReferencedProxyMeshes.Add(MoveTemp(Row));
        Package(Mesh->GetPackage(), Out);
        return true;
    };
    FScriptArrayHelper Membership(MeshArray, MeshArray->ContainerPtrToValuePtr<void>(Proxy));
    FScriptMapHelper MapHelper(ActorMap, ActorMap->ContainerPtrToValuePtr<void>(Proxy));
    if (Membership.Num() > Request.MaxPackageObjects || MapHelper.Num() > Request.MaxPackageObjects ||
        MapHelper.GetMaxIndex() > Request.MaxPackageObjects)
    {
        Fail(Out, TEXT("Proxy membership read exceeds bound"));
        return Out;
    }
    for (int32 Index = 0; Index < Membership.Num(); ++Index)
        if (!AddReferencedMesh(Membership.GetRawPtr(Index))) return Out;
    for (int32 Index = 0; Index < MapHelper.GetMaxIndex(); ++Index)
        if (MapHelper.IsValidIndex(Index) && !AddReferencedMesh(MapHelper.GetValuePtr(Index))) return Out;
    ForEachObjectWithPackage(Shared, [&](UObject* Object)
    {
        if (Out.SharedProxyPackageObjects.Num() >= Request.MaxPackageObjects)
            return bComplete = Fail(Out, TEXT("Shared package object count exceeds bound"));
        FIdentity Row;
        if (!Identity(Object, Row, Out)) return bComplete = false;
        if (UStaticMesh* Mesh = Cast<UStaticMesh>(Object)) SharedMeshes.Add(Mesh);
        Out.SharedProxyPackageObjects.Add(MoveTemp(Row));
        return true;
    }, EGetObjectsFlags::IncludeNestedObjects);
    if (!bComplete) return Out;
    // RemoveAssets can SetStaticMesh(nullptr) on loaded users outside this
    // package. Read one loaded component class, retain only exact shared meshes.
    // Do not instantiate the render-state recreation context (it mutates state).
    int32 Visited = 0;
    for (TObjectIterator<UStaticMeshComponent> It; It; ++It)
    {
        if (++Visited > Request.MaxReferenceComponents)
        {
            Fail(Out, TEXT("Shared mesh user reference read exceeds bound; no complete closure claim"));
            return Out;
        }
        UStaticMeshComponent* Component = *It;
        if (!SharedMeshes.Contains(Component->GetStaticMesh())) continue;
        FIdentity Row;
        if (!Identity(Component, Row, Out)) return Out;
        Out.LoadedSharedMeshUsers.Add(MoveTemp(Row));
        Package(Component->GetPackage(), Out);
        if (AActor* Owner = Component->GetOwner()) Package(Owner->GetPackage(), Out);
    }
    Out.Sources.Sort([](const FIdentity& A, const FIdentity& B) { return A.Path < B.Path; });
    Out.Components.Sort([](const FComponentRead& A, const FComponentRead& B) { return A.Component.Path < B.Component.Path; });
    Out.SharedProxyPackageObjects.Sort([](const FIdentity& A, const FIdentity& B) { return A.Path < B.Path; });
    Out.ReferencedProxyMeshes.Sort([](const FIdentity& A, const FIdentity& B) { return A.Path < B.Path; });
    Out.LoadedSharedMeshUsers.Sort([](const FIdentity& A, const FIdentity& B) { return A.Path < B.Path; });
    Out.Packages.Sort([](const FPackageRead& A, const FPackageRead& B) { return A.Name < B.Name; });
    Out.bLoadedInventoryComplete = true;
    Out.State = TEXT("LOADED_CLOSURE_READ_ONLY_BUILD_STILL_UNADMITTED");
    Out.Reason = TEXT("Native owner must bind this exact read to source/file pins, affected-package admission, resource custody and actual future completion/save/reopen. Shared cleanup/global GC/deferred build are not isolated by one target.");
    return Out;
}
// Complete JSON projection for the existing acceptance-library wrapper. This
// does not reflect a new method or acquire an editor world/transport itself.
inline FString SerializeLoadedClosure(const FClosureRead& Read)
{
    const auto RejectedSerialization = []()
    {
        return FString(TEXT("{\"schema\":\"daedalus.legacy_hlod_closure.v1\",\"state\":\"HELD\",\"reason\":\"Closure serialization invalid or exceeds 262144 UTF-8 bytes\",\"read_only\":true,\"loaded_inventory_complete\":false,\"build_admitted\":false,\"serialization_complete\":false,\"truncated\":false}"));
    };
    if (!Read.bReadOnly || Read.bBuildAdmitted) return RejectedSerialization();
    bool bFinite = true;
    const auto Null = []() -> TSharedPtr<FJsonValue> { return MakeShared<FJsonValueNull>(); };
    const auto OptionalString = [&](const FString& Value) -> TSharedPtr<FJsonValue>
    {
        return Value.IsEmpty() ? Null() : MakeShared<FJsonValueString>(Value);
    };
    const auto Id = [&](const FIdentity& Value) -> TSharedPtr<FJsonValue>
    {
        if (Value.Path.IsEmpty()) return Null();
        TSharedRef<FJsonObject> Json = MakeShared<FJsonObject>();
        Json->SetStringField(TEXT("path"), Value.Path);
        Json->SetStringField(TEXT("class_path"), Value.ClassPath);
        Json->SetStringField(TEXT("outer_package"), Value.OuterPackage);
        Json->SetStringField(TEXT("save_package"), Value.SavePackage);
        Json->SetNumberField(TEXT("object_flags"), static_cast<double>(Value.Flags));
        return MakeShared<FJsonValueObject>(Json);
    };
    const auto Ids = [&](const TArray<FIdentity>& Values)
    {
        TArray<TSharedPtr<FJsonValue>> Json;
        Json.Reserve(Values.Num());
        for (const FIdentity& Value : Values) Json.Add(Id(Value));
        return Json;
    };
    const auto Strings = [&](const TArray<FString>& Values)
    {
        TArray<TSharedPtr<FJsonValue>> Json;
        Json.Reserve(Values.Num());
        for (const FString& Value : Values) Json.Add(MakeShared<FJsonValueString>(Value));
        return Json;
    };
    const auto Numbers = [&](std::initializer_list<double> Values)
    {
        TArray<TSharedPtr<FJsonValue>> Json;
        for (double Value : Values)
        {
            if (!FMath::IsFinite(Value)) bFinite = false;
            Json.Add(FMath::IsFinite(Value) ? TSharedPtr<FJsonValue>(MakeShared<FJsonValueNumber>(Value)) : Null());
        }
        return Json;
    };
    const auto Transform = [&](const FTransform& Value, bool bObserved) -> TSharedPtr<FJsonValue>
    {
        if (!bObserved) return Null();
        const FVector Translation = Value.GetTranslation();
        const FVector Scale = Value.GetScale3D();
        const FQuat Rotation = Value.GetRotation();
        TSharedRef<FJsonObject> Json = MakeShared<FJsonObject>();
        Json->SetArrayField(TEXT("translation_native_units"), Numbers({Translation.X, Translation.Y, Translation.Z}));
        Json->SetArrayField(TEXT("rotation_quat_xyzw"), Numbers({Rotation.X, Rotation.Y, Rotation.Z, Rotation.W}));
        Json->SetArrayField(TEXT("scale_xyz"), Numbers({Scale.X, Scale.Y, Scale.Z}));
        return MakeShared<FJsonValueObject>(Json);
    };
    TSharedRef<FJsonObject> Json = MakeShared<FJsonObject>();
    Json->SetStringField(TEXT("schema"), TEXT("daedalus.legacy_hlod_closure.v1"));
    Json->SetStringField(TEXT("state"), Read.State);
    Json->SetValue(TEXT("reason"), OptionalString(Read.Reason));
    Json->SetBoolField(TEXT("read_only"), Read.bReadOnly);
    Json->SetBoolField(TEXT("loaded_inventory_complete"), Read.bLoadedInventoryComplete);
    Json->SetBoolField(TEXT("build_admitted"), false);
    Json->SetBoolField(TEXT("serialization_complete"), true);
    Json->SetBoolField(TEXT("truncated"), false);
    Json->SetStringField(TEXT("candidate_scope"), Read.CandidateScope);
    Json->SetValue(TEXT("world"), Id(Read.World));
    Json->SetValue(TEXT("lod_actor"), Id(Read.LodActor));
    Json->SetValue(TEXT("level"), Id(Read.Level));
    Json->SetValue(TEXT("world_settings"), Id(Read.WorldSettings));
    Json->SetValue(TEXT("proxy"), Id(Read.Proxy));
    Json->SetValue(TEXT("existing_proxy_component"), Id(Read.ExistingProxyComponent));
    Json->SetValue(TEXT("existing_proxy_mesh"), Id(Read.ExistingProxyMesh));
    Json->SetBoolField(TEXT("existing_proxy_transform_observed"), Read.bExistingProxyTransformObserved);
    Json->SetValue(TEXT("existing_proxy_transform"), Transform(Read.ExistingProxyTransform, Read.bExistingProxyTransformObserved));
    Json->SetValue(TEXT("proxy_map_path"), OptionalString(Read.ProxyMapPath));
    Json->SetValue(TEXT("expected_proxy_name"), OptionalString(Read.ExpectedProxyName));
    Json->SetValue(TEXT("expected_proxy_package"), OptionalString(Read.ExpectedProxyPackage));
    Json->SetValue(TEXT("lod_level_one_based"), Read.LodLevelOneBased > 0 ? TSharedPtr<FJsonValue>(MakeShared<FJsonValueNumber>(Read.LodLevelOneBased)) : Null());
    Json->SetValue(TEXT("lod_index"), Read.LodIndex >= 0 ? TSharedPtr<FJsonValue>(MakeShared<FJsonValueNumber>(Read.LodIndex)) : Null());
    Json->SetBoolField(TEXT("settings_observed"), Read.bSettingsObserved);
    Json->SetValue(TEXT("settings_source"), OptionalString(Read.SettingsSource));
    Json->SetValue(TEXT("selected_level_settings_text"), OptionalString(Read.EffectiveSettingsText));
    Json->SetValue(TEXT("simplification_method"), Read.bSettingsObserved ? TSharedPtr<FJsonValue>(MakeShared<FJsonValueNumber>(Read.SimplificationMethod)) : Null());
    Json->SetValue(TEXT("effective_base_material_path"), OptionalString(Read.EffectiveBaseMaterialPath));
    Json->SetValue(TEXT("baking_transform"), Transform(Read.BakingTransform, Read.bSettingsObserved));
    Json->SetValue(TEXT("save_lod_actors_to_proxy_package"), Read.bSettingsObserved ? TSharedPtr<FJsonValue>(MakeShared<FJsonValueBoolean>(Read.bSaveLodActorsToProxyPackage)) : Null());
    Json->SetBoolField(TEXT("actor_overrides_observed"), Read.bActorOverridesObserved);
    Json->SetValue(TEXT("actor_override_material_merge_settings"), Read.bActorOverridesObserved ? TSharedPtr<FJsonValue>(MakeShared<FJsonValueBoolean>(Read.bActorOverrideMaterialMergeSettings)) : Null());
    Json->SetValue(TEXT("actor_override_screen_size"), Read.bActorOverridesObserved ? TSharedPtr<FJsonValue>(MakeShared<FJsonValueBoolean>(Read.bActorOverrideScreenSize)) : Null());
    Json->SetValue(TEXT("actor_override_transition_screen_size"), Read.bActorOverridesObserved ? TSharedPtr<FJsonValue>(MakeShared<FJsonValueBoolean>(Read.bActorOverrideTransitionScreenSize)) : Null());
    Json->SetValue(TEXT("actor_screen_size"), Read.bActorOverridesObserved ? TSharedPtr<FJsonValue>(MakeShared<FJsonValueNumber>(Read.ActorScreenSize)) : Null());
    if (Read.bActorOverridesObserved && !FMath::IsFinite(Read.ActorTransitionScreenSize)) bFinite = false;
    Json->SetValue(TEXT("actor_transition_screen_size"), Read.bActorOverridesObserved && FMath::IsFinite(Read.ActorTransitionScreenSize) ? TSharedPtr<FJsonValue>(MakeShared<FJsonValueNumber>(Read.ActorTransitionScreenSize)) : Null());
    Json->SetValue(TEXT("actor_material_settings_text"), OptionalString(Read.ActorMaterialSettingsText));
    Json->SetArrayField(TEXT("candidates"), Ids(Read.Candidates));
    Json->SetArrayField(TEXT("sources"), Ids(Read.Sources));
    TArray<TSharedPtr<FJsonValue>> Components;
    Components.Reserve(Read.Components.Num());
    for (const FComponentRead& Value : Read.Components)
    {
        TSharedRef<FJsonObject> Component = MakeShared<FJsonObject>();
        Component->SetValue(TEXT("component"), Id(Value.Component));
        Component->SetValue(TEXT("mesh"), Id(Value.Mesh));
        Component->SetValue(TEXT("world_transform"), Transform(Value.WorldTransform, true));
        Component->SetArrayField(TEXT("materials"), Ids(Value.Materials));
        Components.Add(MakeShared<FJsonValueObject>(Component));
    }
    Json->SetArrayField(TEXT("components"), Components);
    Json->SetArrayField(TEXT("shared_proxy_package_objects"), Ids(Read.SharedProxyPackageObjects));
    Json->SetArrayField(TEXT("referenced_proxy_meshes"), Ids(Read.ReferencedProxyMeshes));
    Json->SetArrayField(TEXT("loaded_shared_mesh_users"), Ids(Read.LoadedSharedMeshUsers));
    TArray<TSharedPtr<FJsonValue>> Packages;
    Packages.Reserve(Read.Packages.Num());
    for (const FPackageRead& Value : Read.Packages)
    {
        TSharedRef<FJsonObject> PackageJson = MakeShared<FJsonObject>();
        PackageJson->SetStringField(TEXT("name"), Value.Name);
        PackageJson->SetBoolField(TEXT("dirty"), Value.bDirty);
        PackageJson->SetBoolField(TEXT("fully_loaded"), Value.bFullyLoaded);
        Packages.Add(MakeShared<FJsonValueObject>(PackageJson));
    }
    Json->SetArrayField(TEXT("packages"), Packages);
    Json->SetArrayField(TEXT("required_loaded_objects"), Strings(Read.RequiredLoadedObjects));
    Json->SetArrayField(TEXT("required_existing_default_object_classes"), Strings(Read.RequiredExistingDefaultObjectClasses));
    Json->SetArrayField(TEXT("required_fully_loaded_packages"), Strings(Read.RequiredFullyLoadedPackages));
    Json->SetNumberField(TEXT("identity_characters"), Read.IdentityCharacters);
    if (!bFinite) return RejectedSerialization();
    FString Serialized;
    if (!FJsonSerializer::Serialize(Json, TJsonWriterFactory<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>::Create(&Serialized)))
        return RejectedSerialization();
    const FTCHARToUTF8 Utf8(*Serialized);
    if (Utf8.Length() > 262144) return RejectedSerialization();
    return Serialized;
}

inline FString ReadLoadedClosureJson(UWorld* CurrentWorld, const FString& LodActorObjectPath)
{
    if (LodActorObjectPath.Len() > 512)
    {
        FClosureRead Rejected;
        Fail(Rejected, TEXT("Exact actor path exceeds 512 characters"));
        return SerializeLoadedClosure(Rejected);
    }
    FReadRequest Request;
    Request.LodActorPath = LodActorObjectPath;
    return SerializeLoadedClosure(ReadLoadedClosure(CurrentWorld, Request));
}
} // namespace DaedalusLegacyHlod
#endif // WITH_EDITOR
