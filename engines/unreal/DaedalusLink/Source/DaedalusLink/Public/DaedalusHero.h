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
 * Controls (see docs/controllers.md): keyboard and mouse, XInput pads (Xbox Elite Series 2, GameSir, Razer
 * Wolverine/Kishi) and, through RawInput, generic USB pads (Switch Pro, N64 USB controllers and adapters) mapped
 * from Saved/Config/DaedalusControllers.json. WASD, the left stick or the d-pad walks; the mouse (raw, unsmoothed,
 * so a Razer 8K's polling comes through) or the right stick looks; Space/A jumps; Shift/B/RB dashes; left mouse,
 * J, X or RT swings; right mouse, K, LT or LB raises the shield. Swinging in the air is the Zelda II down-thrust: it drives the hero down and
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
	/** Falls off an island that put the hero back on the last ground he stood on (the harness reads it). */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Daedalus") int32 Respawns = 0;
	/** How far below the last ground counts as fallen off, in cm. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus") float FallLimit = 2500.f;
	/** The last spot the hero stood on solid ground. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Daedalus") FVector LastGround = FVector::ZeroVector;

	/** Put the hero back on the last ground he stood on. */
	UFUNCTION(BlueprintCallable, Category = "Daedalus") void Respawn();

	/** True while the shield is up (blocks later; slows the walk now). */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Daedalus") bool bShielding = false;

	UFUNCTION(BlueprintCallable, Category = "Daedalus") void Swing();
	/** Every binding as "Action <- Key [modifiers]", for the harness and the controller docs. */
	UFUNCTION(BlueprintCallable, Category = "Daedalus") TArray<FString> DescribeBindings() const;
	/** Where the controller profile lives (written with defaults on first play). */
	UFUNCTION(BlueprintCallable, Category = "Daedalus") static FString ControllerProfilePath();
	UFUNCTION(BlueprintCallable, Category = "Daedalus") void Dash();

protected:
	virtual void BeginPlay() override;

private:
	UStaticMeshComponent* Block(USceneComponent* Parent, const FName Name, const FVector& Size, const FVector& At,
	                            const FLinearColor& Color);
	void Move(const FInputActionValue& V);
	void LookMouse(const FInputActionValue& V);
	void LookStick(const FInputActionValue& V);
	void ShieldOn();
	void ShieldOff();
	void Rumble(float Intensity, float Seconds) const;
	void MapProfile();
	void MapSpec(UInputAction* A, const FString& Spec);

	UPROPERTY() TObjectPtr<UStaticMesh> Cube;
	UPROPERTY() TObjectPtr<UInputMappingContext> Mapping;
	UPROPERTY() TObjectPtr<UInputAction> MoveAction;
	UPROPERTY() TObjectPtr<UInputAction> LookMouseAction;
	UPROPERTY() TObjectPtr<UInputAction> LookStickAction;
	UPROPERTY() TObjectPtr<UInputAction> ShieldAction;
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
