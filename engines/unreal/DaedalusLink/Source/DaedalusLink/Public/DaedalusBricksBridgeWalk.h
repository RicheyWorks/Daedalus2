// SPDX-License-Identifier: MIT
#pragma once
#include "CoreMinimal.h"
#include "DaedalusOrrery.h"
#include "DaedalusBricksBridgeWalkCore.h"
#include "DaedalusBricksBridgeWalk.generated.h"

class ADaedalusBricksBridgeWorkshop;
class ADaedalusBricksBridgeWalk;
class APlayerController;
class UBoxComponent;
class UMaterialInterface;
class UProceduralMeshComponent;
class USceneComponent;
class UTextRenderComponent;
DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FDaedalusBridgeWalkView, ADaedalusBricksBridgeWalk*, Walk);
DECLARE_DYNAMIC_MULTICAST_DELEGATE_ThreeParams(FDaedalusBridgePadVisited, ADaedalusBricksBridgeWalk*, Walk, int32, PadNumber, int32, VisitedCount);
DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FDaedalusBridgeWalkVisited, ADaedalusBricksBridgeWalk*, Walk);

/** Explicit frozen low walkable model of a current solved Bridge blueprint.
 * Null source is inactive. Place on existing safe flat ground away from the
 * protected obby/runway. Nine pad visits are local acknowledgements, not proof
 * selected spans were walked, engineering safety, quest progress or rewards.
 * Captured deck survives source Undo/end; no rebuild/reset is offered. */
UCLASS()
class DAEDALUSLINK_API ADaedalusBricksBridgeWalk : public ADaedalusUsable
{
    GENERATED_BODY()
public:
    ADaedalusBricksBridgeWalk();
    virtual FString Prompt(const ADaedalusHero* Hero) const override;
    virtual bool Use(ADaedalusHero* Hero) override;
    virtual void Tick(float DeltaSeconds) override;
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Daedalus|BridgeWalk") TObjectPtr<ADaedalusBricksBridgeWorkshop> SourceWorkshop;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Daedalus|BridgeWalk") TObjectPtr<UTextRenderComponent> Readout;
    UPROPERTY(BlueprintAssignable, Category="Daedalus|BridgeWalk") FDaedalusBridgeWalkView OnViewChanged;
    UPROPERTY(BlueprintAssignable, Category="Daedalus|BridgeWalk") FDaedalusBridgePadVisited OnPadVisited;
    UPROPERTY(BlueprintAssignable, Category="Daedalus|BridgeWalk") FDaedalusBridgeWalkVisited OnAllPadsVisited;
    UFUNCTION(BlueprintPure, Category="Daedalus|BridgeWalk") int32 VisitedCount() const { return Model.VisitedCount(); }
    UFUNCTION(BlueprintPure, Category="Daedalus|BridgeWalk") bool HasCapturedBlueprint() const { return Model.Active(); }
protected:
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
private:
    UPROPERTY() TObjectPtr<USceneComponent> WalkRoot;
    UPROPERTY() TObjectPtr<UProceduralMeshComponent> ModelInk;
    UPROPERTY() TObjectPtr<UMaterialInterface> InkMaterial;
    UPROPERTY(Transient) TArray<TObjectPtr<UBoxComponent>> DeckPieces;
    UPROPERTY(Transient) TArray<TObjectPtr<UTextRenderComponent>> PadLabels;
    UPROPERTY(Transient, DuplicateTransient) TWeakObjectPtr<ADaedalusHero> Builder;
    UPROPERTY(Transient, DuplicateTransient) TWeakObjectPtr<APlayerController> Controller;
    FTransform FrozenFrame;
    daedalus::bridgewalk::Walk Model;
    FString Notice;
    uint64 Epoch=0;
    bool bEnding=false,bBusy=false,bNotifying=false,bAttempted=false,bPrepared=false,bAllReported=false;
    mutable bool bUnavailable=false;
    mutable FString Fault;
    bool Alive() const;
    bool ViewsReady() const;
    bool ObserveModel() const;
    bool DeckReady(bool RequirePhysics) const;
    void Unavailable(const FString& Why) const;
    bool SourceReady() const;
    bool PawnSpaceClear(const daedalus::bridgewalk::Walk& Snapshot,const FTransform& Frame) const;
    void DrawModel();
    void Refresh();
};
