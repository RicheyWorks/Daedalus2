// SPDX-License-Identifier: MIT

#pragma once

// Dialogue boxes for every realm (Richey, 2026-10-13): "old school realms have dialogue boxes and new school does too,
// like Animal Crossing". The 8-bit realm draws Final Fantasy 1 windows (DaedalusRealmLook.h Ui::Dialogue); the 3D
// realms speak through this model drawn by SDaedalusDialogue in each realm's theme. The behaviour is one thing:
//
//   * a speaker with a name tag, a text that wraps to the box, pages when it won't fit, and a typewriter that reveals
//     it (a blip per letter, pitched by the speaker's voice so every NPC babbles its own way: Animal Crossing's
//     "animalese", the way the 8-bit realm's jukebox gets its SFX);
//   * A: finish the page, then the next page, then the choices (if any), then close; B: skip to the end of the text;
//   * choices (YES/NO, a shop's BUY/SELL/LEAVE, a riddle's answers) with up/down and A;
//   * an era: Retro types in upper case at 60 cps in a square window; Modern types mixed case at 40 cps in a rounded
//     bubble with a bounce on the name tag. The era is the realm's; the text is the NPC's.
//
// Pure C++17 (core-test/dialogue_core_test.cpp). The jukebox takes the blips as events ("BLIP:<pitch>").

#include <algorithm>
#include <cctype>
#include <cstdint>
#include <string>
#include <vector>

namespace daedalus
{
namespace dlg
{

enum class Era { Retro, Modern };

struct Style
{
    Era E = Era::Modern;
    int Cols = 36;              // UTF-8 code points per line (not rendered glyph width)
    int Lines = 3;              // lines per page
    double Cps = 40.0;          // typewriter speed
    bool Upper = false;         // Retro realms shout in capitals
    uint32_t Panel = 0x1C1A14, Ink = 0xF5E9C8, Text = 0xFFFDF5, Name = 0x8CD36C, Dim = 0x8F8A7A;
    int Corner = 18;            // px; 0 = the retro window
    std::string Font = "MODERN"; // or PIXEL
};

inline Style RetroStyle()
{
    Style S;
    S.E = Era::Retro; S.Cols = 28; S.Lines = 4; S.Cps = 60.0; S.Upper = true;
    S.Panel = 0x000000; S.Ink = 0xF8A070; S.Text = 0xFCFCFC; S.Name = 0xF8D878; S.Dim = 0x7C7C7C; S.Corner = 0; S.Font = "PIXEL";
    return S;
}

/** The style a realm's dialogue wears. Themes match DaedalusInventoryCore's names so a realm reads as one thing. */
inline Style StyleNamed(const std::string& Theme)
{
    if (Theme == "retro") return RetroStyle();
    Style S;
    if (Theme == "gallery") { S.Panel = 0x0E0F13; S.Ink = 0xFF4FD8; S.Name = 0x3DF7C0; S.Corner = 6; }
    else if (Theme == "parcels") { S.Panel = 0x2A1F14; S.Ink = 0xD9B27C; S.Name = 0xF2C14E; S.Corner = 22; }
    else if (Theme == "bricks") { S.Panel = 0xB3261E; S.Ink = 0xF9D71C; S.Name = 0xFFFFFF; S.Dim = 0xF3B5B0; S.Corner = 8; }
    else if (Theme == "labyrinth") { S.Panel = 0x101418; S.Ink = 0x6AA0FF; S.Name = 0xFF6A6A; S.Corner = 0; }
    else if (Theme == "zero") { S.Panel = 0x0B1F14; S.Ink = 0x7CFF9A; S.Name = 0xFFE066; S.Corner = 16; }
    return S;
}

namespace detail
{
/** Valid UTF-8 scalar values stay whole. A malformed byte is one unit, preserved unchanged. */
inline size_t Utf8UnitBytes(const std::string& Text, size_t At)
{
    if (At >= Text.size()) return 0;
    const unsigned char Lead = static_cast<unsigned char>(Text[At]);
    if (Lead < 0x80) return 1;
    const size_t Width = Lead >= 0xC2 && Lead <= 0xDF ? 2
        : Lead >= 0xE0 && Lead <= 0xEF ? 3 : Lead >= 0xF0 && Lead <= 0xF4 ? 4 : 1;
    if (Width == 1 || Width > Text.size() - At) return 1;
    for (size_t I = 1; I < Width; ++I)
    {
        const unsigned char C = static_cast<unsigned char>(Text[At + I]);
        if (C < 0x80 || C > 0xBF) return 1;
    }
    const unsigned char Second = static_cast<unsigned char>(Text[At + 1]);
    if ((Lead == 0xE0 && Second < 0xA0) || (Lead == 0xED && Second >= 0xA0)
        || (Lead == 0xF0 && Second < 0x90) || (Lead == 0xF4 && Second >= 0x90)) return 1;
    return Width;
}

inline size_t Utf8Count(const std::string& Text)
{
    size_t Count = 0;
    for (size_t At = 0; At < Text.size(); At += Utf8UnitBytes(Text, At)) ++Count;
    return Count;
}

inline size_t Utf8PrefixBytes(const std::string& Text, size_t Count)
{
    size_t End = 0;
    for (; Count > 0 && End < Text.size(); --Count) End += Utf8UnitBytes(Text, End);
    return End;
}

inline char AsciiUpper(char C) { return C >= 'a' && C <= 'z' ? static_cast<char>(C - 'a' + 'A') : C; }
} // namespace detail

/** A voice: how an NPC babbles. Pitch 0..11 (the jukebox picks the note), Rate scales the typewriter. */
struct Voice
{
    int Pitch = 5;
    double Rate = 1.0;
    /** A voice from a name, so the same NPC always sounds the same without anyone tuning it. */
    static Voice FromName(const std::string& Name)
    {
        uint32_t H = 2166136261u;
        for (char C : Name) { H ^= static_cast<unsigned char>(detail::AsciiUpper(C)); H *= 16777619u; }
        Voice V;
        V.Pitch = static_cast<int>(H % 12);
        V.Rate = 0.85 + static_cast<double>((H / 12) % 7) * 0.05;   // 0.85 .. 1.15
        return V;
    }
};

/** Word-wrap by UTF-8 code points, honouring '\n'. Widths below one use one; no grapheme/display-width layout. */
inline std::vector<std::string> Wrap(const std::string& Text, int Cols)
{
    std::vector<std::string> Out;
    std::string Line, Word;
    const size_t Width = static_cast<size_t>(std::max(1, Cols));
    size_t LineChars = 0;
    auto Flush = [&]() { Out.push_back(Line); Line.clear(); LineChars = 0; };
    auto PutWord = [&]() {
        if (Word.empty()) return;
        size_t WordChars = detail::Utf8Count(Word);
        if (!Line.empty() && LineChars + 1 + WordChars > Width) Flush();
        while (WordChars > Width)   // a word longer than the line: cut at a code-point boundary
        {
            if (!Line.empty()) Flush();
            const size_t End = detail::Utf8PrefixBytes(Word, Width);
            Out.push_back(Word.substr(0, End));
            Word.erase(0, End);
            WordChars -= Width;
        }
        if (!Line.empty()) { Line += ' '; ++LineChars; }
        Line += Word;
        LineChars += WordChars;
        Word.clear();
    };
    for (char C : Text)
    {
        if (C == '\n') { PutWord(); Flush(); }
        else if (C == ' ') PutWord();
        else Word += C;
    }
    PutWord();
    if (!Line.empty() || Out.empty()) Out.push_back(Line);
    while (Out.size() > 1 && Out.back().empty()) Out.pop_back();
    return Out;
}

/** One utterance: who, what, and the choices it ends on. */
struct Line
{
    std::string Speaker, Text;
    std::vector<std::string> Choices;   // empty: A closes it
    Voice V;
};

enum class Button { A, B, Up, Down };

/** What the player did that the host must know: a line closed (Choice = -1) or a choice was picked. */
struct Outcome
{
    bool Closed = false;
    int Choice = -1;
    std::string Speaker;
};

class Dialogue
{
public:
    void SetStyle(const Style& S) { St = S; }
    const Style& GetStyle() const { return St; }

    /** Queue a line; the first one opens the box. */
    void Say(const Line& L)
    {
        Queue.push_back(L);
        if (!IsOpen) Next();
    }
    void Say(const std::string& Speaker, const std::string& Text, std::vector<std::string> Choices = {})
    {
        Line L;
        L.Speaker = Speaker; L.Text = Text; L.Choices = std::move(Choices); L.V = Voice::FromName(Speaker);
        Say(L);
    }

    bool Open() const { return IsOpen; }
    const Line& Current() const { return Cur; }
    int Page() const { return PageIdx; }
    int Pages() const { return std::max(1, (static_cast<int>(Rows.size()) + St.Lines - 1) / St.Lines); }
    bool LastPage() const { return PageIdx >= Pages() - 1; }
    bool PageDone() const { return Shown >= PageChars(); }
    bool Choosing() const { return IsChoosing; }
    int Cursor() const { return ChoiceIdx; }
    /** The rows of the current page, the last one cut to what the typewriter has shown. */
    std::vector<std::string> Visible() const
    {
        std::vector<std::string> V;
        int Left = static_cast<int>(Shown);
        for (int i = PageIdx * St.Lines; i < std::min(static_cast<int>(Rows.size()), (PageIdx + 1) * St.Lines); ++i)
        {
            const std::string& R = Rows[static_cast<size_t>(i)];
            if (Left <= 0) { V.push_back(""); continue; }
            V.push_back(R.substr(0, detail::Utf8PrefixBytes(R, static_cast<size_t>(Left))));
            Left -= static_cast<int>(detail::Utf8Count(R));
        }
        return V;
    }
    std::string Tag() const { return St.Upper ? Up(Cur.Speaker) : Cur.Speaker; }
    /** The tag's bounce (Modern): 0..1 over the first half second after a line opens. */
    double TagBounce() const { return St.E == Era::Modern && Age < 0.5 ? 1.0 - Age / 0.5 : 0.0; }
    /** A hint that more waits: the little arrow, blinking at 2 Hz once the page is typed. */
    bool MoreArrow() const { return IsOpen && PageDone() && !IsChoosing && (static_cast<int>(Age * 4) % 2 == 0); }

    /** Reveal code points; existing ASCII letters/digits blip. No Unicode letter classification is attempted. */
    void Tick(double Dt)
    {
        if (!IsOpen) return;
        Age += Dt;
        if (PageDone())
        {
            if (LastPage() && !Cur.Choices.empty() && !IsChoosing) { IsChoosing = true; ChoiceIdx = 0; }
            return;
        }
        const double Before = Shown;
        Shown = std::min(static_cast<double>(PageChars()), Shown + Dt * St.Cps * Cur.V.Rate);
        int CharIdx = 0;
        for (int Row = PageIdx * St.Lines; Row < std::min(static_cast<int>(Rows.size()), (PageIdx + 1) * St.Lines); ++Row)
        {
            const std::string& Text = Rows[static_cast<size_t>(Row)];
            // Step rows separately: malformed bytes on adjoining rows must not combine into a new scalar value.
            for (size_t At = 0; At < Text.size() && CharIdx < static_cast<int>(Shown); At += detail::Utf8UnitBytes(Text, At), ++CharIdx)
            {
                const unsigned char C = static_cast<unsigned char>(Text[At]);
                if (CharIdx >= static_cast<int>(Before) && C < 0x80 && std::isalnum(C))
                {
                    const bool Vowel = std::string("AEIOUaeiou").find(static_cast<char>(C)) != std::string::npos;
                    Sfx.push_back("BLIP:" + std::to_string((Cur.V.Pitch + (Vowel ? 4 : 0) + (CharIdx % 3)) % 12));
                }
            }
            if (CharIdx >= static_cast<int>(Shown)) break;
        }
        if (PageDone() && LastPage() && !Cur.Choices.empty() && !IsChoosing) { IsChoosing = true; ChoiceIdx = 0; }
    }

    /** A button. Returns true with Out when the host has something to do (a line closed or a choice was picked). */
    bool Press(Button B, Outcome& Out)
    {
        Out = Outcome();
        if (!IsOpen) return false;
        if (IsChoosing)
        {
            const int N = static_cast<int>(Cur.Choices.size());
            if (B == Button::Up) { ChoiceIdx = (ChoiceIdx + N - 1) % N; Sfx.push_back("TICK"); return false; }
            if (B == Button::Down) { ChoiceIdx = (ChoiceIdx + 1) % N; Sfx.push_back("TICK"); return false; }
            if (B == Button::B) { ChoiceIdx = N - 1; Sfx.push_back("TICK"); return false; }   // B lands on the last choice (NO / LEAVE)
            Out.Choice = ChoiceIdx; Out.Speaker = Cur.Speaker;
            Sfx.push_back("PICK");
            Close(Out);
            return true;
        }
        if (B == Button::B) { Shown = PageChars(); if (!LastPage()) { PageIdx = Pages() - 1; Shown = PageChars(); } Tick(0.0); return false; }
        if (B != Button::A) return false;
        if (!PageDone()) { Shown = PageChars(); Tick(0.0); return false; }   // A finishes the page first
        if (!LastPage()) { ++PageIdx; Shown = 0.0; Sfx.push_back("PAGE"); return false; }
        if (!Cur.Choices.empty()) { IsChoosing = true; ChoiceIdx = 0; return false; }
        Out.Closed = true; Out.Speaker = Cur.Speaker;
        Close(Out);
        return true;
    }

    std::vector<std::string> TakeSfx() { std::vector<std::string> S; S.swap(Sfx); return S; }

    std::string Describe() const
    {
        if (!IsOpen) return "open=0 queued=" + std::to_string(Queue.size());
        std::string S = "open=1 era=" + std::string(St.E == Era::Retro ? "RETRO" : "MODERN") + " who=" + Cur.Speaker + " page=" + std::to_string(PageIdx + 1) + "/" + std::to_string(Pages())
            + " shown=" + std::to_string(static_cast<int>(Shown)) + "/" + std::to_string(PageChars());
        if (IsChoosing) S += " choosing=" + std::to_string(ChoiceIdx) + "/" + std::to_string(Cur.Choices.size());
        return S;
    }

private:
    static std::string Up(std::string S) { for (char& C : S) C = detail::AsciiUpper(C); return S; }

    void Next()
    {
        if (Queue.empty()) { IsOpen = false; return; }
        Cur = Queue.front();
        Queue.erase(Queue.begin());
        Rows = Wrap(St.Upper ? Up(Cur.Text) : Cur.Text, St.Cols);
        PageIdx = 0; Shown = 0.0; Age = 0.0; IsChoosing = false; ChoiceIdx = 0; IsOpen = true;
        Sfx.push_back("OPEN");
    }

    void Close(Outcome&)
    {
        IsOpen = false;
        if (!Queue.empty()) Next();   // the next line opens straight away
    }

    int PageChars() const
    {
        int Count = 0;
        for (int i = PageIdx * St.Lines; i < std::min(static_cast<int>(Rows.size()), (PageIdx + 1) * St.Lines); ++i)
            Count += static_cast<int>(detail::Utf8Count(Rows[static_cast<size_t>(i)]));
        return Count;
    }

    Style St;
    std::vector<Line> Queue;
    Line Cur;
    std::vector<std::string> Rows;
    std::vector<std::string> Sfx;
    int PageIdx = 0, ChoiceIdx = 0;
    double Shown = 0.0, Age = 0.0;
    bool IsOpen = false, IsChoosing = false;
};

} // namespace dlg
} // namespace daedalus
