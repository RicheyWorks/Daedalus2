// SPDX-License-Identifier: MIT
#include "DaedalusUnicornPackEventComponent.h"
#include "DaedalusUnicornRewardComponent.h"
#include "Components/PrimitiveComponent.h"
#include "GameFramework/Actor.h"
#include "Engine/World.h"

UDaedalusUnicornPackEventComponent::UDaedalusUnicornPackEventComponent() { PrimaryComponentTick.bCanEverTick = false; }
bool UDaedalusUnicornPackEventComponent::Authority() const
{
    return GetOwner() && GetOwner()->HasAuthority() && GetWorld() && GetWorld()->IsGameWorld();
}
bool UDaedalusUnicornPackEventComponent::MembershipValid() const
{
    if (PackMembers.Num() != 12) return false;
    TSet<AActor*> Unique;
    for (const auto& Member : PackMembers)
    {
        AActor* Actor = Member.Get();
        if (!Actor || Actor->GetWorld() != GetWorld() || !Actor->HasAuthority() ||
            !Actor->ActorHasTag(TEXT("DaedalusUnicornFemale")) || Unique.Contains(Actor)) return false;
        Unique.Add(Actor);
    }
    return Unique.Num() == 12;
}
bool UDaedalusUnicornPackEventComponent::ConfigureHostPack(const FString& StablePackId, const TArray<AActor*>& Members, UPrimitiveComponent* Zone)
{
    if (!Authority() || !PackId.IsEmpty() || !IsValid(Zone) || Zone->GetOwner() != GetOwner() ||
        !Zone->GetGenerateOverlapEvents() || Members.Num() != 12) return false;
    const FTCHARToUTF8 Encoded(*StablePackId);
    if (!DaedalusUnicornReward::Gate::ValidEntityIdentity(std::string(Encoded.Get(), Encoded.Length()))) return false;
    for (AActor* Member : Members) PackMembers.Add(Member);
    if (!MembershipValid()) { PackMembers.Reset(); return false; }
    PackId = StablePackId;
    EncounterZone = Zone;
    Zone->OnComponentBeginOverlap.AddDynamic(this, &UDaedalusUnicornPackEventComponent::OnZoneEnter);
    Zone->OnComponentEndOverlap.AddDynamic(this, &UDaedalusUnicornPackEventComponent::OnZoneExit);
    return true;
}
bool UDaedalusUnicornPackEventComponent::TryRecordEncounter(AActor* PlayerActor)
{
    UPrimitiveComponent* Zone = EncounterZone.Get();
    if (!Authority() || bRecordingEncounter || !Zone || !IsValid(PlayerActor) ||
        PlayerActor->GetWorld() != GetWorld() || !PlayerActor->HasAuthority() ||
        !Zone->IsOverlappingActor(PlayerActor) || !MembershipValid()) return false;
    auto* Player = PlayerActor->FindComponentByClass<UDaedalusUnicornRewardComponent>();
    if (!Player) return false;
    if (!Player->bRecordReady)
    {
        PendingPlayers.Add(Player);
        Player->OnRecordStatus.AddUniqueDynamic(this, &UDaedalusUnicornPackEventComponent::OnPlayerReady);
        return false;
    }
    TGuardValue<bool> Guard(bRecordingEncounter, true);
    const auto Record = Player->ExportHostRecord();
    const bool Accepted = (Record.bAvailable && !Record.PackId.IsEmpty()) || Player->RecordPackEncounter(PackId, 12, true);
    if (Accepted) ForgetPlayer(Player);
    return Accepted;
}
void UDaedalusUnicornPackEventComponent::ForgetPlayer(UDaedalusUnicornRewardComponent* Player)
{
    if (!Player) return;
    PendingPlayers.Remove(Player);
    Player->OnRecordStatus.RemoveDynamic(this, &UDaedalusUnicornPackEventComponent::OnPlayerReady);
}
void UDaedalusUnicornPackEventComponent::OnZoneEnter(UPrimitiveComponent*, AActor* Other, UPrimitiveComponent*, int32, bool, const FHitResult&)
{
    TryRecordEncounter(Other);
}
void UDaedalusUnicornPackEventComponent::OnZoneExit(UPrimitiveComponent*, AActor* Other, UPrimitiveComponent*, int32)
{
    if (Other) ForgetPlayer(Other->FindComponentByClass<UDaedalusUnicornRewardComponent>());
}
void UDaedalusUnicornPackEventComponent::OnPlayerReady(bool Ready, bool, int64)
{
    if (!Ready || bRecordingEncounter) return;
    const auto Waiting = PendingPlayers.Array();
    for (const auto& Weak : Waiting)
        if (auto* Player = Weak.Get()) TryRecordEncounter(Player->GetOwner());
}
void UDaedalusUnicornPackEventComponent::EndPlay(const EEndPlayReason::Type Reason)
{
    if (auto* Zone = EncounterZone.Get())
    {
        Zone->OnComponentBeginOverlap.RemoveDynamic(this, &UDaedalusUnicornPackEventComponent::OnZoneEnter);
        Zone->OnComponentEndOverlap.RemoveDynamic(this, &UDaedalusUnicornPackEventComponent::OnZoneExit);
    }
    const auto Waiting = PendingPlayers.Array();
    for (const auto& Weak : Waiting) if (auto* Player = Weak.Get()) ForgetPlayer(Player);
    PendingPlayers.Reset();
    Super::EndPlay(Reason);
}
