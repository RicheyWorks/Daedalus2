#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "DaedalusOceanHostClient.h"
#include "DaedalusOceanSectorView.generated.h"
class UProceduralMeshComponent;
class UMaterialInterface;

/** Bounded local scene consumer; caller owns streaming tickets and material assignment. */
UCLASS()
class DAEDALUSLINK_API ADaedalusOceanSectorView : public AActor
{
    GENERATED_BODY()
public:
    ADaedalusOceanSectorView();
    UFUNCTION(BlueprintCallable,Category="Daedalus|Ocean") bool ApplyChunk(const FDaedalusOceanChunkView& Chunk);
    UFUNCTION(BlueprintCallable,Category="Daedalus|Ocean") bool RemoveChunk(int32 X,int32 Y,int32 Z);
    UFUNCTION(BlueprintCallable,Category="Daedalus|Ocean") void ClearChunks();
    UFUNCTION(BlueprintPure,Category="Daedalus|Ocean") int32 ResidentCount() const { return Chunks.Num(); }
    UFUNCTION(BlueprintPure,Category="Daedalus|Ocean") int32 TriangleCount(int32 X,int32 Y,int32 Z) const;
    UFUNCTION(BlueprintPure,Category="Daedalus|Ocean") UProceduralMeshComponent* MeshForChunk(int32 X,int32 Y,int32 Z) const;
    UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="Daedalus|Ocean",meta=(ClampMin="1",ClampMax="256")) int32 MaxChunks=64;
    UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="Daedalus|Ocean") TObjectPtr<UMaterialInterface> OpaqueMaterial;
    UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="Daedalus|Ocean") TObjectPtr<UMaterialInterface> WaterMaterial;
private:
    TMap<FIntVector,FDaedalusOceanChunkView> Chunks;
    UPROPERTY() TMap<FIntVector,TObjectPtr<UProceduralMeshComponent>> Meshes;
    TArray<FString> PaletteNames;
    void Rebuild(const FIntVector& Key);
    void RebuildNeighbours(const FIntVector& Key);
    void DropMesh(const FIntVector& Key);
};
