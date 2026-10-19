// SPDX-License-Identifier: MIT
// Engine-free replay of the echo-bell-v1 contract through the same session code AEchoBellGate uses
// (DaedalusLink Public/DaedalusEchoBellSessionCore.h): cue scheduling, Use-key taps, Judge, open/retry.
// Usage (from engines/unreal/core-test/echo_bell):
//   g++ -std=c++17 -Wall -Wextra -Werror -I../../DaedalusLink/Source/DaedalusLink/Public echo_bell_gate_session_test.cpp -o egs
//   ./egs ../../../../docs/contracts/echo-bell-v1/CUE-SHEET.md ../../../../docs/contracts/echo-bell-v1/peals.ebg
#include "DaedalusEchoBellSessionCore.h"

#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>

using namespace daedalus::labyrinth;

static int checks = 0, failures = 0;
static void Check(bool ok, const std::string& what) {
    ++checks;
    if (!ok) { ++failures; std::printf("FAIL %s\n", what.c_str()); }
}

static std::string ReadAll(const char* path) {
    std::ifstream in(path, std::ios::binary);
    std::stringstream ss;
    ss << in.rdbuf();
    return ss.str();
}

static std::string Fmt3(double v) {
    char b[32];
    std::snprintf(b, sizeof b, "%.3f", v);
    return b;
}

static std::string Trim(const std::string& s) {
    const size_t a = s.find_first_not_of(" \t\r");
    if (a == std::string::npos) return "";
    const size_t z = s.find_last_not_of(" \t\r");
    return s.substr(a, z - a + 1);
}

// Drives a session exactly like AEchoBellGate::Tick: advance the clock in steps, tap when told, judge when due.
struct Replay { std::vector<EchoCue> Played; bool Judged = false; EchoVerdict Verdict{false, 0, -1, {}}; int JudgedAtMs = -1; };
static Replay Run(EchoBellSession& s, const std::vector<int>& taps, int stepMs = 10) {
    Replay r;
    std::vector<EchoCue> due;
    size_t nextTap = 0;
    for (int now = 0; now <= s.DeadlineAtMs() + 2 * stepMs; now += stepMs) {
        while (nextTap < taps.size() && taps[nextTap] <= now) s.Tap(taps[nextTap++]);
        s.Advance(now, due);
        r.Played.insert(r.Played.end(), due.begin(), due.end());
        if (s.JudgeDue(now)) { r.Verdict = s.Finish(); r.Judged = true; r.JudgedAtMs = now; break; }
    }
    return r;
}

struct Peal { int64_t Seed; int Difficulty; int Crickets; int Window; std::vector<std::vector<std::string>> Rows; std::string Wire; };

static std::vector<Peal> ParseEbg(const std::string& text) {
    std::vector<Peal> out;
    std::istringstream in(text);
    std::string line, block;
    Peal p{};
    while (std::getline(in, line)) {
        block += line + "\n";
        std::istringstream ls(line);
        std::string tag;
        ls >> tag;
        if (tag == "gate") { long long seed; ls >> seed >> p.Difficulty >> p.Crickets >> p.Window; p.Seed = seed; }
        else if (tag == "bell") {
            std::vector<std::string> f; std::string x;
            while (ls >> x) f.push_back(x);
            p.Rows.push_back(f);  // index ring hz gain depth echo
        } else if (tag == "end") { p.Wire = block; out.push_back(p); p = Peal{}; block.clear(); }
    }
    return out;
}

static std::vector<Peal> ParseCueSheet(const std::string& text) {
    std::vector<Peal> out;
    std::istringstream in(text);
    std::string line;
    while (std::getline(in, line)) {
        if (line.rfind("### seed ", 0) == 0) {  // "### seed S, difficulty D, crickets C: N bells, window +/- W ms"
            std::string h = line;
            for (char& ch : h) if (ch == ',' || ch == ':') ch = ' ';
            std::istringstream hs(h);
            std::string w1, w2, w3, w4, w5, w6, w7;
            long long seed = 0; int d = -1, c = -1, n = 0, w = 0;
            hs >> w1 >> w2 >> seed >> w3 >> d >> w4 >> c >> n >> w5 >> w6 >> w7 >> w;
            if (!hs.fail() && w3 == "difficulty" && w4 == "crickets" && w7 == "+/-") out.push_back(Peal{seed, d, c, w, {}, ""});
            continue;
        }
        if (out.empty() || line.size() < 2 || line[0] != '|' || line.find("---") != std::string::npos || line.find("Bell") != std::string::npos) continue;
        std::vector<std::string> f;
        std::stringstream ls(line.substr(1));
        std::string cell;
        while (std::getline(ls, cell, '|')) { cell = Trim(cell); if (!cell.empty()) f.push_back(cell); }
        if (f.size() == 7) out.back().Rows.push_back(f);  // bell ring hz gain depth delay echo
    }
    return out;
}

static EchoGateConfig ConfigOf(const Peal& p, bool withDepths, size_t depthCol) {
    EchoGateConfig c;
    c.Seed = p.Seed; c.Difficulty = p.Difficulty; c.Crickets = p.Crickets != 0;
    if (withDepths) for (const auto& r : p.Rows) c.Depths.push_back(std::atoi(r[depthCol].c_str()));
    return c;
}

int main(int argc, char** argv) {
    if (argc != 3) { std::printf("usage: echo_bell_gate_session_test CUE-SHEET.md peals.ebg\n"); return 2; }
    const std::vector<Peal> sheet = ParseCueSheet(ReadAll(argv[1]));
    const std::vector<Peal> peals = ParseEbg(ReadAll(argv[2]));
    Check(sheet.size() == 20, "cue sheet has 20 fixture peals (got " + std::to_string(sheet.size()) + ")");
    Check(peals.size() == 20, "peals.ebg has 20 peals (got " + std::to_string(peals.size()) + ")");

    // 1. CUE-SHEET.md: every row's bell and echo cue as scheduled for the actor.
    for (const Peal& p : sheet) {
        const std::string tag = "seed " + std::to_string(p.Seed) + " d" + std::to_string(p.Difficulty);
        EchoBellSession s;
        Check(s.Start(ConfigOf(p, false, 0)), tag + " starts");
        Check(s.WindowMs() == p.Window, tag + " window");
        Check(p.Rows.size() == static_cast<size_t>(3 + p.Difficulty), tag + " bell count");
        const auto& cues = s.GetCues();
        Check(cues.size() == p.Rows.size() * (p.Crickets ? 3u : 2u), tag + " cue count");
        for (const auto& row : p.Rows) {
            const int i = std::atoi(row[0].c_str()), ring = std::atoi(row[1].c_str());
            const int depth = std::atoi(row[4].c_str()), delay = std::atoi(row[5].c_str()), echo = std::atoi(row[6].c_str());
            bool bell = false, echoed = false, cricket = !p.Crickets;
            for (const EchoCue& c : cues) {
                if (c.BellIndex != i) continue;
                if (c.Kind == EchoCueKind::Bell)
                    bell = c.AtMs == ring && Fmt3(c.Hz) == row[2] && Fmt3(c.Gain) == row[3] && c.LowPassHz == 0.0;
                if (c.Kind == EchoCueKind::Echo)
                    echoed = c.AtMs == echo && Fmt3(c.Hz) == row[2] && Fmt3(c.Gain * 2.0) == row[3] && c.LowPassHz == 1200.0;
                if (c.Kind == EchoCueKind::Cricket) cricket = p.Crickets && c.AtMs == echo && c.Gain <= 0.2;
            }
            Check(bell, tag + " bell " + row[0] + " at ringMs/hz/gain");
            Check(echoed, tag + " echo " + row[0] + " at echoMs, x0.5 gain, low-pass");
            Check(cricket, tag + " cricket tick " + row[0]);
            Check(delay == EchoBellGate::EchoDelayMs(depth) && echo - ring == delay, tag + " echo delay = 200 + 70 x depth");
        }
        for (size_t k = 1; k < cues.size(); ++k) {
            if (cues[k].AtMs < cues[k - 1].AtMs) { Check(false, tag + " cues time-ordered"); break; }
        }
    }

    // 2. peals.ebg: same peal with explicit maze depths, then full play loops.
    for (const Peal& p : peals) {
        const std::string tag = "ebg seed " + std::to_string(p.Seed) + " d" + std::to_string(p.Difficulty);
        EchoBellSession s;
        Check(s.Start(ConfigOf(p, true, 4)), tag + " starts with maze depths");
        Check(s.GetGate()->ToWire() == p.Wire, tag + " wire parity with depths");
        EchoBellSession seeded;
        seeded.Start(ConfigOf(p, false, 0));
        Check(seeded.GetGate()->ToWire() == p.Wire, tag + " wire parity seed-picked");

        // Perfect taps: every cue fires once in order, gate opens on attempt 1.
        Replay ok = Run(s, s.PerfectTaps());
        Check(ok.Judged && ok.Verdict.Open && s.Phase() == EchoPhase::Opened && s.Attempts() == 1, tag + " perfect taps open");
        Check(ok.Played.size() == s.GetCues().size(), tag + " all cues played once");
        bool same = ok.Played.size() == s.GetCues().size();
        for (size_t k = 0; same && k < ok.Played.size(); ++k) same = ok.Played[k].AtMs == s.GetCues()[k].AtMs && ok.Played[k].Kind == s.GetCues()[k].Kind;
        Check(same, tag + " cues played in schedule order");
        Check(!s.Tap(99999) && !s.Retry(), tag + " opened gate ignores taps and retry");

        // Window edges: exactly -window on the first echo and +window on the rest still open.
        const int n = static_cast<int>(p.Rows.size());
        EchoBellSession t;
        t.Start(ConfigOf(p, true, 4));
        std::vector<int> edge = t.PerfectTaps();
        edge[0] -= p.Window;
        for (size_t k = 1; k < edge.size(); ++k) edge[k] += p.Window;
        Check(Run(t, edge).Verdict.Open, tag + " taps at exactly +/- window open");

        // One ms outside the window on the last echo: miss, OnRetry data, then the same peal again.
        EchoBellSession m;
        m.Start(ConfigOf(p, true, 4));
        std::vector<int> late = m.PerfectTaps();
        late.back() += p.Window + 1;
        Replay miss = Run(m, late, 1);
        Check(miss.Judged && !miss.Verdict.Open && miss.Verdict.FirstMiss == n - 1 && miss.Verdict.Hits == n - 1,
              tag + " 1 ms outside the window misses");
        Check(m.Phase() == EchoPhase::Failed && !m.Tap(1), tag + " failed gate ignores taps until retry");
        Check(m.Retry() && m.Attempts() == 2 && m.Phase() == EchoPhase::Listening && m.GetTaps().empty() && m.CuesPlayed() == 0,
              tag + " retry re-arms the same peal");
        Replay again = Run(m, m.PerfectTaps());
        Check(again.Verdict.Open && m.Attempts() == 2 && again.Played.size() == m.GetCues().size(),
              tag + " retry replays the full peal and opens");

        // Missing last tap: judged only after the last echo's window closes.
        EchoBellSession q;
        q.Start(ConfigOf(p, true, 4));
        std::vector<int> few = q.PerfectTaps();
        few.pop_back();
        Replay short_ = Run(q, few);
        Check(short_.Judged && !short_.Verdict.Open && short_.JudgedAtMs > q.DeadlineAtMs() && short_.Verdict.FirstMiss == n - 1,
              tag + " missing tap judged after the last window");

        // A stray early tap shifts every tap off its echo: no open.
        EchoBellSession x;
        x.Start(ConfigOf(p, true, 4));
        std::vector<int> stray = x.PerfectTaps();
        stray.insert(stray.begin(), stray.front() - 500);
        Replay sx = Run(x, stray);
        Check(sx.Judged && !sx.Verdict.Open && sx.Verdict.FirstMiss == 0, tag + " stray tap fails");
    }

    // 2b. Prometheus's oracle (48496): 7 bells, gain 0.6 / 0.3 passing (gap <= 750 ms),
    // echo = ring + 200 + 70 x depth, window 140/120/100/80 by difficulty, x1.5 with crickets.
    // Hz within 0.001 of the oracle set: the core rounds G3/F4 to 195.997/349.227 (as peals.ebg and
    // the CUE-SHEET tables do) where the oracle list prints 195.998/349.228.
    {
        const double bells[7] = {146.832, 174.614, 195.998, 219.999, 261.625, 293.664, 349.228};
        const int windows[4] = {140, 120, 100, 80};
        bool hzOk = true, gainOk = true, echoOk = true, winOk = true, cueOk = true;
        for (int64_t seed = -500; seed < 500; ++seed) {
            for (int d = 0; d <= 3; ++d) {
                for (int crk = 0; crk <= 1; ++crk) {
                    EchoBellSession s;
                    EchoGateConfig c; c.Seed = seed; c.Difficulty = d; c.Crickets = crk != 0;
                    s.Start(c);
                    if (s.WindowMs() != (crk ? windows[d] * 3 / 2 : windows[d])) winOk = false;
                    int last = 0;
                    for (const EchoRing& r : s.GetGate()->GetRings()) {
                        bool near = false;
                        for (double b : bells) near = near || std::abs(r.Hz - b) <= 0.0010001;
                        hzOk = hzOk && near;
                        gainOk = gainOk && r.Gain == (r.RingMs - last <= 750 ? 0.3 : 0.6);
                        echoOk = echoOk && r.EchoMs == r.RingMs + 200 + 70 * r.DepthCells;
                        last = r.RingMs;
                    }
                    for (const EchoCue& q : s.GetCues()) {
                        if (q.Kind == EchoCueKind::Cricket) { cueOk = cueOk && q.Gain <= 0.2 && crk; continue; }
                        bool near = false;
                        for (double b : bells) near = near || std::abs(q.Hz - b) <= 0.0010001;
                        cueOk = cueOk && near && q.Gain <= 0.6;
                    }
                }
            }
        }
        Check(hzOk, "oracle: every bell within 0.001 Hz of the 7-bell set (8000 peals)");
        Check(gainOk, "oracle: gain 0.6, 0.3 for passing notes (gap <= 750 ms)");
        Check(echoOk, "oracle: echoMs = ring + 200 + 70 x depth");
        Check(winOk, "oracle: window 140/120/100/80 by difficulty, x1.5 with crickets");
        Check(cueOk, "oracle: scheduled cues stay on the bell set, gain <= 0.6, crickets <= 0.2");
    }
    // 3. Invalid configs are refused without reaching the core's throw paths.
    std::string why;
    EchoBellSession bad;
    EchoGateConfig c4; c4.Difficulty = 4;
    Check(!bad.Start(c4, &why) && why == "difficulty 0-3" && bad.Phase() == EchoPhase::Idle, "difficulty 4 refused");
    EchoGateConfig c0; c0.Depths = {0, 2, 3};
    Check(!bad.Start(c0, &why) && why == "corridor depth 1-40 cells", "depth 0 refused");
    EchoGateConfig c2; c2.Depths = {2, 3};
    Check(!bad.Start(c2, &why) && why == "one depth per bell", "depth count refused");
    Check(!bad.Tap(5) && !bad.JudgeDue(99999) && !bad.Retry(), "idle session ignores taps");

    std::printf("echo_bell_gate_session: %d checks, %d failed\n", checks, failures);
    return failures ? 1 : 0;
}