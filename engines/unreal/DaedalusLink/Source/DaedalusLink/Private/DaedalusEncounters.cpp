// SPDX-License-Identifier: MIT

#include "DaedalusEncounters.h"
#include "DaedalusBestiaryCore.h"

#include "DaedalusHero.h"
#include "DaedalusTarget.h"
#include "Engine/StaticMeshActor.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/Pawn.h"
#include "HAL/IConsoleManager.h"
#include "Kismet/GameplayStatics.h"

static TAutoConsoleVariable<int32> CVarEncounters(TEXT("daedalus.Encounters"), 1,
	TEXT("1: packs of foes appear on the islands (ADR-046). 0: none."));
static TAutoConsoleVariable<int32> CVarMaxFoes(TEXT("daedalus.MaxFoes"), 12,
	TEXT("Most foes the encounter director keeps alive at once."));

namespace
{
	// Pack makeup by kind (index into the ADR-037 rule table): slime, shardback, wisp, knight.
	const float KindWeight[] = {40.f, 25.f, 25.f, 10.f};

	FCollisionQueryParams Simple(const AActor* Ignore)
	{
		return FCollisionQueryParams(SCENE_QUERY_STAT(DaedalusEncounter), false, Ignore);
	}
}

bool UDaedalusEncounters::DoesSupportWorldType(const EWorldType::Type WorldType) const
{
	return WorldType == EWorldType::Game || WorldType == EWorldType::PIE;
}

int32 UDaedalusEncounters::Alive() const
{
	int32 N = 0;
	for (const TArray<TWeakObjectPtr<ADaedalusTarget>>& Pack : Live)
	{
		for (const TWeakObjectPtr<ADaedalusTarget>& F : Pack)
		{
			if (F.IsValid() && F->Health > 0.f) ++N;
		}
	}
	return N;
}

void UDaedalusEncounters::Tick(float DeltaTime)
{
	UWorld* W = GetWorld();
	if (!W || !W->HasBegunPlay() || CVarEncounters.GetValueOnGameThread() == 0) return;

	// Wiped-out packs are cleared.
	for (int32 i = Live.Num() - 1; i >= 0; --i)
	{
		bool bAny = false;
		for (const TWeakObjectPtr<ADaedalusTarget>& F : Live[i])
		{
			if (F.IsValid() && F->Health > 0.f) { bAny = true; break; }
		}
		if (!bAny)
		{
			++Cleared;
			Live.RemoveAtSwap(i);
		}
	}

	Next -= DeltaTime;
	if (Next > 0.f) return;
	Next = 5.f;
	if (Alive() + 2 <= CVarMaxFoes.GetValueOnGameThread())
	{
		SpawnPack();
	}
}

bool UDaedalusEncounters::FindGround(const APawn* Player, FVector& Out)
{
	UWorld* W = GetWorld();
	if (!bIslandsKnown)
	{
		bIslandsKnown = true;
		for (TActorIterator<AStaticMeshActor> It(W); It; ++It)
		{
			FVector Origin, Extent;
			It->GetActorBounds(false, Origin, Extent);
			if (Extent.X >= 200.f && Extent.Y >= 200.f) Islands.Add(*It);
		}
	}
	const FVector P = Player->GetActorLocation();
	TArray<AActor*> Near;
	for (const TWeakObjectPtr<AActor>& A : Islands)
	{
		if (!A.IsValid()) continue;
		// Distance to the island's edge, not its pivot: on a wide island the pivot can be far while you stand on it.
		FVector O, E;
		A->GetActorBounds(false, O, E);
		const float Dx = FMath::Max(0.f, FMath::Abs(P.X - O.X) - E.X);
		const float Dy = FMath::Max(0.f, FMath::Abs(P.Y - O.Y) - E.Y);
		if (FMath::Sqrt(Dx * Dx + Dy * Dy) < 7500.f) Near.Add(A.Get());
	}
	if (Near.Num() == 0) return false;

	const FCollisionObjectQueryParams Statics(ECC_WorldStatic);
	for (int32 Attempt = 0; Attempt < 16; ++Attempt)
	{
		++Tries;
		AActor* Isle = Near[Rng.RandRange(0, Near.Num() - 1)];
		FVector Origin, Extent;
		Isle->GetActorBounds(false, Origin, Extent);
		const FVector Probe(Origin.X + Rng.FRandRange(-Extent.X + 100.f, Extent.X - 100.f),
		                    Origin.Y + Rng.FRandRange(-Extent.Y + 100.f, Extent.Y - 100.f), Origin.Z);
		const float Dist = FVector::Dist2D(Probe, P);
		FHitResult Hit;
		if (Dist < 1200.f
			|| !W->LineTraceSingleByObjectType(Hit, Probe + FVector(0.f, 0.f, Extent.Z + 300.f), Probe - FVector(0.f, 0.f, Extent.Z + 100.f), Statics, Simple(Player))
			|| Hit.ImpactNormal.Z < 0.85f)
		{
			++Rejected;
			continue;
		}
		const FVector Ground = Hit.ImpactPoint;
		// Room for a pack: flat ground all around.
		bool bFlat = true;
		for (int32 k = 0; k < 4 && bFlat; ++k)
		{
			const FVector Side = Ground + FRotator(0.f, 90.f * k, 0.f).Vector() * 160.f;
			FHitResult S;
			bFlat = W->LineTraceSingleByObjectType(S, Side + FVector(0.f, 0.f, 200.f), Side - FVector(0.f, 0.f, 200.f), Statics, Simple(Player))
				&& FMath::Abs(S.ImpactPoint.Z - Ground.Z) < 80.f;
		}
		if (!bFlat)
		{
			++Rejected;
			continue;
		}
		// Out of sight, unless far: foes shouldn't pop in where the player is looking.
		FHitResult Sight;
		const bool bHidden = W->LineTraceSingleByObjectType(Sight, P + FVector(0.f, 0.f, 60.f), Ground + FVector(0.f, 0.f, 120.f), Statics, Simple(Player));
		if (!bHidden && Dist < 3000.f)
		{
			++Rejected;
			continue;
		}
		Out = Ground;
		return true;
	}
	return false;
}

static FString RealmOfPlayer(UWorld* W)
{
	for (TActorIterator<ADaedalusHero> It(W); It; ++It) return It->RealmNow();
	return TEXT("WORLD-ZERO");
}

ADaedalusTarget* UDaedalusEncounters::SpawnFoe(const FVector& At, int32 RuleIndex)
{
	UWorld* W = GetWorld();
	if (!W) return nullptr;
	// In a 3D realm the pack comes from that realm's bestiary (DaedalusBestiaryCore, Sol's creatures); World Zero
	// keeps the server's foe rules.
	const daedalus::bestiary::Foe* B = daedalus::bestiary::Pick(TCHAR_TO_UTF8(*RealmOfPlayer(W)), Rng.FRand());
	FDaedalusFoeRule Rule;
	if (B)
	{
		Rule.Kind = UTF8_TO_TCHAR(B->Kind.c_str()); Rule.Title = UTF8_TO_TCHAR(B->Title.c_str());
		Rule.Life = B->Life; Rule.Power = B->Power; Rule.Exp = B->Exp;
	}
	else
	{
		const TArray<FDaedalusFoeRule>& R = ADaedalusHero::FoeRules();
		if (R.Num() == 0) return nullptr;
		Rule = R[RuleIndex % R.Num()];
	}
	const FTransform Where(FRotator(0.f, Rng.FRandRange(0.f, 360.f), 0.f), At + FVector(0.f, 0.f, 60.f));
	// AlwaysSpawn: the spot was traced to the ground already, and a deferred foe has no collider yet, so the
	// engine's adjust pass only logs "FindTeleportSpot ... root component not being a collider" (28x a Play, 2026-10-13).
	ADaedalusTarget* T = W->SpawnActorDeferred<ADaedalusTarget>(ADaedalusTarget::StaticClass(), Where, nullptr, nullptr,
		ESpawnActorCollisionHandlingMethod::AlwaysSpawn);
	if (!T) return nullptr;
	T->Kind = Rule.Kind;
	T->Title = Rule.Title;
	if (B) T->SkeletalArt = UTF8_TO_TCHAR(B->ArtId.c_str());
	T->ExpValue = Rule.Exp;
	T->Health = Rule.Life * 30.f;
	T->Power = Rule.Power;
	UGameplayStatics::FinishSpawningActor(T, Where);
	return T;
}

int32 UDaedalusEncounters::SpawnPack()
{
	UWorld* W = GetWorld();
	APawn* Player = W ? UGameplayStatics::GetPlayerPawn(W, 0) : nullptr;
	if (!Player) return 0;
	FVector Ground;
	if (!FindGround(Player, Ground)) return 0;

	const int32 Size = Rng.RandRange(2, 4);
	float Total = 0.f;
	for (const float Wt : KindWeight) Total += Wt;
	TArray<TWeakObjectPtr<ADaedalusTarget>> Pack;
	const FCollisionObjectQueryParams Statics(ECC_WorldStatic);
	for (int32 i = 0; i < Size; ++i)
	{
		float Roll = Rng.FRandRange(0.f, Total);
		int32 Kind = 0;
		while (Kind < 3 && Roll > KindWeight[Kind]) { Roll -= KindWeight[Kind]; ++Kind; }
		// Spread the pack around the spot, each on its own ground.
		FVector At = Ground + FRotator(0.f, 360.f * i / Size, 0.f).Vector() * (i == 0 ? 0.f : 200.f);
		FHitResult Hit;
		if (W->LineTraceSingleByObjectType(Hit, At + FVector(0.f, 0.f, 200.f), At - FVector(0.f, 0.f, 300.f), Statics, Simple(Player)))
		{
			At = Hit.ImpactPoint;
		}
		if (ADaedalusTarget* T = SpawnFoe(At, Kind))
		{
			T->Squad = FString::Printf(TEXT("pack-%d"), Packs + 1);   // ADR-060: a pack fights as one squad
			T->UnitId = FString::Printf(TEXT("pack-%d-%d"), Packs + 1, i + 1);
			Pack.Add(T);
			++Spawned;
		}
	}
	if (Pack.Num() > 0)
	{
		Live.Add(Pack);
		++Packs;
	}
	return Pack.Num();
}

FString UDaedalusEncounters::Stats() const
{
	return FString::Printf(TEXT("packs=%d spawned=%d alive=%d cleared=%d tries=%d rejected=%d"), Packs, Spawned, Alive(), Cleared, Tries, Rejected);
}
