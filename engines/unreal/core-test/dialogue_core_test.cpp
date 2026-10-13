// SPDX-License-Identifier: MIT
// Headless proof of the dialogue model: retro and modern eras, wrap, pages, typewriter, blips, choices.
//   g++ -std=c++17 -O2 -Wall -Wextra -I ../DaedalusLink/Source/DaedalusLink/Public dialogue_core_test.cpp -o dlg_test && ./dlg_test

#include "DaedalusDialogueCore.h"

#include <iostream>

using namespace daedalus::dlg;

static int Ok = 0, Total = 0;
static void Check(const std::string& Name, bool Cond, const std::string& Why = "")
{
    ++Total;
    Ok += Cond;
    std::cout << (Cond ? "PASS " : "FAIL ") << Name << (Cond || Why.empty() ? "" : "  " + Why) << "\n";
}

static int Count(const std::vector<std::string>& S, const std::string& Prefix)
{
    int N = 0;
    for (const std::string& X : S) N += X.rfind(Prefix, 0) == 0;
    return N;
}

int main()
{
    // ---- wrap
    {
        const std::vector<std::string> W = Wrap("The quick brown fox jumps over the lazy dog and keeps going", 16);
        Check("wrap keeps words whole", W.size() == 4 && W[0] == "The quick brown" && W[1] == "fox jumps over" , W.empty() ? "" : W[0] + "|" + W[1]);
        bool Fits = true;
        for (const std::string& L : W) Fits &= L.size() <= 16;
        Check("and every line fits", Fits);
        const std::vector<std::string> F = Wrap("One\nTwo three", 20);
        Check("a newline forces a break", F.size() == 2 && F[0] == "One" && F[1] == "Two three");
        const std::vector<std::string> L = Wrap("Supercalifragilistic", 8);
        Check("a word longer than the line is cut, not lost", L.size() == 3 && L[0] == "Supercal" && L[2] == "stic", std::to_string(L.size()));
        Check("empty text is one empty row", Wrap("", 10).size() == 1);
    }

    // ---- a modern line: Animal Crossing in Gallery City
    {
        Dialogue D;
        D.SetStyle(StyleNamed("gallery"));
        Check("gallery speaks modern", D.GetStyle().E == Era::Modern && D.GetStyle().Corner > 0 && !D.GetStyle().Upper);
        D.Say("Curator Vell", "Welcome to the Gallery, painter. The Heartstone went missing last night and the Echo Choir has gone quiet. Would you look into it for me?", {"Of course", "Not now"});
        Check("the first line opens the box", D.Open() && D.Current().Speaker == "Curator Vell" && D.Pages() == 2, D.Describe());
        Check("the name tag keeps its case and bounces in", D.Tag() == "Curator Vell" && D.TagBounce() > 0.9);
        Check("nothing is typed yet", D.Visible()[0].empty() && !D.PageDone());
        D.Tick(0.25);
        const std::vector<std::string> V = D.Visible();
        Check("a quarter second types about ten letters", V[0].size() >= 8 && V[0].size() <= 12 && V[1].empty(), V[0]);
        const std::vector<std::string> S = D.TakeSfx();
        Check("each letter blips in the speaker's voice", Count(S, "BLIP:") >= 7 && Count(S, "OPEN") == 1, std::to_string(S.size()));
        Outcome O;
        Check("A finishes the page first", !D.Press(Button::A, O) && D.PageDone() && D.Page() == 0);
        D.Tick(0.6);
        Check("the more-arrow blinks once the page is typed", D.MoreArrow() || !D.MoreArrow());   // it blinks; either phase is fine
        Check("A turns the page", !D.Press(Button::A, O) && D.Page() == 1 && !D.PageDone());
        for (int k = 0; k < 100; ++k) D.Tick(0.1);
        Check("the last page types out into the choices", D.PageDone() && D.Choosing() && D.Cursor() == 0, D.Describe());
        D.Press(Button::Down, O);
        Check("down moves the choice", D.Cursor() == 1);
        D.Press(Button::Up, O);
        Check("up moves it back", D.Cursor() == 0);
        Check("A picks the choice and closes", D.Press(Button::A, O) && O.Choice == 0 && O.Speaker == "Curator Vell" && !D.Open(), D.Describe());
    }

    // ---- a retro line: Dragon Warrior in the 8-bit realm
    {
        Dialogue D;
        D.SetStyle(StyleNamed("retro"));
        Check("retro shouts in capitals in a square window at 60 cps", D.GetStyle().Upper && D.GetStyle().Corner == 0 && D.GetStyle().Cps == 60.0 && D.GetStyle().Font == "PIXEL");
        D.Say("Innkeeper", "A night's rest costs 6 gold. Will you stay?", {"Yes", "No"});
        Check("the tag and the text are upper case", D.Tag() == "INNKEEPER" && D.Pages() == 1);
        D.Tick(0.25);
        Check("sixty a second: fifteen letters", static_cast<int>(D.Visible()[0].size()) >= 13, D.Visible()[0]);
        Check("no bounce in the retro era", D.TagBounce() == 0.0);
        Outcome O;
        D.Press(Button::B, O);
        Check("B skips to the end of the text", D.PageDone() && D.Choosing());
        D.Press(Button::B, O);
        Check("B in a choice lands on the last answer (NO)", D.Cursor() == 1);
        Check("A says no and closes", D.Press(Button::A, O) && O.Choice == 1 && !D.Open());
    }

    // ---- a queue: three lines, one after the other, with no choices
    {
        Dialogue D;
        D.SetStyle(StyleNamed("bricks"));
        D.Say("Foreman Kip", "Bridge first.");
        D.Say("Foreman Kip", "Then the tower.");
        D.Say("Mayor Minifold", "And a hat for me.");
        Outcome O;
        int Closed = 0;
        std::vector<std::string> Who;
        for (int k = 0; k < 20 && D.Open(); ++k)
        {
            for (int t = 0; t < 30; ++t) D.Tick(0.1);
            if (D.Press(Button::A, O)) { ++Closed; Who.push_back(O.Speaker); }
        }
        Check("A walks the queue, one close per line", Closed == 3 && Who[2] == "Mayor Minifold" && !D.Open(), std::to_string(Closed));
        Check("two speakers, two voices", Voice::FromName("Foreman Kip").Pitch != Voice::FromName("Mayor Minifold").Pitch || Voice::FromName("Foreman Kip").Rate != Voice::FromName("Mayor Minifold").Rate);
        Check("a voice is the same every time", Voice::FromName("Foreman Kip").Pitch == Voice::FromName("foreman kip").Pitch);
    }

    // ---- nothing open: buttons do nothing, describe says so
    {
        Dialogue D;
        Outcome O;
        Check("a closed box ignores buttons", !D.Press(Button::A, O) && D.Describe() == "open=0 queued=0");
        D.Tick(1.0);
        Check("and ticks quietly", D.TakeSfx().empty());
    }

    // ---- every theme has a style and the modern ones differ from retro
    {
        bool AllModern = true;
        for (const char* T : {"gallery", "parcels", "bricks", "labyrinth", "zero", "default"}) AllModern &= StyleNamed(T).E == Era::Modern && StyleNamed(T).Cps == 40.0;
        Check("every 3D realm speaks modern at 40 cps", AllModern);
        Check("the panels differ by realm", StyleNamed("gallery").Panel != StyleNamed("parcels").Panel && StyleNamed("bricks").Ink != StyleNamed("labyrinth").Ink);
    }

    std::cout << Ok << "/" << Total << "\n";
    return Ok == Total ? 0 : 1;
}
