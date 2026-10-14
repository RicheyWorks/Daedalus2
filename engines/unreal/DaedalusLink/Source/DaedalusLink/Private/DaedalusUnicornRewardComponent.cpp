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
    return IsValid(GetOwner()) && !GetOwner()->IsActorBeingDestroyed() && GetOwner()->HasAuthority() && GetWorld() && GetWorld()->IsGameWorld();
}

bool UDaedalusUnicornRewardComponent::CanRecord() const
{
    return HasGameAuthority() && !HostPlayerKey.IsEmpty() && bHostRecordRestored;
}

bool UDaedalusUnicornRewardComponent::BindHostPlayer(const FString& PlayerKey)
{
    if (!HasGameAuthority() || !ValidHostIdentity(PlayerKey)) return false;
    if (!HostPlayerKey.IsEmpty()) return HostPlayerKey == PlayerKey;
    if (!Gate.Pristine() || bHostRecordRestored) return false;
    HostPlayerKey = PlayerKey;
    return true;
}

bool UDaedalusUnicornRewardComponent::InitializeNewHostRecord(const FString& ExpectedPlayerKey)
{
    if (!HasGameAuthority() || HostPlayerKey.IsEmpty() || ExpectedPlayerKey != HostPlayerKey) return false;
    if (bHostRecordRestored) return false;
    if (!Gate.Pristine()) return false;
    bHostRecordRestored = true;
    MarkRecordDirty();
    return true;
}

bool UDaedalusUnicornRewardComponent::RecordBullAtSea(const FString& BullId, bool WasBurning, bool SeaArrivalVerified)
{
    if (!CanRecord() || RecordRevision == MAX_int64) return false;
    const auto Result = Gate.RecordBullAtSea(TCHAR_TO_UTF8(*BullId), WasBurning, SeaArrivalVerified);
    const bool Accepted = Result == DaedalusUnicornReward::Outcome::Progressed || Result == DaedalusUnicornReward::Outcome::Eligible;
    if (Accepted) MarkRecordDirty();
    return Accepted;
}

bool UDaedalusUnicornRewardComponent::HasRecordedBull(const FString& BullId) const
{
    if (!CanRecord()) return false;
    const FTCHARToUTF8 Encoded(*BullId);
    return Gate.HasRecordedBull(std::string(Encoded.Get(), Encoded.Length()));
}

bool UDaedalusUnicornRewardComponent::RecordPackEncounter(const FString& PackId, int32 Members, bool EncounterVerified)
{
    if (!CanRecord() || RecordRevision == MAX_int64 || Members != static_cast<int32>(DaedalusUnicornReward::Gate::LegendaryPackSize)) return false;
    const auto Result = Gate.RecordPackEncounter(TCHAR_TO_UTF8(*PackId), static_cast<unsigned>(Members), EncounterVerified);
    const bool Accepted = Result == DaedalusUnicornReward::Outcome::Progressed || Result == DaedalusUnicornReward::Outcome::Eligible;
    if (Accepted) MarkRecordDirty();
    return Accepted;
}

bool UDaedalusUnicornRewardComponent::ValidHostIdentity(const FString& Value)
{
    if (Value.IsEmpty() || Value.Len() > 128 || Value.TrimStartAndEnd() != Value) return false;
    for (const TCHAR Character : Value) if (FChar::IsControl(Character)) return false;
    return true;
}

FDaedalusUnicornRewardRecord UDaedalusUnicornRewardComponent::PrepareGrantRecord(const FString& ExpectedPlayerKey, const FString& GrantReceiptId) const
{
    if (!CanRecord() || ExpectedPlayerKey != HostPlayerKey || !ValidHostIdentity(GrantReceiptId) ||
        !Gate.Eligible() || Gate.RewardClaimed() || bPersistencePending || RecordRevision >= MAX_int64 - 1)
        return FDaedalusUnicornRewardRecord();
    auto Record = ExportHostRecord();
    Record.bClaimed = true;
    Record.GrantReceiptId = GrantReceiptId;
    Record.Revision = RecordRevision + 1;
    return Record;
}

bool UDaedalusUnicornRewardComponent::ConfirmPersistedReward(const FString& ExpectedPlayerKey, const FString& GrantReceiptId, int64 CommittedRevision)
{
    if (!CanRecord() || ExpectedPlayerKey != HostPlayerKey || !ValidHostIdentity(GrantReceiptId)) return false;
    if (Gate.RewardClaimed()) return CommittedGrantReceiptId == GrantReceiptId && RecordRevision == CommittedRevision;
    if (bPersistencePending || RecordRevision >= MAX_int64 - 1 || CommittedRevision != RecordRevision + 1) return false;
    if (!Gate.ClaimReward()) return false;
    CommittedGrantReceiptId = GrantReceiptId;
    RecordRevision = CommittedRevision;
    bPersistencePending = false; // Host says this exact claimed record and grant committed together.
    Synchronize();
    return true;
}

void UDaedalusUnicornRewardComponent::Synchronize()
{
    BullsAtSea = static_cast<int32>(Gate.BullsAtSea());
    bEligible = Gate.Eligible();
    bClaimed = Gate.RewardClaimed();
    bRecordReady = bHostRecordRestored;
    OnRep_Progress();
    OnRep_RecordStatus();
}

bool UDaedalusUnicornRewardComponent::RestoreHostRecord(const FDaedalusUnicornRewardRecord& Record)
{
    if (!HasGameAuthority() || HostPlayerKey.IsEmpty() || !Record.bAvailable || Record.PlayerKey != HostPlayerKey || bHostRecordRestored || !Gate.Pristine() || Record.Version != 1 || Record.BullIds.Num() > 10 ||
        Record.Revision < 0 || Record.Revision == MAX_int64 ||
        (!Record.GrantReceiptId.IsEmpty() && !ValidHostIdentity(Record.GrantReceiptId)) || Record.bClaimed == Record.GrantReceiptId.IsEmpty()) return false;
    DaedalusUnicornReward::Snapshot state;
    for (const auto& Id : Record.BullIds) state.BullIds.emplace_back(TCHAR_TO_UTF8(*Id));
    state.PackId = TCHAR_TO_UTF8(*Record.PackId);
    state.Claimed = Record.bClaimed;
    if (!Gate.Restore(state)) return false;
    CommittedGrantReceiptId = Record.GrantReceiptId;
    bHostRecordRestored = true;
    RecordRevision = Record.Revision;
    bPersistencePending = false;
    Synchronize();
    return true;
}

FDaedalusUnicornRewardRecord UDaedalusUnicornRewardComponent::ExportHostRecord() const
{
    FDaedalusUnicornRewardRecord out;
    if (!CanRecord()) return out;
    out.PlayerKey = HostPlayerKey;
    out.Revision = RecordRevision;
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

void UDaedalusUnicornRewardComponent::MarkRecordDirty()
{
    ++RecordRevision;
    bPersistencePending = true;
    Synchronize();
    OnRecordDirty.Broadcast(RecordRevision);
}

bool UDaedalusUnicornRewardComponent::ConfirmProgressPersisted(const FString& ExpectedPlayerKey, int64 ExpectedRevision)
{
    if (!CanRecord() || ExpectedPlayerKey != HostPlayerKey || ExpectedRevision != RecordRevision) return false;
    bPersistencePending = false;
    OnRep_RecordStatus();
    return true;
}

void UDaedalusUnicornRewardComponent::OnRep_RecordStatus()
{
    if (LastBroadcastRevision == RecordRevision && bLastBroadcastReady == bRecordReady && bLastBroadcastPending == bPersistencePending) return;
    LastBroadcastRevision = RecordRevision;
    bLastBroadcastReady = bRecordReady;
    bLastBroadcastPending = bPersistencePending;
    OnRecordStatus.Broadcast(bRecordReady, bPersistencePending, RecordRevision);
}

void UDaedalusUnicornRewardComponent::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);
    DOREPLIFETIME_CONDITION(UDaedalusUnicornRewardComponent, BullsAtSea, COND_OwnerOnly);
    DOREPLIFETIME_CONDITION(UDaedalusUnicornRewardComponent, bEligible, COND_OwnerOnly);
    DOREPLIFETIME_CONDITION(UDaedalusUnicornRewardComponent, bClaimed, COND_OwnerOnly);
    DOREPLIFETIME_CONDITION(UDaedalusUnicornRewardComponent, CommittedGrantReceiptId, COND_OwnerOnly);
    DOREPLIFETIME_CONDITION(UDaedalusUnicornRewardComponent, RecordRevision, COND_OwnerOnly);
    DOREPLIFETIME_CONDITION(UDaedalusUnicornRewardComponent, bPersistencePending, COND_OwnerOnly);
    DOREPLIFETIME_CONDITION(UDaedalusUnicornRewardComponent, bRecordReady, COND_OwnerOnly);
}
