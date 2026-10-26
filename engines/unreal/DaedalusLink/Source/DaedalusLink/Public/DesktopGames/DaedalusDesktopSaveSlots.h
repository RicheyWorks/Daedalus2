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
inline constexpr std::array<SaveSlot,12> SaveSlots{{
    {"minesweeper","minesweeper.dgs",SaveStyle::Manual},
    {"star_shooter","star_shooter.dgs",SaveStyle::SourceMenu},
    {"pong","pong.dgs",SaveStyle::Manual},
    {"football","football.dgs",SaveStyle::Manual},
    {"pacman","pacman.dgs",SaveStyle::Manual},
    {"dungeon","dungeon.dgs",SaveStyle::Manual},
    {"zelda","zelda.dgs",SaveStyle::Manual},
    {"asteroids","asteroids.dgs",SaveStyle::Manual},
    {"sega_shooter","sega_shooter.dgs",SaveStyle::Manual},
    {"shadow_ninja","shadow_ninja.dgs",SaveStyle::Manual},
    {"dodge_ball","dodge_ball.dgs",SaveStyle::Manual},
    {"contra","contra.dgs",SaveStyle::Manual},
}};
inline const SaveSlot* FindSaveSlot(const std::string& Id) {
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
