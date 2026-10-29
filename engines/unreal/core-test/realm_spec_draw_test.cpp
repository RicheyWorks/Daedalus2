// SPDX-License-Identifier: MIT
// Direct, engine-free checks of DaedalusRealmSpec.h (the realm spec parser) and DaedalusRealmDraw.h (tiles, colour,
// text wrap, frame). realm_core_test.cpp walks a whole realm; this pins the parser's refusals and the draw
// primitives one by one. Build: g++ -std=c++17 -I../DaedalusLink/Source/DaedalusLink/Public realm_spec_draw_test.cpp
#include "DaedalusRealmSpec.h"

#include <cstdio>
#include <fstream>
#include <sstream>
#include <string>

using namespace daedalus::realm;

static int Passed = 0, Total = 0;
static void Check(const char* What, bool Ok, const std::string& Detail = "")
{
    ++Total;
    if (Ok) ++Passed;
    std::printf("%s %s%s%s\n", Ok ? "PASS" : "FAIL", What, Detail.empty() ? "" : "  ", Detail.c_str());
}

static std::string ReadFile(const std::string& P)
{
    std::ifstream In(P, std::ios::binary);
    std::ostringstream S;
    S << In.rdbuf();
    return S.str();
}

static std::string ReplaceLine(const std::string& T, const std::string& Prefix, const std::string& With)
{
    const size_t At = T.find("\n" + Prefix);
    if (At == std::string::npos) return T;
    const size_t End = T.find('\n', At + 1);
    return T.substr(0, At + 1) + With + T.substr(End);
}

static bool Refuses(const std::string& Text, const std::string& Want, std::string& Got)
{
    Spec S;
    Got.clear();
    return !S.Parse(Text, Got) && Got.find(Want) != std::string::npos;
}

int main(int Argc, char** Argv)
{
    const std::string Path = Argc > 1 ? Argv[1] : "../DaedalusLink/Content/Realm/realm-7.drr";
    const std::string Text = ReadFile(Path);
    std::string Err;

    // ---- the parser accepts the shipped realm
    Spec S;
    Check("the shipped realm parses", S.Parse(Text, Err), Err);
    Check("it has maps, items and monsters", S.Maps.size() == 7 && !S.Items.empty() && !S.Monsters.empty());
    Check("names resolve to indexes", S.MapIndex("FIELD") == 0 && S.ItemIndex("HERB") >= 0 && S.ItemIndex("NOPE") == -1);
    Check("zone 0 is read", S.Zone('0') != nullptr && !S.Zone('0')->Entries.empty());

    // ---- CRLF files read the same
    std::string Crlf;
    for (char C : Text) { if (C == '\n') Crlf += '\r'; Crlf += C; }
    Spec S2;
    Check("CRLF line endings parse the same", S2.Parse(Crlf, Err) && S2.Maps.size() == S.Maps.size()
        && S2.Items.size() == S.Items.size() && S2.Monsters.size() == S.Monsters.size(), Err);

    // ---- refusals, each with a reason
    std::string Got;
    Check("empty text is refused", Refuses("", "not a realm spec", Got), Got);
    Check("a wrong header is refused", Refuses("DRR 2\n" + Text.substr(Text.find('\n') + 1), "not a realm spec", Got), Got);
    Check("an unknown keyword is refused", Refuses(Text + "\nfrobnicate 1 2\n", "unknown 'frobnicate'", Got), Got);
    Check("a short item line is refused", Refuses(ReplaceLine(Text, "item HERB", "item HERB USE"), "too few fields", Got), Got);
    Check("a zone naming an unknown monster is refused",
        Refuses(ReplaceLine(Text, "zone 0", "zone 0 22 NO_SUCH_BEAST:50:1:3"), "unknown monster", Got), Got);
    Check("a bad zone entry is refused", Refuses(ReplaceLine(Text, "zone 0", "zone 0 22 BLIGHT_SLIME"), "bad zone entry", Got), Got);
    Check("a realm with no maps, items or monsters is refused with a reason", Refuses("DRR 1\nseed 1\nname X\n", "", Got) && !Got.empty(), Got);
    Spec S3;
    Check("a failed parse leaves no half-read realm", !S3.Parse("DRR 1\nfrobnicate\n", Err) && S3.Maps.empty() && S3.Items.empty());

    // ---- draw primitives
    bool RoundTrip = true;
    const char* Chars = TileChars();
    for (int i = 0; Chars[i]; ++i) { Tile T; RoundTrip &= TileFromChar(Chars[i], T) && static_cast<int>(T) == i; }
    Tile Dummy;
    Check("every tile char maps to its tile", RoundTrip && static_cast<int>(std::string(Chars).size()) == static_cast<int>(Tile::Count));
    Check("an unknown tile char is refused", !TileFromChar('?', Dummy));
    Check("water and walls block, grass and doors do not",
        !Walkable(Tile::Water) && !Walkable(Tile::Wall) && Walkable(Tile::Grass) && Walkable(Tile::Door));
    Check("shade halves and clamps", Shade(0x804020, 1, 2) == 0x402010 && Shade(0xC0C0C0, 2, 1) == 0xFFFFFF);
    Rng A(42), B(42), Z(0);
    Check("the rng repeats per seed", A.Next() == B.Next() && Z.Next() != 0);
    Rng R(7);
    bool InRange = true;
    for (int i = 0; i < 1000; ++i) { const int V = R.Range(3, 9); InRange &= V >= 3 && V <= 9; }
    Check("range stays inside its bounds", InRange && R.Range(5, 5) == 5 && R.Range(9, 2) == 9);
    const auto W = Wrap("THE QUICK BROWN FOX JUMPS\nOVER", 10);
    bool Fits = true;
    for (const auto& L : W) Fits &= L.size() <= 10;
    Check("wrap keeps every line inside the width", Fits && W.size() == 4 && W.back() == "OVER", std::to_string(W.size()));
    Check("a long word is cut at the width", Wrap("ABCDEFGHIJKLMNO", 6).size() == 3);
    Frame F(8, 4);
    F.Set(-1, 0, 1); F.Set(8, 0, 1); F.Set(0, 4, 1);
    bool Untouched = true;
    for (uint32_t P : F.Px) Untouched &= P == Pal::Black;
    Check("off-frame writes are ignored", Untouched && F.Get(-1, -1) == 0);
    F.Rect(6, 2, 10, 10, 0x123456);
    Check("rects clip to the frame", F.Get(7, 3) == 0x123456 && F.Get(5, 3) == Pal::Black);

    std::printf("%d/%d realm spec + draw checks\n", Passed, Total);
    return Passed == Total ? 0 : 1;
}
