// SPDX-License-Identifier: MIT
#pragma once
#include "CoreMinimal.h"
#include "DaedalusOrrery.h"
#include <string>
#include "DaedalusGalleryMotifStoryboardPress.generated.h"

class ADaedalusGalleryMotifFlipbook;
class ADaedalusGalleryMotifStoryboardPress;
class USceneComponent;
class UTextRenderComponent;
DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FDaedalusStoryboardPressView, ADaedalusGalleryMotifStoryboardPress*, Press);
DECLARE_DYNAMIC_MULTICAST_DELEGATE_TwoParams(FDaedalusStoryboardKept, ADaedalusGalleryMotifStoryboardPress*, Press, FString, PrintId);

/** Explicit one-way local SVG contact sheet of actual captured Flipbook data.
 * Playback settings are information at capture, not an animated file or saved
 * timeline import. Defaults inactive; no startup IO, creator/ownership claim,
 * publication, reward or canonical profile save. Existing files remain intact. */
UCLASS()
class DAEDALUSLINK_API ADaedalusGalleryMotifStoryboardPress : public ADaedalusUsable
{
    GENERATED_BODY()
public:
    ADaedalusGalleryMotifStoryboardPress();
    virtual FString Prompt(const ADaedalusHero* Hero) const override;
    virtual bool Use(ADaedalusHero* Hero) override;
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Daedalus|Storyboard") TObjectPtr<ADaedalusGalleryMotifFlipbook> SourceFlipbook;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Daedalus|Storyboard") TObjectPtr<UTextRenderComponent> Readout;
    UPROPERTY(BlueprintAssignable, Category="Daedalus|Storyboard") FDaedalusStoryboardPressView OnViewChanged;
    UPROPERTY(BlueprintAssignable, Category="Daedalus|Storyboard") FDaedalusStoryboardKept OnStoryboardKept;
    UFUNCTION(BlueprintPure, Category="Daedalus|Storyboard") FString LastKeptFilename() const { return LastFilename; }
protected:
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
private:
    UPROPERTY() TObjectPtr<USceneComponent> PressRoot;
    UPROPERTY(Transient, DuplicateTransient) TWeakObjectPtr<ADaedalusGalleryMotifFlipbook> FrozenSource;
    std::string LastPrintId;
    FString LastFilename,Notice;
    uint64 Epoch=0;
    bool bEnding=false,bBusy=false,bNotifying=false,bFrozen=false;
    bool Alive() const;
    bool ViewsReady() const;
    bool SourceReady() const;
    void Refresh(const FString& KeptId=FString());
};
