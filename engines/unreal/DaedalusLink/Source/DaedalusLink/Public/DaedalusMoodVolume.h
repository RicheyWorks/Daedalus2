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
protected:
	UFUNCTION() void OnEnter(UPrimitiveComponent* Comp, AActor* Other, UPrimitiveComponent* OtherComp, int32 Body, bool bSweep, const FHitResult& Hit);
};
