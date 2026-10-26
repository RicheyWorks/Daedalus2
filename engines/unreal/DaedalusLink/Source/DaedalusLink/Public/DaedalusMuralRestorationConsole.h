// SPDX-License-Identifier: MIT
#pragma once

#include "CoreMinimal.h"
#include "DaedalusOrrery.h"
#include "DaedalusMuralToolCore.h"
#include "DaedalusMuralRestorationConsole.generated.h"

class ADaedalusLivingPainting;
class UMaterialInterface;
class UProceduralMeshComponent;
class UTextRenderComponent;

UENUM(BlueprintType)
enum class EDaedalusMuralToolAction : uint8
{
    NextCell, PreviousCell, NextPigment, PreviousPigment, MixPigment, WashCell, RevealCell
};

/** Opt-in local GAL01 prototype controls. Delegates every stroke/mix/hint to the existing painting.
 * No inventory grants, hidden colour access, shared painter profile or persistence. */
UCLASS()
class DAEDALUSLINK_API ADaedalusMuralRestorationConsole : public ADaedalusUsable
{
    GENERATED_BODY()
public:
    ADaedalusMuralRestorationConsole();
    virtual FString Prompt(const ADaedalusHero* Hero) const override;
    virtual bool Use(ADaedalusHero* Hero) override;

    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category = "Daedalus|Gallery") TObjectPtr<ADaedalusLivingPainting> Painting;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Daedalus|Gallery") TObjectPtr<UProceduralMeshComponent> CellBorder;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Daedalus|Gallery") TObjectPtr<UTextRenderComponent> Readout;

    UFUNCTION(BlueprintCallable, Category = "Daedalus|Gallery") void SetPainting(ADaedalusLivingPainting* NewPainting);
    UFUNCTION(BlueprintCallable, Category = "Daedalus|Gallery") bool SelectCell(int32 X, int32 Y);
    UFUNCTION(BlueprintCallable, Category = "Daedalus|Gallery") FString PaintSelectedCell();
    UFUNCTION(BlueprintCallable, Category = "Daedalus|Gallery") FString PerformTool(EDaedalusMuralToolAction Action);
    UFUNCTION(BlueprintPure, Category = "Daedalus|Gallery") FString ToolPrompt(EDaedalusMuralToolAction Action) const;
    UFUNCTION(BlueprintPure, Category = "Daedalus|Gallery") int32 SelectedX() const { return Focus.X(); }
    UFUNCTION(BlueprintPure, Category = "Daedalus|Gallery") int32 SelectedY() const { return Focus.Y(); }
    UFUNCTION(BlueprintPure, Category = "Daedalus|Gallery") FString ConsoleStatus() const;

protected:
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;

private:
    UPROPERTY() TObjectPtr<UMaterialInterface> BorderMaterial;
    DaedalusMuralTools::Focus Focus;
    FString Notice;
    bool bHasHint = false;
    int32 HintPigment = 0;
    int64 ObservedSeed = -1;
    bool bEnding = false;

    bool Synchronize();
    void ClearHint();
    void Refresh();
    void UnbindPainting();
    UFUNCTION() void OnStroke(int32 X, int32 Y, const FString& Result);
    UFUNCTION() void OnAwake(const FString& Subject);
    UFUNCTION() void OnPaintingDestroyed(AActor* DestroyedActor);
    UFUNCTION() void OnPaintingEndPlay(AActor* EndingActor, EEndPlayReason::Type Reason);
};

/** One explicitly placed E / X tool button. Several buttons may target the same console. */
UCLASS()
class DAEDALUSLINK_API ADaedalusMuralToolButton : public ADaedalusUsable
{
    GENERATED_BODY()
public:
    ADaedalusMuralToolButton();
    virtual FString Prompt(const ADaedalusHero* Hero) const override;
    virtual bool Use(ADaedalusHero* Hero) override;
    UPROPERTY(EditInstanceOnly, BlueprintReadWrite, Category = "Daedalus|Gallery") TObjectPtr<ADaedalusMuralRestorationConsole> Console;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|Gallery") EDaedalusMuralToolAction Action = EDaedalusMuralToolAction::NextCell;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Daedalus|Gallery") TObjectPtr<UTextRenderComponent> Label;
protected:
    virtual void BeginPlay() override;
};
