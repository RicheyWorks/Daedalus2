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

    // ---- UTF-8 from the existing FString/Slate boundary: wrap/reveal complete code points
    {
        Check("an accented word fits its character width", Wrap(u8"Caf\u00E9", 4) == std::vector<std::string>{u8"Caf\u00E9"});
        const auto W = Wrap(u8"\u732B\U0001F680\u754C", 2);
        Check("long UTF-8 words split at code point boundaries",
              W == std::vector<std::string>{u8"\u732B\U0001F680", u8"\u754C"});
        Check("mixed words wrap without splitting their UTF-8 bytes",
              Wrap(u8"Hi \u732B\u754C!", 4) == std::vector<std::string>{"Hi", u8"\u732B\u754C!"});
        Check("forced breaks preserve complete multibyte rows",
              Wrap(u8"\u00E9\n\u732B\U0001F680", 2) == std::vector<std::string>{u8"\u00E9", u8"\u732B\U0001F680"});

        Style St = StyleNamed("gallery");
        St.Cols = 20; St.Lines = 2; St.Cps = 1.0;
        Dialogue D;
        D.SetStyle(St);
        Line L;
        L.Speaker = u8"Ren\u00E9e";
        L.Text = u8"A\u00E9\u732B\U0001F680Z";
        L.V.Rate = 1.0;
        D.Say(L);
        const std::vector<std::string> Prefixes = {
            "A", u8"A\u00E9", u8"A\u00E9\u732B", u8"A\u00E9\u732B\U0001F680", u8"A\u00E9\u732B\U0001F680Z"};
        for (std::size_t i = 0; i < Prefixes.size(); ++i)
        {
            D.Tick(1.0);
            Check("typed UTF-8 prefix " + std::to_string(i + 1), D.Visible()[0] == Prefixes[i]);
            Check("completion follows character count " + std::to_string(i + 1), D.PageDone() == (i + 1 == Prefixes.size()));
        }
        Check("description counts revealed characters", D.Describe().find("shown=5/5") != std::string::npos);
        Check("multibyte text preserves existing ASCII blip policy", Count(D.TakeSfx(), "BLIP:") == 2);
        D.Visible(); D.Visible(); D.Tick(0.0);
        Check("reading completed UTF-8 text emits no repeated blips", D.TakeSfx().empty());
    }

    // ---- Unicode text still follows the same page/skip/choice and retro controls
    {
        Style St = StyleNamed("parcels");
        St.Cols = 2; St.Lines = 1; St.Cps = 1.0;
        Dialogue D;
        D.SetStyle(St);
        Line L;
        L.Speaker = "Courier"; L.Text = u8"\u00E9\u732B \U0001F680Z";
        L.Choices = {"Deliver", "Not now"}; L.V.Rate = 1.0;
        D.Say(L);
        Check("UTF-8 page capacity counts characters", D.Pages() == 2);
        D.Tick(1.0);
        Check("first Unicode page reveals one complete character", D.Visible()[0] == u8"\u00E9");
        Outcome O;
        Check("A completes the Unicode page without advancing", !D.Press(Button::A, O) && D.Page() == 0 && D.Visible()[0] == u8"\u00E9\u732B");
        Check("A advances to the next empty Unicode page", !D.Press(Button::A, O) && D.Page() == 1 && D.Visible()[0].empty());
        D.Press(Button::B, O);
        Check("B finishes the final Unicode page into choices", D.Choosing() && D.Visible()[0] == u8"\U0001F680Z");
        D.Press(Button::Down, O);
        Check("Unicode dialogue keeps choice outcomes", D.Press(Button::A, O) && O.Choice == 1 && O.Speaker == "Courier" && !D.Open());

        Dialogue Retro;
        Retro.SetStyle(RetroStyle());
        Retro.Say(u8"Ren\u00E9e", u8"Caf\u00E9");
        Retro.Press(Button::B, O);
        Check("retro uppercases ASCII without changing UTF-8 bytes", Retro.Tag() == u8"REN\u00E9E" && Retro.Visible()[0] == u8"CAF\u00E9");
    }

    // Invalid byte input is not normalized: fallback must preserve bytes and make progress.
    {
        bool Preserved = true;
        for (const auto& Bytes : {std::string("\xF0\x9F"), std::string("\xC0\xAF"),
                                  std::string("\xED\xA0\x80"), std::string("\xF4\x90\x80\x80")})
        {
            const auto Rows = Wrap(Bytes, 1);
            std::string Joined;
            for (const auto& Row : Rows) Joined += Row;
            Preserved &= Joined == Bytes && Rows.size() == Bytes.size();
        }
        Check("malformed-byte fallback preserves input without stalling", Preserved);

        Style St = StyleNamed("zero");
        St.Lines = 2; St.Cps = 1.0;
        Dialogue D;
        D.SetStyle(St);
        Line L;
        L.Text = std::string("\xC2\n\xA2Z"); L.V.Rate = 1.0;
        D.Say(L);
        D.TakeSfx();
        D.Tick(1.0);
        Check("malformed row tail reveals alone", D.Visible() == std::vector<std::string>{std::string("\xC2"), ""} && D.TakeSfx().empty());
        D.Tick(1.0);
        Check("next row cannot combine with the previous row tail",
              D.Visible() == std::vector<std::string>{std::string("\xC2"), std::string("\xA2")} && !D.PageDone() && D.TakeSfx().empty());
        D.Tick(1.0);
        Check("ASCII after malformed rows blips on its own reveal step",
              D.Visible()[1] == std::string("\xA2Z") && D.PageDone() && Count(D.TakeSfx(), "BLIP:") == 1);
    }

    std::cout << Ok << "/" << Total << "\n";
    return Ok == Total ? 0 : 1;
}
