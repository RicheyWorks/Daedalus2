// SPDX-License-Identifier: MIT

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "DaedalusVoxelIsle.generated.h"

class UHierarchicalInstancedStaticMeshComponent;
class UMaterialInstanceDynamic;
class UStaticMeshComponent;

/**
 * A floating voxel isle grown from a seed (ADR-058), for building whole domains such as the Orrery Reach.
 *
 * - **Top:** terraced hills rise to a summit at the centre. The rim is noisy, so it never reads as a circle.
 * - **Underneath:** a hanging rock tapers to a glowing heartstone tip.
 * - **IsleLayers:** grass on top (sand near the rim and the pond), dirt below, then stone.
 * - **Water:** an optional pond is carved out and filled with water, and a waterfall pours off the rim.
 *
 * Only cubes that can be seen are made, so a 240 m isle costs about 100k instances, held in one HISM per material.
 * TopZ(x, y) answers the ground height anywhere on the isle, so placement scripts set things on the real ground.
 * Building runs in the editor (OnConstruction) and is the same for a given seed.
 */
UCLASS(meta = (DisplayName = "Daedalus Voxel Isle"))
class DAEDALUSLINK_API ADaedalusVoxelIsle : public AActor
{
	GENERATED_BODY()

public:
	ADaedalusVoxelIsle();

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|Isle") int32 Seed = 7;
	/** Radius in cubes. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|Isle", meta = (ClampMin = "8", ClampMax = "200")) int32 Radius = 120;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|Isle") float CubeSize = 100.f;
	/** Height of the summit above the rim, in cubes. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|Isle") int32 SummitHeight = 16;
	/** How far the hanging rock reaches down, in cubes. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|Isle") int32 Depth = 70;
	/** Pond centre, in cubes from the isle's centre; radius 0 = no pond. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|Isle") FIntPoint PondAt = FIntPoint(-70, 45);
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|Isle") int32 PondRadius = 14;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|Isle") FLinearColor GrassColor = FLinearColor(0.20f, 0.46f, 0.20f);
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|Isle") FLinearColor SandColor = FLinearColor(0.78f, 0.70f, 0.48f);
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|Isle") FLinearColor DirtColor = FLinearColor(0.36f, 0.24f, 0.15f);
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|Isle") FLinearColor StoneColor = FLinearColor(0.34f, 0.32f, 0.38f);
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|Isle") FLinearColor WaterColor = FLinearColor(0.10f, 0.38f, 0.75f);
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|Isle") FLinearColor HeartColor = FLinearColor(1.0f, 0.42f, 0.25f);

	/** Rebuild everything from the settings. Returns "cubes=N columns=M". */
	UFUNCTION(BlueprintCallable, CallInEditor, Category = "Daedalus|Isle") FString Build();
	/** World Z of the ground's top at world (X, Y); the actor's own Z if off the isle. */
	UFUNCTION(BlueprintPure, Category = "Daedalus|Isle") float TopZ(float X, float Y) const;
	/** True if world (X, Y) is over the isle (and not the pond). */
	UFUNCTION(BlueprintPure, Category = "Daedalus|Isle") bool IsLand(float X, float Y) const;
	UFUNCTION(BlueprintPure, Category = "Daedalus|Isle") FString Stats() const { return LastStats; }

	virtual void OnConstruction(const FTransform& Transform) override;

private:
	/** Column height in cubes above the rim level, or INT32_MIN off the isle. */
	int32 ColumnTop(int32 X, int32 Y) const;
	int32 ColumnBottom(int32 X, int32 Y) const;
	bool InPond(int32 X, int32 Y) const;
	float Noise(float X, float Y, int32 Salt) const;
	UHierarchicalInstancedStaticMeshComponent* Layer(int32 Index, const FLinearColor& Color, bool bGlow);

	UPROPERTY() TArray<TObjectPtr<UHierarchicalInstancedStaticMeshComponent>> IsleLayers;
	UPROPERTY() TObjectPtr<UStaticMeshComponent> PondWater;
	UPROPERTY() TObjectPtr<UStaticMeshComponent> Falls;
	FString LastStats;
};
