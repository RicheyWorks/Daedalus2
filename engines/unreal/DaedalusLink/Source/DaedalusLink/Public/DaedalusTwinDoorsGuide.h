// SPDX-License-Identifier: MIT
#pragma once

// Player-facing words and choices for the existing Twin Doors actor. Puzzle rules remain in
// DaedalusTwinDoorsCore.h; this only describes the question and the answer the player has heard.
#include "DaedalusTwinDoorsCore.h"
#include <vector>

namespace daedalus::twindoors {

enum class GuidePage { Welcome, Doors, Clue };
enum class GuideAction { Leave, Ask, Left, Right, Clue, Repeat, Back };

struct GuideChoice
{
    std::string Label;
    GuideAction Action;
};

inline std::vector<GuideChoice> GuideChoices(GuidePage Page)
{
    // Native dialogue's B/Escape highlights the last choice. Leaving is always last.
    switch (Page)
    {
        case GuidePage::Welcome: return {{"Ask the question", GuideAction::Ask}, {"Not now", GuideAction::Leave}};
        case GuidePage::Doors: return {{"Open the left door", GuideAction::Left}, {"Open the right door", GuideAction::Right},
            {"A clue, please", GuideAction::Clue}, {"Not now", GuideAction::Leave}};
        case GuidePage::Clue: return {{"Hear the bell again", GuideAction::Repeat}, {"Back to the doors", GuideAction::Back},
            {"Not now", GuideAction::Leave}};
    }
    return {{"Not now", GuideAction::Leave}};
}

inline GuideAction GuidePick(GuidePage Page, int Choice)
{
    const auto Choices = GuideChoices(Page);
    return Choice >= 0 && Choice < static_cast<int>(Choices.size())
        ? Choices[static_cast<size_t>(Choice)].Action : GuideAction::Leave;
}

inline const char* GuideSide(int Side) { return Side == 0 ? "left" : "right"; }

inline std::string GuideQuestion(Question Q, int Door)
{
    const std::string Side = GuideSide(Door);
    switch (Q)
    {
        case Question::Direct: return "Is the " + Side + " door safe?";
        case Question::OtherGuard: return "Would the other guard say the " + Side + " door is safe?";
        case Question::Embedded: return "If I asked if the " + Side + " door is safe, would you ring the low bell?";
        case Question::Self: return "Are you the truth guard?";
    }
    return {};
}

inline std::string GuideWelcome(Question Q, int Guard, int Door)
{
    return "One guard tells the truth. One fibs. Ask one question, then choose a door. "
        "A wrong door only restarts this puzzle. Take your time.\nAsk the " + std::string(GuideSide(Guard))
        + " guard: \"" + GuideQuestion(Q, Door) + "\"";
}

inline std::string GuideAnswer(Question Q, int Guard, int Door, Tone Heard)
{
    return "You asked the " + std::string(GuideSide(Guard)) + " guard: \"" + GuideQuestion(Q, Door)
        + "\"\nYou heard the " + (Heard == Tone::Low ? "low" : "high") + " bell. Which door would you like to try?";
}

inline std::string GuideClue(int Difficulty, int Guard, Question Q, int Door, Tone Heard)
{
    const int Safe = Deduce(Difficulty, Guard, Q, Door, Heard);
    if (Safe < 0)
        return "That answer does not prove which door is safe. You can still try either door. "
            "A wrong door only restarts this puzzle. The question about what a guard would ring can reveal a safe door.";
    const std::string Why = Q == Question::Embedded
        ? "This question works even when a guard fibs or the bell meanings are hidden. "
          "A low bell points to the door you asked about. A high bell points to the other door. "
        : "Asking about the other guard flips the answer. Here, low means yes: "
          "a low bell points to the other door, and a high bell points to the door you asked about. ";
    return Why + "The answer points to the " + GuideSide(Safe) + " door.";
}

inline std::string GuideResult(int Door, bool Opened)
{
    return "The " + std::string(GuideSide(Door)) + (Opened
        ? " door swings open. The archive opens through reasoning."
        : " door is a wall of bells. The guards change places: a new riddle. Take your time and try again.");
}

} // namespace daedalus::twindoors
