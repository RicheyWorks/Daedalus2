// SPDX-License-Identifier: MIT
#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "DaedalusOrrery.h"
#include "DaedalusGalleryMotifCore.h"
#include "DaedalusGalleryMotifStudio.generated.h"

class ADaedalusGalleryMotifStudio;
class ADaedalusMotifTool;
class UMaterialInterface;
class UProceduralMeshComponent;
class USceneComponent;
class UTextRenderComponent;
UENUM(BlueprintType)
// Append new tools so existing placed/Blueprint action ordinals stay stable.
enum class EDaedalusMotifAction : uint8 { Cell, Colour, Symmetry, Undo, Redo, Export, NextSketch, SaveLoad, SaveClear, Brush, Rotate, FlipColumns, FlipRows };
DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FDaedalusMotifViewChanged, ADaedalusGalleryMotifStudio*, Studio);

/** An original local 8x8 motif studio; not the Gallery server frame protocol.
 * Explicit placement on existing ground. No owned collision, network, canonical
 * inventory/profile/ownership, imported art, or automatic disk IO. Export is an
 * explicit immutable local .dgm artifact. Actor-life drafts need Export to keep. */
UCLASS()
class DAEDALUSLINK_API ADaedalusGalleryMotifStudio : public AActor
{
    GENERATED_BODY()
public:
    ADaedalusGalleryMotifStudio();
    UPROPERTY(BlueprintAssignable, Category="Daedalus|MotifStudio") FDaedalusMotifViewChanged OnViewChanged;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Daedalus|MotifStudio") TObjectPtr<UProceduralMeshComponent> Canvas;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Daedalus|MotifStudio") TObjectPtr<UProceduralMeshComponent> Preview;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Daedalus|MotifStudio") TObjectPtr<UTextRenderComponent> Readout;
    UFUNCTION(BlueprintPure, Category="Daedalus|MotifStudio") bool IsStudioAlive() const;
    UFUNCTION(BlueprintPure, Category="Daedalus|MotifStudio") bool IsDirty() const { return Draft.Active() && Draft.Canvas()!=Baseline; }
    FString ToolPrompt(EDaedalusMotifAction Action, int32 Cell) const;
    FString ToolLabel(EDaedalusMotifAction Action, int32 Cell) const;
    bool Operate(ADaedalusHero* Hero, const AActor* Tool, EDaedalusMotifAction Action, int32 Cell);
protected:
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
private:
    UPROPERTY() TObjectPtr<USceneComponent> StudioRoot;
    UPROPERTY() TObjectPtr<UMaterialInterface> InkMaterial;
    UPROPERTY(Transient, DuplicateTransient) TArray<TObjectPtr<ADaedalusMotifTool>> OwnedTools;
    daedalus::motif::Session Draft;
    daedalus::motif::Image Baseline{}; // Last loaded/exported image; initially blank.
    std::string LineageId;
    daedalus::motif::Document Chosen;
    std::string ChosenBytes;
    FString ChosenId, ArmedId;
    std::string ArmedBytes;
    FString Notice;
    int32 Ink=1, SelectedCell=-1;
    daedalus::motif::Symmetry Mode=daedalus::motif::Symmetry::None;
    EDaedalusMotifAction ArmedAction=EDaedalusMotifAction::Cell;
    EDaedalusMotifAction FeedbackAction=EDaedalusMotifAction::Colour;
    int32 FeedbackCell=-1;
    uint64 Epoch=0;
    bool bEnding=false, bBusy=false, bNotifying=false, bAvailable=true, bToolsAttempted=false, bFeedback=false, bHasChosen=false, bFill=false;
    bool ViewsReady() const;
    bool ToolsReady() const;
    void SpawnTools();
    void ReleaseTools();
    void DrawCanvas();
    void Refresh();
    bool ExportPrepared(const daedalus::motif::Image& Pixels, const std::string& Parent, std::string& ExportedId, FString& Error) const;
    bool ReadChosen(daedalus::motif::Document& Out, std::string& Bytes, FString& Error) const;
    bool NextSketch();
    bool SaveAndLoad();
    bool SaveAndClear();
    UFUNCTION() void ToolEnded(AActor* Actor, EEndPlayReason::Type Reason);
};

/** One noncolliding pixel or utility. Cell origins are at the floor pixel
 * centres; the Studio itself is not Usable and cannot steal their selection. */
UCLASS()
class DAEDALUSLINK_API ADaedalusMotifTool : public ADaedalusUsable
{
    GENERATED_BODY()
public:
    ADaedalusMotifTool();
    virtual FString Prompt(const ADaedalusHero* Hero) const override;
    virtual bool Use(ADaedalusHero* Hero) override;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Daedalus|MotifStudio") TObjectPtr<UTextRenderComponent> Label;
    UFUNCTION(BlueprintCallable, Category="Daedalus|MotifStudio") bool ConfigureStudio(ADaedalusGalleryMotifStudio* NewStudio, EDaedalusMotifAction NewAction, int32 NewCell = -1);
    bool Matches(const ADaedalusGalleryMotifStudio* Target, EDaedalusMotifAction ExpectedAction, int32 ExpectedCell) const;
protected:
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
private:
    UPROPERTY() TObjectPtr<USceneComponent> ToolRoot;
    UPROPERTY(EditInstanceOnly, Category="Daedalus|MotifStudio") TObjectPtr<ADaedalusGalleryMotifStudio> Studio;
    UPROPERTY(EditAnywhere, Category="Daedalus|MotifStudio") EDaedalusMotifAction Action=EDaedalusMotifAction::Cell;
    UPROPERTY(EditAnywhere, Category="Daedalus|MotifStudio", meta=(ClampMin="-1",ClampMax="63")) int32 Cell=0;
    UPROPERTY(Transient, DuplicateTransient) TWeakObjectPtr<ADaedalusGalleryMotifStudio> ObservedStudio;
    bool bEnding=false;
    void UnbindStudio();
    void RefreshLabel();
    UFUNCTION() void StudioViewChanged(ADaedalusGalleryMotifStudio* ChangedStudio);
};
