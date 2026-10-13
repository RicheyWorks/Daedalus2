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
 * - daedalus.TacticsRemote 1: once a second each squad's roster (and the events) are POSTed to the Java director
 *   (daedalus.Server + /api/v1/tactics/decide) without blocking; the spec that comes back goes through ApplyOrders.
 *   One request per squad in flight; a slow or missing answer just leaves the local director in charge.
 * daedalus.Tactics 0 turns the local director off. It runs in Play and in the game, never in the editor world.
 */
UCLASS()
class DAEDALUSLINK_API UDaedalusTactics : public UTickableWorldSubsystem
{
	GENERATED_BODY()

public:
	virtual bool DoesSupportWorldType(const EWorldType::Type WorldType) const override;
	virtual void Initialize(FSubsystemCollectionBase& Collection) override;
	virtual void Tick(float DeltaTime) override;
	virtual TStatId GetStatId() const override { RETURN_QUICK_DECLARE_CYCLE_STAT(UDaedalusTactics, STATGROUP_Tickables); }

	/** For Python and Blueprints: the world's tactics. */
	UFUNCTION(BlueprintPure, Category = "Daedalus|Tactics", meta = (WorldContext = "WorldContext"))
	static UDaedalusTactics* GetTactics(const UObject* WorldContext);

	/** Apply a DTO 1 spec. Returns "applied=N unknown=M squad=S", "repeat: tick N" (same tick again, ignored) or
	 * "refused: <why>" (a bad line, or a stale tick older than that squad's last); a refused spec changes nothing. */
	UFUNCTION(BlueprintCallable, Category = "Daedalus|Tactics") FString ApplyOrders(const FString& Spec);
	/** Run the local director for one squad now and apply its orders. Returns the DTO 1 spec it wrote. */
	UFUNCTION(BlueprintCallable, Category = "Daedalus|Tactics") FString DecideNow(const FString& Squad);
	/** The events since the last call, as DTE 1, and clear them. */
	UFUNCTION(BlueprintCallable, Category = "Daedalus|Tactics") FString TakeEvents();
	/** DTR 1: the trusted roster of one squad (ids, kinds, health and max health, positions), for Java to build its
	 * Frame from. Includes this world's session id. */
	UFUNCTION(BlueprintCallable, Category = "Daedalus|Tactics") FString TakeRoster(const FString& Squad);
	/** This world's session id: new each time the world starts (Play or game), so stale Java state can't carry over. */
	UFUNCTION(BlueprintPure, Category = "Daedalus|Tactics") FString SessionId() const { return Session; }
	/** Squads with live foes, comma-separated. */
	UFUNCTION(BlueprintPure, Category = "Daedalus|Tactics") FString Squads() const;
	UFUNCTION(BlueprintPure, Category = "Daedalus|Tactics") FString Stats() const;

	/** A squad member went down: kept for the rest of the session and listed in its roster with health 0, so the
	 * Java director can count casualties (its Frame takes dead units as health 0). */
	void NoteDown(const FString& Squad, const FString& Unit, const FString& Kind, float MaxHealth, const FVector& At);
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
	TMap<FString, int64> LastExternalTick;
	struct FDowned { FString Unit, Kind; float MaxHealth = 0.f; FVector At = FVector::ZeroVector; };
	TMap<FString, TArray<FDowned>> Downed;   // per squad, this session   // per squad: an outside spec older than this is refused (stale fencing)
	FString Session;
	/** Squads with a request to the Java director in flight (one each, so a slow server can't pile them up). */
	TSet<FString> InFlight;
	void AskRemote(const FString& Squad, const FString& Events);
	void RemoteAnswer(const FString& Squad, int32 Code, const FString& Body);
	int32 Asked = 0, Answered = 0, RemoteFailed = 0;
	FString CachedToken;   // from Saved/Daedalus/tactics.token; never logged
	float Next = 1.f;
	int64 TickNo = 0;
	int32 Applied = 0, Refused = 0, Decided = 0, Dropped = 0;
	FString LastError;
};
