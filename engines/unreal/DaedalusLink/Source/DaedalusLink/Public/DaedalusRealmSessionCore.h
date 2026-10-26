// SPDX-License-Identifier: MIT

#pragma once

// A player's realm session (hub 28885, Richey 2026-10-13): which realm a player is in and how they move between
// them. The worlds are different games (ADR-065 rule 6), so a switch changes the inventory catalog, the dialogue
// theme, the cast, and which world host streams. The rules, in one place:
//
//   WORLD-ZERO --gate-->  GALLERY-CITY | PARCELS | BRICKS | LABYRINTH      (the rainbow gates, ADR-053)
//   any 3D realm --portal--> PORTAL                                        (a portal cube: the 8-bit realm)
//   PORTAL --portal--> back where you came from
//   a realm with docks --dock(boat|sub)--> OCEAN                           (Richey 15:53: boats and submarines at docks)
//   OCEAN --shore--> the realm you sailed from                             (an ordinary shore landing)
//   OCEAN --dock(sub)--> any realm with an underwater dock                 (destination docks connect other realms)
//   any --gate--> WORLD-ZERO                                               (home is always one gate away)
//
// Pure C++17; core-test/realm_session_test.cpp proves every row and every refusal. The host (ADaedalusHero)
// applies a Change: saves the old realm, asks its host to leave, asks the new host to enter at the hint.

#include <algorithm>
#include <string>
#include <vector>

namespace daedalus
{
namespace session
{

enum class Via { Gate, Portal, Dock, Shore };

inline const char* ViaName(Via V) { static const char* N[] = {"GATE", "PORTAL", "DOCK", "SHORE"}; return N[static_cast<int>(V)]; }

/** What a realm is, for the rules. Theme and catalog follow DaedalusInventoryCore's names. */
struct RealmDef
{
    std::string Id, Theme, Catalog;
    bool Is3D = true;          // the 8-bit realm is not
    bool HasDocks = false;     // boats and submarines leave from here
    bool HasSubDock = false;   // an underwater dock: a submarine can arrive here from the Ocean
    bool Gate = false;         // reachable by a rainbow gate from World Zero
};

inline const std::vector<RealmDef>& Realms()
{
    static const std::vector<RealmDef> R = {
        {"WORLD-ZERO", "zero", "world-zero", true, true, false, false},
        {"GALLERY-CITY", "gallery", "gallery-city", true, true, true, true},
        {"PARCELS", "parcels", "parcels", true, true, true, true},
        {"BRICKS", "bricks", "bricks", true, true, false, true},
        {"LABYRINTH", "labyrinth", "labyrinth", true, false, true, true},
        {"PORTAL", "retro", "", false, true, false, false},        // the 8-bit realm: Dragon Warrior docks (Richey 15:53)
        {"OCEAN", "ocean", "ocean", true, false, false, false},
    };
    return R;
}

inline const RealmDef* Find(const std::string& Id)
{
    for (const RealmDef& R : Realms()) if (R.Id == Id) return &R;
    return nullptr;
}

/** One switch the host must apply. */
struct Change
{
    std::string From, To, Theme, Catalog;
    Via How = Via::Gate;
    std::string Hint;      // where to stand: "spawn", "gate:<from>", "portal", "dock:<id>", "shore"
    bool Ok = false;
    std::string Why;       // when !Ok
};

class Session
{
public:
    const std::string& Current() const { return Cur; }
    const std::string& SailedFrom() const { return Departure; }
    const std::string& PortalFrom() const { return PortalBack; }
    int Switches() const { return Count; }

    /** Try to go to Target by Via; Detail is the dock id for a dock, the vehicle for a dock ("boat"/"sub"). */
    Change Go(const std::string& Target, Via How, const std::string& Detail = "")
    {
        Change C;
        C.From = Cur; C.To = Target; C.How = How;
        const RealmDef* T = Find(Target);
        const RealmDef* F = Find(Cur);
        if (!T) { C.Why = "no realm " + Target; return C; }
        if (!F) { C.Why = "not in a realm"; return C; }
        if (Target == Cur) { C.Why = "already in " + Target; return C; }
        C.Theme = T->Theme; C.Catalog = T->Catalog;
        switch (How)
        {
        case Via::Gate:
            if (Target == "WORLD-ZERO") { C.Hint = "gate:" + Cur; break; }           // home from anywhere
            if (Cur != "WORLD-ZERO") { C.Why = "gates leave from World Zero"; return C; }
            if (!T->Gate) { C.Why = "no gate to " + Target; return C; }
            C.Hint = "gate:WORLD-ZERO";
            break;
        case Via::Portal:
            if (Target == "PORTAL")
            {
                if (!F->Is3D) { C.Why = "already in the 8-bit realm"; return C; }
                C.Hint = "spawn";
                break;
            }
            if (Cur != "PORTAL") { C.Why = "a portal only leads into the 8-bit realm"; return C; }
            if (Target != PortalBack) { C.Why = "the portal leads back to " + PortalBack; return C; }
            C.Hint = "portal";
            break;
        case Via::Dock:
        {
            const std::string Vehicle = Detail.substr(0, Detail.find(':'));
            const std::string DockId = Detail.find(':') == std::string::npos ? "" : Detail.substr(Detail.find(':') + 1);
            if (Vehicle != "boat" && Vehicle != "sub") { C.Why = "a dock takes a boat or a sub"; return C; }
            if (DockId.empty()) { C.Why = "which dock?"; return C; }
            if (Target == "OCEAN")
            {
                if (!F->HasDocks) { C.Why = Cur + " has no docks"; return C; }
                C.Hint = "dock:" + DockId;
                break;
            }
            if (Cur != "OCEAN") { C.Why = "docks lead to the Ocean; the Ocean's docks lead on"; return C; }
            if (Vehicle != "sub") { C.Why = "a boat can only land on a shore"; return C; }
            if (!T->HasSubDock) { C.Why = Target + " has no underwater dock"; return C; }
            C.Hint = "dock:" + DockId;
            break;
        }
        case Via::Shore:
            if (Cur != "OCEAN") { C.Why = "a shore landing is a thing the Ocean does"; return C; }
            if (Target != Departure) { C.Why = "the shore leads back to " + Departure; return C; }
            C.Hint = "shore";
            break;
        }
        C.Ok = true;
        return C;
    }

    /** The host applied a Change: remember it. */
    void Apply(const Change& C)
    {
        if (!C.Ok) return;
        if (C.To == "PORTAL") PortalBack = C.From;
        if (C.To == "OCEAN" && C.How == Via::Dock) Departure = C.From;
        if (C.From == "OCEAN" && C.How == Via::Shore) Departure.clear();
        Cur = C.To;
        ++Count;
    }

    std::string Save() const { return Cur + " " + (Departure.empty() ? "-" : Departure) + " " + (PortalBack.empty() ? "-" : PortalBack) + " " + std::to_string(Count); }
    bool Restore(const std::string& Line)
    {
        std::vector<std::string> F;
        std::string W;
        for (char Ch : Line) { if (Ch == ' ') { if (!W.empty()) F.push_back(W); W.clear(); } else W += Ch; }
        if (!W.empty()) F.push_back(W);
        if (F.size() < 3 || !Find(F[0])) return false;
        Cur = F[0];
        Departure = F[1] == "-" ? "" : F[1];
        PortalBack = F[2] == "-" ? "" : F[2];
        Count = F.size() > 3 ? std::atoi(F[3].c_str()) : 0;
        return true;
    }

    std::string Describe() const
    {
        return "realm=" + Cur + " sailed_from=" + (Departure.empty() ? "-" : Departure) + " portal_from=" + (PortalBack.empty() ? "-" : PortalBack) + " switches=" + std::to_string(Count);
    }

private:
    std::string Cur = "WORLD-ZERO", Departure, PortalBack;
    int Count = 0;
};

} // namespace session
} // namespace daedalus
