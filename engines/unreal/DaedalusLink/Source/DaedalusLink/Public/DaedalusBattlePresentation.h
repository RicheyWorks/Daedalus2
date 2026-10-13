#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "DaedalusBattleStageCore.h"
#include "DaedalusBattlePresentation.generated.h"

class UAnimSequence;

/** Dedicated visual stage models only. Never modifies combat HP, loot or world actors. */
UCLASS()
class DAEDALUSLINK_API ADaedalusBattlePresentation : public AActor
{
    GENERATED_BODY()
public:
    ADaedalusBattlePresentation();
    virtual void Tick(float DeltaSeconds) override;
    bool Submit(const std::vector<daedalus::stage::Cue>& Cues);
    UFUNCTION(BlueprintCallable, Category="Daedalus|Battle") void ClearCues();
    UPROPERTY(EditAnywhere, Category="Daedalus|Battle") TArray<TObjectPtr<AActor>> Members;
    UPROPERTY(EditAnywhere, Category="Daedalus|Battle") TArray<TObjectPtr<AActor>> Foes;
    UPROPERTY(EditAnywhere, Category="Daedalus|Battle") TObjectPtr<UAnimSequence> AttackAnimation;
    UPROPERTY(EditAnywhere, Category="Daedalus|Battle") TObjectPtr<UAnimSequence> HurtAnimation;
    UPROPERTY(EditAnywhere, Category="Daedalus|Battle") bool bPaused = false;
    UFUNCTION(BlueprintImplementableEvent, Category="Daedalus|Battle")
    void PresentCue(const FString& Kind, AActor* Actor, AActor* Target, int32 Amount,
                    const FString& Text, float Duration, bool bTargetIsFoe, int32 TargetSlot);
private:
    struct Pending { daedalus::stage::Cue Cue; double Due = 0.0; };
    std::vector<Pending> Queue;
    double Clock = 0.0;
    uint64 Generation = 0;
    AActor* Slot(int Index, bool bFoe) const;
    void Play(AActor* Actor, UAnimSequence* Animation);
};
