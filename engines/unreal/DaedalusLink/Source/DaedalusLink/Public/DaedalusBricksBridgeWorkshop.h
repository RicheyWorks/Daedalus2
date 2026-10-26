// SPDX-License-Identifier: MIT
#pragma once
#include "CoreMinimal.h"
#include "DaedalusOrrery.h"
#include "DaedalusBricksBridgeCore.h"
#include "DaedalusBricksBridgeWorkshop.generated.h"

class ADaedalusBricksBridgeWorkshop;
class ADaedalusBridgeControl;
class UMaterialInterface;
class UProceduralMeshComponent;
class USceneComponent;
class UTextRenderComponent;
UENUM(BlueprintType)
enum class EDaedalusBridgeAction : uint8 { Link, NextBlueprint, Hint, Undo, Redo, Restart };
DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FDaedalusBridgeViewChanged, ADaedalusBricksBridgeWorkshop*, Workshop);
DECLARE_DYNAMIC_MULTICAST_DELEGATE_TwoParams(FDaedalusBlueprintStudied, ADaedalusBricksBridgeWorkshop*, Workshop, int32, BlueprintIndex);

/** Original local construction puzzle. Beam-length allowance belongs only to
 * the blueprint model, never inventory, engineering safety or a world bridge.
 * Explicit placement; standalone E/X; all owned geometry is noncolliding. */
UCLASS()
class DAEDALUSLINK_API ADaedalusBricksBridgeWorkshop : public ADaedalusUsable
{
    GENERATED_BODY()
public:
    ADaedalusBricksBridgeWorkshop();
    virtual FString Prompt(const ADaedalusHero* Hero) const override;
    virtual bool Use(ADaedalusHero* Hero) override;
    UPROPERTY(BlueprintAssignable, Category="Daedalus|BridgeWorkshop") FDaedalusBridgeViewChanged OnViewChanged;
    /** Informational actor-life first study, separately for each blueprint. */
    UPROPERTY(BlueprintAssignable, Category="Daedalus|BridgeWorkshop") FDaedalusBlueprintStudied OnBlueprintStudied;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Daedalus|BridgeWorkshop") TObjectPtr<UProceduralMeshComponent> Diagram;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Daedalus|BridgeWorkshop") TObjectPtr<UTextRenderComponent> Readout;
    UFUNCTION(BlueprintPure, Category="Daedalus|BridgeWorkshop") bool IsWorkshopAlive() const;
    UFUNCTION(BlueprintPure, Category="Daedalus|BridgeWorkshop") bool IsWorkshopReady() const { return IsWorkshopAlive() && Run.Active() && bAvailable && ViewsReady() && ToolsReady(); }
    UFUNCTION(BlueprintPure, Category="Daedalus|BridgeWorkshop") bool WasBlueprintStudied(int32 Index) const { return Run.EverCompleted(Index); }
    /** Frozen current model only; no file/profile/ever-completion mutation. */
    bool CopyBlueprintSnapshot(int32& OutRule,int32& OutMask) const
    { if (!IsWorkshopReady()) return false; const int32 Rule=Run.CurrentRule(),Mask=Run.Mask(); OutRule=Rule; OutMask=Mask; return true; }
    UFUNCTION(BlueprintPure, Category="Daedalus|BridgeWorkshop") bool IsCurrentComplete() const;
    UFUNCTION(BlueprintPure, Category="Daedalus|BridgeWorkshop") int32 BlueprintIndex() const { return Run.Active()?Run.CurrentRule():-1; }
    FString ControlLabel(EDaedalusBridgeAction Action,int32 Link) const;
    FString ControlPrompt(EDaedalusBridgeAction Action,int32 Link) const;
    bool Operate(ADaedalusHero* Hero,const AActor* Tool,EDaedalusBridgeAction Action,int32 Link=-1);
protected:
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
private:
    UPROPERTY() TObjectPtr<USceneComponent> WorkshopRoot;
    UPROPERTY() TObjectPtr<UMaterialInterface> InkMaterial;
    UPROPERTY() TObjectPtr<UTextRenderComponent> Title;
    UPROPERTY(Transient) TArray<TObjectPtr<UTextRenderComponent>> PadLabels;
    UPROPERTY(Transient) TArray<TObjectPtr<UTextRenderComponent>> SpanLabels;
    UPROPERTY(Transient, DuplicateTransient) TArray<TObjectPtr<ADaedalusBridgeControl>> OwnedControls;
    daedalus::brickbridge::Session Run;
    daedalus::brickbridge::Clue ShownHint;
    FString Notice;
    uint64 Epoch=0;
    bool bEnding=false,bBusy=false,bNotifying=false,bAvailable=true,bToolsAttempted=false;
    bool bRestartArmed=false,bHintVisible=false,bFeedback=false;
    EDaedalusBridgeAction FeedbackAction=EDaedalusBridgeAction::Hint;
    int32 FeedbackLink=-1;
    bool ViewsReady() const;
    bool ToolsReady() const;
    void DrawBlueprint();
    void Refresh(int32 NewlyStudied=-1);
    void SpawnControls();
    void ReleaseControls();
    UFUNCTION() void ControlEnded(AActor* Actor,EEndPlayReason::Type Reason);
};

UCLASS()
class DAEDALUSLINK_API ADaedalusBridgeControl : public ADaedalusUsable
{
    GENERATED_BODY()
public:
    ADaedalusBridgeControl();
    virtual FString Prompt(const ADaedalusHero* Hero) const override;
    virtual bool Use(ADaedalusHero* Hero) override;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Daedalus|BridgeWorkshop") TObjectPtr<UTextRenderComponent> Label;
    UFUNCTION(BlueprintCallable, Category="Daedalus|BridgeWorkshop") bool ConfigureWorkshop(ADaedalusBricksBridgeWorkshop* NewWorkshop,EDaedalusBridgeAction NewAction,int32 NewLink=-1);
    bool Matches(const ADaedalusBricksBridgeWorkshop* Target,EDaedalusBridgeAction ExpectedAction,int32 ExpectedLink) const;
protected:
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
private:
    UPROPERTY() TObjectPtr<USceneComponent> ControlRoot;
    UPROPERTY(EditInstanceOnly, Category="Daedalus|BridgeWorkshop") TObjectPtr<ADaedalusBricksBridgeWorkshop> Workshop;
    UPROPERTY(EditAnywhere, Category="Daedalus|BridgeWorkshop") EDaedalusBridgeAction Action=EDaedalusBridgeAction::Hint;
    UPROPERTY(EditAnywhere, Category="Daedalus|BridgeWorkshop", meta=(ClampMin="-1",ClampMax="11")) int32 Link=-1;
    UPROPERTY(Transient, DuplicateTransient) TWeakObjectPtr<ADaedalusBricksBridgeWorkshop> ObservedWorkshop;
    bool bEnding=false;
    void UnbindWorkshop();
    void RefreshLabel();
    UFUNCTION() void WorkshopViewChanged(ADaedalusBricksBridgeWorkshop* ChangedWorkshop);
};
