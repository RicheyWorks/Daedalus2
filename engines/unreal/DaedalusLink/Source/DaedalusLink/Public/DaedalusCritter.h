// SPDX-License-Identifier: MIT

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "DaedalusCritter.generated.h"

class UStaticMeshComponent;

/**
 * Wildlife (ADR-055): one of the Blender team's land animals (Mob_Sheep, Mob_Deer, Mob_Rabbit...) living on the
 * live cubes. It grazes, wanders a few metres at a time within reach of where it was put, never walks off a ledge,
 * and bolts from the player when they come close (the shy ones do; cows and horses only look). The world dresser
 * puts them out in herds on ground that suits them.
 */
UCLASS()
class DAEDALUSLINK_API ADaedalusCritter : public AActor
{
	GENERATED_BODY()

public:
	ADaedalusCritter();

	/** The Mob_ asset, e.g. "Mob_Sheep". Set before BeginPlay (or call Rebuild). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus") FString Species = TEXT("Mob_Sheep");
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus") int32 Seed = 1;
	/** How far from home it strays (cm). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus") float Range = 1200.f;

	// The record (the harness reads these).
	/** GRAZE, WALK, FLEE. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Daedalus") FString State = TEXT("GRAZE");
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Daedalus") int32 Parts = 0;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Daedalus") float Walked = 0.f;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Daedalus") int32 Flees = 0;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Daedalus") int32 Ledges = 0;

	UFUNCTION(BlueprintCallable, Category = "Daedalus") int32 Rebuild();
	/** Whether this kind runs from people. */
	UFUNCTION(BlueprintPure, Category = "Daedalus") bool IsShy() const;

	virtual void Tick(float DeltaSeconds) override;

protected:
	virtual void BeginPlay() override;

private:
	bool Step(const FVector& Dir, float Speed, float Dt);
	void Settle();

	UPROPERTY() TObjectPtr<USceneComponent> Look;
	UPROPERTY() TArray<TObjectPtr<UStaticMeshComponent>> Meshes;
	FVector Home = FVector::ZeroVector;
	FVector Heading = FVector::ForwardVector;
	FRandomStream Rng;
	float Left = 0.f;
	float Age = 0.f;
	/** Seconds into Play when the critter grounds itself again: the live world (and streamed islands) can arrive
	 * after BeginPlay, leaving a herd settled on older, lower geometry and walled in by every step (2026-10-13). */
	float NextSettle = 1.5f;
	int32 Settles = 0;
	float Gait = 0.f;
	float Size = 100.f;
	float Check = 0.f;
};
