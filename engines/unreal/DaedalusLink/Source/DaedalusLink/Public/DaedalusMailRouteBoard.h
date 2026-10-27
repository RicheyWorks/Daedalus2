// SPDX-License-Identifier: MIT
#pragma once
#include "CoreMinimal.h"
#include "DaedalusOrrery.h"
#include "DaedalusMailRouteBoard.generated.h"

class UDaedalusMailRouteSession;
class UMaterialInterface;
class UProceduralMeshComponent;
class UTextRenderComponent;

/** Explicitly placed PAR01 depot board or mailbox. No auto-spawn or route start.
 * PlotNumber -1 is the helipad; 0..63 excluding plaza plots identifies a mailbox.
 * The inset is a canonical street diagram, not a claim that scene placement matches it. */
UCLASS()
class DAEDALUSLINK_API ADaedalusMailRouteBoard : public ADaedalusUsable
{
    GENERATED_BODY()
public:
    ADaedalusMailRouteBoard();
    virtual FString Prompt(const ADaedalusHero* Hero) const override;
    virtual bool Use(ADaedalusHero* Hero) override;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Daedalus|Mail") TObjectPtr<UTextRenderComponent> Readout;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Daedalus|Mail") TObjectPtr<UProceduralMeshComponent> StreetPlan;
    UFUNCTION(BlueprintCallable, Category="Daedalus|Mail") void SetRouteSession(UDaedalusMailRouteSession* Session);
    UFUNCTION(BlueprintPure, Category="Daedalus|Mail") UDaedalusMailRouteSession* GetRouteSession() const { return RouteSession.Get(); }
    UFUNCTION(BlueprintPure, Category="Daedalus|Mail") int32 GetPlotNumber() const { return PlotNumber; }
    UFUNCTION(BlueprintCallable, Category="Daedalus|Mail") bool SetPlotNumber(int32 Plot);
    UFUNCTION(BlueprintCallable, Category="Daedalus|Mail") void RefreshBoard();
    bool IsStationActive() const { return !bEnding && HasActorBegunPlay() && !IsActorBeingDestroyed(); }
    /** Canonical expected station cube, not a validation of the actor's real location. */
    UFUNCTION(BlueprintPure, Category="Daedalus|Mail") bool ExpectedStationCube(FIntVector& Cube) const;
protected:
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
private:
    // Editor placement defaults only. Runtime reconfiguration must use setters
    // so an in-flight request is canceled even if the binding changes back.
    UPROPERTY(EditInstanceOnly, Category="Daedalus|Mail") TObjectPtr<UDaedalusMailRouteSession> RouteSession;
    UPROPERTY(EditAnywhere, Category="Daedalus|Mail") int32 PlotNumber = -1;
    UPROPERTY(Transient) TWeakObjectPtr<UDaedalusMailRouteSession> ObservedSession;
    UPROPERTY(Transient) TArray<TObjectPtr<UTextRenderComponent>> StopLabels;
    UPROPERTY() TObjectPtr<UMaterialInterface> PlanMaterial;
    uint64 ConfigurationRevision = 0;
    bool bEnding = false;
    void UnbindSession();
    void RefreshPlan();
    UFUNCTION() void SessionChanged(UDaedalusMailRouteSession* Session);
};
