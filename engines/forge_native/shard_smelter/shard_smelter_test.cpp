// SPDX-License-Identifier: MIT
//
// Standalone test for DaedalusShardSmelterCore.h. Replays shard_smelter_golden.txt (written by the Python rules
// reference shard_smelter_ref.py) row for row, checks the recipe and value tables against it, and adds property,
// refusal and compile-time checks.
// Build: g++ -std=c++17 -Wall -Wextra -Werror shard_smelter_test.cpp -o t && ./t shard_smelter_golden.txt
#include "DaedalusShardSmelterCore.h"

#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <sstream>
#include <string>

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

constexpr std::int64_t CompileTimeSmelt() {
    sm::ShardInventory inv{};
    inv.count[0] = 6;
    inv.count[1] = 2;
    return sm::Smelt(&inv, 0, 2) == sm::Status::Ok ? inv.count[5] : -1;
}
static_assert(CompileTimeSmelt() == 2, "two glowsteel from 6 ember + 2 tide");
static_assert(sm::Smelt(nullptr, 0, 1) == sm::Status::NullPointer, "null refused");
static_assert(sm::StatusName(sm::Status::Overflow)[0] == 'O', "StatusName is constexpr");

static bool ReadInv(std::istringstream& in, sm::ShardInventory* inv) {
    for (int i = 0; i < sm::kMaterials; ++i) {
        long long v = 0;
        if (!(in >> v)) {
            return false;
        }
        inv->count[i] = static_cast<std::int64_t>(v);
    }
    return true;
}

static bool SameInv(const sm::ShardInventory& a, const sm::ShardInventory& b) {
    for (int i = 0; i < sm::kMaterials; ++i) {
        if (a.count[i] != b.count[i]) {
            return false;
        }
    }
    return true;
}

static void Golden(const char* path) {
    std::ifstream f(path);
    Check(f.good(), std::string("open golden file ") + path);
    std::string line;
    int rows = 0;
    int ok_rows = 0;
    int refused = 0;
    int recipes_seen = 0;
    bool saw_m = false;
    bool saw_c = false;
    bool saw_n = false;
    bool saw_v = false;
    int line_no = 0;
    int problems = 0;
    auto expect = [&problems](bool ok, const std::string& what) {
        if (!ok) {
            ++problems;
            if (problems <= 20) {
                std::printf("FAIL: %s\n", what.c_str());
            }
        }
    };
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
        if (tag == "M") {
            int m = 0;
            in >> m;
            expect(!saw_m && m == sm::kMaterials && !(in >> extra), "M " + where);
            saw_m = true;
        } else if (tag == "C") {
            long long mc = 0;
            long long mb = 0;
            in >> mc >> mb;
            expect(!saw_c && mc == sm::kMaxCount && mb == sm::kMaxBatch && !(in >> extra), "C " + where);
            saw_c = true;
        } else if (tag == "N") {
            bool same = true;
            for (int i = 0; i < sm::kMaterials; ++i) {
                std::string nm;
                in >> nm;
                same = same && nm == sm::kMaterialNames[i];
            }
            expect(!saw_n && same && !(in >> extra), "N " + where);
            saw_n = true;
        } else if (tag == "V") {
            bool same = true;
            for (int i = 0; i < sm::kMaterials; ++i) {
                long long v = -1;
                in >> v;
                same = same && v == sm::kValue[i];
            }
            expect(!saw_v && same && !in.fail() && !(in >> extra), "V " + where);
            saw_v = true;
        } else if (tag == "R") {
            int id = -1;
            std::string name;
            in >> id >> name;
            bool same = id == recipes_seen && id >= 0 && id < sm::kRecipes && name == sm::kRecipeTable[id].name;
            for (int i = 0; same && i < sm::kMaterials; ++i) {
                long long v = -1;
                in >> v;
                same = v == sm::kRecipeTable[id].in[i];
            }
            for (int i = 0; same && i < sm::kMaterials; ++i) {
                long long v = -1;
                in >> v;
                same = v == sm::kRecipeTable[id].out[i];
            }
            expect(same && !in.fail() && !(in >> extra), "R " + where);
            ++recipes_seen;
        } else if (tag == "S") {
            sm::ShardInventory before{};
            sm::ShardInventory want{};
            int recipe = 0;
            long long batches = 0;
            std::string status;
            long long want_max = 0;
            long long vb = 0;
            long long va = 0;
            const bool parsed = ReadInv(in, &before) && (in >> recipe >> batches >> status) && ReadInv(in, &want) &&
                                (in >> want_max >> vb >> va) && !(in >> extra);
            expect(parsed, "malformed " + where);
            if (!parsed) {
                continue;
            }
            sm::ShardInventory got = before;
            const sm::Status st = sm::Smelt(&got, recipe, batches);
            expect(status == sm::StatusName(st), "status " + where + " got " + sm::StatusName(st));
            expect(SameInv(got, want), "inventory " + where);
            expect(sm::MaxBatches(before, recipe) == want_max, "max_batches " + where);
            if (sm::ValidInventory(before)) {
                expect(sm::Value(before) == vb && sm::Value(got) == va, "value " + where);
            }
            if (st == sm::Status::Ok) {
                ++ok_rows;
            } else {
                ++refused;
            }
            ++rows;
        } else {
            expect(false, "unknown row " + where);
        }
    }
    expect(saw_m && saw_c && saw_n && saw_v && recipes_seen == sm::kRecipes, "headers and full recipe table");
    expect(rows > 2000 && ok_rows > 500 && refused > 500, "coverage");
    Check(problems == 0, "golden fixture replays with no problems");
    std::printf("golden: %d smelt rows (%d ok, %d refused), %d recipes, %d problems\n", rows, ok_rows, refused,
                recipes_seen, problems);
}

// Properties over a deterministic grid of inventories (no randomness needed).
static void Properties() {
    int conserved = 0;
    int untouched = 0;
    int boundary = 0;
    int total = 0;
    bool all_ok = true;
    for (int recipe = 0; recipe < sm::kRecipes; ++recipe) {
        for (int seed = 0; seed < 400; ++seed) {
            sm::ShardInventory inv{};
            for (int i = 0; i < sm::kMaterials; ++i) {
                inv.count[i] = static_cast<std::int64_t>((seed * 7919 + i * 104729 + recipe * 31) % 37);
            }
            if (seed % 50 == 0) {
                inv.count[seed % sm::kMaterials] = sm::kMaxCount - (seed % 3);
            }
            const std::int64_t mb = sm::MaxBatches(inv, recipe);
            for (std::int64_t b = 1; b <= 6; ++b) {
                sm::ShardInventory t = inv;
                const sm::Status st = sm::Smelt(&t, recipe, b);
                ++total;
                if (st == sm::Status::Ok) {
                    conserved += sm::Value(t) == sm::Value(inv) ? 1 : 0;
                    all_ok = all_ok && b <= mb;
                } else {
                    untouched += SameInv(t, inv) ? 1 : 0;
                    all_ok = all_ok && b > mb;
                }
                all_ok = all_ok && ((st == sm::Status::Ok) == (b <= mb));
            }
            if (mb >= 1 && mb < sm::kMaxBatch) {
                sm::ShardInventory t = inv;
                boundary += sm::Smelt(&t, recipe, mb) == sm::Status::Ok ? 1 : 0;
                t = inv;
                boundary += sm::Smelt(&t, recipe, mb + 1) != sm::Status::Ok ? 1 : 0;
                boundary -= 2;
            }
        }
    }
    Check(all_ok, "Smelt accepts exactly the batch counts up to MaxBatches");
    Check(boundary == 0, "MaxBatches is the exact boundary");
    std::printf("properties: %d smelts, %d value-conserving, %d refusals untouched\n", total, conserved, untouched);
    Check(conserved + untouched == total, "every Ok conserves value and every refusal leaves the inventory untouched");
}

static void Edges() {
    sm::ShardInventory inv{};
    inv.count[0] = 3;
    inv.count[1] = 1;
    const sm::ShardInventory keep = inv;
    Check(sm::Smelt(&inv, -1, 1) == sm::Status::UnknownRecipe && SameInv(inv, keep), "recipe -1");
    Check(sm::Smelt(&inv, sm::kRecipes, 1) == sm::Status::UnknownRecipe, "recipe past table");
    Check(sm::Smelt(&inv, 0, 0) == sm::Status::BadBatch, "zero batches");
    Check(sm::Smelt(&inv, 0, sm::kMaxBatch + 1) == sm::Status::BadBatch, "too many batches");
    Check(sm::Smelt(&inv, 0, 2) == sm::Status::Short && SameInv(inv, keep), "short refuses whole smelt");
    Check(sm::Smelt(&inv, 0, 1) == sm::Status::Ok && inv.count[5] == 1 && inv.count[0] == 0, "one glowsteel");
    sm::ShardInventory bad{};
    bad.count[9] = -1;
    Check(sm::Smelt(&bad, 0, 1) == sm::Status::BadInventory && bad.count[9] == -1, "negative count");
    Check(sm::MaxBatches(bad, 0) == -1, "MaxBatches bad inventory");
    Check(sm::MaxBatches(keep, 7) == -1, "MaxBatches bad recipe");
    sm::ShardInventory top{};
    top.count[0] = 3;
    top.count[1] = 1;
    top.count[5] = sm::kMaxCount;
    Check(sm::Smelt(&top, 0, 1) == sm::Status::Overflow && top.count[0] == 3, "overflow refuses");
    sm::ShardInventory heart{};
    for (int i = 5; i <= 8; ++i) {
        heart.count[i] = 2;
    }
    Check(sm::Smelt(&heart, 4, 2) == sm::Status::Ok && heart.count[9] == 2 && sm::Value(heart) == 30, "heartglass");
    Check(std::strcmp(sm::StatusName(static_cast<sm::Status>(77)), "UNKNOWN") == 0, "unknown status name");
}

int main(int argc, char** argv) {
    const char* path = argc > 1 ? argv[1] : "shard_smelter_golden.txt";
    Golden(path);
    Properties();
    Edges();
    std::printf("%s: %d checks, %d failures\n", g_failures == 0 ? "PASS" : "FAIL", g_checks, g_failures);
    return g_failures == 0 ? EXIT_SUCCESS : EXIT_FAILURE;
}
