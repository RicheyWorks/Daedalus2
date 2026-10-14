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

bool UDaedalusUnicornRewardComponent::HasGameAuthority() const
{
    return GetOwner() && GetOwner()->HasAuthority() && GetWorld() && GetWorld()->IsGameWorld();
}

bool UDaedalusUnicornRewardComponent::CanRecord() const
{
    return HasGameAuthority() && !HostPlayerKey.IsEmpty();
}

bool UDaedalusUnicornRewardComponent::BindHostPlayer(const FString& PlayerKey)
{
    if (!HasGameAuthority() || PlayerKey.IsEmpty() || PlayerKey.Len() > 128 || PlayerKey.TrimStartAndEnd() != PlayerKey) return false;
    for (const TCHAR Character : PlayerKey) if (FChar::IsControl(Character)) return false;
    if (!HostPlayerKey.IsEmpty()) return HostPlayerKey == PlayerKey;
    if (!Gate.Pristine() || bHostRecordRestored) return false;
    HostPlayerKey = PlayerKey;
    return true;
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

bool UDaedalusUnicornRewardComponent::ConfirmPersistedReward(const FString& ExpectedPlayerKey, const FString& GrantReceiptId)
{
    if (!CanRecord() || ExpectedPlayerKey != HostPlayerKey || GrantReceiptId.IsEmpty() || GrantReceiptId.Len() > 128) return false;
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

bool UDaedalusUnicornRewardComponent::RestoreHostRecord(const FDaedalusUnicornRewardRecord& Record)
{
    if (!CanRecord() || Record.PlayerKey != HostPlayerKey || bHostRecordRestored || !Gate.Pristine() || Record.Version != 1 || Record.BullIds.Num() > 10 ||
        Record.GrantReceiptId.Len() > 128 || Record.bClaimed == Record.GrantReceiptId.IsEmpty()) return false;
    DaedalusUnicornReward::Snapshot state;
    for (const auto& Id : Record.BullIds) state.BullIds.emplace_back(TCHAR_TO_UTF8(*Id));
    state.PackId = TCHAR_TO_UTF8(*Record.PackId);
    state.Claimed = Record.bClaimed;
    if (!Gate.Restore(state)) return false;
    CommittedGrantReceiptId = Record.GrantReceiptId;
    bHostRecordRestored = true;
    Synchronize();
    return true;
}

FDaedalusUnicornRewardRecord UDaedalusUnicornRewardComponent::ExportHostRecord() const
{
    FDaedalusUnicornRewardRecord out;
    if (!CanRecord()) return out;
    out.PlayerKey = HostPlayerKey;
    const auto state = Gate.Export();
    for (const auto& Id : state.BullIds) out.BullIds.Add(UTF8_TO_TCHAR(Id.c_str()));
    out.PackId = UTF8_TO_TCHAR(state.PackId.c_str());
    out.bClaimed = state.Claimed;
    out.GrantReceiptId = CommittedGrantReceiptId;
    out.bAvailable = true;
    return out;
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
