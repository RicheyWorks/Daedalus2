#pragma once
#include <string>

namespace DaedalusOceanTravel
{
enum class Vessel { Boat, Submarine };
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
inline Route Board(const std::string& currentRealm, const Dock& departure,
                   const Dock& oceanArrival, Vessel vessel)
{
    if (currentRealm.empty() || departure.Id.empty() || oceanArrival.Id.empty()
        || departure.Realm != currentRealm || currentRealm == "Ocean Realm"
        || oceanArrival.Realm != "Ocean Realm" || oceanArrival.ArrivalAnchor.empty()
        || (vessel == Vessel::Boat && (departure.Underwater || oceanArrival.Underwater)))
        return {};
    return {true, oceanArrival.Realm, oceanArrival.ArrivalAnchor};
}
inline Route Land(const std::string& currentRealm, const Dock& destination,
                  Vessel vessel)
{
    if (currentRealm != "Ocean Realm" || destination.Id.empty()
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
