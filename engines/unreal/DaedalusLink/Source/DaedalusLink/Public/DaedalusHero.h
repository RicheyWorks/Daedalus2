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
class UInputModifierDeadZone;
class UMaterialInterface;
class SDaedalusSettingsMenu;
class SDaedalusFieldMenu;
class SDaedalusHud;
class SWidget;
struct FInputActionValue;

/** A foe's numbers, from the Daedalus server's /api/v1/hero/rules (ADR-037), with a built-in copy of the same table. */
struct FDaedalusFoeRule
{
	FString Kind;
	FString Title;
	int32 Life = 1;
	int32 Power = 1;
	int32 Exp = 1;
};

/**
 * The Daedalus hero (ADR-040, -041, -042): a blocky adventurer with a sword and a blaster, built in code so he needs
 * no assets.
 *
 * Views (R3 / D-pad up / V cycles; Settings > Video): FIRST PERSON with a centred reticle (Halo Infinite), OVER THE
 * SHOULDER with a shoulder swap (Gears of War; LB / D-pad down / C), and CLASSIC chase.
 * Weapons (Y / 1 / 2 / mouse wheel): the SWORD (Zelda II: swing, down-thrust in the air) and the BLASTER (hitscan
 * from the reticle, heat and overheat, zoom on the aim button). Melee always swings the sword.
 * Controls: keyboard and mouse (raw mouse look), XInput pads with Halo Infinite's button layouts (Default, Bumper
 * Jumper, Bumper Ninja, Boxer, Green Thumb, Recon) and thumbstick layouts (Default, Southpaw, Legacy, Legacy
 * Southpaw), and generic USB pads (Switch Pro, N64) through RawInput and Saved/Config/DaedalusControllers.json.
 * See docs/controllers.md.
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

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus") float SwingTime = 0.22f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus") float DashSpeed = 1800.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus") float FallLimit = 2500.f;

	// The record (the harness and the field menu read these).
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Daedalus") int32 Swings = 0;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Daedalus") int32 Bounces = 0;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Daedalus") int32 Respawns = 0;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Daedalus") int32 ShotsFired = 0;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Daedalus") int32 Hits = 0;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Daedalus") int32 Kills = 0;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Daedalus") int32 Exp = 0;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Daedalus") FVector LastGround = FVector::ZeroVector;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Daedalus") bool bShielding = false;

	// Weapons and views.
	/** 0 = sword, 1 = blaster. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Daedalus") int32 CurrentWeapon = 0;
	/** 0 = first person, 1 = over the shoulder, 2 = classic chase. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Daedalus") int32 CameraView = 1;
	/** +1 right shoulder, -1 left. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Daedalus") float ShoulderSide = 1.f;
	/** Blaster heat 0..1; at 1 it overheats and vents. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Daedalus") float Heat = 0.f;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Daedalus") bool bOverheated = false;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Daedalus") bool bAiming = false;

	UFUNCTION(BlueprintCallable, Category = "Daedalus") void Swing();
	UFUNCTION(BlueprintCallable, Category = "Daedalus") void Melee();
	UFUNCTION(BlueprintCallable, Category = "Daedalus") bool Fire();
	UFUNCTION(BlueprintCallable, Category = "Daedalus") void SwitchWeapon();
	UFUNCTION(BlueprintCallable, Category = "Daedalus") void Dash();
	UFUNCTION(BlueprintCallable, Category = "Daedalus") void CycleView();
	UFUNCTION(BlueprintCallable, Category = "Daedalus") void SwapShoulder();
	UFUNCTION(BlueprintCallable, Category = "Daedalus") void Respawn();
	/** Put N foes (ADR-037's four kinds, in turn) in front of the hero. Returns how many were placed. */
	UFUNCTION(BlueprintCallable, Category = "Daedalus") int32 SpawnFoes(int32 Count);
	/** Turn so the reticle is on a world point (the harness aims with it). */
	UFUNCTION(BlueprintCallable, Category = "Daedalus") void AimAt(FVector Point);
	/** Interact (X / E): get on the nearest Ghost within reach. Returns true if he mounted. */
	UFUNCTION(BlueprintCallable, Category = "Daedalus") bool Interact();
	/** Put a Ghost (ADR-043) on the ground a few steps ahead. Returns it. */
	UFUNCTION(BlueprintCallable, Category = "Daedalus") class ADaedalusGhost* SpawnVehicle();
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus") float InteractReach = 350.f;

	// Menus (ADR-041).
	UFUNCTION(BlueprintCallable, Category = "Daedalus") void ToggleSettings();
	UFUNCTION(BlueprintCallable, Category = "Daedalus") bool IsSettingsOpen() const;
	UFUNCTION(BlueprintCallable, Category = "Daedalus") void ToggleField();
	UFUNCTION(BlueprintCallable, Category = "Daedalus") bool IsFieldOpen() const;
	UFUNCTION(BlueprintCallable, Category = "Daedalus") FString FieldInput(const FString& Command);
	UFUNCTION(BlueprintCallable, Category = "Daedalus") FString MenuInput(const FString& Command);
	UFUNCTION(BlueprintCallable, Category = "Daedalus") void ApplySettings();
	UFUNCTION(BlueprintCallable, Category = "Daedalus") bool SetSetting(FName Id, float Value);
	UFUNCTION(BlueprintCallable, Category = "Daedalus") float GetSetting(FName Id) const;
	UFUNCTION(BlueprintCallable, Category = "Daedalus") TArray<FString> DescribeBindings() const;
	UFUNCTION(BlueprintCallable, Category = "Daedalus") static FString ControllerProfilePath();

	// For the HUD.
	float HitMarkerTime() const { return SinceHit; }
	float Bloom() const { return Spread; }
	bool ShowsReticle() const;
	FString WeaponName() const;
	FString ViewName() const;
	static const TArray<FDaedalusFoeRule>& FoeRules();

protected:
	virtual void BeginPlay() override;
	virtual void EndPlay(const EEndPlayReason::Type Reason) override;

private:
	UStaticMeshComponent* Block(USceneComponent* Parent, const FName Name, const FVector& Size, const FVector& At,
	                            const FLinearColor& Color, bool bBody = true);
	void Move(const FInputActionValue& V);
	void LookMouse(const FInputActionValue& V);
	void LookStick(const FInputActionValue& V);
	void AttackStart();
	void AttackHeld();
	void AimOn();
	void AimOff();
	void InteractPressed() { Interact(); }
	void SprintOn();
	void SprintOff();
	void Rumble(float Intensity, float Seconds) const;
	void RebuildBindings();
	void MapProfile();
	void MapSpec(UInputAction* A, const FString& Spec, int32 Stick = 0);
	void ApplyCameraView();
	void ShowWeapon();
	void HitArea(const FVector& Center, float Radius, float Amount);
	void Damage(AActor* Target, float Amount, const FVector& From);
	void Flash(const FVector& At, const FVector& Size, const FRotator& Rot, const FLinearColor& Color, float Life);
	void FetchFoeRules();
	void ShowOverlay(const TSharedRef<SWidget>& Content, const TSharedRef<SWidget>& Focus, TSharedPtr<SWidget>& Host);
	void HideOverlay(TSharedPtr<SWidget>& Host);

	UPROPERTY() TObjectPtr<UStaticMesh> Cube;
	UPROPERTY() TObjectPtr<UInputMappingContext> Mapping;
	UPROPERTY() TObjectPtr<UInputAction> MoveAction;
	UPROPERTY() TObjectPtr<UInputAction> LookMouseAction;
	UPROPERTY() TObjectPtr<UInputAction> LookStickAction;
	UPROPERTY() TObjectPtr<UInputAction> JumpAction;
	UPROPERTY() TObjectPtr<UInputAction> AttackAction;
	UPROPERTY() TObjectPtr<UInputAction> MeleeAction;
	UPROPERTY() TObjectPtr<UInputAction> DashAction;
	UPROPERTY() TObjectPtr<UInputAction> AimAction;
	UPROPERTY() TObjectPtr<UInputAction> SwitchAction;
	UPROPERTY() TObjectPtr<UInputAction> InteractAction;
	UPROPERTY() TObjectPtr<UInputAction> SprintAction;
	UPROPERTY() TObjectPtr<UInputAction> ViewCycleAction;
	UPROPERTY() TObjectPtr<UInputAction> ShoulderAction;
	UPROPERTY() TObjectPtr<UInputAction> MenuAction;
	UPROPERTY() TObjectPtr<UInputAction> ViewAction;
	UPROPERTY() TArray<TObjectPtr<UInputModifierDeadZone>> LeftDeadzones;
	UPROPERTY() TArray<TObjectPtr<UInputModifierDeadZone>> RightDeadzones;
	UPROPERTY() TArray<TObjectPtr<UStaticMeshComponent>> Legs;
	UPROPERTY() TArray<TObjectPtr<UStaticMeshComponent>> Arms;
	UPROPERTY() TArray<TObjectPtr<UStaticMeshComponent>> BodyBlocks;
	UPROPERTY() TArray<TObjectPtr<UStaticMeshComponent>> SwordBlocks;
	UPROPERTY() TArray<TObjectPtr<UStaticMeshComponent>> GunBlocks;
	UPROPERTY() TObjectPtr<UStaticMeshComponent> GunTip;
	UPROPERTY() TObjectPtr<UMaterialInterface> FlashMaterial;

	TSharedPtr<SDaedalusSettingsMenu> Menu;
	TSharedPtr<SWidget> MenuHost;
	TSharedPtr<SDaedalusFieldMenu> Field;
	TSharedPtr<SWidget> FieldHost;
	TSharedPtr<SDaedalusHud> Hud;
	TSharedPtr<SWidget> HudHost;

	int32 AppliedButtonLayout = -1;
	int32 AppliedStickLayout = -1;
	bool bShieldToggle = false;
	bool bSprinting = false;
	float LookHeld = 0.f;
	float SwingLeft = 0.f;
	bool bThrusting = false;
	float WalkPhase = 0.f;
	float FireCooldown = 0.f;
	float SinceHit = 99.f;
	float Spread = 0.f;
	float BaseFov = 80.f;
};

/** The game mode that plays as the Daedalus hero. Set it as the level's GameMode Override (daedalus.hero_setup). */
UCLASS()
class DAEDALUSLINK_API ADaedalusGameMode : public AGameModeBase
{
	GENERATED_BODY()

public:
	ADaedalusGameMode();
};
