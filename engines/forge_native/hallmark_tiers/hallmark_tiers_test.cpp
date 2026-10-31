// SPDX-License-Identifier: MIT
//
// Standalone test for DaedalusHallmarkTiersCore.h. Pins the input numbering to the real landed headers (Prism
// Satchel seals, Fair Par tiers, Quench Window outcomes), replays hallmark_tiers_golden.txt (every input, valid and
// not), and stamps hallmarks straight from a real Satchel record and a real Fair Par row.
// Build: g++ -std=c++17 -Wall -Wextra -Werror hallmark_tiers_test.cpp -o t && ./t hallmark_tiers_golden.txt
#include "DaedalusHallmarkTiersCore.h"

#include "../../unreal/DaedalusLink/Source/DaedalusLink/Public/DaedalusPrismFairParCore.h"
#include "../../unreal/DaedalusLink/Source/DaedalusLink/Public/DaedalusPrismSatchelCore.h"
#include "../quench_window/DaedalusQuenchWindowCore.h"

#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <sstream>
#include <string>

namespace hm = daedalus::prism::hallmark;
namespace ps = daedalus::prism_satchel;
namespace pp = daedalus::prismpar;
namespace qw = daedalus::prism::quench;

// The inputs are the landed systems' own numbers.
static_assert(hm::kSeals == 7 && ps::SealNone == 0 && ps::SealHeartglass == hm::kSealHeartglass, "Satchel seals");
static_assert(static_cast<int>(pp::Tier::None) == 0 && static_cast<int>(pp::Tier::Bronze) == 1 &&
                  static_cast<int>(pp::Tier::Silver) == 2 && static_cast<int>(pp::Tier::Gold) == hm::kParGold,
              "Fair Par tiers");
static_assert(static_cast<int>(qw::Outcome::Soft) == hm::kQuenchSoft &&
                  static_cast<int>(qw::Outcome::Tempered) == hm::kQuenchTempered &&
                  static_cast<int>(qw::Outcome::Perfect) == hm::kQuenchPerfect &&
                  static_cast<int>(qw::Outcome::Cracked) == hm::kQuenchCracked,
              "Quench outcomes");

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

static void Golden(const char* path) {
    std::ifstream f(path);
    Check(f.good(), std::string("open golden file ") + path);
    std::string line;
    int rows = 0;
    int ok_rows = 0;
    int problems = 0;
    int line_no = 0;
    while (std::getline(f, line)) {
        ++line_no;
        if (!line.empty() && line.back() == '\r') {
            line.pop_back();
        }
        if (line.empty() || line[0] == '#') {
            continue;
        }
        std::istringstream in(line);
        std::string tag;
        std::string status;
        int s = 0;
        int p = 0;
        int q = 0;
        in >> tag >> s >> p >> q >> status;
        std::string tier;
        std::string finish;
        if (status == "OK") {
            in >> tier >> finish;
        }
        std::string extra;
        bool ok = tag == "M" && !in.fail() && !(in >> extra);
        hm::Hallmark h;
        h.finish = 77;
        const hm::Status st = hm::Stamp(s, p, q, &h);
        ok = ok && status == hm::StatusName(st);
        if (st == hm::Status::Ok) {
            ok = ok && tier == hm::TierName(h.tier) && finish == hm::FinishName(h.finish);
            ok = ok && finish == ps::Seals[static_cast<std::size_t>(h.finish)];
            ++ok_rows;
        } else {
            ok = ok && h.finish == 77 && h.tier == hm::Tier::None;  // refusal leaves out unchanged
        }
        if (!ok) {
            ++problems;
            if (problems <= 20) {
                std::printf("FAIL: line %d: %s\n", line_no, line.c_str());
            }
        }
        ++rows;
    }
    Check(rows == 9 * 6 * 6 && ok_rows == 7 * 4 * 4, "golden covers every input");
    Check(problems == 0, "golden fixture replays with no problems");
    std::printf("golden: %d rows (%d stamped), %d problems\n", rows, ok_rows, problems);
}

// End to end with the real systems: a Satchel record gives the seal, a Fair Par row gives the tier.
static void Landed() {
    ps::Satchel bag;
    const ps::Payout& pay = ps::Payouts[0];
    const ps::RecordResult r = bag.Record(pay.Game, "hard", 100000, true, true);
    Check(r.Ok && r.Seal == ps::SealHeartglass, "a perfect hard win seals heartglass");
    const int seal = bag.SealsByGame[pay.Game];
    pp::Row row;
    row.Bronze = 10;
    row.Silver = 20;
    row.Gold = 30;
    const int gold = static_cast<int>(pp::TierOf(row, true, 35));
    const int silver = static_cast<int>(pp::TierOf(row, true, 25));
    hm::Hallmark h;
    Check(hm::Stamp(seal, gold, static_cast<int>(qw::Outcome::Perfect), &h) == hm::Status::Ok && h.tier == hm::Tier::Prism,
          "heartglass seal + gold par + perfect quench = PRISM");
    Check(hm::Stamp(seal, silver, static_cast<int>(qw::Outcome::Perfect), &h) == hm::Status::Ok && h.tier == hm::Tier::Silver,
          "silver par = SILVER");
    Check(hm::Stamp(seal, gold, static_cast<int>(qw::Outcome::Soft), &h) == hm::Status::Ok && h.tier == hm::Tier::Bronze,
          "a soft quench caps at BRONZE");
    Check(hm::Stamp(seal, static_cast<int>(pp::TierOf(row, false, 99)), static_cast<int>(qw::Outcome::Tempered), &h) ==
                  hm::Status::Ok && h.tier == hm::Tier::Plain,
          "a lost run still stamps PLAIN");
    Check(hm::Stamp(0, 0, 0, nullptr) == hm::Status::NullPointer, "null out");
    Check(std::strcmp(hm::TierName(static_cast<hm::Tier>(9)), "UNKNOWN") == 0 &&
              std::strcmp(hm::StatusName(static_cast<hm::Status>(9)), "UNKNOWN") == 0 &&
              std::strcmp(hm::FinishName(7), "unknown") == 0,
          "unknown names");
    for (int i = 0; i < hm::kSeals; ++i) {
        Check(std::strcmp(hm::kSealNames[i], ps::Seals[static_cast<std::size_t>(i)]) == 0, "seal name " + std::to_string(i));
    }
}

int main(int argc, char** argv) {
    Golden(argc > 1 ? argv[1] : "hallmark_tiers_golden.txt");
    Landed();
    std::printf("%s: %d checks, %d failures\n", g_failures == 0 ? "PASS" : "FAIL", g_checks, g_failures);
    return g_failures == 0 ? EXIT_SUCCESS : EXIT_FAILURE;
}
