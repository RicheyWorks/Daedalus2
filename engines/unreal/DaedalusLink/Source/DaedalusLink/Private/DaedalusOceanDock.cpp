#include "DaedalusOceanDock.h"
#include "DaedalusHero.h"
#include "DaedalusOceanTravelComponent.h"
#include "GameFramework/Controller.h"
#include "GameFramework/PlayerController.h"
#include "DaedalusOceanInteractor.h"
#include "Net/UnrealNetwork.h"

ADaedalusOceanDockControl::ADaedalusOceanDockControl()
{
    bReplicates=true;
}
FString ADaedalusOceanDockControl::Prompt(const ADaedalusHero* Hero) const
{
    if (!IsValid(Vessel) || !IsValid(TravelHost) || DockId.IsEmpty()) return TEXT("Dock unavailable");
    if (Vessel->GetController()) return TEXT("Vessel occupied");
    return Vessel->VesselType==EDaedalusOceanVessel::Submarine ? TEXT("Board submarine") : TEXT("Board boat");
}
bool ADaedalusOceanDockControl::Use(ADaedalusHero* Hero)
{
    if (!HasAuthority())
    {
        if (!IsValid(Hero) || Hero->GetWorld()!=GetWorld()) return false;
        auto* Player=Cast<APlayerController>(Hero->GetController());
        auto* Interactor=Hero->FindComponentByClass<UDaedalusOceanInteractor>();
        if (!IsValid(Player) || !Player->IsLocalController() || Player->GetPawn()!=Hero || !Interactor) return false;
        Interactor->RequestDockUse(this);
        return true; // Request queued; server possession is the success signal.
    }
    if (!HasAuthority() || !IsValid(Hero) || !Hero->HasAuthority()
        || Hero->GetWorld()!=GetWorld() || !IsValid(Vessel) || !IsValid(TravelHost)
        || TravelHost->GetWorld()!=GetWorld() || Vessel->GetWorld()!=GetWorld()
        || !FMath::IsFinite(InteractionReachCm) || InteractionReachCm<=0 || InteractionReachCm>1000) return false;
    const double Distance=FVector::DistSquared(Hero->GetActorLocation(),GetActorLocation());
    if (!FMath::IsFinite(Distance) || Distance>InteractionReachCm*InteractionReachCm) return false;
    auto* Travel=TravelHost->FindComponentByClass<UDaedalusOceanTravelComponent>();
    auto* Player=Hero->GetController();
    if (!Travel || !IsValid(Player) || Player->GetPawn()!=Hero) return false;
    return Travel->BoardAtDock(Player,Vessel,DockId);
}
void ADaedalusOceanDockControl::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);
    DOREPLIFETIME(ADaedalusOceanDockControl,DockId);
    DOREPLIFETIME(ADaedalusOceanDockControl,TravelHost);
    DOREPLIFETIME(ADaedalusOceanDockControl,Vessel);
    DOREPLIFETIME(ADaedalusOceanDockControl,InteractionReachCm);
}
bool ADaedalusOceanDockControl::ExitVessel(ADaedalusOceanVessel* OccupiedVessel)
{
    if (!HasAuthority() || !IsValid(OccupiedVessel) || !OccupiedVessel->HasAuthority()
        || OccupiedVessel->GetWorld()!=GetWorld() || !IsValid(TravelHost)
        || TravelHost->GetWorld()!=GetWorld() || !FMath::IsFinite(InteractionReachCm)
        || InteractionReachCm<=0 || InteractionReachCm>1000) return false;
    const double Distance=FVector::DistSquared(OccupiedVessel->GetActorLocation(),GetActorLocation());
    if (!FMath::IsFinite(Distance) || Distance>InteractionReachCm*InteractionReachCm) return false;
    auto* Player=Cast<APlayerController>(OccupiedVessel->GetController());
    auto* Travel=TravelHost->FindComponentByClass<UDaedalusOceanTravelComponent>();
    if (!IsValid(Player) || Player->GetPawn()!=OccupiedVessel || !Travel) return false;
    return Travel->DisembarkAtDock(Player,OccupiedVessel,DockId);
}
