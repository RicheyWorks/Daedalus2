// SPDX-License-Identifier: MIT

#include "DaedalusHomestead.h"

#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/Pawn.h"
#include "Kismet/GameplayStatics.h"

// ---------------- Thirst ----------------
UDaedalusThirstComponent::UDaedalusThirstComponent() { PrimaryComponentTick.bCanEverTick = true; }

UDaedalusThirstComponent* UDaedalusThirstComponent::For(AActor* Actor)
{
	if (!Actor) return nullptr;
	if (UDaedalusThirstComponent* C = Actor->FindComponentByClass<UDaedalusThirstComponent>()) return C;
	UDaedalusThirstComponent* C = NewObject<UDaedalusThirstComponent>(Actor, TEXT("DaedalusThirst"));
	C->RegisterComponent();
	return C;
}

void UDaedalusThirstComponent::TickComponent(float Dt, ELevelTick TickType, FActorComponentTickFunction* Fn)
{
	Super::TickComponent(Dt, TickType, Fn);
	Thirst = FMath::Max(0.f, Thirst - DrainPerMinute * (bSick ? 2.f : 1.f) * Dt / 60.f);
	if (Thirst <= 0.f) Health = FMath::Max(0.f, Health - HealthDrainPerSecondWhenDry * Dt);
	if (FMath::Abs(Thirst - LastBroadcast) >= 1.f || Thirst <= 0.f)
	{
		LastBroadcast = Thirst;
		OnThirstChanged.Broadcast(Thirst, Health);
	}
}

float UDaedalusThirstComponent::Drink(const FString& Quality)
{
	if (Quality == TEXT("clean")) { Thirst += 30.f; bSick = false; }
	else if (Quality == TEXT("raw")) { Thirst += 20.f; if (FMath::FRand() < 0.25f) bSick = true; }
	else if (Quality == TEXT("salt")) { Thirst -= 10.f; }
	Thirst = FMath::Clamp(Thirst, 0.f, ThirstMax);
	OnThirstChanged.Broadcast(Thirst, Health);
	UE_LOG(LogTemp, Log, TEXT("Daedalus thirst: drank %s -> %.0f"), *Quality, Thirst);
	return Thirst;
}

// ---------------- Water source ----------------
ADaedalusWaterSource::ADaedalusWaterSource()
{
	PrimaryActorTick.bCanEverTick = true;
	PrimaryActorTick.TickInterval = 0.5f;
	RootComponent = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
	Tags.Add(TEXT("YTM_Water"));
}

bool ADaedalusWaterSource::Drink(AActor* Drinker)
{
	UDaedalusThirstComponent* T = UDaedalusThirstComponent::For(Drinker);
	if (!T || Cooldown > 0.f) return false;
	T->Drink(bTreats ? FString(TEXT("clean")) : Quality);
	Cooldown = 2.f;
	return true;
}

void ADaedalusWaterSource::Tick(float Dt)
{
	Super::Tick(Dt);
	Cooldown = FMath::Max(0.f, Cooldown - Dt);
	if (!bAutoSip) return;
	APawn* P = UGameplayStatics::GetPlayerPawn(this, 0);
	if (!P || FVector::Dist(P->GetActorLocation(), GetActorLocation()) > Reach) return;
	UDaedalusThirstComponent* T = UDaedalusThirstComponent::For(P);
	if (T && T->Thirst < T->ThirstMax - 10.f) Drink(P);
}

// ---------------- Chord Brewing ----------------
namespace
{
	const TCHAR* GHerbs[12] = { TEXT("Doleaf"), TEXT("Sharpcress"), TEXT("Rebell"), TEXT("Flatfern"), TEXT("Mimint"), TEXT("Fasage"),
		TEXT("Hushmoss"), TEXT("Solthorn"), TEXT("Gloryroot"), TEXT("Lavine"), TEXT("Dronebloom"), TEXT("Tisquill") };
	const TCHAR* GStats[12] = { TEXT("health"), TEXT("hunger"), TEXT("stamina"), TEXT("thirst"), TEXT("warmth"), TEXT("luck"),
		TEXT("calm"), TEXT("harvest"), TEXT("craft"), TEXT("speed"), TEXT("sight"), TEXT("pet_bond") };
	struct FChord { TArray<int32> Iv; const TCHAR* Name; const TCHAR* Tonic; const TCHAR* Effect; };
	const TArray<FChord>& Chords()
	{
		static TArray<FChord> C = {
			{ {0,4,7}, TEXT("Major"), TEXT("Major"), TEXT("regen_health") }, { {0,3,7}, TEXT("Minor"), TEXT("Minor"), TEXT("restore_hunger") },
			{ {0,5,7}, TEXT("Sus"), TEXT("Sus"), TEXT("stamina_boost") },   { {0,3,6}, TEXT("Dim"), TEXT("Dim"), TEXT("night_vision") },
			{ {0,4,8}, TEXT("Aug"), TEXT("Aug"), TEXT("haste") },           { {0,4,7,10}, TEXT("Seventh"), TEXT("Seventh"), TEXT("purify_water") },
			{ {0,7}, TEXT("Power"), TEXT("Sus"), TEXT("strength") },        { {0,4,7,11}, TEXT("Major"), TEXT("Major"), TEXT("regen_health") } };
		return C;
	}
	int32 NoteOf(const FString& H) { for (int32 i = 0; i < 12; ++i) if (H.Equals(GHerbs[i], ESearchCase::IgnoreCase)) return i; return -1; }
}

ADaedalusBrewBench::ADaedalusBrewBench()
{
	RootComponent = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
	Tags.Add(TEXT("YTM_BrewBench"));
}

FDaedalusBrewResult ADaedalusBrewBench::BrewStatic(const TArray<FString>& Herbs, const TArray<int32>& Stages)
{
	FDaedalusBrewResult R;
	if (Herbs.Num() < 2 || Herbs.Num() > 4) { R.Chord = TEXT("Invalid"); return R; }
	TSet<int32> Set; float StageSum = 0.f;
	for (int32 i = 0; i < Herbs.Num(); ++i)
	{
		const int32 N = NoteOf(Herbs[i]);
		if (N < 0) { R.Chord = TEXT("Invalid"); return R; }
		Set.Add(N); StageSum += Stages.IsValidIndex(i) ? Stages[i] : 1;
	}
	TArray<int32> Pcs = Set.Array(); Pcs.Sort(); R.Notes = Pcs;
	R.Tier = FMath::Clamp(FMath::RoundToInt(StageSum / Herbs.Num()), 1, 4);
	for (int32 Root : Pcs)
	{
		TArray<int32> Iv; for (int32 P : Pcs) Iv.Add((P - Root + 12) % 12); Iv.Sort();
		for (const FChord& C : Chords())
		{
			if (Iv == C.Iv)
			{
				R.Chord = FString(GHerbs[Root]) + TEXT(" ") + C.Name;
				R.Tonic = FString::Printf(TEXT("Item_YTM_Tonic_%s_T%d"), C.Tonic, R.Tier);
				R.Effect = C.Effect; R.Stat = GStats[Root];
				R.Magnitude = 5.f * R.Tier * Pcs.Num(); R.DurationS = 60.f * R.Tier;
				return R;
			}
		}
	}
	R.Chord = TEXT("Noise"); R.Tonic = TEXT("Item_YTM_Tonic_Dim_T1"); R.Effect = TEXT("poison_mild"); R.Tier = 1;
	return R;
}

FDaedalusBrewResult ADaedalusBrewBench::Brew(const TArray<FString>& Herbs, const TArray<int32>& Stages)
{
	FDaedalusBrewResult R = BrewStatic(Herbs, Stages);
	OnChordBrewed.Broadcast(R.Chord, R.Tonic, R.Notes);
	UE_LOG(LogTemp, Log, TEXT("Daedalus brew: %s -> %s (%s)"), *R.Chord, *R.Tonic, *R.Effect);
	return R;
}

// ---------------- Livestock ----------------
ADaedalusLivestock::ADaedalusLivestock()
{
	PrimaryActorTick.bCanEverTick = true;
	PrimaryActorTick.TickInterval = 1.f;
	RootComponent = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
	Tags.Add(TEXT("YTM_Livestock"));
}

void ADaedalusLivestock::Feed() { SinceFedMin = 0.f; }

bool ADaedalusLivestock::HasWater() const
{
	for (TActorIterator<AActor> It(GetWorld()); It; ++It)
		if ((It->ActorHasTag(TEXT("YTM_Trough")) || It->ActorHasTag(TEXT("Drinkable"))) &&
			FVector::Dist(It->GetActorLocation(), GetActorLocation()) <= TroughReach) return true;
	return false;
}

void ADaedalusLivestock::Tick(float Dt)
{
	Super::Tick(Dt);
	const float Min = Dt * TimeScale / 60.f;
	SinceFedMin += Min;
	const bool bHappy = SinceFedMin < StarveAfterMin && HasWater();
	if (!bHappy) return;
	AgeMin += Min;
	if (Age == TEXT("Calf") && AgeMin >= GrowAdultMin) { Age = TEXT("Adult"); SetActorScale3D(GetActorScale3D() * 1.8f); }
	else if (Age == TEXT("Adult") && AgeMin >= GrowElderMin) { Age = TEXT("Elder"); SetActorScale3D(GetActorScale3D() * 1.15f); }
	if (Age == TEXT("Calf")) return;
	SinceProduceMin += Min;
	if (SinceProduceMin >= ProduceEveryMin)
	{
		SinceProduceMin = 0.f; ++ProducedCount;
		OnProduced.Broadcast(Species, Product);
		UE_LOG(LogTemp, Log, TEXT("Daedalus livestock: %s produced %s (#%d)"), *Species, *Product, ProducedCount);
	}
}
