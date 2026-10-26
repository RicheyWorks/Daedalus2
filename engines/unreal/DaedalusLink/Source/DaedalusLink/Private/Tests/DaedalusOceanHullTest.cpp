#include "DaedalusOceanTravelComponent.h"
#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "Engine/World.h"
#include "Components/BoxComponent.h"
#include "GameFramework/PlayerController.h"
#include <limits>

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDaedalusOceanHullTest,"Daedalus.Ocean.HullProfile",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FDaedalusOceanHullTest::RunTest(const FString& Parameters)
{
    UWorld* World=UWorld::CreateWorld(EWorldType::Game,false);
    if (!TestNotNull(TEXT("Hull test world"),World)) return false;
    World->InitializeActorsForPlay(FURL());
    auto* Vessel=World->SpawnActor<ADaedalusOceanVessel>();
    const FVector Skiff(235,95,65),Submarine(280,115,90);
    TestTrue(TEXT("Unoccupied skiff profile accepted"),Vessel->ConfigureHull(Skiff));
    TestEqual(TEXT("Collider receives body dimensions"),Vessel->HullCollision->GetUnscaledBoxExtent(),Skiff);
    TestFalse(TEXT("Tiny dimensions refused"),Vessel->ConfigureHull(FVector(9,95,65)));
    TestFalse(TEXT("Unbounded dimensions refused"),Vessel->ConfigureHull(FVector(5001,95,65)));
    TestFalse(TEXT("Nonfinite dimensions refused"),Vessel->ConfigureHull(FVector(std::numeric_limits<double>::quiet_NaN(),95,65)));
    TestEqual(TEXT("Invalid profile preserves collider"),Vessel->HullHalfExtentCm,Skiff);
    AActor* Wall=World->SpawnActor<AActor>();
    auto* Barrier=NewObject<UBoxComponent>(Wall);
    Wall->AddInstanceComponent(Barrier);Wall->SetRootComponent(Barrier);
    Barrier->SetBoxExtent(FVector(30,500,500));
    Barrier->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
    Barrier->SetCollisionObjectType(ECC_WorldStatic);
    Barrier->SetCollisionResponseToAllChannels(ECR_Block);
    Barrier->SetWorldLocation(FVector(400,0,0));Barrier->RegisterComponent();
    TestFalse(TEXT("Resize into wall refused"),Vessel->ConfigureHull(FVector(380,95,65)));
    TestEqual(TEXT("Overlap refusal preserves profile"),Vessel->HullHalfExtentCm,Skiff);
    auto* Player=World->SpawnActor<APlayerController>();Player->Possess(Vessel);
    TestFalse(TEXT("Occupied resize refused"),Vessel->ConfigureHull(Submarine));
    for(int i=0;i<30;++i){Vessel->SetHelmInput(1,0,0);Vessel->Tick(.1f);}
    TestTrue(TEXT("Fitted skiff advances"),Vessel->GetActorLocation().X>10);
    TestTrue(TEXT("Fitted skiff stops at its body extent"),Vessel->GetActorLocation().X<=136);
    Player->UnPossess();Vessel->SetActorLocation(FVector::ZeroVector);
    TestTrue(TEXT("Submarine profile accepted after unpossess"),Vessel->ConfigureHull(Submarine));
    Player->Possess(Vessel);Vessel->VesselType=EDaedalusOceanVessel::Submarine;
    Vessel->SeaLevelCm=0;
    for(int i=0;i<30;++i){Vessel->SetHelmInput(1,0,0);Vessel->Tick(.1f);}
    TestTrue(TEXT("Fitted submarine stops before wall"),Vessel->GetActorLocation().X<=91);
    World->DestroyWorld(false);
    return true;
}
#endif
