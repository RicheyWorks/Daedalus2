#include "DaedalusOceanTravelComponent.h"
#include "DaedalusRealmSessionCore.h"
#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "Components/BoxComponent.h"
#include "Camera/CameraTypes.h"

// Source-authored regression only: this package has not compiled or run it.
// Uses the existing session policy as the departure authority; no host/loader
// activation, realm aliases in Session, or client-supplied departure is added.
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDaedalusOceanCanonicalDepartureTest,
    "Daedalus.Ocean.CanonicalDeparturePolicy",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FDaedalusOceanCanonicalDepartureTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    using namespace DaedalusOceanTravel;
    const Dock Portal{"portal","PORTAL","portal_shore",false};
    const Dock WorldZero{"wz","WORLD-ZERO","wz_shore",false};
    const Dock Sea{"sea","OCEAN","sea_pier",false};
    const Dock SeaSub{"sea-sub","OCEAN","sea_airlock",true};
    const Dock Gallery{"gallery","GALLERY-CITY","gallery_airlock",true};
    const Dock GalleryShore{"gallery-shore","GALLERY-CITY","gallery_shore",false};
    const Dock LegacyHome{"legacy-home","Portal Realm","legacy_shore",false};
    const Dock LegacySea{"legacy-sea","Ocean Realm","legacy_pier",false};
    TestTrue(TEXT("Canonical Ocean recognised"),IsOceanRealm("OCEAN"));
    TestTrue(TEXT("Legacy Ocean recognised"),IsOceanRealm("Ocean Realm"));
    TestTrue(TEXT("Canonical Portal recognised"),IsPortalRealm("PORTAL"));
    TestTrue(TEXT("Legacy Portal recognised"),IsPortalRealm("Portal Realm"));
    TestFalse(TEXT("No guessed lowercase Ocean alias"),IsOceanRealm("ocean"));
    TestTrue(TEXT("Legacy boarding remains compatible"),Board("Portal Realm",LegacyHome,LegacySea,Vessel::Boat).Allowed);
    TestTrue(TEXT("Legacy default shore remains Portal only"),Land("Ocean Realm",LegacyHome,Vessel::Boat).Allowed);
    TestFalse(TEXT("Legacy default does not authorize World Zero"),Land("Ocean Realm",WorldZero,Vessel::Boat).Allowed);
    TestTrue(TEXT("Canonical Portal boarding"),Board("PORTAL",Portal,Sea,Vessel::Boat).Allowed);
    TestTrue(TEXT("Canonical World Zero boarding"),Board("WORLD-ZERO",WorldZero,Sea,Vessel::Boat).DestinationRealm=="OCEAN");
    TestFalse(TEXT("Boat cannot board underwater arrival"),Board("WORLD-ZERO",WorldZero,SeaSub,Vessel::Boat).Allowed);
    TestTrue(TEXT("Submarine can board underwater arrival"),Board("WORLD-ZERO",WorldZero,SeaSub,Vessel::Submarine).Allowed);

    DockRegistry Registry;
    const std::vector<std::string> Realms{"WORLD-ZERO","PORTAL","OCEAN","GALLERY-CITY"};
    const std::vector<Dock> Docks{WorldZero,Portal,Sea,SeaSub,Gallery,GalleryShore};
    const std::vector<DockConnection> Connections{
        {"wz","sea",true,true},{"portal","sea",true,true},
        {"sea","wz",true,true},{"sea","portal",true,true},
        {"sea","gallery-shore",true,true},{"sea-sub","gallery",false,true}};
    TestTrue(TEXT("Trusted registry can declare potential canonical shore edges"),Registry.Configure(Realms,Docks,Connections));

    daedalus::session::Session Session;
    const auto Enter=Session.Go("OCEAN",daedalus::session::Via::Dock,"boat:wz");
    TestTrue(TEXT("Existing session accepts World Zero boat departure"),Enter.Ok);
    Session.Apply(Enter);
    TestTrue(TEXT("Existing session owns the remembered departure"),Session.SailedFrom()=="WORLD-ZERO");
    const auto Home=Registry.Resolve(Session.Current(),"sea","wz",Vessel::Boat,Session.SailedFrom());
    TestTrue(TEXT("World Zero shore return matches authoritative session departure"),Home.Allowed && Home.DestinationRealm=="WORLD-ZERO" && Home.ArrivalAnchor=="wz_shore");
    TestFalse(TEXT("Configured Portal shore still refused for World Zero passenger"),Registry.Resolve(Session.Current(),"sea","portal",Vessel::Boat,Session.SailedFrom()).Allowed);
    TestFalse(TEXT("Configured unrelated shore refused"),Registry.Resolve(Session.Current(),"sea","gallery-shore",Vessel::Boat,Session.SailedFrom()).Allowed);
    TestFalse(TEXT("Missing remembered departure fails closed"),Registry.Resolve("OCEAN","sea","wz",Vessel::Boat,"").Allowed);
    TestFalse(TEXT("Ocean cannot be a remembered shore realm"),Land("OCEAN",WorldZero,Vessel::Boat,"OCEAN").Allowed);
    TestFalse(TEXT("Unknown destination has no configured route"),Registry.Resolve("OCEAN","sea","unknown",Vessel::Boat,Session.SailedFrom()).Allowed);
    TestFalse(TEXT("Wrong current realm cannot use ocean departure"),Registry.Resolve("WORLD-ZERO","sea","wz",Vessel::Boat,Session.SailedFrom()).Allowed);
    TestFalse(TEXT("Boat cannot use an underwater dock edge"),Registry.Resolve("OCEAN","sea-sub","gallery",Vessel::Boat,Session.SailedFrom()).Allowed);
    TestTrue(TEXT("Submarine underwater link remains independent of shore return"),Registry.Resolve("OCEAN","sea-sub","gallery",Vessel::Submarine,Session.SailedFrom()).Allowed);
    TestFalse(TEXT("Invalid vessel enum refused"),Registry.Resolve("OCEAN","sea","wz",static_cast<Vessel>(99),Session.SailedFrom()).Allowed);
    TestFalse(TEXT("Malformed remembered departure refused"),Land("OCEAN",WorldZero,Vessel::Boat,"WORLD-ZERO\n").Allowed);
    TestTrue(TEXT("Legacy Portal departure identity matches canonical shore"),Land("OCEAN",Portal,Vessel::Boat,"Portal Realm").Allowed);

    auto DuplicateDocks=Docks;
    DuplicateDocks.push_back(WorldZero);
    TestFalse(TEXT("Duplicate dock reload rejected"),Registry.Configure(Realms,DuplicateDocks,Connections));
    auto DuplicateConnections=Connections;
    DuplicateConnections.push_back(Connections.front());
    TestFalse(TEXT("Duplicate edge reload rejected"),Registry.Configure(Realms,Docks,DuplicateConnections));
    TestFalse(TEXT("Unknown dock edge rejected"),Registry.Configure(Realms,Docks,{{"wz","unknown",true,false}}));
    TestFalse(TEXT("Unknown dock realm rejected"),Registry.Configure({"WORLD-ZERO","OCEAN"},Docks,Connections));
    TestFalse(TEXT("Alias duplicate realm registration rejected"),Registry.Configure({"WORLD-ZERO","PORTAL","Portal Realm","OCEAN","GALLERY-CITY"},Docks,Connections));
    TestFalse(TEXT("Boat/underwater configuration rejected"),Registry.Configure(Realms,Docks,{{"wz","sea-sub",true,false}}));
    TestTrue(TEXT("Failed reloads preserve last accepted World Zero route"),Registry.Resolve("OCEAN","sea","wz",Vessel::Boat,Session.SailedFrom()).Allowed);
    TestFalse(TEXT("Session itself refuses wrong shore"),Session.Go("PORTAL",daedalus::session::Via::Shore).Ok);
    const auto Return=Session.Go(Home.DestinationRealm,daedalus::session::Via::Shore);
    TestTrue(TEXT("Accepted core destination fits existing session shore contract"),Return.Ok);
    Session.Apply(Return);
    TestTrue(TEXT("Returned session clears its remembered departure"),Session.Current()=="WORLD-ZERO" && Session.SailedFrom().empty());
    return true;
}

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
