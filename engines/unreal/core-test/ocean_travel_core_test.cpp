#include "../DaedalusLink/Source/DaedalusLink/Public/DaedalusOceanTravelCore.h"
#include <cstdlib>
#include "../DaedalusLink/Source/DaedalusLink/Public/DaedalusRealmSessionCore.h"
#include <iostream>
using namespace DaedalusOceanTravel;
#define CHECK(x) do { if (!(x)) { std::cerr << "CHECK failed at line " << __LINE__ << ": " #x "\n"; return 1; } ++checks; } while (0)
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
    // Capability definitions are the independent session oracle. Do not maintain
    // a second hard-coded list of dock/underwater realms in these regressions.
    const auto& capabilities=daedalus::session::Realms();
    std::vector<std::string> matrixRealms;
    std::vector<Dock> matrixDocks{{"matrix-sea","OCEAN","matrix-pier",false}};
    std::vector<DockConnection> matrixEdges;
    for (const auto& realm : capabilities)
    {
        matrixRealms.push_back(realm.Id);
        if (realm.HasDocks)
        {
            const std::string id="shore-"+realm.Id;
            matrixDocks.push_back({id,realm.Id,"arrival-"+id,false});
            matrixEdges.push_back({id,"matrix-sea",true,true});
            matrixEdges.push_back({"matrix-sea",id,true,true});
        }
        if (realm.HasSubDock)
        {
            const std::string id="sub-"+realm.Id;
            matrixDocks.push_back({id,realm.Id,"arrival-"+id,true});
            matrixEdges.push_back({"matrix-sea",id,false,true});
        }
    }
    DockRegistry matrix;
    CHECK(matrix.Configure(matrixRealms,matrixDocks,matrixEdges));
    int roundTrips=0,underwaterCases=0;
    for (const auto& origin : capabilities)
    {
        if (!origin.HasDocks) continue;
        for (const auto vessel : {Vessel::Boat,Vessel::Submarine})
        {
            daedalus::session::Session trip;
            if (trip.Current()!=origin.Id)
            {
                const auto navigation=trip.Go(origin.Id,origin.Gate
                    ? daedalus::session::Via::Gate : daedalus::session::Via::Portal);
                CHECK(navigation.Ok);
                trip.Apply(navigation);
            }
            CHECK(trip.Current()==origin.Id && trip.SailedFrom().empty());
            const std::string own="shore-"+origin.Id;
            const std::string vehicle=vessel==Vessel::Boat ? "boat:" : "sub:";
            const auto onLand=trip.Save();
            const auto eligible=matrix.Resolve(trip.Current(),own,"matrix-sea",vessel,trip.SailedFrom());
            CHECK(eligible.Allowed && eligible.DestinationRealm=="OCEAN");
            CHECK(trip.Save()==onLand);
            const auto embark=trip.Go(eligible.DestinationRealm,daedalus::session::Via::Dock,vehicle+own);
            CHECK(embark.Ok && trip.Save()==onLand);
            trip.Apply(embark);
            CHECK(trip.Current()=="OCEAN" && trip.SailedFrom()==origin.Id);
            const auto oceanState=trip.Save();
            for (const auto& other : capabilities)
            {
                if (!other.HasDocks || other.Id==origin.Id) continue;
                const auto refused=matrix.Resolve(trip.Current(),"matrix-sea","shore-"+other.Id,vessel,trip.SailedFrom());
                CHECK(!refused.Allowed && refused.DestinationRealm.empty() && refused.ArrivalAnchor.empty());
                CHECK(!trip.Go(other.Id,daedalus::session::Via::Shore).Ok);
                CHECK(trip.Save()==oceanState);
            }
            for (const auto& target : capabilities)
            {
                if (!target.HasSubDock) continue;
                const std::string subDock="sub-"+target.Id;
                CHECK(!matrix.Resolve(trip.Current(),"matrix-sea",subDock,Vessel::Boat,trip.SailedFrom()).Allowed);
                CHECK(!trip.Go(target.Id,daedalus::session::Via::Dock,"boat:"+subDock).Ok);
                const auto dive=matrix.Resolve(trip.Current(),"matrix-sea",subDock,Vessel::Submarine,trip.SailedFrom());
                CHECK(dive.Allowed && dive.DestinationRealm==target.Id);
                CHECK(dive.ArrivalAnchor=="arrival-"+subDock && trip.Save()==oceanState);
                const auto arrive=trip.Go(dive.DestinationRealm,daedalus::session::Via::Dock,"sub:"+subDock);
                CHECK(arrive.Ok && trip.Save()==oceanState);
                auto underwaterTrip=trip; // fork an actually accepted Ocean session
                underwaterTrip.Apply(arrive);
                CHECK(underwaterTrip.Current()==target.Id && underwaterTrip.SailedFrom()==origin.Id);
                const auto underwaterState=underwaterTrip.Save();
                CHECK(!matrix.Resolve(underwaterTrip.Current(),subDock,"matrix-sea",Vessel::Submarine,underwaterTrip.SailedFrom()).Allowed);
                CHECK(underwaterTrip.Save()==underwaterState);
                CHECK(trip.Save()==oceanState);
                ++underwaterCases;
            }
            const auto shore=matrix.Resolve(trip.Current(),"matrix-sea",own,vessel,trip.SailedFrom());
            CHECK(shore.Allowed && shore.DestinationRealm==origin.Id && shore.ArrivalAnchor=="arrival-"+own);
            CHECK(trip.Save()==oceanState);
            const auto land=trip.Go(shore.DestinationRealm,daedalus::session::Via::Shore);
            CHECK(land.Ok && trip.Save()==oceanState);
            trip.Apply(land);
            CHECK(trip.Current()==origin.Id && trip.SailedFrom().empty());
            ++roundTrips;
        }
    }
    std::cout << "OCEAN_CAPABILITY_MATRIX " << roundTrips << " roundtrips "
              << underwaterCases << " underwater cases\n";
    std::cout << "OCEAN_TRAVEL_PASS " << checks << " checks\n";
}
