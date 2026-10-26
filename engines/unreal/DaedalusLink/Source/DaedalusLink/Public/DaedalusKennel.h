// SPDX-License-Identifier: MIT

#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "Subsystems/WorldSubsystem.h"
#include "DaedalusKennelPetCore.h"
#include "DaedalusKennel.generated.h"

/**
 * Kennel Isle pets in Unreal (contest G102, docs/islands/KENNEL-KEEPERS-LEDGER.md).
 * Every rule lives in the engine-free headers: DaedalusKennelCore.h (G84 twin of the Java G37 bond, G61 drills,
 * G65 growth, parity-tested) and DaedalusKennelPetCore.h (one pet's day, seeded rolls, tags; core-test/kennel_pet_core_test.cpp).
 * This file only
 *   - gives each placed pet (tag AMF_Companion or AMF_Wild) a UDaedalusKennelPet at BeginPlay, seeded from Bond_NN / CareDays_NN tags,
 *   - forwards care, end-of-day and drills to the core and broadcasts what changed,
 *   - adds daedalus.kennel.* console commands for PIE checks, like daedalus.tonic.*.
 * No network, no credentials, no saved state yet (save/load is a later UNREAL-QUEUE row).
 */

UENUM(BlueprintType)
enum class EDaedalusKennelDrill : uint8 { Obeyed, Failed, TierLocked, StageLocked, Unknown };

DECLARE_DYNAMIC_MULTICAST_DELEGATE_FiveParams(FDaedalusKennelDayEnded, int32, Day, int32, Bond, int32, CareDays, const FString&, Tier, const FString&, Stage);
DECLARE_DYNAMIC_MULTICAST_DELEGATE_TwoParams(FDaedalusKennelTierChanged, const FString&, OldTier, const FString&, NewTier);
DECLARE_DYNAMIC_MULTICAST_DELEGATE_TwoParams(FDaedalusKennelStageChanged, const FString&, OldStage, const FString&, NewStage);
DECLARE_DYNAMIC_MULTICAST_DELEGATE_ThreeParams(FDaedalusKennelDrilled, const FString&, Command, EDaedalusKennelDrill, Outcome, int32, SuccessPct);

/** One pet's bond, care-days and today's care. Read-only views for the pet panel; changes go through Care/EndDay/Drill. */
UCLASS(ClassGroup = (Daedalus), meta = (BlueprintSpawnableComponent))
class DAEDALUSLINK_API UDaedalusKennelPet : public UActorComponent
{
	GENERATED_BODY()
public:
	UDaedalusKennelPet();

	/** Seed from the owner's tags (Bond_NN, CareDays_NN) and its name as the roll key. Called once by For(). */
	UFUNCTION(BlueprintCallable, Category = "Daedalus|Kennel") void SeedFromOwner();

	/** "feed", "water", "tonic" (once a day each) or "fetch" with Catches. False when refused (repeat, unknown, cap). */
	UFUNCTION(BlueprintCallable, Category = "Daedalus|Kennel") bool Care(const FString& What, int32 Catches = 1);
	/** Close the day: growth (seeded spurt roll), bond step, fresh day. Broadcasts OnDayEnded and any tier/stage change. */
	UFUNCTION(BlueprintCallable, Category = "Daedalus|Kennel") void EndDay();
	/** A drill: come, stay, fetch, guard, rescue. Stage gate, tier gate, then a seeded roll. */
	UFUNCTION(BlueprintCallable, Category = "Daedalus|Kennel") EDaedalusKennelDrill Drill(const FString& Command);

	UFUNCTION(BlueprintPure, Category = "Daedalus|Kennel") int32 GetBond() const { return Pet.Bond; }
	UFUNCTION(BlueprintPure, Category = "Daedalus|Kennel") int32 GetCareDays() const { return Pet.CareDays; }
	UFUNCTION(BlueprintPure, Category = "Daedalus|Kennel") int32 GetDay() const { return Pet.Day; }
	UFUNCTION(BlueprintPure, Category = "Daedalus|Kennel") FString GetTier() const;
	UFUNCTION(BlueprintPure, Category = "Daedalus|Kennel") FString GetStage() const;
	/** True when tier and stage both allow the command (the drill can roll). */
	UFUNCTION(BlueprintPure, Category = "Daedalus|Kennel") bool CanDrill(const FString& Command) const;
	/** G61 success percent for the command at the current bond (0 for an unknown command). */
	UFUNCTION(BlueprintPure, Category = "Daedalus|Kennel") int32 DrillSuccessPct(const FString& Command) const;
	UFUNCTION(BlueprintPure, Category = "Daedalus|Kennel") FString StatusLine() const;

	UPROPERTY(BlueprintAssignable, Category = "Daedalus|Kennel") FDaedalusKennelDayEnded OnDayEnded;
	UPROPERTY(BlueprintAssignable, Category = "Daedalus|Kennel") FDaedalusKennelTierChanged OnTierChanged;
	UPROPERTY(BlueprintAssignable, Category = "Daedalus|Kennel") FDaedalusKennelStageChanged OnStageChanged;
	UPROPERTY(BlueprintAssignable, Category = "Daedalus|Kennel") FDaedalusKennelDrilled OnDrilled;

	/** Find (or add and seed) the component on an actor. */
	static UDaedalusKennelPet* For(AActor* Actor);
	const daedalus::kennel::FPet& Core() const { return Pet; }

private:
	daedalus::kennel::FPet Pet;
};

/** Gives every tagged pet a UDaedalusKennelPet when play begins and ends the kennel day for all of them. daedalus.kennel.* console. */
UCLASS()
class DAEDALUSLINK_API UDaedalusKennelSubsystem : public UWorldSubsystem
{
	GENERATED_BODY()
public:
	virtual void OnWorldBeginPlay(UWorld& InWorld) override;

	/** Pets this subsystem knows, companions first. */
	UFUNCTION(BlueprintPure, Category = "Daedalus|Kennel") TArray<UDaedalusKennelPet*> GetPets() const;
	/** First pet whose actor name contains Name (case-insensitive); empty Name gives the first pet. */
	UFUNCTION(BlueprintPure, Category = "Daedalus|Kennel") UDaedalusKennelPet* FindPet(const FString& Name) const;
	/** End the day for every pet. Returns how many pets stepped. */
	UFUNCTION(BlueprintCallable, Category = "Daedalus|Kennel") int32 EndDayAll();
	/** Add a pet that was spawned after BeginPlay. */
	UFUNCTION(BlueprintCallable, Category = "Daedalus|Kennel") UDaedalusKennelPet* Adopt(AActor* Actor);

	UFUNCTION(BlueprintPure, Category = "Daedalus|Kennel", meta = (WorldContext = "WorldContext"))
	static UDaedalusKennelSubsystem* GetKennel(const UObject* WorldContext);

private:
	TArray<TWeakObjectPtr<UDaedalusKennelPet>> Pets;
};
