// SPDX-License-Identifier: MIT
// Mounts per realm (BASE-LAYER row 9): the table, the fallback, the altitude rule.
//   g++ -std=c++17 -O2 -Wall -Wextra -I ../DaedalusLink/Source/DaedalusLink/Public mount_core_test.cpp -o mount_test && ./mount_test
#include "DaedalusMountCore.h"
#include "DaedalusRealmSessionCore.h"
#include <iostream>
using namespace daedalus::mount;
static int Ok = 0, Total = 0;
static void Check(const std::string& N, bool C, const std::string& W = "") { ++Total; Ok += C; std::cout << (C ? "PASS " : "FAIL ") << N << (C || W.empty() ? "" : "  " + W) << "\n"; }
int main()
{
    Check("five profiles, one per realm with a land mount", Profiles().size() == 5);
    Check("every profile's realm is a session realm", [] { for (const Profile& P : Profiles()) if (!daedalus::session::Find(P.Realm)) return false; return true; }());
    Check("Gallery rides the drone, Parcels the helicopter, Bricks the plane, Labyrinth the sky-strider",
          For("GALLERY-CITY").ArtId == "Mob_Gallery_GalleryDrone" && For("PARCELS").ArtId == "Mob_Parcels_ParcelHelicopter" && For("BRICKS").ArtId == "Mob_Bricks_BrickPlane" && For("LABYRINTH").ArtId == "Mob_Lab_SkyStrider");
    Check("World Zero keeps the hover bike (no art, ground-hugging)", For("WORLD-ZERO").ArtId.empty() && !For("WORLD-ZERO").Flies());
    Check("PORTAL and OCEAN fall back to the bike", For("PORTAL").Realm == "WORLD-ZERO" && For("OCEAN").Realm == "WORLD-ZERO");
    Check("the realm mounts fly; the plane fastest and highest", For("BRICKS").Flies() && For("BRICKS").TopCmS > For("GALLERY-CITY").TopCmS && For("BRICKS").CeilingM >= For("PARCELS").CeilingM);
    Check("altitude: a ground-hugger always sits at hover", Altitude(For("WORLD-ZERO"), 5000.0) == 110.0);
    Check("altitude: a flyer is clamped between hover and its ceiling", Altitude(For("PARCELS"), 50.0) == 220.0 && Altitude(For("PARCELS"), 9000.0) == 9000.0 && Altitude(For("PARCELS"), 99999.0) == 20000.0);
    Check("describe", Describe(For("LABYRINTH")) == "mount=sky-strider realm=LABYRINTH art=Mob_Lab_SkyStrider hover=140 top=1300 ceiling_m=60", Describe(For("LABYRINTH")));
    std::cout << Ok << "/" << Total << "\n";
    return Ok == Total ? 0 : 1;
}
