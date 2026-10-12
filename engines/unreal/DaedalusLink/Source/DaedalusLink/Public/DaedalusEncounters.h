// SPDX-License-Identifier: MIT

#pragma once

#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "DaedalusEncounters.generated.h"

class ADaedalusTarget;

/**
 * Encounters (ADR-046): packs of foes appear on the islands by themselves, the way Halo's encounters wait around
 * the next corner. Every few seconds, while fewer than daedalus.MaxFoes are alive, the director looks for flat
 * ground 25 to 60 m from the player that the player can't see (or that is far), and puts a pack of 2 to 4 there,
 * mixed by weight (slimes common, knights rare). A pack that is wiped out counts as cleared and the ground fills
 * again later. Runs in Play and in the game, never in the editor world. daedalus.Encounters 0 turns it off.
 */
UCLASS()
class DAEDALUSLINK_API UDaedalusEncounters : public UTickableWorldSubsystem
{
	GENERATED_BODY()

public:
	virtual bool DoesSupportWorldType(const EWorldType::Type WorldType) const override;
	virtual void Tick(float DeltaTime) override;
	virtual TStatId GetStatId() const override { RETURN_QUICK_DECLARE_CYCLE_STAT(UDaedalusEncounters, STATGROUP_Tickables); }

	/** Put a pack on flat hidden ground near the player now, if there is room. Returns how many foes. */
	int32 SpawnPack();
	FString Stats() const;

	int32 Packs = 0;
	int32 Spawned = 0;
	int32 Cleared = 0;
	int32 Tries = 0;
	int32 Rejected = 0;

private:
	bool FindGround(const APawn* Player, FVector& Out);
	ADaedalusTarget* SpawnFoe(const FVector& At, int32 RuleIndex);
	int32 Alive() const;

	TArray<TArray<TWeakObjectPtr<ADaedalusTarget>>> Live;
	float Next = 4.f;
	FRandomStream Rng = FRandomStream(4207);
};
