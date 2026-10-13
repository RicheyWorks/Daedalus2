#pragma once
#include <string>

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
        || departure.Realm != currentRealm || currentRealm == "Ocean Realm"
        || oceanArrival.Realm != "Ocean Realm" || oceanArrival.ArrivalAnchor.empty()
        || (vessel == Vessel::Boat && (departure.Underwater || oceanArrival.Underwater)))
        return {};
    return {true, oceanArrival.Realm, oceanArrival.ArrivalAnchor};
}
inline Route Land(const std::string& currentRealm, const Dock& destination,
                  Vessel vessel)
{
    if (!ValidVessel(vessel) || !ValidDock(destination)
        || currentRealm != "Ocean Realm" || destination.Id.empty()
        || destination.Realm.empty() || destination.Realm == "Ocean Realm"
        || destination.ArrivalAnchor.empty()
        || (vessel == Vessel::Boat && destination.Underwater))
        return {};
    // Other worlds require their configured underwater docks. Ordinary shores
    // return to Portal/Dragon Warrior land, never an arbitrary requested realm.
    if (!destination.Underwater && destination.Realm != "Portal Realm") return {};
    return {true, destination.Realm, destination.ArrivalAnchor};
}
}
