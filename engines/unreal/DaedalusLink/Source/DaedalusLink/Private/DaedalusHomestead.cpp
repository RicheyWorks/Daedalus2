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

float UDaedalusThirstComponent::Drink(const FString& Quality, float Restore)
{
	if (Quality == TEXT("clean")) { Thirst += Restore >= 0.f ? Restore : 35.f; bSick = false; }
	else if (Quality == TEXT("raw")) { Thirst += Restore >= 0.f ? Restore : 20.f; if (FMath::FRand() < 0.25f) bSick = true; }
	else if (Quality == TEXT("salt")) { Thirst += Restore >= 0.f ? -Restore : -10.f; }
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
	T->Drink(bTreats ? FString(TEXT("clean")) : Quality, RestoreAmount);
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

// ---------------- Melody Brewing ----------------
namespace
{
	const TCHAR* GHerbs[12] = { TEXT("Doleaf"), TEXT("Sharpcress"), TEXT("Rebell"), TEXT("Flatfern"), TEXT("Mimint"), TEXT("Fasage"),
		TEXT("Hushmoss"), TEXT("Solthorn"), TEXT("Gloryroot"), TEXT("Lavine"), TEXT("Dronebloom"), TEXT("Tisquill") };
	int32 NoteOf(const FString& H) { for (int32 i = 0; i < 12; ++i) if (H.Equals(GHerbs[i], ESearchCase::IgnoreCase)) return i; return -1; }
	int32 Step(int32 A, int32 B) { const int32 D = ((B - A) % 12 + 12) % 12; return D > 6 ? D - 12 : D; }
	FDaedalusBrewResult Noise() { FDaedalusBrewResult R; R.Melody = TEXT("Noise"); R.Tonic = TEXT("Item_YTM_Tonic_Dim_T1"); R.Effect = TEXT("poison_mild"); R.Tier = 1; return R; }
}

ADaedalusBrewBench::ADaedalusBrewBench()
{
	RootComponent = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
	Tags.Add(TEXT("YTM_BrewBench"));
}

FDaedalusBrewResult ADaedalusBrewBench::BrewStatic(const TArray<FString>& Herbs, const TArray<int32>& Stages)
{
	if (Herbs.Num() < 3 || Herbs.Num() > 5) return Noise();
	TArray<int32> Notes; float StageSum = 0.f;
	for (int32 i = 0; i < Herbs.Num(); ++i)
	{
		const int32 N = NoteOf(Herbs[i]);
		if (N < 0) return Noise();
		Notes.Add(N); StageSum += Stages.IsValidIndex(i) ? Stages[i] : 1;
	}
	TArray<int32> Steps; bool bAllSteps = true, bLeap = false;
	for (int32 i = 1; i < Notes.Num(); ++i)
	{
		const int32 S = Step(Notes[i - 1], Notes[i]);
		if (S == 0) { FDaedalusBrewResult R = Noise(); R.Notes = Notes; return R; }
		Steps.Add(S); bAllSteps &= FMath::Abs(S) <= 2; bLeap |= FMath::Abs(S) >= 5;
	}
	int32 Turns = 0;
	for (int32 i = 1; i < Steps.Num(); ++i) if ((Steps[i] > 0) != (Steps[i - 1] > 0)) ++Turns;
	const bool bUp = Steps[0] > 0;
	FString Contour, Quality, Effect;
	if (Turns == 0) { Contour = bUp ? TEXT("Rise") : TEXT("Fall"); Quality = bUp ? TEXT("Aug") : TEXT("Dim"); Effect = bUp ? TEXT("haste") : TEXT("cure_sickness"); }
	else if (Turns == 1) { Contour = bUp ? TEXT("Arch") : TEXT("Valley"); Quality = bUp ? TEXT("Major") : TEXT("Minor"); Effect = bUp ? TEXT("regen_health") : TEXT("restore_hunger"); }
	else { Contour = TEXT("Dance"); Quality = TEXT("Sus"); Effect = TEXT("stamina_boost"); }
	FDaedalusBrewResult R;
	R.Notes = Notes;
	R.Tier = FMath::Clamp(FMath::RoundToInt(StageSum / Herbs.Num()), 1, 4);
	R.bPurifiesWater = Notes.Last() == Notes[0];
	R.Melody = R.bPurifiesWater ? Contour + TEXT(" Cadence") : Contour;
	R.Tonic = FString::Printf(TEXT("Item_YTM_Tonic_%s_T%d"), R.bPurifiesWater ? TEXT("Seventh") : *Quality, R.Tier);
	R.Effect = Effect;
	R.Magnitude = 5.f * R.Tier * Notes.Num() * (bLeap ? 2.f : 1.f);
	R.DurationS = 60.f * R.Tier * (bAllSteps ? 2.f : 1.f);
	return R;
}

FDaedalusBrewResult ADaedalusBrewBench::Brew_Implementation(const TArray<FString>& Herbs, const TArray<int32>& Stages)
{
	FDaedalusBrewResult R = BrewStatic(Herbs, Stages);
	OnMelodyBrewed.Broadcast(R.Melody, R.Tonic, R.Notes);
	UE_LOG(LogTemp, Log, TEXT("Daedalus brew: %s -> %s (%s%s)"), *R.Melody, *R.Tonic, *R.Effect, R.bPurifiesWater ? TEXT(", purifies water") : TEXT(""));
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
