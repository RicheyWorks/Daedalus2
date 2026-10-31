// SPDX-License-Identifier: MIT
//
// Standalone test for DaedalusSalvageReforgeCore.h. Replays salvage_reforge_golden.txt (written by the Python rules
// reference salvage_reforge_ref.py) op by op, then proves the conservation property: over a grid of ledgers every
// single op keeps or lowers ledger value, and an exhaustive search of every ledger reachable from several starts
// (any sequence of Smelt, Salvage and Reforge) never finds one worth more than the start.
// Build: g++ -std=c++17 -Wall -Wextra -Werror salvage_reforge_test.cpp -o t && ./t salvage_reforge_golden.txt
#include "DaedalusSalvageReforgeCore.h"

#include <array>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <deque>
#include <fstream>
#include <set>
#include <sstream>
#include <string>

namespace rf = daedalus::prism::reforge;
namespace sm = daedalus::prism::smelter;

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

constexpr std::int64_t CompileTimeLoop() {
    rf::ForgeLedger l{};
    l.inv.count[5] = 4;  // four glowsteel, value 16
    rf::Salvage(&l, 5, 4);
    rf::Reforge(&l, 5, 3);
    return rf::LedgerValue(l);
}
static_assert(CompileTimeLoop() == 12, "salvage 4 glowsteel (12 scrap), reforge 3 (12 scrap): value 16 -> 12");
static_assert(rf::Salvage(nullptr, 5, 1) == rf::Status::NullPointer, "null refused");

static bool ReadLedger(std::istringstream& in, rf::ForgeLedger* l) {
    for (int i = 0; i < sm::kMaterials; ++i) {
        long long v = 0;
        if (!(in >> v)) {
            return false;
        }
        l->inv.count[i] = static_cast<std::int64_t>(v);
    }
    long long s = 0;
    if (!(in >> s)) {
        return false;
    }
    l->scrap = static_cast<std::int64_t>(s);
    return true;
}

static bool Same(const rf::ForgeLedger& a, const rf::ForgeLedger& b) {
    for (int i = 0; i < sm::kMaterials; ++i) {
        if (a.inv.count[i] != b.inv.count[i]) {
            return false;
        }
    }
    return a.scrap == b.scrap;
}

static rf::Status Apply(rf::ForgeLedger* l, const std::string& op, int arg, std::int64_t count, bool* known) {
    *known = true;
    if (op == "smelt") {
        return rf::Smelt(l, arg, count);
    }
    if (op == "salvage") {
        return rf::Salvage(l, arg, count);
    }
    if (op == "reforge") {
        return rf::Reforge(l, arg, count);
    }
    *known = false;
    return rf::Status::BadLedger;
}

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
    int scripts = 0;
    int ops = 0;
    int ok_ops = 0;
    bool in_script = false;
    bool saw_k = false;
    bool saw_y = false;
    bool saw_z = false;
    int ops_in_script = 0;
    long long start_value = -1;
    rf::ForgeLedger cur{};
    std::string name;
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
        std::string extra;
        in >> tag;
        const std::string where = "line " + std::to_string(line_no) + ": " + line.substr(0, 120);
        if (tag == "K") {
            long long ms = 0;
            long long mo = 0;
            in >> ms >> mo;
            expect(!saw_k && ms == rf::kMaxScrap && mo == rf::kMaxOps && !(in >> extra), "K " + where);
            saw_k = true;
        } else if (tag == "Y" || tag == "Z") {
            bool same = true;
            for (int i = 0; i < sm::kMaterials; ++i) {
                long long v = -1;
                in >> v;
                same = same && v == (tag == "Y" ? rf::ScrapPerUnit(i) : rf::CostPerUnit(i));
            }
            expect(same && !in.fail() && !(in >> extra), tag + " table " + where);
            (tag == "Y" ? saw_y : saw_z) = true;
        } else if (tag == "P") {
            expect(!in_script, "P inside a script " + where);
            in >> name;
            const bool parsed = ReadLedger(in, &cur) && (in >> start_value) && !(in >> extra);
            expect(parsed, "malformed " + where);
            expect(!rf::ValidLedger(cur) ? start_value == -1 : start_value == rf::LedgerValue(cur), "start value " + where);
            in_script = true;
            ops_in_script = 0;
            ++scripts;
        } else if (tag == "O") {
            expect(in_script, "O outside a script " + where);
            std::string op;
            int arg = 0;
            long long count = 0;
            std::string status;
            rf::ForgeLedger want{};
            long long want_value = 0;
            const bool parsed = (in >> op >> arg >> count >> status) && ReadLedger(in, &want) && (in >> want_value) &&
                                !(in >> extra);
            expect(parsed, "malformed " + where);
            if (!parsed) {
                continue;
            }
            const rf::ForgeLedger before = cur;
            bool known = false;
            const rf::Status st = Apply(&cur, op, arg, count, &known);
            expect(known, "unknown op " + where);
            expect(status == rf::StatusName(st), "status " + where + " got " + rf::StatusName(st));
            expect(Same(cur, want), "ledger " + where);
            if (st != rf::Status::Ok) {
                expect(Same(cur, before), "refusal changed the ledger " + where);
            } else {
                ++ok_ops;
            }
            if (rf::ValidLedger(cur)) {
                expect(rf::LedgerValue(cur) == want_value, "value " + where);
                if (start_value >= 0) {
                    expect(want_value <= start_value, "value rose above the script start " + where);
                }
            }
            ++ops;
            ++ops_in_script;
        } else if (tag == "E") {
            std::string end_name;
            int n = 0;
            long long v0 = 0;
            long long ve = 0;
            in >> end_name >> n >> v0 >> ve;
            expect(in_script && end_name == name && n == ops_in_script && v0 == start_value && !in.fail() && !(in >> extra),
                   "E " + where);
            if (v0 >= 0 && rf::ValidLedger(cur)) {
                expect(ve == rf::LedgerValue(cur) && ve <= v0, "end value " + where);
            }
            in_script = false;
        } else {
            expect(false, "unknown row " + where);
        }
    }
    expect(saw_k && saw_y && saw_z && !in_script, "headers present and last script closed");
    expect(scripts > 400 && ops > 5000 && ok_ops > 1000, "coverage");
    Check(problems == 0, "golden fixture replays with no problems");
    std::printf("golden: %d scripts, %d ops (%d ok), %d problems\n", scripts, ops, ok_ops, problems);
}

// Every single op from a grid of ledgers: Smelt and Reforge keep value, Salvage strictly lowers it.
static void SingleOps() {
    int tried = 0;
    bool smelt_equal = true;
    bool reforge_equal = true;
    bool salvage_lower = true;
    for (int seed = 0; seed < 600; ++seed) {
        rf::ForgeLedger l{};
        for (int i = 0; i < sm::kMaterials; ++i) {
            l.inv.count[i] = static_cast<std::int64_t>((seed * 131 + i * 17) % 9);
        }
        l.scrap = static_cast<std::int64_t>((seed * 7) % 40);
        const std::int64_t v0 = rf::LedgerValue(l);
        for (int arg = 0; arg < sm::kMaterials; ++arg) {
            for (std::int64_t c = 1; c <= 3; ++c) {
                rf::ForgeLedger t = l;
                if (arg < sm::kRecipes && rf::Smelt(&t, arg, c) == rf::Status::Ok) {
                    smelt_equal = smelt_equal && rf::LedgerValue(t) == v0;
                }
                t = l;
                if (rf::Reforge(&t, arg, c) == rf::Status::Ok) {
                    reforge_equal = reforge_equal && rf::LedgerValue(t) == v0;
                }
                t = l;
                if (rf::Salvage(&t, arg, c) == rf::Status::Ok) {
                    salvage_lower = salvage_lower && rf::LedgerValue(t) < v0;
                }
                tried += 3;
            }
        }
    }
    Check(smelt_equal, "Smelt keeps ledger value");
    Check(reforge_equal, "Reforge keeps ledger value");
    Check(salvage_lower, "Salvage strictly lowers ledger value");
    std::printf("single ops: %d tried\n", tried);
}

// Exhaustive closure: every ledger reachable by any sequence of single-unit ops is worth at most the start.
using Key = std::array<std::int64_t, sm::kMaterials + 1>;

static Key KeyOf(const rf::ForgeLedger& l) {
    Key k{};
    for (int i = 0; i < sm::kMaterials; ++i) {
        k[static_cast<std::size_t>(i)] = l.inv.count[i];
    }
    k[sm::kMaterials] = l.scrap;
    return k;
}

static void Reachable() {
    rf::ForgeLedger starts[4]{};
    starts[0].inv.count[0] = 7;
    starts[0].inv.count[1] = 3;
    starts[0].inv.count[4] = 4;
    starts[1].inv.count[5] = 3;
    starts[1].inv.count[9] = 1;
    starts[2].scrap = 30;
    starts[2].inv.count[2] = 4;
    starts[2].inv.count[1] = 4;
    starts[3].inv.count[0] = 4;
    starts[3].inv.count[1] = 3;
    starts[3].inv.count[2] = 2;
    starts[3].inv.count[3] = 2;
    starts[3].inv.count[4] = 4;
    starts[3].scrap = 6;
    std::size_t total = 0;
    bool never_more = true;
    bool loop_gain = false;
    for (const rf::ForgeLedger& s : starts) {
        const std::int64_t v0 = rf::LedgerValue(s);
        std::set<Key> seen;
        std::deque<rf::ForgeLedger> todo;
        seen.insert(KeyOf(s));
        todo.push_back(s);
        while (!todo.empty() && seen.size() < 2000000) {
            const rf::ForgeLedger cur = todo.front();
            todo.pop_front();
            never_more = never_more && rf::LedgerValue(cur) <= v0;
            for (int arg = 0; arg < sm::kMaterials; ++arg) {
                for (int op = 0; op < 3; ++op) {
                    rf::ForgeLedger t = cur;
                    const rf::Status st = op == 0 ? rf::Smelt(&t, arg, 1) : op == 1 ? rf::Salvage(&t, arg, 1) : rf::Reforge(&t, arg, 1);
                    if (st != rf::Status::Ok) {
                        continue;
                    }
                    // A loop that returns to a seen inventory with more scrap would be a gain.
                    loop_gain = loop_gain || rf::LedgerValue(t) > rf::LedgerValue(cur);
                    if (seen.insert(KeyOf(t)).second) {
                        todo.push_back(t);
                    }
                }
            }
        }
        Check(todo.empty(), "reachable set fully explored");
        total += seen.size();
    }
    Check(never_more, "no reachable ledger is worth more than its start");
    Check(!loop_gain, "no single step gains value, so no loop can");
    std::printf("reachable: %zu ledgers explored from 4 starts\n", total);
}

static void Edges() {
    rf::ForgeLedger l{};
    l.inv.count[0] = 3;
    l.inv.count[1] = 1;
    l.scrap = 5;
    const rf::ForgeLedger keep = l;
    Check(rf::Salvage(&l, 0, 1) == rf::Status::NotAnIngot && Same(l, keep), "shards not salvageable");
    Check(rf::Reforge(&l, 4, 1) == rf::Status::NotAnIngot, "shards not reforgeable");
    Check(rf::Reforge(&l, 10, 1) == rf::Status::NotAnIngot, "material past table");
    Check(rf::Salvage(&l, 5, 1) == rf::Status::Short, "no ingot to salvage");
    Check(rf::Reforge(&l, 9, 1) == rf::Status::Short && Same(l, keep), "not enough scrap");
    Check(rf::Reforge(&l, 5, 0) == rf::Status::BadCount, "zero count");
    Check(rf::Reforge(&l, 5, rf::kMaxOps + 1) == rf::Status::BadCount, "count past max");
    Check(rf::Reforge(&l, 5, 1) == rf::Status::Ok && l.scrap == 1 && l.inv.count[5] == 1, "reforge glowsteel");
    Check(rf::Smelt(&l, 9, 1) == rf::Status::NotAnIngot, "smelt unknown recipe maps");
    rf::ForgeLedger bad = keep;
    bad.scrap = -1;
    Check(rf::Smelt(&bad, 0, 1) == rf::Status::BadLedger && bad.inv.count[0] == 3, "bad scrap");
    rf::ForgeLedger top{};
    top.inv.count[9] = 1;
    top.scrap = rf::kMaxScrap - 10;
    Check(rf::Salvage(&top, 9, 1) == rf::Status::Overflow && top.inv.count[9] == 1, "scrap ceiling");
    Check(rf::ScrapPerUnit(9) == 11 && rf::CostPerUnit(9) == 15, "heartglass: 11 scrap out, 15 in");
    Check(std::strcmp(rf::StatusName(static_cast<rf::Status>(99)), "UNKNOWN") == 0, "unknown status name");
}

int main(int argc, char** argv) {
    const char* path = argc > 1 ? argv[1] : "salvage_reforge_golden.txt";
    Golden(path);
    SingleOps();
    Reachable();
    Edges();
    std::printf("%s: %d checks, %d failures\n", g_failures == 0 ? "PASS" : "FAIL", g_checks, g_failures);
    return g_failures == 0 ? EXIT_SUCCESS : EXIT_FAILURE;
}
