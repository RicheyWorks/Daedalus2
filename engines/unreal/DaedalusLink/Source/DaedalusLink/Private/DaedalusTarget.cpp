// SPDX-License-Identifier: MIT

#include "DaedalusTarget.h"

#include "Components/StaticMeshComponent.h"
#include "DaedalusNav.h"
#include "Engine/StaticMesh.h"
#include "Engine/StaticMeshActor.h"
#include "Engine/World.h"
#include "GameFramework/Pawn.h"
#include "HAL/IConsoleManager.h"
#include "Kismet/GameplayStatics.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "UObject/ConstructorHelpers.h"

static TAutoConsoleVariable<int32> CVarFoesHunt(TEXT("daedalus.FoesHunt"), 1,
	TEXT("1: foes hunt the player (ADR-044). 0: they stay where they are."));

namespace
{
	UMaterialInterface* FoeMaterial()
	{
		static UMaterialInterface* M = LoadObject<UMaterialInterface>(nullptr, TEXT("/Engine/BasicShapes/BasicShapeMaterial.BasicShapeMaterial"));
		return M;
	}

	const FLinearColor Telegraph(1.f, 0.45f, 0.1f);
}

ADaedalusTarget::ADaedalusTarget()
{
	PrimaryActorTick.bCanEverTick = true;
	static ConstructorHelpers::FObjectFinder<UStaticMesh> Shape(TEXT("/Engine/BasicShapes/Cone.Cone"));
	static ConstructorHelpers::FObjectFinder<UStaticMesh> Sphere(TEXT("/Engine/BasicShapes/Sphere.Sphere"));
	BoltMesh = Sphere.Object;
	Crystal = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Crystal"));
	RootComponent = Crystal;
	Crystal->SetStaticMesh(Shape.Object);
	Crystal->SetRelativeScale3D(FVector(0.9f, 0.9f, 1.4f));
	Crystal->SetCollisionProfileName(TEXT("BlockAllDynamic"));
	Crystal->SetMobility(EComponentMobility::Movable);
	Tags.Add(TEXT("DaedalusTarget"));
}

float ADaedalusTarget::HoverOffset() const
{
	if (Kind == TEXT("DUST_WISP")) return 260.f;
	if (Kind == TEXT("STONE_KNIGHT")) return 100.f;
	if (Kind == TEXT("SHARDBACK")) return 65.f;
	return 30.f;
}

void ADaedalusTarget::BeginPlay()
{
	Super::BeginPlay();
	Home = GetActorLocation();
	// Each kind its own look: the slime green and low, the shardback stony, the wisp pale and high, the knight dark.
	FLinearColor Tint(0.85f, 0.2f, 0.9f);
	if (Kind == TEXT("BLIGHT_SLIME")) { Tint = FLinearColor(0.35f, 0.85f, 0.25f); SetActorScale3D(FVector(1.1f, 1.1f, 0.6f)); }
	else if (Kind == TEXT("SHARDBACK")) { Tint = FLinearColor(0.45f, 0.55f, 0.75f); SetActorScale3D(FVector(1.3f)); }
	else if (Kind == TEXT("DUST_WISP")) { Tint = FLinearColor(0.85f, 0.95f, 1.f); SetActorScale3D(FVector(0.7f)); }
	else if (Kind == TEXT("STONE_KNIGHT")) { Tint = FLinearColor(0.25f, 0.25f, 0.3f); SetActorScale3D(FVector(1.2f, 1.2f, 2.0f)); }
	BaseTint = Tint;
	StartScale = GetActorScale3D();
	if (FoeMaterial())
	{
		Mat = UMaterialInstanceDynamic::Create(FoeMaterial(), this);
		Mat->SetVectorParameterValue(TEXT("Color"), BaseTint);
		Crystal->SetMaterial(0, Mat);
	}
	// Settle onto the ground under where it was placed.
	FHitResult Hit;
	FCollisionObjectQueryParams Objects(ECC_WorldStatic);
	if (GetWorld()->LineTraceSingleByObjectType(Hit, Home + FVector(0.f, 0.f, 100.f), Home - FVector(0.f, 0.f, 1500.f), Objects, FCollisionQueryParams(SCENE_QUERY_STAT(DaedalusFoeSettle), false, this)))
	{
		Home.Z = Hit.ImpactPoint.Z + HoverOffset();
	}
	Cooldown = FMath::FRandRange(0.5f, 1.5f);   // so a pack doesn't strike in unison
}

void ADaedalusTarget::EndPlay(const EEndPlayReason::Type Reason)
{
	for (FBolt& B : Bolts)
	{
		if (B.Vis.IsValid()) B.Vis->Destroy();
	}
	Bolts.Reset();
	Super::EndPlay(Reason);
}

// Move along the ground a step at a time, stopping at ledges. Returns false if the way was a drop or a wall.
bool ADaedalusTarget::StepToward(const FVector& Dir, float Speed, float Dt)
{
	const FVector Flat(Dir.X, Dir.Y, 0.f);
	if (Flat.IsNearlyZero()) return true;
	const FVector Next = Home + Flat.GetSafeNormal() * Speed * Dt;
	if (Kind == TEXT("DUST_WISP"))
	{
		Home = Next;   // it flies
		return true;
	}
	FHitResult Hit;
	FCollisionObjectQueryParams Objects(ECC_WorldStatic);
	const float Floor = Home.Z - HoverOffset();
	if (!GetWorld()->LineTraceSingleByObjectType(Hit, FVector(Next.X, Next.Y, Floor + 300.f), FVector(Next.X, Next.Y, Floor - 300.f), Objects, FCollisionQueryParams(SCENE_QUERY_STAT(DaedalusFoeStep), false, this)))
	{
		return false;   // a drop
	}
	const float Rise = Hit.ImpactPoint.Z - Floor;
	if (Rise > UDaedalusNav::StepUp || Rise < -UDaedalusNav::StepDown) return false;
	Home = FVector(Next.X, Next.Y, FMath::FInterpTo(Home.Z, Hit.ImpactPoint.Z + HoverOffset(), Dt, 12.f));
	return true;
}

void ADaedalusTarget::Strike(APawn* Who, float Damage)
{
	if (!Who) return;
	++Landed;
	UGameplayStatics::ApplyDamage(Who, Damage, nullptr, this, nullptr);
}

void ADaedalusTarget::FireBolt(const APawn* Who)
{
	if (!Who) return;
	const FVector From = GetActorLocation() + FVector(0.f, 0.f, 30.f);
	// Lead the target a little, like a careful archer, but slow enough to sidestep.
	const FVector Aim = Who->GetActorLocation() + Who->GetVelocity() * 0.35f;
	FBolt B;
	B.Pos = From;
	B.Vel = (Aim - From).GetSafeNormal() * 1500.f;
	FActorSpawnParameters P;
	P.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
	if (AStaticMeshActor* V = GetWorld()->SpawnActor<AStaticMeshActor>(From, FRotator::ZeroRotator, P))
	{
		UStaticMeshComponent* C = V->GetStaticMeshComponent();
		C->SetMobility(EComponentMobility::Movable);
		C->SetStaticMesh(BoltMesh);
		C->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		C->SetCastShadow(false);
		V->SetActorScale3D(FVector(0.3f));
		if (FoeMaterial())
		{
			UMaterialInstanceDynamic* M = UMaterialInstanceDynamic::Create(FoeMaterial(), V);
			M->SetVectorParameterValue(TEXT("Color"), FLinearColor(1.f, 0.8f, 0.35f) * 4.f);
			C->SetMaterial(0, M);
		}
		B.Vis = V;
	}
	Bolts.Add(B);
	++Attacks;
}

void ADaedalusTarget::TickBolts(APawn* Who, float Dt)
{
	FCollisionQueryParams Q(SCENE_QUERY_STAT(DaedalusBolt), false, this);
	if (Who) Q.AddIgnoredActor(Who);
	FCollisionObjectQueryParams Objects(ECC_WorldStatic);
	for (int32 i = Bolts.Num() - 1; i >= 0; --i)
	{
		FBolt& B = Bolts[i];
		const FVector Next = B.Pos + B.Vel * Dt;
		B.Life -= Dt;
		bool bDone = B.Life <= 0.f;
		// The player: closest point of this step's segment within reach of their middle.
		if (!bDone && Who)
		{
			const FVector Closest = FMath::ClosestPointOnSegment(Who->GetActorLocation(), B.Pos, Next);
			if (FVector::Dist(Closest, Who->GetActorLocation()) < 75.f)
			{
				Strike(Who, Power * 10.f);
				bDone = true;
			}
		}
		FHitResult Wall;
		if (!bDone && GetWorld()->LineTraceSingleByObjectType(Wall, B.Pos, Next, Objects, Q)) bDone = true;
		B.Pos = Next;
		if (B.Vis.IsValid()) B.Vis->SetActorLocation(Next);
		if (bDone)
		{
			if (B.Vis.IsValid()) B.Vis->Destroy();
			Bolts.RemoveAtSwap(i);
		}
	}
}

void ADaedalusTarget::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	const float Dt = FMath::Min(DeltaSeconds, 0.1f);
	Age += Dt;
	if (Dying >= 0.f)
	{
		// Shatter: swell and vanish over a fifth of a second.
		State = TEXT("DYING");
		Dying += Dt;
		SetActorScale3D(StartScale * (1.f + Dying * 6.f));
		if (Dying > 0.2f) Destroy();
		return;
	}

	APawn* Who = UGameplayStatics::GetPlayerPawn(this, 0);
	TickBolts(Who, Dt);
	Cooldown = FMath::Max(0.f, Cooldown - Dt);

	// Can it see the player? A trace to them that meets nothing solid on the way (checked four times a second).
	const FVector Me = GetActorLocation();
	const float Dist = Who ? FVector::Dist(Who->GetActorLocation(), Me) : TNumericLimits<float>::Max();
	SightCheck -= Dt;
	if (SightCheck <= 0.f)
	{
		SightCheck = 0.25f;
		bSeesPlayer = false;
		if (Who && Dist < AggroRange)
		{
			FHitResult Hit;
			FCollisionQueryParams Q(SCENE_QUERY_STAT(DaedalusFoeSight), false, this);
			Q.AddIgnoredActor(Who);
			bSeesPlayer = !GetWorld()->LineTraceSingleByObjectType(Hit, Me + FVector(0.f, 0.f, 40.f), Who->GetActorLocation(),
				FCollisionObjectQueryParams(ECC_WorldStatic), Q);
		}
	}
	const bool bHunting = Who && bHunts && CVarFoesHunt.GetValueOnGameThread() != 0 && Dist < AggroRange
		&& (bSeesPlayer || Windup >= 0.f || ChargeLeft > 0.f || Dist < 900.f);

	float Bob = FMath::Sin(Age * 2.f) * 40.f;
	float Glow = 0.f;
	if (!bHunting)
	{
		State = TEXT("IDLE");
		Windup = -1.f;
		ChargeLeft = 0.f;
		AddActorLocalRotation(FRotator(0.f, 60.f * Dt, 0.f));
	}
	else
	{
		const FVector To = Who->GetActorLocation() - Home;
		const FVector Dir(To.X, To.Y, 0.f);
		const float Flat = Dir.Size();
		SetActorRotation(FRotator(0.f, Dir.Rotation().Yaw, 0.f));
		State = TEXT("HUNT");

		if (Kind == TEXT("SHARDBACK"))
		{
			Bob *= 0.3f;
			if (ChargeLeft > 0.f)
			{
				State = TEXT("CHARGE");
				ChargeLeft -= Dt;
				if (!StepToward(ChargeDir, 1500.f, Dt)) ChargeLeft = 0.f;   // stops dead at a ledge or a wall
				if (ChargeLeft <= 0.f) Cooldown = FMath::Max(Cooldown, 1.8f);   // a miss leaves it winded
				if (Dist < 170.f)
				{
					Strike(Who, Power * 10.f);
					ChargeLeft = 0.f;
					Cooldown = 1.6f;
				}
			}
			else if (Windup >= 0.f)
			{
				State = TEXT("WINDUP");
				Windup -= Dt;
				Glow = 1.f - FMath::Max(Windup, 0.f) / WindupTime;
				if (Windup < 0.f)
				{
					ChargeDir = Dir.GetSafeNormal();
					ChargeLeft = 0.75f;
					++Attacks;
				}
			}
			else if (Flat < 1000.f && Cooldown <= 0.f && bSeesPlayer)
			{
				Windup = WindupTime = 0.55f;
			}
			else
			{
				StepToward(Dir, 380.f, Dt);
			}
		}
		else if (Kind == TEXT("DUST_WISP"))
		{
			// Keep 700..1300 cm away, float above the player's head, and shoot.
			if (Flat > 1300.f) StepToward(Dir, 360.f, Dt);
			else if (Flat < 700.f) StepToward(-Dir, 320.f, Dt);
			else StepToward(FVector(-Dir.Y, Dir.X, 0.f), 140.f * FMath::Sin(Age * 0.7f), Dt);   // drift sideways
			Home.Z = FMath::FInterpTo(Home.Z, Who->GetActorLocation().Z + HoverOffset(), Dt, 1.5f);
			if (Windup >= 0.f)
			{
				State = TEXT("WINDUP");
				Windup -= Dt;
				Glow = 1.f - FMath::Max(Windup, 0.f) / WindupTime;
				if (Windup < 0.f) FireBolt(Who);
			}
			else if (Cooldown <= 0.f && bSeesPlayer)
			{
				Windup = WindupTime = 0.4f;
				Cooldown = 1.9f;
			}
		}
		else
		{
			// Slime and knight: follow the A* route (ported from the maze solver) and strike up close.
			const bool bKnight = Kind == TEXT("STONE_KNIGHT");
			const float Reach = bKnight ? 260.f : 150.f;
			if (Windup >= 0.f)
			{
				State = TEXT("WINDUP");
				Windup -= Dt;
				Glow = 1.f - FMath::Max(Windup, 0.f) / WindupTime;
				if (Windup < 0.f)
				{
					++Attacks;
					Cooldown = bKnight ? 1.7f : 1.1f;
					Flash = 0.6f;
					if (Dist < Reach + 60.f) Strike(Who, Power * 10.f);   // stepped out of the slam: no hit
				}
			}
			else if (Dist < Reach)
			{
				if (Cooldown <= 0.f) Windup = WindupTime = bKnight ? 0.65f : 0.3f;
			}
			else
			{
				const float Speed = bKnight ? 240.f : 300.f;
				RouteAge += Dt;
				if (UDaedalusNav* Nav = GetWorld()->GetSubsystem<UDaedalusNav>())
				{
					const FVector Feet(Home.X, Home.Y, Home.Z - HoverOffset());
					const FVector Goal = Who->GetActorLocation() - FVector(0.f, 0.f, 90.f);
					if (RouteAge > 0.6f || Route.Num() == 0 || FVector::Dist2D(Goal, RouteGoal) > 250.f)
					{
						RouteAge = 0.f;
						RouteGoal = Goal;
						bRouted = Nav->FindPath(Feet, Goal, Route);
						RouteStep = Route.Num() > 1 ? 1 : 0;
						if (bRouted) ++Routes;
					}
				}
				if (bRouted && Route.IsValidIndex(RouteStep))
				{
					if (FVector::Dist2D(Route[RouteStep], Home) < 45.f && RouteStep < Route.Num() - 1) ++RouteStep;
					StepToward(Route[RouteStep] - Home, Speed, Dt);
				}
				else if (Flat < 400.f)
				{
					StepToward(Dir, Speed, Dt);   // close: go straight
				}
				else
				{
					State = TEXT("LOST");   // no way there on foot (another tier, another island): wait
				}
			}
			if (!bKnight) Bob = FMath::Abs(FMath::Sin(Age * 7.f)) * 45.f;   // the slime hops
			else Bob *= 0.15f;
		}
	}

	SetActorLocation(Home + FVector(0.f, 0.f, Bob));
	if (Mat)
	{
		Flash = FMath::Max(0.f, Flash - Dt * 6.f);
		const FLinearColor Tint = FMath::Lerp(BaseTint, Telegraph * 2.f, Glow);
		Mat->SetVectorParameterValue(TEXT("Color"), FMath::Lerp(Tint, FLinearColor(1.f, 1.f, 1.f), Flash));
	}
}

float ADaedalusTarget::TakeDamage(float Damage, const FDamageEvent& Event, AController* EventInstigator, AActor* DamageCauser)
{
	if (Dying >= 0.f) return 0.f;
	Health -= Damage;
	StartScale = GetActorScale3D();
	Flash = 1.f;
	SightCheck = 0.f;   // being shot wakes it
	if (Health <= 0.f)
	{
		Dying = 0.f;
		SetActorEnableCollision(false);
	}
	return Damage;
}
