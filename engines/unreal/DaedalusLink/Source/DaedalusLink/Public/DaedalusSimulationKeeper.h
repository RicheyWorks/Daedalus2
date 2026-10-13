// SPDX-License-Identifier: MIT
#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "DaedalusSimulationCore.h"
#include "DaedalusSimulationKeeper.generated.h"

class IHttpRequest;

USTRUCT(BlueprintType)
struct FDaedalusKeeperView {
    GENERATED_BODY()
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Simulation") FString Task;
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Simulation") FString Reason;
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Simulation") FString RememberedActor;
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Simulation") int64 Tick = 0;
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Simulation") int64 Revision = 0;
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Simulation") int32 CisternWater = 0;
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Simulation") int32 KeeperWater = 0;
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Simulation") bool bQuestCompleted = false;
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Simulation") bool bDrySpell = false;
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Simulation") bool bFresh = false;
};

/** Optional explicit npc-zero binding to PR29 simulation/v1. Add to a dedicated movable keeper actor.
 * Start only on the server using the host's existing URL/authentication. No auto-spawn, supply, rewards,
 * inventory mutation or changes to Orrery/Sol journals. Polling uses one asynchronous GET per second.
 * Server owns collision/movement; network movement requires a replicated owner with movement replication enabled.
 */
UCLASS(ClassGroup=(Daedalus), meta=(BlueprintSpawnableComponent))
class DAEDALUSLINK_API UDaedalusSimulationKeeper : public UActorComponent {
    GENERATED_BODY()
public:
    UDaedalusSimulationKeeper();
    virtual void TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction) override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const override;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Daedalus|Simulation") FString BoundNpcId;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Daedalus|Simulation") bool bMoveKeeper = false;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Daedalus|Simulation") TObjectPtr<AActor> RestMarker;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Daedalus|Simulation") TObjectPtr<AActor> WorkMarker;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Daedalus|Simulation") TObjectPtr<AActor> WaterMarker;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Replicated, Category="Daedalus|Simulation") FDaedalusKeeperView View;

    // Authorization is an ephemeral host-supplied header, never replicated or saved. Empty supports test profile.
    UFUNCTION(BlueprintCallable, BlueprintAuthorityOnly, Category="Daedalus|Simulation")
    bool Start(const FString& ServerUrl, const FString& WorldId, const FString& Authorization);
    UFUNCTION(BlueprintCallable, BlueprintAuthorityOnly, Category="Daedalus|Simulation") void Stop();

private:
    bool CanRun() const;
    void Poll();
    void MoveKeeper(float DeltaTime);
    daedalus::simulation::Mailbox Mailbox;
    TSharedPtr<IHttpRequest, ESPMode::ThreadSafe> Request;
    FString Url, Auth;
    uint64 Session = 0;
    double NextPoll = 0;
    bool bRunning = false;
};
