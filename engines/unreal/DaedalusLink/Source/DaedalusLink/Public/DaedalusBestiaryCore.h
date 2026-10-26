// SPDX-License-Identifier: MIT

#pragma once

// The bestiary per realm (BASE-LAYER.md row 6, CAST01: 50 enemy types): what the encounter director spawns in
// each 3D realm instead of World Zero's four crystal kinds. Rows follow Sol's creature manifests
// (data/art/<realm>/creature(s)-manifest.json: the "encounter" and "boss proposal" roles); the art id is the
// imported skeletal creature under /Game/Daedalus/Art/Creatures/<ArtId>. Life/Power/Exp use the same scale as
// the server's foe rules (ADaedalusHero::FoeRules: life x30 = health). Weight is the pick weight within the
// realm (bosses rare). Pure C++17; bestiary_core_test proves the table and the picker.

#include <string>
#include <vector>

namespace daedalus
{
namespace bestiary
{

struct Foe
{
    std::string Realm, Kind, Title, ArtId;
    int Life = 1, Power = 1, Exp = 1, Weight = 10;
    bool Boss() const { return Weight <= 1; }
};

inline const std::vector<Foe>& Table()
{
    static const std::vector<Foe> T = {
        // GALLERY-CITY: ink, canvas and marble
        {"GALLERY-CITY", "SMUDGELING", "Smudgeling", "Mob_Gallery_Smudgeling", 1, 1, 2, 12},
        {"GALLERY-CITY", "THUMBTACK_BEETLE", "Thumbtack Beetle", "Mob_Gallery_ThumbtackBeetle", 2, 1, 3, 10},
        {"GALLERY-CITY", "CANVAS_MOTH", "Canvas Moth", "Mob_Gallery_CanvasMoth", 1, 2, 3, 8},
        {"GALLERY-CITY", "EASEL_STRIDER", "Easel Strider", "Mob_Gallery_EaselStrider", 3, 2, 5, 6},
        {"GALLERY-CITY", "TURPENTINE_TOAD", "Turpentine Toad", "Mob_Gallery_TurpentineToad", 3, 3, 6, 5},
        {"GALLERY-CITY", "MOSAIC_HOUND", "Mosaic Hound", "Mob_Gallery_MosaicHound", 4, 3, 8, 4},
        {"GALLERY-CITY", "GILDED_FRAME_MIMIC", "Gilded Frame Mimic", "Mob_Gallery_GildedFrameMimic", 5, 4, 12, 2},
        {"GALLERY-CITY", "SENTINEL_BUST", "Sentinel Bust", "Mob_Gallery_SentinelBust", 6, 4, 14, 2},
        {"GALLERY-CITY", "GREY_WASH", "Grey Wash", "Mob_Gallery_GreyWash", 20, 6, 60, 1},
        // PARCELS: fields, fences and the mail
        {"PARCELS", "BURROW_VOLE", "Burrow Vole", "Mob_Parcels_BurrowVole", 1, 1, 2, 12},
        {"PARCELS", "HAY_SPRITE", "Hay Sprite", "Mob_Parcels_HaySprite", 1, 1, 2, 10},
        {"PARCELS", "MAILBOX_MIMIC", "Mailbox Mimic", "Mob_Parcels_MailboxMimic", 3, 2, 5, 6},
        {"PARCELS", "TWINE_SNAKE", "Twine Snake", "Mob_Parcels_TwineSnake", 2, 2, 4, 8},
        {"PARCELS", "THISTLE_BOAR", "Thistle Boar", "Mob_Parcels_ThistleBoar", 4, 3, 7, 5},
        {"PARCELS", "STAMPEDE_CALF", "Stampede Calf", "Mob_Parcels_StampedeCalf", 3, 3, 6, 5},
        {"PARCELS", "WHEELBARROW_GOLEM", "Wheelbarrow Golem", "Mob_Parcels_WheelbarrowGolem", 6, 4, 12, 3},
        {"PARCELS", "COMBINE_CRAB", "Combine Crab", "Mob_Parcels_CombineCrab", 7, 4, 14, 2},
        {"PARCELS", "RUSTWING_HAWK", "Rustwing Hawk", "Mob_Parcels_RustwingHawk", 4, 5, 10, 3},
        {"PARCELS", "BLIGHT_BAILIFF", "Blight Bailiff", "Mob_Parcels_BlightBailiff", 22, 6, 70, 1},
        // BRICKS: constructs that come apart
        {"BRICKS", "BRICKBUG", "Brickbug", "Mob_Bricks_Brickbug", 1, 1, 2, 12},
        {"BRICKS", "LOOSE_STUD", "Loose Stud", "Mob_Bricks_LooseStud", 1, 1, 2, 10},
        {"BRICKS", "PLATE_CRAB", "Plate Crab", "Mob_Bricks_PlateCrab", 3, 2, 5, 7},
        {"BRICKS", "HINGE_HOUND", "Hinge Hound", "Mob_Bricks_HingeHound", 3, 3, 6, 6},
        {"BRICKS", "SLOPE_SLUG", "Slope Slug", "Mob_Bricks_SlopeSlug", 4, 2, 6, 5},
        {"BRICKS", "WIND_UP_KNIGHT", "Wind-Up Knight", "Mob_Bricks_WindUpKnight", 5, 4, 10, 4},
        {"BRICKS", "MAGNET_MOTH", "Magnet Moth", "Mob_Bricks_MagnetMoth", 2, 3, 5, 5},
        {"BRICKS", "REBUILD_REX", "Rebuild Rex", "Mob_Bricks_RebuildRex", 18, 5, 50, 1},
        {"BRICKS", "TOWER_TITAN", "Tower Titan", "Mob_Bricks_TowerTitan", 24, 6, 80, 1},
        // LABYRINTH: the maze's own
        {"LABYRINTH", "CHALK_EATER", "Chalk Eater", "Mob_Lab_ChalkEater", 2, 1, 3, 12},
        {"LABYRINTH", "THREAD_MOTH", "Thread Moth", "Mob_Lab_ThreadMoth", 1, 2, 3, 10},
        {"LABYRINTH", "ECHO_CRICKET", "Echo Cricket", "Mob_Lab_EchoCricket", 1, 1, 2, 10},
        {"LABYRINTH", "MIRROR_BAT", "Mirror Bat", "Mob_Lab_MirrorBat", 2, 2, 4, 8},
        {"LABYRINTH", "WALL_MIMIC", "Wall Mimic", "Mob_Lab_WallMimic", 5, 3, 9, 4},
        {"LABYRINTH", "HORNBACK_BULL", "Hornback Bull", "Mob_Lab_HornbackBull", 6, 4, 12, 3},
        {"LABYRINTH", "SENTINEL_SPHINXLING", "Sentinel Sphinxling", "Mob_Lab_SentinelSphinxling", 7, 4, 14, 2},
        {"LABYRINTH", "FOLDING_MAZE", "Folding Maze", "Mob_Lab_FoldingMaze", 26, 6, 90, 1},
    };
    return T;
}

inline std::vector<const Foe*> ForRealm(const std::string& Realm)
{
    std::vector<const Foe*> Out;
    for (const Foe& F : Table()) if (F.Realm == Realm) Out.push_back(&F);
    return Out;
}

inline const Foe* Find(const std::string& Kind)
{
    for (const Foe& F : Table()) if (F.Kind == Kind) return &F;
    return nullptr;
}

/** Weighted pick for a realm: Roll in [0, 1). Bosses (weight 1) come up about one pack in fifty. nullptr for a
 *  realm with no bestiary (World Zero keeps the server's foe rules). */
inline const Foe* Pick(const std::string& Realm, double Roll)
{
    const std::vector<const Foe*> R = ForRealm(Realm);
    if (R.empty()) return nullptr;
    int Total = 0;
    for (const Foe* F : R) Total += F->Weight;
    double At = (Roll < 0.0 ? 0.0 : (Roll >= 1.0 ? 0.999999 : Roll)) * Total;
    for (const Foe* F : R) { At -= F->Weight; if (At < 0.0) return F; }
    return R.back();
}

/** A pack of N for a realm from N rolls; a boss never shares a pack (it comes alone). */
inline std::vector<const Foe*> Pack(const std::string& Realm, const std::vector<double>& Rolls)
{
    std::vector<const Foe*> Out;
    for (double R : Rolls)
    {
        const Foe* F = Pick(Realm, R);
        if (!F) break;
        if (F->Boss()) return {F};
        Out.push_back(F);
    }
    return Out;
}

} // namespace bestiary
} // namespace daedalus
