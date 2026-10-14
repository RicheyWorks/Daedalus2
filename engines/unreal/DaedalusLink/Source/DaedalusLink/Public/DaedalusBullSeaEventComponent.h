// SPDX-License-Identifier: MIT
#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "TimerManager.h"
#include "DaedalusBullSeaEventComponent.generated.h"
class ATriggerVolume;
class UDaedalusUnicornRewardComponent;

/** Host binds the driven bull's stable identity and credited player's reward component.
 * Sea volumes must be ATriggerVolume actors tagged DaedalusSeaArrival. No client RPC or movement logic. */
UCLASS(ClassGroup=(Daedalus), meta=(BlueprintSpawnableComponent))
class DAEDALUSLINK_API UDaedalusBullSeaEventComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    UDaedalusBullSeaEventComponent();
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
    UFUNCTION(BlueprintCallable, BlueprintAuthorityOnly, Category="Daedalus|Unicorn")
    bool BindHostBull(const FString& StableBullId, UDaedalusUnicornRewardComponent* CreditedPlayer, bool BurningVerified);
    UFUNCTION(BlueprintCallable, BlueprintAuthorityOnly, Category="Daedalus|Unicorn")
    bool RetryPendingArrival();
    UFUNCTION(BlueprintCallable, BlueprintAuthorityOnly, Category="Daedalus|Unicorn")
    bool SetBurningFromHost(bool BurningVerified);
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Daedalus|Unicorn") bool bArrivalRecorded = false;
private:
    UFUNCTION() void OnOwnerOverlap(AActor* OwnerActor, AActor* OtherActor);
    UFUNCTION() void OnOwnerExit(AActor* OwnerActor, AActor* OtherActor);
    UFUNCTION() void OnPlayerRecordStatus(bool Ready, bool Pending, int64 Revision);
    bool Authority() const;
    void OnArrivalRetry();
    void ClearPendingArrival();
    FString BullId;
    bool bBurningVerified = false;
    TWeakObjectPtr<UDaedalusUnicornRewardComponent> Reward;
    TWeakObjectPtr<ATriggerVolume> PendingSea;
    FTimerHandle ArrivalRetryTimer;
    bool bRecordingArrival = false;
};
