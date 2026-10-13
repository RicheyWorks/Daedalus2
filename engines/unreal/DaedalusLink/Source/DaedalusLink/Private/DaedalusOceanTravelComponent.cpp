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
        if (!Finite(Dock.BoardingLocation) || !Finite(Dock.ExitLocation)
            || !FMath::IsFinite(Dock.BoardingRadiusCm)
            || Dock.BoardingRadiusCm <= 0 || Dock.BoardingRadiusCm > 10000) return false;
        if (FVector::DistSquared(Dock.ExitLocation, Dock.BoardingLocation)
            > Dock.BoardingRadiusCm * Dock.BoardingRadiusCm) return false;
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

bool UDaedalusOceanTravelComponent::BoardAtDock(AController* Player,
    ADaedalusOceanVessel* Vessel, const FString& DockId)
{
    if (!IsHost() || !IsValid(Player) || !IsValid(Vessel) || !Player->HasAuthority()
        || !Vessel->HasAuthority() || Player->GetWorld() != GetWorld()
        || Vessel->GetWorld() != GetWorld() || Vessel->GetController()) return false;
    APawn* Avatar = Player->GetPawn();
    if (!IsValid(Avatar) || Avatar == Vessel || Avatar->GetWorld() != GetWorld()
        || !Avatar->HasAuthority() || Avatar->GetController() != Player) return false;
    // Do not replace a live boarding session with another avatar or vessel.
    if (const auto* Prior = BoardingAvatars.Find(Player); Prior && Prior->IsValid()) return false;
    if (Vessel->VesselType != EDaedalusOceanVessel::Boat
        && Vessel->VesselType != EDaedalusOceanVessel::Submarine) return false;
    const auto* Dock = ActiveDocks.FindByPredicate([&](const FDaedalusOceanDock& Candidate) {
        return Candidate.Id == DockId;
    });
    if (!Dock || Dock->Realm != Vessel->CurrentRealm
        || (Dock->bUnderwater && Vessel->VesselType == EDaedalusOceanVessel::Boat)) return false;
    for (APawn* Pawn : {Avatar, static_cast<APawn*>(Vessel)})
    {
        const FVector Position = Pawn->GetActorLocation();
        if (!Finite(Position) || FVector::DistSquared(Position, Dock->BoardingLocation)
            > Dock->BoardingRadiusCm * Dock->BoardingRadiusCm) return false;
    }
    Player->Possess(Vessel);
    if (Player->GetPawn() != Vessel || Vessel->GetController() != Player) return false;
    BoardingAvatars.Add(Player, Avatar);
    return true;
}

bool UDaedalusOceanTravelComponent::DisembarkAtDock(AController* Player,
    ADaedalusOceanVessel* Vessel, const FString& DockId)
{
    if (!IsHost() || !IsValid(Player) || !IsValid(Vessel) || !Player->HasAuthority()
        || !Vessel->HasAuthority() || Player->GetWorld() != GetWorld()
        || Vessel->GetWorld() != GetWorld() || Player->GetPawn() != Vessel
        || Vessel->GetController() != Player) return false;
    const auto* Original = BoardingAvatars.Find(Player);
    APawn* Avatar = Original ? Original->Get() : nullptr;
    if (!IsValid(Avatar) || Avatar == Vessel || !Avatar->HasAuthority()
        || Avatar->GetWorld() != GetWorld() || Avatar->GetController()) return false;
    const auto* Dock = ActiveDocks.FindByPredicate([&](const FDaedalusOceanDock& Candidate) {
        return Candidate.Id == DockId;
    });
    const FVector Position = Vessel->GetActorLocation();
    if (!Dock || Dock->Realm != Vessel->CurrentRealm || !Finite(Position)
        || FVector::DistSquared(Position, Dock->BoardingLocation)
            > Dock->BoardingRadiusCm * Dock->BoardingRadiusCm) return false;
    // Collision-aware teleport refuses an obstructed exit before possession changes.
    if (!Avatar->TeleportTo(Dock->ExitLocation, Avatar->GetActorRotation(), false, false)) return false;
    Player->Possess(Avatar);
    if (Player->GetPawn() != Avatar || Avatar->GetController() != Player) return false;
    BoardingAvatars.Remove(Player);
    return true;
}
