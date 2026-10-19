// SPDX-License-Identifier: MIT

#include "DaedalusLivingPainting.h"
#include "Components/PointLightComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/Engine.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "HAL/IConsoleManager.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Materials/MaterialInterface.h"
#include "UObject/ConstructorHelpers.h"

// Named (not anonymous) so unity builds cannot collide with other files' helpers.
namespace DaedalusLivingPaintingLocal
{
daedalus::gallery::Pigment ToCore(EDaedalusPigment P) { return static_cast<daedalus::gallery::Pigment>(static_cast<uint8>(P)); }
FLinearColor PigmentColour(int32 P)
{
	static const FLinearColor K[] = {FLinearColor(0.75f, 0.12f, 0.1f), FLinearColor(0.95f, 0.8f, 0.2f), FLinearColor(0.15f, 0.3f, 0.8f),
	                                 FLinearColor(0.95f, 0.5f, 0.12f), FLinearColor(0.2f, 0.6f, 0.3f), FLinearColor(0.5f, 0.25f, 0.7f)};
	return (P >= 0 && P < 6) ? K[P] : FLinearColor(0.35f, 0.35f, 0.35f);
}
bool ParsePigment(const FString& S, EDaedalusPigment& Out)
{
	static const TCHAR* K[] = {TEXT("red"), TEXT("yellow"), TEXT("blue"), TEXT("orange"), TEXT("green"), TEXT("violet")};
	for (int32 I = 0; I < 6; ++I)
	{
		if (S.Equals(K[I], ESearchCase::IgnoreCase)) { Out = static_cast<EDaedalusPigment>(I); return true; }
	}
	return false;
}
ADaedalusLivingPainting* FirstPainting(UWorld* World)
{
	if (!World) { return nullptr; }
	TActorIterator<ADaedalusLivingPainting> It(World);
	return It ? *It : nullptr;
}
}

ADaedalusLivingPainting::ADaedalusLivingPainting()
{
	bReplicates = false;
	Tags.Add(TEXT("LivingPainting"));
	Tags.Add(TEXT("Interact_LivingPainting"));
	static ConstructorHelpers::FObjectFinder<UStaticMesh> Cube(TEXT("/Engine/BasicShapes/Cube.Cube"));
	Body->SetCollisionProfileName(TEXT("NoCollision"));
	Panel = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Panel"));
	Panel->SetupAttachment(Body);
	if (Cube.Succeeded()) { Panel->SetStaticMesh(Cube.Object); }
	Panel->SetMobility(EComponentMobility::Movable);
	Panel->SetCollisionProfileName(TEXT("BlockAllDynamic"));
	Glow->SetLightColor(FLinearColor(1.f, 0.85f, 0.6f));
}

void ADaedalusLivingPainting::BeginPlay()
{
	Super::BeginPlay();
	const int32 N = FMath::Clamp(StartingPrimaries, 0, daedalus::gallery::Palette::kMaxUnits);
	Pal.Add(daedalus::gallery::Pigment::Red, N);
	Pal.Add(daedalus::gallery::Pigment::Yellow, N);
	Pal.Add(daedalus::gallery::Pigment::Blue, N);
	Rebuild();
}

void ADaedalusLivingPainting::SetFromFrame(int64 FrameSeed, int32 FrameW, int32 FrameH)
{
	Seed = FrameSeed;
	Width = FMath::Min(daedalus::gallery::kMaxSide, FrameW * 2);
	Height = FMath::Min(daedalus::gallery::kMaxSide, FrameH * 2);
	Rebuild();
}

bool ADaedalusLivingPainting::Rebuild()
{
	Mural = MakeUnique<daedalus::gallery::Painting>(static_cast<int64_t>(Seed), Width, Height);
	bAwake = false;
	for (UStaticMeshComponent* C : CellParts) { if (C) { C->DestroyComponent(); } }
	CellParts.Reset();
	CellMats.Reset();
	PaintedWith.Init(-1, Mural->Valid() ? Mural->CellCount() : 0);
	if (!Mural->Valid())
	{
		UE_LOG(LogTemp, Warning, TEXT("Daedalus living painting: seed %lld or size %dx%d is out of range (seed 0..999999999, sides 1..12)"),
		       static_cast<long long>(Seed), Width, Height);
		return false;
	}
	UStaticMesh* Plane = LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Plane.Plane"));
	UMaterialInterface* Base = LoadObject<UMaterialInterface>(nullptr, TEXT("/Engine/BasicShapes/BasicShapeMaterial.BasicShapeMaterial"));
	const float W = Width * CellSize, H = Height * CellSize;
	Panel->SetRelativeLocation(FVector(-6.f, 0.f, H * 0.5f));
	Panel->SetRelativeScale3D(FVector(0.1f, (W + 20.f) / 100.f, (H + 20.f) / 100.f));
	for (int32 Y = 0; Y < Height; ++Y)
	{
		for (int32 X = 0; X < Width; ++X)
		{
			UStaticMeshComponent* C = NewObject<UStaticMeshComponent>(this, *FString::Printf(TEXT("Cell_%d_%d"), X, Y));
			C->SetupAttachment(Body);
			C->SetMobility(EComponentMobility::Movable);
			C->SetCollisionProfileName(TEXT("NoCollision"));
			if (Plane) { C->SetStaticMesh(Plane); }
			// Plane faces +Z; stand it up facing +X. Row 0 is the top of the mural.
			C->SetRelativeRotation(FRotator(90.f, 0.f, 0.f));
			C->SetRelativeLocation(FVector(0.f, (X + 0.5f) * CellSize - W * 0.5f, H - (Y + 0.5f) * CellSize));
			C->SetRelativeScale3D(FVector(CellSize * 0.009f, CellSize * 0.009f, 1.f));
			C->RegisterComponent();
			UMaterialInstanceDynamic* M = Base ? UMaterialInstanceDynamic::Create(Base, this) : nullptr;
			if (M) { C->SetMaterial(0, M); }
			CellParts.Add(C);
			CellMats.Add(M);
			Recolour(X, Y);
		}
	}
	return true;
}

void ADaedalusLivingPainting::Recolour(int32 X, int32 Y)
{
	const int32 I = Y * Width + X;
	if (!CellMats.IsValidIndex(I) || !CellMats[I] || !Mural.IsValid()) { return; }
	const daedalus::gallery::Cell C = Mural->CellAt(X, Y);
	const FLinearColor Col = C == daedalus::gallery::Cell::Restored ? DaedalusLivingPaintingLocal::PigmentColour(PaintedWith[I])
		: (C == daedalus::gallery::Cell::Smudged ? FLinearColor(0.2f, 0.17f, 0.14f) : FLinearColor(0.35f, 0.35f, 0.35f));
	CellMats[I]->SetVectorParameterValue(TEXT("Color"), Col);
}

FString ADaedalusLivingPainting::Grind(const FString& Ingredient)
{
	const FString R = daedalus::gallery::PaletteResultName(Pal.Grind(std::string(TCHAR_TO_UTF8(*Ingredient.ToLower()))));
	Tell(FString::Printf(TEXT("Grind %s: %s"), *Ingredient, *R));
	return R;
}

FString ADaedalusLivingPainting::Mix(EDaedalusPigment Secondary)
{
	const daedalus::gallery::Pigment P = DaedalusLivingPaintingLocal::ToCore(Secondary);
	const FString R = daedalus::gallery::PaletteResultName(Pal.Mix(P, Know));
	Tell(FString::Printf(TEXT("Mix %s: %s"), UTF8_TO_TCHAR(daedalus::gallery::PigmentName(P)), *R));
	return R;
}

FString ADaedalusLivingPainting::Paint(int32 X, int32 Y, EDaedalusPigment Pigment)
{
	if (!Mural.IsValid() || !Mural->Valid()) { return TEXT("BAD_CELL"); }
	const daedalus::gallery::Pigment P = DaedalusLivingPaintingLocal::ToCore(Pigment);
	const daedalus::gallery::Result R = Mural->Paint(X, Y, P, Pal, Know);
	const FString Name = daedalus::gallery::ResultName(R);
	if (R == daedalus::gallery::Result::Restored) { PaintedWith[Y * Width + X] = static_cast<int32>(P); }
	Recolour(X, Y);
	OnStroke.Broadcast(X, Y, Name);
	if (R == daedalus::gallery::Result::Smudged) { Tell(TEXT("Wrong colour: the cell smudges and a Smudgeling stirs. Wash it with turpentine.")); }
	if (!bAwake && Mural->GetState() == daedalus::gallery::State::Living)
	{
		bAwake = true;
		Glow->SetIntensity(3000.f);
		const FString Who = Subject();
		OnAwake.Broadcast(Who);
		Tell(FString::Printf(TEXT("The mural wakes! %s steps out of the painting."), *Who));
	}
	return Name;
}

FString ADaedalusLivingPainting::Wash(int32 X, int32 Y)
{
	if (!Mural.IsValid()) { return TEXT("BAD_CELL"); }
	const FString Name = daedalus::gallery::ResultName(Mural->Wash(X, Y));
	Recolour(X, Y);
	return Name;
}

bool ADaedalusLivingPainting::Reveal(int32 X, int32 Y, EDaedalusPigment& Pigment) const
{
	daedalus::gallery::Pigment P = daedalus::gallery::Pigment::Red;
	if (!Mural.IsValid() || !Mural->Reveal(X, Y, Know, P)) { return false; }
	Pigment = static_cast<EDaedalusPigment>(static_cast<int32>(P));
	return true;
}

bool ADaedalusLivingPainting::NextCell(int32& X, int32& Y) const
{
	if (!Mural.IsValid() || !Mural->Valid()) { return false; }
	for (int32 I = 0; I < Mural->CellCount(); ++I)
	{
		X = I % Width;
		Y = I / Width;
		if (Mural->CellAt(X, Y) != daedalus::gallery::Cell::Restored) { return true; }
	}
	return false;
}

FString ADaedalusLivingPainting::Prompt(const ADaedalusHero* Hero) const
{
	int32 X = 0, Y = 0;
	if (!NextCell(X, Y)) { return bAwake ? TEXT("The mural is alive") : TEXT("Look at the painting"); }
	if (Mural->CellAt(X, Y) == daedalus::gallery::Cell::Smudged) { return TEXT("Wash the smudge"); }
	return FString::Printf(TEXT("Paint with %s"), UTF8_TO_TCHAR(daedalus::gallery::PigmentName(DaedalusLivingPaintingLocal::ToCore(SelectedPigment))));
}

bool ADaedalusLivingPainting::Use(ADaedalusHero* Hero)
{
	int32 X = 0, Y = 0;
	if (!NextCell(X, Y)) { Tell(bAwake ? TEXT("The mural is alive.") : TEXT("Nothing to paint.")); return false; }
	const FString R = Mural->CellAt(X, Y) == daedalus::gallery::Cell::Smudged ? Wash(X, Y) : Paint(X, Y, SelectedPigment);
	Tell(FString::Printf(TEXT("Cell %d,%d: %s (%d per mille)"), X, Y, *R, ProgressPm()));
	return R == TEXT("RESTORED") || R == TEXT("WASHED");
}

FString ADaedalusLivingPainting::MuralState() const
{
	return Mural.IsValid() ? FString(daedalus::gallery::StateName(Mural->GetState())) : FString(TEXT("DRAINED"));
}

int32 ADaedalusLivingPainting::ProgressPm() const { return Mural.IsValid() ? Mural->ProgressPm() : 0; }
int32 ADaedalusLivingPainting::Units(EDaedalusPigment Pigment) const { return Pal.Count(DaedalusLivingPaintingLocal::ToCore(Pigment)); }
bool ADaedalusLivingPainting::Knows(EDaedalusPigment Pigment) const { return Know.Knows(DaedalusLivingPaintingLocal::ToCore(Pigment)); }

TArray<FString> ADaedalusLivingPainting::Abilities() const
{
	TArray<FString> Out;
	for (int32 I = 0; I < daedalus::gallery::kAbilities; ++I)
	{
		const daedalus::gallery::Ability A = static_cast<daedalus::gallery::Ability>(I);
		if (Know.Has(A)) { Out.Add(UTF8_TO_TCHAR(daedalus::gallery::AbilityName(A))); }
	}
	return Out;
}

FString ADaedalusLivingPainting::Subject() const { return UTF8_TO_TCHAR(daedalus::gallery::Subject(static_cast<int64_t>(Seed))); }

FString ADaedalusLivingPainting::Status() const
{
	return FString::Printf(TEXT("seed %lld %dx%d %s %d pm, smudges %d, units R%d Y%d B%d O%d G%d V%d, abilities [%s], subject %s"),
	                       static_cast<long long>(Seed), Width, Height, *MuralState(), ProgressPm(), Mural.IsValid() ? Mural->SmudgeCount() : 0,
	                       Units(EDaedalusPigment::Red), Units(EDaedalusPigment::Yellow), Units(EDaedalusPigment::Blue),
	                       Units(EDaedalusPigment::Orange), Units(EDaedalusPigment::Green), Units(EDaedalusPigment::Violet),
	                       *FString::Join(Abilities(), TEXT(",")), *Subject());
}

void ADaedalusLivingPainting::Tell(const FString& Text) const
{
	UE_LOG(LogTemp, Log, TEXT("Daedalus living painting: %s"), *Text);
	if (GEngine) { GEngine->AddOnScreenDebugMessage(-1, 5.f, FColor(240, 210, 150), Text); }
}

static FAutoConsoleCommandWithWorldAndArgs GLivingPaintingPaint(
	TEXT("daedalus.painting.paint"), TEXT("daedalus.painting.paint <x> <y> <red|yellow|blue|orange|green|violet>"),
	FConsoleCommandWithWorldAndArgsDelegate::CreateLambda([](const TArray<FString>& Args, UWorld* World)
	{
		ADaedalusLivingPainting* P = DaedalusLivingPaintingLocal::FirstPainting(World);
		EDaedalusPigment Pg = EDaedalusPigment::Red;
		if (!P || Args.Num() < 3 || !DaedalusLivingPaintingLocal::ParsePigment(Args[2], Pg)) { UE_LOG(LogTemp, Warning, TEXT("daedalus.painting.paint: no painting, or bad arguments")); return; }
		UE_LOG(LogTemp, Log, TEXT("Daedalus living painting: %s"), *P->Paint(FCString::Atoi(*Args[0]), FCString::Atoi(*Args[1]), Pg));
	}));

static FAutoConsoleCommandWithWorldAndArgs GLivingPaintingWash(
	TEXT("daedalus.painting.wash"), TEXT("daedalus.painting.wash <x> <y>: turpentine wash of a smudged cell"),
	FConsoleCommandWithWorldAndArgsDelegate::CreateLambda([](const TArray<FString>& Args, UWorld* World)
	{
		ADaedalusLivingPainting* P = DaedalusLivingPaintingLocal::FirstPainting(World);
		if (!P || Args.Num() < 2) { UE_LOG(LogTemp, Warning, TEXT("daedalus.painting.wash: no painting, or bad arguments")); return; }
		UE_LOG(LogTemp, Log, TEXT("Daedalus living painting: %s"), *P->Wash(FCString::Atoi(*Args[0]), FCString::Atoi(*Args[1])));
	}));

static FAutoConsoleCommandWithWorldAndArgs GLivingPaintingGrind(
	TEXT("daedalus.painting.grind"), TEXT("daedalus.painting.grind <ingredient> [mix <orange|green|violet>]"),
	FConsoleCommandWithWorldAndArgsDelegate::CreateLambda([](const TArray<FString>& Args, UWorld* World)
	{
		ADaedalusLivingPainting* P = DaedalusLivingPaintingLocal::FirstPainting(World);
		if (!P || Args.Num() < 1) { UE_LOG(LogTemp, Warning, TEXT("daedalus.painting.grind: no painting, or no ingredient")); return; }
		EDaedalusPigment Pg = EDaedalusPigment::Orange;
		if (Args[0].Equals(TEXT("mix"), ESearchCase::IgnoreCase) && Args.Num() > 1 && DaedalusLivingPaintingLocal::ParsePigment(Args[1], Pg)) { P->Mix(Pg); }
		else { P->Grind(Args[0]); }
	}));

static FAutoConsoleCommandWithWorldAndArgs GLivingPaintingStatus(
	TEXT("daedalus.painting.status"), TEXT("daedalus.painting.status: mural state, progress, palette, abilities, subject"),
	FConsoleCommandWithWorldAndArgsDelegate::CreateLambda([](const TArray<FString>&, UWorld* World)
	{
		ADaedalusLivingPainting* P = DaedalusLivingPaintingLocal::FirstPainting(World);
		UE_LOG(LogTemp, Log, TEXT("Daedalus living painting: %s"), P ? *P->Status() : TEXT("none in the world"));
	}));