// SPDX-License-Identifier: MIT

#pragma once

#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "DaedalusNav.generated.h"

/**
 * Ground routes for foes (ADR-044), ported from the maze engine's AStarSolver (daedalus-core,
 * com.daedalus.solver.solvers.AStarSolver): best-first search on f = g + h over cell-id-indexed arrays (gScore,
 * parent, closed), with per-cell weights as in WeightedMazeGrid.
 *
 * The maze here is the island itself, read on demand: the world is cut into 100 cm cells, and a cell's floor is
 * found by a trace down the first time a search touches it, then cached. A step is walkable if it climbs no more
 * than StepUp and drops no more than StepDown; anything else is a wall (a cliff, a block) or a ledge. Cells next to
 * a drop cost more, so foes keep off the lips of the islands. Moves are 8-connected without cutting corners, and
 * the octile heuristic stays admissible because every weight is at least 1. A search has a budget of expansions
 * (SolverBudgetExceededException's idea); over budget, or no route, it reports failure and the foe waits.
 */
UCLASS()
class DAEDALUSLINK_API UDaedalusNav : public UWorldSubsystem
{
	GENERATED_BODY()

public:
	static constexpr float Cell = 100.f;
	static constexpr float StepUp = 70.f;
	static constexpr float StepDown = 220.f;
	static constexpr int32 Radius = 40;          // cells each way from the middle of the search
	static constexpr int32 Budget = 4000;        // expansions per search

	/** Route over the ground from one point to another, as cell-centre waypoints at floor height. */
	bool FindPath(const FVector& From, const FVector& To, TArray<FVector>& OutPath);

	/** The floor under a point near a reference height, or false if there is none (a ledge). */
	bool FloorAt(int32 CX, int32 CY, float RefZ, float& OutZ);

	// The record (the harness reads these with Stats()).
	UFUNCTION(BlueprintCallable, Category = "Daedalus") FString Stats() const;
	UFUNCTION(BlueprintCallable, Category = "Daedalus") void ResetCache();
	/** For the harness: the floor trace for one point, uncached, with what it hit and in which world. */
	FString TraceReport(const FVector& At, float RefZ);

	int32 Searches = 0;
	int32 Found = 0;
	int32 Expanded = 0;
	int32 Samples = 0;
	int32 LastExpanded = 0;
	int32 LastLength = 0;

private:
	// Floors by (cell x, cell y, height band): islands have tiers, so one column can hold several floors.
	TMap<FIntVector, float> Floors;
};
