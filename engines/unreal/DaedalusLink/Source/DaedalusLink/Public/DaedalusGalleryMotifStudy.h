// SPDX-License-Identifier: MIT
#pragma once
#include "CoreMinimal.h"
#include "DaedalusOrrery.h"
#include "DaedalusGalleryMotifCore.h"
#include "DaedalusGalleryMotifStudy.generated.h"

class ADaedalusGalleryMotifStudy;
class UMaterialInterface;
class UProceduralMeshComponent;
class USceneComponent;
class UTextRenderComponent;
DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FDaedalusMotifStudyViewChanged, ADaedalusGalleryMotifStudy*, Study);

/** Read-only, actor-life copy of one immutable local motif export. This is not
 * a canonical Gallery frame, parcel claim, creator identity or network image.
 * Explicit placement and E/X opt in; BeginPlay performs no file IO. */
UCLASS()
class DAEDALUSLINK_API ADaedalusGalleryMotifStudy : public ADaedalusUsable
{
    GENERATED_BODY()
public:
    ADaedalusGalleryMotifStudy();
    virtual FString Prompt(const ADaedalusHero* Hero) const override;
    virtual bool Use(ADaedalusHero* Hero) override;
    /** Placement binding. Once captured, a later edit never retargets this copy;
     * place a new Study actor for another export or version. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Daedalus|MotifStudy") FString MotifId;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Daedalus|MotifStudy") TObjectPtr<UProceduralMeshComponent> Mosaic;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Daedalus|MotifStudy") TObjectPtr<UTextRenderComponent> Readout;
    UPROPERTY(BlueprintAssignable, Category="Daedalus|MotifStudy") FDaedalusMotifStudyViewChanged OnViewChanged;
    UFUNCTION(BlueprintPure, Category="Daedalus|MotifStudy") bool HasCapturedSketch() const { return bCaptured; }
    /** Read-only actor-life document, never the mutable requested MotifId or a file reload. */
    bool CopyCapturedSketch(daedalus::motif::Document& Out) const
    { if (!Alive() || !bCaptured || !ViewsReady()) return false; const auto Snapshot=Captured; Out=Snapshot; return true; }
protected:
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
private:
    UPROPERTY() TObjectPtr<USceneComponent> StudyRoot;
    UPROPERTY() TObjectPtr<UMaterialInterface> InkMaterial;
    daedalus::motif::Document Captured;
    FString Notice;
    uint64 Epoch=0;
    bool bCaptured=false, bEnding=false, bBusy=false, bNotifying=false;
    bool Alive() const;
    bool ViewsReady() const;
    FString RequestedId() const;
    void Refresh();
};
