// SPDX-License-Identifier: MIT
//
// Standalone test for DaedalusCommissionBoardCore.h. Replays commission_board_golden.txt (written by
// commission_board_ref.py with CPython's random): every board, then every delivery and its full resulting state.
// Then refusal-safety and board-shape checks.
// Build: g++ -std=c++17 -Wall -Wextra -Werror commission_board_test.cpp -o t && ./t commission_board_golden.txt
#include "DaedalusCommissionBoardCore.h"

#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <sstream>
#include <string>

namespace cb = daedalus::prism::commission;
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

static bool SameState(const sm::ShardInventory& a, const cb::Board& x, const sm::ShardInventory& b, const cb::Board& y) {
    for (int i = 0; i < sm::kMaterials; ++i) {
        if (a.count[i] != b.count[i]) {
            return false;
        }
    }
    for (int i = 0; i < cb::kSlots; ++i) {
        if (x.done[i] != y.done[i] || x.slot[i].material != y.slot[i].material || x.slot[i].qty != y.slot[i].qty ||
            x.slot[i].marks != y.slot[i].marks) {
            return false;
        }
    }
    return x.marks == y.marks;
}

static void Golden(const char* path) {
    std::ifstream f(path);
    Check(f.good(), std::string("open golden file ") + path);
    int problems = 0;
    auto expect = [&problems](bool ok, const std::string& what) {
        if (!ok) {
            ++problems;
            if (problems <= 20) {
                std::printf("FAIL: %s\n", what.c_str());
            }
        }
    };
    std::string line;
    std::string date;
    int line_no = 0;
    int boards = 0;
    int bad_dates = 0;
    int deliveries = 0;
    int ok_deliveries = 0;
    int full_boards = 0;
    enum { kWantD, kWantB, kWantI, kInScript } state = kWantD;
    sm::ShardInventory inv{};
    cb::Board board{};
    while (std::getline(f, line)) {
        ++line_no;
        if (!line.empty() && line.back() == '\r') {
            line.pop_back();
        }
        if (line.empty() || line[0] == '#') {
            continue;
        }
        const std::string where = "line " + std::to_string(line_no);
        if (line.rfind("D ", 0) == 0) {
            expect(state == kWantD || state == kInScript, "D out of order " + where);
            const std::size_t sp = line.find(' ', 2);
            const long n = sp == std::string::npos ? -1 : std::strtol(line.substr(2, sp - 2).c_str(), nullptr, 10);
            const bool ok = n >= 0 && sp + 1 + static_cast<std::size_t>(n) == line.size();
            expect(ok, "D " + where);
            date = ok ? line.substr(sp + 1) : std::string();
            state = kWantB;
        } else if (line.rfind("B ", 0) == 0) {
            expect(state == kWantB, "B out of order " + where);
            cb::Board b{};
            b.marks = 42;
            const cb::Status st = cb::MakeBoard(date, &b);
            if (line == "B BAD_DATE") {
                expect(st == cb::Status::BadDate && b.marks == 42 && b.slot[0].qty == 0, "bad date '" + date + "' " + where);
                ++bad_dates;
                state = kWantD;
                continue;
            }
            std::istringstream in(line.substr(2));
            cb::Board want{};
            for (int i = 0; i < cb::kSlots; ++i) {
                in >> want.slot[i].material >> want.slot[i].qty >> want.slot[i].marks;
            }
            std::string extra;
            expect(!in.fail() && !(in >> extra), "malformed B " + where);
            want.marks = 42;
            expect(st == cb::Status::Ok && SameState(inv, b, inv, want), "board for '" + date + "' " + where);
            board = b;
            ++boards;
            state = kWantI;
        } else if (line.rfind("I ", 0) == 0) {
            expect(state == kWantI, "I out of order " + where);
            std::istringstream in(line.substr(2));
            for (int i = 0; i < sm::kMaterials; ++i) {
                in >> inv.count[i];
            }
            in >> board.marks;
            std::string extra;
            expect(!in.fail() && !(in >> extra), "malformed I " + where);
            state = kInScript;
        } else if (line.rfind("X ", 0) == 0) {
            expect(state == kInScript, "X out of order " + where);
            std::istringstream in(line.substr(2));
            int slot = 0;
            std::string name;
            in >> slot >> name;
            sm::ShardInventory want_inv{};
            cb::Board want = board;
            for (int i = 0; i < sm::kMaterials; ++i) {
                in >> want_inv.count[i];
            }
            int mask = 0;
            in >> want.marks >> mask;
            std::string extra;
            expect(!in.fail() && !(in >> extra) && mask >= 0 && mask < 8, "malformed X " + where);
            for (int i = 0; i < cb::kSlots; ++i) {
                want.done[i] = ((mask >> i) & 1) != 0;
            }
            const sm::ShardInventory before_inv = inv;
            const cb::Board before = board;
            const cb::Status st = cb::Deliver(&inv, &board, slot);
            expect(name == cb::StatusName(st), "status " + name + " vs " + cb::StatusName(st) + " " + where);
            expect(SameState(inv, board, want_inv, want), "state " + where);
            if (st != cb::Status::Ok) {
                expect(SameState(inv, board, before_inv, before), "refusal changed state " + where);
            } else {
                ++ok_deliveries;
                full_boards += mask == 7 ? 1 : 0;
            }
            ++deliveries;
        } else {
            expect(false, "unknown row " + where);
        }
    }
    expect(state == kWantD || state == kInScript, "file ends cleanly");
    expect(boards > 400 && bad_dates >= 10 && ok_deliveries > 100 && full_boards > 0, "coverage");
    Check(problems == 0, "golden fixture replays with no problems");
    std::printf("golden: %d boards, %d bad dates, %d deliveries (%d OK, %d boards filled), %d problems\n", boards,
                bad_dates, deliveries, ok_deliveries, full_boards, problems);
}

// Board shape over a run of real days: three different ingots, legal quantities, exact marks.
static void Shapes() {
    bool ok = true;
    int days = 0;
    for (int y = 2026; y <= 2027; ++y) {
        for (int m = 1; m <= 12; ++m) {
            for (int d = 1; d <= 31; ++d) {
                char buf[48];
                std::snprintf(buf, sizeof buf, "%04d-%02d-%02d", y, m, d);
                cb::Board b{};
                const cb::Status st = cb::MakeBoard(buf, &b);
                if (!cb::ValidDate(buf, 10)) {
                    ok = ok && st == cb::Status::BadDate;
                    continue;
                }
                ++days;
                ok = ok && st == cb::Status::Ok;
                for (int i = 0; i < cb::kSlots; ++i) {
                    const cb::Commission& c = b.slot[i];
                    ok = ok && c.material >= cb::kFirstIngot && c.material < sm::kMaterials;
                    ok = ok && c.qty >= 1 && c.qty <= (c.material == 9 ? 1 : cb::kMaxQty);
                    ok = ok && c.marks == c.qty * sm::kValue[c.material] + cb::kMarkBonus;
                    for (int j = 0; j < i; ++j) {
                        ok = ok && b.slot[j].material != c.material;
                    }
                }
            }
        }
    }
    Check(ok && days == 730, "730 days of boards have legal shape");
    std::printf("shapes: %d days checked\n", days);
}

static void Edges() {
    cb::Board b{};
    Check(cb::MakeBoard("2026-10-30", nullptr) == cb::Status::NullPointer, "null board");
    Check(cb::MakeBoard("2026-10-30", &b) == cb::Status::Ok, "today posts");
    sm::ShardInventory inv{};
    for (int i = 0; i < sm::kMaterials; ++i) {
        inv.count[i] = 5;
    }
    Check(cb::Deliver(nullptr, &b, 0) == cb::Status::NullPointer && cb::Deliver(&inv, nullptr, 0) == cb::Status::NullPointer, "null deliver");
    std::int64_t total = 0;
    for (int i = 0; i < cb::kSlots; ++i) {
        total += b.slot[i].marks;
        Check(cb::Deliver(&inv, &b, i) == cb::Status::Ok, "deliver slot " + std::to_string(i));
    }
    Check(b.marks == total + cb::kBoardBonus, "board bonus paid once on the third delivery");
    Check(cb::Deliver(&inv, &b, 1) == cb::Status::AlreadyDone, "no double delivery");
    cb::Board again{};
    again.marks = 9;
    cb::MakeBoard("2026-10-30", &again);
    Check(again.marks == 9 && again.slot[0].material == b.slot[0].material && !again.done[0], "repost keeps marks, clears progress");
    cb::Board bad = again;
    bad.slot[0].material = 2;
    Check(cb::Deliver(&inv, &bad, 0) == cb::Status::BadInventory, "non-ingot commission refused");
    Check(!cb::ValidDate(nullptr, 10) && !cb::ValidDate("0000-01-01", 10) && cb::ValidDate("9999-12-31", 10), "date range");
    Check(std::strcmp(cb::StatusName(static_cast<cb::Status>(99)), "UNKNOWN") == 0, "unknown status name");
}

int main(int argc, char** argv) {
    Golden(argc > 1 ? argv[1] : "commission_board_golden.txt");
    Shapes();
    Edges();
    std::printf("%s: %d checks, %d failures\n", g_failures == 0 ? "PASS" : "FAIL", g_checks, g_failures);
    return g_failures == 0 ? EXIT_SUCCESS : EXIT_FAILURE;
}
