// SPDX-License-Identifier: MIT
// A box that blends the Sky Director to a biome mood (and optional weather) when a pawn enters. Claim 13.
#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "DaedalusSkyDirector.h"
#include "DaedalusMoodVolume.generated.h"

class UBoxComponent;

UCLASS(BlueprintType, Blueprintable, ClassGroup = Daedalus, meta = (DisplayName = "Daedalus Mood Volume"))
class DAEDALUSLINK_API ADaedalusMoodVolume : public AActor
{
	GENERATED_BODY()
public:
	ADaedalusMoodVolume();
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Daedalus") TObjectPtr<UBoxComponent> Box;
	/** Row name in the director's mood table, e.g. pine_stand. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus") FName Mood = TEXT("young_meadow");
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus") bool bSetWeather = false;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus", meta = (EditCondition = "bSetWeather")) EDaedalusWeather Weather = EDaedalusWeather::Clear;
	/** Also trigger when the active VIEW (player camera, hero cam, spectator) is inside, not only an overlapping pawn.
	 *  Fixes Play shots where the pawn spawns on another island while the camera looks at this one. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus") bool bTriggerOnView = true;
	/** Apply at BeginPlay regardless of where the player is (hero/mint shots, island showcase sublevels). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus") bool bForceOnBeginPlay = false;
	/** Optional hour to set when this volume applies (<0 = leave the clock alone). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus") float SetHour = -1.f;
	/** Stop the director's clock / auto weather while inside so the look holds. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus") bool bHoldWhileInside = true;
	/** Restore the previous mood/weather on leaving. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus") bool bRestoreOnExit = true;
	UFUNCTION(BlueprintCallable, Category = "Daedalus") void ApplyNow(bool bInstant = true);
	UFUNCTION(BlueprintPure, Category = "Daedalus") bool IsPointInside(const FVector& P) const;
	virtual void Tick(float Dt) override;
protected:
	virtual void BeginPlay() override;
	void Restore();
	UFUNCTION() void OnExit(UPrimitiveComponent* Comp, AActor* Other, UPrimitiveComponent* OtherComp, int32 Body);
	bool bApplied = false;
	FName PrevMood; EDaedalusWeather PrevWeather = EDaedalusWeather::Clear; bool bPrevClock = true; float PrevAuto = 0.f;
	UFUNCTION() void OnEnter(UPrimitiveComponent* Comp, AActor* Other, UPrimitiveComponent* OtherComp, int32 Body, bool bSweep, const FHitResult& Hit);
};
