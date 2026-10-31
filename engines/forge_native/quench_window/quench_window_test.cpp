// SPDX-License-Identifier: MIT
//
// Standalone test for DaedalusQuenchWindowCore.h. Replays quench_window_golden.txt (written by quench_window_ref.py
// with CPython's random) curve by curve and tick by tick, then checks curve invariants and grading edges.
// Build: g++ -std=c++17 -Wall -Wextra -Werror quench_window_test.cpp -o t && ./t quench_window_golden.txt
#include "DaedalusQuenchWindowCore.h"

#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <sstream>
#include <string>

namespace qw = daedalus::prism::quench;

static int g_checks = 0;
static int g_failures = 0;

static void Check(bool ok, const std::string& what) {
    ++g_checks;
    if (!ok) {
        ++g_failures;
        if (g_failures <= 20) {
            std::printf("FAIL: %s\n", what.c_str());
        }
    }
}

constexpr qw::QuenchCurve Fixed() {
    qw::QuenchCurve c{};
    for (int t = 0; t <= qw::kTicks; ++t) {
        c.heat[t] = 1000 - 70 * t;
    }
    c.lo = 560;
    c.hi = 650;
    return c;
}

constexpr qw::Outcome GradeAt(int tick) {
    qw::Outcome o = qw::Outcome::Soft;
    qw::Grade(Fixed(), tick, &o);
    return o;
}
// Heat 1000, 930, ..., 650 (t=5), 580 (t=6), 510 (t=7); band 560..650, middle 605.
static_assert(GradeAt(4) == qw::Outcome::Soft, "720 is above the band");
static_assert(GradeAt(5) == qw::Outcome::Tempered, "650 is the band top");
static_assert(GradeAt(6) == qw::Outcome::Tempered, "580 is 25 from the middle");
static_assert(GradeAt(7) == qw::Outcome::Cracked, "510 is below the band");
static_assert(qw::BestTick(Fixed()) == 6, "580 is closest to 605");

static void Golden(const char* path) {
    std::ifstream f(path);
    Check(f.good(), std::string("open golden file ") + path);
    std::string line;
    int problems = 0;
    auto expect = [&problems](bool ok, const std::string& what) {
        if (!ok) {
            ++problems;
            if (problems <= 20) {
                std::printf("FAIL: %s\n", what.c_str());
            }
        }
    };
    int curves = 0;
    int ticks = 0;
    int perfect_best = 0;
    bool saw_k = false;
    std::string seed;
    bool have_seed = false;
    qw::QuenchCurve cur{};
    bool have_curve = false;
    int line_no = 0;
    while (std::getline(f, line)) {
        ++line_no;
        if (!line.empty() && line.back() == '\r') {
            line.pop_back();
        }
        if (line.empty() || line[0] == '#') {
            continue;
        }
        const std::string where = "line " + std::to_string(line_no);
        if (line.rfind("K ", 0) == 0) {
            std::istringstream in(line.substr(2));
            int t = 0;
            int b = 0;
            int p = 0;
            std::string extra;
            in >> t >> b >> p;
            expect(!saw_k && t == qw::kTicks && b == qw::kBand && p == qw::kPerfect && !(in >> extra), "K " + where);
            saw_k = true;
        } else if (line.rfind("Q ", 0) == 0) {
            // "Q <len> <seed>": the seed may hold spaces, so it is taken by length.
            const std::size_t sp = line.find(' ', 2);
            const long n = sp == std::string::npos ? -1 : std::strtol(line.substr(2, sp - 2).c_str(), nullptr, 10);
            const bool ok = !have_seed && n >= 0 && sp + 1 + static_cast<std::size_t>(n) == line.size();
            expect(ok, "Q " + where);
            seed = ok ? line.substr(sp + 1) : std::string();
            have_seed = ok;
        } else if (line.rfind("H ", 0) == 0) {
            expect(have_seed && !have_curve, "H out of order " + where);
            std::istringstream in(line.substr(2));
            qw::QuenchCurve want{};
            for (int t = 0; t <= qw::kTicks; ++t) {
                in >> want.heat[t];
            }
            int best = -1;
            std::string extra;
            in >> want.lo >> want.hi >> best;
            expect(!in.fail() && !(in >> extra), "malformed H " + where);
            cur = qw::MakeCurve(seed);
            bool same = cur.lo == want.lo && cur.hi == want.hi;
            for (int t = 0; t <= qw::kTicks; ++t) {
                same = same && cur.heat[t] == want.heat[t];
            }
            expect(same, "curve " + where + " seed '" + seed + "'");
            expect(qw::BestTick(cur) == best, "best tick " + where);
            have_curve = true;
        } else if (line.rfind("G ", 0) == 0) {
            expect(have_curve, "G before H " + where);
            std::istringstream in(line.substr(2));
            for (int t = 0; t <= qw::kTicks; ++t) {
                std::string name;
                in >> name;
                qw::Outcome o = qw::Outcome::Soft;
                expect(qw::Grade(cur, t, &o) == qw::Status::Ok && name == qw::OutcomeName(o), "grade t=" + std::to_string(t) + " " + where);
                ++ticks;
            }
            std::string extra;
            expect(!(in >> extra), "trailing G " + where);
            qw::Outcome ob = qw::Outcome::Soft;
            qw::Grade(cur, qw::BestTick(cur), &ob);
            perfect_best += ob == qw::Outcome::Perfect ? 1 : 0;
            ++curves;
            have_seed = false;
            have_curve = false;
        } else {
            expect(false, "unknown row " + where);
        }
    }
    expect(saw_k && !have_seed && !have_curve, "header present and last curve closed");
    expect(curves > 600 && ticks == curves * (qw::kTicks + 1), "coverage");
    Check(problems == 0, "golden fixture replays with no problems");
    std::printf("golden: %d curves, %d graded ticks, best tick perfect on %d curves, %d problems\n", curves, ticks,
                perfect_best, problems);
}

// Invariants over many seeds: strictly cooling, within bounds, and at least one tick in the band.
static void Invariants() {
    bool ok = true;
    int in_band_min = 99;
    for (int k = 0; k < 5000; ++k) {
        const qw::QuenchCurve c = qw::MakeCurve("inv" + std::to_string(k));
        ok = ok && c.heat[0] >= qw::kHeat0Base && c.heat[0] < qw::kHeat0Base + qw::kHeat0Span;
        ok = ok && c.lo >= qw::kLoBase && c.lo < qw::kLoBase + qw::kLoSpan && c.hi == c.lo + qw::kBand;
        int in_band = 0;
        for (int t = 1; t <= qw::kTicks; ++t) {
            const int drop = c.heat[t - 1] - c.heat[t];
            ok = ok && drop >= qw::kCoolBase && drop < qw::kCoolBase + qw::kCoolSpan;
        }
        for (int t = 0; t <= qw::kTicks; ++t) {
            in_band += c.heat[t] >= c.lo && c.heat[t] <= c.hi ? 1 : 0;
        }
        ok = ok && c.heat[0] > c.hi && c.heat[qw::kTicks] < c.lo;
        in_band_min = in_band < in_band_min ? in_band : in_band_min;
    }
    Check(ok, "curves cool within bounds and cross the band");
    Check(in_band_min >= 1, "every curve has a tick inside the band");
    std::printf("invariants: 5000 curves, fewest in-band ticks %d\n", in_band_min);
}

static void Edges() {
    const qw::QuenchCurve c = Fixed();
    qw::Outcome o = qw::Outcome::Perfect;
    Check(qw::Grade(c, -1, &o) == qw::Status::BadTick && o == qw::Outcome::Perfect, "tick -1, out untouched");
    Check(qw::Grade(c, qw::kTicks + 1, &o) == qw::Status::BadTick, "tick past end");
    Check(qw::Grade(c, 0, nullptr) == qw::Status::NullPointer, "null out");
    qw::QuenchCurve p = c;
    p.heat[6] = 615;  // 10 above the middle 605
    Check(qw::Grade(p, 6, &o) == qw::Status::Ok && o == qw::Outcome::Perfect, "perfect at the edge");
    p.heat[6] = 616;
    Check(qw::Grade(p, 6, &o) == qw::Status::Ok && o == qw::Outcome::Tempered, "one past perfect");
    const qw::QuenchCurve a = qw::MakeCurve("same");
    const qw::QuenchCurve b = qw::MakeCurve("same");
    Check(std::memcmp(&a, &b, sizeof a) == 0, "same seed, same curve");
    Check(std::strcmp(qw::OutcomeName(static_cast<qw::Outcome>(9)), "UNKNOWN") == 0, "unknown outcome name");
}

int main(int argc, char** argv) {
    const char* path = argc > 1 ? argv[1] : "quench_window_golden.txt";
    Golden(path);
    Invariants();
    Edges();
    std::printf("%s: %d checks, %d failures\n", g_failures == 0 ? "PASS" : "FAIL", g_checks, g_failures);
    return g_failures == 0 ? EXIT_SUCCESS : EXIT_FAILURE;
}
