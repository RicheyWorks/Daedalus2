#include "DaedalusOceanDock.h"
#include "DaedalusHero.h"
#include "DaedalusOceanTravelComponent.h"
#include "GameFramework/Controller.h"

ADaedalusOceanDock::ADaedalusOceanDock()
{
    bReplicates=true;
}
FString ADaedalusOceanDock::Prompt(const ADaedalusHero* Hero) const
{
    if (!IsValid(Vessel) || !IsValid(TravelHost) || DockId.IsEmpty()) return TEXT("Dock unavailable");
    if (Vessel->GetController()) return TEXT("Vessel occupied");
    return Vessel->VesselType==EDaedalusOceanVessel::Submarine ? TEXT("Board submarine") : TEXT("Board boat");
}
bool ADaedalusOceanDock::Use(ADaedalusHero* Hero)
{
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
