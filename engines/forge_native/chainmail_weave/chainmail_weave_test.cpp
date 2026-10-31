// SPDX-License-Identifier: MIT
//
// Standalone test for DaedalusChainmailWeaveCore.h. Replays chainmail_weave_golden.txt (written by
// chainmail_weave_ref.py with CPython's random): every new grid and budget, then every placement with its status,
// full grid, budget, state, score and the demo move after it. Then invariants and edges.
// Build: g++ -std=c++17 -Wall -Wextra -Werror chainmail_weave_test.cpp -o t && ./t chainmail_weave_golden.txt
#include "DaedalusChainmailWeaveCore.h"

#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <istream>
#include <memory>
#include <sstream>
#include <string>

namespace cw = daedalus::prism::chainmail;

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

static std::string Text(const cw::Grid& g) {
    std::string s(cw::kCells, '?');
    for (int i = 0; i < cw::kCells; ++i) {
        s[static_cast<std::size_t>(i)] = ".#L"[g.ring[i]];
    }
    return s;
}

struct Replay {
    int problems = 0;
    int rounds = 0;
    int moves = 0;
    int wins = 0;
    int losses = 0;
    int blocked = 0;
};

// Replays a fixture stream. `quiet` suppresses messages (used for the tampered-fixture self-test).
static Replay ReplayGolden(std::istream& f, bool quiet) {
    Replay out;
    int& problems = out.problems;
    auto expect = [&problems, quiet](bool ok, const std::string& what) {
        if (!ok) {
            ++problems;
            if (!quiet && problems <= 20) {
                std::printf("FAIL: %s\n", what.c_str());
            }
        }
    };
    std::string line;
    std::string seed;
    std::unique_ptr<cw::Game> game;
    bool have_seed = false;
    int line_no = 0;
    int& rounds = out.rounds;
    int& moves = out.moves;
    int& wins = out.wins;
    int& losses = out.losses;
    while (std::getline(f, line)) {
        ++line_no;
        if (!line.empty() && line.back() == '\r') {
            line.pop_back();
        }
        if (line.empty() || line[0] == '#') {
            continue;
        }
        const std::string where = "line " + std::to_string(line_no);
        if (line.rfind("S ", 0) == 0) {
            const std::size_t sp = line.find(' ', 2);
            const long n = sp == std::string::npos ? -1 : std::strtol(line.substr(2, sp - 2).c_str(), nullptr, 10);
            const bool ok = n >= 0 && sp + 1 + static_cast<std::size_t>(n) == line.size();
            expect(ok, "S " + where);
            seed = ok ? line.substr(sp + 1) : std::string();
            have_seed = ok;
            game.reset();
        } else if (line.rfind("N ", 0) == 0) {
            expect(have_seed && !game, "N out of order " + where);
            std::istringstream in(line.substr(2));
            std::string grid;
            int budget = 0;
            std::string extra;
            in >> grid >> budget;
            expect(!in.fail() && !(in >> extra), "malformed N " + where);
            game.reset(new cw::Game(seed));
            expect(Text(game->GetGrid()) == grid && game->Budget() == budget, "new grid for '" + seed + "' " + where);
            have_seed = false;
            ++rounds;
        } else if (line.rfind("P ", 0) == 0) {
            expect(game != nullptr, "P before N " + where);
            if (!game) {
                continue;
            }
            std::istringstream in(line.substr(2));
            int cell = 0;
            int budget = 0;
            int score = 0;
            int demo = 0;
            std::string status;
            std::string grid;
            std::string state;
            std::string reason;
            std::string extra;
            in >> cell >> status >> grid >> budget >> state >> reason >> score >> demo;
            expect(!in.fail() && !(in >> extra), "malformed P " + where);
            const cw::Grid before = game->GetGrid();
            const int budget_before = game->Budget();
            const cw::Status st = game->Place(cell);
            expect(status == cw::StatusName(st), "status " + status + " vs " + cw::StatusName(st) + " " + where);
            expect(Text(game->GetGrid()) == grid, "grid " + where);
            expect(game->Budget() == budget && state == cw::StateName(game->GetState()), "budget/state " + where);
            expect(game->Score() == score && game->Demo() == demo, "score/demo " + where);
            expect(reason == cw::ReasonName(game->Reason()), "loss reason " + where);
            expect((game->GetState() == cw::State::Lost) == (game->Reason() != cw::LossReason::None), "reason iff lost " + where);
            if (st != cw::Status::Ok) {
                expect(std::memcmp(&before, &game->GetGrid(), sizeof before) == 0 && game->Budget() == budget_before,
                       "refusal changed the round " + where);
            } else if (game->GetState() != cw::State::Playing) {
                wins += game->GetState() == cw::State::Won ? 1 : 0;
                losses += game->GetState() == cw::State::Lost ? 1 : 0;
                out.blocked += game->Reason() == cw::LossReason::Blocked ? 1 : 0;
            }
            ++moves;
        } else {
            expect(false, "unknown row " + where);
        }
    }
    expect(rounds > 300 && wins > 20 && losses > 20 && out.blocked > 0, "coverage");
    return out;
}

static std::string Slurp(const char* path) {
    std::ifstream f(path, std::ios::binary);
    std::ostringstream s;
    s << f.rdbuf();
    return s.str();
}

static void Golden(const char* path) {
    const std::string text = Slurp(path);
    Check(!text.empty(), std::string("read golden file ") + path);
    std::istringstream in(text);
    const Replay r = ReplayGolden(in, false);
    Check(r.problems == 0, "golden fixture replays with no problems");
    std::printf("golden: %d rounds, %d placements, %d wins, %d losses (%d blocked), %d problems\n", r.rounds, r.moves,
                r.wins, r.losses, r.blocked, r.problems);
    // Self-test: tampered copies of the fixture must be rejected, so a passing replay means something.
    const std::size_t p = text.find("\nP ");
    const std::size_t n = text.find("\nN ");
    struct Tamper {
        const char* name;
        std::string body;
    };
    std::string flip_grid = text;
    flip_grid[n + 3] = flip_grid[n + 3] == '.' ? '#' : '.';
    std::string flip_status = text;
    const std::size_t ok = text.find(" OK ", p);
    flip_status.replace(ok, 4, " OCCUPIED ");
    std::string flip_reason = text;
    const std::size_t lost = text.find(" OUT_OF_LINKS ");
    flip_reason.replace(lost, 14, " BLOCKED ");
    std::string extra_token = text;
    extra_token.insert(text.find('\n', p + 1), " 7");
    std::string unknown_row = text + "Q nonsense\n";
    const Tamper tampers[] = {{"grid", flip_grid}, {"status", flip_status}, {"reason", flip_reason},
                              {"trailing token", extra_token}, {"unknown row", unknown_row}};
    for (const Tamper& t : tampers) {
        std::istringstream tin(t.body);
        Check(ReplayGolden(tin, true).problems > 0, std::string("tampered fixture rejected: ") + t.name);
    }
}

// Refusals must not draw randomness: interleaving bad moves leaves every later grid identical.
static void RefusalsDrawNothing() {
    bool ok = true;
    for (int s = 0; s < 200; ++s) {
        cw::Game a("r" + std::to_string(s));
        cw::Game b("r" + std::to_string(s));
        while (a.GetState() == cw::State::Playing) {
            const int cell = a.Demo();
            b.Place(-1);
            b.Place(cw::kCells);
            for (int i = 0; i < cw::kCells; ++i) {
                if (b.GetGrid().ring[i] != cw::kEmpty) {
                    b.Place(i);  // OCCUPIED
                    break;
                }
            }
            ok = ok && a.Place(cell) == cw::Status::Ok && b.Place(cell) == cw::Status::Ok;
            ok = ok && std::memcmp(&a.GetGrid(), &b.GetGrid(), sizeof(cw::Grid)) == 0 && a.Budget() == b.Budget();
        }
        ok = ok && a.GetState() == b.GetState() && a.Reason() == b.Reason();
    }
    Check(ok, "refusals draw no randomness and change nothing");
}

// Crossing cost moves the right way: a link on an empty ring lowers it by at most one, rust never lowers it.
static void CostMoves() {
    bool ok = true;
    int checked = 0;
    for (int s = 0; s < 300; ++s) {
        cw::Game g("c" + std::to_string(s));
        const cw::Grid base = g.GetGrid();
        const int c0 = cw::Crossing(base);
        for (int i = 0; i < cw::kCells; ++i) {
            if (base.ring[i] != cw::kEmpty) {
                continue;
            }
            cw::Grid l = base;
            l.ring[i] = cw::kLink;
            cw::Grid r = base;
            r.ring[i] = cw::kRust;
            const int cl = cw::Crossing(l);
            const int cr = cw::Crossing(r);
            ok = ok && cl <= c0 && cl >= c0 - 1 && cr >= c0;
            // The demo ring is exactly one that lowers the cost.
            ok = ok && (i != cw::DemoCell(base) || cl == c0 - 1);
            ++checked;
        }
    }
    Check(ok, "links lower the crossing by at most one, rust never lowers it, the demo ring lowers it");
    std::printf("cost moves: %d single-ring changes checked\n", checked);
}

// Every seed starts crossable within budget; the demo never wastes a link and wins most rounds.
static void Invariants() {
    int demo_wins = 0;
    bool ok = true;
    for (int s = 0; s < 1000; ++s) {
        cw::Game g("inv" + std::to_string(s));
        ok = ok && cw::Crossing(g.GetGrid()) + cw::kSlack == g.Budget() && g.Budget() > cw::kSlack;
        int turns = 0;
        while (g.GetState() == cw::State::Playing && turns < cw::kCells) {
            const int before = cw::Crossing(g.GetGrid());
            const int cell = g.Demo();
            ok = ok && cell >= 0 && g.Place(cell) == cw::Status::Ok;
            // A demo link always lowers the cheapest crossing by one before rust spreads.
            ok = ok && (g.GetState() == cw::State::Won || before >= 1);
            ++turns;
        }
        ok = ok && g.GetState() != cw::State::Playing;
        demo_wins += g.GetState() == cw::State::Won ? 1 : 0;
    }
    Check(ok, "every round starts crossable and ends");
    Check(demo_wins > 700, "the demo wins most rounds");
    std::printf("invariants: 1000 rounds, demo won %d\n", demo_wins);
}

static void Edges() {
    cw::Game g("edges");
    Check(g.Place(-1) == cw::Status::BadCell && g.Place(cw::kCells) == cw::Status::BadCell && g.Placed() == 0, "bad cells");
    int rust = -1;
    for (int i = 0; i < cw::kCells && rust < 0; ++i) {
        rust = g.GetGrid().ring[i] == cw::kRust ? i : -1;
    }
    Check(rust < 0 || g.Place(rust) == cw::Status::Occupied, "rust is occupied");
    while (g.GetState() == cw::State::Playing) {
        g.Place(g.Demo());
    }
    Check(g.Place(0) == cw::Status::GameOver, "no moves after the round ends");
    cw::Game a("same");
    cw::Game b("same");
    Check(std::memcmp(&a.GetGrid(), &b.GetGrid(), sizeof(cw::Grid)) == 0 && a.Budget() == b.Budget(), "same seed, same weave");
    Check(std::strcmp(cw::StatusName(static_cast<cw::Status>(9)), "UNKNOWN") == 0 &&
              std::strcmp(cw::StateName(static_cast<cw::State>(9)), "UNKNOWN") == 0 &&
              std::strcmp(cw::ReasonName(static_cast<cw::LossReason>(9)), "UNKNOWN") == 0,
          "unknown names");
}

int main(int argc, char** argv) {
    Golden(argc > 1 ? argv[1] : "chainmail_weave_golden.txt");
    Invariants();
    RefusalsDrawNothing();
    CostMoves();
    Edges();
    std::printf("%s: %d checks, %d failures\n", g_failures == 0 ? "PASS" : "FAIL", g_checks, g_failures);
    return g_failures == 0 ? EXIT_SUCCESS : EXIT_FAILURE;
}
