// SPDX-License-Identifier: MIT

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Character.h"
#include "GameFramework/GameModeBase.h"
#include "DaedalusHero.generated.h"

class UCameraComponent;
class USpringArmComponent;
class UStaticMesh;
class UStaticMeshComponent;
class UInputAction;
class UInputMappingContext;
struct FInputActionValue;

/**
 * The Daedalus hero (ADR-036): a blocky adventurer with a sword, built entirely in code so it needs no assets.
 * WASD or the left stick walks, the mouse or right stick looks, Space jumps, Shift dashes, and the left mouse
 * button or J swings the sword. Swinging in the air is the Zelda II down-thrust: it drives the hero down and
 * bounces off what it hits. Input is Enhanced Input, with the actions and mapping made at runtime.
 */
UCLASS(Blueprintable)
class DAEDALUSLINK_API ADaedalusHero : public ACharacter
{
	GENERATED_BODY()

public:
	ADaedalusHero();

	virtual void Tick(float DeltaSeconds) override;
	virtual void SetupPlayerInputComponent(UInputComponent* Input) override;
	virtual void Landed(const FHitResult& Hit) override;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Daedalus") TObjectPtr<USpringArmComponent> Boom;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Daedalus") TObjectPtr<UCameraComponent> Camera;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Daedalus") TObjectPtr<USceneComponent> Body;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Daedalus") TObjectPtr<USceneComponent> SwordPivot;

	/** How long a swing lasts, in seconds. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus") float SwingTime = 0.22f;
	/** Dash speed burst, cm/s. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus") float DashSpeed = 1800.f;
	/** Swings so far (the harness reads it). */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Daedalus") int32 Swings = 0;
	/** Down-thrusts that bounced (the harness reads it). */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Daedalus") int32 Bounces = 0;

	UFUNCTION(BlueprintCallable, Category = "Daedalus") void Swing();
	UFUNCTION(BlueprintCallable, Category = "Daedalus") void Dash();

protected:
	virtual void BeginPlay() override;

private:
	UStaticMeshComponent* Block(USceneComponent* Parent, const FName Name, const FVector& Size, const FVector& At,
	                            const FLinearColor& Color);
	void Move(const FInputActionValue& V);
	void Look(const FInputActionValue& V);

	UPROPERTY() TObjectPtr<UStaticMesh> Cube;
	UPROPERTY() TObjectPtr<UInputMappingContext> Mapping;
	UPROPERTY() TObjectPtr<UInputAction> MoveAction;
	UPROPERTY() TObjectPtr<UInputAction> LookAction;
	UPROPERTY() TObjectPtr<UInputAction> JumpAction;
	UPROPERTY() TObjectPtr<UInputAction> SwingAction;
	UPROPERTY() TObjectPtr<UInputAction> DashAction;
	UPROPERTY() TArray<TObjectPtr<UStaticMeshComponent>> Legs;
	UPROPERTY() TArray<TObjectPtr<UStaticMeshComponent>> Arms;

	float SwingLeft = 0.f;
	bool bThrusting = false;
	float WalkPhase = 0.f;
};

/** The game mode that plays as the Daedalus hero. Set it as the level's GameMode Override. */
UCLASS()
class DAEDALUSLINK_API ADaedalusGameMode : public AGameModeBase
{
	GENERATED_BODY()

public:
	ADaedalusGameMode();
};
