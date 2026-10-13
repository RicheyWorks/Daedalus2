#include "OceanNetworkProbe.h"
#include "DaedalusOceanTravelComponent.h"
#include "Engine/World.h"
#include "GameFramework/PlayerStart.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "EngineUtils.h"

AOceanProbeController::AOceanProbeController() { PrimaryActorTick.bCanEverTick=true; }
void AOceanProbeController::Tick(float Dt)
{
    Super::Tick(Dt);
    // No server/controller-side input: observed motion must arrive from the client.
    if (HasAuthority() || !IsLocalController()) return;
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
        Elapsed+=Dt;
        if (Elapsed<3)
            Vessel->SetHelmInput(1,0,FParse::Param(FCommandLine::Get(),TEXT("ProbeDive")) ? -1 : 0);
    }
}
AOceanProbeGameMode::AOceanProbeGameMode()
{
    PrimaryActorTick.bCanEverTick=true;
    DefaultPawnClass=ADaedalusOceanVessel::StaticClass();
    PlayerControllerClass=AOceanProbeController::StaticClass();
}
void AOceanProbeGameMode::BeginPlay()
{
    Super::BeginPlay();
    GetWorld()->SpawnActor<APlayerStart>();
}
void AOceanProbeGameMode::Tick(float Dt)
{
    Super::Tick(Dt); Elapsed+=Dt;
    const bool NonOwner=FParse::Param(FCommandLine::Get(),TEXT("ProbeNonOwner"));
    for (TActorIterator<ADaedalusOceanVessel> It(GetWorld());It;++It)
    {
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
