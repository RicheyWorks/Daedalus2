// SPDX-License-Identifier: MIT
// The realm session rules (hub 28885): every row of the table and every refusal.
//   g++ -std=c++17 -O2 -Wall -Wextra -I ../DaedalusLink/Source/DaedalusLink/Public realm_session_test.cpp -o session_test && ./session_test

#include "DaedalusRealmSessionCore.h"

#include <cstdlib>
#include <iostream>

using namespace daedalus::session;

static int Ok = 0, Total = 0;
static void Check(const std::string& Name, bool Cond, const std::string& Why = "")
{
    ++Total;
    Ok += Cond;
    std::cout << (Cond ? "PASS " : "FAIL ") << Name << (Cond || Why.empty() ? "" : "  " + Why) << "\n";
}

int main()
{
    Session S;
    Check("a session starts in World Zero", S.Current() == "WORLD-ZERO" && S.Switches() == 0);
    Check("the seven realms are known", Realms().size() == 7 && Find("OCEAN") && !Find("MARS"));

    // gates
    Change C = S.Go("GALLERY-CITY", Via::Gate);
    Check("a gate from World Zero reaches Gallery City with its theme and catalog", C.Ok && C.Theme == "gallery" && C.Catalog == "gallery-city" && C.Hint == "gate:WORLD-ZERO", C.Why);
    S.Apply(C);
    Check("the session moved", S.Current() == "GALLERY-CITY" && S.Switches() == 1);
    Check("a gate between two 3D realms is refused", !S.Go("PARCELS", Via::Gate).Ok && S.Go("PARCELS", Via::Gate).Why.find("World Zero") != std::string::npos);
    Check("the same realm is refused", !S.Go("GALLERY-CITY", Via::Gate).Ok);
    Check("home is always one gate away", S.Go("WORLD-ZERO", Via::Gate).Ok && S.Go("WORLD-ZERO", Via::Gate).Hint == "gate:GALLERY-CITY");
    Check("the Ocean has no gate", [&] { Session Z; return !Z.Go("OCEAN", Via::Gate).Ok; }());

    // the portal
    C = S.Go("PORTAL", Via::Portal);
    Check("a portal from Gallery City enters the 8-bit realm in its retro theme", C.Ok && C.Theme == "retro" && C.Catalog.empty() && C.Hint == "spawn", C.Why);
    S.Apply(C);
    Check("the realm remembers where the portal came from", S.PortalFrom() == "GALLERY-CITY");
    Check("a second portal from inside is refused", !S.Go("PORTAL", Via::Portal).Ok);
    Check("the portal only leads back where you came from", !S.Go("PARCELS", Via::Portal).Ok && S.Go("GALLERY-CITY", Via::Portal).Ok && S.Go("GALLERY-CITY", Via::Portal).Hint == "portal");

    // Dragon Warrior docks: a boat into the Ocean, a shore back
    C = S.Go("OCEAN", Via::Dock, "boat:ashdale-pier");
    Check("a boat at a Dragon Warrior dock enters the Ocean", C.Ok && C.Hint == "dock:ashdale-pier" && C.Theme == "ocean", C.Why);
    Check("a dock needs a vehicle and an id", !S.Go("OCEAN", Via::Dock, "cart:x").Ok && !S.Go("OCEAN", Via::Dock, "boat").Ok);
    S.Apply(C);
    Check("the Ocean remembers the departure", S.Current() == "OCEAN" && S.SailedFrom() == "PORTAL");
    Check("a shore landing returns to the departure realm only", S.Go("PORTAL", Via::Shore).Ok && S.Go("PORTAL", Via::Shore).Hint == "shore" && !S.Go("PARCELS", Via::Shore).Ok);
    Check("a boat cannot use a destination dock", !S.Go("GALLERY-CITY", Via::Dock, "boat:vat-pier").Ok && S.Go("GALLERY-CITY", Via::Dock, "boat:vat-pier").Why.find("shore") != std::string::npos);
    Check("a submarine reaches a realm with an underwater dock", S.Go("GALLERY-CITY", Via::Dock, "sub:vat-pier").Ok && S.Go("LABYRINTH", Via::Dock, "sub:deep-gate").Ok);
    Check("but not one without", !S.Go("BRICKS", Via::Dock, "sub:x").Ok && !S.Go("WORLD-ZERO", Via::Dock, "sub:x").Ok);
    Check("a shore landing is the Ocean's alone", [&] { Session Z; return !Z.Go("PARCELS", Via::Shore).Ok; }());
    Check("a realm without docks can't launch", [&] { Session Z; Z.Apply(Z.Go("LABYRINTH", Via::Gate)); return !Z.Go("OCEAN", Via::Dock, "boat:x").Ok; }());

    // save and restore
    const std::string Saved = S.Save();
    Session R;
    Check("a session saves to one line and comes back", R.Restore(Saved) && R.Current() == "OCEAN" && R.SailedFrom() == "PORTAL" && R.PortalFrom() == "GALLERY-CITY" && R.Switches() == 3, Saved);
    Check("a bad save line is refused and leaves World Zero", !Session().Restore("MARS - - 0") && Session().Current() == "WORLD-ZERO");
    S.Apply(S.Go("PORTAL", Via::Shore));
    Check("after the landing the departure is cleared", S.Current() == "PORTAL" && S.SailedFrom().empty() && S.Describe().find("sailed_from=-") != std::string::npos, S.Describe());
    Check("unknown realms are refused with a reason", S.Go("MARS", Via::Gate).Why == "no realm MARS");

    std::cout << Ok << "/" << Total << "\n";
    return Ok == Total ? 0 : 1;
}
