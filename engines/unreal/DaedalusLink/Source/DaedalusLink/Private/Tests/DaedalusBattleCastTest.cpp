#include "DaedalusBattlePresentation.h"
#if WITH_DEV_AUTOMATION_TESTS && WITH_EDITOR
#include "Misc/AutomationTest.h"
#include "AssetRegistry/AssetRegistryModule.h"
#include "Animation/AnimSequence.h"
#include "Animation/Skeleton.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"
#include "UObject/Package.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDaedalusBattleCastTest,"Daedalus.Battle.CastAnimations",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FDaedalusBattleCastTest::RunTest(const FString& Parameters)
{
    UWorld* World=UWorld::CreateWorld(EWorldType::Game,false);
    if (!TestNotNull(TEXT("Battle test world"),World)) return false;
    World->InitializeActorsForPlay(FURL());
    auto* Stage=World->SpawnActor<ADaedalusBattlePresentation>();
    TArray<UObject*> Registered;
    auto MakeClip=[&](UPackage* Package,const TCHAR* Name,USkeleton* Skeleton) {
        auto* Clip=NewObject<UAnimSequence>(Package,FName(Name),RF_Public|RF_Standalone);
        Clip->SetSkeleton(Skeleton);FAssetRegistryModule::AssetCreated(Clip);Registered.Add(Clip);return Clip;
    };
    auto MakeActor=[&](const TCHAR* Id,USkeleton* Skeleton) {
        const FString Folder=FString(TEXT("/Game/Daedalus/Art/Cast/"))+Id;
        auto* Package=CreatePackage(*(Folder+TEXT("/Mesh")));
        auto* Mesh=NewObject<USkeletalMesh>(Package,FName(TEXT("Mesh")),RF_Public|RF_Standalone);
        Mesh->SetSkeleton(Skeleton);
        auto* Actor=World->SpawnActor<AActor>();
        auto* Component=NewObject<USkeletalMeshComponent>(Actor);
        Actor->AddInstanceComponent(Component);Component->SetSkeletalMesh(Mesh);
        return Actor;
    };
    auto* SkeletonA=NewObject<USkeleton>();auto* SkeletonB=NewObject<USkeleton>();
    // Unique folders keep reruns independent and never write assets to disk.
    const FString Run=FGuid::NewGuid().ToString(EGuidFormats::Digits);
    const FString IdA=TEXT("TestA_")+Run,IdB=TEXT("TestB_")+Run;
    auto* A=MakeActor(*IdA,SkeletonA);auto* B=MakeActor(*IdB,SkeletonB);
    auto* PackageA=CreatePackage(*(TEXT("/Game/Daedalus/Art/Cast/")+IdA+TEXT("/Clips")));
    auto* PackageB=CreatePackage(*(TEXT("/Game/Daedalus/Art/Cast/")+IdB+TEXT("/Clips")));
    MakeClip(PackageA,TEXT("A_Attack"),SkeletonB); // Earlier name, wrong skeleton.
    auto* AttackA=MakeClip(PackageA,TEXT("B_Attack"),SkeletonA);
    auto* HurtA=MakeClip(PackageA,TEXT("B_Hurt"),SkeletonA);
    auto* AttackB=MakeClip(PackageB,TEXT("B_Attack"),SkeletonB);
    Stage->Members={A,B};Stage->RefreshCastAnimations();
    TestEqual(TEXT("First actor receives its own attack"),Stage->ResolveCastAnimation(A,false),AttackA);
    TestEqual(TEXT("Second skeleton receives its own attack"),Stage->ResolveCastAnimation(B,false),AttackB);
    TestEqual(TEXT("Hurt selects target-compatible clip"),Stage->ResolveCastAnimation(A,true),HurtA);
    TestNull(TEXT("Missing hurt never borrows another cast"),Stage->ResolveCastAnimation(B,true));
    Stage->AttackAnimation=AttackA;
    TestEqual(TEXT("Compatible explicit override retained"),Stage->ResolveCastAnimation(A,false),AttackA);
    TestEqual(TEXT("Incompatible override falls back to own cast"),Stage->ResolveCastAnimation(B,false),AttackB);
    TestNull(TEXT("Null actor refused"),Stage->ResolveCastAnimation(nullptr,false));
    TestNull(TEXT("Actor without skeletal mesh refused"),Stage->ResolveCastAnimation(World->SpawnActor<AActor>(),false));
    for (auto* Object:Registered){FAssetRegistryModule::AssetDeleted(Object);Object->ClearFlags(RF_Standalone);}
    World->DestroyWorld(false);
    return true;
}
#endif
