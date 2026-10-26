// SPDX-License-Identifier: MIT

#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "Subsystems/WorldSubsystem.h"
#include "DaedalusTonicCore.h"
#include "DaedalusTonic.generated.h"

class IHttpRequest;

/**
 * Kennel Isle trough tonics in Unreal (TONIC 1, docs/contracts/tonic-v1, docs/KENNEL_ISLE_TONIC_TROUGH.md).
 * Java (TonicBrewer behind POST /api/v1/kennel/brew) does every calculation; this file only
 *   - gathers the Tonic_Herb_<Name> herbs a player drops in the trough,
 *   - asks Java once to STEEP them (proves a recipe exists; 3 drinks, flat after 10 minutes),
 *   - asks Java again for EACH pet that drinks (its coat, drinker kind, stage, charm decide the strength),
 *   - applies the reply exactly once to that pet (UDaedalusTonicEffects): mods, grants, breed chance.
 * All parsing, bounds, decay and stacking live in DaedalusTonicCore.h, tested in core-test/tonic_core_test.cpp.
 * UDaedalusTonicSubsystem adds the trough component to the placed Brew_Trough actor at BeginPlay, so no level edit is needed.
 */

UENUM(BlueprintType)
enum class EDaedalusTroughPhase : uint8 { Empty, Gathering, Steeping, Steeped };

DECLARE_DYNAMIC_MULTICAST_DELEGATE_TwoParams(FDaedalusTonicSteeped, const FString&, RecipeId, int32, HerbCount);
DECLARE_DYNAMIC_MULTICAST_DELEGATE_ThreeParams(FDaedalusTonicDrunk, AActor*, Drinker, const FString&, RecipeId, bool, bSecondRoll);
DECLARE_DYNAMIC_MULTICAST_DELEGATE_TwoParams(FDaedalusTonicRefused, int32, Status, const FString&, Reason);
DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FDaedalusTonicExpired, const FString&, RecipeId);
/** A pulse tonic's one-shot modifier, handed to the owner once (Coppercap and friends). Op is "add" or "mul". */
DECLARE_DYNAMIC_MULTICAST_DELEGATE_FourParams(FDaedalusTonicPulse, const FString&, RecipeId, const FString&, Stat, const FString&, Op, float, Value);

/** What the tonics are doing to one pet. Read stats through GetStat so a tonic's mods apply without changing the pet's own numbers. */
UCLASS(ClassGroup = (Daedalus), meta = (BlueprintSpawnableComponent))
class DAEDALUSLINK_API UDaedalusTonicEffects : public UActorComponent
{
	GENERATED_BODY()
public:
	UDaedalusTonicEffects();
	virtual void TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction) override;

	/** Parse a TONIC 1 reply and apply it. All-or-nothing: false (see LastError) changes nothing. */
	UFUNCTION(BlueprintCallable, Category = "Daedalus|Tonic") bool ApplyTonicText(const FString& Reply);
	/** (Base + active adds) * active muls for a stat such as hearts, speed, damage, blunt, cooldownPct, loyalty, hazardResist, expPct. */
	UFUNCTION(BlueprintPure, Category = "Daedalus|Tonic") float GetStat(const FString& Stat, float Base) const;
	UFUNCTION(BlueprintPure, Category = "Daedalus|Tonic") bool HasGrant(const FString& Grant) const;
	UFUNCTION(BlueprintPure, Category = "Daedalus|Tonic") float GetBreedChancePct() const;
	UFUNCTION(BlueprintPure, Category = "Daedalus|Tonic") bool IsTonicActive(const FString& RecipeId) const;
	UFUNCTION(BlueprintPure, Category = "Daedalus|Tonic") int32 ActiveCount() const { return (int32)Ledger.Count(); }
	UFUNCTION(BlueprintPure, Category = "Daedalus|Tonic") FString LastError() const { return Error; }

	UPROPERTY(BlueprintAssignable, Category = "Daedalus|Tonic") FDaedalusTonicExpired OnTonicExpired;
	UPROPERTY(BlueprintAssignable, Category = "Daedalus|Tonic") FDaedalusTonicPulse OnTonicPulse;

	/** Find (or add) the component on an actor. */
	static UDaedalusTonicEffects* For(AActor* Actor);
private:
	double Now() const;
	daedalus::tonic::Ledger Ledger;
	FString Error;
};

/** The Kennel Isle brew trough: herbs in, Interact to steep, pets drink. Credentials are never saved (not UPROPERTY/config). */
UCLASS(ClassGroup = (Daedalus), meta = (BlueprintSpawnableComponent))
class DAEDALUSLINK_API UDaedalusBrewTroughComponent : public UActorComponent
{
	GENERATED_BODY()
public:
	UDaedalusBrewTroughComponent();
	virtual void TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction) override;
	virtual void OnComponentDestroyed(bool bDestroyingHierarchy) override;
	virtual void EndPlay(const EEndPlayReason::Type Reason) override;

	/** Pets within this many cm of the trough drink on their own when bAutoDrink is on (the Interact key stand-in, like ADaedalusWaterSource). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|Tonic") float Reach = 300.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|Tonic") bool bAutoDrink = true;

	/**
	 * Origin of the Daedalus server (https anywhere, http only to 127.0.0.1) and the host's bearer token.
	 * Not stored. Without a call, DAEDALUS_KENNEL_ORIGIN / DAEDALUS_KENNEL_TOKEN from the environment are used.
	 */
	UFUNCTION(BlueprintCallable, Category = "Daedalus|Tonic") bool ConfigureSession(const FString& Origin, const FString& Token);
	UFUNCTION(BlueprintCallable, Category = "Daedalus|Tonic") void ClearSession();

	/** Put a harvested plant in: reads its Tonic_Herb_<Name> tag. False when full, steeping, duplicate or not a tonic herb. */
	UFUNCTION(BlueprintCallable, Category = "Daedalus|Tonic") bool DepositHerbActor(AActor* Herb);
	UFUNCTION(BlueprintCallable, Category = "Daedalus|Tonic") bool DepositHerb(const FString& HerbName);
	/** Throw the herbs out and start over (only while nothing is steeped). */
	UFUNCTION(BlueprintCallable, Category = "Daedalus|Tonic") bool EmptyTrough();
	/** Steep what is in the trough: asks Java whether the herbs make a tonic. Herbs stay put on a refusal. */
	UFUNCTION(BlueprintCallable, Category = "Daedalus|Tonic") bool Interact(AActor* Instigator);
	/** One pet drinks: Java scales the tonic for THIS pet, then it is applied once. Needs a steeped trough. */
	UFUNCTION(BlueprintCallable, Category = "Daedalus|Tonic") bool Drink(AActor* Drinker);

	UFUNCTION(BlueprintPure, Category = "Daedalus|Tonic") EDaedalusTroughPhase GetPhase() const;
	UFUNCTION(BlueprintPure, Category = "Daedalus|Tonic") int32 DrinksLeft() const;
	UFUNCTION(BlueprintPure, Category = "Daedalus|Tonic") int32 HerbCount() const { return Trough.HerbCount(); }
	UFUNCTION(BlueprintPure, Category = "Daedalus|Tonic") FString RecipeId() const { return UTF8_TO_TCHAR(Trough.RecipeId().c_str()); }
	UFUNCTION(BlueprintPure, Category = "Daedalus|Tonic") TArray<FString> Herbs() const;

	UPROPERTY(BlueprintAssignable, Category = "Daedalus|Tonic") FDaedalusTonicSteeped OnSteeped;
	UPROPERTY(BlueprintAssignable, Category = "Daedalus|Tonic") FDaedalusTonicDrunk OnDrunk;
	UPROPERTY(BlueprintAssignable, Category = "Daedalus|Tonic") FDaedalusTonicRefused OnRefused;

private:
	using FDone = TFunction<void(int32 Status, bool bConnected, const std::string& Body)>;
	bool Post(const std::string& Json, FDone Done);
	bool HasSession();
	double Now() const;
	std::string Key() const;
	AActor* FindCorso() const;

	daedalus::tonic::Trough Trough;
	// Deliberately not UPROPERTY/config/replicated: credentials are not asset data.
	FString ServerOrigin;
	FString BearerToken;
	uint64 Generation = 0;
	TSharedPtr<IHttpRequest, ESPMode::ThreadSafe> Pending;
	float SinceScan = 0.f;
};

/** Adds a UDaedalusBrewTroughComponent to the placed Brew_Trough actor when play begins. daedalus.tonic.* console commands for tests. */
UCLASS()
class DAEDALUSLINK_API UDaedalusTonicSubsystem : public UWorldSubsystem
{
	GENERATED_BODY()
public:
	virtual void OnWorldBeginPlay(UWorld& InWorld) override;
	/** The trough this subsystem attached (the Interact_Brew volume if the level has one, else the first Brew_Trough actor). */
	UFUNCTION(BlueprintPure, Category = "Daedalus|Tonic") UDaedalusBrewTroughComponent* GetTrough() const { return Trough.Get(); }
	UFUNCTION(BlueprintPure, Category = "Daedalus|Tonic", meta = (WorldContext = "WorldContext"))
	static UDaedalusTonicSubsystem* GetTonics(const UObject* WorldContext);
private:
	TWeakObjectPtr<UDaedalusBrewTroughComponent> Trough;
};