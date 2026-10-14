// SPDX-License-Identifier: MIT
#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "DaedalusUnicornRewardCore.h"
#include "DaedalusUnicornRewardComponent.generated.h"

DECLARE_DYNAMIC_MULTICAST_DELEGATE_ThreeParams(FDaedalusUnicornRewardProgress, int32, BullsAtSea, bool, Eligible, bool, Claimed);
DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FDaedalusUnicornRecordDirty, int64, Revision);

USTRUCT(BlueprintType)
struct DAEDALUSLINK_API FDaedalusUnicornRewardRecord
{
    GENERATED_BODY()
    UPROPERTY(BlueprintReadWrite, Category="Daedalus|Unicorn") int32 Version = 1;
    UPROPERTY(BlueprintReadWrite, Category="Daedalus|Unicorn") FString PlayerKey;
    UPROPERTY(BlueprintReadWrite, Category="Daedalus|Unicorn") int64 Revision = 0;
    UPROPERTY(BlueprintReadWrite, Category="Daedalus|Unicorn") TArray<FString> BullIds;
    UPROPERTY(BlueprintReadWrite, Category="Daedalus|Unicorn") FString PackId;
    UPROPERTY(BlueprintReadWrite, Category="Daedalus|Unicorn") bool bClaimed = false;
    UPROPERTY(BlueprintReadWrite, Category="Daedalus|Unicorn") FString GrantReceiptId;
    UPROPERTY(BlueprintReadWrite, Category="Daedalus|Unicorn") bool bAvailable = false;
};

/** Per-player progress adapter. Server world-event producers supply verified identities.
 * No client RPC, inventory mutation, wallet access or durable reward transaction is implemented here. */
UCLASS(ClassGroup=(Daedalus), meta=(BlueprintSpawnableComponent))
class DAEDALUSLINK_API UDaedalusUnicornRewardComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    UDaedalusUnicornRewardComponent();
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const override;
    /** Bind once to the authenticated host player key before events or restore. */
    UFUNCTION(BlueprintCallable, BlueprintAuthorityOnly, Category="Daedalus|Unicorn")
    bool BindHostPlayer(const FString& PlayerKey);
    /** Only after the host's durable lookup confirmed no existing record. */
    UFUNCTION(BlueprintCallable, BlueprintAuthorityOnly, Category="Daedalus|Unicorn")
    bool InitializeNewHostRecord(const FString& ExpectedPlayerKey);

    UFUNCTION(BlueprintCallable, BlueprintAuthorityOnly, Category="Daedalus|Unicorn")
    bool RecordBullAtSea(const FString& BullId, bool WasBurning, bool SeaArrivalVerified);
    UFUNCTION(BlueprintCallable, BlueprintAuthorityOnly, Category="Daedalus|Unicorn")
    bool RecordPackEncounter(const FString& PackId, int32 Members, bool EncounterVerified);
    /** Call only AFTER the host committed its idempotent durable reward transaction. */
    UFUNCTION(BlueprintCallable, BlueprintAuthorityOnly, Category="Daedalus|Unicorn")
    bool ConfirmPersistedReward(const FString& ExpectedPlayerKey, const FString& GrantReceiptId);
    UFUNCTION(BlueprintCallable, BlueprintAuthorityOnly, Category="Daedalus|Unicorn")
    bool RestoreHostRecord(const FDaedalusUnicornRewardRecord& Record);
    UFUNCTION(BlueprintCallable, BlueprintAuthorityOnly, Category="Daedalus|Unicorn")
    FDaedalusUnicornRewardRecord ExportHostRecord() const;
    UFUNCTION(BlueprintCallable, BlueprintAuthorityOnly, Category="Daedalus|Unicorn")
    bool ConfirmProgressPersisted(const FString& ExpectedPlayerKey, int64 ExpectedRevision);

    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, ReplicatedUsing=OnRep_Progress, Category="Daedalus|Unicorn")
    int32 BullsAtSea = 0;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, ReplicatedUsing=OnRep_Progress, Category="Daedalus|Unicorn")
    bool bEligible = false;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, ReplicatedUsing=OnRep_Progress, Category="Daedalus|Unicorn")
    bool bClaimed = false;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Replicated, Category="Daedalus|Unicorn")
    FString CommittedGrantReceiptId;
    UPROPERTY(BlueprintAssignable, Category="Daedalus|Unicorn")
    FDaedalusUnicornRewardProgress OnProgress;
    UPROPERTY(BlueprintAssignable, Category="Daedalus|Unicorn") FDaedalusUnicornRecordDirty OnRecordDirty;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Replicated, Category="Daedalus|Unicorn") int64 RecordRevision = 0;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Replicated, Category="Daedalus|Unicorn") bool bPersistencePending = false;

private:
    bool HasGameAuthority() const;
    bool CanRecord() const;
    void Synchronize();
    void MarkRecordDirty();
    UFUNCTION() void OnRep_Progress();
    DaedalusUnicornReward::Gate Gate;
    int32 LastBroadcastBulls = -1;
    bool bLastBroadcastEligible = false;
    bool bLastBroadcastClaimed = false;
    bool bHostRecordRestored = false;
    FString HostPlayerKey;
};
