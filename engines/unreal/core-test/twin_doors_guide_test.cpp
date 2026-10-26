// SPDX-License-Identifier: MIT
// Focused offline coverage of the Twin Doors guide and its existing dialogue/core contracts.
#include "DaedalusTwinDoorsGuide.h"
#include "DaedalusDialogueCore.h"
#include <cstdio>

using namespace daedalus::twindoors;

static int Passed = 0, Total = 0;
static void Expect(bool Ok, const char* Name)
{
    ++Total;
    if (Ok) { ++Passed; }
    std::printf("%s %s\n", Ok ? "PASS" : "FAIL", Name);
}

int main()
{
    bool Menus = true, Invalid = true, BackLeaves = true, SkipsSafe = true;
    for (GuidePage Page : {GuidePage::Welcome, GuidePage::Doors, GuidePage::Clue})
    {
        const auto Choices = GuideChoices(Page);
        Menus &= !Choices.empty() && Choices.size() <= 4 && Choices.back().Label == "Not now"
            && GuidePick(Page, static_cast<int>(Choices.size()) - 1) == GuideAction::Leave;
        Invalid &= GuidePick(Page, -1) == GuideAction::Leave
            && GuidePick(Page, 99) == GuideAction::Leave;

        // Exercise actual native dialogue input semantics; B reveals text and then selects the final option.
        daedalus::dlg::Dialogue Dialogue;
        std::vector<std::string> Labels;
        for (const auto& C : Choices) { Labels.push_back(C.Label); }
        Dialogue.Say("Twin Doors", "Take your time choosing.", Labels);
        daedalus::dlg::Outcome Out;
        SkipsSafe &= !Dialogue.Press(daedalus::dlg::Button::B, Out) && Dialogue.Choosing();
        SkipsSafe &= !Dialogue.Press(daedalus::dlg::Button::B, Out);
        BackLeaves &= Dialogue.Press(daedalus::dlg::Button::A, Out)
            && GuidePick(Page, Out.Choice) == GuideAction::Leave;
    }
    Expect(Menus, "every menu has at most four choices and ends with Not now");
    Expect(Invalid, "closed lines and invalid choice indexes cannot select a door");
    Expect(SkipsSafe, "skipping dialogue text emits no choice");
    Expect(BackLeaves, "native B then A leaves every guard menu");
    Expect(GuidePick(GuidePage::Doors, 0) == GuideAction::Left
        && GuidePick(GuidePage::Doors, 1) == GuideAction::Right,
        "door choices have explicit sides without player-location input");
    Expect(GuidePick(GuidePage::Clue, 0) == GuideAction::Repeat
        && GuidePick(GuidePage::Clue, 1) == GuideAction::Back,
        "a clue offers replay and a return to the doors");
    Expect(GuideResult(0, true).find("left door swings open") != std::string::npos
        && GuideResult(1, false).find("right door is a wall of bells") != std::string::npos
        && GuideResult(1, false).find("try again") != std::string::npos,
        "per-attempt results name the selected door and invite a retry after failure");

    bool HonestClues = true, BothTones = true, DescribeQuestion = true, Replay = true;
    bool SawUncertain = false, SawSafeLeft = false, SawSafeRight = false;
    for (int64_t Seed = -32; Seed <= 32; ++Seed)
        for (int Difficulty = 0; Difficulty <= 1; ++Difficulty)
            for (int Guard = 0; Guard <= 1; ++Guard)
                for (int Door = 0; Door <= 1; ++Door)
                    for (Question Q : {Question::Direct, Question::OtherGuard, Question::Embedded, Question::Self})
                    {
                        Riddle R(Seed, Difficulty);
                        Session S(R);
                        Tone Heard = Tone::Low;
                        S.Ask(Guard, Q, Door, Heard);
                        const std::string Welcome = GuideWelcome(Q, Guard, Door);
                        const std::string Answer = GuideAnswer(Q, Guard, Door, Heard);
                        const std::string Clue = GuideClue(Difficulty, Guard, Q, Door, Heard);
                        DescribeQuestion &= Welcome.find(GuideQuestion(Q, Door)) != std::string::npos
                            && Answer.find(GuideQuestion(Q, Door)) != std::string::npos;
                        BothTones &= Answer.find(Heard == Tone::Low ? "low bell" : "high bell") != std::string::npos;
                        const int Safe = Deduce(Difficulty, Guard, Q, Door, Heard);
                        if (Safe < 0)
                        {
                            SawUncertain = true;
                            HonestClues &= Clue.find("does not prove") != std::string::npos
                                && Clue.find("answer points to") == std::string::npos;
                        }
                        else
                        {
                            SawSafeLeft |= Safe == 0;
                            SawSafeRight |= Safe == 1;
                            HonestClues &= Safe == R.GetSafeDoor()
                                && Clue.find("answer points to the " + std::string(GuideSide(Safe)) + " door") != std::string::npos;
                        }
                        // Reading/replaying the observation never consumes another question or chooses a door.
                        Replay &= Answer == GuideAnswer(Q, Guard, Door, S.HeardTone())
                            && Clue == GuideClue(Difficulty, Guard, Q, Door, S.HeardTone())
                            && S.Asked() && !S.Chosen() && S.HeardTone() == Heard;
                    }
    Expect(DescribeQuestion, "welcome and answer show the exact configured question");
    Expect(BothTones, "heard bells have readable low/high text");
    Expect(HonestClues && SawUncertain && SawSafeLeft && SawSafeRight,
        "clues use only provable deductions across 2080 seeded questions");
    Expect(Replay, "repeating an observation preserves the one-question session");

    std::printf("%d/%d\n", Passed, Total);
    return Passed == Total ? 0 : 1;
}
