// SPDX-License-Identifier: MIT

#include "DaedalusWorldActor.h"

#include "DaedalusLinkModule.h"
#include "Components/SceneComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Dom/JsonObject.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "HttpModule.h"
#include "Interfaces/IHttpRequest.h"
#include "Interfaces/IHttpResponse.h"
#include "Materials/MaterialInterface.h"
#include "ProceduralMeshComponent.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "TimerManager.h"

#include <string>

namespace
{
	/** Engine material that shows vertex colour, used until the project has its own. */
	const TCHAR* FallbackMaterial = TEXT("/Engine/EngineDebugMaterials/VertexColorMaterial.VertexColorMaterial");

	/** The realm's ark standoff: pier tip to hull centreline, along +Z (ADR-022). */
	constexpr double ArkStandoff = 9.0;

	FIntVector KeyOf(const daedalus::ChunkKey& K) { return FIntVector(K.X, K.Y, K.Z); }
	daedalus::ChunkKey KeyOf(const FIntVector& K) { return daedalus::ChunkKey{K.X, K.Y, K.Z}; }

	FVector Xyz(const TSharedPtr<FJsonObject>& O, const TCHAR* Field)
	{
		const TArray<TSharedPtr<FJsonValue>>* A = nullptr;
		if (!O->TryGetArrayField(Field, A) || A->Num() != 3)
		{
			return FVector::ZeroVector;
		}
		return FVector((*A)[0]->AsNumber(), (*A)[1]->AsNumber(), (*A)[2]->AsNumber());
	}
}

ADaedalusWorldActor::ADaedalusWorldActor()
{
	PrimaryActorTick.bCanEverTick = true;
	RootComponent = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
}

FVector ADaedalusWorldActor::ToUnreal(const FVector& D) const
{
	return FVector(D.X, D.Z, D.Y) * UnitsPerCube;
}

void ADaedalusWorldActor::BeginPlay()
{
	Super::BeginPlay();
	if (bLoadOnBeginPlay)
	{
		LoadWorld();
	}
}

void ADaedalusWorldActor::EndPlay(const EEndPlayReason::Type Reason)
{
	if (UWorld* W = GetWorld())
	{
		W->GetTimerManager().ClearTimer(PollTimer);
	}
	++Generation;
	Super::EndPlay(Reason);
}

void ADaedalusWorldActor::LoadWorld()
{
	ClearWorld();
	const uint32 Gen = Generation;
	UE_LOG(LogDaedalus, Log, TEXT("Loading %s from %s"), *WorldId, *ServerUrl);
	GetJson(FString::Printf(TEXT("/api/v1/world/%s/package/manifest"), *WorldId),
		[this, Gen](const TSharedPtr<FJsonObject>& Json)
		{
			if (!Json.IsValid())
			{
				UE_LOG(LogDaedalus, Warning, TEXT("No world %s at %s: is the server up, and does the world exist?"), *WorldId, *ServerUrl);
				return;
			}
			ReadManifest(Json);
			Poll();
			UWorld* W = GetWorld();
			if (bFollowLive && W && W->IsGameWorld() && Gen == Generation)
			{
				W->GetTimerManager().SetTimer(PollTimer, this, &ADaedalusWorldActor::Poll, PollSeconds, true);
			}
		});
}

void ADaedalusWorldActor::ClearWorld()
{
	++Generation;
	if (UWorld* W = GetWorld())
	{
		W->GetTimerManager().ClearTimer(PollTimer);
	}
	for (auto& KV : ChunkMeshes)
	{
		if (KV.Value)
		{
			KV.Value->DestroyComponent();
		}
	}
	for (auto& KV : ArkComponents)
	{
		if (KV.Value)
		{
			KV.Value->DestroyComponent();
		}
	}
	ChunkMeshes.Empty();
	ArkComponents.Empty();
	Arks.Empty();
	ChunkRevisions.Empty();
	Dirty.Empty();
	Store = daedalus::ChunkStore();
	CubePalette = daedalus::Palette();
	Islands.Empty();
	Gates.Empty();
	InFlight = 0;
	bPolling = false;
	bAnnounced = false;
}

bool ADaedalusWorldActor::TravelThroughGate(int32 Gate)
{
	for (const FDaedalusGate& G : Gates)
	{
		if (G.Gate == Gate && !G.ToWorld.IsEmpty())
		{
			UE_LOG(LogDaedalus, Log, TEXT("Through gate %d of %s to %s (%s)"), Gate, *WorldId, *G.ToWorld, *G.ToTitle);
			WorldId = G.ToWorld;
			LoadWorld();
			return true;
		}
	}
	return false;
}

void ADaedalusWorldActor::GetJson(const FString& Path, FJsonHandler OnJson)
{
	TSharedRef<IHttpRequest, ESPMode::ThreadSafe> Req = FHttpModule::Get().CreateRequest();
	Req->SetURL(ServerUrl + Path);
	Req->SetVerb(TEXT("GET"));
	Req->SetHeader(TEXT("Accept"), TEXT("application/json"));
	TWeakObjectPtr<ADaedalusWorldActor> Self(this);
	const uint32 Gen = Generation;
	Req->OnProcessRequestComplete().BindLambda(
		[Self, Gen, Path, OnJson = MoveTemp(OnJson)](FHttpRequestPtr, FHttpResponsePtr Resp, bool bConnected)
		{
			if (!Self.IsValid() || Self->Generation != Gen)
			{
				return; // a newer load (or the end of play) made this answer moot
			}
			if (!bConnected || !Resp.IsValid() || !EHttpResponseCodes::IsOk(Resp->GetResponseCode()))
			{
				UE_LOG(LogDaedalus, Warning, TEXT("GET %s failed (%d)"), *Path, Resp.IsValid() ? Resp->GetResponseCode() : 0);
				OnJson(nullptr);
				return;
			}
			TSharedPtr<FJsonObject> Json;
			const TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(Resp->GetContentAsString());
			if (!FJsonSerializer::Deserialize(Reader, Json) || !Json.IsValid())
			{
				UE_LOG(LogDaedalus, Warning, TEXT("GET %s: not JSON"), *Path);
				OnJson(nullptr);
				return;
			}
			OnJson(Json);
		});
	Req->ProcessRequest();
}

void ADaedalusWorldActor::ReadManifest(const TSharedPtr<FJsonObject>& Json)
{
	const TSharedPtr<FJsonObject>* World = nullptr;
	if (Json->TryGetObjectField(TEXT("world"), World))
	{
		WorldTitle = (*World)->GetStringField(TEXT("title"));
		WorldStyle = (*World)->GetStringField(TEXT("style"));
	}
	const TSharedPtr<FJsonObject>* MountJson = nullptr;
	if (Json->TryGetObjectField(TEXT("mount"), MountJson))
	{
		Mount = (*MountJson)->GetStringField(TEXT("kind"));
	}

	// The palette is data, not code: a new cube type on the server needs no new plugin.
	CubePalette = daedalus::Palette();
	CubePalette.Types.resize(1);
	CubePalette.Types[0] = daedalus::CubeType{"AIR", 0, false, true};
	for (const TSharedPtr<FJsonValue>& V : Json->GetArrayField(TEXT("palette")))
	{
		const TSharedPtr<FJsonObject> S = V->AsObject();
		const int32 Ord = S->GetIntegerField(TEXT("ordinal"));
		if (Ord <= 0 || Ord > 255)
		{
			continue;
		}
		if (static_cast<int32>(CubePalette.Types.size()) <= Ord)
		{
			CubePalette.Types.resize(Ord + 1);
		}
		FString Hex = S->GetStringField(TEXT("rgb"));
		Hex.RemoveFromStart(TEXT("#"));
		daedalus::CubeType& T = CubePalette.Types[Ord];
		T.Name = TCHAR_TO_UTF8(*S->GetStringField(TEXT("type")));
		T.Rgb = FParse::HexNumber(*Hex);
		T.bTranslucent = S->GetBoolField(TEXT("translucent"));
		T.bSeeThrough = S->GetBoolField(TEXT("seeThrough"));
	}

	Islands.Empty();
	for (const TSharedPtr<FJsonValue>& V : Json->GetArrayField(TEXT("islands")))
	{
		const TSharedPtr<FJsonObject> O = V->AsObject();
		FDaedalusIsland I;
		I.Slot = O->GetIntegerField(TEXT("slot"));
		I.Seed = static_cast<int64>(O->GetNumberField(TEXT("seed")));
		I.Radius = O->GetIntegerField(TEXT("radius"));
		I.Origin = ToUnreal(Xyz(O, TEXT("origin")));
		I.Dock = ToUnreal(Xyz(O, TEXT("dock")));
		O->TryGetStringField(TEXT("owner"), I.Owner);
		Islands.Add(I);
	}
	Gates.Empty();
	for (const TSharedPtr<FJsonValue>& V : Json->GetArrayField(TEXT("gates")))
	{
		const TSharedPtr<FJsonObject> O = V->AsObject();
		FDaedalusGate G;
		G.Gate = O->GetIntegerField(TEXT("gate"));
		G.ToWorld = O->GetStringField(TEXT("toWorld"));
		O->TryGetStringField(TEXT("toTitle"), G.ToTitle);
		G.ToGate = O->GetIntegerField(TEXT("toGate"));
		G.Center = ToUnreal(Xyz(O, TEXT("center")));
		G.Berth = ToUnreal(Xyz(O, TEXT("berth")));
		Gates.Add(G);
	}
	UE_LOG(LogDaedalus, Log, TEXT("%s (%s): %d cube types, %d islands, %d gates, mount %s"), *WorldTitle, *WorldStyle,
		static_cast<int32>(CubePalette.Types.size()), Islands.Num(), Gates.Num(), *Mount);
}

void ADaedalusWorldActor::Poll()
{
	if (bPolling)
	{
		return; // the last poll is still being answered
	}
	bPolling = true;
	InFlight = 2;
	GetJson(FString::Printf(TEXT("/api/v1/world/%s/chunks"), *WorldId),
		[this](const TSharedPtr<FJsonObject>& Json)
		{
			if (Json.IsValid())
			{
				ReadChunks(Json);
			}
			FinishOne();
		});
	GetJson(FString::Printf(TEXT("/api/v1/world/%s/arks"), *WorldId),
		[this](const TSharedPtr<FJsonObject>& Json)
		{
			if (Json.IsValid())
			{
				ReadArks(Json);
			}
			FinishOne();
		});
}

void ADaedalusWorldActor::ReadChunks(const TSharedPtr<FJsonObject>& Json)
{
	TSet<FIntVector> Seen;
	for (const TSharedPtr<FJsonValue>& V : Json->GetArrayField(TEXT("chunks")))
	{
		const TSharedPtr<FJsonObject> Row = V->AsObject();
		const FIntVector K(Row->GetIntegerField(TEXT("x")), Row->GetIntegerField(TEXT("y")), Row->GetIntegerField(TEXT("z")));
		const int64 Rev = static_cast<int64>(Row->GetNumberField(TEXT("revision")));
		Seen.Add(K);
		const int64* Had = ChunkRevisions.Find(K);
		if (Had && *Had == Rev)
		{
			continue;
		}
		ChunkRevisions.Add(K, Rev);
		++InFlight;
		GetJson(FString::Printf(TEXT("/api/v1/world/%s/chunk/blocks?x=%d&y=%d&z=%d"), *WorldId, K.X, K.Y, K.Z),
			[this, K](const TSharedPtr<FJsonObject>& Blocks)
			{
				if (Blocks.IsValid())
				{
					ReadChunk(Blocks);
				}
				else
				{
					ChunkRevisions.Remove(K); // fetch it again on the next poll
				}
				FinishOne();
			});
	}
	TArray<FIntVector> Gone;
	for (const auto& KV : ChunkRevisions)
	{
		if (!Seen.Contains(KV.Key))
		{
			Gone.Add(KV.Key);
		}
	}
	for (const FIntVector& K : Gone)
	{
		ChunkRevisions.Remove(K);
		Store.Drop(KeyOf(K));
		MarkDirty(KeyOf(K));
	}
}

void ADaedalusWorldActor::ReadChunk(const TSharedPtr<FJsonObject>& Json)
{
	const daedalus::ChunkKey K{Json->GetIntegerField(TEXT("x")), Json->GetIntegerField(TEXT("y")),
		Json->GetIntegerField(TEXT("z"))};
	if (!Json->GetBoolField(TEXT("present")))
	{
		Store.Drop(K);
	}
	else
	{
		daedalus::ChunkStore::Cubes Cubes{};
		const std::string Data = TCHAR_TO_UTF8(*Json->GetStringField(TEXT("data")));
		if (!daedalus::DecodeChunk(Data, Cubes))
		{
			UE_LOG(LogDaedalus, Warning, TEXT("Chunk %d,%d,%d: bad payload"), K.X, K.Y, K.Z);
			return;
		}
		Store.Put(K, Cubes);
	}
	MarkDirty(K);
}

void ADaedalusWorldActor::MarkDirty(const daedalus::ChunkKey& K)
{
	// A cube on a chunk's edge decides whether its neighbour's face shows: remesh the six neighbours too.
	Dirty.Add(KeyOf(K));
	Dirty.Add(FIntVector(K.X + 1, K.Y, K.Z));
	Dirty.Add(FIntVector(K.X - 1, K.Y, K.Z));
	Dirty.Add(FIntVector(K.X, K.Y + 1, K.Z));
	Dirty.Add(FIntVector(K.X, K.Y - 1, K.Z));
	Dirty.Add(FIntVector(K.X, K.Y, K.Z + 1));
	Dirty.Add(FIntVector(K.X, K.Y, K.Z - 1));
}

void ADaedalusWorldActor::FinishOne()
{
	if (--InFlight > 0)
	{
		return;
	}
	Rebuild();
	bPolling = false;
	if (!bAnnounced)
	{
		bAnnounced = true;
		UE_LOG(LogDaedalus, Log, TEXT("%s built: %d chunks, %d arks"), *WorldId, ChunkMeshes.Num(), ArkComponents.Num());
		OnWorldLoaded.Broadcast(WorldId);
	}
}

void ADaedalusWorldActor::Rebuild()
{
	for (const FIntVector& K : Dirty)
	{
		BuildChunk(KeyOf(K));
	}
	Dirty.Empty();
}

void ADaedalusWorldActor::BuildChunk(const daedalus::ChunkKey& Key)
{
	const FIntVector K = KeyOf(Key);
	daedalus::Part Opaque;
	daedalus::Part Translucent;
	daedalus::MeshChunk(Store, CubePalette, Key, Opaque, Translucent);
	TObjectPtr<UProceduralMeshComponent>* Existing = ChunkMeshes.Find(K);
	if (Opaque.IsEmpty() && Translucent.IsEmpty())
	{
		if (Existing && *Existing)
		{
			(*Existing)->DestroyComponent();
		}
		ChunkMeshes.Remove(K);
		return;
	}
	UProceduralMeshComponent* Mesh = Existing ? Existing->Get() : nullptr;
	if (!Mesh)
	{
		Mesh = NewObject<UProceduralMeshComponent>(this, *FString::Printf(TEXT("chunk_%d_%d_%d"), K.X, K.Y, K.Z));
		Mesh->SetupAttachment(RootComponent);
		Mesh->bUseAsyncCooking = true;
		Mesh->RegisterComponent();
		ChunkMeshes.Add(K, Mesh);
	}

	UMaterialInterface* Fallback = nullptr;
	if (!OpaqueMaterial || !TranslucentMaterial)
	{
		Fallback = LoadObject<UMaterialInterface>(nullptr, FallbackMaterial);
	}
	const daedalus::Part* Parts[2] = {&Opaque, &Translucent};
	for (int32 Section = 0; Section < 2; ++Section)
	{
		const daedalus::Part& P = *Parts[Section];
		if (P.IsEmpty())
		{
			Mesh->ClearMeshSection(Section);
			continue;
		}
		const int32 NV = P.VertexCount();
		TArray<FVector> Vertices;
		TArray<FVector> Normals;
		TArray<FLinearColor> Colors;
		TArray<int32> Triangles;
		Vertices.Reserve(NV);
		Normals.Reserve(NV);
		Colors.Reserve(NV);
		for (int32 I = 0; I < NV; ++I)
		{
			const float* V = &P.Positions[I * 3];
			const float* N = &P.Normals[I * 3];
			const float* C = &P.Colors[I * 3];
			Vertices.Add(ToUnreal(FVector(V[0], V[1], V[2])));
			Normals.Add(FVector(N[0], N[2], N[1]));
			Colors.Add(FLinearColor(C[0], C[1], C[2], 1.0f));
		}
		Triangles.Reserve(P.Indices.size());
		for (size_t I = 0; I + 2 < P.Indices.size(); I += 3)
		{
			// Swapping Y and Z mirrors the space, which also turns Daedalus' counter-clockwise faces into
			// the clockwise faces Unreal draws: the indices stay as they are unless asked otherwise.
			Triangles.Add(static_cast<int32>(P.Indices[I]));
			Triangles.Add(static_cast<int32>(bFlipWinding ? P.Indices[I + 2] : P.Indices[I + 1]));
			Triangles.Add(static_cast<int32>(bFlipWinding ? P.Indices[I + 1] : P.Indices[I + 2]));
		}
		const bool bCollide = bCollision && Section == 0;
		Mesh->CreateMeshSection_LinearColor(Section, Vertices, Triangles, Normals, TArray<FVector2D>(), Colors,
			TArray<FProcMeshTangent>(), bCollide);
		UMaterialInterface* Mat = Section == 0 ? OpaqueMaterial.Get() : TranslucentMaterial.Get();
		Mesh->SetMaterial(Section, Mat ? Mat : Fallback);
	}
}

FVector ADaedalusWorldActor::ArkBerth(const TSharedPtr<FJsonObject>& Ark) const
{
	return ToUnreal(FVector(Ark->GetNumberField(TEXT("x")), Ark->GetNumberField(TEXT("y")),
		Ark->GetNumberField(TEXT("z")) + ArkStandoff));
}

int64 ADaedalusWorldActor::ServerNow() const
{
	return ServerClockAt + static_cast<int64>((FPlatformTime::Seconds() - LocalClockAt) * 1000.0);
}

void ADaedalusWorldActor::ReadArks(const TSharedPtr<FJsonObject>& Json)
{
	ServerClockAt = static_cast<int64>(Json->GetNumberField(TEXT("now")));
	LocalClockAt = FPlatformTime::Seconds();
	TSet<FString> Seen;
	for (const TSharedPtr<FJsonValue>& V : Json->GetArrayField(TEXT("arks")))
	{
		const TSharedPtr<FJsonObject> O = V->AsObject();
		const FString Id = O->GetStringField(TEXT("id"));
		Seen.Add(Id);
		const FVector Berth = ArkBerth(O);
		const bool bSailing = O->GetStringField(TEXT("state")) == TEXT("SAILING");
		FArkState* S = Arks.Find(Id);
		if (!S)
		{
			S = &Arks.Add(Id);
			S->From = Berth;
			S->To = Berth;
		}
		if (bSailing && (!S->bSailing || S->To != Berth))
		{
			// Sail from wherever the hull is now; the server says only where it is bound.
			if (const TObjectPtr<UStaticMeshComponent>* C = ArkComponents.Find(Id))
			{
				S->From = (*C)->GetRelativeLocation();
			}
		}
		S->To = Berth;
		S->bSailing = bSailing;
		S->DepartAt = static_cast<int64>(O->GetNumberField(TEXT("departAt")));
		S->ArriveAt = static_cast<int64>(O->GetNumberField(TEXT("arriveAt")));
		if (!bSailing)
		{
			S->From = Berth;
		}
		if (ArkMesh && !ArkComponents.Contains(Id))
		{
			UStaticMeshComponent* C = NewObject<UStaticMeshComponent>(this, *FString::Printf(TEXT("ark_%s"), *Id));
			C->SetStaticMesh(ArkMesh);
			C->SetupAttachment(RootComponent);
			C->SetRelativeScale3D(FVector(ArkScale));
			C->SetRelativeLocation(S->From);
			C->RegisterComponent();
			ArkComponents.Add(Id, C);
		}
	}
	TArray<FString> Gone;
	for (const auto& KV : Arks)
	{
		if (!Seen.Contains(KV.Key))
		{
			Gone.Add(KV.Key);
		}
	}
	for (const FString& Id : Gone)
	{
		Arks.Remove(Id);
		if (TObjectPtr<UStaticMeshComponent> C = ArkComponents.FindRef(Id))
		{
			C->DestroyComponent();
		}
		ArkComponents.Remove(Id);
	}
}

void ADaedalusWorldActor::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	if (ArkComponents.Num() == 0)
	{
		return;
	}
	const int64 Now = ServerNow();
	for (const auto& KV : Arks)
	{
		const TObjectPtr<UStaticMeshComponent>* C = ArkComponents.Find(KV.Key);
		if (!C || !*C)
		{
			continue;
		}
		const FArkState& S = KV.Value;
		FVector At = S.To;
		if (S.bSailing && S.ArriveAt > S.DepartAt)
		{
			const double T = FMath::Clamp(static_cast<double>(Now - S.DepartAt) / static_cast<double>(S.ArriveAt - S.DepartAt), 0.0, 1.0);
			At = FMath::Lerp(S.From, S.To, FMath::InterpEaseInOut(0.0, 1.0, T, 2.0));
		}
		(*C)->SetRelativeLocation(At);
	}
}
