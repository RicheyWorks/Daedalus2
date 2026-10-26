// SPDX-License-Identifier: MIT
#pragma once
#include "CoreMinimal.h"
#include "DaedalusOrrery.h"
#include "DaedalusMailRoutePracticeCore.h"
#include "DaedalusMailRoutePractice.generated.h"

class ADaedalusMailRoutePractice;
class APlayerController;
class UMaterialInterface;
class UProceduralMeshComponent;
class USceneComponent;
class UTextRenderComponent;

/** Informational LOCAL PRACTICE snapshot. Points are a calculation, never issued stamps. */
USTRUCT(BlueprintType)
struct FDaedalusMailPracticeReceipt
{
    GENERATED_BODY()
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|MailPractice") int32 Delivered=0;
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|MailPractice") int32 Late=0;
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|MailPractice") int32 Undelivered=0;
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|MailPractice") bool bGhostReturned=false;
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|MailPractice") int32 PracticePoints=0;
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|MailPractice") int32 Seconds=0;
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|MailPractice") int32 ParSeconds=0;
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|MailPractice") FString Medal;
};
DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FDaedalusMailPracticeView, ADaedalusMailRoutePractice*, Practice);
DECLARE_DYNAMIC_MULTICAST_DELEGATE_TwoParams(FDaedalusMailPracticeReceiptEvent, ADaedalusMailRoutePractice*, Practice, FDaedalusMailPracticeReceipt, Receipt);

/** Exact-owned ephemeral practice mailbox; never binds a canonical courier session. */
UCLASS(NotBlueprintable)
class DAEDALUSLINK_API ADaedalusMailPracticeStop : public ADaedalusUsable
{
    GENERATED_BODY()
public:
    ADaedalusMailPracticeStop();
    virtual FString Prompt(const ADaedalusHero* Hero) const override;
    virtual bool Use(ADaedalusHero* Hero) override;
private:
    friend class ADaedalusMailRoutePractice;
    UPROPERTY() TObjectPtr<USceneComponent> MailRoot;
    UPROPERTY() TObjectPtr<UTextRenderComponent> Label;
    UPROPERTY(Transient, DuplicateTransient) TWeakObjectPtr<ADaedalusMailRoutePractice> Course;
    int32 Letter=-1;
    bool bEnding=false;
    bool ViewsReady() const;
protected:
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
};

/** Explicit local-only PAR01 lesson: board, streets, delivery, Ghost and return.
 * Place at the depot on existing flat safe ground with 148m square clearance.
 * No automatic setup, canonical identity, host adapter, save or reward grant.
 * One deliberate setup attempt; partial effects remain until normal teardown. */
UCLASS()
class DAEDALUSLINK_API ADaedalusMailRoutePractice : public ADaedalusUsable
{
    GENERATED_BODY()
public:
    ADaedalusMailRoutePractice();
    virtual FString Prompt(const ADaedalusHero* Hero) const override;
    virtual bool Use(ADaedalusHero* Hero) override;
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Daedalus|MailPractice") int64 PracticeSeed=1;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Daedalus|MailPractice") TObjectPtr<UTextRenderComponent> Readout;
    UPROPERTY(BlueprintAssignable, Category="Daedalus|MailPractice") FDaedalusMailPracticeView OnViewChanged;
    /** May be sampled repeatedly; never connect directly to a reward/settlement grant. */
    UPROPERTY(BlueprintAssignable, Category="Daedalus|MailPractice") FDaedalusMailPracticeReceiptEvent OnPracticeReceipt;
    UFUNCTION(BlueprintPure, Category="Daedalus|MailPractice") bool IsPracticeActive() const;
protected:
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
private:
    friend class ADaedalusMailPracticeStop;
    UPROPERTY() TObjectPtr<USceneComponent> PracticeRoot;
    UPROPERTY() TObjectPtr<UProceduralMeshComponent> StreetInk;
    UPROPERTY() TObjectPtr<UProceduralMeshComponent> GuideInk;
    UPROPERTY() TObjectPtr<UProceduralMeshComponent> GhostLetter;
    UPROPERTY() TObjectPtr<UMaterialInterface> InkMaterial;
    UPROPERTY(Transient, DuplicateTransient) TArray<TObjectPtr<ADaedalusMailPracticeStop>> Stops;
    UPROPERTY(Transient, DuplicateTransient) TArray<TObjectPtr<AActor>> SetupEffects;
    UPROPERTY(Transient, DuplicateTransient) TWeakObjectPtr<ADaedalusHero> Courier;
    UPROPERTY(Transient, DuplicateTransient) TWeakObjectPtr<APlayerController> Controller;
    TArray<FTransform> ExpectedStops;
    FTransform FrozenFrame;
    int64 FrozenSeed=0;
    daedalus::mailpractice::Practice Round;
    FString Notice;
    FDaedalusMailPracticeReceipt LastReceipt;
    uint64 Epoch=0;
    bool bEnding=false,bBusy=false,bNotifying=false,bAttempted=false,bPrepared=false,bHasReceipt=false,bGhostReturned=false;
    mutable bool bUnavailable=false;
    mutable FString Fault;
    bool Alive() const;
    bool ViewsReady() const;
    bool ObserveCourse() const;
    void Unavailable(const FString& Why) const;
    bool StopReady(const ADaedalusMailPracticeStop* Stop,int32 Letter,bool Begun) const;
    bool ReadCourier(ADaedalusHero* Hero,const AActor* Station,FVector& LocalFeet,double& Now) const;
    bool Prepare(ADaedalusHero* Hero);
    bool UseStop(ADaedalusHero* Hero,ADaedalusMailPracticeStop* Stop);
    FString StopPrompt(const ADaedalusHero* Hero,int32 Letter) const;
    void DrawStreets();
    void DrawGuide();
    void Refresh();
    void RememberEffect(AActor* Actor);
    void ReleaseEffects();
    UFUNCTION() void StopEnded(AActor* Actor,EEndPlayReason::Type Reason);
};
