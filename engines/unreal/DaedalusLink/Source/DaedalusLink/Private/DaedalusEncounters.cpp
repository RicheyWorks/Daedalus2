// SPDX-License-Identifier: MIT

#include "DaedalusEncounters.h"

#include "DaedalusHero.h"
#include "DaedalusTarget.h"
#include "Engine/World.h"
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
	const FVector P = Player->GetActorLocation();
	const FCollisionObjectQueryParams Statics(ECC_WorldStatic);
	for (int32 Attempt = 0; Attempt < 16; ++Attempt)
	{
		++Tries;
		const float Yaw = Rng.FRandRange(0.f, 360.f);
		const float Dist = Rng.FRandRange(2500.f, 6000.f);
		const FVector Probe = P + FRotator(0.f, Yaw, 0.f).Vector() * Dist;
		FHitResult Hit;
		if (!W->LineTraceSingleByObjectType(Hit, Probe + FVector(0.f, 0.f, 2500.f), Probe - FVector(0.f, 0.f, 4000.f), Statics, Simple(Player))
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
			const FVector Side = Ground + FRotator(0.f, 90.f * k, 0.f).Vector() * 220.f;
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
		if (!bHidden && Dist < 4500.f)
		{
			++Rejected;
			continue;
		}
		Out = Ground;
		return true;
	}
	return false;
}

ADaedalusTarget* UDaedalusEncounters::SpawnFoe(const FVector& At, int32 RuleIndex)
{
	UWorld* W = GetWorld();
	const TArray<FDaedalusFoeRule>& R = ADaedalusHero::FoeRules();
	if (!W || R.Num() == 0) return nullptr;
	const FDaedalusFoeRule& Rule = R[RuleIndex % R.Num()];
	const FTransform Where(FRotator(0.f, Rng.FRandRange(0.f, 360.f), 0.f), At + FVector(0.f, 0.f, 60.f));
	ADaedalusTarget* T = W->SpawnActorDeferred<ADaedalusTarget>(ADaedalusTarget::StaticClass(), Where, nullptr, nullptr,
		ESpawnActorCollisionHandlingMethod::AdjustIfPossibleButAlwaysSpawn);
	if (!T) return nullptr;
	T->Kind = Rule.Kind;
	T->Title = Rule.Title;
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
