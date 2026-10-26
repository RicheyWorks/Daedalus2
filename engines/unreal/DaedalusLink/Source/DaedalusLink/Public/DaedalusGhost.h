// SPDX-License-Identifier: MIT

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Pawn.h"
#include "DaedalusGhost.generated.h"

class UBoxComponent;
class UCameraComponent;
class USpringArmComponent;
class UStaticMesh;
class UStaticMeshComponent;
class UInputAction;
class UInputMappingContext;
class ADaedalusHero;
struct FInputActionValue;

/**
 * A hover bike with twin guns (ADR-043), Halo's Ghost for the sky islands. The hero gets on with Interact (X / E)
 * near it. Riding, the left stick (WASD) throttles and strafes, the bike steers to where the camera looks (right
 * stick / mouse, the hero's invert and sensitivity settings), boost is LB / Shift, the guns are RT / left mouse,
 * and Interact gets off. It hovers over the islands on four traces; off an edge it falls, and far below its last
 * ground it is put back there. Built in code, like the hero, so it needs no assets.
 */
UCLASS(Blueprintable)
class DAEDALUSLINK_API ADaedalusGhost : public APawn
{
	GENERATED_BODY()

public:
	ADaedalusGhost();

	virtual void Tick(float DeltaSeconds) override;
	virtual void PossessedBy(AController* NewController) override;
	virtual void UnPossessed() override;
	virtual void SetupPlayerInputComponent(UInputComponent* PlayerInputComponent) override;
	/** Hits on the bike hurt the rider, softened by its frame (ADR-044). */
	virtual float TakeDamage(float Damage, const FDamageEvent& Event, AController* EventInstigator, AActor* DamageCauser) override;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Daedalus") TObjectPtr<UBoxComponent> Hull;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Daedalus") TObjectPtr<USceneComponent> Frame;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Daedalus") TObjectPtr<USpringArmComponent> Boom;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Daedalus") TObjectPtr<UCameraComponent> Camera;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus") float HoverHeight = 110.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus") float TopSpeed = 1900.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus") float BoostSpeed = 3200.f;

	// The record (the harness reads these).
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Daedalus") int32 ShotsFired = 0;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Daedalus") int32 Hits = 0;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Daedalus") float Heat = 0.f;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Daedalus") bool bOverheated = false;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Daedalus") FVector Velocity = FVector::ZeroVector;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Daedalus") bool bGrounded = false;

	/** Who is riding (null when parked). */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Daedalus") TObjectPtr<ADaedalusHero> Rider;

	/** Get the hero on: he is hidden and carried, and the player's controller takes the bike. */
	UFUNCTION(BlueprintCallable, Category = "Daedalus") bool Mount(ADaedalusHero* Hero);
	/** Get off: the hero stands beside the bike and the player takes him back. */
	UFUNCTION(BlueprintCallable, Category = "Daedalus") void Dismount();
	UFUNCTION(BlueprintCallable, Category = "Daedalus") bool FireGuns();
	/** For the harness: drive for one frame as if the stick were at (Forward, Right), -1..1. */
	UFUNCTION(BlueprintCallable, Category = "Daedalus") void Drive(float Forward, float Right, bool bBoost);

	/** Become the realm's mount (DaedalusMountCore: drone, helicopter, plane, sky-strider; World Zero's bike for
	 *  the rest): the profile's hover/top/boost/ceiling, and Sol's rigged art on the frame when it is imported
	 *  (the cube bike shows otherwise). Returns what it became. */
	UFUNCTION(BlueprintCallable, Category = "Daedalus|Mount") FString Wear(const FString& Realm);
	/** Ask a flying mount for a height over the ground (cm); clamped to the profile. Ground-huggers ignore it. */
	UFUNCTION(BlueprintCallable, Category = "Daedalus|Mount") void Lift(float OverGroundCm);
	UFUNCTION(BlueprintCallable, Category = "Daedalus|Mount") FString MountState() const;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Daedalus|Mount") FString MountRealm = TEXT("WORLD-ZERO");
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Daedalus|Mount") FString MountName = TEXT("hover bike");
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Daedalus|Mount") FString MountArt;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Daedalus|Mount") bool bMountArt = false;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Daedalus|Mount") float CeilingCm = 0.f;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Daedalus|Mount") float WantedHeight = 0.f;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Daedalus|Mount") TObjectPtr<class USkeletalMeshComponent> Skin;

protected:
	virtual void BeginPlay() override;

private:
	UStaticMeshComponent* Part(const FName Name, const FVector& Size, const FVector& At, const FLinearColor& Color);
	void Move(const FInputActionValue& V);
	void Look(const FInputActionValue& V);
	void LookMouse(const FInputActionValue& V);
	void BoostOn() { bBoost = true; }
	void BoostOff() { bBoost = false; }
	void TriggerHeld() { FireGuns(); }
	void Shot(const FVector& Muzzle);

	UPROPERTY() TObjectPtr<UStaticMesh> Cube;
	UPROPERTY() TObjectPtr<UInputMappingContext> Mapping;
	UPROPERTY() TObjectPtr<UInputAction> MoveAction;
	UPROPERTY() TObjectPtr<UInputAction> LookAction;
	UPROPERTY() TObjectPtr<UInputAction> LookMouseAction;
	UPROPERTY() TObjectPtr<UInputAction> FireAction;
	UPROPERTY() TObjectPtr<UInputAction> BoostAction;
	UPROPERTY() TObjectPtr<UInputAction> ExitAction;
	UPROPERTY() TObjectPtr<UStaticMeshComponent> GunL;
	UPROPERTY() TObjectPtr<UStaticMeshComponent> GunR;

	FVector2D Stick = FVector2D::ZeroVector;
	FVector LastGround = FVector::ZeroVector;
	bool bBoost = false;
	bool bLeftGun = false;
	float FireCooldown = 0.f;
	float Bank = 0.f;
};
