// SPDX-License-Identifier: MIT

#include "DaedalusCritter.h"

#include "Components/SceneComponent.h"
#include "Components/StaticMeshComponent.h"
#include "DaedalusMob.h"
#include "DaedalusNav.h"
#include "Engine/World.h"
#include "GameFramework/Pawn.h"
#include "Kismet/GameplayStatics.h"

ADaedalusCritter::ADaedalusCritter()
{
	PrimaryActorTick.bCanEverTick = true;
	RootComponent = CreateDefaultSubobject<USceneComponent>(TEXT("Feet"));
	RootComponent->SetMobility(EComponentMobility::Movable);
	Look = CreateDefaultSubobject<USceneComponent>(TEXT("Look"));
	Look->SetupAttachment(RootComponent);
	Look->SetRelativeRotation(FRotator(0.f, -90.f, 0.f));   // the art faces +Y; actors face +X
	Tags.Add(TEXT("DaedalusCritter"));
}

bool ADaedalusCritter::IsShy() const
{
	for (const TCHAR* Bold : {TEXT("Cow"), TEXT("Horse"), TEXT("PolarBear"), TEXT("Crocodile"), TEXT("Tapir"), TEXT("Caribou")})
		if (Species.Contains(Bold)) return false;
	return true;
}

int32 ADaedalusCritter::Rebuild()
{
	for (UStaticMeshComponent* C : Meshes)
		if (C) C->DestroyComponent();
	Meshes.Reset();
	TArray<UStaticMeshComponent*> Made;
	float Height = 0.f;
	Parts = DaedalusMob::Build(this, Look, Species, &Made, &Height);
	for (UStaticMeshComponent* C : Made) Meshes.Add(C);
	Size = FMath::Max(Height * GetActorScale3D().Z, 20.f);
	if (bShiny)
	{
		SetActorScale3D(FVector(DaedalusShiny::ScaleBoost));
		Size *= DaedalusShiny::ScaleBoost;
		DaedalusShiny::Attach(this, Look, Size, Shiny);
	}
	else DaedalusShiny::Detach(Shiny);
	return Parts;
}

void ADaedalusCritter::Settle()
{
	FHitResult Hit;
	const FVector At = GetActorLocation();
	FCollisionQueryParams Q(SCENE_QUERY_STAT(DaedalusCritterSettle), false, this);
	if (GetWorld()->LineTraceSingleByObjectType(Hit, At + FVector(0.f, 0.f, 400.f), At - FVector(0.f, 0.f, 2000.f),
		FCollisionObjectQueryParams(ECC_WorldStatic), Q))
	{
		SetActorLocation(Hit.ImpactPoint);
	}
}

void ADaedalusCritter::BeginPlay()
{
	Super::BeginPlay();
	Rng.Initialize(Seed);
	Rebuild();
	Settle();
	Home = GetActorLocation();
	Heading = FRotator(0.f, Rng.FRandRange(0.f, 360.f), 0.f).Vector();
	SetActorRotation(Heading.Rotation());
	Left = Rng.FRandRange(0.5f, 4.f);   // so a herd doesn't move as one
}

// One step along the ground; false (and no move) at a ledge, a wall or a tree.
bool ADaedalusCritter::Step(const FVector& Dir, float Speed, float Dt)
{
	const FVector Flat(Dir.X, Dir.Y, 0.f);
	if (Flat.IsNearlyZero()) return true;
	const FVector Now = GetActorLocation();
	const FVector Next = Now + Flat.GetSafeNormal() * Speed * Dt;
	FHitResult Hit;
	FCollisionQueryParams Q(SCENE_QUERY_STAT(DaedalusCritterStep), false, this);
	if (APawn* P = UGameplayStatics::GetPlayerPawn(this, 0)) Q.AddIgnoredActor(P);
	if (!GetWorld()->LineTraceSingleByObjectType(Hit, Next + FVector(0.f, 0.f, 250.f), Next - FVector(0.f, 0.f, 300.f),
		FCollisionObjectQueryParams(ECC_WorldStatic), Q))
	{
		return false;   // a drop
	}
	const float Rise = Hit.ImpactPoint.Z - Now.Z;
	if (Rise > UDaedalusNav::StepUp || Rise < -UDaedalusNav::StepDown) return false;
	SetActorLocation(FVector(Next.X, Next.Y, FMath::FInterpTo(Now.Z, Hit.ImpactPoint.Z, Dt, 14.f)));
	Walked += Speed * Dt;
	return true;
}

void ADaedalusCritter::Tick(float DeltaSeconds)
{
	if (bShiny) DaedalusShiny::Tick(Shiny, DeltaSeconds);
	Super::Tick(DeltaSeconds);
	const float Dt = FMath::Min(DeltaSeconds, 0.1f);
	Age += Dt;
	if (Settles < 3 && Age >= NextSettle)
	{
		// Ground again at 1.5, 4 and 8 s: whatever streamed in after BeginPlay (the live world, an island) is
		// under the critter's feet now, so it is not walled in by a "step up" that is really the new surface.
		const FVector Before = GetActorLocation();
		Settle();
		Home += GetActorLocation() - Before;
		++Settles;
		NextSettle = Settles == 1 ? 4.f : 8.f;
	}
	const APawn* Who = UGameplayStatics::GetPlayerPawn(this, 0);
	const float Dist = Who ? FVector::Dist(Who->GetActorLocation(), GetActorLocation()) : 1e9f;
	// Out of sight, out of mind: far animals think once a second.
	SetActorTickInterval(Dist > 25000.f ? 1.f : 0.f);

	Check -= Dt;
	if (Who && Check <= 0.f)
	{
		Check = 0.2f;
		const float Fear = 450.f + Size * 2.f;
		if (IsShy() && Dist < Fear && State != TEXT("FLEE"))
		{
			State = TEXT("FLEE");
			++Flees;
			Left = Rng.FRandRange(1.5f, 2.5f);
		}
		if (State == TEXT("FLEE"))
		{
			const FVector Away = GetActorLocation() - Who->GetActorLocation();
			Heading = FVector(Away.X, Away.Y, 0.f).GetSafeNormal();
		}
	}

	Left -= Dt;
	if (Left <= 0.f)
	{
		if (State == TEXT("GRAZE"))
		{
			State = TEXT("WALK");
			Left = Rng.FRandRange(1.5f, 4.f);
			FVector ToHome = Home - GetActorLocation();
			ToHome.Z = 0.f;
			const float Far = ToHome.Size() / FMath::Max(Range, 1.f);
			const FVector Wander = FRotator(0.f, Rng.FRandRange(0.f, 360.f), 0.f).Vector();
			Heading = (Wander + ToHome.GetSafeNormal() * FMath::Clamp(Far, 0.f, 2.f)).GetSafeNormal2D();
			if (Heading.IsNearlyZero()) Heading = Wander;
		}
		else
		{
			State = TEXT("GRAZE");
			Left = Rng.FRandRange(2.f, 6.f);
		}
	}

	float Speed = 0.f;
	if (State == TEXT("WALK")) Speed = 50.f + Size * 0.6f;
	else if (State == TEXT("FLEE")) Speed = 220.f + Size * 2.f;
	if (bShiny) Speed *= DaedalusShiny::StatBoost;
	if (Speed > 0.f && !Step(Heading, Speed, Dt))
	{
		++Ledges;
		Heading = FRotator(0.f, Rng.FRandRange(120.f, 240.f), 0.f).RotateVector(Heading);   // turn away and try again
		if (State == TEXT("WALK")) Left = FMath::Min(Left, 0.6f);
	}

	// Face the way it goes; bob and rock while moving, nod while it grazes.
	const float Yaw = FMath::FixedTurn(GetActorRotation().Yaw, Heading.Rotation().Yaw, 240.f * Dt);
	SetActorRotation(FRotator(0.f, Yaw, 0.f));
	Gait += Dt * Speed / FMath::Max(Size, 20.f) * 7.f;
	const float Bob = Speed > 0.f ? FMath::Abs(FMath::Sin(Gait)) * Size * 0.05f : 0.f;
	const float Nod = Speed > 0.f ? FMath::Sin(Gait * 2.f) * 3.f : FMath::Sin(Age * 1.3f) * 4.f - 4.f;
	Look->SetRelativeLocationAndRotation(FVector(0.f, 0.f, Bob), FRotator(0.f, -90.f, Nod));
}
