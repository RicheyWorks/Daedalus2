// SPDX-License-Identifier: MIT
#include "DaedalusPCGFixtureOwnerLibrary.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonWriter.h"
#if WITH_EDITOR
#include "Editor.h"
#include "Engine/Level.h"
#include "Engine/World.h"
#include "PCGComponent.h"
#include "GameFramework/Actor.h"
#include "Components/BoxComponent.h"
#include "UObject/Package.h"
#endif

namespace PCGFixtureOwner
{
    static FString Reply(bool bOK, const FString& Diagnostic, const FString& Actor = FString(), const FString& Component = FString(), bool bBusy = false)
    {
        TSharedRef<FJsonObject> Object = MakeShared<FJsonObject>();
        Object->SetBoolField(TEXT("ok"), bOK);
        Object->SetStringField(TEXT("diagnostic"), Diagnostic);
        Object->SetStringField(TEXT("actor_path"), Actor);
        Object->SetStringField(TEXT("component_path"), Component);
        Object->SetBoolField(TEXT("busy"), bBusy);
        FString Text;
        TSharedRef<TJsonWriter<>> Writer = TJsonWriterFactory<>::Create(&Text);
        FJsonSerializer::Serialize(Object, Writer);
        return Text;
    }
#if WITH_EDITOR
    static TWeakObjectPtr<AActor> Owner;
    static TWeakObjectPtr<UWorld> OwnerWorld;
    static const FName OwnerName(TEXT("CodexOwnedPCGFixture_20261021_R1"));

    static UWorld* CurrentWorld()
    {
        if (!IsInGameThread() || !GEditor || GEditor->PlayWorld || GUndo)
            return nullptr;
        UWorld* World = GEditor->GetEditorWorldContext().World();
        return World && World->WorldType == EWorldType::Editor
            && World->GetPathName() == TEXT("/Game/Daedalus/DaedalusWorld.DaedalusWorld") ? World : nullptr;
    }

    static bool Matches(AActor* Actor, UWorld* World)
    {
        return Actor && World && World == OwnerWorld.Get() && Actor == Owner.Get()
            && Actor->GetWorld() == World && Actor->GetLevel() == World->PersistentLevel
            && Actor->GetFName() == OwnerName && Actor->HasAnyFlags(RF_Transient)
            && !Actor->HasAnyFlags(RF_Transactional);
    }
#endif
}

FString UDaedalusPCGFixtureOwnerLibrary::CreateOwnedFixture()
{
#if WITH_EDITOR
    using namespace PCGFixtureOwner;
    UWorld* World = CurrentWorld();
    if (!World || !World->PersistentLevel || World->GetOutermost()->IsDirty())
        return Reply(false, TEXT("Clean exact editor world with no PIE/transaction required"));
    if (Owner.IsValid() || FindObject<UObject>(World->PersistentLevel, *OwnerName.ToString()))
        return Reply(false, TEXT("Owned fixture or name already exists; never replace"));
    FActorSpawnParameters Params;
    Params.Name = OwnerName;
    Params.ObjectFlags = RF_Transient;
    Params.OverrideLevel = World->PersistentLevel;
    Params.bCreateActorPackage = false;
    Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    AActor* Actor = World->SpawnActor<AActor>(AActor::StaticClass(), FVector(700000, 700000, 300000), FRotator::ZeroRotator, Params);
    if (!Actor)
        return Reply(false, TEXT("Owned fixture spawn returned null"));
    Owner = Actor;
    OwnerWorld = World;
    UBoxComponent* Bounds = NewObject<UBoxComponent>(Actor, TEXT("OwnedPCGFixtureBounds"), RF_Transient);
    Bounds->SetBoxExtent(FVector(1000));
    Bounds->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Bounds->SetGenerateOverlapEvents(false);
    Actor->SetRootComponent(Bounds);
    Actor->AddInstanceComponent(Bounds);
    Bounds->RegisterComponent();
    Actor->SetActorLocation(FVector(700000, 700000, 300000));
    UPCGComponent* Component = NewObject<UPCGComponent>(Actor, TEXT("OwnedPCGFixtureComponent"), RF_Transient);
    Actor->AddInstanceComponent(Component);
    if (!Matches(Actor, World) || !Component || Component->GetOwner() != Actor)
        return Reply(false, TEXT("Created owner mismatch; retained for reconciliation"), Actor->GetPathName());
    Component->SetFlags(RF_Transient);
    Component->ClearFlags(RF_Transactional); // Owned fresh object only.
    Component->GenerationTrigger = EPCGComponentGenerationTrigger::GenerateOnDemand;
    Component->bGenerateOnDropWhenTriggerOnDemand = false;
    Component->SetIsPartitioned(false);
    Component->Seed = 42;
    Component->RegisterComponent();
    if (World->GetOutermost()->IsDirty())
        return Reply(false, TEXT("Fixture creation dirtied world; never clear dirty state"), Actor->GetPathName(), Component->GetPathName());
    return Reply(true, TEXT("Owned transient fixture created; no generation"), Actor->GetPathName(), Component->GetPathName());
#else
    return PCGFixtureOwner::Reply(false, TEXT("Editor only"));
#endif
}

FString UDaedalusPCGFixtureOwnerLibrary::DescribeOwnedFixture()
{
#if WITH_EDITOR
    using namespace PCGFixtureOwner;
    UWorld* World = CurrentWorld();
    AActor* Actor = Owner.Get();
    if (!Matches(Actor, World))
        return Reply(false, TEXT("No exact registered owned fixture"));
    UPCGComponent* Component = Actor->FindComponentByClass<UPCGComponent>();
    if (!Component)
        return Reply(false, TEXT("Owned component missing"));
    return Reply(true, TEXT("Registered transient fixture"), Actor->GetPathName(), Component->GetPathName(), Component->IsGenerating() || Component->IsCleaningUp());
#else
    return PCGFixtureOwner::Reply(false, TEXT("Editor only"));
#endif
}

FString UDaedalusPCGFixtureOwnerLibrary::DestroyOwnedFixture()
{
#if WITH_EDITOR
    using namespace PCGFixtureOwner;
    UWorld* World = CurrentWorld();
    AActor* Actor = Owner.Get();
    if (!Matches(Actor, World))
        return Reply(false, TEXT("No exact registered owned fixture; no arbitrary deletion"));
    UPCGComponent* Component = Actor->FindComponentByClass<UPCGComponent>();
    if (!Component || Component->IsGenerating() || Component->IsCleaningUp())
        return Reply(false, TEXT("Owned work pending or component absent; retain owner"), Actor->GetPathName(), Component ? Component->GetPathName() : FString(), true);
    const FString Path = Actor->GetPathName();
    Component->CleanupLocalImmediate(true);
    // No editor transaction, level Modify(), SaveAll, flag clearing or other actor cleanup.
    if (!World->DestroyActor(Actor, false, false))
        return Reply(false, TEXT("Owned destroy refused; retain registry"), Path);
    Owner.Reset();
    OwnerWorld.Reset();
    return Reply(!World->GetOutermost()->IsDirty(), World->GetOutermost()->IsDirty()
        ? TEXT("Destroyed own fixture but world dirty; preserve and reconcile") : TEXT("Owned fixture removed; world remains clean"), Path);
#else
    return PCGFixtureOwner::Reply(false, TEXT("Editor only"));
#endif
}
