// SPDX-License-Identifier: MIT
#pragma once
#include "CoreMinimal.h"
#include "DaedalusOrrery.h"
#include "DaedalusGalleryMotifFlipbookCore.h"
#include "DaedalusGalleryMotifFlipbook.generated.h"

class ADaedalusGalleryMotifFlipbook;
class ADaedalusGalleryMotifRack;
class APlayerController;
class UMaterialInterface;
class UProceduralMeshComponent;
class USceneComponent;
class UTextRenderComponent;
DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FDaedalusMotifFlipbookView, ADaedalusGalleryMotifFlipbook*, Flipbook);

/** Exact-owned opt-in playback button. It cannot rebind or replace a frame. */
UCLASS(NotBlueprintable)
class DAEDALUSLINK_API ADaedalusMotifFlipbookButton : public ADaedalusUsable
{
    GENERATED_BODY()
public:
    ADaedalusMotifFlipbookButton();
    virtual FString Prompt(const ADaedalusHero* Hero) const override;
    virtual bool Use(ADaedalusHero* Hero) override;
private:
    friend class ADaedalusGalleryMotifFlipbook;
    UPROPERTY() TObjectPtr<USceneComponent> ButtonRoot;
    UPROPERTY() TObjectPtr<UTextRenderComponent> Label;
    UPROPERTY(Transient, DuplicateTransient) TWeakObjectPtr<ADaedalusGalleryMotifFlipbook> Bench;
    int32 Command=-1;
    bool bEnding=false;
    bool ViewsReady() const;
protected:
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
};

/** One immutable local preview of2–4 captured Rack studies, initially paused.
 * No new file IO, artifact format, creator identity, reward or saved timeline.
 * Pixels/IDs survive later SourceRack/Study changes and ending. A new bench
 * is needed for different frames; playback only changes the local playhead. */
UCLASS()
class DAEDALUSLINK_API ADaedalusGalleryMotifFlipbook : public ADaedalusUsable
{
    GENERATED_BODY()
public:
    ADaedalusGalleryMotifFlipbook();
    virtual FString Prompt(const ADaedalusHero* Hero) const override;
    virtual bool Use(ADaedalusHero* Hero) override;
    virtual void Tick(float DeltaSeconds) override;
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Daedalus|Flipbook") TObjectPtr<ADaedalusGalleryMotifRack> SourceRack;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Daedalus|Flipbook") TObjectPtr<UProceduralMeshComponent> Mosaic;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Daedalus|Flipbook") TObjectPtr<UTextRenderComponent> Readout;
    UPROPERTY(BlueprintAssignable, Category="Daedalus|Flipbook") FDaedalusMotifFlipbookView OnViewChanged;
    UFUNCTION(BlueprintPure, Category="Daedalus|Flipbook") int32 FrameCount() const { return Book.Count(); }
    UFUNCTION(BlueprintPure, Category="Daedalus|Flipbook") int32 CurrentFrameNumber() const { return Book.Active()?Book.Index()+1:0; }
    /** Keep actual captured data even if buttons later fail. No source lookup,
     * view/artist authority claim, playback mutation or file IO. */
    bool CopyCapturedBook(daedalus::flipbook::Player& Out) const
    { if (!Alive() || !Book.Active()) return false; const auto Snapshot=Book; Out=Snapshot; return true; }
protected:
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
private:
    friend class ADaedalusMotifFlipbookButton;
    UPROPERTY() TObjectPtr<USceneComponent> BenchRoot;
    UPROPERTY() TObjectPtr<UMaterialInterface> InkMaterial;
    UPROPERTY(Transient, DuplicateTransient) TArray<TObjectPtr<ADaedalusMotifFlipbookButton>> Buttons;
    UPROPERTY(Transient, DuplicateTransient) TArray<TObjectPtr<AActor>> SetupEffects;
    UPROPERTY(Transient) TArray<TObjectPtr<UTextRenderComponent>> ThumbnailLabels;
    UPROPERTY(Transient, DuplicateTransient) TWeakObjectPtr<ADaedalusHero> Artist;
    UPROPERTY(Transient, DuplicateTransient) TWeakObjectPtr<APlayerController> Controller;
    daedalus::flipbook::Player Book;
    FTransform FrozenFrame;
    FString Notice;
    uint64 Epoch=0;
    bool bEnding=false,bBusy=false,bNotifying=false,bAttempted=false,bPrepared=false;
    mutable bool bUnavailable=false;
    mutable FString Fault;
    bool Alive() const;
    bool ViewsReady() const;
    bool ObserveBench() const;
    void Unavailable(const FString& Why) const;
    bool ButtonReady(const ADaedalusMotifFlipbookButton* Button,int32 Command,bool Begun) const;
    FTransform ButtonPose(int32 Command) const;
    FString ButtonPrompt(const ADaedalusHero* Hero,int32 Command) const;
    bool Operate(ADaedalusHero* Hero,ADaedalusMotifFlipbookButton* Button);
    bool PrepareButtons(ADaedalusHero* Hero);
    void Refresh();
    void RememberEffect(AActor* Actor);
    void ReleaseEffects();
    UFUNCTION() void ButtonEnded(AActor* Actor,EEndPlayReason::Type Reason);
};
