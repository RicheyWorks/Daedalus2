// SPDX-License-Identifier: MIT
#pragma once
#include "CoreMinimal.h"
#include "DaedalusOrrery.h"
#include "DaedalusGallerySpectrumCore.h"
#include "DaedalusGallerySpectrumTable.generated.h"

class ADaedalusGallerySpectrumTable;
class ADaedalusSpectrumControl;
class UMaterialInterface;
class UProceduralMeshComponent;
class USceneComponent;
class UTextRenderComponent;
UENUM(BlueprintType)
enum class EDaedalusSpectrumAction : uint8 { Router, NextPicture, Hint, Undo, Redo, Restart };
DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FDaedalusSpectrumViewChanged, ADaedalusGallerySpectrumTable*, Table);
DECLARE_DYNAMIC_MULTICAST_DELEGATE_TwoParams(FDaedalusSpectrumPictureCompleted, ADaedalusGallerySpectrumTable*, Table, int32, PictureIndex);

/** Original local RGB-channel practice, not physical lighting or server art.
 * Explicit placement, standalone and existing E/X only. Static owned ribbons,
 * windows and controls never collide. No light service, IO, quest or award. */
UCLASS()
class DAEDALUSLINK_API ADaedalusGallerySpectrumTable : public ADaedalusUsable
{
    GENERATED_BODY()
public:
    ADaedalusGallerySpectrumTable();
    virtual FString Prompt(const ADaedalusHero* Hero) const override;
    virtual bool Use(ADaedalusHero* Hero) override;
    UPROPERTY(BlueprintAssignable, Category="Daedalus|Spectrum") FDaedalusSpectrumViewChanged OnViewChanged;
    /** Informational first completion only, separately for each picture. */
    UPROPERTY(BlueprintAssignable, Category="Daedalus|Spectrum") FDaedalusSpectrumPictureCompleted OnPictureCompleted;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Daedalus|Spectrum") TObjectPtr<UProceduralMeshComponent> Diagram;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Daedalus|Spectrum") TObjectPtr<UTextRenderComponent> Readout;
    UFUNCTION(BlueprintPure, Category="Daedalus|Spectrum") bool IsTableAlive() const;
    UFUNCTION(BlueprintPure, Category="Daedalus|Spectrum") int32 PictureIndex() const { return Run.Active()?Run.CurrentPicture():-1; }
    UFUNCTION(BlueprintPure, Category="Daedalus|Spectrum") bool IsCurrentComplete() const;
    UFUNCTION(BlueprintPure, Category="Daedalus|Spectrum") bool WasPictureCompleted(int32 Index) const { return Run.EverCompleted(Index); }
    FString ControlLabel(EDaedalusSpectrumAction Action, int32 Router) const;
    FString ControlPrompt(EDaedalusSpectrumAction Action, int32 Router) const;
    bool Operate(ADaedalusHero* Hero, const AActor* Tool, EDaedalusSpectrumAction Action, int32 Router = -1);
protected:
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
private:
    UPROPERTY() TObjectPtr<USceneComponent> TableRoot;
    UPROPERTY() TObjectPtr<UMaterialInterface> InkMaterial;
    UPROPERTY() TObjectPtr<UTextRenderComponent> Title;
    UPROPERTY(Transient) TArray<TObjectPtr<UTextRenderComponent>> SourceLabels;
    UPROPERTY(Transient) TArray<TObjectPtr<UTextRenderComponent>> WindowLabels;
    UPROPERTY(Transient, DuplicateTransient) TArray<TObjectPtr<ADaedalusSpectrumControl>> OwnedControls;
    daedalus::spectrum::Session Run;
    daedalus::spectrum::Clue ShownHint;
    FString Notice;
    uint64 Epoch=0;
    bool bEnding=false,bBusy=false,bNotifying=false,bAvailable=true,bToolsAttempted=false;
    bool bRestartArmed=false,bHintVisible=false,bFeedback=false;
    EDaedalusSpectrumAction FeedbackAction=EDaedalusSpectrumAction::Hint;
    int32 FeedbackRouter=-1;
    bool ViewsReady() const;
    bool ToolsReady() const;
    void DrawTable();
    void Refresh(int32 NewlyCompleted = -1);
    void SpawnControls();
    void ReleaseControls();
    UFUNCTION() void ControlEnded(AActor* Actor, EEndPlayReason::Type Reason);
};

/** One numbered RGB router or utility, with local feedback at the last tool. */
UCLASS()
class DAEDALUSLINK_API ADaedalusSpectrumControl : public ADaedalusUsable
{
    GENERATED_BODY()
public:
    ADaedalusSpectrumControl();
    virtual FString Prompt(const ADaedalusHero* Hero) const override;
    virtual bool Use(ADaedalusHero* Hero) override;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Daedalus|Spectrum") TObjectPtr<UTextRenderComponent> Label;
    UFUNCTION(BlueprintCallable, Category="Daedalus|Spectrum") bool ConfigureTable(ADaedalusGallerySpectrumTable* NewTable, EDaedalusSpectrumAction NewAction, int32 NewRouter = -1);
    bool Matches(const ADaedalusGallerySpectrumTable* Target, EDaedalusSpectrumAction ExpectedAction, int32 ExpectedRouter) const;
protected:
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
private:
    UPROPERTY() TObjectPtr<USceneComponent> ControlRoot;
    UPROPERTY(EditInstanceOnly, Category="Daedalus|Spectrum") TObjectPtr<ADaedalusGallerySpectrumTable> Table;
    UPROPERTY(EditAnywhere, Category="Daedalus|Spectrum") EDaedalusSpectrumAction Action=EDaedalusSpectrumAction::Hint;
    UPROPERTY(EditAnywhere, Category="Daedalus|Spectrum", meta=(ClampMin="-1",ClampMax="5")) int32 Router=-1;
    UPROPERTY(Transient, DuplicateTransient) TWeakObjectPtr<ADaedalusGallerySpectrumTable> ObservedTable;
    bool bEnding=false;
    void UnbindTable();
    void RefreshLabel();
    UFUNCTION() void TableViewChanged(ADaedalusGallerySpectrumTable* ChangedTable);
};
