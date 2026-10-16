#include "../DaedalusLink/Source/DaedalusLink/Public/DaedalusOceanTravelCore.h"
#include <cstdlib>
#include "../DaedalusLink/Source/DaedalusLink/Public/DaedalusRealmSessionCore.h"
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
    // The actual existing session owns accepted departure; requested targets do not.
    const Dock wz{"wz","WORLD-ZERO","wz_shore",false};
    const Dock canonicalPortal{"portal","PORTAL","portal_shore",false};
    const Dock canonicalSea{"sea","OCEAN","sea_pier",false};
    const Dock canonicalSub{"sea-sub","OCEAN","sea_airlock",true};
    const Dock canonicalGallery{"gallery","GALLERY-CITY","gallery_airlock",true};
    const std::vector<std::string> canonicalRealms{"WORLD-ZERO","PORTAL","OCEAN","GALLERY-CITY"};
    const std::vector<Dock> canonicalDocks{wz,canonicalPortal,canonicalSea,canonicalSub,canonicalGallery};
    const std::vector<DockConnection> canonicalEdges{{"wz","sea",true,true},{"sea","wz",true,true},
        {"portal","sea",true,true},{"sea","portal",true,true},{"sea-sub","gallery",false,true}};
    DockRegistry bound;
    CHECK(bound.Configure(canonicalRealms,canonicalDocks,canonicalEdges));
    daedalus::session::Session session;
    const auto before=session.Save();
    const auto outbound=bound.Resolve(session.Current(),"wz","sea",Vessel::Boat,session.SailedFrom());
    CHECK(outbound.Allowed && outbound.DestinationRealm=="OCEAN");
    CHECK(session.Save()==before); // Eligibility alone must not apply a realm switch.
    const auto enter=session.Go(outbound.DestinationRealm,daedalus::session::Via::Dock,"boat:wz");
    CHECK(enter.Ok && session.Current()=="WORLD-ZERO" && session.SailedFrom().empty());
    session.Apply(enter);
    CHECK(session.Current()=="OCEAN" && session.SailedFrom()=="WORLD-ZERO");
    const auto atSea=session.Save();
    const auto wrong=bound.Resolve(session.Current(),"sea","portal",Vessel::Boat,session.SailedFrom());
    CHECK(!wrong.Allowed && wrong.DestinationRealm.empty() && wrong.ArrivalAnchor.empty());
    CHECK(!session.Go("PORTAL",daedalus::session::Via::Shore).Ok);
    CHECK(session.Save()==atSea);
    CHECK(!bound.Resolve("OCEAN","sea","wz",Vessel::Boat,"").Allowed);
    CHECK(!bound.Resolve("OCEAN","sea","portal",Vessel::Boat,"").Allowed);
    CHECK(!bound.Resolve("WORLD-ZERO","sea","wz",Vessel::Boat,"WORLD-ZERO").Allowed);
    CHECK(!bound.Resolve("Ocean Realm","sea","wz",Vessel::Boat,"WORLD-ZERO").Allowed); // Exact registry spelling.
    CHECK(!bound.Resolve("OCEAN","sea-sub","gallery",Vessel::Boat,session.SailedFrom()).Allowed);
    CHECK(bound.Resolve("OCEAN","sea-sub","gallery",Vessel::Submarine,session.SailedFrom()).Allowed);
    CHECK(!bound.Resolve("OCEAN","sea","wz",static_cast<Vessel>(99),session.SailedFrom()).Allowed);
    CHECK(!bound.Resolve("OCEAN","sea","missing",Vessel::Boat,session.SailedFrom()).Allowed);
    const auto inbound=bound.Resolve(session.Current(),"sea","wz",Vessel::Boat,session.SailedFrom());
    CHECK(inbound.Allowed && inbound.DestinationRealm==session.SailedFrom());
    const auto returnHome=session.Go(inbound.DestinationRealm,daedalus::session::Via::Shore);
    CHECK(returnHome.Ok && session.Save()==atSea);
    session.Apply(returnHome);
    CHECK(session.Current()=="WORLD-ZERO" && session.SailedFrom().empty());
    // Legacy registry stays valid; canonical session IDs are not silently aliased.
    CHECK(Board("Portal Realm",home,sea,Vessel::Boat).Allowed);
    CHECK(Land("Ocean Realm",home,Vessel::Boat,"PORTAL").Allowed);
    CHECK(!Board("PORTAL",home,sea,Vessel::Boat).Allowed);
    CHECK(!bound.Configure({"WORLD-ZERO","PORTAL","Portal Realm","OCEAN","GALLERY-CITY"},canonicalDocks,canonicalEdges));
    CHECK(bound.Resolve("WORLD-ZERO","wz","sea",Vessel::Boat,"").Allowed);
    std::cout << "OCEAN_TRAVEL_PASS " << checks << " checks\n";
}
