// SPDX-License-Identifier: MIT

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "DaedalusMeshCore.h"
#include "DaedalusWorldActor.generated.h"

class UMaterialInterface;
class UProceduralMeshComponent;
class UStaticMesh;
class UStaticMeshComponent;
class FJsonObject;

/** A sky gate (ADR-031) as the package manifest names it, in Unreal units. */
USTRUCT(BlueprintType)
struct FDaedalusGate
{
	GENERATED_BODY()

	UPROPERTY(BlueprintReadOnly, Category = "Daedalus") int32 Gate = 0;
	UPROPERTY(BlueprintReadOnly, Category = "Daedalus") FString ToWorld;
	UPROPERTY(BlueprintReadOnly, Category = "Daedalus") FString ToTitle;
	UPROPERTY(BlueprintReadOnly, Category = "Daedalus") int32 ToGate = 0;
	/** The doorway's centre, past the rainbow. */
	UPROPERTY(BlueprintReadOnly, Category = "Daedalus") FVector Center = FVector::ZeroVector;
	/** The cloud berth an ark (or a mount) ties up at. */
	UPROPERTY(BlueprintReadOnly, Category = "Daedalus") FVector Berth = FVector::ZeroVector;
};

/** A raised island (ADR-018) as the manifest names it, in Unreal units. */
USTRUCT(BlueprintType)
struct FDaedalusIsland
{
	GENERATED_BODY()

	UPROPERTY(BlueprintReadOnly, Category = "Daedalus") int32 Slot = 0;
	UPROPERTY(BlueprintReadOnly, Category = "Daedalus") int64 Seed = 0;
	UPROPERTY(BlueprintReadOnly, Category = "Daedalus") int32 Radius = 0;
	UPROPERTY(BlueprintReadOnly, Category = "Daedalus") FVector Origin = FVector::ZeroVector;
	UPROPERTY(BlueprintReadOnly, Category = "Daedalus") FVector Dock = FVector::ZeroVector;
	/** Who holds the deed; empty when unclaimed. */
	UPROPERTY(BlueprintReadOnly, Category = "Daedalus") FString Owner;
};

DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FDaedalusWorldLoaded, const FString&, LoadedWorldId);

/**
 * A live Daedalus world in an Unreal level (ADR-032). On load it reads the World Package manifest
 * (palette, islands, sky gates), streams every chunk from the server's REST API, meshes each one with
 * DaedalusMeshCore.h — the same rules as the Java exporter and the web realm, checked by a parity test —
 * and, while playing, polls for changed chunks and sailing arks. Daedalus is metres, +Y up, right-handed;
 * Unreal is centimetres, +Z up, left-handed: a Daedalus (x, y, z) stands at Unreal (x, z, y) × UnitsPerCube.
 */
UCLASS(BlueprintType, Blueprintable, meta = (DisplayName = "Daedalus World"))
class DAEDALUSLINK_API ADaedalusWorldActor : public AActor
{
	GENERATED_BODY()

public:
	ADaedalusWorldActor();

	/** The Daedalus server, e.g. http://localhost:8088 (no trailing slash). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus")
	FString ServerUrl = TEXT("http://localhost:8088");

	/** Which world on that server: world-zero, or any id from /api/v1/worlds. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus")
	FString WorldId = TEXT("world-zero");

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus")
	bool bLoadOnBeginPlay = true;

	/** While playing, poll for changed chunks and moving arks every PollSeconds. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus")
	bool bFollowLive = true;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus", meta = (ClampMin = "0.25"))
	float PollSeconds = 2.0f;

	/** Unreal units per cube. 100 keeps Daedalus' one cube = one metre. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus", meta = (ClampMin = "1"))
	float UnitsPerCube = 100.0f;

	/** Opaque cubes collide; water, glass, rainbows and gate doorways do not. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus")
	bool bCollision = true;

	/** Reverse every triangle, for a project whose materials cull the other side. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|Advanced")
	bool bFlipWinding = false;

	/** A material that shows vertex colour as base colour (import_world_package.py makes one). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|Look")
	TObjectPtr<UMaterialInterface> OpaqueMaterial;

	/** A translucent vertex-colour material for water, glass, rainbows and gate doorways. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|Look")
	TObjectPtr<UMaterialInterface> TranslucentMaterial;

	/** The ark, imported from the package's assets/ark.glb. Optional: without it arks are not drawn. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|Look")
	TObjectPtr<UStaticMesh> ArkMesh;

	/** The web realm draws the ark at 0.6 of its modelled size; so do we. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|Look")
	float ArkScale = 0.6f;

	UPROPERTY(BlueprintReadOnly, Category = "Daedalus")
	FString WorldTitle;

	UPROPERTY(BlueprintReadOnly, Category = "Daedalus")
	FString WorldStyle;

	UPROPERTY(BlueprintReadOnly, Category = "Daedalus")
	TArray<FDaedalusIsland> Islands;

	UPROPERTY(BlueprintReadOnly, Category = "Daedalus")
	TArray<FDaedalusGate> Gates;

	/** What flies to this world's gates: ARK, HELICOPTER, PLANE, DRONE or SKY_STRIDER (ADR-031). */
	UPROPERTY(BlueprintReadOnly, Category = "Daedalus")
	FString Mount;

	UPROPERTY(BlueprintAssignable, Category = "Daedalus")
	FDaedalusWorldLoaded OnWorldLoaded;

	/** Fetch the world and build it, in the editor or at play. Failed requests are retried on the next poll. */
	UFUNCTION(CallInEditor, BlueprintCallable, Category = "Daedalus")
	void LoadWorld();

	/** Remove every chunk and ark this actor built. */
	UFUNCTION(CallInEditor, BlueprintCallable, Category = "Daedalus")
	void ClearWorld();

	/** Go through a sky gate: this actor becomes the world on the other side. False if no such gate. */
	UFUNCTION(BlueprintCallable, Category = "Daedalus")
	bool TravelThroughGate(int32 Gate);

	/** A Daedalus (x, y, z) in metres to this actor's local Unreal space. */
	UFUNCTION(BlueprintPure, Category = "Daedalus")
	FVector ToUnreal(const FVector& Daedalus) const;

	/** How many chunks are built right now. */
	UFUNCTION(BlueprintPure, Category = "Daedalus")
	int32 ChunkCount() const { return ChunkMeshes.Num(); }

	virtual void BeginPlay() override;
	virtual void EndPlay(const EEndPlayReason::Type Reason) override;
	virtual void Tick(float DeltaSeconds) override;

private:
	struct FArkState
	{
		FVector From = FVector::ZeroVector;
		FVector To = FVector::ZeroVector;
		int64 DepartAt = 0;
		int64 ArriveAt = 0;
		bool bSailing = false;
	};

	using FJsonHandler = TFunction<void(const TSharedPtr<FJsonObject>&)>;

	void GetJson(const FString& Path, FJsonHandler OnJson);
	void ReadManifest(const TSharedPtr<FJsonObject>& Json);
	void Poll();
	void ReadChunks(const TSharedPtr<FJsonObject>& Json);
	void ReadChunk(const TSharedPtr<FJsonObject>& Json);
	void ReadArks(const TSharedPtr<FJsonObject>& Json);
	void FinishOne();
	void Rebuild();
	void BuildChunk(const daedalus::ChunkKey& Key);
	void MarkDirty(const daedalus::ChunkKey& Key);
	FVector ArkBerth(const TSharedPtr<FJsonObject>& Ark) const;
	int64 ServerNow() const;

	daedalus::Palette CubePalette;
	daedalus::ChunkStore Store;
	TMap<FIntVector, int64> ChunkRevisions;
	TSet<FIntVector> Dirty;

	UPROPERTY(Transient)
	TMap<FIntVector, TObjectPtr<UProceduralMeshComponent>> ChunkMeshes;

	UPROPERTY(Transient)
	TMap<FString, TObjectPtr<UStaticMeshComponent>> ArkComponents;

	TMap<FString, FArkState> Arks;
	FTimerHandle PollTimer;
	uint32 Generation = 0;     // bumped on every load: replies for an older load are dropped
	int32 InFlight = 0;
	bool bPolling = false;
	bool bAnnounced = false;
	int64 ServerClockAt = 0;   // the server's now, in ms, at ...
	double LocalClockAt = 0.0; // ... this local time, in seconds
};
