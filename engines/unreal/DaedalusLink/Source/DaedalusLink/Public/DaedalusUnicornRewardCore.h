// SPDX-License-Identifier: MIT
#pragma once
#include "DaedalusPortalQuestCore.h"
#include <algorithm>

// Per-player eligibility only. The host supplies verified world events and must
// persist/award a reward atomically. No wallet, inventory or client trust here.
namespace DaedalusUnicornReward
{
enum class Outcome { Ignored, Duplicate, Progressed, Eligible };
struct Snapshot
{
    unsigned Version = 1;
    std::vector<std::string> BullIds;
    std::string PackId;
    bool Claimed = false;
};

class Gate
{
public:
    static constexpr unsigned RequiredBulls = 10;
    static constexpr unsigned LegendaryPackSize = 12;

    Gate() : Quest({{"burning-bull-at-sea", "sea", RequiredBulls},
                    {"unicorn-pack", "twelve", 1}}) {}

    Outcome RecordBullAtSea(const std::string& bullId, bool wasBurning, bool seaArrivalVerified)
    {
        if (!Identity(bullId) || !wasBurning || !seaArrivalVerified) return Outcome::Ignored;
        if (Bulls.count(bullId)) return Outcome::Duplicate;
        if (Bulls.size() >= RequiredBulls) return Outcome::Ignored;
        const auto result = Quest.Apply("bull:" + bullId, "burning-bull-at-sea", "sea");
        if (result != DaedalusPortalQuest::Result::Progressed && result != DaedalusPortalQuest::Result::Completed)
            return Outcome::Ignored;
        Bulls.insert(bullId);
        FinishEncounter();
        return Eligible() ? Outcome::Eligible : Outcome::Progressed;
    }

    Outcome RecordPackEncounter(const std::string& packId, unsigned members, bool encounterVerified)
    {
        if (!Identity(packId) || members != LegendaryPackSize || !encounterVerified) return Outcome::Ignored;
        if (PackId == packId) return Outcome::Duplicate;
        if (!PackId.empty()) return Outcome::Ignored; // One qualifying encounter is sufficient.
        PackId = packId;
        FinishEncounter();
        return Eligible() ? Outcome::Eligible : Outcome::Progressed;
    }

    unsigned BullsAtSea() const { return static_cast<unsigned>(Bulls.size()); }
    bool HasLegendaryEncounter() const { return !PackId.empty(); }
    const std::string& EncounterId() const { return PackId; }
    bool Eligible() const { return Quest.Complete(); }
    bool RewardClaimed() const { return Claimed; }
    bool Pristine() const { return Bulls.empty() && PackId.empty() && !Claimed; }

    Snapshot Export() const
    {
        Snapshot out;
        out.BullIds.assign(Bulls.begin(), Bulls.end());
        std::sort(out.BullIds.begin(), out.BullIds.end());
        out.PackId = PackId;
        out.Claimed = Claimed;
        return out;
    }

    // Restore only into a fresh per-player gate. Build a candidate first so an
    // invalid host record never partially changes active state.
    bool Restore(const Snapshot& state)
    {
        if (!Pristine() || state.Version != 1 || state.BullIds.size() > RequiredBulls ||
            (!state.PackId.empty() && !Identity(state.PackId))) return false;
        Gate candidate;
        for (const auto& bull : state.BullIds)
        {
            const auto result = candidate.RecordBullAtSea(bull, true, true);
            if (result != Outcome::Progressed && result != Outcome::Eligible) return false;
        }
        if (!state.PackId.empty()) candidate.RecordPackEncounter(state.PackId, LegendaryPackSize, true);
        if (state.Claimed && !candidate.ClaimReward()) return false;
        *this = std::move(candidate);
        return true;
    }

    // One-shot signal for a host transaction, NOT an award implementation.
    // The host must persist this state with its reward grant before acknowledging.
    bool ClaimReward()
    {
        if (!Quest.ClaimReward()) return false;
        Claimed = true;
        return true;
    }

private:
    static bool Identity(const std::string& id)
    {
        return !id.empty() && id.size() <= 100 &&
            std::all_of(id.begin(), id.end(), [](unsigned char c) { return c >= 33 && c != 127; });
    }
    void FinishEncounter()
    {
        // Conditions can arrive in either order. The underlying ordered quest
        // receives its encounter step only after ten distinct arrivals exist.
        if (Bulls.size() == RequiredBulls && !PackId.empty() && !Quest.Complete())
            Quest.Apply("pack:" + PackId, "unicorn-pack", "twelve");
    }
    DaedalusPortalQuest::Progress Quest;
    std::unordered_set<std::string> Bulls;
    std::string PackId;
    bool Claimed = false;
};
}
