// SPDX-License-Identifier: MIT

#include "DaedalusLandDistrict.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "UObject/ConstructorHelpers.h"

ADaedalusLandDistrict::ADaedalusLandDistrict()
{
	PrimaryActorTick.bCanEverTick = false;
	USceneComponent* Root = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
	Root->SetMobility(EComponentMobility::Static);
	SetRootComponent(Root);
	static ConstructorHelpers::FObjectFinder<UStaticMesh> CubeFinder(TEXT("/Engine/BasicShapes/Cube.Cube"));
	Plots = CreateDefaultSubobject<UInstancedStaticMeshComponent>(TEXT("Plots"));
	Plots->SetupAttachment(Root);
	Plots->SetMobility(EComponentMobility::Static);
	Plots->SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);
	Ground = CreateDefaultSubobject<UInstancedStaticMeshComponent>(TEXT("Ground"));
	Ground->SetupAttachment(Root);
	Ground->SetMobility(EComponentMobility::Static);
	Ground->SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);
	if (CubeFinder.Succeeded())
	{
		Plots->SetStaticMesh(CubeFinder.Object);
		Ground->SetStaticMesh(CubeFinder.Object);
	}
}

int32 ADaedalusLandDistrict::LayPlots(const TArray<int32>& CellNumbers, const TArray<FTransform>& Where)
{
	if (!Plots || CellNumbers.Num() != Where.Num()) return 0;
	Plots->ClearInstances();
	Plots->AddInstances(Where, false, true);
	Cells = CellNumbers;
	return Plots->GetInstanceCount();
}

int32 ADaedalusLandDistrict::LayGround(const TArray<FTransform>& Where)
{
	if (!Ground) return 0;
	Ground->ClearInstances();
	Ground->AddInstances(Where, false, true);
	return Ground->GetInstanceCount();
}

FString ADaedalusLandDistrict::DistrictState() const
{
	return FString::Printf(TEXT("realm=%s district=%d plots=%d ground=%d"), *Realm, District, Plots ? Plots->GetInstanceCount() : 0, Ground ? Ground->GetInstanceCount() : 0);
}
