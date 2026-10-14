#include "../DaedalusLink/Source/DaedalusLink/Public/DaedalusOceanTravelCore.h"
#include <iostream>
#include <cstdlib>
#include "../DaedalusLink/Source/DaedalusLink/Public/DaedalusRealmSessionCore.h"
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
    DockRegistry registry;
    const std::vector<std::string> realms{"Portal Realm","Ocean Realm","Gallery City"};
    const std::vector<Dock> docks{home,sea,reef,gallery};
    const std::vector<DockConnection> connections{{"home","sea",true,true},
        {"sea","home",true,true},{"reef","gallery",false,true}};
    CHECK(!registry.Resolve("Portal Realm","home","sea",Vessel::Boat).Allowed);
    CHECK(registry.Configure(realms,docks,connections));
    CHECK(registry.Resolve("Portal Realm","home","sea",Vessel::Boat).ArrivalAnchor=="sea_pier");
    CHECK(registry.Resolve("Ocean Realm","sea","home",Vessel::Boat).DestinationRealm=="Portal Realm");
    CHECK(registry.Resolve("Ocean Realm","reef","gallery",Vessel::Submarine).ArrivalAnchor=="gallery_airlock");
    CHECK(!registry.Resolve("Ocean Realm","reef","gallery",Vessel::Boat).Allowed);
    CHECK(!registry.Resolve("Gallery City","gallery","reef",Vessel::Submarine).Allowed);
    CHECK(!registry.Resolve("Portal Realm","home","reef",Vessel::Submarine).Allowed);
    CHECK(!registry.Resolve("Gallery City","home","sea",Vessel::Boat).Allowed);
    CHECK(!registry.Resolve("Portal Realm","home","invented",Vessel::Boat).Allowed);
    CHECK(!registry.Resolve("Portal Realm","home","sea",static_cast<Vessel>(99)).Allowed);
    CHECK(!registry.Configure({"Portal Realm"},docks,connections));
    auto duplicateDocks=docks;duplicateDocks.push_back(home);
    CHECK(!registry.Configure(realms,duplicateDocks,connections));
    auto duplicateConnections=connections;duplicateConnections.push_back(connections[0]);
    CHECK(!registry.Configure(realms,docks,duplicateConnections));
    CHECK(!registry.Configure(realms,docks,{{"home","missing",true,false}}));
    CHECK(!registry.Configure(realms,docks,{{"home","home",true,false}}));
    CHECK(!registry.Configure(realms,docks,{{"home","sea",false,false}}));
    CHECK(!registry.Configure(realms,docks,{{"reef","gallery",true,true}}));
    CHECK(!registry.Configure(realms,docks,{{"sea","gallery",false,true},{"gallery","home",false,true}}));
    CHECK(!registry.Configure({"Portal Realm","Ocean Realm","Gallery City","Ocean Realm"},docks,connections));
    CHECK(!registry.Configure(realms,{},connections));
    // Every failed reload above preserves the last accepted routes.
    CHECK(registry.Resolve("Portal Realm","home","sea",Vessel::Boat).ArrivalAnchor=="sea_pier");
    CHECK(registry.Configure(realms,docks,{}));
    CHECK(!registry.Resolve("Portal Realm","home","sea",Vessel::Boat).Allowed);
    // Use the exact IDs emitted by the native session and Java realm directory.
    const Dock canonicalHome{"home", "PORTAL", "home_pier", false};
    const Dock canonicalSea{"sea", "OCEAN", "sea_pier", false};
    const Dock canonicalReef{"reef", "OCEAN", "reef_airlock", true};
    const Dock canonicalGallery{"gallery", "GALLERY-CITY", "gallery_airlock", true};
    DockRegistry canonical;
    const std::vector<std::string> canonicalRealms{"PORTAL","OCEAN","GALLERY-CITY"};
    CHECK(canonical.Configure(canonicalRealms,{canonicalHome,canonicalSea,canonicalReef,canonicalGallery},connections));
    daedalus::session::Session session;
    auto enterPortal=session.Go("PORTAL",daedalus::session::Via::Portal);
    CHECK(enterPortal.Ok);session.Apply(enterPortal);
    const auto out=canonical.Resolve(session.Current(),"home","sea",Vessel::Boat);
    CHECK(out.Allowed && out.DestinationRealm=="OCEAN");
    auto board=session.Go(out.DestinationRealm,daedalus::session::Via::Dock,"boat:home");
    CHECK(board.Ok);session.Apply(board);
    const auto back=canonical.Resolve(session.Current(),"sea","home",Vessel::Boat);
    CHECK(back.Allowed && back.DestinationRealm=="PORTAL");
    CHECK(session.Go(back.DestinationRealm,daedalus::session::Via::Shore).Ok);
    const auto sub=canonical.Resolve(session.Current(),"reef","gallery",Vessel::Submarine);
    CHECK(sub.Allowed && sub.DestinationRealm=="GALLERY-CITY");
    CHECK(session.Go(sub.DestinationRealm,daedalus::session::Via::Dock,"sub:gallery").Ok);
    CHECK(!canonical.Resolve("OCEAN","reef","gallery",Vessel::Boat).Allowed);
    CHECK(!Board("OCEAN",canonicalSea,canonicalReef,Vessel::Submarine).Allowed);
    CHECK(!Land("OCEAN",canonicalSea,Vessel::Submarine).Allowed);
    CHECK(!Board("PORTAL",canonicalHome,{"bad","ocean","bad",false},Vessel::Boat).Allowed);
    auto aliases=canonicalRealms;aliases.push_back("Ocean Realm");
    CHECK(!canonical.Configure(aliases,{canonicalHome,canonicalSea},{}));
    aliases=canonicalRealms;aliases.push_back("Portal Realm");
    CHECK(!canonical.Configure(aliases,{canonicalHome,canonicalSea},{}));
    CHECK(canonical.Resolve("PORTAL","home","sea",Vessel::Boat).DestinationRealm=="OCEAN");
    const Dock galleryShore{"gallery_shore","GALLERY-CITY","gallery_shore_anchor",false};
    DockRegistry returning;
    CHECK(returning.Configure(canonicalRealms,{canonicalHome,canonicalSea,galleryShore},
        {{"gallery_shore","sea",true,true},{"sea","gallery_shore",true,true},{"sea","home",true,true}}));
    CHECK(returning.Resolve("GALLERY-CITY","gallery_shore","sea",Vessel::Boat,"").Allowed);
    CHECK(returning.Resolve("OCEAN","sea","gallery_shore",Vessel::Boat,"GALLERY-CITY").Allowed);
    CHECK(returning.Resolve("OCEAN","sea","gallery_shore",Vessel::Submarine,"GALLERY-CITY").Allowed);
    CHECK(!returning.Resolve("OCEAN","sea","gallery_shore",Vessel::Boat,"PORTAL").Allowed);
    CHECK(!returning.Resolve("OCEAN","sea","gallery_shore",Vessel::Boat,"").Allowed);
    CHECK(!returning.Resolve("OCEAN","sea","home",Vessel::Boat,"GALLERY-CITY").Allowed);
    CHECK(!returning.Resolve("OCEAN","sea","home",Vessel::Boat,"").Allowed);
    CHECK(!returning.Resolve("OCEAN","sea","gallery_shore",Vessel::Boat,"OCEAN").Allowed);
    CHECK(!returning.Resolve("OCEAN","sea","gallery_shore",Vessel::Boat,std::string("GALLERY-CITY\0",13)).Allowed);
    CHECK(canonical.Resolve("OCEAN","reef","gallery",Vessel::Submarine,"").Allowed);
    CHECK(!canonical.Resolve("OCEAN","reef","gallery",Vessel::Boat,"GALLERY-CITY").Allowed);
    CHECK(!returning.Resolve("OCEAN","sea","missing",Vessel::Boat,"GALLERY-CITY").Allowed);
    CHECK(!returning.Resolve("OCEAN","sea","gallery_shore",Vessel::Boat).Allowed);
    std::cout << "OCEAN_TRAVEL_PASS " << checks << " checks\n";
}
