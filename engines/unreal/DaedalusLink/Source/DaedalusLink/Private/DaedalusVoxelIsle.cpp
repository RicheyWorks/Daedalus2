// SPDX-License-Identifier: MIT

#include "DaedalusVoxelIsle.h"

#include "Components/HierarchicalInstancedStaticMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "UObject/ConstructorHelpers.h"

namespace
{
	enum ELayer : int32 { Grass, Sand, Dirt, Stone, Heart, Meadow, Count };
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

float ADaedalusVoxelIsle::Noise(float X, float Y, int32 Salt) const
{
	// Value noise on an integer lattice, smoothly interpolated; the same for a given seed everywhere.
	auto Hash = [this, Salt](int32 IX, int32 IY)
	{
		uint32 H = static_cast<uint32>(IX) * 374761393u + static_cast<uint32>(IY) * 668265263u
			+ static_cast<uint32>(Seed) * 2246822519u + static_cast<uint32>(Salt) * 3266489917u;
		H = (H ^ (H >> 13)) * 1274126177u;
		return static_cast<float>((H ^ (H >> 16)) & 0xFFFF) / 65535.f;
	};
	const int32 X0 = FMath::FloorToInt(X), Y0 = FMath::FloorToInt(Y);
	const float FX = X - X0, FY = Y - Y0;
	const float SX = FX * FX * (3.f - 2.f * FX), SY = FY * FY * (3.f - 2.f * FY);
	const float A = FMath::Lerp(Hash(X0, Y0), Hash(X0 + 1, Y0), SX);
	const float B = FMath::Lerp(Hash(X0, Y0 + 1), Hash(X0 + 1, Y0 + 1), SX);
	return FMath::Lerp(A, B, SY);
}

bool ADaedalusVoxelIsle::InPond(int32 X, int32 Y) const
{
	if (PondRadius <= 0) return false;
	const float R = PondRadius * (0.85f + 0.3f * Noise(X * 0.15f, Y * 0.15f, 9));
	return FVector2D(X - PondAt.X, Y - PondAt.Y).Size() < R;
}

int32 ADaedalusVoxelIsle::ColumnTop(int32 X, int32 Y) const
{
	const float R = FVector2D(X, Y).Size();
	const float Ang = FMath::Atan2(static_cast<float>(Y), static_cast<float>(X));
	const float Edge = Radius * (0.84f + 0.16f * Noise(FMath::Cos(Ang) * 3.f + 10.f, FMath::Sin(Ang) * 3.f + 10.f, 1));
	if (R >= Edge) return INT32_MIN;
	const float T = 1.f - R / Edge;                                        // 1 at the centre, 0 at the rim
	float H = SummitHeight * FMath::Pow(T, 1.6f) + 2.5f * Noise(X * 0.07f, Y * 0.07f, 2) + 1.2f * Noise(X * 0.2f, Y * 0.2f, 3);
	H = FMath::FloorToFloat(H / 2.f) * 2.f;                                // gentle two-cube terraces
	if (InPond(X, Y)) return -2;
	return FMath::Max(0, static_cast<int32>(H));
}

int32 ADaedalusVoxelIsle::ColumnBottom(int32 X, int32 Y) const
{
	const float R = FVector2D(X, Y).Size();
	const float T = FMath::Clamp(1.f - R / Radius, 0.f, 1.f);
	return -3 - static_cast<int32>(Depth * FMath::Pow(T, 1.1f) * (0.8f + 0.4f * Noise(X * 0.1f, Y * 0.1f, 4)));
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
	int32 Columns = 0;
	// Each column's top and bottom, so neighbours can be checked cheaply.
	const int32 N = Radius + 2;
	const int32 W = 2 * N + 1;
	TArray<int32> Tops, Bottoms;
	Tops.Init(INT32_MIN, W * W);
	Bottoms.Init(0, W * W);
	for (int32 Y = -N; Y <= N; ++Y)
		for (int32 X = -N; X <= N; ++X)
		{
			const int32 I = (Y + N) * W + (X + N);
			Tops[I] = ColumnTop(X, Y);
			if (Tops[I] != INT32_MIN) Bottoms[I] = ColumnBottom(X, Y);
		}
	auto Top = [&](int32 X, int32 Y) { return (X < -N || X > N || Y < -N || Y > N) ? INT32_MIN : Tops[(Y + N) * W + (X + N)]; };
	auto Bot = [&](int32 X, int32 Y) { return (X < -N || X > N || Y < -N || Y > N) ? 0 : Bottoms[(Y + N) * W + (X + N)]; };
	for (int32 Y = -N; Y <= N; ++Y)
		for (int32 X = -N; X <= N; ++X)
		{
			const int32 T = Top(X, Y);
			if (T == INT32_MIN) continue;
			++Columns;
			const int32 B = Bot(X, Y);
			// Sand only on a narrow beach: within two cubes of the rim, and round the pond.
			bool bShore = InPond(X, Y) || (PondRadius > 0 && FVector2D(X - PondAt.X, Y - PondAt.Y).Size() < PondRadius + 2.5f);
			for (int32 k = 0; k < 4 && !bShore; ++k)
				bShore = Top(X + (k == 0 ? 2 : k == 1 ? -2 : 0), Y + (k == 2 ? 2 : k == 3 ? -2 : 0)) == INT32_MIN;
			for (int32 Z = B; Z <= T; ++Z)
			{
				// Only cubes with an open face: the top, the bottom, and sides beside a shorter or missing column.
				bool bOpen = Z == T || Z == B;
				const int32 NX[] = {1, -1, 0, 0}, NY[] = {0, 0, 1, -1};
				for (int32 k = 0; k < 4 && !bOpen; ++k)
				{
					const int32 NT = Top(X + NX[k], Y + NY[k]);
					bOpen = NT == INT32_MIN || NT < Z || Bot(X + NX[k], Y + NY[k]) > Z;
				}
				if (!bOpen) continue;
				int32 L = Stone;
				if (Z == T) L = bShore ? Sand : (Noise(X * 0.09f, Y * 0.09f, 7) > 0.55f ? Meadow : Grass);
				else if (Z >= T - 2) L = Dirt;
				if (Z <= B + 1 && FVector2D(X, Y).Size() < 4.f) L = Heart;   // the glowing tip that holds the isle up
				Out[L].Add(FTransform(FRotator::ZeroRotator, FVector((X + 0.5f) * C, (Y + 0.5f) * C, (Z + 0.5f) * C), Scale));
			}
		}
	int32 Cubes = 0;
	for (int32 L = 0; L < Count; ++L)
	{
		UHierarchicalInstancedStaticMeshComponent* H = Layer(L, Colors[L], L == Heart);
		H->ClearInstances();
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
	LastStats = FString::Printf(TEXT("cubes=%d columns=%d radius=%d"), Cubes, Columns, Radius);
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
