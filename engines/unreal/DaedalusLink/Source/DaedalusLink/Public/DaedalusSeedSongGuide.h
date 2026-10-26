// SPDX-License-Identifier: MIT
#pragma once

// Words, choice intents and a review snapshot for Keeper Oriel's existing gramophone.
// Restoration, spring and quest rules remain in DaedalusSeedSongCore.h.
#include "DaedalusSeedSongCore.h"
#include <cmath>
#include <cstdint>
#include <string>
#include <vector>

namespace daedalus { namespace seedsong {

enum class GuidePage { Home, Listen, Clue, Review, Result, Water, Spring };
enum class GuideAction { Leave, Listen, Clue, Review, Confirm, Back, Water, ReviewSpring, LookSpring };

struct GuideChoice
{
    std::string Label;
    GuideAction Action;
};

struct GuideSpring
{
    std::string Name;
    bool Clean = false;
};

struct GuideSpringTarget
{
    std::string Id, Name, ActorKey;
    double DistanceSquared = 0;
    bool Clean = false, Available = false;
};

// The native actor supplies only loaded, eligible actors from this chapter.
// Keep equal-distance selection stable without displaying actor paths to the player.
inline int GuideNearestSpring(const std::vector<GuideSpringTarget>& Targets)
{
    int Nearest = -1;
    for (size_t I = 0; I < Targets.size(); ++I)
    {
        const GuideSpringTarget& Candidate = Targets[I];
        if (!Candidate.Clean || !Candidate.Available || Candidate.Id.empty() || Candidate.Name.empty()
            || Candidate.ActorKey.empty() || !std::isfinite(Candidate.DistanceSquared)
            || Candidate.DistanceSquared < 0) { continue; }
        if (Nearest >= 0)
        {
            const GuideSpringTarget& Best = Targets[static_cast<size_t>(Nearest)];
            if (Candidate.DistanceSquared > Best.DistanceSquared) { continue; }
            if (Candidate.DistanceSquared == Best.DistanceSquared
                && (Candidate.ActorKey > Best.ActorKey
                    || (Candidate.ActorKey == Best.ActorKey && Candidate.Id >= Best.Id))) { continue; }
        }
        Nearest = static_cast<int>(I);
    }
    return Nearest;
}

struct GuideReview
{
    std::string RecordItem, RecordName;
    std::vector<std::string> Herbs;
    int64_t ProgressRevision = 0;
    bool CanAttempt() const { return !RecordItem.empty() && !Herbs.empty(); }
};

inline bool SameReview(const GuideReview& Presented, const GuideReview& Current)
{
    return Presented.RecordItem == Current.RecordItem && Presented.RecordName == Current.RecordName
        && Presented.Herbs == Current.Herbs && Presented.ProgressRevision == Current.ProgressRevision;
}

inline std::vector<GuideChoice> GuideChoices(GuidePage Page, bool HasRecord, bool HasHerbs, bool CanGuideSpring = false)
{
    std::vector<GuideChoice> Out;
    if (Page == GuidePage::Home)
    {
        Out.push_back({"Listen to Keeper Oriel", GuideAction::Listen});
        if (HasRecord) { Out.push_back({"A record clue, please", GuideAction::Clue}); }
        if (HasRecord && HasHerbs) { Out.push_back({"Review a mend", GuideAction::Review}); }
    }
    else if (Page == GuidePage::Listen)
    {
        Out.push_back({"Which springs are clean?", GuideAction::Water});
        Out.push_back({"Back", GuideAction::Back});
    }
    else if (Page == GuidePage::Review)
    {
        if (HasRecord && HasHerbs) { Out.push_back({"Use these herbs to mend", GuideAction::Confirm}); }
        Out.push_back({"Back", GuideAction::Back});
    }
    else if (Page == GuidePage::Water)
    {
        if (CanGuideSpring) { Out.push_back({"Look toward a clean spring", GuideAction::ReviewSpring}); }
        Out.push_back({"Back", GuideAction::Back});
    }
    else if (Page == GuidePage::Spring)
    {
        if (CanGuideSpring) { Out.push_back({"Turn my camera", GuideAction::LookSpring}); }
        Out.push_back({"Back", GuideAction::Back});
    }
    else { Out.push_back({"Back", GuideAction::Back}); }
    // Native B/Escape highlights the final choice; A confirms it.
    Out.push_back({"Not now", GuideAction::Leave});
    return Out;
}

inline GuideAction GuidePick(const std::vector<GuideChoice>& PresentedChoices, int Choice)
{
    return Choice >= 0 && Choice < static_cast<int>(PresentedChoices.size())
        ? PresentedChoices[static_cast<size_t>(Choice)].Action : GuideAction::Leave;
}

inline std::string GuideProgress(int Mended, int Total, int CleanSprings)
{
    return std::to_string(Mended) + " of " + std::to_string(Total) + " records mended. "
        + std::to_string(CleanSprings) + " springs clean.";
}

inline std::string GuideHome(int Mended, int Total, int CleanSprings, bool HasRecord, bool HasHerbs)
{
    std::string Text = GuideProgress(Mended, Total, CleanSprings);
    if (HasRecord && !HasHerbs) { Text += "\nThe kettle has no herbs loaded. You can listen or ask for a clue."; }
    return Text;
}

inline std::string GuideWaterText(const std::vector<GuideSpring>& Springs)
{
    std::string Names;
    for (const GuideSpring& Spring : Springs)
        if (Spring.Clean && !Spring.Name.empty()) { Names += "\n" + Spring.Name; }
    if (Names.empty())
        return "None of these song springs have been cleared yet. Each record you mend clears the next song spring.";
    return "These song springs run clean:" + Names;
}

inline const char* GuideSpringUnavailableText()
{
    return "I cannot point to a clean song spring here right now. You can still read the clean spring list.";
}

inline const char* GuideSpringChangedText()
{
    return "That spring changed or is no longer available. Please choose a spring again before looking.";
}

inline std::string GuideSpringReviewText(const std::string& Name)
{
    if (Name.empty()) { return GuideSpringUnavailableText(); }
    return "Look toward " + Name + "?\nThis turns your camera while you stay where you are. "
        "Check the ground and choose a safe path before walking.";
}

inline std::string GuideReviewText(const GuideReview& Review)
{
    if (!Review.CanAttempt()) { return "There is no record and loaded herb combination to review. Nothing was used."; }
    std::string Text = "Mend " + Review.RecordName + "?\nHerbs in order: ";
    for (size_t I = 0; I < Review.Herbs.size(); ++I) { Text += (I ? ", " : "") + Review.Herbs[I]; }
    return Text + ".\nTrying this mend uses all these herbs, even if the record does not mend.";
}

inline const char* GuideChanged()
{
    return "The record, loaded herbs or progress changed. Nothing was used. Review the current details before trying a mend.";
}

inline std::string GuideResult(const std::string& Outcome, int Mended, int Total, int CleanSprings)
{
    std::string Text = "The mend could not finish.";
    if (Outcome == "RESTORED") { Text = "The record is mended."; }
    else if (Outcome == "NEEDLE_SKIPS") { Text = "The needle skipped. The record still needs mending."; }
    else if (Outcome == "MISSING_HERBS") { Text = "The tune needs at least " + std::to_string(MinHerbs) + " herbs. The record still needs mending."; }
    else if (Outcome == "ALREADY_RESTORED") { Text = "That record is already mended."; }
    return Text + "\n" + GuideProgress(Mended, Total, CleanSprings);
}

}} // namespace daedalus::seedsong
