// SPDX-License-Identifier: MIT

#include "DaedalusMob.h"

#include "AssetRegistry/AssetData.h"
#include "AssetRegistry/AssetRegistryModule.h"
#include "AssetRegistry/IAssetRegistry.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "GameFramework/Actor.h"

const TArray<FSoftObjectPath>& DaedalusMob::Parts(const FString& Asset)
{
	static TMap<FString, TArray<FSoftObjectPath>> Cache;
	if (const TArray<FSoftObjectPath>* Hit = Cache.Find(Asset)) return *Hit;
	TArray<FSoftObjectPath>& Paths = Cache.Add(Asset);
	IAssetRegistry& Reg = FModuleManager::LoadModuleChecked<FAssetRegistryModule>("AssetRegistry").Get();
	FARFilter Filter;
	Filter.ClassPaths.Add(UStaticMesh::StaticClass()->GetClassPathName());
	Filter.PackagePaths.Add(FName(*(FString(TEXT("/Game/Daedalus/Art/Mob/")) + Asset)));
	Filter.bRecursivePaths = true;
	TArray<FAssetData> Found;
	Reg.GetAssets(Filter, Found);
	Found.Sort([](const FAssetData& A, const FAssetData& B) { return A.AssetName.LexicalLess(B.AssetName); });
	for (const FAssetData& A : Found) Paths.Add(A.GetSoftObjectPath());
	if (Paths.Num() == 0) Cache.Remove(Asset);   // not shipped yet: look again next time
	static const TArray<FSoftObjectPath> None;
	const TArray<FSoftObjectPath>* Kept = Cache.Find(Asset);
	return Kept ? *Kept : None;
}

int32 DaedalusMob::Build(AActor* Owner, USceneComponent* Under, const FString& Asset, TArray<UStaticMeshComponent*>* Out,
	float* OutHeight)
{
	if (!Owner || !Under) return 0;
	int32 N = 0;
	float Height = 0.f;
	for (const FSoftObjectPath& P : Parts(Asset))
	{
		UStaticMesh* M = Cast<UStaticMesh>(P.TryLoad());
		if (!M) continue;
		UStaticMeshComponent* C = NewObject<UStaticMeshComponent>(Owner);
		C->SetStaticMesh(M);
		C->SetMobility(EComponentMobility::Movable);
		C->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		C->SetupAttachment(Under);
		C->RegisterComponent();
		Owner->AddInstanceComponent(C);
		Height = FMath::Max(Height, static_cast<float>(M->GetBoundingBox().Max.Z));
		if (Out) Out->Add(C);
		++N;
	}
	if (OutHeight) *OutHeight = Height;
	return N;
}
