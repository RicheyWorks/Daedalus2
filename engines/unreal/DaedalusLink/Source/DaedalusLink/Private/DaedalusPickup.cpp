// SPDX-License-Identifier: MIT

#include "DaedalusPickup.h"

#include "Components/StaticMeshComponent.h"
#include "DaedalusGhost.h"
#include "DaedalusHero.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "Kismet/GameplayStatics.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "UObject/ConstructorHelpers.h"

ADaedalusPickup::ADaedalusPickup()
{
	PrimaryActorTick.bCanEverTick = true;
	static ConstructorHelpers::FObjectFinder<UStaticMesh> Shape(TEXT("/Engine/BasicShapes/Cube.Cube"));
	Gem = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Gem"));
	RootComponent = Gem;
	Gem->SetStaticMesh(Shape.Object);
	Gem->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Gem->SetCastShadow(false);
	Gem->SetMobility(EComponentMobility::Movable);
	Gem->SetRelativeScale3D(FVector(0.35f));
	InitialLifeSpan = 60.f;
	Tags.Add(TEXT("DaedalusPickup"));
}

void ADaedalusPickup::BeginPlay()
{
	Super::BeginPlay();
	Home = GetActorLocation();
	if (UMaterialInterface* Base = LoadObject<UMaterialInterface>(nullptr, TEXT("/Engine/BasicShapes/BasicShapeMaterial.BasicShapeMaterial")))
	{
		Mat = UMaterialInstanceDynamic::Create(Base, this);
		const FLinearColor Color = Kind == TEXT("OVERSHIELD") ? FLinearColor(1.f, 0.75f, 0.15f) : FLinearColor(0.3f, 0.8f, 1.f);
		Mat->SetVectorParameterValue(TEXT("Color"), Color * 3.f);
		Gem->SetMaterial(0, Mat);
	}
	SetActorRotation(FRotator(45.f, 0.f, 45.f));
}

ADaedalusPickup* ADaedalusPickup::Drop(UWorld* World, const FVector& At, const FString& InKind)
{
	if (!World) return nullptr;
	FVector Spot = At;
	FHitResult Hit;
	if (World->LineTraceSingleByObjectType(Hit, At + FVector(0.f, 0.f, 100.f), At - FVector(0.f, 0.f, 800.f),
		FCollisionObjectQueryParams(ECC_WorldStatic), FCollisionQueryParams(SCENE_QUERY_STAT(DaedalusPickupDrop), false)))
	{
		Spot = Hit.ImpactPoint + FVector(0.f, 0.f, 70.f);
	}
	ADaedalusPickup* Pick = World->SpawnActorDeferred<ADaedalusPickup>(ADaedalusPickup::StaticClass(), FTransform(Spot), nullptr, nullptr,
		ESpawnActorCollisionHandlingMethod::AlwaysSpawn);
	if (!Pick) return nullptr;
	Pick->Kind = InKind;
	UGameplayStatics::FinishSpawningActor(Pick, FTransform(Spot));
	return Pick;
}

void ADaedalusPickup::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	Age += DeltaSeconds;
	SetActorLocation(Home + FVector(0.f, 0.f, FMath::Sin(Age * 3.f) * 15.f));
	AddActorWorldRotation(FRotator(0.f, 120.f * DeltaSeconds, 0.f));
	if (Mat && GetLifeSpan() > 0.f && GetLifeSpan() < 5.f)
	{
		Gem->SetVisibility(FMath::Fmod(Age * 6.f, 1.f) > 0.3f);   // blinks before it fades
	}

	// Picked up on foot or from a Ghost.
	APawn* P = UGameplayStatics::GetPlayerPawn(this, 0);
	ADaedalusHero* Hero = Cast<ADaedalusHero>(P);
	if (!Hero)
	{
		if (const ADaedalusGhost* Bike = Cast<ADaedalusGhost>(P)) Hero = Bike->Rider;
	}
	if (!Hero || !P || FVector::Dist(P->GetActorLocation(), GetActorLocation()) > 180.f) return;
	if (Kind == TEXT("OVERSHIELD")) Hero->GiveOvershield(100.f);
	else Hero->AddShieldCore();
	Destroy();
}
