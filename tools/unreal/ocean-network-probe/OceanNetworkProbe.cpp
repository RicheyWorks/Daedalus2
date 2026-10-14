#include "OceanNetworkProbe.h"
#include "DaedalusOceanTravelComponent.h"
#include "Engine/World.h"
#include "GameFramework/PlayerStart.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "EngineUtils.h"
#include "InputKeyEventArgs.h"
#include "DaedalusHero.h"
#include "DaedalusOceanDock.h"
#include "DaedalusOceanInteractor.h"
#include "GameFramework/CharacterMovementComponent.h"

AOceanProbeController::AOceanProbeController() { PrimaryActorTick.bCanEverTick=true; }
void AOceanProbeController::Tick(float Dt)
{
    Super::Tick(Dt);
    // No server/controller-side input: observed motion must arrive from the client.
    if (HasAuthority() || !IsLocalController()) return;
    if (FParse::Param(FCommandLine::Get(),TEXT("ProbeDock")))
    {
        if (auto* Hero=Cast<ADaedalusHero>(GetPawn()))
        {
            Hero->GetCharacterMovement()->DisableMovement(); // Stationary interaction fixture.
            if (!DockRequested && Hero->FindComponentByClass<UDaedalusOceanInteractor>())
                if (auto* Dock=Cast<ADaedalusOceanDockControl>(ADaedalusUsable::Nearest(Hero,350));
                    Dock && Dock->Vessel && Dock->TravelHost)
                {
                    Hero->Interact();DockRequested=true;
                    UE_LOG(LogTemp,Display,TEXT("OCEAN_REMOTE_DOCK_REQUEST"));
                }
        }
        if (auto* Vessel=Cast<ADaedalusOceanVessel>(GetPawn());Vessel && Vessel->GetController()==this && !BoardClientLogged)
        {
            const auto Expected=FParse::Param(FCommandLine::Get(),TEXT("ProbeDive"))
                ? EDaedalusOceanVessel::Submarine : EDaedalusOceanVessel::Boat;
            if (Vessel->VesselType!=Expected || Vessel->CurrentRealm!=TEXT("Ocean Realm")) return;
            BoardClientLogged=true;UE_LOG(LogTemp,Display,TEXT("OCEAN_REMOTE_BOARD_CLIENT_POSSESSION"));
        }
        return;
    }
    if (FParse::Param(FCommandLine::Get(),TEXT("ProbeAttack")))
    {
        AttackClock+=Dt;
        if (AttackClock<.2f || !GetPawn()) return;
        AttackClock=0;
        for (TActorIterator<ADaedalusOceanVessel> It(GetWorld());It;++It)
            if (*It!=GetPawn())
            {
                if (!AttackLogged)
                {
                    UE_LOG(LogTemp,Display,TEXT("OCEAN_FOREIGN_RPC_ATTEMPT target=%s owned=%d"),
                           *It->GetName(),It->GetOwner()==this);
                    AttackLogged=true;
                }
                It->SetHelmInput(-1,1,-1);
            }
        return;
    }
    if (auto* Vessel=Cast<ADaedalusOceanVessel>(GetPawn()))
    {
        const bool Dive=FParse::Param(FCommandLine::Get(),TEXT("ProbeDive"));
        const auto Expected=Dive ? EDaedalusOceanVessel::Submarine : EDaedalusOceanVessel::Boat;
        if (Vessel->VesselType!=Expected || Vessel->CurrentRealm!=TEXT("Ocean Realm")
            || Vessel->CruiseSpeedCm!=700 || Vessel->SeaLevelCm!=25 || Vessel->MaxDepthCm!=15000) return;
        if (!IdentityLogged)
        {
            UE_LOG(LogTemp,Display,TEXT("OCEAN_REPLICATED_IDENTITY mode=%s realm=%s speed=%.0f sea=%.0f depth=%.0f"),
                   Dive ? TEXT("submarine") : TEXT("boat"),*Vessel->CurrentRealm,
                   Vessel->CruiseSpeedCm,Vessel->SeaLevelCm,Vessel->MaxDepthCm);
            IdentityLogged=true;
        }
        Elapsed+=Dt;
        if (FParse::Param(FCommandLine::Get(),TEXT("ProbeGamepad")))
        {
            auto Axis=[this](FKey Value,float Amount) {
                InputKey(FInputKeyEventArgs(nullptr,INPUTDEVICEID_NONE,Value,IE_Axis,Amount,false,FPlatformTime::Cycles64()));
            };
            if (Elapsed<3)
            {
                Axis(EKeys::Gamepad_LeftY,1);if (Dive) Axis(EKeys::Gamepad_RightTriggerAxis,1);
                if (!KeysPressed) {KeysPressed=true;UE_LOG(LogTemp,Display,TEXT("OCEAN_ANALOG_INPUT_STARTED"));}
            }
            else if (!KeysReleased)
            {
                Axis(EKeys::Gamepad_LeftY,0);if (Dive) Axis(EKeys::Gamepad_RightTriggerAxis,0);
                KeysReleased=true;UE_LOG(LogTemp,Display,TEXT("OCEAN_ANALOG_INPUT_NEUTRAL"));
            }
        }
        else if (FParse::Param(FCommandLine::Get(),TEXT("ProbeKeyboard")))
        {
            auto Key=[this](FKey Value,EInputEvent Event) {
                InputKey(FInputKeyEventArgs(nullptr,INPUTDEVICEID_NONE,Value,Event,1.f,false,FPlatformTime::Cycles64()));
            };
            if (!KeysPressed)
            {
                Key(EKeys::W,IE_Pressed);if (Dive) Key(EKeys::LeftControl,IE_Pressed);
                KeysPressed=true;UE_LOG(LogTemp,Display,TEXT("OCEAN_KEY_INPUT_PRESSED"));
            }
            if (Elapsed>=3 && !KeysReleased)
            {
                Key(EKeys::W,IE_Released);if (Dive) Key(EKeys::LeftControl,IE_Released);
                KeysReleased=true;UE_LOG(LogTemp,Display,TEXT("OCEAN_KEY_INPUT_RELEASED"));
            }
        }
        else if (Elapsed<3)
            Vessel->SetLocalHelmInput(1,0,FParse::Param(FCommandLine::Get(),TEXT("ProbeDive")) ? -1 : 0);
    }
}
AOceanProbeGameMode::AOceanProbeGameMode()
{
    PrimaryActorTick.bCanEverTick=true;
    DefaultPawnClass=FParse::Param(FCommandLine::Get(),TEXT("ProbeDock"))
        ? ADaedalusHero::StaticClass() : ADaedalusOceanVessel::StaticClass();
    PlayerControllerClass=AOceanProbeController::StaticClass();
}
void AOceanProbeGameMode::BeginPlay()
{
    Super::BeginPlay();
    GetWorld()->SpawnActor<APlayerStart>();
}
APawn* AOceanProbeGameMode::SpawnDefaultPawnAtTransform_Implementation(AController* Player, const FTransform& Transform)
{
    if (FParse::Param(FCommandLine::Get(),TEXT("ProbeDock")))
    {
        const FVector Home(0,GetNumPlayers()*1200,25);
        FActorSpawnParameters AvatarSpawn;AvatarSpawn.Owner=Player;
        AvatarSpawn.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
        auto* Hero=GetWorld()->SpawnActor<ADaedalusHero>(Home+FVector(0,-300,75),FRotator::ZeroRotator,AvatarSpawn);
        Hero->SetReplicates(true);Hero->SetReplicateMovement(true);
        Hero->GetCharacterMovement()->DisableMovement();
        UDaedalusOceanInteractor::EnsureOnHero(Hero);
        FActorSpawnParameters PublicSpawn;
        PublicSpawn.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
        auto* Vessel=GetWorld()->SpawnActor<ADaedalusOceanVessel>(Home,FRotator::ZeroRotator,PublicSpawn);
        Vessel->CurrentRealm=TEXT("Ocean Realm");Vessel->SeaLevelCm=25;
        Vessel->VesselType=FParse::Param(FCommandLine::Get(),TEXT("ProbeDive"))
            ? EDaedalusOceanVessel::Submarine : EDaedalusOceanVessel::Boat;
        auto* Dock=GetWorld()->SpawnActor<ADaedalusOceanDockControl>(Home+FVector(0,-150,75),FRotator::ZeroRotator,PublicSpawn);
        auto* Travel=NewObject<UDaedalusOceanTravelComponent>(Dock);
        Dock->AddInstanceComponent(Travel);Travel->RegisterComponent();
        FDaedalusOceanDock Definition;
        Definition.Id=TEXT("harbour");Definition.Realm=Vessel->CurrentRealm;
        Definition.ArrivalAnchor=TEXT("harbour_arrival");Definition.BoardingLocation=Home;
        Definition.ExitLocation=Home+FVector(0,300,75);
        Travel->ConfigureHost({Vessel->CurrentRealm},{Definition},{});
        Dock->DockId=Definition.Id;Dock->TravelHost=Dock;Dock->Vessel=Vessel;
        Target=Vessel;DockHero=Hero;
        return Hero;
    }
    FActorSpawnParameters Spawn;
    Spawn.Owner=Player;
    Spawn.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    // Separate collision-enabled hulls; no spawn adjustment along the measured X axis.
    return GetWorld()->SpawnActor<ADaedalusOceanVessel>(FVector(0,GetNumPlayers()*1200,25),FRotator::ZeroRotator,Spawn);
}
void AOceanProbeGameMode::Tick(float Dt)
{
    Super::Tick(Dt); Elapsed+=Dt;
    if (FParse::Param(FCommandLine::Get(),TEXT("ProbeDock")))
    {
        auto* Player=GetWorld()->GetFirstPlayerController();
        if (Player && Target.IsValid() && DockHero.IsValid() && Player->GetPawn()==Target.Get()
            && Target->GetController()==Player && DockHero->IsHidden() && !DockHero->GetActorEnableCollision())
        {
            BoardTime+=Dt;
            if (BoardTime>2)
            {
                UE_LOG(LogTemp,Display,TEXT("OCEAN_REMOTE_BOARD_PASS mode=%s authority_possession=1 saved_avatar_hidden=1"),
                    FParse::Param(FCommandLine::Get(),TEXT("ProbeDive")) ? TEXT("submarine") : TEXT("boat"));
                FPlatformMisc::RequestExitWithStatus(false,0);
            }
        }
        if (Elapsed>45) {UE_LOG(LogTemp,Error,TEXT("OCEAN_REMOTE_BOARD_FAIL timeout"));FPlatformMisc::RequestExitWithStatus(false,1);}
        return;
    }
    const bool NonOwner=FParse::Param(FCommandLine::Get(),TEXT("ProbeNonOwner"));
    for (TActorIterator<ADaedalusOceanVessel> It(GetWorld());It;++It)
    {
        It->CurrentRealm=TEXT("Ocean Realm");
        It->CruiseSpeedCm=700; It->SeaLevelCm=25; It->MaxDepthCm=15000;
        if (FParse::Param(FCommandLine::Get(),TEXT("ProbeDive")))
            It->VesselType=EDaedalusOceanVessel::Submarine;
        if (!Target.IsValid() && It->GetActorLocation().X>100) Target=*It;
    }
    auto* Vessel=Target.Get();
    if (Vessel)
    {
        const bool Dive=FParse::Param(FCommandLine::Get(),TEXT("ProbeDive"));
        Vessel->VesselType=Dive ? EDaedalusOceanVessel::Submarine : EDaedalusOceanVessel::Boat;
        const FVector Position=Vessel->GetActorLocation();
        if (Position.X>100 && (!Dive || Position.Z<-100)) Moved=true;
        StillTime=(Moved && FVector::DistSquared(Position,Previous)<.01) ? StillTime+Dt : 0;
        Previous=Position;
        if (Moved && StillTime>2 && (!NonOwner || GetNumPlayers()>=2))
        {
            UE_LOG(LogTemp,Display,TEXT("OCEAN_NETWORK_PASS mode=%s x=%.3f z=%.3f stopped=%.3f"),
                   Dive ? TEXT("submarine") : TEXT("boat"),Position.X,Position.Z,StillTime);
            FPlatformMisc::RequestExitWithStatus(false,0);
        }
    }
    if (Elapsed>45)
    {
        UE_LOG(LogTemp,Error,TEXT("OCEAN_NETWORK_FAIL timeout moved=%d"),Moved);
        FPlatformMisc::RequestExitWithStatus(false,1);
    }
}
