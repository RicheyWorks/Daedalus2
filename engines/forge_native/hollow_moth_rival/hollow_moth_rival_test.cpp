// SPDX-License-Identifier: MIT
// Hollow Moth rival core test: replays hollow_moth_rival_golden.txt (from hollow_moth_rival_ref.py) plus properties.
#include "DaedalusHollowMothRivalCore.h"
#include <cstdio>
#include <cstring>
#include <fstream>
#include <sstream>
#include <string>

using namespace Daedalus::HollowMothRival;

static int g_fail = 0;
#define CHECK(c) do { if (!(c)) { ++g_fail; std::fprintf(stderr, "FAIL %s:%d %s\n", __FILE__, __LINE__, #c); } } while (0)

static bool Same(const State& a, const State& b) {
    return a.Round == b.Round && a.Tries == b.Tries && a.Beaten == b.Beaten && a.Game == b.Game && a.Mark == b.Mark &&
           a.NeedPerfect == b.NeedPerfect;
}

static bool ReadState(std::istringstream& in, State* s) {
    int beaten = 0, perfect = 0; long long mark = 0;
    in >> s->Round >> s->Tries >> beaten >> s->Game >> mark >> perfect;
    s->Beaten = beaten != 0; s->Mark = mark; s->NeedPerfect = perfect != 0;
    return static_cast<bool>(in);
}

static int Golden(const char* path) {
    std::ifstream f(path);
    if (!f) return -1;
    std::string line; State st; long long seed = 0, mask = 0; int rows = 0;
    while (std::getline(f, line)) {
        if (line.empty() || line[0] == '#') continue;
        std::istringstream in(line); std::string tag, want; in >> tag;
        if (tag == "N") { in >> seed >> mask; st = State(); ++rows; continue; }
        State before = st, expect;
        Status s;
        if (tag == "B") {
            in >> want;
            s = Begin(&st, seed, mask);
        } else if (tag == "X") {
            int g, d, won, pf; long long sc; in >> g >> d >> sc >> won >> pf >> want;
            s = Attempt(&st, g, d, sc, won != 0, pf != 0);
        } else { ++g_fail; std::fprintf(stderr, "bad golden line: %s\n", line.c_str()); continue; }
        CHECK(ReadState(in, &expect));
        CHECK(want == StatusName(s));
        CHECK(Same(st, expect));
        if (s != Status::Ok && s != Status::Beaten && s != Status::FellShort && s != Status::FlewOff)
            CHECK(Same(st, before));
        if (!Same(st, expect)) std::fprintf(stderr, "  at: %s\n", line.c_str());
        ++rows;
    }
    return rows;
}

static void Properties() {
    namespace sat = ::daedalus::prism_satchel;
    // Unlock follows the Satchel count: 2 Heartglass is locked, 3 opens.
    CHECK(!Unlocked(2) && Unlocked(3));
    sat::Satchel bag; CHECK(!Unlocked(bag.Heartglass()));
    State st;
    CHECK(Begin(&st, 7, 0b11) == Status::Locked && Same(st, State()));
    CHECK(Begin(&st, 7, -1) == Status::BadMask && Begin(&st, 7, int64_t{1} << kGames) == Status::BadMask);
    CHECK(Begin(nullptr, 7, 0b111) == Status::NullPointer);
    CHECK(Attempt(&st, 0, kHard, 999, true, true) == Status::NoChallenge);
    // A drawn challenge avoids Heartglass cabinets and its mark sits in [par, par + max(1, par/10)].
    for (int64_t seed = 0; seed < 200; ++seed) {
        State s; const int64_t mask = 0b10000000111 | (seed % 3 == 0 ? 0b1000 : 0);
        CHECK(Begin(&s, seed, mask) == Status::Ok);
        CHECK(s.Game >= 0 && !(mask >> s.Game & 1) && s.Tries == kTries && s.Round == 1);
        const sat::Payout& p = sat::Payouts[static_cast<size_t>(s.Game)];
        const int base = p.HeartPar < 0 ? p.UmbraPar : p.HeartPar;
        CHECK(s.Mark >= base && s.Mark <= base + (base / 10 > 1 ? base / 10 : 1));
        CHECK(s.NeedPerfect == (p.HeartPar < 0));
        CHECK(std::strcmp(ChallengeGame(s), p.Game) == 0);
        // An open challenge is not redrawn.
        const State open = s; CHECK(Begin(&s, seed + 1, mask) == Status::Ok && Same(s, open));
        // A non-hard win at the mark never beats the moth; three misses and it flies off.
        CHECK(Attempt(&s, s.Game, 1, s.Mark, true, true) == Status::FellShort);
        CHECK(Attempt(&s, s.Game, kHard, s.Mark - 1, true, true) == Status::FellShort);
        const int g = s.Game;
        CHECK(Attempt(&s, g, kHard, s.Mark, false, true) == Status::FlewOff && s.Game == -1 && !MothFreed(s));
        CHECK(Begin(&s, seed, mask) == Status::Ok && s.Round == 2 && s.Tries == kTries);
        CHECK(Attempt(&s, s.Game, kHard, s.Mark, true, true) == Status::Beaten && MothFreed(s));
        const State done = s;
        CHECK(Begin(&s, seed, mask) == Status::AlreadyBeaten && Same(s, done));
        CHECK(Attempt(&s, done.Game, kHard, 1 << 30, true, true) == Status::AlreadyBeaten && Same(s, done));
    }
    // With every cabinet sealed the moth may pick any of them; same seed draws the same challenge.
    State a, b; const int64_t full = (int64_t{1} << kGames) - 1;
    CHECK(Begin(&a, 42, full) == Status::Ok && Begin(&b, 42, full) == Status::Ok && Same(a, b));
    // Perfect-par cabinet: a hard win without a perfect run is not enough.
    for (int64_t seed = 0; seed < 400; ++seed) {
        State s; if (Begin(&s, seed, full ^ 0b100) != Status::Ok) { CHECK(false); break; }
        CHECK(s.Game == 2 && s.NeedPerfect);
        CHECK(Attempt(&s, 2, kHard, s.Mark + 50, true, false) == Status::FellShort);
        CHECK(Attempt(&s, 2, kHard, s.Mark, true, true) == Status::Beaten);
        break;
    }
    // Round ceiling.
    State r; r.Round = kMaxRound; CHECK(Begin(&r, 1, 0b111) == Status::RoundLimit && r.Round == kMaxRound);
}

int main(int argc, char** argv) {
    int rows = Golden(argc > 1 ? argv[1] : "hollow_moth_rival/hollow_moth_rival_golden.txt");
    if (rows < 0) rows = Golden("hollow_moth_rival_golden.txt");
    if (rows < 100) { std::fprintf(stderr, "golden rows %d too few\n", rows); return 1; }
    Properties();
    std::printf("hollow_moth_rival: %d golden rows, %s\n", rows, g_fail ? "FAIL" : "all pass");
    return g_fail ? 1 : 0;
}
