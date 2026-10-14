// SPDX-License-Identifier: MIT

#include "DaedalusTarget.h"
#include "AssetRegistry/AssetRegistryModule.h"
#include "Animation/AnimSequence.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"

#include "DaedalusTactics.h"

#include "Components/StaticMeshComponent.h"
#include "DaedalusMob.h"
#include "DaedalusNav.h"
#include "DaedalusPickup.h"
#include "Engine/StaticMesh.h"
#include "Engine/StaticMeshActor.h"
#include "Engine/World.h"
#include "Camera/PlayerCameraManager.h"
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

	static ConstructorHelpers::FObjectFinder<UStaticMesh> Box(TEXT("/Engine/BasicShapes/Cube.Cube"));
	for (TObjectPtr<UStaticMeshComponent>* Bar : {&BarBack, &BarFill})
	{
		*Bar = CreateDefaultSubobject<UStaticMeshComponent>(Bar == &BarBack ? TEXT("BarBack") : TEXT("BarFill"));
		(*Bar)->SetupAttachment(Crystal);
		(*Bar)->SetStaticMesh(Box.Object);
		(*Bar)->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		(*Bar)->SetCastShadow(false);
		(*Bar)->SetUsingAbsoluteLocation(true);
		(*Bar)->SetUsingAbsoluteRotation(true);
		(*Bar)->SetUsingAbsoluteScale(true);
		(*Bar)->SetHiddenInGame(true);
	}
}

// A bar over the head that faces the camera: dark back, red fill from the left.
void ADaedalusTarget::TickBar()
{
	const bool bShow = IsBarShown();
	BarBack->SetHiddenInGame(!bShow);
	BarFill->SetHiddenInGame(!bShow);
	if (!bShow) return;
	const APlayerCameraManager* Cam = UGameplayStatics::GetPlayerCameraManager(this, 0);
	const float Yaw = Cam ? Cam->GetCameraRotation().Yaw : 0.f;
	const FRotator Face(0.f, Yaw + 90.f, 0.f);
	const FVector Across = Face.Vector();
	const float Top = TopAbove();
	const FVector Mid = GetActorLocation() + FVector(0.f, 0.f, Top + 45.f);
	const float Frac = FMath::Clamp(Health / FMath::Max(MaxHealth, 1.f), 0.f, 1.f);
	BarBack->SetWorldLocationAndRotation(Mid, Face);
	BarBack->SetWorldScale3D(FVector(1.2f, 0.05f, 0.12f));
	BarFill->SetWorldLocationAndRotation(Mid - Across * (120.f * (1.f - Frac) * 0.5f) - Face.RotateVector(FVector(0.f, 3.f, 0.f)), Face);
	BarFill->SetWorldScale3D(FVector(FMath::Max(1.2f * Frac, 0.01f), 0.06f, 0.10f));
}

float ADaedalusTarget::HoverOffset() const
{
	if (Kind == TEXT("DUST_WISP")) return 260.f;
	if (Kind == TEXT("STONE_KNIGHT")) return 100.f;
	if (Kind == TEXT("SHARDBACK")) return 65.f;
	return 45.f;
}

FString ADaedalusTarget::ArtFor(const FString& InKind)
{
	if (InKind == TEXT("SHARDBACK")) return TEXT("Mob_Shardback");
	if (InKind == TEXT("DUST_WISP")) return TEXT("Mob_DustWisp");
	if (InKind == TEXT("STONE_KNIGHT")) return TEXT("Mob_StoneKnight");
	return TEXT("Mob_BlightSlime");
}

// ADR-055: wear the shipped creature. The crystal stays as the (hidden) collision shape, so every hit, trace and
// sight line works as before; a small inverted crystal over the head keeps the kind's colour and the orange
// telegraph, so attacks still read at a glance.
// A realm creature (bestiary): Sol's rigged export under /Game/Daedalus/Art/Creatures/<id>/, Idle looping.
// Returns 1 when the mesh was found (the "parts" count DressArt expects), 0 to fall back to the crystal.
int32 ADaedalusTarget::DressSkeletal()
{
	FAssetRegistryModule& Reg = FModuleManager::LoadModuleChecked<FAssetRegistryModule>("AssetRegistry");
	TArray<FAssetData> Found;
	Reg.Get().GetAssetsByPath(FName(*(TEXT("/Game/Daedalus/Art/Creatures/") + SkeletalArt)), Found, true);
	USkeletalMesh* Mesh = nullptr;
	UAnimSequence* Idle = nullptr;
	for (const FAssetData& D : Found)
	{
		if (D.AssetClassPath.GetAssetName() == USkeletalMesh::StaticClass()->GetFName() && !Mesh) Mesh = Cast<USkeletalMesh>(D.GetAsset());
		if (D.AssetClassPath.GetAssetName() == UAnimSequence::StaticClass()->GetFName() && (!Idle || D.AssetName.ToString().Contains(TEXT("Idle")))) Idle = Cast<UAnimSequence>(D.GetAsset());
	}
	if (!Mesh) return 0;
	SkinMesh = NewObject<USkeletalMeshComponent>(this, TEXT("SkinMesh"));
	SkinMesh->SetMobility(EComponentMobility::Movable);
	SkinMesh->SetupAttachment(Look);
	SkinMesh->SetSkeletalMesh(Mesh);
	SkinMesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	SkinMesh->RegisterComponent();
	AddInstanceComponent(SkinMesh);
	if (Idle) { SkinMesh->SetAnimationMode(EAnimationMode::AnimationSingleNode); Hide->PlayAnimation(Idle, true); }
	ArtHeight = Mesh->GetBounds().BoxExtent.Z * 2.f;
	return 1;
}

void ADaedalusTarget::DressArt()
{
	Look = NewObject<USceneComponent>(this, TEXT("Look"));
	Look->SetMobility(EComponentMobility::Movable);
	Look->SetupAttachment(Crystal);
	Look->SetUsingAbsoluteLocation(true);
	Look->SetUsingAbsoluteScale(true);
	Look->SetRelativeRotation(FRotator(0.f, -90.f, 0.f));   // the art faces +Y; actors face +X
	Look->RegisterComponent();
	AddInstanceComponent(Look);
	ArtParts = SkeletalArt.IsEmpty() ? DaedalusMob::Build(this, Look, ArtFor(Kind), nullptr, &ArtHeight) : DressSkeletal();
	if (ArtParts == 0)
	{
		Look->DestroyComponent();
		Look = nullptr;
		return;
	}
	ArtScale = Kind == TEXT("BLIGHT_SLIME") ? 1.7f : Kind == TEXT("SHARDBACK") ? 1.35f : Kind == TEXT("DUST_WISP") ? 1.6f : 1.f;
	Look->SetWorldScale3D(FVector(ArtScale));
	Crystal->SetHiddenInGame(true);   // collision stays; only the drawing goes

	Gem = NewObject<UStaticMeshComponent>(this, TEXT("Gem"));
	Gem->SetStaticMesh(Crystal->GetStaticMesh());
	Gem->SetMobility(EComponentMobility::Movable);
	Gem->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Gem->SetCastShadow(false);
	Gem->SetupAttachment(Look);
	Gem->SetRelativeLocationAndRotation(FVector(0.f, 0.f, ArtHeight + 30.f / ArtScale), FRotator(180.f, 0.f, 0.f));
	Gem->SetRelativeScale3D(FVector(0.22f, 0.22f, 0.3f) / ArtScale);
	Gem->RegisterComponent();
	AddInstanceComponent(Gem);
}

float ADaedalusTarget::TopAbove() const
{
	if (!Look) return Crystal->Bounds.BoxExtent.Z;
	return Look->GetComponentLocation().Z + ArtHeight * ArtScale + 50.f - GetActorLocation().Z;
}

// Keep the art on the ground under the (hovering) collision shape; the wisp floats, centred on it.
void ADaedalusTarget::TickArt(float Glow)
{
	if (!Look) return;
	const float Drop = Kind == TEXT("DUST_WISP") ? ArtHeight * ArtScale * 0.5f : HoverOffset();
	Look->SetWorldLocation(GetActorLocation() - FVector(0.f, 0.f, Drop));
	float S = ArtScale * (1.f + Flash * 0.12f + Glow * 0.08f);   // a flinch when hit, a swell as it winds up
	if (Dying >= 0.f) S = ArtScale * FMath::Max(0.05f, 1.f - Dying * 4.5f);
	Look->SetWorldScale3D(FVector(S));
	if (Gem) Gem->AddLocalRotation(FRotator(0.f, 90.f * GetWorld()->GetDeltaSeconds(), 0.f));
}

void ADaedalusTarget::BeginPlay()
{
	Super::BeginPlay();
	Home = GetActorLocation();
	// Each kind its own look: the slime green and low, the shardback stony, the wisp pale and high, the knight dark.
	FLinearColor Tint(0.85f, 0.2f, 0.9f);
	if (Kind == TEXT("BLIGHT_SLIME")) { Tint = FLinearColor(0.35f, 0.85f, 0.25f); SetActorScale3D(FVector(1.1f, 1.1f, 0.9f)); }
	else if (Kind == TEXT("SHARDBACK")) { Tint = FLinearColor(0.45f, 0.55f, 0.75f); SetActorScale3D(FVector(1.3f)); }
	else if (Kind == TEXT("DUST_WISP")) { Tint = FLinearColor(0.85f, 0.95f, 1.f); SetActorScale3D(FVector(0.7f)); }
	else if (Kind == TEXT("STONE_KNIGHT")) { Tint = FLinearColor(0.25f, 0.25f, 0.3f); SetActorScale3D(FVector(1.2f, 1.2f, 2.0f)); }
	BaseTint = Tint;
	StartScale = GetActorScale3D();
	MaxHealth = Health;
	if (UMaterialInterface* Base = FoeMaterial())
	{
		UMaterialInstanceDynamic* Back = UMaterialInstanceDynamic::Create(Base, this);
		Back->SetVectorParameterValue(TEXT("Color"), FLinearColor(0.05f, 0.05f, 0.06f));
		BarBack->SetMaterial(0, Back);
		UMaterialInstanceDynamic* Fill = UMaterialInstanceDynamic::Create(Base, this);
		Fill->SetVectorParameterValue(TEXT("Color"), FLinearColor(1.f, 0.15f, 0.1f) * 2.f);
		BarFill->SetMaterial(0, Fill);
	}
	if (FoeMaterial())
	{
		Mat = UMaterialInstanceDynamic::Create(FoeMaterial(), this);
		Mat->SetVectorParameterValue(TEXT("Color"), BaseTint);
		Crystal->SetMaterial(0, Mat);
	}
	DressArt();
	if (Gem && Mat) Gem->SetMaterial(0, Mat);
	if (bShiny) { bShiny = false; MakeShiny(); }
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
	if (bShiny) DaedalusShiny::Tick(Shiny, DeltaSeconds);
	Super::Tick(DeltaSeconds);
	const float Dt = FMath::Min(DeltaSeconds, 0.1f);
	Age += Dt;
	if (Dying >= 0.f)
	{
		// Shatter: swell and vanish over a fifth of a second.
		State = TEXT("DYING");
		Dying += Dt;
		if (Look) TickArt(0.f);   // the creature shrinks away
		else SetActorScale3D(StartScale * (1.f + Dying * 6.f));
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

	// Squad orders (ADR-060). Moving orders (RETREAT; FLANK, REINFORCE and DEFEND until there) take over the feet and
	// stop attacks. FLANK and REINFORCE end on arrival, and the foe hunts from its new spot. HOLD and DEFEND only fight
	// a player who comes close. ATTACK is the foe's own hunting.
	OrderLeft = FMath::Max(0.f, OrderLeft - Dt);
	if (OrderLeft <= 0.f && !OrderVerb.IsEmpty()) { OrderVerb.Reset(); OrderWhy.Reset(); }
	const FVector ToGoal(OrderPoint.X - Home.X, OrderPoint.Y - Home.Y, 0.f);
	const bool bThere = ToGoal.Size() < 200.f;
	const bool bMoveOrder = OrderVerb == TEXT("RETREAT") || OrderVerb == TEXT("FLANK") || OrderVerb == TEXT("REINFORCE") || OrderVerb == TEXT("DEFEND");
	if (bThere && (OrderVerb == TEXT("FLANK") || OrderVerb == TEXT("REINFORCE"))) OrderLeft = 0.f;   // in position: now hunt
	const bool bMoving = bMoveOrder && !bThere && OrderLeft > 0.f;
	const bool bStayPut = (OrderVerb == TEXT("HOLD") || OrderVerb == TEXT("DEFEND") || OrderVerb == TEXT("RETREAT")) && Dist > 900.f;

	float Bob = FMath::Sin(Age * 2.f) * 40.f;
	float Glow = 0.f;
	if (bMoving)
	{
		State = OrderVerb;
		Windup = -1.f;
		ChargeLeft = 0.f;
		SetActorRotation(FRotator(0.f, ToGoal.Rotation().Yaw, 0.f));
		const float Speed = Kind == TEXT("DUST_WISP") ? 360.f : Kind == TEXT("SHARDBACK") ? 380.f : Kind == TEXT("STONE_KNIGHT") ? 240.f : 300.f;
		if (!StepToward(ToGoal, OrderVerb == TEXT("RETREAT") ? Speed * 1.15f : Speed, Dt)) OrderLeft = 0.f;   // blocked: fight alone
		if (Kind == TEXT("BLIGHT_SLIME")) Bob = FMath::Abs(FMath::Sin(Age * 7.f)) * 45.f;
	}
	else if (!bHunting || bStayPut)
	{
		State = TEXT("IDLE");
		Windup = -1.f;
		ChargeLeft = 0.f;
		if (Look) SetActorRotation(FRotator(0.f, GetActorRotation().Yaw + FMath::Sin(Age * 0.6f) * 25.f * Dt, 0.f));   // looks about
		else AddActorLocalRotation(FRotator(0.f, 60.f * Dt, 0.f));
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
					// Re-plan when the route is stale or the player has moved; after a failed search wait longer, so a
					// foe with no way across doesn't run A* every frame (it did: 1,752 searches in a minute).
					const float Every = bRouted ? 0.6f : 1.5f;
					if (RouteAge > Every || (bRouted && FVector::Dist2D(Goal, RouteGoal) > 250.f))
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
	TickArt(Glow);
	SinceHurt += Dt;
	TickBar();
	if (Mat)
	{
		Flash = FMath::Max(0.f, Flash - Dt * 6.f);
		const FLinearColor Tint = FMath::Lerp(BaseTint, Telegraph * 2.f, Glow);
		Mat->SetVectorParameterValue(TEXT("Color"), FMath::Lerp(Tint, FLinearColor(1.f, 1.f, 1.f), Flash));
	}
}

void ADaedalusTarget::SetOrder(const FString& Verb, FVector Point, const FString& Why, float Seconds)
{
	OrderVerb = Verb.ToUpper();
	OrderPoint = Point;
	OrderWhy = Why;
	OrderLeft = FMath::Clamp(Seconds, 0.f, 30.f);
}

float ADaedalusTarget::TakeDamage(float Damage, const FDamageEvent& Event, AController* EventInstigator, AActor* DamageCauser)
{
	if (Dying >= 0.f) return 0.f;
	Health -= Damage;
	if (!Squad.IsEmpty())
		if (UDaedalusTactics* Tac = GetWorld()->GetSubsystem<UDaedalusTactics>())
		{
			Tac->Note(Health <= 0.f ? TEXT("DOWN") : TEXT("HIT"), TacticalId(), GetActorLocation(), Health <= 0.f ? 0.f : Damage);
			if (Health <= 0.f) Tac->NoteDown(Squad, TacticalId(), Kind, MaxHealth, GetActorLocation());
		}
	StartScale = GetActorScale3D();
	Flash = 1.f;
	SinceHurt = 0.f;
	SightCheck = 0.f;   // being shot wakes it
	if (Health <= 0.f)
	{
		Dying = 0.f;
		SetActorEnableCollision(false);
		// Drops (ADR-047): knights always leave a shield core, shardbacks one time in four; anything, rarely, an overshield.
		const float Roll = FMath::FRand();
		if (Kind == TEXT("STONE_KNIGHT") || (Kind == TEXT("SHARDBACK") && Roll < 0.25f))
		{
			ADaedalusPickup::Drop(GetWorld(), GetActorLocation(), TEXT("CORE"));
		}
		else if (Roll > 0.95f)
		{
			ADaedalusPickup::Drop(GetWorld(), GetActorLocation(), TEXT("OVERSHIELD"));
		}
	}
	return Damage;
}

void ADaedalusTarget::MakeShiny()
{
	if (bShiny) return;
	bShiny = true;
	SetActorScale3D(GetActorScale3D() * DaedalusShiny::ScaleBoost);
	StartScale = GetActorScale3D();
	MaxHealth *= DaedalusShiny::StatBoost;
	Health *= DaedalusShiny::StatBoost;
	DaedalusShiny::Attach(this, Look ? Look.Get() : Crystal.Get(), FMath::Max(ArtHeight * ArtScale, 120.f), Shiny);
}
