#include "DaedalusOceanTravelComponent.h"
#include "Engine/World.h"
#include "GameFramework/Controller.h"
#include "Components/StaticMeshComponent.h"

namespace
{
std::string Utf8(const FString& Text)
{
    const FTCHARToUTF8 Converted(*Text, Text.Len());
    return std::string(Converted.Get(), Converted.Length());
}
bool Finite(const FVector& Position)
{
    return FMath::IsFinite(Position.X) && FMath::IsFinite(Position.Y)
        && FMath::IsFinite(Position.Z);
}
}

ADaedalusOceanVessel::ADaedalusOceanVessel()
{
    VesselMesh = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("VesselMesh"));
    SetRootComponent(VesselMesh);
    bReplicates = true;
    SetReplicateMovement(true);
}

bool UDaedalusOceanTravelComponent::IsHost() const
{
    return IsValid(GetOwner()) && GetOwner()->HasAuthority() && GetWorld()
        && GetWorld()->GetNetMode() != NM_Client;
}

bool UDaedalusOceanTravelComponent::ConfigureHost(const TArray<FString>& RegisteredRealms,
    const TArray<FDaedalusOceanDock>& Docks, const TArray<FDaedalusOceanConnection>& Connections)
{
    if (!IsHost() || RegisteredRealms.Num() > 32 || Docks.Num() > 1024
        || Connections.Num() > 4096) return false;
    std::vector<std::string> Realms;
    std::vector<DaedalusOceanTravel::Dock> CoreDocks;
    std::vector<DaedalusOceanTravel::DockConnection> CoreConnections;
    for (const auto& Realm : RegisteredRealms) Realms.push_back(Utf8(Realm));
    for (const auto& Dock : Docks)
    {
        if (!Finite(Dock.BoardingLocation) || !FMath::IsFinite(Dock.BoardingRadiusCm)
            || Dock.BoardingRadiusCm <= 0 || Dock.BoardingRadiusCm > 10000) return false;
        CoreDocks.push_back({Utf8(Dock.Id), Utf8(Dock.Realm), Utf8(Dock.ArrivalAnchor), Dock.bUnderwater});
    }
    for (const auto& Connection : Connections)
        CoreConnections.push_back({Utf8(Connection.DepartureId), Utf8(Connection.DestinationId),
            Connection.bBoats, Connection.bSubmarines});
    // Build both next states before publishing either one.
    DaedalusOceanTravel::DockRegistry NextRegistry;
    auto NextDocks = Docks;
    if (!NextRegistry.Configure(Realms, CoreDocks, CoreConnections)) return false;
    Registry = MoveTemp(NextRegistry);
    ActiveDocks = MoveTemp(NextDocks);
    return true;
}

bool UDaedalusOceanTravelComponent::ResolveForPlayer(AController* Player,
    ADaedalusOceanVessel* Vessel, const FString& DepartureId, const FString& DestinationId,
    FString& DestinationRealm, FString& ArrivalAnchor) const
{
    DestinationRealm.Reset();
    ArrivalAnchor.Reset();
    if (!IsHost() || !IsValid(Player) || !IsValid(Vessel) || !Player->HasAuthority()
        || !Vessel->HasAuthority() || Player->GetWorld() != GetWorld()
        || Vessel->GetWorld() != GetWorld() || Player->GetPawn() != Vessel
        || Vessel->GetController() != Player) return false;
    DaedalusOceanTravel::Vessel Kind;
    switch (Vessel->VesselType)
    {
    case EDaedalusOceanVessel::Boat: Kind = DaedalusOceanTravel::Vessel::Boat; break;
    case EDaedalusOceanVessel::Submarine: Kind = DaedalusOceanTravel::Vessel::Submarine; break;
    default: return false;
    }
    const FVector Location = Vessel->GetActorLocation();
    if (!Finite(Location)) return false;
    const auto* Dock = ActiveDocks.FindByPredicate([&](const FDaedalusOceanDock& Candidate) {
        return Candidate.Id == DepartureId;
    });
    if (!Dock || FVector::DistSquared(Location, Dock->BoardingLocation)
        > Dock->BoardingRadiusCm * Dock->BoardingRadiusCm) return false;
    const auto Route = Registry.Resolve(Utf8(Vessel->CurrentRealm), Utf8(DepartureId),
                                       Utf8(DestinationId), Kind);
    if (!Route.Allowed) return false;
    DestinationRealm = UTF8_TO_TCHAR(Route.DestinationRealm.c_str());
    ArrivalAnchor = UTF8_TO_TCHAR(Route.ArrivalAnchor.c_str());
    return true;
}
