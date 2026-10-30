// SPDX-License-Identifier: MIT
// DaedalusDesktopSaveText.h: the save line writer/reader the Prismheart cabinets share. Every reader path must refuse
// malformed or out-of-range text rather than throw (Unreal game targets build without exceptions).
#include "DesktopGames/DaedalusDesktopSaveText.h"
#include <iostream>
#include <string>
#include <vector>

using namespace daedalus::desktop;
namespace {
int Checks = 0, Failed = 0;
void Check(bool Ok, const std::string& What) {
    ++Checks;
    if(!Ok) {
        ++Failed;
        std::cerr << "FAIL " << What << '\n';
    }
}
}

int main() {
    const std::string Line = SaveWriter("demo")
        .Field("d", std::string("easy"))
        .Field("seed", std::uint32_t(4294967295u))
        .Field("score", 42)
        .Flag("over", true)
        .List("bag", {3, 0, 5})
        .List("history", {})
        .Text();
    Check(Line == "demo v1 d=easy seed=4294967295 score=42 over=1 bag=3,0,5 history=-", "writer lays out fields in order: " + Line);

    const SaveFields Fields(Line, "demo");
    Check(Fields.IsValid(), "header matches");
    Check(!SaveFields(Line, "other").IsValid() && !SaveFields("demo v2 d=easy", "demo").IsValid() && !SaveFields("", "demo").IsValid(), "foreign or versioned headers are refused");
    Check(Fields.Str("d") == "easy" && Fields.Str("missing").empty(), "Str reads a field and gives empty for a missing key");

    std::uint32_t Seed = 0;
    int Score = 0;
    long long Big = 0;
    bool Over = false;
    std::vector<int> Bag, History;
    Check(Fields.Seed("seed", Seed) && Seed == 4294967295u, "Seed accepts the full 32-bit range");
    Check(Fields.Int("score", 0, 100, Score) && Score == 42, "Int reads within range");
    Check(!Fields.Int("score", 0, 41, Score) && !Fields.Int("score", 43, 100, Score), "Int refuses out-of-range values");
    Check(!Fields.Int("d", 0, 100, Score) && !Fields.Int("missing", 0, 100, Score), "Int refuses text and missing keys");
    Check(Fields.Int("seed", 0LL, 5000000000LL, Big) && Big == 4294967295LL, "the long long overload reads beyond int");
    Check(Fields.Flag("over", Over) && Over, "Flag reads 1 as true");
    Check(Fields.IntList("bag", 0, 5, Bag) && Bag == std::vector<int>({3, 0, 5}), "IntList reads a comma list");
    Check(Fields.IntList("history", 0, 5, History) && History.empty(), "IntList reads '-' as the empty list");
    Check(!Fields.IntList("bag", 1, 5, Bag) && !Fields.IntList("missing", 0, 5, Bag), "IntList refuses out-of-range items and missing keys");

    const SaveFields Odd("demo v1 n=+7 m=-3 f=2 bad=1x huge=99999999999999999999 trail=1,,2 hex=0x10", "demo");
    int Value = 0;
    Check(Odd.Int("n", 0, 10, Value) && Value == 7 && Odd.Int("m", -5, 5, Value) && Value == -3, "signed integers parse");
    Check(!Odd.Flag("f", Over), "Flag refuses anything but 0 and 1");
    Check(!Odd.Int("bad", 0, 10, Value) && !Odd.Int("huge", 0LL, 1LL << 62, Big) && !Odd.Int("hex", 0, 100, Value), "trailing junk, overflow and hex are refused");
    Check(!Odd.IntList("trail", 0, 10, Bag), "an empty list item is refused");

    Check(SplitText("", ',').empty() && SplitText("a", ',').size() == 1 && SplitText("a,,b", ',').size() == 3, "SplitText keeps empty inner tokens");
    Check(JoinIntegers({}) == "-" && JoinIntegers({1}) == "1" && JoinIntegers({1, 2}) == "1,2", "JoinIntegers round-trips");

    EdgeLatch Edge;
    Check(Edge.Rose(true) && !Edge.Rose(true) && !Edge.Rose(false) && Edge.Rose(true), "EdgeLatch fires once per press");
    Check(SourceKey::IsConfirm(SourceKey::A) && SourceKey::IsConfirm(SourceKey::Space) && !SourceKey::IsConfirm(SourceKey::R) && SourceKey::IsRestart(SourceKey::R), "SourceKey groups confirm and restart keys");

    std::cout << "save text: " << (Checks - Failed) << "/" << Checks << " checks\n";
    return Failed == 0 ? 0 : 1;
}
