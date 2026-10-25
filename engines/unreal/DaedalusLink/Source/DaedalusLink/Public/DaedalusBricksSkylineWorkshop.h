// SPDX-License-Identifier: MIT
#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "DaedalusOrrery.h"
#include "DaedalusBricksSkylineCore.h"
#include "DaedalusBricksSkylineWorkshop.generated.h"

class ADaedalusBricksSkylineWorkshop;
class ADaedalusSkylineControl;
class UMaterialInterface;
class UProceduralMeshComponent;
class USceneComponent;
class UTextRenderComponent;
UENUM(BlueprintType)
enum class EDaedalusSkylineAction : uint8 { Cell, Height, NextBlueprint, Hint, Undo, Redo, Restart };
DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FDaedalusSkylineViewChanged, ADaedalusBricksSkylineWorkshop*, Workshop);
DECLARE_DYNAMIC_MULTICAST_DELEGATE_TwoParams(FDaedalusSkylineStudied, ADaedalusBricksSkylineWorkshop*, Workshop, int32, BlueprintIndex);

/** Original local height/visibility blueprint practice. Explicit placement on
 * existing ground; owned towers are noncolliding models, not world building,
 * structural physics, inventory or canonical quest/profile progress. */
UCLASS()
class DAEDALUSLINK_API ADaedalusBricksSkylineWorkshop : public AActor
{
    GENERATED_BODY()
public:
    ADaedalusBricksSkylineWorkshop();
    UPROPERTY(BlueprintAssignable, Category="Daedalus|Skyline") FDaedalusSkylineViewChanged OnViewChanged;
    /** Actor-life first study only; current completion remains reversible. */
    UPROPERTY(BlueprintAssignable, Category="Daedalus|Skyline") FDaedalusSkylineStudied OnBlueprintStudied;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Daedalus|Skyline") TObjectPtr<UProceduralMeshComponent> Model;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Daedalus|Skyline") TObjectPtr<UTextRenderComponent> Readout;
    UFUNCTION(BlueprintPure, Category="Daedalus|Skyline") bool IsWorkshopAlive() const;
    UFUNCTION(BlueprintPure, Category="Daedalus|Skyline") bool IsWorkshopReady() const { return IsWorkshopAlive() && Run.Active() && bAvailable && ViewsReady() && ToolsReady(); }
    UFUNCTION(BlueprintPure, Category="Daedalus|Skyline") bool WasBlueprintStudied(int32 Index) const { return Run.EverCompleted(Index); }
    /** Frozen current model only; no file/profile/ever-completion mutation. */
    bool CopyBlueprintSnapshot(int32& OutRule,daedalus::skyline::Grid& OutGrid) const
    { if (!IsWorkshopReady()) return false; const int32 Rule=Run.CurrentRule(); const auto Grid=Run.Canvas(); OutRule=Rule; OutGrid=Grid; return true; }
    UFUNCTION(BlueprintPure, Category="Daedalus|Skyline") bool IsCurrentComplete() const;
    UFUNCTION(BlueprintPure, Category="Daedalus|Skyline") int32 BlueprintIndex() const { return Run.Active()?Run.CurrentRule():-1; }
    FString ControlLabel(EDaedalusSkylineAction Action,int32 Parameter) const;
    FString ControlPrompt(EDaedalusSkylineAction Action,int32 Parameter) const;
    bool Operate(ADaedalusHero* Hero,const AActor* Tool,EDaedalusSkylineAction Action,int32 Parameter);
protected:
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
private:
    UPROPERTY() TObjectPtr<USceneComponent> WorkshopRoot;
    UPROPERTY() TObjectPtr<UMaterialInterface> InkMaterial;
    UPROPERTY() TObjectPtr<UTextRenderComponent> Title;
    UPROPERTY(Transient) TArray<TObjectPtr<UTextRenderComponent>> ClueLabels;
    UPROPERTY(Transient, DuplicateTransient) TArray<TObjectPtr<ADaedalusSkylineControl>> OwnedControls;
    daedalus::skyline::Session Run;
    daedalus::skyline::Clue ShownHint;
    FString Notice;
    int32 BrushHeight=1,SelectedCell=-1;
    uint64 Epoch=0;
    bool bEnding=false,bBusy=false,bNotifying=false,bAvailable=true,bToolsAttempted=false;
    bool bRestartArmed=false,bHintVisible=false,bFeedback=false;
    EDaedalusSkylineAction FeedbackAction=EDaedalusSkylineAction::Hint;
    int32 FeedbackParameter=-1;
    bool ViewsReady() const;
    bool ToolsReady() const;
    void DrawModel();
    void Refresh(int32 NewlyStudied=-1);
    void SpawnControls();
    void ReleaseControls();
    UFUNCTION() void ControlEnded(AActor* Actor,EEndPlayReason::Type Reason);
};

UCLASS()
class DAEDALUSLINK_API ADaedalusSkylineControl : public ADaedalusUsable
{
    GENERATED_BODY()
public:
    ADaedalusSkylineControl();
    virtual FString Prompt(const ADaedalusHero* Hero) const override;
    virtual bool Use(ADaedalusHero* Hero) override;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Daedalus|Skyline") TObjectPtr<UTextRenderComponent> Label;
    UFUNCTION(BlueprintCallable, Category="Daedalus|Skyline") bool ConfigureWorkshop(ADaedalusBricksSkylineWorkshop* NewWorkshop,EDaedalusSkylineAction NewAction,int32 NewParameter=-1);
    bool Matches(const ADaedalusBricksSkylineWorkshop* Target,EDaedalusSkylineAction ExpectedAction,int32 ExpectedParameter) const;
protected:
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
private:
    UPROPERTY() TObjectPtr<USceneComponent> ControlRoot;
    UPROPERTY(EditInstanceOnly, Category="Daedalus|Skyline") TObjectPtr<ADaedalusBricksSkylineWorkshop> Workshop;
    UPROPERTY(EditAnywhere, Category="Daedalus|Skyline") EDaedalusSkylineAction Action=EDaedalusSkylineAction::Hint;
    UPROPERTY(EditAnywhere, Category="Daedalus|Skyline", meta=(ClampMin="-1",ClampMax="15")) int32 Parameter=-1;
    UPROPERTY(Transient, DuplicateTransient) TWeakObjectPtr<ADaedalusBricksSkylineWorkshop> ObservedWorkshop;
    bool bEnding=false;
    void UnbindWorkshop();
    void RefreshLabel();
    UFUNCTION() void WorkshopViewChanged(ADaedalusBricksSkylineWorkshop* ChangedWorkshop);
};
