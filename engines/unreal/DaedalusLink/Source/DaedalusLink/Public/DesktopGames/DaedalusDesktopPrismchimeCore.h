// SPDX-License-Identifier: MIT
// Prismchime Ring (Prismheart cabinet): the ADaedalusDesktopArcade host for DaedalusPrismchimeCore.h, a port of
// tools/minigames/prismchime.py (the rules authority). CPython-compatible seeding, so StartGame("prismchime", seed)
// hangs the same ring as prismchime.start(seed, difficulty).
//
//   Left/Right or stick   pick a chime (the cursor walks the ring)
//   pad A / J / Space     tap it
//   R / pad Start         restart a finished ring
//   option 0 Ring; option 1 Guide practice marks the chime demo_action would tap
#pragma once
#include "DaedalusDesktopGameTypes.h"
#include "DaedalusDesktopSaveText.h"
#include "DaedalusPrismchimeCore.h"
#include <cmath>
#include <string>
#include <vector>

namespace daedalus { namespace desktop {

class PrismchimeGame final : public Game {
    prismchime::Game Core;
    std::uint32_t SessionSeed = 730;
    int Option = 0;
    int Cursor = 0;
    int LastPealed = -1;      // peals from the last tap; -1 until the first
    EdgeLatch PrevEdge, NextEdge, ConfirmEdge;

    static constexpr int MaxScore = 10000;
    static constexpr int MaxPeals = 1000;

    void Deal() {
        Core.Start(SessionSeed, CabinetDifficulty());
        ResetTable();
    }
    void ResetTable() {
        Cursor = 0;
        LastPealed = -1;
        PrevEdge.Clear();
        NextEdge.Clear();
        ConfirmEdge.Clear();
    }
    static bool GoPrev(const Input& I) { return I.Left || I.Up || I.PadLeft || I.PadUp || I.AxisX < -0.4 || I.AxisY < -0.4; }
    static bool GoNext(const Input& I) { return I.Right || I.Down || I.PadRight || I.PadDown || I.AxisX > 0.4 || I.AxisY > 0.4; }
    static bool Confirm(const Input& I) { return I.FirePressed || I.JumpPressed || I.ActionPressed || I.DashPressed; }
    void Move(int Direction) {
        const int N = Core.Chimes();
        if(N <= 0) return;
        Cursor = ((Cursor + Direction) % N + N) % N;
    }
    /** Parses "+1,-1,..." into facings. */
    static bool ParseFacing(const std::string& Text, int Count, std::vector<int>& Out) {
        Out.clear();
        for(const std::string& Token : SplitText(Text, ',')) {
            if(Token == "+1") Out.push_back(1);
            else if(Token == "-1") Out.push_back(-1);
            else return false;
        }
        return static_cast<int>(Out.size()) == Count;
    }
    /** Parses "0110..." into lit flags. */
    static bool ParseLit(const std::string& Text, int Count, std::vector<bool>& Out) {
        Out.clear();
        for(char Ch : Text) {
            if(Ch != '0' && Ch != '1') return false;
            Out.push_back(Ch == '1');
        }
        return static_cast<int>(Out.size()) == Count;
    }

public:
    const prismchime::Game& CoreState() const { return Core; }
    int CursorChime() const { return Cursor; }
    int LastPealCount() const { return LastPealed; }

    void Reset(std::uint32_t Seed) override {
        SessionSeed = Seed;
        Deal();
    }
    bool SetCabinetDifficulty(const std::string& Name) override {
        if(!Game::SetCabinetDifficulty(Name)) return false;
        Deal();
        return true;
    }
    bool SetOption(int Value, std::uint32_t Seed) override {
        if(Value < 0 || Value > 1) return false;
        Option = Value;
        SessionSeed = Seed;
        Deal();
        return true;
    }
    int GetOption() const override { return Option; }

    bool Tap() {
        if(Core.Over) return false;
        int Pealed = 0;
        std::string Result;
        if(Core.Tap(Cursor, Pealed, Result) != prismchime::Game::Act::Ok) return false;
        LastPealed = Pealed;
        return true;
    }

    bool SourceKeyDown(int Key) override {
        if(Core.Over) {
            if(!SourceKey::IsRestart(Key)) return false;
            Deal();
            return true;
        }
        if(Key == SourceKey::Up || Key == SourceKey::Left) Move(-1);
        else if(Key == SourceKey::Down || Key == SourceKey::Right) Move(1);
        else if(SourceKey::IsConfirm(Key)) Tap();
        return false;
    }
    bool SourceControllerButton(int Button) override {
        if(Button == PadButton::A && !Core.Over) {
            Tap();
            return true;
        }
        if(Button == PadButton::Start && Core.Over) {
            Deal();
            return true;
        }
        return false;
    }
    void Step(const Input& I) override {
        if(Core.Over) {
            if(Confirm(I)) Deal();
            return;
        }
        const bool Prev = PrevEdge.Rose(GoPrev(I));
        const bool Next = NextEdge.Rose(GoNext(I));
        if(Prev) Move(-1);
        else if(Next) Move(1);
        if(ConfirmEdge.Rose(Confirm(I))) Tap();
    }

    std::string SaveState() const override {
        return SaveWriter(prismchime::GameId())
            .Field("d", CabinetDifficulty())
            .Field("seed", SessionSeed)
            .Field("taps", Core.Taps)
            .Field("peals", Core.Peals)
            .Field("score", Core.Score)
            .Flag("over", Core.Over)
            .Flag("won", Core.Won)
            .Field("cursor", Cursor)
            .Field("charge", Core.ChargeString())
            .Field("facing", Core.FacingString())
            .Field("lit", Core.LitString())
            .Text();
    }
    // No draws happen after Start, so the stream needs no fast-forward; the ring is range-checked instead (charges are
    // always below Peal between taps, facings are +1/-1, the lit mask matches the ring).
    bool RestoreState(const std::string& Text, std::uint32_t) override {
        const SaveFields Fields(Text, prismchime::GameId());
        if(!Fields.IsValid()) return false;
        const std::string DifficultyName = Fields.Str("d");
        const prismchime::Difficulty* Diff = prismchime::FindDifficulty(DifficultyName);
        if(!Diff) return false;

        std::uint32_t Seed = 0;
        int Taps = 0, Peals = 0, Score = 0, SavedCursor = 0;
        bool Over = false, Won = false;
        std::vector<int> Charge, Facing;
        std::vector<bool> Lit;
        if(!Fields.Seed("seed", Seed)) return false;
        if(!Fields.Int("taps", 0, Diff->Taps, Taps)) return false;
        if(!Fields.Int("peals", 0, MaxPeals, Peals)) return false;
        if(!Fields.Int("score", 0, MaxScore, Score)) return false;
        if(!Fields.Flag("over", Over) || !Fields.Flag("won", Won)) return false;
        if(!Fields.Int("cursor", 0, Diff->Chimes - 1, SavedCursor)) return false;
        if(!Fields.IntList("charge", 0, prismchime::Peal - 1, Charge) || static_cast<int>(Charge.size()) != Diff->Chimes) return false;
        if(!ParseFacing(Fields.Str("facing"), Diff->Chimes, Facing)) return false;
        if(!ParseLit(Fields.Str("lit"), Diff->Chimes, Lit)) return false;
        if(Taps == 0 && !Over) return false;

        if(!Core.Start(Seed, DifficultyName)) return false;   // keeps Diff and the seeded stream position honest
        Game::SetCabinetDifficulty(DifficultyName);
        SessionSeed = Seed;
        Core.Charge = Charge;
        Core.Facing = Facing;
        Core.Lit = Lit;
        Core.Taps = Taps;
        Core.Peals = Peals;
        Core.Score = Score;
        Core.Over = Over;
        Core.Won = Won;
        ResetTable();
        Cursor = SavedCursor;
        return true;
    }
    std::uint32_t SeedAfterRestore(std::uint32_t) const override { return SessionSeed; }

    std::string HintLine() const {
        if(Core.Over) {
            return Core.Won ? "HINT Every chime rings. Pad A or R hangs a new ring."
                            : "HINT The ring fell silent. Pad A or R hangs a new ring.";
        }
        if(Option == 1) return "HINT Practice: the blue ring marks the chime the watcher would tap.";
        if(LastPealed > 1) return "HINT Chain! Peals charge their neighbours; look for the next chime one short of four.";
        return "HINT A tap pulses a chime's charge along its arrow; a chime at four peals and lights.";
    }
    std::string ActionCue() const {
        if(Core.Over) return "CUE Retry";
        return Core.Taps == 1 ? "CUE Last tap" : "CUE Tap a chime";
    }
    std::string HowToLine() const override {
        return "HOW Tap a chime to ring it: its charge pulses along its facing and it gains one; a chime that fills to four peals and charges both neighbours. Light every chime before your taps run out.";
    }
    std::string KeyHint() const override { return "KEYS Left or Right picks a chime; A taps it."; }
    std::string ContrastMark() const override { return Core.Over ? "MARK WAIT" : "MARK ACT"; }

    void Render(Frame& F) const override {
        const Color Pearl{236, 232, 255, 255}, Gold{255, 236, 180, 255}, Sky{120, 225, 255, 255}, Dark{40, 36, 60, 255};
        const int Taps = Core.Diff ? Core.Diff->Taps : 0;

        F.Clear(800, 600, {12, 10, 22, 255});
        F.AddText(28, 20, std::string(Option == 1 ? "PRISMCHIME GUIDE  [" : "PRISMCHIME RING  [") + CabinetDifficulty() + "]", Pearl, 26);
        F.AddText(28, 56, "TAPS " + std::to_string(Core.Taps) + "/" + std::to_string(Taps) + "   LIT: " + std::to_string(Core.LitCount()) + "/" + std::to_string(Core.Chimes())
                          + "   PEALS: " + std::to_string(Core.Peals) + "   SCORE: " + std::to_string(Core.Score), White, 18);
        const int N = Core.Chimes();
        if(N <= 0) return;

        // The ring: chimes on a circle from twelve o'clock; fill shows charge 0..3, lit chimes glow, arrows show facing
        const double CX = 330, CY = 310, Radius = 160, Bell = 26;
        const int Guide = (Option == 1 && !Core.Over) ? Core.DemoAction() : -1;
        F.AddCircle(CX, CY, Radius + Bell + 12, {26, 22, 44, 255});
        F.AddCircle(CX, CY, Radius - Bell - 12, {12, 10, 22, 255});
        for(int I = 0; I < N; ++I) {
            const double Angle = -1.5707963267948966 + 6.283185307179586 * I / static_cast<double>(N);
            const double X = CX + Radius * std::cos(Angle), Y = CY + Radius * std::sin(Angle);
            const int Charge = Core.Charge[static_cast<size_t>(I)];
            const bool Lit = Core.Lit[static_cast<size_t>(I)];
            if(I == Cursor && !Core.Over) F.AddCircle(X, Y, Bell + 7, Gold);
            if(I == Guide) F.AddCircle(X, Y, Bell + 4, Sky);
            F.AddCircle(X, Y, Bell, Lit ? Color{255, 228, 150, 255} : Dark);
            // charge pips stack inside the bell
            for(int P = 0; P < Charge; ++P) F.AddRect(X - 10, Y + 10 - P * 8, 20, 5, Lit ? Color{120, 90, 30, 255} : Pearl);
            // facing arrow along the ring tangent
            const double TX = -std::sin(Angle), TY = std::cos(Angle), Dir = Core.Facing[static_cast<size_t>(I)] > 0 ? 1.0 : -1.0;
            const double AX = X + TX * Dir * (Bell + 14), AY = Y + TY * Dir * (Bell + 14);
            F.AddTriangle({AX + TX * Dir * 8, AY + TY * Dir * 8}, {AX - TY * 5, AY + TX * 5}, {AX + TY * 5, AY - TX * 5}, Sky);
            F.AddText(X - 6, Y - 32, std::to_string(I + 1), White, 12);
        }
        if(LastPealed >= 0 && !Core.Over) F.AddText(CX - 60, CY - 10, std::to_string(LastPealed) + (LastPealed == 1 ? " peal" : " peals"), Gold, 22);
        if(Core.Over) F.AddText(CX - 120, CY - 12, Core.Won ? "WON: EVERY CHIME RINGS" : "LOST: THE RING FALLS SILENT", Gold, 22);

        F.AddText(580, 120, "PEAL AT 4", Pearl, 14);
        for(int P = 0; P < prismchime::Peal; ++P) F.AddRect(580, 150 + P * 14, 60, 10, P < Core.Charge[static_cast<size_t>(Cursor)] ? Gold : Dark);
        F.AddText(580, 215, "chime " + std::to_string(Cursor + 1), White, 14);

        F.AddText(28, 528, HowToLine(), Gold, 13);
        F.AddText(28, 548, HintLine(), Gold, 16);
        DrawAccess(F, 300, 500, KeyHint(), ContrastMark());
        F.AddText(620, 548, ActionCue(), Sky, 16);
    }
    Status GetStatus() const override {
        const std::string LitText = std::to_string(Core.LitCount()) + "/" + std::to_string(Core.Chimes());
        if(Core.Over) {
            const std::string Outcome = Core.Won ? "Every chime rings; " : "The ring fell silent; ";
            return {Core.Score, 0, true, Core.Won, Outcome + "pad A or R hangs a new ring; lit " + LitText};
        }
        return {Core.Score, 1, false, false, "Taps " + std::to_string(Core.Taps) + "; lit " + LitText + "; peals " + std::to_string(Core.Peals)};
    }
};

}} // daedalus::desktop
