#include "DaedalusExplorationTerrain.h"
#include "DaedalusExplorationTerrainCore.h"
#include "ProceduralMeshComponent.h"
#include "KismetProceduralMeshLibrary.h"

ADaedalusExplorationTerrain::ADaedalusExplorationTerrain()
{
    PrimaryActorTick.bCanEverTick=false;
    Surface=CreateDefaultSubobject<UProceduralMeshComponent>(TEXT("TerrainSurface"));
    SetRootComponent(Surface);
    Surface->bUseComplexAsSimpleCollision=true;
    Surface->SetCollisionProfileName(TEXT("BlockAll"));
}

void ADaedalusExplorationTerrain::OnConstruction(const FTransform& Transform)
{
    Super::OnConstruction(Transform);
    Surface->ClearAllMeshSections();
    // Editor metadata is advisory; reject invalid programmatic inputs as well.
    if (Cells<1 || Cells>256 || !FMath::IsFinite(SpacingMetres)
        || SpacingMetres<0.1 || SpacingMetres>100.0
        || !FMath::IsFinite(SampleOriginMetres.X) || !FMath::IsFinite(SampleOriginMetres.Y)
        || FMath::Abs(SampleOriginMetres.X)>1.e8 || FMath::Abs(SampleOriginMetres.Y)>1.e8)
        return;
    using namespace DaedalusExplorationTerrain;
    const auto Patch=Build(bOcean?Realm::Ocean:Realm::Prairie,
                          SampleOriginMetres.X,SampleOriginMetres.Y,
                          static_cast<unsigned>(Cells),SpacingMetres);
    TArray<FVector> Vertices,Normals;
    TArray<int32> Indices;
    TArray<FVector2D> UVs;
    TArray<FProcMeshTangent> Tangents;
    for (const auto& V:Patch.Vertices)
    {
        Vertices.Add(FVector((V.X-SampleOriginMetres.X)*100.0,
                            (V.Y-SampleOriginMetres.Y)*100.0,V.Z*100.0));
        UVs.Add(FVector2D((V.X-SampleOriginMetres.X)/4.0,(V.Y-SampleOriginMetres.Y)/4.0));
    }
    // Core uses mathematical CCW; Unreal rendering uses the reverse winding.
    for (std::size_t I=0;I<Patch.Indices.size();I+=3)
    {
        Indices.Add(static_cast<int32>(Patch.Indices[I]));
        Indices.Add(static_cast<int32>(Patch.Indices[I+2]));
        Indices.Add(static_cast<int32>(Patch.Indices[I+1]));
    }
    UKismetProceduralMeshLibrary::CalculateTangentsForMesh(Vertices,Indices,UVs,Normals,Tangents);
    Surface->CreateMeshSection_LinearColor(0,Vertices,Indices,Normals,UVs,TArray<FLinearColor>(),Tangents,true);
    if (SurfaceMaterial) Surface->SetMaterial(0,SurfaceMaterial);
}
