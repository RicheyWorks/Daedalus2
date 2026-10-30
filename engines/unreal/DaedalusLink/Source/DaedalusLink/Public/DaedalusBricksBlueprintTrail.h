// SPDX-License-Identifier: MIT
#pragma once
#include "CoreMinimal.h"
#include "DaedalusOrrery.h"
#include "DaedalusBricksBlueprintTrail.generated.h"

class ADaedalusBricksBlueprintTrail;
class ADaedalusBricksBridgeWorkshop;
class ADaedalusBricksSkylineWorkshop;
class UMaterialInterface;
class UProceduralMeshComponent;
class USceneComponent;
class UTextRenderComponent;
DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FDaedalusBlueprintTrailView, ADaedalusBricksBlueprintTrail*, Trail);
DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FDaedalusBlueprintTrailStudied, ADaedalusBricksBlueprintTrail*, Trail);

/** Optional local teaching course. First deliberate use prepares two fresh
 * practice workshops on existing ground. Six first-study notes are actor-life
 * information, never a canonical Kip quest, profile, reward or saved progress.
 * No workshop is reset/replaced; a failed setup keeps its partial effects. */
UCLASS()
class DAEDALUSLINK_API ADaedalusBricksBlueprintTrail : public ADaedalusUsable
{
    GENERATED_BODY()
public:
    ADaedalusBricksBlueprintTrail();
    virtual FString Prompt(const ADaedalusHero* Hero) const override;
    virtual bool Use(ADaedalusHero* Hero) override;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Daedalus|BlueprintTrail") TObjectPtr<UTextRenderComponent> Readout;
    UPROPERTY(BlueprintAssignable, Category="Daedalus|BlueprintTrail") FDaedalusBlueprintTrailView OnViewChanged;
    /** Informational once-course event; current workshop plans remain editable. */
    UPROPERTY(BlueprintAssignable, Category="Daedalus|BlueprintTrail") FDaedalusBlueprintTrailStudied OnBlueprintTrailStudied;
    UFUNCTION(BlueprintPure, Category="Daedalus|BlueprintTrail") int32 StudiedCount() const;
protected:
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
private:
    UPROPERTY() TObjectPtr<USceneComponent> TrailRoot;
    UPROPERTY() TObjectPtr<UProceduralMeshComponent> Wayfinding;
    UPROPERTY() TObjectPtr<UMaterialInterface> InkMaterial;
    UPROPERTY() TObjectPtr<UTextRenderComponent> Title;
    UPROPERTY() TObjectPtr<UTextRenderComponent> BridgeSign;
    UPROPERTY() TObjectPtr<UTextRenderComponent> SkylineSign;
    UPROPERTY(Transient, DuplicateTransient) TObjectPtr<ADaedalusBricksBridgeWorkshop> Bridge;
    UPROPERTY(Transient, DuplicateTransient) TObjectPtr<ADaedalusBricksSkylineWorkshop> Skyline;
    // Includes staged AND returned identities. A partial live failure retains
    // them for review; ownership is checked again before normal End cleanup.
    UPROPERTY(Transient, DuplicateTransient) TArray<TObjectPtr<AActor>> SetupEffects;
    const AActor* BridgeIdentity=nullptr; // EndPlay comparison only.
    const AActor* SkylineIdentity=nullptr;
    FTransform FrozenTrail,ExpectedBridge,ExpectedSkyline;
    bool BridgeNotes[3]{},SkylineNotes[3]{};
    FString Notice;
    uint64 Epoch=0;
    bool bEnding=false,bBusy=false,bNotifying=false,bSetupAttempted=false,bPrepared=false,bEverReported=false;
    mutable bool bUnavailable=false;
    mutable FString Fault;
    bool Alive() const;
    bool ViewsReady() const;
    bool ObservePrepared() const;
    void Unavailable(const FString& Why) const;
    bool StationReady(const AActor* Station,const FTransform& Expected,int32 Lane,bool Begun) const;
    void DrawWayfinding();
    void Refresh();
    void RememberEffect(AActor* Actor);
    void UnbindEffect(AActor* Actor);
    void ReleaseEffects();
    UFUNCTION() void BridgeViewChanged(ADaedalusBricksBridgeWorkshop* ChangedWorkshop);
    UFUNCTION() void SkylineViewChanged(ADaedalusBricksSkylineWorkshop* ChangedWorkshop);
    UFUNCTION() void WorkshopEnded(AActor* Actor,EEndPlayReason::Type Reason);
};
