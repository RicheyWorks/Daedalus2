// SPDX-License-Identifier: MIT
#pragma once
// One table for which desktop games keep a local save, the file each one owns,
// and how the host offers it. Hosts read this instead of hard-coding game ids.
// Manual: the host shows Save run / Continue saved run (F5 / F9, pad X / Y when paused).
// SourceMenu: the game raises its own save request (Star's pause menu); the host
// only offers Continue. tools/minigames/minigame_catalog.py --check keeps this
// table equal to the games whose cores implement SaveState/RestoreState.
#include <array>
#include <string>

namespace daedalus { namespace desktop {
enum class SaveStyle { Manual, SourceMenu };
struct SaveSlot { const char* Id; const char* File; SaveStyle Style; };
inline constexpr std::array<SaveSlot,18> SaveSlots{{
    {"beacon_sweep","beacon_sweep.dgs",SaveStyle::Manual},
    {"star_shooter","star_shooter.dgs",SaveStyle::SourceMenu},
    {"twinwake","twinwake.dgs",SaveStyle::Manual},
    {"football","football.dgs",SaveStyle::Manual},
    {"glowtrail","glowtrail.dgs",SaveStyle::Manual},
    {"dungeon","dungeon.dgs",SaveStyle::Manual},
    {"lanternwild","lanternwild.dgs",SaveStyle::Manual},
    {"driftstone","driftstone.dgs",SaveStyle::Manual},
    {"riftwing","riftwing.dgs",SaveStyle::Manual},
    {"emberstep","emberstep.dgs",SaveStyle::Manual},
    {"dodge_ball","dodge_ball.dgs",SaveStyle::Manual},
    {"ironwake","ironwake.dgs",SaveStyle::Manual},
    {"shardring","shardring.dgs",SaveStyle::Manual},
    {"lumenpath","lumenpath.dgs",SaveStyle::Manual},
    {"wardens_accord","wardens_accord.dgs",SaveStyle::Manual},
    {"facetlock","facetlock.dgs",SaveStyle::Manual},
    {"prismcairn","prismcairn.dgs",SaveStyle::Manual},
    {"prismvault","prismvault.dgs",SaveStyle::Manual},
}};
// Original names replaced the earlier working ids (2026-10-25). Old ids still resolve, and a
// save written under the old file name is still offered by Continue until the new file exists.
struct GameAlias { const char* OldId; const char* Id; const char* OldFile; };
inline constexpr std::array<GameAlias,8> GameAliases{{
    {"minesweeper","beacon_sweep","minesweeper.dgs"},
    {"zelda","lanternwild","zelda.dgs"},
    {"contra","ironwake","contra.dgs"},
    {"sega_shooter","riftwing","sega_shooter.dgs"},
    {"asteroids","driftstone","asteroids.dgs"},
    {"pacman","glowtrail","pacman.dgs"},
    {"pong","twinwake","pong.dgs"},
    {"shadow_ninja","emberstep","shadow_ninja.dgs"},
}};
inline std::string CanonicalGameId(const std::string& Id) {
    for(const GameAlias& Alias:GameAliases) if(Id==Alias.OldId) return Alias.Id;
    return Id;
}
inline const char* LegacySaveFileFor(const std::string& Id) {
    const std::string Canonical=CanonicalGameId(Id);
    for(const GameAlias& Alias:GameAliases) if(Canonical==Alias.Id) return Alias.OldFile;
    return nullptr;
}
inline const SaveSlot* FindSaveSlot(const std::string& RawId) {
    const std::string Id=CanonicalGameId(RawId);
    for(const SaveSlot& Slot:SaveSlots) if(Id==Slot.Id) return &Slot;
    return nullptr;
}
inline bool SupportsManualSave(const std::string& Id) {
    const SaveSlot* Slot=FindSaveSlot(Id);
    return Slot && Slot->Style==SaveStyle::Manual;
}
// Games without a slot keep the original host behavior: Continue offers the Star save.
inline const char* ResumeGameId(const std::string& Id) {
    const SaveSlot* Slot=FindSaveSlot(Id);
    return Slot ? Slot->Id : "star_shooter";
}
inline const char* SaveFileFor(const std::string& Id) {
    const SaveSlot* Slot=FindSaveSlot(Id);
    return Slot ? Slot->File : "star_shooter.dgs";
}
}} // namespace daedalus::desktop
