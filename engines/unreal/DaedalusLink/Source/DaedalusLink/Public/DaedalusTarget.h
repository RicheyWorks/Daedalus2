// SPDX-License-Identifier: MIT

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "DaedalusTarget.generated.h"

class UStaticMesh;
class UStaticMeshComponent;
class UMaterialInstanceDynamic;

/**
 * A foe (ADR-037, ADR-042, ADR-044): one of the four blighted kinds. Idle, it bobs where it was placed. When the
 * player (on foot or on a Ghost) comes within reach and in sight, it hunts, each kind its own way:
 *
 * - BLIGHT_SLIME hops after you and bites up close.
 * - SHARDBACK closes in, glows, then charges in a straight line.
 * - DUST_WISP floats out of reach and fires slow bolts you can dodge.
 * - STONE_KNIGHT plods in, winds up, and slams the ground around it.
 *
 * Ground foes stop at island edges instead of walking off. Every attack is telegraphed (the foe glows orange first).
 * Damage is the foe's ADR-037 power x 10 against the hero's 100 shield and 100 health. `daedalus.FoesHunt 0` stops
 * all hunting (for building and for the harness).
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
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Daedalus") float MaxHealth = 60.f;
	/** The health bar over its head (ADR-048): shown for a few seconds after each hit. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Daedalus") TObjectPtr<UStaticMeshComponent> BarBack;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Daedalus") TObjectPtr<UStaticMeshComponent> BarFill;
	bool IsBarShown() const { return SinceHurt < 4.f && Health > 0.f; }
	/** Which ADR-037 foe this is (BLIGHT_SLIME, SHARDBACK, DUST_WISP, STONE_KNIGHT), its name and what it pays. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus") FString Kind = TEXT("BLIGHT_SLIME");
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus") FString Title = TEXT("Blight slime");
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus") int32 ExpValue = 2;
	/** ADR-037 power; each hit does Power x 10. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus") int32 Power = 1;
	/** False keeps this one idle whatever daedalus.FoesHunt says. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus") bool bHunts = true;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus") float AggroRange = 2600.f;

	// The record (the harness reads these).
	/** IDLE, HUNT, WINDUP, CHARGE, DYING. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Daedalus") FString State = TEXT("IDLE");
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Daedalus") int32 Attacks = 0;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Daedalus") int32 Landed = 0;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Daedalus") bool bSeesPlayer = false;
	/** Ground routes found by the A* port (UDaedalusNav). */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Daedalus") int32 Routes = 0;
	/** ADR-055: parts of the Blender team's Mob_ art worn by this foe (0: the art isn't shipped, the crystal shows). */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Daedalus") int32 ArtParts = 0;
	/** The Mob_ asset each kind wears. */
	static FString ArtFor(const FString& Kind);

protected:
	virtual void BeginPlay() override;
	virtual void EndPlay(const EEndPlayReason::Type Reason) override;

private:
	struct FBolt
	{
		FVector Pos;
		FVector Vel;
		float Life = 3.f;
		TWeakObjectPtr<AActor> Vis;
	};

	bool StepToward(const FVector& Dir, float Speed, float Dt);
	void Strike(APawn* Who, float Damage);
	void FireBolt(const APawn* Who);
	void TickBolts(APawn* Who, float Dt);
	float HoverOffset() const;
	void DressArt();
	void TickArt(float Glow);
	/** World height of the top of the foe (art or crystal) above its actor location. */
	float TopAbove() const;

	UPROPERTY() TObjectPtr<USceneComponent> Look;
	UPROPERTY() TObjectPtr<UStaticMeshComponent> Gem;
	float ArtScale = 1.f;
	float ArtHeight = 0.f;

	UPROPERTY() TObjectPtr<UMaterialInstanceDynamic> Mat;
	UPROPERTY() TObjectPtr<UStaticMesh> BoltMesh;
	TArray<FBolt> Bolts;
	FVector Home = FVector::ZeroVector;
	FVector StartScale = FVector::OneVector;
	FVector ChargeDir = FVector::ForwardVector;
	FLinearColor BaseTint = FLinearColor(0.85f, 0.2f, 0.9f);
	float Age = 0.f;
	float Flash = 0.f;
	float Dying = -1.f;
	float Cooldown = 0.f;
	float Windup = -1.f;
	float WindupTime = 0.5f;
	float ChargeLeft = 0.f;
	float SightCheck = 0.f;
	float SinceHurt = 100.f;
	void TickBar();
	TArray<FVector> Route;
	FVector RouteGoal = FVector::ZeroVector;
	int32 RouteStep = 0;
	float RouteAge = 100.f;   // search on the first hunting frame
	bool bRouted = false;
};
