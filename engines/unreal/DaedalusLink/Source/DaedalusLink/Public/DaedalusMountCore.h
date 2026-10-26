// SPDX-License-Identifier: MIT

#pragma once

// Mounts per realm (BASE-LAYER.md row 9, REALM-CASTS.md: "Gallery City (mount: drone)", "The Parcels (mount:
// helicopter)", "Brick Realm (mount: plane)", "Labyrinth (mount: sky-strider)"). The hero's CallVehicle spawns the
// hover bike (ADaedalusGhost); in a realm the bike wears that realm's mount (Sol's rigged export, imported under
// /Game/Daedalus/Art/Creatures/<ArtId>) and flies with that mount's profile. Pure C++17: mount_core_test proves the
// table; the Ghost applies it.

#include <string>
#include <vector>

namespace daedalus
{
namespace mount
{

struct Profile
{
    std::string Realm;      // session realm id
    std::string Name;       // what the realm calls it
    std::string ArtId;      // Sol's export id (a creature with Idle/Walk clips)
    double HoverCm = 110.0; // resting height over the ground
    double TopCmS = 1900.0; // cruise
    double BoostCmS = 3200.0;
    double CeilingM = 0.0;  // 0 = hugs the ground (hover bike); >0 = can climb to this height over the ground
    double ScaleArt = 1.0;  // the art's scale on the frame
    bool Flies() const { return CeilingM > 0.0; }
};

inline const std::vector<Profile>& Profiles()
{
    static const std::vector<Profile> P = {
        {"WORLD-ZERO", "hover bike", "", 110.0, 1900.0, 3200.0, 0.0, 1.0},
        {"GALLERY-CITY", "gallery drone", "Mob_Gallery_GalleryDrone", 160.0, 1600.0, 2600.0, 120.0, 1.0},
        {"PARCELS", "parcel helicopter", "Mob_Parcels_ParcelHelicopter", 220.0, 1700.0, 2800.0, 200.0, 1.0},
        {"BRICKS", "brick plane", "Mob_Bricks_BrickPlane", 180.0, 2400.0, 4200.0, 240.0, 1.0},
        {"LABYRINTH", "sky-strider", "Mob_Lab_SkyStrider", 140.0, 1300.0, 2000.0, 60.0, 1.0},
    };
    return P;
}

/** The mount for a realm; World Zero's bike for a realm without one (PORTAL, OCEAN: no land mount). */
inline const Profile& For(const std::string& Realm)
{
    for (const Profile& P : Profiles()) if (P.Realm == Realm) return P;
    return Profiles()[0];
}

/** Where a flying mount may be this frame: clamp a requested height over the ground to the profile's ceiling,
 *  never below hover. Ground-huggers always return HoverCm. */
inline double Altitude(const Profile& P, double WantedOverGroundCm)
{
    if (!P.Flies()) return P.HoverCm;
    const double Max = P.CeilingM * 100.0;
    return WantedOverGroundCm < P.HoverCm ? P.HoverCm : (WantedOverGroundCm > Max ? Max : WantedOverGroundCm);
}

inline std::string Describe(const Profile& P)
{
    return "mount=" + P.Name + " realm=" + P.Realm + " art=" + (P.ArtId.empty() ? "-" : P.ArtId) + " hover=" + std::to_string(static_cast<int>(P.HoverCm))
         + " top=" + std::to_string(static_cast<int>(P.TopCmS)) + " ceiling_m=" + std::to_string(static_cast<int>(P.CeilingM));
}

} // namespace mount
} // namespace daedalus
