#pragma once
#include <string>
#include <vector>

namespace DaedalusOceanTravel
{
enum class Vessel { Boat, Submarine };
inline bool ValidVessel(Vessel vessel)
{
    return vessel == Vessel::Boat || vessel == Vessel::Submarine;
}
inline bool ValidIdentifier(const std::string& text)
{
    if (text.empty() || text.size() > 128) return false;
    for (unsigned char c : text)
        if (c < 32 || c == 127) return false;
    return true;
}
struct Dock
{
    std::string Id;
    std::string Realm;
    std::string ArrivalAnchor;
    bool Underwater = false;
};
struct Route
{
    bool Allowed = false;
    std::string DestinationRealm;
    std::string ArrivalAnchor;
};
// Session/realm-directory IDs are canonical; retain the original display-name contracts.
// Registries should use one spelling consistently, never both aliases as separate realms.
inline bool IsOceanRealm(const std::string& realm) { return realm == "OCEAN" || realm == "Ocean Realm"; }
inline bool IsPortalRealm(const std::string& realm) { return realm == "PORTAL" || realm == "Portal Realm"; }
inline bool SameRealmIdentity(const std::string& a, const std::string& b)
{
    return a == b || (IsOceanRealm(a) && IsOceanRealm(b)) || (IsPortalRealm(a) && IsPortalRealm(b));
}
inline bool ValidDock(const Dock& dock)
{
    return ValidIdentifier(dock.Id) && ValidIdentifier(dock.Realm)
        && ValidIdentifier(dock.ArrivalAnchor);
}
inline Route Board(const std::string& currentRealm, const Dock& departure,
                   const Dock& oceanArrival, Vessel vessel)
{
    if (!ValidVessel(vessel) || !ValidIdentifier(currentRealm)
        || !ValidDock(departure) || !ValidDock(oceanArrival)
        || departure.Realm != currentRealm || IsOceanRealm(currentRealm)
        || !IsOceanRealm(oceanArrival.Realm) || oceanArrival.ArrivalAnchor.empty()
        || (vessel == Vessel::Boat && (departure.Underwater || oceanArrival.Underwater)))
        return {};
    return {true, oceanArrival.Realm, oceanArrival.ArrivalAnchor};
}
inline Route Land(const std::string& currentRealm, const Dock& destination,
                  Vessel vessel, const std::string& shoreReturnRealm = "Portal Realm")
{
    if (!ValidVessel(vessel) || !ValidDock(destination)
        || !IsOceanRealm(currentRealm) || destination.Id.empty()
        || destination.Realm.empty() || IsOceanRealm(destination.Realm)
        || destination.ArrivalAnchor.empty()
        || (vessel == Vessel::Boat && destination.Underwater))
        return {};
    // The caller supplies its host-owned departure record, never a requested destination.
    // The legacy three-argument API retains its original Portal-only shore behavior.
    if (!destination.Underwater && (!ValidIdentifier(shoreReturnRealm)
        || IsOceanRealm(shoreReturnRealm) || !SameRealmIdentity(destination.Realm, shoreReturnRealm))) return {};
    return {true, destination.Realm, destination.ArrivalAnchor};
}

struct DockConnection
{
    std::string DepartureId;
    std::string DestinationId;
    bool Boats = false;
    bool Submarines = false;
};

// Configure from trusted host data, never from an individual travel request.
// Connections are directed: a return trip must be configured separately.
class DockRegistry
{
    std::vector<Dock> Docks;
    std::vector<DockConnection> Connections;
    static const Dock* Find(const std::vector<Dock>& docks, const std::string& id)
    {
        for (const auto& dock : docks) if (dock.Id == id) return &dock;
        return nullptr;
    }
    static Route ResolvePair(const Dock& from, const Dock& to, Vessel vessel,
                             const std::string& shoreReturnRealm = "Portal Realm")
    {
        if (IsOceanRealm(from.Realm))
        {
            if (vessel == Vessel::Boat && from.Underwater) return {};
            return Land(from.Realm, to, vessel, shoreReturnRealm);
        }
        return Board(from.Realm, from, to, vessel);
    }
public:
    bool Configure(const std::vector<std::string>& registeredRealms,
                   const std::vector<Dock>& docks,
                   const std::vector<DockConnection>& connections)
    {
        if (registeredRealms.empty() || registeredRealms.size() > 32
            || docks.empty() || docks.size() > 1024 || connections.size() > 4096)
            return false;
        for (std::size_t i=0;i<registeredRealms.size();++i)
        {
            if (!ValidIdentifier(registeredRealms[i])) return false;
            for (std::size_t j=0;j<i;++j)
                if (SameRealmIdentity(registeredRealms[i], registeredRealms[j])) return false;
        }
        for (std::size_t i=0;i<docks.size();++i)
        {
            if (!ValidDock(docks[i])) return false;
            bool registered=false;
            for (const auto& realm : registeredRealms)
                registered |= realm == docks[i].Realm;
            if (!registered) return false;
            for (std::size_t j=0;j<i;++j)
                if (docks[i].Id == docks[j].Id) return false;
        }
        for (std::size_t i=0;i<connections.size();++i)
        {
            const auto& connection=connections[i];
            if (!connection.Boats && !connection.Submarines) return false;
            const Dock* from=Find(docks,connection.DepartureId);
            const Dock* to=Find(docks,connection.DestinationId);
            if (!from || !to || from == to) return false;
            // A configured shore edge is only potential. Resolve checks the actual passenger departure.
            if (connection.Boats && !ResolvePair(*from,*to,Vessel::Boat,to->Realm).Allowed) return false;
            if (connection.Submarines && !ResolvePair(*from,*to,Vessel::Submarine,to->Realm).Allowed) return false;
            for (std::size_t j=0;j<i;++j)
                if (connections[j].DepartureId == connection.DepartureId
                    && connections[j].DestinationId == connection.DestinationId) return false;
        }
        // Validation finishes before replacing the active configuration.
        auto nextDocks=docks;
        auto nextConnections=connections;
        Docks.swap(nextDocks);
        Connections.swap(nextConnections);
        return true;
    }
    Route Resolve(const std::string& currentRealm, const std::string& departureId,
                  const std::string& destinationId, Vessel vessel,
                  const std::string& shoreReturnRealm = "Portal Realm") const
    {
        if (!ValidVessel(vessel) || !ValidIdentifier(currentRealm)
            || !ValidIdentifier(departureId) || !ValidIdentifier(destinationId)) return {};
        const Dock* from=Find(Docks,departureId);
        const Dock* to=Find(Docks,destinationId);
        if (!from || !to || from->Realm != currentRealm) return {};
        for (const auto& connection : Connections)
            if (connection.DepartureId == departureId && connection.DestinationId == destinationId
                && ((vessel == Vessel::Boat && connection.Boats)
                    || (vessel == Vessel::Submarine && connection.Submarines)))
                return ResolvePair(*from,*to,vessel,shoreReturnRealm);
        return {};
    }
};
}
