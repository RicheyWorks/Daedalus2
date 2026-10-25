// SPDX-License-Identifier: MIT
#pragma once
#include "CoreMinimal.h"
#include "DaedalusOrrery.h"
#include "DaedalusGalleryMotifRack.generated.h"

class ADaedalusGalleryMotifRack;
class ADaedalusGalleryMotifStudio;
class ADaedalusGalleryMotifStudy;
class USceneComponent;
class UTextRenderComponent;
DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FDaedalusMotifRackViewChanged, ADaedalusGalleryMotifRack*, Rack);

/** Four actor-life study references from one explicitly bound local Studio.
 * Preparing never reads a file, captures an image, or changes a Studio draft.
 * Existing studies/IDs never get replaced. Local exports remain independent of
 * these transient props; no canonical Gallery frame/rights/profile is implied. */
UCLASS()
class DAEDALUSLINK_API ADaedalusGalleryMotifRack : public ADaedalusUsable
{
    GENERATED_BODY()
public:
    ADaedalusGalleryMotifRack();
    virtual FString Prompt(const ADaedalusHero* Hero) const override;
    virtual bool Use(ADaedalusHero* Hero) override;
    /** Binding freezes after the first successful preparation. A different
     * Studio, changed prepared frame, or full rack needs a new Rack actor. */
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Daedalus|MotifRack") TObjectPtr<ADaedalusGalleryMotifStudio> Studio;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Daedalus|MotifRack") TObjectPtr<UTextRenderComponent> Readout;
    UPROPERTY(BlueprintAssignable, Category="Daedalus|MotifRack") FDaedalusMotifRackViewChanged OnViewChanged;
    UFUNCTION(BlueprintPure, Category="Daedalus|MotifRack") int32 PreparedCount() const { return PreparedIds.Num(); }
protected:
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
private:
    UPROPERTY() TObjectPtr<USceneComponent> RackRoot;
    UPROPERTY(Transient, DuplicateTransient) TArray<TObjectPtr<ADaedalusGalleryMotifStudy>> Studies;
    UPROPERTY(Transient, DuplicateTransient) TArray<FString> PreparedIds;
    UPROPERTY(Transient, DuplicateTransient) TArray<FTransform> PreparedTransforms;
    UPROPERTY(Transient, DuplicateTransient) TObjectPtr<ADaedalusGalleryMotifStudy> PendingStudy;
    UPROPERTY(Transient, DuplicateTransient) TWeakObjectPtr<ADaedalusGalleryMotifStudio> BoundStudio;
    const AActor* BoundStudioIdentity=nullptr; // EndPlay comparison only.
    FString Notice;
    FTransform PreparedRackTransform;
    uint64 Epoch=0;
    bool bEnding=false,bBusy=false,bNotifying=false;
    // A const Prompt may latch an observed readiness fault; no world mutation
    // or background Tick is needed. Committed slots/IDs are never recycled.
    mutable bool bUnavailable=false;
    mutable FString Fault;
    bool Alive() const;
    bool ViewsReady() const;
    bool ObservePrepared() const;
    void Unavailable(const FString& Why) const;
    bool StudyReady(const ADaedalusGalleryMotifStudy* Study, const FString& Id, const FTransform& Expected, bool Begun) const;
    void UnbindStudy(ADaedalusGalleryMotifStudy* Study);
    void ReleaseStudies();
    void Refresh();
    UFUNCTION() void StudyViewChanged(ADaedalusGalleryMotifStudy* Study);
    UFUNCTION() void StudyEnded(AActor* Actor, EEndPlayReason::Type Reason);
    UFUNCTION() void StudioEnded(AActor* Actor, EEndPlayReason::Type Reason);
};
