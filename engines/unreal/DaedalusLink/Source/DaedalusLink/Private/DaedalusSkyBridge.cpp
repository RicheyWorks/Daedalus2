// SPDX-License-Identifier: MIT

#include "DaedalusSkyBridge.h"

#include "Components/InstancedStaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "UObject/ConstructorHelpers.h"

ADaedalusSkyBridge::ADaedalusSkyBridge()
{
	PrimaryActorTick.bCanEverTick = false;
	RootComponent = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
	static ConstructorHelpers::FObjectFinder<UStaticMesh> Cube(TEXT("/Engine/BasicShapes/Cube.Cube"));
	Planks = CreateDefaultSubobject<UInstancedStaticMeshComponent>(TEXT("Planks"));
	Planks->SetupAttachment(RootComponent);
	Planks->SetStaticMesh(Cube.Object);
	Planks->SetCollisionProfileName(TEXT("BlockAll"));
	Ropes = CreateDefaultSubobject<UInstancedStaticMeshComponent>(TEXT("Ropes"));
	Ropes->SetupAttachment(RootComponent);
	Ropes->SetStaticMesh(Cube.Object);
	Ropes->SetCollisionProfileName(TEXT("BlockAll"));   // the rails keep walkers on the deck
}

void ADaedalusSkyBridge::OnConstruction(const FTransform& Transform)
{
	Super::OnConstruction(Transform);
	Build();
}

FVector ADaedalusSkyBridge::PointAt(float T) const
{
	// Local space: start at the origin, end at End relative to the actor; a parabola stands in for the catenary.
	const FVector Rel = End - GetActorLocation();
	const float Span = Rel.Size2D();
	return Rel * T - FVector(0.f, 0.f, 4.f * Sag * Span * T * (1.f - T));
}

FString ADaedalusSkyBridge::Build()
{
	if (!Planks || !Ropes) return TEXT("no components");
	Planks->ClearInstances();
	Ropes->ClearInstances();
	if (UMaterialInterface* Base = LoadObject<UMaterialInterface>(nullptr, TEXT("/Engine/BasicShapes/BasicShapeMaterial.BasicShapeMaterial")))
	{
		UMaterialInstanceDynamic* P = UMaterialInstanceDynamic::Create(Base, this);
		P->SetVectorParameterValue(TEXT("Color"), PlankColor);
		Planks->SetMaterial(0, P);
		UMaterialInstanceDynamic* R = UMaterialInstanceDynamic::Create(Base, this);
		R->SetVectorParameterValue(TEXT("Color"), RopeColor);
		Ropes->SetMaterial(0, R);
	}
	const FVector Rel = End - GetActorLocation();
	const float Span = Rel.Size();
	if (Span < 100.f) return TEXT("too short");
	const int32 N = FMath::Clamp(FMath::CeilToInt(Span / 70.f), 2, 2000);
	const FVector Side = FVector::CrossProduct(Rel.GetSafeNormal(), FVector::UpVector).GetSafeNormal();
	for (int32 i = 0; i < N; ++i)
	{
		const float T0 = static_cast<float>(i) / N, T1 = static_cast<float>(i + 1) / N;
		const FVector A = PointAt(T0), B = PointAt(T1);
		const FVector Mid = (A + B) * 0.5f;
		const FRotator Rot = (B - A).Rotation();
		Planks->AddInstance(FTransform(Rot, Mid, FVector((B - A).Size() * 0.9f / 100.f, Width / 100.f, 0.08f)));
		// rails at hand height on both sides
		for (int32 s = -1; s <= 1; s += 2)
			Ropes->AddInstance(FTransform(Rot, Mid + Side * (Width * 0.5f * s) + FVector(0.f, 0.f, 95.f),
				FVector((B - A).Size() / 100.f, 0.05f, 0.05f)));
		if (i % 6 == 0)   // a post every few planks, holding the rails up
			for (int32 s = -1; s <= 1; s += 2)
				Ropes->AddInstance(FTransform(FRotator::ZeroRotator, A + Side * (Width * 0.5f * s) + FVector(0.f, 0.f, 48.f),
					FVector(0.08f, 0.08f, 1.0f)));
	}
	return FString::Printf(TEXT("planks=%d span=%.0fm"), N, Span / 100.f);
}
