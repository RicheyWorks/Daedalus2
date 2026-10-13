#include "../DaedalusLink/Source/DaedalusLink/Public/DaedalusOceanTravelCore.h"
#include <iostream>
using namespace DaedalusOceanTravel;
#define CHECK(x) do { if (!(x)) return 1; ++checks; } while (0)
int main()
{
    int checks=0;
    const Dock home{"home", "Portal Realm", "home_pier", false};
    const Dock sea{"sea", "Ocean Realm", "sea_pier", false};
    const Dock reef{"reef", "Ocean Realm", "reef_airlock", true};
    const Dock gallery{"gallery", "Gallery City", "gallery_airlock", true};
    CHECK(Board("Portal Realm",home,sea,Vessel::Boat).Allowed);
    CHECK(Board("Portal Realm",home,reef,Vessel::Submarine).Allowed);
    CHECK(!Board("Portal Realm",home,reef,Vessel::Boat).Allowed);
    CHECK(!Board("Gallery City",home,sea,Vessel::Boat).Allowed);
    CHECK(Land("Ocean Realm",home,Vessel::Boat).DestinationRealm=="Portal Realm");
    CHECK(Land("Ocean Realm",gallery,Vessel::Submarine).DestinationRealm=="Gallery City");
    CHECK(!Land("Ocean Realm",gallery,Vessel::Boat).Allowed);
    CHECK(!Land("Portal Realm",home,Vessel::Boat).Allowed);
    CHECK(!Land("Ocean Realm",{"bad","Gallery City","surface",false},Vessel::Boat).Allowed);
    CHECK(!Land("Ocean Realm",{"bad","Portal Realm","",false},Vessel::Boat).Allowed);
    std::cout << "OCEAN_TRAVEL_PASS " << checks << " checks\n";
}
