#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "DaedalusExplorationTerrain.generated.h"

class UProceduralMeshComponent;
class UMaterialInterface;

/** Placeable terrain patch. No automatic world placement or land ownership changes. */
UCLASS()
class DAEDALUSLINK_API ADaedalusExplorationTerrain : public AActor
{
    GENERATED_BODY()
public:
    ADaedalusExplorationTerrain();
    virtual void OnConstruction(const FTransform& Transform) override;
    UPROPERTY(EditAnywhere, Category="Daedalus|Terrain") bool bOcean = false;
    UPROPERTY(EditAnywhere, Category="Daedalus|Terrain", meta=(ClampMin="1",ClampMax="256")) int32 Cells = 64;
    UPROPERTY(EditAnywhere, Category="Daedalus|Terrain", meta=(ClampMin="0.1",ClampMax="100")) double SpacingMetres = 4.0;
    UPROPERTY(EditAnywhere, Category="Daedalus|Terrain") FVector2D SampleOriginMetres = FVector2D::ZeroVector;
    UPROPERTY(EditAnywhere, Category="Daedalus|Terrain") TObjectPtr<UMaterialInterface> SurfaceMaterial;
    UPROPERTY(VisibleAnywhere, Category="Daedalus|Terrain") TObjectPtr<UProceduralMeshComponent> Surface;
};
