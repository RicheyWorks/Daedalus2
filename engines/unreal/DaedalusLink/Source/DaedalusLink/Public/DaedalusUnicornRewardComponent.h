// SPDX-License-Identifier: MIT
#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "DaedalusUnicornRewardCore.h"
#include "DaedalusUnicornRewardComponent.generated.h"

DECLARE_DYNAMIC_MULTICAST_DELEGATE_ThreeParams(FDaedalusUnicornRewardProgress, int32, BullsAtSea, bool, Eligible, bool, Claimed);

/** Per-player progress adapter. Server world-event producers supply verified identities.
 * No client RPC, inventory mutation, wallet access or durable reward transaction is implemented here. */
UCLASS(ClassGroup=(Daedalus), meta=(BlueprintSpawnableComponent))
class DAEDALUSLINK_API UDaedalusUnicornRewardComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    UDaedalusUnicornRewardComponent();
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const override;

    UFUNCTION(BlueprintCallable, BlueprintAuthorityOnly, Category="Daedalus|Unicorn")
    bool RecordBullAtSea(const FString& BullId, bool WasBurning, bool SeaArrivalVerified);
    UFUNCTION(BlueprintCallable, BlueprintAuthorityOnly, Category="Daedalus|Unicorn")
    bool RecordPackEncounter(const FString& PackId, int32 Members, bool EncounterVerified);
    /** Call only AFTER the host committed its idempotent durable reward transaction. */
    UFUNCTION(BlueprintCallable, BlueprintAuthorityOnly, Category="Daedalus|Unicorn")
    bool ConfirmPersistedReward(const FString& GrantReceiptId);

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

private:
    bool CanRecord() const;
    void Synchronize();
    UFUNCTION() void OnRep_Progress();
    DaedalusUnicornReward::Gate Gate;
    int32 LastBroadcastBulls = -1;
    bool bLastBroadcastEligible = false;
    bool bLastBroadcastClaimed = false;
};
