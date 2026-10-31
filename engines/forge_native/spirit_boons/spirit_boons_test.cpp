// SPDX-License-Identifier: MIT
// Spirit Boons core test: replays spirit_boons_golden.txt (from spirit_boons_ref.py) plus property checks.
#include "DaedalusSpiritBoonsCore.h"
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <sstream>
#include <string>

using namespace Daedalus::SpiritBoons;

static int g_fail = 0;
#define CHECK(c) do { if (!(c)) { ++g_fail; std::fprintf(stderr, "FAIL %s:%d %s\n", __FILE__, __LINE__, #c); } } while (0)

static std::string Counts(const Tally& t) {
    std::string s;
    for (int i = 0; i < kSpirits; ++i) { if (i) s += ' '; s += std::to_string(t.Count[i]); }
    return s;
}

static int Golden(const char* path) {
    std::ifstream f(path);
    if (!f) { std::fprintf(stderr, "cannot open %s\n", path); return -1; }
    std::string line; Tally t; int rows = 0;
    while (std::getline(f, line)) {
        if (line.empty() || line[0] == '#') continue;
        std::istringstream in(line); std::string tag; in >> tag;
        if (tag == "T") { for (int i = 0; i < kSpirits; ++i) in >> t.Count[i]; ++rows; continue; }
        if (tag == "A") {
            int sp; long long cnt; std::string st; in >> sp >> cnt >> st;
            std::string rest; std::getline(in, rest); if (!rest.empty() && rest[0] == ' ') rest.erase(0, 1);
            const Tally before = t;
            const Status s = Add(&t, sp, static_cast<int32_t>(cnt));
            CHECK(st == StatusName(s));
            CHECK(rest == Counts(t));
            if (s != Status::Ok) CHECK(std::memcmp(&before, &t, sizeof t) == 0);
            ++rows; continue;
        }
        if (tag == "Q") {
            std::string g, st; int moth, n; in >> g >> moth >> st >> n;
            BoonList b; b.Count = 99;
            const Status s = BoonsFor(t, g == "-" ? "" : g.c_str(), moth != 0, &b);
            CHECK(st == StatusName(s));
            if (s != Status::Ok) { CHECK(b.Count == 99); ++rows; continue; }
            CHECK(b.Count == n);
            for (int i = 0; i < n && i < b.Count; ++i) {
                int sp, d; std::string key; in >> sp >> key >> d;
                CHECK(b.Items[i].Spirit == sp); CHECK(key == b.Items[i].Key); CHECK(b.Items[i].Delta == d);
            }
            ++rows; continue;
        }
        ++g_fail; std::fprintf(stderr, "bad golden line: %s\n", line.c_str());
    }
    return rows;
}

static void Properties() {
    // Every boon targets a Satchel game, never its own source cabinets, and has a non-zero delta.
    for (int s = 0; s < kSpirits; ++s) {
        const Boon& b = BoonOf(s);
        CHECK(KnownGame(b.Game));
        CHECK(std::strcmp(b.Game, "wardens_accord") != 0 && std::strcmp(b.Game, "shardring") != 0);
        CHECK(b.DeltaPerLevel != 0);
        for (int o = 0; o < s; ++o) CHECK(std::strcmp(BoonOf(o).Game, b.Game) != 0);  // one boon per cabinet
    }
    CHECK(std::strcmp(BoonOf(0).Game, "glowmoss") == 0 && BoonOf(0).DeltaPerLevel == 1);    // IDEAS: Cinder Wisp
    CHECK(std::strcmp(BoonOf(1).Game, "spiritkite") == 0 && BoonOf(1).DeltaPerLevel == 2);  // IDEAS: Mere Sprite +2
    CHECK(std::strcmp(SpiritName(kHollowMoth), "Hollow Moth") == 0);
    CHECK(SpiritName(-1) == nullptr && SpiritName(kSpirits) == nullptr && GameId(kGames) == nullptr);
    // Hollow Moth stays dormant until the rival is beaten.
    Tally t; CHECK(Add(&t, kHollowMoth, 9) == Status::Ok);
    BoonList b;
    CHECK(BoonsFor(t, "shardfall", false, &b) == Status::Ok && b.Count == 0);
    CHECK(BoonsFor(t, "shardfall", true, &b) == Status::Ok && b.Count == 1 && b.Items[0].Delta == -2);
    // Shardring hues map to the first five spirits only.
    Tally h; CHECK(AddShardringHue(&h, 4, 1) == Status::Ok && h.Count[kHollowMoth] == 1);
    CHECK(AddShardringHue(&h, 5, 1) == Status::BadSpirit && h.Count[5] == 0);
    // Null pointers refuse.
    CHECK(Add(nullptr, 0, 1) == Status::NullPointer);
    CHECK(BoonsFor(t, "glowmoss", true, nullptr) == Status::NullPointer);
    CHECK(BoonsFor(t, nullptr, true, &b) == Status::UnknownGame);
    // Overflow at the ceiling, no wraparound.
    Tally m; CHECK(Add(&m, 0, kMaxCount) == Status::Ok && Add(&m, 0, 1) == Status::Overflow && m.Count[0] == kMaxCount);
}

int main(int argc, char** argv) {
    const char* path = argc > 1 ? argv[1] : "spirit_boons/spirit_boons_golden.txt";
    int rows = Golden(path);
    if (rows < 0) { std::ifstream probe("spirit_boons_golden.txt"); if (probe) rows = Golden("spirit_boons_golden.txt"); }
    if (rows < 100) { std::fprintf(stderr, "golden rows %d too few\n", rows); return 1; }
    Properties();
    std::printf("spirit_boons: %d golden rows, %s\n", rows, g_fail ? "FAIL" : "all pass");
    return g_fail ? 1 : 0;
}
