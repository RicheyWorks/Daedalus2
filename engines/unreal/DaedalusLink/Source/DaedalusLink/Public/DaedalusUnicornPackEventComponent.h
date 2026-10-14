// SPDX-License-Identifier: MIT
#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "DaedalusUnicornPackEventComponent.generated.h"
class UPrimitiveComponent;
class UDaedalusUnicornRewardComponent;

/** Legendary twelve-member female pack encounter. Host membership is explicit,
 * never inferred from mesh names. Spawn probabilities and pack generation are separate. */
UCLASS(ClassGroup=(Daedalus), meta=(BlueprintSpawnableComponent))
class DAEDALUSLINK_API UDaedalusUnicornPackEventComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    UDaedalusUnicornPackEventComponent();
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
    UFUNCTION(BlueprintCallable, BlueprintAuthorityOnly, Category="Daedalus|Unicorn")
    bool ConfigureHostPack(const FString& StablePackId, const TArray<AActor*>& Members, UPrimitiveComponent* Zone);
    UFUNCTION(BlueprintCallable, BlueprintAuthorityOnly, Category="Daedalus|Unicorn")
    bool TryRecordEncounter(AActor* PlayerActor);
private:
    bool Authority() const;
    bool MembershipValid() const;
    void ForgetPlayer(UDaedalusUnicornRewardComponent* Player);
    UFUNCTION() void OnZoneEnter(UPrimitiveComponent* Zone, AActor* Other, UPrimitiveComponent* OtherComp, int32 BodyIndex, bool FromSweep, const FHitResult& Sweep);
    UFUNCTION() void OnZoneExit(UPrimitiveComponent* Zone, AActor* Other, UPrimitiveComponent* OtherComp, int32 BodyIndex);
    UFUNCTION() void OnPlayerReady(bool Ready, bool Pending, int64 Revision);
    FString PackId;
    TArray<TWeakObjectPtr<AActor>> PackMembers;
    TWeakObjectPtr<UPrimitiveComponent> EncounterZone;
    TSet<TWeakObjectPtr<UDaedalusUnicornRewardComponent>> PendingPlayers;
    bool bRecordingEncounter = false;
};
