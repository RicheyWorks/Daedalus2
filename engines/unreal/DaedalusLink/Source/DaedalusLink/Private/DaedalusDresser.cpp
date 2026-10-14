// SPDX-License-Identifier: MIT

#include "DaedalusDresser.h"

#include "AssetRegistry/AssetData.h"
#include "AssetRegistry/AssetRegistryModule.h"
#include "AssetRegistry/IAssetRegistry.h"
#include "Components/HierarchicalInstancedStaticMeshComponent.h"
#include "DaedalusCritter.h"
#include "DaedalusLinkModule.h"
#include "DaedalusMob.h"
#include "DaedalusWorldActor.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/PlayerStart.h"
#include "TimerManager.h"

namespace DaedalusDress
{
	/** A stable number in [0, 1) for a cube and a purpose. */
	static double Roll(int32 X, int32 Y, int32 Z, int32 Seed, uint32 Salt)
	{
		uint64 H = (static_cast<uint64>(static_cast<uint32>(X)) * 0x9E3779B97F4A7C15ull)
			^ (static_cast<uint64>(static_cast<uint32>(Y)) * 0xC2B2AE3D27D4EB4Full)
			^ (static_cast<uint64>(static_cast<uint32>(Z)) * 0x165667B19E3779F9ull)
			^ (static_cast<uint64>(static_cast<uint32>(Seed)) << 32) ^ Salt;
		H = (H ^ (H >> 30)) * 0xBF58476D1CE4E5B9ull;
		H = (H ^ (H >> 27)) * 0x94D049BB133111EBull;
		H ^= H >> 31;
		return static_cast<double>(H >> 11) * (1.0 / 9007199254740992.0);
	}

	enum class EGround : uint8 { None, Grass, Sand, Stone, Snow };

	/** What grows where: species names (the token after Prop_Tree_ / Prop_Shrub_ ...) by ground. */
	static bool Belongs(const FString& Name, EGround G)
	{
		static const TArray<FString> Wet = {TEXT("Coral"), TEXT("Kelp"), TEXT("Seagrass"), TEXT("SeaAnemone"), TEXT("WaterLily"),
			TEXT("Lotus"), TEXT("Mangrove"), TEXT("Cattail"), TEXT("Reed")};
		static const TArray<FString> Desert = {TEXT("Palm"), TEXT("Joshua"), TEXT("Saguaro"), TEXT("Tumbleweed"), TEXT("DesertRose"),
			TEXT("DuneGrass"), TEXT("Aloe")};
		static const TArray<FString> Alpine = {TEXT("Pine"), TEXT("Spruce"), TEXT("Larch"), TEXT("Edelweiss"), TEXT("Gentian"),
			TEXT("Moss"), TEXT("Lichen"), TEXT("Frostcap"), TEXT("Juniper"), TEXT("Heather")};
		for (const FString& W : Wet) if (Name.Contains(W)) return false;   // no water to stand in yet
		bool bDesert = false, bAlpine = false;
		for (const FString& D : Desert) bDesert |= Name.Contains(D);
		for (const FString& A : Alpine) bAlpine |= Name.Contains(A);
		switch (G)
		{
		case EGround::Sand: return bDesert;
		case EGround::Stone: case EGround::Snow: return bAlpine;
		case EGround::Grass: return !bDesert;   // meadows and forests take the alpine kinds too, a little
		default: return false;
		}
	}
}

using namespace DaedalusDress;

ADaedalusDresser::ADaedalusDresser()
{
	PrimaryActorTick.bCanEverTick = false;
	RootComponent = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
	// The pools are Static (they never move and Nanite/lighting want it); a Static child can't attach to a Movable
	// root ("AttachTo ... is not static, cannot attach" x4 per pool, 2026-10-13), so the root is Static too.
	RootComponent->SetMobility(EComponentMobility::Static);
}

void ADaedalusDresser::BeginPlay()
{
	Super::BeginPlay();
	if (!bDressOnLoad) return;
	if (ADaedalusWorldActor* W = ADaedalusWorldActor::Find(this))
		W->OnWorldLoaded.AddUniqueDynamic(this, &ADaedalusDresser::OnWorldLoaded);
	TryDressSoon();
}

void ADaedalusDresser::OnWorldLoaded(const FString& WorldId)
{
	bDressed = false;
	TryDressSoon();
}

void ADaedalusDresser::TryDressSoon()
{
	// The live world streams in; dress once it has stopped growing for a moment.
	GetWorldTimerManager().SetTimer(Retry, FTimerDelegate::CreateWeakLambda(this, [this]()
	{
		const ADaedalusWorldActor* W = ADaedalusWorldActor::Find(this);
		static int32 LastCount = -1;
		const int32 Now = W ? W->ChunkCount() : 0;
		if (!bDressed && Now > 0 && Now == LastCount)
		{
			UE_LOG(LogDaedalus, Log, TEXT("Dresser: %s"), *Dress());
			GetWorldTimerManager().ClearTimer(Retry);
		}
		LastCount = Now;
	}), 1.5f, true);
}

UHierarchicalInstancedStaticMeshComponent* ADaedalusDresser::Pool(UStaticMesh* Mesh, bool bCollide)
{
	if (TObjectPtr<UHierarchicalInstancedStaticMeshComponent>* Found = Pools.Find(Mesh)) return *Found;
	UHierarchicalInstancedStaticMeshComponent* C = NewObject<UHierarchicalInstancedStaticMeshComponent>(this);
	C->SetStaticMesh(Mesh);
	C->SetupAttachment(RootComponent);
	C->SetMobility(EComponentMobility::Static);
	C->SetCollisionEnabled(bCollide ? ECollisionEnabled::QueryAndPhysics : ECollisionEnabled::NoCollision);
	if (bCollide) C->SetCollisionProfileName(TEXT("BlockAll"));
	C->SetCullDistances(0, 60000);
	C->RegisterComponent();
	AddInstanceComponent(C);
	Pools.Add(Mesh, C);
	return C;
}

void ADaedalusDresser::Undress()
{
	for (auto& P : Pools)
		if (P.Value) P.Value->DestroyComponent();
	Pools.Empty();
	for (const TWeakObjectPtr<AActor>& C : Critters)
		if (C.IsValid()) C->Destroy();
	Critters.Reset();
	bDressed = false;
	Town = FVector::ZeroVector;
}

FString ADaedalusDresser::Dress()
{
	Undress();
	ADaedalusWorldActor* W = ADaedalusWorldActor::Find(this);
	if (!W || W->ChunkCount() == 0) return LastStats = TEXT("no live world yet");
	const daedalus::ChunkStore& Store = W->CubeStore();
	const daedalus::Palette& Pal = W->CubePaletteRef();
	const float U = W->UnitsPerCube;

	// ---- the library: every static mesh the art queue shipped, by kind.
	IAssetRegistry& Reg = FModuleManager::LoadModuleChecked<FAssetRegistryModule>("AssetRegistry").Get();
	FARFilter Filter;
	Filter.ClassPaths.Add(UStaticMesh::StaticClass()->GetClassPathName());
	Filter.PackagePaths.Add(FName(TEXT("/Game/Daedalus/Art")));
	Filter.bRecursivePaths = true;
	TArray<FAssetData> Found;
	Reg.GetAssets(Filter, Found);
	TMap<FString, TArray<FAssetData>> ByCat;   // Tree, Shrub, Flower, Grass, Mushroom, Herb, Bld, Prop
	TMap<FString, FAssetData> ByName;
	for (const FAssetData& A : Found)
	{
		const FString N = A.AssetName.ToString();
		ByName.Add(N, A);
		// A plant that ships in two meshes (Prop_Tree_Oak_Mature + Prop_Tree_Oak_Mature_Top: trunk and crown) is one plant;
		// the _Top goes on when the base is placed. Before 2026-10-13 crowns stood on the ground and trunks stood bare.
		if (N.EndsWith(TEXT("_Top")) || N.EndsWith(TEXT("_Harvested"))) continue;
		for (const TCHAR* Cat : {TEXT("Tree"), TEXT("Shrub"), TEXT("Flower"), TEXT("Grass"), TEXT("Mushroom"), TEXT("Herb")})
			if (N.StartsWith(FString(TEXT("Prop_")) + Cat)) ByCat.FindOrAdd(Cat).Add(A);
	}
	auto Load = [](const FAssetData& A) { return Cast<UStaticMesh>(A.GetAsset()); };
	/** The crown that sits on a base mesh, if it ships one. */
	auto TopOf = [&](const FAssetData& Base) -> UStaticMesh*
	{
		const FAssetData* T = ByName.Find(Base.AssetName.ToString() + TEXT("_Top"));
		return T ? Load(*T) : nullptr;
	};

	auto Ground = [&](uint8 T) -> EGround
	{
		const std::string& N = Pal.Of(T).Name;
		if (N == "GRASS" || N == "DIRT") return EGround::Grass;
		if (N == "SAND") return EGround::Sand;
		if (N == "STONE" || N == "GRAVEL") return EGround::Stone;
		if (N == "SNOW") return EGround::Snow;
		return EGround::None;
	};
	auto Top = [&](int32 X, int32 Y, int32 Z) { return FVector(W->CubeCenter(FIntVector(X, Y, Z))) + FVector(0, 0, U * 0.5f); };

	// ---- the town: the flattest grass near the hero's start.
	int32 TX = 0, TY = 0, TZ = 0;
	bool bHaveTown = false;
	if (bTown)
	{
		FVector StartAt = FVector::ZeroVector;
		for (TActorIterator<APlayerStart> It(GetWorld()); It; ++It) { StartAt = It->GetActorLocation(); break; }
		const FIntVector S = W->CubeCoord(StartAt);
		auto TopY = [&](int32 X, int32 Z, int32 NearY) -> int32
		{
			for (int32 Y = NearY + 8; Y >= NearY - 12; --Y)
				if (Store.Get(X, Y, Z) != 0 && Store.Get(X, Y + 1, Z) == 0) return Y;
			return INT32_MIN;
		};
		int32 Best = -1;
		for (int32 DZ = -20; DZ <= 20; DZ += 2)
			for (int32 DX = -20; DX <= 20; DX += 2)
			{
				const int32 CX = S.X + DX, CZ = S.Z + DZ;
				const int32 CY = TopY(CX, CZ, S.Y);
				if (CY == INT32_MIN || Ground(Store.Get(CX, CY, CZ)) != EGround::Grass) continue;
				int32 Flat = 0;
				for (int32 Z = -6; Z <= 6; ++Z)
					for (int32 X = -6; X <= 6; ++X)
						Flat += TopY(CX + X, CZ + Z, CY) == CY;
				const int32 Score = Flat * 100 - (DX * DX + DZ * DZ);
				if (Score > Best) { Best = Score; TX = CX; TY = CY; TZ = CZ; }
			}
		bHaveTown = Best > 100 * 60;   // at least 60 of 169 columns flat
	}

	int32 Placed = 0, Trees = 0, Plants = 0, TownPieces = 0;
	TSet<FIntPoint> TreeAt;

	// ---- the wildlife (ADR-055): which shipped animals live on which ground.
	auto Shipped = [](std::initializer_list<const TCHAR*> Names)
	{
		TArray<FString> Out;
		for (const TCHAR* N : Names) if (DaedalusMob::Parts(N).Num() > 0) Out.Add(N);
		return Out;
	};
	const TArray<FString> Meadow = Shipped({TEXT("Mob_Sheep"), TEXT("Mob_Cow"), TEXT("Mob_Pig"), TEXT("Mob_Chicken"), TEXT("Mob_Deer"),
		TEXT("Mob_Rabbit"), TEXT("Mob_Fox"), TEXT("Mob_Goat"), TEXT("Mob_Horse"), TEXT("Mob_Hare"), TEXT("Mob_Squirrel"), TEXT("Mob_Duck")});
	const TArray<FString> Dunes = Shipped({TEXT("Mob_Lizard"), TEXT("Mob_Jerboa"), TEXT("Mob_Scorpion"), TEXT("Mob_Crab")});
	const TArray<FString> Heights = Shipped({TEXT("Mob_MountainGoat"), TEXT("Mob_Marmot"), TEXT("Mob_SnowFox"), TEXT("Mob_Caribou")});
	struct FHerd { FString Species; FVector At; int32 Count; int32 Salt; };
	TArray<FHerd> Herds;

	// ---- the plants.
	for (const auto& KV : Store.All())
	{
		const daedalus::ChunkKey& K = KV.first;
		for (int32 LZ = 0; LZ < daedalus::ChunkSize; ++LZ)
			for (int32 LX = 0; LX < daedalus::ChunkSize; ++LX)
				for (int32 LY = 0; LY < daedalus::ChunkSize; ++LY)
				{
					const int32 X = K.X * daedalus::ChunkSize + LX, Y = K.Y * daedalus::ChunkSize + LY, Z = K.Z * daedalus::ChunkSize + LZ;
					const uint8 T = KV.second[LX + daedalus::ChunkSize * (LY + daedalus::ChunkSize * LZ)];
					if (T == 0 || Store.Get(X, Y + 1, Z) != 0 || Store.Get(X, Y + 2, Z) != 0) continue;
					const EGround G = Ground(T);
					if (G == EGround::None) continue;
					if (bHaveTown && FMath::Abs(X - TX) <= 9 && FMath::Abs(Z - TZ) <= 9) continue;   // keep the town clear
					const double R = Roll(X, Y, Z, Seed, 1);
					if (R > 0.9 && R < 0.9 + 0.003 * Density)
					{
						const TArray<FString>& Kinds = G == EGround::Grass ? Meadow : G == EGround::Sand ? Dunes : Heights;
						if (Kinds.Num() > 0)
						{
							const int32 Which = FMath::Min(Kinds.Num() - 1, static_cast<int32>(Roll(X, Y, Z, Seed, 9) * Kinds.Num()));
							Herds.Add({Kinds[Which], Top(X, Y, Z), 1 + static_cast<int32>(Roll(X, Y, Z, Seed, 10) * 4.0), static_cast<int32>((static_cast<uint32>(X) * 73856093u) ^ (static_cast<uint32>(Z) * 19349663u))});
						}
						continue;
					}
					// Ground cover first (Richey 2026-10-13: the world looked "rough and scarce"): at Density 1 about 6 cubes in
					// 10 carry something, most of it grass and flowers; trees stay sparse and spaced. Density scales the lot.
					const double D = Density;
					const TCHAR* Cat = nullptr;
					if (R < 0.012 * D) Cat = TEXT("Tree");   // 1.2%: a 36 m island carried 160 trunks and read as a field of poles
					else if (R < 0.055 * D) Cat = TEXT("Shrub");
					else if (R < 0.135 * D) Cat = TEXT("Flower");
					else if (R < 0.585 * D) Cat = TEXT("Grass");
					else if (R < 0.595 * D) Cat = TEXT("Mushroom");
					else if (R < 0.610 * D) Cat = TEXT("Herb");
					if (!Cat) continue;
					const bool bTree = FCString::Strcmp(Cat, TEXT("Tree")) == 0;
					if (bTree)
					{
						bool bCrowded = false;
						for (int32 Z2 = -4; Z2 <= 4 && !bCrowded; ++Z2)
							for (int32 X2 = -4; X2 <= 4 && !bCrowded; ++X2) bCrowded = TreeAt.Contains(FIntPoint(X + X2, Z + Z2));
						if (bCrowded) continue;
					}
					const TArray<FAssetData>* Pool0 = ByCat.Find(Cat);
					if (!Pool0) continue;
					TArray<const FAssetData*> Fit;
					for (const FAssetData& A : *Pool0) if (Belongs(A.AssetName.ToString(), G)) Fit.Add(&A);
					if (Fit.Num() == 0) continue;
					// Neighbouring plants of one kind cluster: pick by a coarse cell, not per cube.
					const int32 Pick = FMath::Min(Fit.Num() - 1, static_cast<int32>(Roll(X / 6, 0, Z / 6, Seed, 2) * Fit.Num()));
					const int32 Pick2 = FMath::Min(Fit.Num() - 1, static_cast<int32>(Roll(X, Y, Z, Seed, 3) * Fit.Num()));
					const FAssetData& Chosen = *Fit[Roll(X, Y, Z, Seed, 4) < 0.7 ? Pick : Pick2];
					UStaticMesh* M = Load(Chosen);
					if (!M) continue;
					const float Yaw = static_cast<float>(Roll(X, Y, Z, Seed, 5) * 360.0);
					const float Sc = static_cast<float>(0.85 + Roll(X, Y, Z, Seed, 6) * 0.35);
					const FVector Jit((Roll(X, Y, Z, Seed, 7) - 0.5) * U * 0.6, (Roll(X, Y, Z, Seed, 8) - 0.5) * U * 0.6, 0.0);
					const FVector At = Top(X, Y, Z) + Jit;
					Pool(M, bTree)->AddInstance(FTransform(FRotator(0, Yaw, 0), At, FVector(Sc)), true);
					if (UStaticMesh* Crown = TopOf(Chosen))
					{
						// The crown shares the base's origin with its height baked in (Oak_Mature_Top starts at z = 182 over
						// a 220 trunk), so it goes at the same place, scale and yaw.
						Pool(Crown, false)->AddInstance(FTransform(FRotator(0, Yaw, 0), At, FVector(Sc)), true);
					}
					++Placed;
					if (bTree) { ++Trees; TreeAt.Add(FIntPoint(X, Z)); } else ++Plants;
				}
	}

	// ---- the town: a plaza with a well, a news board, a shop, cottages round it, benches, lanterns, mail, flowers.
	if (bHaveTown)
	{
		Town = Top(TX, TY, TZ);
		struct FPiece { const TCHAR* Name; int32 DX, DZ; float Yaw; bool bCollide; };
		const FPiece Pieces[] = {
			{TEXT("Prop_Well"), 0, 0, 0.f, true}, {TEXT("Bld_NewsBoard"), 0, -4, 0.f, true},
			{TEXT("Bld_Shop"), -8, 0, 90.f, true}, {TEXT("Bld_Cottage"), 8, -6, -90.f, true},
			{TEXT("Bld_Cottage"), 8, 6, -90.f, true}, {TEXT("Bld_Cottage"), 0, 9, 180.f, true},
			{TEXT("Prop_Bench"), -3, 3, 45.f, false}, {TEXT("Prop_Bench"), 3, 3, -45.f, false},
			{TEXT("Prop_Lantern"), -5, -5, 0.f, false}, {TEXT("Prop_Lantern"), 5, -5, 0.f, false},
			{TEXT("Prop_Lantern"), -5, 5, 0.f, false}, {TEXT("Prop_Lantern"), 5, 5, 0.f, false},
			{TEXT("Prop_Mailbox"), 6, -3, -90.f, false}, {TEXT("Prop_Mailbox"), 6, 3, -90.f, false},
			{TEXT("Prop_FlowerPot"), -2, -2, 0.f, false}, {TEXT("Prop_FlowerPot"), 2, -2, 0.f, false},
			{TEXT("Prop_FlowerPot"), -2, 2, 0.f, false}, {TEXT("Prop_FlowerPot"), 2, 2, 0.f, false},
		};
		for (const FPiece& P : Pieces)
		{
			const FAssetData* A = ByName.Find(P.Name);
			UStaticMesh* M = A ? Load(*A) : nullptr;
			if (!M) continue;
			// Sit each piece on its own column's top, near the plaza's height.
			int32 Y = TY;
			for (int32 Up = TY + 3; Up >= TY - 3; --Up)
				if (Store.Get(TX + P.DX, Up, TZ + P.DZ) != 0 && Store.Get(TX + P.DX, Up + 1, TZ + P.DZ) == 0) { Y = Up; break; }
			Pool(M, P.bCollide)->AddInstance(FTransform(FRotator(0, P.Yaw, 0), Top(TX + P.DX, Y, TZ + P.DZ), FVector(1.f)), true);
			++Placed;
			++TownPieces;
		}
	}

	// ---- the herds, nearest the start first (so the cap keeps the ones the player will meet).
	{
		const FVector From = bHaveTown ? Town : FVector::ZeroVector;
		Herds.Sort([&](const FHerd& A, const FHerd& B) { return FVector::DistSquared(A.At, From) < FVector::DistSquared(B.At, From); });
		for (const FHerd& H : Herds)
			for (int32 i = 0; i < H.Count && Critters.Num() < MaxCritters; ++i)
			{
				const FVector Off = FRotator(0.f, i * 137.5f, 0.f).Vector() * (i == 0 ? 0.f : 120.f + 40.f * i);
				const FTransform T(FRotator::ZeroRotator, H.At + Off + FVector(0, 0, 50.f));
				if (ADaedalusCritter* C = GetWorld()->SpawnActorDeferred<ADaedalusCritter>(ADaedalusCritter::StaticClass(), T, this,
					nullptr, ESpawnActorCollisionHandlingMethod::AlwaysSpawn))
				{
					C->Species = H.Species;
					C->Seed = H.Salt + i * 7919 + Seed;
					C->FinishSpawning(T);
					Critters.Add(C);
				}
			}
	}

	bDressed = true;
	LastStats = FString::Printf(TEXT("placed=%d meshes=%d trees=%d plants=%d town=%d library=%d critters=%d herds=%d town_at=%d,%d,%d"),
		Placed, Pools.Num(), Trees, Plants, TownPieces, Found.Num(), Critters.Num(), Herds.Num(), TX, TY, TZ);
	return LastStats;
}
