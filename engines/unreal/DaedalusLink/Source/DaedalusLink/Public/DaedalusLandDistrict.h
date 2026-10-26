// SPDX-License-Identifier: MIT

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "DaedalusLandDistrict.generated.h"

class UInstancedStaticMeshComponent;

/**
 * One district of lands as ONE actor (ADR-065/066; 2026-10-14 00:05, "I need you to be fast"): the plots of a
 * 10x10 district are instances of a single cube on an InstancedStaticMeshComponent, and the district's ground is a
 * second instance set. 38,400 plots are 384 of these instead of 76,800 actors. Instance i of Plots is cell
 * Cells[i] (the ADR-065 spiral number), so the land registry can still address every plot.
 */
UCLASS()
class DAEDALUSLINK_API ADaedalusLandDistrict : public AActor
{
	GENERATED_BODY()

public:
	ADaedalusLandDistrict();

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|Lands") FString Realm;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|Lands") int32 District = -1;
	/** Spiral cell number of each plot instance, in instance order. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|Lands") TArray<int32> Cells;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Daedalus|Lands") TObjectPtr<UInstancedStaticMeshComponent> Plots;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Daedalus|Lands") TObjectPtr<UInstancedStaticMeshComponent> Ground;

	/** Lay the plots: one instance per transform (world space); Cells[i] names instance i. Replaces what was there. */
	UFUNCTION(BlueprintCallable, Category = "Daedalus|Lands") int32 LayPlots(const TArray<int32>& CellNumbers, const TArray<FTransform>& Where);
	/** The ground slab(s) under the district, world-space transforms. */
	UFUNCTION(BlueprintCallable, Category = "Daedalus|Lands") int32 LayGround(const TArray<FTransform>& Where);
	UFUNCTION(BlueprintCallable, Category = "Daedalus|Lands") FString DistrictState() const;
	/** The instance index of a cell number, -1 when the district has no plot there. */
	UFUNCTION(BlueprintCallable, Category = "Daedalus|Lands") int32 IndexOfCell(int32 Cell) const { return Cells.IndexOfByKey(Cell); }
};
