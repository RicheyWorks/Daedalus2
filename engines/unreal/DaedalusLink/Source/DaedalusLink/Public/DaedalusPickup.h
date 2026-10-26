// SPDX-License-Identifier: MIT

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "DaedalusPickup.generated.h"

class UStaticMeshComponent;
class UMaterialInstanceDynamic;

/**
 * Something a foe drops (ADR-047): a SHIELD CORE (three raise the hero's armor tier: more shield, faster recharge)
 * or an OVERSHIELD (Halo's: shield past full, slowly fading). It spins and bobs where it fell, glows its colour,
 * is picked up by walking or riding within 1.8 m, and fades after a minute.
 */
UCLASS()
class DAEDALUSLINK_API ADaedalusPickup : public AActor
{
	GENERATED_BODY()

public:
	ADaedalusPickup();
	virtual void Tick(float DeltaSeconds) override;

	/** CORE or OVERSHIELD. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus") FString Kind = TEXT("CORE");
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Daedalus") TObjectPtr<UStaticMeshComponent> Gem;

	/** Drop one at a point, settled onto the ground under it. */
	static ADaedalusPickup* Drop(UWorld* World, const FVector& At, const FString& Kind);

protected:
	virtual void BeginPlay() override;

private:
	UPROPERTY() TObjectPtr<UMaterialInstanceDynamic> Mat;
	FVector Home = FVector::ZeroVector;
	float Age = 0.f;
};
