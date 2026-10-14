// SPDX-License-Identifier: MIT
#include "DaedalusUnicornRewardComponent.h"
#include "GameFramework/Actor.h"
#include "Engine/World.h"
#include "Net/UnrealNetwork.h"

UDaedalusUnicornRewardComponent::UDaedalusUnicornRewardComponent()
{
    PrimaryComponentTick.bCanEverTick = false;
    SetIsReplicatedByDefault(true);
}

bool UDaedalusUnicornRewardComponent::CanRecord() const
{
    return GetOwner() && GetOwner()->HasAuthority() && GetWorld() && GetWorld()->IsGameWorld();
}

bool UDaedalusUnicornRewardComponent::RecordBullAtSea(const FString& BullId, bool WasBurning, bool SeaArrivalVerified)
{
    if (!CanRecord()) return false;
    const auto Result = Gate.RecordBullAtSea(TCHAR_TO_UTF8(*BullId), WasBurning, SeaArrivalVerified);
    Synchronize();
    return Result == DaedalusUnicornReward::Outcome::Progressed || Result == DaedalusUnicornReward::Outcome::Eligible;
}

bool UDaedalusUnicornRewardComponent::RecordPackEncounter(const FString& PackId, int32 Members, bool EncounterVerified)
{
    if (!CanRecord() || Members != static_cast<int32>(DaedalusUnicornReward::Gate::LegendaryPackSize)) return false;
    const auto Result = Gate.RecordPackEncounter(TCHAR_TO_UTF8(*PackId), static_cast<unsigned>(Members), EncounterVerified);
    Synchronize();
    return Result == DaedalusUnicornReward::Outcome::Progressed || Result == DaedalusUnicornReward::Outcome::Eligible;
}

bool UDaedalusUnicornRewardComponent::ConfirmPersistedReward(const FString& GrantReceiptId)
{
    if (!CanRecord() || GrantReceiptId.IsEmpty() || GrantReceiptId.Len() > 128) return false;
    if (Gate.RewardClaimed()) return CommittedGrantReceiptId == GrantReceiptId;
    if (!Gate.ClaimReward()) return false;
    CommittedGrantReceiptId = GrantReceiptId;
    Synchronize();
    return true;
}

void UDaedalusUnicornRewardComponent::Synchronize()
{
    BullsAtSea = static_cast<int32>(Gate.BullsAtSea());
    bEligible = Gate.Eligible();
    bClaimed = Gate.RewardClaimed();
    OnRep_Progress();
}

void UDaedalusUnicornRewardComponent::OnRep_Progress()
{
    if (LastBroadcastBulls == BullsAtSea && bLastBroadcastEligible == bEligible && bLastBroadcastClaimed == bClaimed) return;
    LastBroadcastBulls = BullsAtSea;
    bLastBroadcastEligible = bEligible;
    bLastBroadcastClaimed = bClaimed;
    OnProgress.Broadcast(BullsAtSea, bEligible, bClaimed);
}

void UDaedalusUnicornRewardComponent::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);
    DOREPLIFETIME_CONDITION(UDaedalusUnicornRewardComponent, BullsAtSea, COND_OwnerOnly);
    DOREPLIFETIME_CONDITION(UDaedalusUnicornRewardComponent, bEligible, COND_OwnerOnly);
    DOREPLIFETIME_CONDITION(UDaedalusUnicornRewardComponent, bClaimed, COND_OwnerOnly);
    DOREPLIFETIME_CONDITION(UDaedalusUnicornRewardComponent, CommittedGrantReceiptId, COND_OwnerOnly);
}
