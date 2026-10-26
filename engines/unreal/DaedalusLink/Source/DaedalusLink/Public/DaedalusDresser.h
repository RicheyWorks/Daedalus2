// SPDX-License-Identifier: MIT

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "DaedalusDresser.generated.h"

class UHierarchicalInstancedStaticMeshComponent;
class UStaticMesh;
class ADaedalusWorldActor;

/**
 * The world dresser (ADR-054): turns the Blender team's shipped art library into a living world, the moment the live
 * cubes arrive. Every grass, sand and stone top becomes the ground for the plants that belong there (temperate
 * forest and meadow on grass, palms and cactus on sand, conifers and moss on stone), spaced so trees don't crowd,
 * and a starter town (shop, cottages, news board, well, benches, lanterns, mailboxes, flower pots) goes on the flattest
 * ground near the hero's start. Deterministic per Seed; one instanced component per mesh, so thousands cost little.
 *
 * The meshes are found by name under /Game/Daedalus/Art (Prop_Tree_<Species>_<Stage>, Prop_Flower_*, Bld_*...),
 * so every new asset the queue ships joins the world on the next Dress() with no code change.
 */
UCLASS(meta = (DisplayName = "Daedalus Dresser"))
class DAEDALUSLINK_API ADaedalusDresser : public AActor
{
	GENERATED_BODY()

public:
	ADaedalusDresser();

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus") int32 Seed = 7;
	/** 1 = the default amount of plants; 0.5 half, 2 double. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus", meta = (ClampMin = "0")) float Density = 1.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus") bool bTown = true;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus") bool bDressOnLoad = true;
	/** ADR-055: wildlife herds from the Mob_ library (0 turns them off). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus", meta = (ClampMin = "0")) int32 MaxCritters = 120;

	/** Place everything again from the current cubes and art library. Returns a one-line summary. */
	UFUNCTION(BlueprintCallable, Category = "Daedalus") FString Dress();
	UFUNCTION(BlueprintCallable, Category = "Daedalus") void Undress();
	/** "placed=N meshes=M trees=.. flowers=.. town=.. library=.." for the harness. */
	UFUNCTION(BlueprintCallable, Category = "Daedalus") FString Stats() const { return LastStats; }
	/** Where the town went (world space), or zero. */
	UFUNCTION(BlueprintCallable, Category = "Daedalus") FVector TownCenter() const { return Town; }

	virtual void BeginPlay() override;

private:
	UFUNCTION() void OnWorldLoaded(const FString& WorldId);
	void TryDressSoon();
	UHierarchicalInstancedStaticMeshComponent* Pool(UStaticMesh* Mesh, bool bCollide);

	UPROPERTY() TMap<TObjectPtr<UStaticMesh>, TObjectPtr<UHierarchicalInstancedStaticMeshComponent>> Pools;
	TArray<TWeakObjectPtr<AActor>> Critters;
	FString LastStats;
	FVector Town = FVector::ZeroVector;
	FTimerHandle Retry;
	bool bDressed = false;
};
