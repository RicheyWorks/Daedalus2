// SPDX-License-Identifier: MIT

#pragma once

#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "DaedalusTactics.generated.h"

class ADaedalusTarget;

/**
 * Squad tactics (ADR-060). Foes that share a Squad take orders together; the orders are DTO 1 specs
 * (DaedalusTacticsCore.h).
 * - Java's combat director (team-codex's Living World) sends a spec through ApplyOrders, from the bridge or a socket
 *   later. That squad then follows Java for ExternalHold seconds.
 * - Otherwise the local director decides each squad's orders once a second. It is deterministic and explainable:
 *   one attacks, two flank, the badly hurt retreat.
 * - Movement, attacks and hits stay in ADaedalusTarget every frame. Nothing here waits on Java.
 * - Events (HIT, DOWN, SEEN, PLAYER) are kept as DTE 1 lines for Java to collect with TakeEvents.
 * daedalus.Tactics 0 turns the local director off. It runs in Play and in the game, never in the editor world.
 */
UCLASS()
class DAEDALUSLINK_API UDaedalusTactics : public UTickableWorldSubsystem
{
	GENERATED_BODY()

public:
	virtual bool DoesSupportWorldType(const EWorldType::Type WorldType) const override;
	virtual void Tick(float DeltaTime) override;
	virtual TStatId GetStatId() const override { RETURN_QUICK_DECLARE_CYCLE_STAT(UDaedalusTactics, STATGROUP_Tickables); }

	/** For Python and Blueprints: the world's tactics. */
	UFUNCTION(BlueprintPure, Category = "Daedalus|Tactics", meta = (WorldContext = "WorldContext"))
	static UDaedalusTactics* GetTactics(const UObject* WorldContext);

	/** Apply a DTO 1 spec. Returns "applied=N unknown=M squad=S" or "refused: <line N: why>"; a bad spec changes nothing. */
	UFUNCTION(BlueprintCallable, Category = "Daedalus|Tactics") FString ApplyOrders(const FString& Spec);
	/** Run the local director for one squad now and apply its orders. Returns the DTO 1 spec it wrote. */
	UFUNCTION(BlueprintCallable, Category = "Daedalus|Tactics") FString DecideNow(const FString& Squad);
	/** The events since the last call, as DTE 1, and clear them. */
	UFUNCTION(BlueprintCallable, Category = "Daedalus|Tactics") FString TakeEvents();
	/** Squads with live foes, comma-separated. */
	UFUNCTION(BlueprintPure, Category = "Daedalus|Tactics") FString Squads() const;
	UFUNCTION(BlueprintPure, Category = "Daedalus|Tactics") FString Stats() const;

	/** A foe reports an event (TakeDamage calls this). */
	void Note(const FString& Kind, const FString& Unit, const FVector& At, float Value);

	/** Seconds a squad follows an outside (Java) spec before the local director takes it back. */
	float ExternalHold = 3.f;
	/** Seconds each order lasts if not renewed (the director renews once a second). */
	float OrderSeconds = 2.5f;

private:
	TArray<ADaedalusTarget*> Members(const FString& Squad) const;
	FString Apply(const FString& Spec, bool bLocal);

	struct FNote { FString Kind, Unit; FVector At; float Value; };
	TArray<FNote> Outbox;
	TMap<FString, double> ExternalUntil;
	float Next = 1.f;
	int64 TickNo = 0;
	int32 Applied = 0, Refused = 0, Decided = 0, Dropped = 0;
	FString LastError;
};
