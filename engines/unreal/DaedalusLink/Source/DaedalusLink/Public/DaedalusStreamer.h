// SPDX-License-Identifier: MIT

#pragma once

#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "DaedalusStreamer.generated.h"

/**
 * Minecraft's view distance for islands (ADR-062). In Play and in the game, it loads island sublevels as the player
 * comes near and unloads them as the player leaves, so only nearby islands use RAM. The decisions come from
 * DaedalusStreamCore.h, which is tested in core-test.
 *
 * The islands are listed in Saved/Daedalus/islands.json (written by daedalus_islands.py in the editor):
 *     [{"package": "/Game/Claude/ClaudeIsland_Sub", "x": 400000, "y": 0, "z": 5000, "radius": 60000, "always": false}]
 * Only listed sublevels are touched. Each must be a Dynamic (not AlwaysLoaded) streaming level, so it can unload.
 * It runs twice a second. CVars:
 * - daedalus.Stream: 0 turns it off;
 * - daedalus.StreamLoadKm: load distance, default 1.5;
 * - daedalus.StreamUnloadKm: unload distance, default 2.5.
 */
UCLASS()
class DAEDALUSLINK_API UDaedalusStreamer : public UTickableWorldSubsystem
{
	GENERATED_BODY()

public:
	virtual bool DoesSupportWorldType(const EWorldType::Type WorldType) const override;
	virtual void Initialize(FSubsystemCollectionBase& Collection) override;
	virtual void Tick(float DeltaTime) override;
	virtual TStatId GetStatId() const override { RETURN_QUICK_DECLARE_CYCLE_STAT(UDaedalusStreamer, STATGROUP_Tickables); }

	/** Re-read Saved/Daedalus/islands.json. Returns how many islands are listed. */
	UFUNCTION(BlueprintCallable, Category = "Daedalus|Streaming") int32 Reload();
	/** "listed=N loaded=M loads=L unloads=U last=<step>". */
	UFUNCTION(BlueprintPure, Category = "Daedalus|Streaming") FString Stats() const;
	UFUNCTION(BlueprintPure, Category = "Daedalus|Streaming", meta = (WorldContext = "WorldContext"))
	static UDaedalusStreamer* GetStreamer(const UObject* WorldContext);

private:
	struct FIsle { FString Package; FVector Centre; double Radius = 0; bool bAlways = false; };
	TArray<FIsle> Isles;
	float Next = 0.f;
	int32 Loads = 0, Unloads = 0;
	FString Last;
};
