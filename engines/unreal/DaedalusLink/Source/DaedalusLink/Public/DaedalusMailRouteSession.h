// SPDX-License-Identifier: MIT
#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "DaedalusMailRouteCore.h"
#include "DaedalusMailRouteSession.generated.h"

class ADaedalusMailRouteBoard;
class UDaedalusMailRouteSession;

UENUM(BlueprintType)
enum class EDaedalusMailRouteAction : uint8 { Start, Deliver, Receipt };

/** Caller-supplied, validated observations in Java's X/Y-up/Z cube coordinates.
 * This struct is not authentication or a network position/clock validator. */
USTRUCT(BlueprintType)
struct FDaedalusMailRouteObservation
{
    GENERATED_BODY()
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Daedalus|Mail") FString CourierIdentity;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Daedalus|Mail") FString SessionIdentity;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Daedalus|Mail") FString DistrictIdentity;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Daedalus|Mail") int64 DaySeed = 0;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Daedalus|Mail") FIntVector CourierCube = FIntVector::ZeroValue;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Daedalus|Mail") FIntVector StationCube = FIntVector::ZeroValue;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Daedalus|Mail") int32 ElapsedSeconds = -1;
};

/** Informational Java receipt. No inventory, companion XP or once-only settlement is performed. */
USTRUCT(BlueprintType)
struct FDaedalusMailRoutePendingReceipt
{
    GENERATED_BODY()
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Mail") bool bAvailable = false;
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Mail") bool bPendingSettlement = true;
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Mail") int32 Delivered = 0;
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Mail") int32 Late = 0;
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Mail") int32 Undelivered = 0;
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Mail") bool bGhostReturned = false;
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Mail") int32 Stamps = 0;
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Mail") int32 Seconds = 0;
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Mail") int32 ParSeconds = 0;
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Mail") FString Medal;
};

DECLARE_DYNAMIC_MULTICAST_DELEGATE_FiveParams(FDaedalusMailRouteRequested,
    UDaedalusMailRouteSession*, Session, int64, Ticket, ADaedalusMailRouteBoard*, Station,
    EDaedalusMailRouteAction, Action, int32, LetterId);
DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FDaedalusMailRouteChanged, UDaedalusMailRouteSession*, Session);

/** Opt-in per-courier PAR01 projection. Attach explicitly to the courier actor.
 * A separately implemented host adapter must establish canonical identity and
 * validate district/scene coordinates and elapsed time before completing a request.
 * No RPC, automatic Hero lookup, world-clock sampling, save or reward service. */
UCLASS(ClassGroup=(Daedalus), meta=(BlueprintSpawnableComponent))
class DAEDALUSLINK_API UDaedalusMailRouteSession : public UActorComponent
{
    GENERATED_BODY()
public:
    UDaedalusMailRouteSession();

    UPROPERTY(BlueprintAssignable, Category="Daedalus|Mail") FDaedalusMailRouteRequested OnActionRequested;
    UPROPERTY(BlueprintAssignable, Category="Daedalus|Mail") FDaedalusMailRouteChanged OnChanged;

    /** Bind after the adapter subscribes. Owner is the exact courier, not an ID lookup.
     * Rebinding the same round preserves progress; a different active round is refused. */
    UFUNCTION(BlueprintCallable, BlueprintAuthorityOnly, Category="Daedalus|Mail")
    bool ConfigureHost(UObject* HostAdapter, const FString& CourierIdentity, const FString& SessionIdentity,
                       const FString& DistrictIdentity, int64 DaySeed);
    /** Suspend, fence outstanding replies and retain the current round in memory. */
    UFUNCTION(BlueprintCallable, BlueprintAuthorityOnly, Category="Daedalus|Mail") void ClearHostBinding();
    UFUNCTION(BlueprintCallable, BlueprintAuthorityOnly, Category="Daedalus|Mail") bool CancelPendingRequest();
    /** All core actions go through this single ticket-matching response path. */
    UFUNCTION(BlueprintCallable, BlueprintAuthorityOnly, Category="Daedalus|Mail")
    bool CompleteHostAction(UObject* HostAdapter, int64 Ticket, const FDaedalusMailRouteObservation& Observation);
    UFUNCTION(BlueprintCallable, BlueprintAuthorityOnly, Category="Daedalus|Mail")
    bool RejectHostAction(UObject* HostAdapter, int64 Ticket);

    UFUNCTION(BlueprintPure, Category="Daedalus|Mail") bool HasHostBinding() const;
    UFUNCTION(BlueprintPure, Category="Daedalus|Mail") bool HasRoute() const { return Route.Active(); }
    UFUNCTION(BlueprintPure, Category="Daedalus|Mail") bool IsWaitingForHost() const { return PendingTicket != 0; }
    UFUNCTION(BlueprintPure, Category="Daedalus|Mail") FString GetCourierIdentity() const { return CourierKey; }
    UFUNCTION(BlueprintPure, Category="Daedalus|Mail") FString GetSessionIdentity() const { return SessionKey; }
    UFUNCTION(BlueprintPure, Category="Daedalus|Mail") FString GetDistrictIdentity() const { return DistrictKey; }
    UFUNCTION(BlueprintPure, Category="Daedalus|Mail") int64 GetDaySeed() const { return Seed; }
    UFUNCTION(BlueprintPure, Category="Daedalus|Mail") FDaedalusMailRoutePendingReceipt GetPendingReceipt() const { return Receipt; }
    UFUNCTION(BlueprintPure, Category="Daedalus|Mail") FString RouteStatus() const;

    bool IsCourier(const AActor* Courier) const;
    bool RequestAction(AActor* Courier, ADaedalusMailRouteBoard* Station);
    void CancelStationRequest(ADaedalusMailRouteBoard* Station);
    FString StationPrompt(const AActor* Courier, int32 Plot) const;
    FString StationText(int32 Plot) const;
    const daedalus::parcels::Session& ReadRoute() const { return Route; }

protected:
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;

private:
    UPROPERTY(Transient) TWeakObjectPtr<UObject> Host;
    UPROPERTY(Transient) TWeakObjectPtr<AActor> CourierActor;
    UPROPERTY(Transient) TWeakObjectPtr<ADaedalusMailRouteBoard> PendingStation;
    FString CourierKey, SessionKey, DistrictKey;
    int64 Seed = 0;
    uint64 BindingRevision = 0, PendingRevision = 0;
    int64 NextTicket = 0, PendingTicket = 0;
    EDaedalusMailRouteAction PendingAction = EDaedalusMailRouteAction::Start;
    int32 PendingLetter = -1, PendingPlot = -1, LastElapsed = -1;
    bool bConfigured = false, bEnding = false;
    FString Notice;
    daedalus::parcels::Session Route;
    FDaedalusMailRoutePendingReceipt Receipt;

    bool CanHost() const;
    bool MatchingTicket(UObject* HostAdapter, int64 Ticket) const;
    void ForgetPending();
    void Changed();
    int32 LetterForPlot(int32 Plot) const;
};
