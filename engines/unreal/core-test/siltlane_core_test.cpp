// SPDX-License-Identifier: MIT
// Siltlane parity: DaedalusSiltlaneCore.h replays siltlane_parity.txt from tools/minigames/siltlane_parity.py.
//   g++ -std=c++17 -O1 -Wall -Wextra -Wshadow -Werror -I../DaedalusLink/Source/DaedalusLink/Public siltlane_core_test.cpp -o siltlane_core_test && ./siltlane_core_test siltlane_parity.txt
#include "DaedalusSiltlaneCore.h"
#include <fstream>
#include <iostream>
#include <sstream>
#include <string>

using daedalus::siltlane::Game;

namespace {
int Fails = 0;
void Expect(bool Ok, const std::string& What) {
    if (!Ok) { ++Fails; std::cerr << "FAIL " << What << '\n'; }
}
void Replay(Game& Core, char Move) { Core.Step(Move == 'L', Move == 'R'); }
}

int main(int Argc, char** Argv) {
    if (Argc < 2) { std::cerr << "usage: siltlane_core_test siltlane_parity.txt\n"; return 2; }
    std::ifstream In(Argv[1]);
    if (!In) { std::cerr << "FAIL cannot read " << Argv[1] << '\n'; return 2; }

    Game Fresh;
    Fresh.Reset(730);
    Expect(Fresh.Lane() == 1 && Fresh.FallEvery() == 12 && Fresh.SpawnEvery() == 24 && Fresh.Target() == 8, "01 fresh normal course");
    Expect(Fresh.Note() == "Lane 1; passed 0 of 8", "02 opening note names the target");
    const std::string Opening = Fresh.Note();
    Expect(Fresh.SetDifficulty("hard") && Fresh.FallEvery() == 8 && Fresh.SpawnEvery() == 14 && Fresh.Passed() == 0 && Fresh.Lane() == 1, "03 hard pace keeps the run");
    Expect(Fresh.Note() == "Lane 1; passed 0 of 10", "04 hard note names ten stones");
    Expect(Fresh.Note() != Opening, "05 the note follows the target");
    Expect(Fresh.SetDifficulty("easy") && Fresh.FallEvery() == 20 && Fresh.SpawnEvery() == 36 && Fresh.Target() == 6, "06 easy pace and six-stone clear");
    Expect(!Fresh.SetDifficulty("legendary") && Fresh.Difficulty() == "easy", "07 unknown difficulty is refused");

    Game Practice;
    Expect(Practice.SetOption(1, 730) && Practice.Course() == 2 && Practice.Lane() == 0 && Practice.Target() == 5, "08 practice is two lanes and five stones");
    Expect(!Practice.SetOption(2, 730) && Practice.Option() == 1, "09 option 2 is refused");
    Expect(Practice.SetOption(0, 730) && Practice.Course() == 3 && Practice.Target() == 8 && Practice.Lane() == 1, "10 option 0 restores three lanes");

    Game Zero, One;
    Zero.Reset(0);
    One.Reset(1);
    for (int N = 0; N < 30; ++N) { Zero.Step(false, false); One.Step(false, false); }
    Expect(Zero.Lane() == One.Lane() && Zero.Passed() == One.Passed() && Zero.Tick() == One.Tick(), "11 seed 0 matches seed 1");

    Game Edge;
    Edge.Reset(730);
    Edge.Step(false, true); Edge.Step(false, false);
    Edge.Step(false, true); Edge.Step(false, false);
    Edge.Step(false, true);
    Expect(Edge.Lane() == 2, "12 the right edge stops at lane 2");
    Practice.Reset(730);
    Practice.SetOption(1, 730);
    Practice.Step(false, true); Practice.Step(false, false); Practice.Step(false, true);
    Expect(Practice.Lane() == 1, "13 practice stops at lane 1");

    Game Hold;
    Hold.Reset(730);
    Hold.Step(true, false); Hold.Step(true, false);
    Expect(Hold.Lane() == 0, "14 a held left press moves once");
    Hold.Step(false, false); Hold.Step(false, true); Hold.Step(false, true);
    Expect(Hold.Lane() == 1, "15 a held right press moves once");
    Game Both;
    Both.Reset(730);
    Both.Step(true, true);
    Expect(Both.Lane() == 0, "16 left wins when both directions are held");
    Game Opened;
    Opened.Reset(730);
    Expect(Opened.Closest() == 99, "17 closest starts empty");

    Game Live;
    std::string Line;
    int Runs = 0, Steps = 0;
    while (std::getline(In, Line)) {
        if (Line.empty() || Line[0] == '#') continue;
        if (Line.rfind("RUN ", 0) == 0) {
            std::istringstream Header(Line.substr(4));
            unsigned Seed = 0;
            int Option = 0;
            std::string Pace;
            Header >> Seed >> Option >> Pace;
            Live.SetDifficulty(Pace);
            Live.SetOption(Option, Seed);
            ++Runs;
            continue;
        }
        const char Move = Line[0];
        int Lane = -1, Passed = -1, Lost = -1, Cleared = -1;
        std::istringstream Body(Line.substr(1));
        Body >> Lane >> Passed >> Lost >> Cleared;
        Replay(Live, Move);
        ++Steps;
        if (Live.Lane() != Lane || Live.Passed() != Passed || static_cast<int>(Live.Lost()) != Lost || static_cast<int>(Live.Cleared()) != Cleared) {
            Expect(false, std::string("parity ") + Line);
            break;
        }
    }
    Expect(Runs == 3 && Steps > 40, "30 the fixture replays stand, practice and hard");
    if (Fails) std::cerr << Fails << " gap(s)\n";
    else std::cout << "siltlane core: " << Steps << " steps, " << Runs << " runs\n";
    return Fails == 0 ? 0 : 1;
}
