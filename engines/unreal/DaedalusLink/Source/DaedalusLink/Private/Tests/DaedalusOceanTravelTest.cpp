#include "DaedalusOceanTravelComponent.h"
#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "Components/BoxComponent.h"
#include "Camera/CameraTypes.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDaedalusOceanEligibilityTest,
    "Daedalus.Ocean.HostEligibility",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FDaedalusOceanEligibilityTest::RunTest(const FString& Parameters)
{
    UWorld* World = UWorld::CreateWorld(EWorldType::Game, false);
    if (!TestNotNull(TEXT("Test world"), World)) return false;
    World->InitializeActorsForPlay(FURL());
    TestTrue(TEXT("World actors initialized for RPC dispatch"),World->AreActorsInitialized());
    AActor* Host = World->SpawnActor<AActor>();
    auto* Component = NewObject<UDaedalusOceanTravelComponent>(Host);
    Host->AddInstanceComponent(Component);
    Component->RegisterComponent();
    auto* Player = World->SpawnActor<APlayerController>();
    auto* Stranger = World->SpawnActor<APlayerController>();
    auto* Vessel = World->SpawnActor<ADaedalusOceanVessel>();
    Vessel->CurrentRealm = TEXT("Portal Realm");
    Player->Possess(Vessel);
    FDaedalusOceanDock Home;
    Home.Id=TEXT("home"); Home.Realm=TEXT("Portal Realm"); Home.ArrivalAnchor=TEXT("home_pier");
    Home.BoardingRadiusCm=500;
    Home.ExitLocation=FVector(0,300,0);
    auto Sea=Home; Sea.Id=TEXT("sea"); Sea.Realm=TEXT("Ocean Realm"); Sea.ArrivalAnchor=TEXT("sea_pier");
    FDaedalusOceanConnection Connection;
    Connection.DepartureId=Home.Id; Connection.DestinationId=Sea.Id;
    Connection.bBoats=true; Connection.bSubmarines=true;
    const TArray<FString> Realms{Home.Realm,Sea.Realm};
    TestTrue(TEXT("Configure host"),Component->ConfigureHost(Realms,{Home,Sea},{Connection}));
    FString Realm,Anchor;
    auto Resolve=[&](AController* Controller) {
        return Component->ResolveForPlayer(Controller,Vessel,Home.Id,Sea.Id,Realm,Anchor);
    };
    TestTrue(TEXT("Possessed boat at dock"),Resolve(Player));
    TestEqual(TEXT("Configured realm"),Realm,Sea.Realm);
    TestEqual(TEXT("Configured anchor"),Anchor,Sea.ArrivalAnchor);
    TestFalse(TEXT("Other controller refused"),Resolve(Stranger));
    TestTrue(TEXT("Failure clears outputs"),Realm.IsEmpty() && Anchor.IsEmpty());
    Vessel->SetActorLocation(FVector(500,0,0));
    TestTrue(TEXT("Radius boundary accepted"),Resolve(Player));
    Vessel->SetActorLocation(FVector(501,0,0));
    TestFalse(TEXT("Outside radius refused"),Resolve(Player));
    Vessel->SetActorLocation(FVector::ZeroVector);
    Vessel->VesselType=static_cast<EDaedalusOceanVessel>(99);
    TestFalse(TEXT("Invalid vessel refused"),Resolve(Player));
    Vessel->VesselType=EDaedalusOceanVessel::Submarine;
    TestTrue(TEXT("Possessed submarine"),Resolve(Player));
    Vessel->CurrentRealm=TEXT("Gallery City");
    TestFalse(TEXT("Wrong current realm refused"),Resolve(Player));
    Vessel->CurrentRealm=Home.Realm;
    auto BadHome=Home; BadHome.BoardingRadiusCm=0;
    TestFalse(TEXT("Invalid radius reload"),Component->ConfigureHost(Realms,{BadHome,Sea},{Connection}));
    TestTrue(TEXT("Failed reload preserves route"),Resolve(Player));
    Player->UnPossess();
    TestFalse(TEXT("Unpossessed vessel refused"),Resolve(Player));
    auto* Avatar = World->SpawnActor<ADaedalusOceanVessel>(FVector(0,300,0),FRotator::ZeroRotator);
    if (!TestNotNull(TEXT("Avatar spawn"),Avatar)) {World->DestroyWorld(false);return false;}
    Player->Possess(Avatar);
    Avatar->SetActorLocation(FVector(501,0,0));
    TestFalse(TEXT("Remote avatar cannot board"),Component->BoardAtDock(Player,Vessel,Home.Id));
    TestTrue(TEXT("Rejected boarding retains avatar"),Player->GetPawn()==Avatar);
    Avatar->SetActorLocation(FVector::ZeroVector);
    TestFalse(TEXT("Unknown dock cannot board"),Component->BoardAtDock(Player,Vessel,TEXT("invented")));
    TestTrue(TEXT("Nearby player boards vessel"),Component->BoardAtDock(Player,Vessel,Home.Id));
    TestTrue(TEXT("Boarded avatar hidden and nonblocking"),Avatar->IsHidden() && !Avatar->GetActorEnableCollision());
    TestTrue(TEXT("Boarded vessel can resolve route"),Resolve(Player));
    TestFalse(TEXT("Cannot erase docks during active passenger session"),Component->ConfigureHost(Realms,{},{}));
    TestTrue(TEXT("Refused reload preserves boarded route"),Resolve(Player));
    auto* OtherVessel=World->SpawnActor<ADaedalusOceanVessel>(FVector(0,1000,0),FRotator::ZeroRotator);
    OtherVessel->CurrentRealm=Home.Realm;
    Player->Possess(OtherVessel);OtherVessel->SetActorLocation(FVector::ZeroVector);
    TestFalse(TEXT("Different possessed vessel cannot restore passenger"),Component->DisembarkAtDock(Player,OtherVessel,Home.Id));
    TestTrue(TEXT("Wrong-vessel exit retains current possession"),Player->GetPawn()==OtherVessel);
    TestTrue(TEXT("Wrong-vessel exit preserves saved avatar state"),Avatar->IsHidden() && !Avatar->GetActorEnableCollision());
    Player->Possess(Vessel);OtherVessel->SetActorLocation(FVector(0,1000,0));
    TestFalse(TEXT("Another controller cannot take occupied vessel"),Component->BoardAtDock(Stranger,Vessel,Home.Id));
    TestFalse(TEXT("Unknown exit dock refused"),Component->DisembarkAtDock(Player,Vessel,TEXT("invented")));
    TestTrue(TEXT("Rejected exit retains vessel"),Player->GetPawn()==Vessel);
    Vessel->SetActorLocation(FVector(501,0,0));
    TestFalse(TEXT("Remote vessel cannot disembark"),Component->DisembarkAtDock(Player,Vessel,Home.Id));
    Vessel->SetActorLocation(FVector::ZeroVector);
    TestTrue(TEXT("Dock restores original avatar"),Component->DisembarkAtDock(Player,Vessel,Home.Id));
    TestTrue(TEXT("Original avatar controlled"),Player->GetPawn()==Avatar);
    TestTrue(TEXT("Avatar visibility and collision restored"),!Avatar->IsHidden() && Avatar->GetActorEnableCollision());
    TestTrue(TEXT("Configuration allowed after passenger exits"),Component->ConfigureHost(Realms,{Home,Sea},{Connection}));
    TestFalse(TEXT("Repeated disembark refused"),Component->DisembarkAtDock(Player,Vessel,Home.Id));
    TestTrue(TEXT("New boarding cycle allowed"),Component->BoardAtDock(Player,Vessel,Home.Id));
    Vessel->SetActorLocation(FVector::ZeroVector);
    Vessel->VesselType=EDaedalusOceanVessel::Boat;
    Vessel->SetHelmInput(1,0,-1); Vessel->Tick(.1f);
    TestTrue(TEXT("Boat helm moves forward"),Vessel->GetActorLocation().X>0);
    TestEqual(TEXT("Boat stays at sea level"),Vessel->GetActorLocation().Z,0.0);
    Vessel->VesselType=EDaedalusOceanVessel::Submarine;
    Vessel->SetHelmInput(0,0,-1); Vessel->Tick(.1f);
    TestTrue(TEXT("Submarine dives"),Vessel->GetActorLocation().Z<0);
    Vessel->SetActorLocation(FVector(0,0,-19999));
    Vessel->SetHelmInput(0,0,-1); Vessel->Tick(.1f);
    TestTrue(TEXT("Depth limit enforced"),Vessel->GetActorLocation().Z>=-20000);
    Vessel->SetActorLocation(FVector(0,0,-100));
    Vessel->SetHelmInput(0,0,-1);
    for (int i=0;i<10;++i) Vessel->Tick(.1f);
    const double StoppedDepth=Vessel->GetActorLocation().Z;
    Vessel->Tick(.1f);
    TestEqual(TEXT("Expired dive command stops away from depth boundary"),Vessel->GetActorLocation().Z,StoppedDepth);
    AActor* Wall=World->SpawnActor<AActor>();
    auto* Barrier=NewObject<UBoxComponent>(Wall);
    Wall->AddInstanceComponent(Barrier);Wall->SetRootComponent(Barrier);
    Barrier->SetBoxExtent(FVector(30,500,500));
    Barrier->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
    Barrier->SetCollisionObjectType(ECC_WorldStatic);
    Barrier->SetCollisionResponseToAllChannels(ECR_Block);
    Barrier->SetWorldLocation(FVector(400,0,0));Barrier->RegisterComponent();
    Vessel->VesselType=EDaedalusOceanVessel::Boat;
    Vessel->SetActorLocation(FVector::ZeroVector);Vessel->SetActorRotation(FRotator::ZeroRotator);
    for (int i=0;i<30;++i) {Vessel->SetHelmInput(1,0,0);Vessel->Tick(.1f);}
    TestTrue(TEXT("Hull advances toward barrier"),Vessel->GetActorLocation().X>10);
    TestTrue(TEXT("Hull sweep stops before barrier"),Vessel->GetActorLocation().X<=191);
    FMinimalViewInfo View;
    Vessel->CalcCamera(.016f,View);
    TestTrue(TEXT("Chase camera provides a view behind hull"),View.Location.X<Vessel->GetActorLocation().X-100);
    TestTrue(TEXT("Chase camera provides an elevated view"),View.Location.Z>Vessel->GetActorLocation().Z+100);
    World->DestroyWorld(false);
    return true;
}
#endif
