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
    // Network/Blueprint integer casts must not become a submarine by default.
    for (int value : {-1,2,3,255,65535})
    {
        const auto invalid=static_cast<Vessel>(value);
        const auto boarding=Board("Portal Realm",home,reef,invalid);
        const auto landing=Land("Ocean Realm",gallery,invalid);
        CHECK(!boarding.Allowed && boarding.DestinationRealm.empty() && boarding.ArrivalAnchor.empty());
        CHECK(!landing.Allowed && landing.DestinationRealm.empty() && landing.ArrivalAnchor.empty());
    }
    for (const auto& invalid : {std::string(),std::string("bad\nanchor"),
                                std::string("bad\0anchor",10),std::string(129,'a')})
    {
        for (int field=0;field<3;++field)
        {
            Dock badHome=home,badSea=sea,badGallery=gallery;
            auto change=[&](Dock& dock) {
                if (field==0) dock.Id=invalid;
                else if (field==1) dock.Realm=invalid;
                else dock.ArrivalAnchor=invalid;
            };
            change(badHome);change(badSea);change(badGallery);
            CHECK(!Board("Portal Realm",badHome,sea,Vessel::Submarine).Allowed);
            CHECK(!Board("Portal Realm",home,badSea,Vessel::Submarine).Allowed);
            CHECK(!Land("Ocean Realm",badGallery,Vessel::Submarine).Allowed);
        }
    }
    const Dock longAnchor{"boundary","Ocean Realm",std::string(128,'a'),false};
    CHECK(Board("Portal Realm",home,longAnchor,Vessel::Boat).ArrivalAnchor==longAnchor.ArrivalAnchor);
    CHECK(Board("Gallery City",gallery,reef,Vessel::Submarine).Allowed);
    CHECK(!Board("Gallery City",gallery,sea,Vessel::Boat).Allowed);
    std::cout << "OCEAN_TRAVEL_PASS " << checks << " checks\n";
}
