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
class SDaedalusInventory;
class SDaedalusDialogue;
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
	virtual float TakeDamage(float Damage, const FDamageEvent& Event, AController* EventInstigator, AActor* DamageCauser) override;

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

	// Halo-style vitals (ADR-044): the energy shield takes hits first and recharges after ShieldDelay seconds
	// untouched; health refills once the shield is full. At zero health he falls and comes back at the start.
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus") float MaxShield = 100.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus") float MaxHealth = 100.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus") float ShieldDelay = 4.f;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Daedalus") float Shield = 100.f;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Daedalus") float Health = 100.f;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Daedalus") float DamageTaken = 0.f;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Daedalus") int32 Deaths = 0;
	/** For the harness and for building: nothing hurts him. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus") bool bInvulnerable = false;
	/** Shield recharge per second once it starts. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus") float ShieldRate = 50.f;

	// Armor (ADR-047): 0 Recruit, 1 Scout, 2 Vanguard, 3 Paragon. Each tier: +40 shield, a quicker recharge.
	// Three shield cores (dropped by knights and some shardbacks) raise a tier. Kept in Saved/Config/DaedalusHero.json.
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Daedalus") int32 ArmorTier = 0;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Daedalus") int32 ShieldCores = 0;
	UFUNCTION(BlueprintCallable, Category = "Daedalus") void AddShieldCore();
	/** Halo's overshield: shield past full, fading slowly. */
	UFUNCTION(BlueprintCallable, Category = "Daedalus") void GiveOvershield(float Amount);
	UFUNCTION(BlueprintCallable, Category = "Daedalus") void SetArmorTier(int32 Tier);
	UFUNCTION(BlueprintCallable, Category = "Daedalus") FString ArmorName() const;
	// Encounters (ADR-046), for the harness.
	UFUNCTION(BlueprintCallable, Category = "Daedalus") FString EncounterStats() const;

	// Dig and build (ADR-049), the third tool: the PICK. Hold attack on a cube to mine it into the bag (harder
	// cubes take longer); aim places the selected cube against the face you look at. R / D-pad left picks the cube.
	// Survival rules: you place what you mined (daedalus.Creative 1: anything, endlessly).
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Daedalus") TMap<FString, int32> Bag;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Daedalus") FString SelectedCube;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Daedalus") float MineProgress = 0.f;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Daedalus") int32 CubesMined = 0;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Daedalus") int32 CubesPlaced = 0;
	/** The cube under the reticle (within reach), and its type. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Daedalus") FIntVector TargetCube = FIntVector::ZeroValue;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Daedalus") FString TargetType;
	UFUNCTION(BlueprintCallable, Category = "Daedalus") bool MineTarget();
	UFUNCTION(BlueprintCallable, Category = "Daedalus") bool PlaceCube();
	UFUNCTION(BlueprintCallable, Category = "Daedalus") void NextCube();
	/** Seconds to mine a cube of this type (0: can't be mined). */
	UFUNCTION(BlueprintCallable, Category = "Daedalus") static float Hardness(const FString& Type);
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus") float Reach = 550.f;

	// Common sense (ADR-049): falls hurt, water slows a fall and you swim up with jump, the void kills.
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Daedalus") bool bInWater = false;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Daedalus") float FallDamageTaken = 0.f;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Daedalus") float LastLandingSpeed = 0.f;
	UFUNCTION(BlueprintCallable, Category = "Daedalus") int32 SpawnPack();

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
	/** The foes' route finder's record (searches, routes found, cells expanded, floor samples). */
	UFUNCTION(BlueprintCallable, Category = "Daedalus") FString NavStats() const;
	/** For the harness: run one route search and report it, with the floors the finder reads around the start. */
	UFUNCTION(BlueprintCallable, Category = "Daedalus") TArray<FString> NavProbe(FVector From, FVector To);
	UFUNCTION(BlueprintCallable, Category = "Daedalus") FString NavTrace(FVector At, float RefZ);
	/** Turn so the reticle is on a world point (the harness aims with it). */
	UFUNCTION(BlueprintCallable, Category = "Daedalus") void AimAt(FVector Point);
	/** Interact (X / E): get on the nearest Ghost within reach. Returns true if he mounted. */
	UFUNCTION(BlueprintCallable, Category = "Daedalus") bool Interact();
	/** Put a Ghost (ADR-043) on the ground a few steps ahead. Returns it. */
	UFUNCTION(BlueprintCallable, Category = "Daedalus") class ADaedalusGhost* SpawnVehicle();
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus") float InteractReach = 350.f;

	// The 8-bit realm behind a portal (ADR-052).
	/** Step through a portal: the world turns into the 8-bit realm for Seed, generated by the Java engines on the server
	 *  (the realm shipped in Content/Realm when the server is down). The party keeps its levels between trips. */
	UFUNCTION(BlueprintCallable, Category = "Daedalus") void EnterRealm(int64 Seed);
	/** Back through the portal: saves the party and returns to the 3D world. */
	UFUNCTION(BlueprintCallable, Category = "Daedalus") void ExitRealm();
	UFUNCTION(BlueprintCallable, Category = "Daedalus") bool IsRealmOpen() const;
	/** For the harness: drive the realm. up/down/left/right/a/b/start tap a button; hold:<b> / release:<b>; tick:<s>;
	 *  place:<MAP>:<x>:<y>:<facing>; give:<ITEM>:<n>; gold:<n>; battle:<ID>+<ID>; autofight; toughen; portal (stand below it); save; spec.
	 *  Returns the realm's state line (or the save text for 'save'). */
	UFUNCTION(BlueprintCallable, Category = "Daedalus") FString RealmInput(const FString& Command);
	UFUNCTION(BlueprintCallable, Category = "Daedalus") FString RealmState() const;

	// The tabbed inventory (hub 28570/28573/28574): I or d-pad up opens it over the game. One interaction in every
	// realm; the realm's catalog (Content/Inventory/<realm>.dic) brings its tabs, items, slots, actions and theme.
	UFUNCTION(BlueprintCallable, Category = "Daedalus") void ToggleInventory();
	UFUNCTION(BlueprintCallable, Category = "Daedalus") bool IsInventoryOpen() const;
	/** For the harness: tab+ tab- up down left right accept back; realm:<name> picks the catalog (world-zero, gallery-city,
	 *  parcels, bricks, labyrinth); give:<ID>:<n> and wear:<SLOT>:<ID> stock the satchel; state. Returns the model's line. */
	UFUNCTION(BlueprintCallable, Category = "Daedalus") FString InventoryInput(const FString& Command);
	/** Which catalog this world uses: InventoryRealm when set, else from the map's name, else world-zero. */
	UFUNCTION(BlueprintCallable, Category = "Daedalus") FString InventoryCatalogName() const;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus") FString InventoryRealm;

	// Control from the bridge (Richey 2026-10-13: "more control over Unreal"): real Enhanced Input injected into the
	// hero's actions, so a harness or a bot plays the game the way a pad does; and the two editor-ish moves a tester
	// wants without a cheat console.
	/** Inject an action for Seconds (0 = one frame): Move (X right, Y forward), LookStick, Jump, Attack, Melee, Dash, Aim,
	 *  Switch, Interact, Sprint, ViewCycle, CallVehicle, NextCube, Shoulder, Menu, View, Inventory. Returns what was injected. */
	UFUNCTION(BlueprintCallable, Category = "Daedalus|Control") FString Inject(const FString& Action, FVector Value, float Seconds);
	/** Put the hero at a world point (feet on the ground when Snap), facing Yaw. */
	UFUNCTION(BlueprintCallable, Category = "Daedalus|Control") bool Teleport(FVector Where, float Yaw, bool bSnap);
	/** Point the camera: yaw/pitch in degrees (the control rotation). */
	UFUNCTION(BlueprintCallable, Category = "Daedalus|Control") void Look(float Yaw, float Pitch);
	/** One line of everything a tester wants: position, yaw, health/shield, weapon, realm, speed, what is open. */
	UFUNCTION(BlueprintCallable, Category = "Daedalus|Control") FString ControlState() const;

	// The realm session (hub 28885): which realm this player is in and how they move between them. The rules are
	// DaedalusRealmSessionCore.h; a switch sets the inventory catalog and dialogue theme, saves the session, and
	// tells the realm hosts (world actors, Sol's Ocean view) through OnRealmChange so they stream the right world.
	/** Where the player is: WORLD-ZERO, GALLERY-CITY, PARCELS, BRICKS, LABYRINTH, PORTAL, OCEAN. */
	UFUNCTION(BlueprintCallable, Category = "Daedalus|Realm") FString RealmNow() const;
	/** Go to a realm by a way: gate, portal, dock, shore. Detail: "boat:<dock>" / "sub:<dock>" for a dock.
	 *  Returns "ok <from> -> <to> hint=<where>" or "refused: <why>". Nothing moves on a refusal. */
	UFUNCTION(BlueprintCallable, Category = "Daedalus|Realm") FString SwitchRealm(const FString& To, const FString& Via, const FString& Detail);
	UFUNCTION(BlueprintCallable, Category = "Daedalus|Realm") FString RealmSessionState() const;
	DECLARE_MULTICAST_DELEGATE_FourParams(FOnRealmChange, const FString& /*From*/, const FString& /*To*/, const FString& /*Via*/, const FString& /*Hint*/);
	/** Realm hosts subscribe: leave From, enter To at Hint. World Zero's world actor and the Portal are wired here. */
	FOnRealmChange OnRealmChange;

	// Dialogue (Richey, 2026-10-13): every realm has dialogue boxes. The 3D realms speak through SDaedalusDialogue in
	// the realm's theme (Animal Crossing's bubble, name tag, babble); the 8-bit realm keeps its FF1 window.
	/** An NPC speaks: opens the box (or queues behind the line showing). Choices end the line on a pick. */
	UFUNCTION(BlueprintCallable, Category = "Daedalus") void Speak(const FString& Speaker, const FString& Text, const TArray<FString>& Choices);
	UFUNCTION(BlueprintCallable, Category = "Daedalus") bool IsDialogueOpen() const;
	/** For the harness: a b up down tick:<s> state. Returns the model's line plus last=<outcome>. */
	UFUNCTION(BlueprintCallable, Category = "Daedalus") FString DialogueInput(const FString& Command);
	/** The last outcome: "closed:<speaker>" or "choice:<n>:<speaker>" (quests read it). */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Daedalus") FString LastDialogue;
	DECLARE_MULTICAST_DELEGATE_TwoParams(FOnDialogueChoice, const FString& /*Speaker*/, int32 /*Choice: -1 closed*/);
	FOnDialogueChoice OnDialogueChoice;
	/** A realm's own loot (item id -> count) and what is worn (slot -> item id). World Zero's bag is the cubes + tools. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Daedalus") TMap<FString, int32> Satchel;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Daedalus") TMap<FString, FString> Worn;
	/** Write the realm's screen to a PNG (3x), straight from its framebuffer: no viewport capture needed. */
	UFUNCTION(BlueprintCallable, Category = "Daedalus") bool RealmCapture(const FString& Path);
	/** A portal cube at or around the hero's feet, if there is one. */
	bool PortalNear(FIntVector& Out) const;
	static FString RealmSavePath();

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
	float SinceHurt() const { return SinceDamaged; }
	/** Where the last blow came from, in degrees from straight ahead on screen (+ right); for the HUD's arc. */
	float HitDirection() const;
	bool HasHitDirection() const { return bHitFromSomewhere; }
	float Bloom() const { return Spread; }
	bool ShowsReticle() const;
	FString WeaponName() const;
	FString ViewName() const;
	static const TArray<FDaedalusFoeRule>& FoeRules();

protected:
	virtual void BeginPlay() override;
	virtual void EndPlay(const EEndPlayReason::Type Reason) override;

private:
	TWeakObjectPtr<class ADaedalusGhost> CalledGhost;
	float SinceDamaged = 100.f;
	FVector HitFrom = FVector::ZeroVector;
	bool bHitFromSomewhere = false;
	void Fall();
	void ApplyArmor();
	void LoadProgress();
	void SaveProgress() const;
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
	void UpdateTarget(float Dt);
	void MineHeld(float Dt);
	void CallVehiclePressed();
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
	UPROPERTY() TObjectPtr<UInputAction> CallVehicleAction;
	UPROPERTY() TObjectPtr<UInputAction> NextCubeAction;
	UPROPERTY() TObjectPtr<USceneComponent> Cursor;
	UPROPERTY(Transient) TArray<TObjectPtr<UStaticMeshComponent>> PickBlocks;
	bool bHasTarget = false;
	FIntVector PlaceAt = FIntVector::ZeroValue;
	FIntVector MiningCube = FIntVector(MAX_int32, 0, 0);
	float SinceWater = 100.f;
	float BaseGravity = 1.6f;
	float BaseAirControl = 0.65f;
	UPROPERTY() TObjectPtr<UInputAction> ShoulderAction;
	UPROPERTY() TObjectPtr<UInputAction> MenuAction;
	UPROPERTY() TObjectPtr<UInputAction> ViewAction;
	UPROPERTY() TObjectPtr<UInputAction> InventoryAction;
	UPROPERTY() TArray<TObjectPtr<UInputModifierDeadZone>> LeftDeadzones;
	UPROPERTY() TArray<TObjectPtr<UInputModifierDeadZone>> RightDeadzones;
	UPROPERTY(Transient) TArray<TObjectPtr<UStaticMeshComponent>> Legs;
	UPROPERTY(Transient) TArray<TObjectPtr<UStaticMeshComponent>> Arms;
	UPROPERTY(Transient) TArray<TObjectPtr<UStaticMeshComponent>> BodyBlocks;
	UPROPERTY(Transient) TArray<TObjectPtr<UStaticMeshComponent>> SwordBlocks;
	UPROPERTY(Transient) TArray<TObjectPtr<UStaticMeshComponent>> GunBlocks;
	UPROPERTY() TObjectPtr<UStaticMeshComponent> GunTip;
	UPROPERTY() TObjectPtr<UMaterialInterface> FlashMaterial;

	TSharedPtr<SDaedalusSettingsMenu> Menu;
	TSharedPtr<SWidget> MenuHost;
	TSharedPtr<SDaedalusFieldMenu> Field;
	TSharedPtr<SWidget> FieldHost;
	TSharedPtr<SDaedalusInventory> Inventory;
	TSharedPtr<SWidget> InventoryHost;
	TSharedPtr<SDaedalusDialogue> Dialogue;
	TSharedPtr<SWidget> DialogueHost;
	TArray<FString> DialogueSfx;
	TSharedPtr<struct FDaedalusRealmSessionHolder> RealmSession;
	struct FInjected { TObjectPtr<UInputAction> Action; FVector Value; float Left; };
	TArray<FInjected> Injected;
	UInputAction* ActionNamed(const FString& Name) const;
	FString RealmSessionLine;   // saved with progress
	void DialogueOutcome(const struct FDaedalusDialogueOutcome& Outcome);
	void DialogueSound(const FString& Event);
	TSharedPtr<struct FDaedalusCatalogHolder> InventoryCatalog;
	void InventoryBag(TMap<FString, int32>& OutBag, TMap<FString, FString>& OutWorn) const;
	void InventoryIntent(const struct FDaedalusInventoryIntent& Intent);
	FString InventoryLog;
	TSharedPtr<SDaedalusHud> Hud;
	TSharedPtr<SWidget> HudHost;
	TSharedPtr<class SDaedalusRealm> RealmView;
	/** The 3D battle stage (Sol's ADaedalusBattlePresentation) that plays the 8-bit realm's cues; found once per Play. */
	TWeakObjectPtr<class ADaedalusBattlePresentation> Stage;
	bool bStageLooked = false;
	int32 CuesStaged = 0;
	TSharedPtr<SWidget> RealmHost;
	FString RealmSource;
	void RealmReady(const FString& Spec, const FString& Source);
	void RealmWantsOut();

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
