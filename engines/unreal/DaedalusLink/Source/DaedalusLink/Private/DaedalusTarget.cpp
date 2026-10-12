// SPDX-License-Identifier: MIT

#include "DaedalusTarget.h"

#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "UObject/ConstructorHelpers.h"

ADaedalusTarget::ADaedalusTarget()
{
	PrimaryActorTick.bCanEverTick = true;
	static ConstructorHelpers::FObjectFinder<UStaticMesh> Shape(TEXT("/Engine/BasicShapes/Cone.Cone"));
	Crystal = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Crystal"));
	RootComponent = Crystal;
	Crystal->SetStaticMesh(Shape.Object);
	Crystal->SetRelativeScale3D(FVector(0.9f, 0.9f, 1.4f));
	Crystal->SetCollisionProfileName(TEXT("BlockAllDynamic"));
	Crystal->SetMobility(EComponentMobility::Movable);
	Tags.Add(TEXT("DaedalusTarget"));
}

void ADaedalusTarget::BeginPlay()
{
	Super::BeginPlay();
	Home = GetActorLocation();
	// Each kind its own look: the slime green and low, the shardback stony, the wisp pale and high, the knight dark.
	FLinearColor Tint(0.85f, 0.2f, 0.9f);
	if (Kind == TEXT("BLIGHT_SLIME")) { Tint = FLinearColor(0.35f, 0.85f, 0.25f); SetActorScale3D(FVector(1.1f, 1.1f, 0.6f)); }
	else if (Kind == TEXT("SHARDBACK")) { Tint = FLinearColor(0.45f, 0.55f, 0.75f); SetActorScale3D(FVector(1.3f)); }
	else if (Kind == TEXT("DUST_WISP")) { Tint = FLinearColor(0.85f, 0.95f, 1.f); SetActorScale3D(FVector(0.7f)); Home.Z += 120.f; }
	else if (Kind == TEXT("STONE_KNIGHT")) { Tint = FLinearColor(0.25f, 0.25f, 0.3f); SetActorScale3D(FVector(1.2f, 1.2f, 2.0f)); }
	BaseTint = Tint;
	if (UMaterialInterface* Base = LoadObject<UMaterialInterface>(nullptr, TEXT("/Engine/BasicShapes/BasicShapeMaterial.BasicShapeMaterial")))
	{
		Mat = UMaterialInstanceDynamic::Create(Base, this);
		Mat->SetVectorParameterValue(TEXT("Color"), BaseTint);
		Crystal->SetMaterial(0, Mat);
	}
}

void ADaedalusTarget::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	Age += DeltaSeconds;
	if (Dying >= 0.f)
	{
		// Shatter: swell and vanish over a fifth of a second.
		Dying += DeltaSeconds;
		SetActorScale3D(StartScale * (1.f + Dying * 6.f));
		if (Dying > 0.2f) Destroy();
		return;
	}
	SetActorLocation(Home + FVector(0.f, 0.f, FMath::Sin(Age * 2.f) * 40.f));
	AddActorLocalRotation(FRotator(0.f, 60.f * DeltaSeconds, 0.f));
	if (Mat)
	{
		Flash = FMath::Max(0.f, Flash - DeltaSeconds * 6.f);
		Mat->SetVectorParameterValue(TEXT("Color"), FMath::Lerp(BaseTint, FLinearColor(1.f, 1.f, 1.f), Flash));
	}
}

float ADaedalusTarget::TakeDamage(float Damage, const FDamageEvent& Event, AController* EventInstigator, AActor* DamageCauser)
{
	if (Dying >= 0.f) return 0.f;
	Health -= Damage;
	StartScale = GetActorScale3D();
	Flash = 1.f;
	if (Health <= 0.f)
	{
		Dying = 0.f;
		SetActorEnableCollision(false);
	}
	return Damage;
}
