#include "DaedalusOceanDock.h"
#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "Engine/World.h"
#include "DaedalusHero.h"
#include "DaedalusOceanTravelComponent.h"
#include "DaedalusOceanInteractor.h"
#include "GameFramework/PlayerController.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDaedalusOceanDockTest,"Daedalus.Ocean.HeroDockInteraction",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FDaedalusOceanDockTest::RunTest(const FString& Parameters)
{
    UWorld* World=UWorld::CreateWorld(EWorldType::Game,false);
    if (!TestNotNull(TEXT("Test world"),World)) return false;
    World->InitializeActorsForPlay(FURL());
    auto* Player=World->SpawnActor<APlayerController>();
    auto* Hero=World->SpawnActor<ADaedalusHero>(FVector(0,-300,0),FRotator::ZeroRotator);
    auto* Vessel=World->SpawnActor<ADaedalusOceanVessel>();
    auto* Dock=World->SpawnActor<ADaedalusOceanDockControl>(FVector(0,-150,0),FRotator::ZeroRotator);
    AActor* Host=World->SpawnActor<AActor>();
    auto* Travel=NewObject<UDaedalusOceanTravelComponent>(Host);
    Host->AddInstanceComponent(Travel);Travel->RegisterComponent();
    Player->Possess(Hero);Vessel->CurrentRealm=TEXT("Ocean Realm");
    auto* Interactor=UDaedalusOceanInteractor::EnsureOnHero(Hero);
    TestNotNull(TEXT("Host attaches owned interactor"),Interactor);
    TestTrue(TEXT("Attachment is idempotent"),UDaedalusOceanInteractor::EnsureOnHero(Hero)==Interactor);
    Interactor->RequestDockUse(nullptr);
    TestTrue(TEXT("Null dock request retains hero"),Player->GetPawn()==Hero);
    FDaedalusOceanDock Definition;
    Definition.Id=TEXT("harbour");Definition.Realm=Vessel->CurrentRealm;
    Definition.ArrivalAnchor=TEXT("harbour_arrival");Definition.ExitLocation=FVector(0,300,0);
    TestTrue(TEXT("Host dock configured"),Travel->ConfigureHost({Vessel->CurrentRealm},{Definition},{}));
    TestFalse(TEXT("Unconfigured control point refuses"),Dock->Use(Hero));
    TestTrue(TEXT("Refusal retains hero"),Player->GetPawn()==Hero);
    Dock->DockId=Definition.Id;Dock->TravelHost=Host;Dock->Vessel=Vessel;
    TestEqual(TEXT("Boat prompt"),Dock->Prompt(Hero),FString(TEXT("Board boat")));
    Hero->SetActorLocation(FVector(0,-1000,0));
    TestFalse(TEXT("Remote interaction refuses"),Dock->Use(Hero));
    Hero->SetActorLocation(FVector(0,-300,0));
    TestTrue(TEXT("Existing usable lookup finds dock"),ADaedalusUsable::Nearest(Hero,350)==Dock);
    TestTrue(TEXT("Existing hero Interact executes"),Hero->Interact());
    TestTrue(TEXT("Existing path actually boards vessel"),Player->GetPawn()==Vessel);
    TestEqual(TEXT("Occupied prompt"),Dock->Prompt(Hero),FString(TEXT("Vessel occupied")));
    TestFalse(TEXT("Unpossessed hero cannot reuse dock"),Dock->Use(Hero));
    TestTrue(TEXT("Existing exit restores hero"),Travel->DisembarkAtDock(Player,Vessel,Definition.Id));
    TestTrue(TEXT("Hero restored"),Player->GetPawn()==Hero);
    Hero->SetActorLocation(FVector(0,-300,0));
    Interactor->RequestDockUse(Dock);
    TestTrue(TEXT("Owned endpoint boards validated hero"),Player->GetPawn()==Vessel);
    World->DestroyWorld(false);return true;
}
#endif
