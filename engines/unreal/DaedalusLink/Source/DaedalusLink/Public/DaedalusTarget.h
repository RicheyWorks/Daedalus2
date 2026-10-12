// SPDX-License-Identifier: MIT

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "DaedalusTarget.generated.h"

class UStaticMeshComponent;
class UMaterialInstanceDynamic;

/**
 * A foe (ADR-037 / ADR-042): one of the four blighted kinds, floating where it was placed, flashing when hit and
 * shattering at zero health. Its life and EXP come from the server's foe rules. Fighting AI comes next.
 */
UCLASS()
class DAEDALUSLINK_API ADaedalusTarget : public AActor
{
	GENERATED_BODY()

public:
	ADaedalusTarget();

	virtual void Tick(float DeltaSeconds) override;
	virtual float TakeDamage(float Damage, const FDamageEvent& Event, AController* EventInstigator, AActor* DamageCauser) override;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Daedalus") TObjectPtr<UStaticMeshComponent> Crystal;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus") float Health = 60.f;
	/** Which ADR-037 foe this is (BLIGHT_SLIME, SHARDBACK, DUST_WISP, STONE_KNIGHT), its name and what it pays. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus") FString Kind = TEXT("BLIGHT_SLIME");
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus") FString Title = TEXT("Blight slime");
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus") int32 ExpValue = 2;

protected:
	virtual void BeginPlay() override;

private:
	UPROPERTY() TObjectPtr<UMaterialInstanceDynamic> Mat;
	FVector Home = FVector::ZeroVector;
	FVector StartScale = FVector::OneVector;
	FLinearColor BaseTint = FLinearColor(0.85f, 0.2f, 0.9f);
	float Age = 0.f;
	float Flash = 0.f;
	float Dying = -1.f;
};
