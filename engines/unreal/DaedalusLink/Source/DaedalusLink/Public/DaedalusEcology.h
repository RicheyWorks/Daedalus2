// SPDX-License-Identifier: MIT

#pragma once

#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "DaedalusEcology.generated.h"

UENUM(BlueprintType)
enum class EDaedalusEcologyEvent : uint8 { Ignite, Blast, Douse };

/**
 * Reactive Battlefield Ecology in Unreal (ADR-061). Reads the DBE 1 snapshot Java writes and answers cover,
 * concealment and fire questions for any world spot; queues IGNITE/BLAST/DOUSE events and writes them as DBE-E 1
 * for Java to apply. All parsing/writing lives in DaedalusEcologyCore.h, which is tested in core-test.
 * Default files: Saved/Daedalus/ecology.dbe (in) and Saved/Daedalus/ecology_events.dbe (out).
 */
UCLASS()
class DAEDALUSLINK_API UDaedalusEcology : public UWorldSubsystem
{
	GENERATED_BODY()

public:
	virtual ~UDaedalusEcology() override;

	/** Read a DBE 1 snapshot file (empty = Saved/Daedalus/ecology.dbe). False keeps the old field; see LastError. */
	UFUNCTION(BlueprintCallable, Category = "Daedalus|Ecology") bool LoadSnapshot(const FString& Path);
	/** Same, from text already in memory. */
	UFUNCTION(BlueprintCallable, Category = "Daedalus|Ecology") bool LoadSnapshotText(const FString& Spec);

	UFUNCTION(BlueprintPure, Category = "Daedalus|Ecology") bool HasField() const { return Field != nullptr; }
	/** 0..1 cover at a world spot; 0 when no field is loaded. */
	UFUNCTION(BlueprintPure, Category = "Daedalus|Ecology") float CoverAt(const FVector& Where) const;
	UFUNCTION(BlueprintPure, Category = "Daedalus|Ecology") float ConcealmentAt(const FVector& Where) const;
	UFUNCTION(BlueprintPure, Category = "Daedalus|Ecology") bool BurningAt(const FVector& Where) const;

	/** Queue an event for Java. False when the queue is full (256) or the radius is out of range. */
	UFUNCTION(BlueprintCallable, Category = "Daedalus|Ecology")
	bool QueueEvent(EDaedalusEcologyEvent Kind, const FVector& Where, float RadiusCm);
	/** Write queued events as DBE-E 1 (empty = Saved/Daedalus/ecology_events.dbe) and clear the queue on success. */
	UFUNCTION(BlueprintCallable, Category = "Daedalus|Ecology") bool FlushEvents(const FString& Path);

	UFUNCTION(BlueprintPure, Category = "Daedalus|Ecology") FString LastError() const { return Error; }
	/** "field=WxH tick=T queued=N". */
	UFUNCTION(BlueprintPure, Category = "Daedalus|Ecology") FString Stats() const;
	UFUNCTION(BlueprintPure, Category = "Daedalus|Ecology", meta = (WorldContext = "WorldContext"))
	static UDaedalusEcology* GetEcology(const UObject* WorldContext);

private:
	struct FImpl;
	FImpl* Field = nullptr;
	struct FQueued { EDaedalusEcologyEvent Kind; FVector Where; float RadiusCm; };
	TArray<FQueued> Queue;
	FString Error;
};
