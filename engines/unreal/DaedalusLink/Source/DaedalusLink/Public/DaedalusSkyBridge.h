// SPDX-License-Identifier: MIT

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "DaedalusSkyBridge.generated.h"

class UInstancedStaticMeshComponent;

/**
 * A walkable rope-and-plank bridge between two floating isles (ADR-058). It runs from the actor to End (world space),
 * sagging in a catenary-like curve. It has planks you can walk on, posts at both ends and rope rails along each side.
 * Instanced, so a 300 m span costs one draw per part.
 */
UCLASS(meta = (DisplayName = "Daedalus Sky Bridge"))
class DAEDALUSLINK_API ADaedalusSkyBridge : public AActor
{
	GENERATED_BODY()

public:
	ADaedalusSkyBridge();
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|Bridge") FVector End = FVector(5000.f, 0.f, 0.f);
	/** How far the middle hangs below the straight line, as a fraction of the span. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|Bridge") float Sag = 0.04f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|Bridge") float Width = 220.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|Bridge") FLinearColor PlankColor = FLinearColor(0.42f, 0.28f, 0.16f);
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|Bridge") FLinearColor RopeColor = FLinearColor(0.75f, 0.62f, 0.38f);

	UFUNCTION(BlueprintCallable, CallInEditor, Category = "Daedalus|Bridge") FString Build();
	virtual void OnConstruction(const FTransform& Transform) override;

private:
	UPROPERTY(Transient) TObjectPtr<UInstancedStaticMeshComponent> Planks;
	UPROPERTY(Transient) TObjectPtr<UInstancedStaticMeshComponent> Ropes;
	FVector PointAt(float T) const;
};
