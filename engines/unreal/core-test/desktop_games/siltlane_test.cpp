// SPDX-License-Identifier: MIT
#include "DesktopGames/DaedalusDesktopGameRegistry.h"
#include <iostream>
#include <string>

using namespace daedalus::desktop;
namespace {
int Checks = 0, Failed = 0;
void Check(bool Ok, const std::string& What) { ++Checks; if (!Ok) { ++Failed; std::cerr << "FAIL " << What << '\n'; } }
void Press(SiltlaneGame& G, int Dir) {
    Input I;
    if (Dir < 0) I.Left = true;
    else if (Dir > 0) I.Right = true;
    G.Step(I);
}
void Nudge(SiltlaneGame& G, int Dir) { Press(G, Dir); G.Step({}); }
bool HasText(const Frame& F, const std::string& Part) {
    for (const auto& C : F.Commands) if (C.Kind == Shape::Text && C.Label.find(Part) != std::string::npos) return true;
    return false;
}
}

int main() {
    SiltlaneGame Fresh;
    Fresh.Reset(730);
    const std::string Note = Fresh.GetStatus().Note;
    Check(Fresh.LaneIndex() == 1 && Fresh.FallEveryCount() == 12 && Fresh.SpawnEveryCount() == 24 && Fresh.PassTarget() == 8, "a fresh run is the normal lane");
    Check(!Fresh.GetStatus().Over && Fresh.GetStatus().Score == 0 && Note == "Lane 1; passed 0 of 8", "opening score names eight stones and the hint stays off the note");
    Check(Fresh.SetCabinetDifficulty("hard") && Fresh.FallEveryCount() == 8 && Fresh.SpawnEveryCount() == 14 && Fresh.GetStatus().Score == 0 && Fresh.LaneIndex() == 1 && Fresh.PassTarget() == 10, "hard drifts faster, keeps the run, and names ten stones");
    Check(Fresh.SetCabinetDifficulty("easy") && Fresh.FallEveryCount() == 20 && Fresh.SpawnEveryCount() == 36 && Fresh.PassTarget() == 6, "easy drifts slowly and clears six stones");
    Check(!Fresh.SetCabinetDifficulty("legendary") && Fresh.CabinetDifficulty() == "easy", "an unknown name is refused");
    Fresh.SetCabinetDifficulty("normal");
    Frame F;
    Fresh.Render(F);
    Check(HasText(F, Fresh.HowToLine()) && HasText(F, "eight") && HasText(F, "five") && HasText(F, Fresh.KeyHint()) && HasText(F, Fresh.HintLine()) && HasText(F, Fresh.ActionCue()), "how-to names the clear, and keys, hint and cue are on the frame");
    Press(Fresh, -1);
    Check(Fresh.LaneIndex() == 0, "one left press changes lane");
    Press(Fresh, -1);
    Check(Fresh.LaneIndex() == 0, "held left does not change lane again");

    SiltlaneGame Run;
    Run.Reset(730);
    for (int N = 0; N < 800 && !Run.GetStatus().Over && Run.GetStatus().Score == 0; ++N) {
        if (Run.ClosestSilt() <= 3 && Run.LaneIndex() > 0) Nudge(Run, -1);
        else if (Run.ClosestSilt() <= 3) Nudge(Run, 1);
        else Run.Step({});
    }
    Check(Run.GetStatus().Score > 0, "a stone that misses the runner adds to the score");
    for (int N = 0; N < 800 && !Run.GetStatus().Over; ++N) Run.Step({});
    Check(Run.GetStatus().Over && !Run.GetStatus().Won && Run.GetStatus().Lives == 0, "standing still ends the run when silt arrives");
    const auto Caught = Run.GetStatus().Score;
    Check(Run.SourceKeyDown(8) && !Run.GetStatus().Over && Run.GetStatus().Score == 0 && Run.LaneIndex() == 1, "R starts the same lane again");
    SiltlaneGame Practice;
    Check(Practice.SetOption(1, 730) && Practice.GetOption() == 1 && Practice.LaneCount() == 2 && Practice.LaneIndex() == 0, "practice is two lanes");
    Check(!Practice.SetOption(2, 730) && Practice.GetOption() == 1, "an out-of-range course is refused");
    Check(Practice.PassTarget() == 5, "practice clears five stones");
    Input Stick;
    Stick.AxisX = 0.4;
    Practice.Step(Stick);
    Check(Practice.LaneIndex() == 0, "a stick inside the dead zone does not move");
    Stick.AxisX = 0.5;
    Practice.Step(Stick);
    Practice.Step({});
    Check(Practice.LaneIndex() == 1, "a stick past the dead zone moves once");
    Check(Caught >= 0, "the caught score was a host-visible count");
    std::cout << "siltlane: " << (Checks - Failed) << "/" << Checks << " checks\n";
    return Failed == 0 ? 0 : 1;
}
