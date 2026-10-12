// SPDX-License-Identifier: MIT

#include "DaedalusNav.h"

#include "Engine/World.h"

namespace
{
	constexpr float NoFloor = -1.0e9f;

	struct FNavNode
	{
		int32 Id;
		float G;
		float F;
	};

	struct FByF
	{
		bool operator()(const FNavNode& A, const FNavNode& B) const { return A.F < B.F; }
	};

	// Octile distance in cells: admissible for 8-connected moves costing 1 and sqrt(2) with weights >= 1.
	float Octile(int32 DX, int32 DY)
	{
		const float Ax = FMath::Abs(DX), Ay = FMath::Abs(DY);
		return FMath::Max(Ax, Ay) + (UE_SQRT_2 - 1.f) * FMath::Min(Ax, Ay);
	}
}

bool UDaedalusNav::FloorAt(int32 CX, int32 CY, float RefZ, float& OutZ)
{
	const FIntVector Key(CX, CY, FMath::FloorToInt(RefZ / 150.f));
	if (const float* Known = Floors.Find(Key))
	{
		OutZ = *Known;
		return *Known > NoFloor * 0.5f;
	}
	UWorld* W = GetWorld();
	float Z = NoFloor;
	if (W)
	{
		++Samples;
		const FVector Mid((CX + 0.5f) * Cell, (CY + 0.5f) * Cell, RefZ);
		FHitResult Hit;
		FCollisionObjectQueryParams Objects(ECC_WorldStatic);
		// From well above: a hit higher than a step is a wall (a block, a cliff face), not a floor.
		if (W->LineTraceSingleByObjectType(Hit, Mid + FVector(0.f, 0.f, 300.f), Mid - FVector(0.f, 0.f, StepDown + 20.f), Objects)
			&& Hit.ImpactNormal.Z > 0.6f)
		{
			Z = Hit.ImpactPoint.Z;
		}
	}
	Floors.Add(Key, Z);
	OutZ = Z;
	return Z > NoFloor * 0.5f;
}

bool UDaedalusNav::FindPath(const FVector& From, const FVector& To, TArray<FVector>& OutPath)
{
	OutPath.Reset();
	++Searches;
	LastExpanded = 0;
	LastLength = 0;

	const int32 SX = FMath::FloorToInt(From.X / Cell), SY = FMath::FloorToInt(From.Y / Cell);
	const int32 GX = FMath::FloorToInt(To.X / Cell), GY = FMath::FloorToInt(To.Y / Cell);
	const int32 OX = (SX + GX) / 2 - Radius, OY = (SY + GY) / 2 - Radius;
	const int32 Side = Radius * 2 + 1;
	auto Inside = [&](int32 X, int32 Y) { return X >= OX && Y >= OY && X < OX + Side && Y < OY + Side; };
	if (!Inside(SX, SY) || !Inside(GX, GY)) return false;   // too far for one search
	auto IdOf = [&](int32 X, int32 Y) { return (X - OX) + (Y - OY) * Side; };

	// Cell-id-indexed arrays, as in AStarSolver (GridIndex).
	const int32 N = Side * Side;
	TArray<float> GScore;  GScore.Init(TNumericLimits<float>::Max(), N);
	TArray<int32> Parent;  Parent.Init(-1, N);
	TArray<bool> Closed;   Closed.Init(false, N);
	TArray<float> FloorZ;  FloorZ.Init(NoFloor, N);

	float StartZ;
	if (!FloorAt(SX, SY, From.Z + 40.f, StartZ)) StartZ = From.Z;
	const int32 StartId = IdOf(SX, SY);
	const int32 GoalId = IdOf(GX, GY);
	FloorZ[StartId] = StartZ;
	GScore[StartId] = 0.f;

	TArray<FNavNode> Open;
	Open.HeapPush({StartId, 0.f, Octile(GX - SX, GY - SY)}, FByF());

	static const int32 DX[8] = {1, -1, 0, 0, 1, 1, -1, -1};
	static const int32 DY[8] = {0, 0, 1, -1, 1, -1, 1, -1};

	// Is the step from one cell (at its floor) into a neighbour walkable? Fills the neighbour's floor.
	auto Step = [&](int32 FromId, int32 X, int32 Y, float& OutZ) -> bool
	{
		if (!Inside(X, Y)) return false;
		const float Here = FloorZ[FromId];
		float Z;
		if (!FloorAt(X, Y, Here + 40.f, Z)) return false;
		if (Z - Here > StepUp || Here - Z > StepDown) return false;
		OutZ = Z;
		return true;
	};

	while (Open.Num() > 0)
	{
		FNavNode Cur;
		Open.HeapPop(Cur, FByF());
		if (Closed[Cur.Id]) continue;
		Closed[Cur.Id] = true;
		++LastExpanded;
		++Expanded;
		const int32 CX = OX + Cur.Id % Side, CY = OY + Cur.Id / Side;

		if (Cur.Id == GoalId && FMath::Abs(FloorZ[Cur.Id] - To.Z) < 200.f)
		{
			TArray<int32> Ids;
			for (int32 At = GoalId; At != -1; At = Parent[At]) Ids.Add(At);
			for (int32 i = Ids.Num() - 1; i >= 0; --i)
			{
				const int32 Id = Ids[i];
				OutPath.Add(FVector((OX + Id % Side + 0.5f) * Cell, (OY + Id / Side + 0.5f) * Cell, FloorZ[Id]));
			}
			LastLength = OutPath.Num();
			++Found;
			return true;
		}
		if (LastExpanded >= Budget) return false;   // over budget: the foe waits and tries again later

		// Edge cells (a neighbour is a drop) cost more, as WeightedMazeGrid weights cells: keep off the lips.
		int32 Drops = 0;
		for (int32 i = 0; i < 4; ++i)
		{
			float Z;
			if (!Step(Cur.Id, CX + DX[i], CY + DY[i], Z)) ++Drops;
		}
		const float Weight = 1.f + (Drops > 0 ? 1.5f : 0.f);

		for (int32 i = 0; i < 8; ++i)
		{
			const int32 NX = CX + DX[i], NY = CY + DY[i];
			if (!Inside(NX, NY)) continue;
			const int32 NextId = IdOf(NX, NY);
			if (Closed[NextId]) continue;
			float Z;
			if (!Step(Cur.Id, NX, NY, Z)) continue;
			if (i >= 4)
			{
				// No cutting corners: both orthogonal cells must be walkable too.
				float A, B;
				if (!Step(Cur.Id, CX + DX[i], CY, A) || !Step(Cur.Id, CX, CY + DY[i], B)) continue;
			}
			const float Tentative = Cur.G + (i >= 4 ? UE_SQRT_2 : 1.f) * Weight;
			if (Tentative < GScore[NextId])
			{
				GScore[NextId] = Tentative;
				Parent[NextId] = Cur.Id;
				FloorZ[NextId] = Z;
				Open.HeapPush({NextId, Tentative, Tentative + Octile(GX - NX, GY - NY)}, FByF());
			}
		}
	}
	return false;
}

FString UDaedalusNav::Stats() const
{
	return FString::Printf(TEXT("searches=%d found=%d expanded=%d samples=%d cached=%d last_expanded=%d last_length=%d"),
		Searches, Found, Expanded, Samples, Floors.Num(), LastExpanded, LastLength);
}

void UDaedalusNav::ResetCache()
{
	Floors.Reset();
}
