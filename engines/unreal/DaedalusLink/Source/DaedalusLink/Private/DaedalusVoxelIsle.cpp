// SPDX-License-Identifier: MIT

#include "DaedalusVoxelIsle.h"

#include "DaedalusVoxelIsleCore.h"

#include "Components/HierarchicalInstancedStaticMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "UObject/ConstructorHelpers.h"

namespace
{
	// The shape lives in DaedalusVoxelIsleCore.h (tested in core-test, mirrored in Java for the web realm).
	enum ELayer : int32 { Grass = daedalus::isle::Grass, Sand, Dirt, Stone, Heart, Meadow, Count };
	const TCHAR* LayerNames[] = {TEXT("Grass"), TEXT("Sand"), TEXT("Dirt"), TEXT("Stone"), TEXT("Heart"), TEXT("Meadow")};
}

ADaedalusVoxelIsle::ADaedalusVoxelIsle()
{
	PrimaryActorTick.bCanEverTick = false;
	RootComponent = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
	static ConstructorHelpers::FObjectFinder<UStaticMesh> Cube(TEXT("/Engine/BasicShapes/Cube.Cube"));
	static ConstructorHelpers::FObjectFinder<UStaticMesh> Cyl(TEXT("/Engine/BasicShapes/Cylinder.Cylinder"));
	for (int32 i = 0; i < Count; ++i)
	{
		UHierarchicalInstancedStaticMeshComponent* H = CreateDefaultSubobject<UHierarchicalInstancedStaticMeshComponent>(LayerNames[i]);
		H->SetupAttachment(RootComponent);
		H->SetStaticMesh(Cube.Object);
		H->SetCollisionProfileName(TEXT("BlockAll"));
		H->SetCullDistances(0, 80000);
		IsleLayers.Add(H);
	}
	PondWater = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("PondWater"));
	PondWater->SetupAttachment(RootComponent);
	PondWater->SetStaticMesh(Cyl.Object);
	PondWater->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Falls = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Falls"));
	Falls->SetupAttachment(RootComponent);
	Falls->SetStaticMesh(Cube.Object);
	Falls->SetCollisionEnabled(ECollisionEnabled::NoCollision);
}

void ADaedalusVoxelIsle::OnConstruction(const FTransform& Transform)
{
	Super::OnConstruction(Transform);
	Build();
}

static daedalus::isle::Params IsleParams(const ADaedalusVoxelIsle& I)
{
	daedalus::isle::Params P;
	P.Seed = I.Seed;
	P.Radius = I.Radius;
	P.SummitHeight = I.SummitHeight;
	P.Depth = I.Depth;
	P.PondX = I.PondAt.X;
	P.PondY = I.PondAt.Y;
	P.PondRadius = I.PondRadius;
	return P;
}

float ADaedalusVoxelIsle::Noise(float X, float Y, int32 Salt) const
{
	return static_cast<float>(daedalus::isle::Noise(IsleParams(*this), X, Y, Salt));
}

bool ADaedalusVoxelIsle::InPond(int32 X, int32 Y) const
{
	return daedalus::isle::InPond(IsleParams(*this), X, Y);
}

int32 ADaedalusVoxelIsle::ColumnTop(int32 X, int32 Y) const
{
	const int T = daedalus::isle::ColumnTop(IsleParams(*this), X, Y);
	return T == daedalus::isle::Off ? INT32_MIN : T;
}

int32 ADaedalusVoxelIsle::ColumnBottom(int32 X, int32 Y) const
{
	return daedalus::isle::ColumnBottom(IsleParams(*this), X, Y);
}

UHierarchicalInstancedStaticMeshComponent* ADaedalusVoxelIsle::Layer(int32 Index, const FLinearColor& Color, bool bGlow)
{
	UHierarchicalInstancedStaticMeshComponent* H = IsleLayers[Index];
	if (UMaterialInterface* Base = LoadObject<UMaterialInterface>(nullptr, TEXT("/Engine/BasicShapes/BasicShapeMaterial.BasicShapeMaterial")))
	{
		UMaterialInstanceDynamic* M = UMaterialInstanceDynamic::Create(Base, this);
		M->SetVectorParameterValue(TEXT("Color"), bGlow ? Color * 4.f : Color);
		H->SetMaterial(0, M);
	}
	return H;
}

FString ADaedalusVoxelIsle::Build()
{
	if (IsleLayers.Num() < Count)
	{
		// Recover the layers from the components themselves (they are default subobjects, named after their layer).
		IsleLayers.Reset();
		TArray<UHierarchicalInstancedStaticMeshComponent*> Found;
		GetComponents(Found);
		for (int32 i = 0; i < Count; ++i)
			for (UHierarchicalInstancedStaticMeshComponent* H : Found)
				if (H->GetFName() == FName(LayerNames[i])) IsleLayers.Add(H);
		if (IsleLayers.Num() < Count) return LastStats = TEXT("layers missing; re-place the isle");
	}
	const FLinearColor Colors[] = {GrassColor, SandColor, DirtColor, StoneColor, HeartColor,
		FLinearColor(GrassColor.R * 1.25f + 0.04f, GrassColor.G * 1.18f, GrassColor.B * 0.8f)};
	TArray<TArray<FTransform>> Out;
	Out.SetNum(Count);
	const float C = CubeSize;
	const FVector Scale(C / 100.f);
	const int32 Columns = daedalus::isle::Build(IsleParams(*this), [&](int X, int Y, int Z, daedalus::isle::Layer L)
	{
		Out[L].Add(FTransform(FRotator::ZeroRotator, FVector((X + 0.5f) * C, (Y + 0.5f) * C, (Z + 0.5f) * C), Scale));
	});
	int32 Cubes = 0;
	for (int32 L = 0; L < Count; ++L)
	{
		UHierarchicalInstancedStaticMeshComponent* H = Layer(L, Colors[L], L == Heart);
		H->ClearInstances();
		const bool bRock = L == Stone || L == Heart;
		H->SetCollisionEnabled(bRock && !bRockCollision ? ECollisionEnabled::NoCollision : ECollisionEnabled::QueryAndPhysics);
		H->AddInstances(Out[L], false);
		Cubes += Out[L].Num();
	}
	// The pond's water, and a waterfall where its stream leaves the rim.
	if (UMaterialInterface* Base = LoadObject<UMaterialInterface>(nullptr, TEXT("/Engine/BasicShapes/BasicShapeMaterial.BasicShapeMaterial")))
	{
		UMaterialInstanceDynamic* M = UMaterialInstanceDynamic::Create(Base, this);
		M->SetVectorParameterValue(TEXT("Color"), WaterColor);
		PondWater->SetMaterial(0, M);
		Falls->SetMaterial(0, M);
	}
	PondWater->SetVisibility(PondRadius > 0);
	Falls->SetVisibility(PondRadius > 0);
	if (PondRadius > 0)
	{
		PondWater->SetRelativeLocation(FVector(PondAt.X * C, PondAt.Y * C, -0.6f * C));
		PondWater->SetRelativeScale3D(FVector(PondRadius * 2.1f * C / 100.f, PondRadius * 2.1f * C / 100.f, 0.02f));
		const FVector2D Out2 = FVector2D(PondAt.X, PondAt.Y).GetSafeNormal();
		const float Edge = Radius * 0.95f;
		Falls->SetRelativeLocation(FVector(Out2.X * Edge * C, Out2.Y * Edge * C, -Depth * 0.35f * C));
		Falls->SetRelativeScale3D(FVector(4.f * C / 100.f, 4.f * C / 100.f, Depth * 0.7f * C / 100.f));
	}
	int32 Solid = 0;
	for (int32 L = 0; L < Count; ++L)
		if (bRockCollision || (L != Stone && L != Heart)) Solid += Out[L].Num();
	LastStats = FString::Printf(TEXT("cubes=%d columns=%d radius=%d colliding=%d"), Cubes, Columns, Radius, Solid);
	return LastStats;
}

float ADaedalusVoxelIsle::TopZ(float X, float Y) const
{
	const FVector L = GetActorLocation();
	const int32 CX = FMath::FloorToInt((X - L.X) / CubeSize), CY = FMath::FloorToInt((Y - L.Y) / CubeSize);
	const int32 T = ColumnTop(CX, CY);
	return T == INT32_MIN ? L.Z : L.Z + (T + 1) * CubeSize;
}

bool ADaedalusVoxelIsle::IsLand(float X, float Y) const
{
	const FVector L = GetActorLocation();
	const int32 CX = FMath::FloorToInt((X - L.X) / CubeSize), CY = FMath::FloorToInt((Y - L.Y) / CubeSize);
	return ColumnTop(CX, CY) != INT32_MIN && !InPond(CX, CY);
}
