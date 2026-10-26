// SPDX-License-Identifier: MIT
// Usage: echo_bell_test <docs/contracts/echo-bell-v1/peals.ebg>
#include "DaedalusEchoBellCore.h"
#include <climits>
#include <fstream>
#include <sstream>

using daedalus::labyrinth::EchoBellGate;
static int checks = 0, failures = 0;
static void Check(bool ok, const char* what) { ++checks; if (!ok) { ++failures; std::printf("FAIL %s\n", what); } }
static std::vector<int> Perfect(const EchoBellGate& g) {
    std::vector<int> e; for (const auto& r : g.GetRings()) e.push_back(r.EchoMs);
    std::sort(e.begin(), e.end()); return e;
}

int main(int argc, char** argv) {
    if (argc != 2) { std::printf("usage: echo_bell_test peals.ebg\n"); return 2; }
    std::ifstream in(argv[1], std::ios::binary); std::stringstream ss; ss << in.rdbuf();
    const int64_t seeds[] = {1, 42, -7, 0x5EEDCAFE, LLONG_MIN};
    std::string all;
    for (int64_t s : seeds) for (int d = 0; d <= 3; ++d) all += EchoBellGate(s, d, d % 2 == 1).ToWire();
    Check(all == ss.str(), "byte parity with Java fixture (20 peals)");
    for (int64_t s = -500; s < 500; ++s) for (int d = 0; d <= 3; ++d) {
        EchoBellGate g(s, d, false); int last = 0;
        for (const auto& r : g.GetRings()) {
            if (r.Hz < EchoBellGate::kRootHz - 0.001 || r.Hz > EchoBellGate::kMaxHz) { Check(false, "ear rule hz"); }
            if (r.Gain != (r.RingMs - last <= 750 ? 0.3 : 0.6)) { Check(false, "passing notes light"); }
            last = r.RingMs;
        }
    }
    Check(true, "ear rules over 4000 peals");
    EchoBellGate g(42, 2, false);
    Check(g.GetWindowMs() == 100, "window");
    auto taps = Perfect(g);
    Check(g.Judge(taps).Open, "perfect taps open");
    for (auto& t : taps) t += 100;
    Check(g.Judge(taps).Open, "window edge counts");
    taps[0] += 1;
    auto v = g.Judge(taps);
    Check(!v.Open && v.FirstMiss == 0 && v.Hits == static_cast<int>(taps.size()) - 1, "just outside misses");
    auto p = Perfect(g); p.pop_back();
    Check(!g.Judge(p).Open && g.Judge(p).FirstMiss == static_cast<int>(p.size()), "missing tap");
    p = Perfect(g); p.push_back(p.back() + 50);
    Check(!g.Judge(p).Open && g.Judge(p).FirstMiss == static_cast<int>(p.size()) - 1, "extra tap");
    Check(EchoBellGate(1, 0, true).GetWindowMs() == 210, "crickets widen");
    EchoBellGate m(99, 0, false, {1, 20, 40});
    Check(m.GetRings()[2].EchoMs - m.GetRings()[2].RingMs == 200 + 70 * 40, "maze depth echo");
    Check(m.IsValid() && EchoBellGate(42, 2, false).IsValid(), "valid configs are valid");
    EchoBellGate badDepth(1, 0, false, {0, 2, 3});
    Check(!badDepth.IsValid() && badDepth.GetRings().empty() && badDepth.GetWindowMs() == 0, "bad depth rejected");
    EchoBellGate badDiff(1, 4, false);
    Check(!badDiff.IsValid() && badDiff.GetRings().empty(), "bad difficulty rejected");
    Check(!EchoBellGate(1, 1, false, {2, 3}).IsValid(), "wrong depth count rejected");
    std::printf("echo_bell: %d checks, %d failed\n", checks, failures);
    return failures ? 1 : 0;
}
