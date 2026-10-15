// SPDX-License-Identifier: MIT
#pragma once

#include "CoreMinimal.h"
#include "DaedalusOrrery.h"
#include "DaedalusTideglassWorkshopComponent.h"
#include "DaedalusTideglassStation.generated.h"

class USoundBase;

/** Uses Claude's existing E/X routing and HUD. Place only in Poot's owned child level. */
UCLASS(BlueprintType, Blueprintable)
class DAEDALUSLINK_API ADaedalusTideglassStation : public ADaedalusUsable
{
	GENERATED_BODY()
public:
	ADaedalusTideglassStation();
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Daedalus|Tideglass")
	TObjectPtr<UDaedalusTideglassWorkshopComponent> Workshop;
	/** Stable, unique within the host save namespace. Editing it creates a different operation identity. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|Tideglass") FString WorkshopId;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|Tideglass") TObjectPtr<USoundBase> CommitSound;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|Tideglass") TObjectPtr<USoundBase> BlockedSound;
	virtual FString Prompt(const ADaedalusHero* Hero) const override;
	virtual bool Use(ADaedalusHero* Hero) override;
protected:
	virtual void BeginPlay() override;
private:
	UFUNCTION() void HandleFeedback(const FDaedalusTideglassResult& Result);
};
