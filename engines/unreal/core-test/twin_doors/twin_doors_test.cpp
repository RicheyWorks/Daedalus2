// SPDX-License-Identifier: MIT
// Usage: twin_doors_test <docs/contracts/twin-doors-v1/riddles.twd>
#include "DaedalusTwinDoorsCore.h"
#include <climits>
#include <fstream>
#include <sstream>

using namespace daedalus::labyrinth;
static int checks = 0, failures = 0;
static void Check(bool ok, const char* what) { ++checks; if (!ok) { ++failures; std::printf("FAIL %s\n", what); } }

int main(int argc, char** argv) {
    if (argc != 2) { std::printf("usage: twin_doors_test riddles.twd\n"); return 2; }
    std::ifstream in(argv[1], std::ios::binary); std::stringstream ss; ss << in.rdbuf();
    const int64_t seeds[] = {1, 42, -7, 0x5EEDCAFE, LLONG_MIN};
    std::string all;
    for (int64_t s : seeds) for (int d = 0; d <= 1; ++d) all += TwinDoors(s, d).ToWire();
    Check(all == ss.str(), "byte parity with Java fixture (10 riddles)");
    bool embedded = true, worlds[8] = {};
    for (int64_t s = -1000; s < 1000; ++s) for (int d = 0; d <= 1; ++d) {
        TwinDoors t(s, d);
        worlds[t.GetSafeDoor() * 4 + t.GetLiar() * 2 + (t.GetLowMeansYes() ? 1 : 0)] = true;
        for (int g = 0; g < 2; ++g) for (int door = 0; door < 2; ++door) {
            const TwinTone h = t.Answer(g, TwinQuestion::Embedded, door);
            if (TwinDoors::Deduce(d, g, TwinQuestion::Embedded, door, h) != t.GetSafeDoor()) embedded = false;
        }
    }
    Check(embedded, "embedded question always solves (2000 seeds x 2 difficulties)");
    bool all8 = true; for (bool w : worlds) all8 = all8 && w;
    Check(all8, "seeds reach all 8 worlds");
    TwinDoors e(3, 0), h(3, 1);
    Check(TwinDoors::Deduce(0, 1, TwinQuestion::OtherGuard, 0, e.Answer(1, TwinQuestion::OtherGuard, 0)) == e.GetSafeDoor(), "other-guard solves at difficulty 0");
    Check(TwinDoors::Deduce(1, 1, TwinQuestion::OtherGuard, 0, h.Answer(1, TwinQuestion::OtherGuard, 0)) == -1, "other-guard fails at difficulty 1");
    Check(TwinDoors::Deduce(0, 0, TwinQuestion::Direct, 0, TwinTone::Low) == -1, "direct never solves");
    Check(TwinDoors::Deduce(1, 0, TwinQuestion::Self, 1, TwinTone::High) == -1, "self never solves");
    Check(TwinDoors::kLowHz < TwinDoors::kHighHz && TwinDoors::kHighHz < 360.0 && TwinDoors::kGain <= 0.6, "ear rules");
    Check(e.Choose(e.GetSafeDoor()) && !e.Choose(1 - e.GetSafeDoor()), "choose");
    bool threw = false; try { TwinDoors(1, 2); } catch (const std::invalid_argument&) { threw = true; }
    Check(threw, "bad difficulty rejected");
    threw = false; try { (void)e.Answer(2, TwinQuestion::Direct, 0); } catch (const std::invalid_argument&) { threw = true; }
    Check(threw, "bad guard rejected");
    std::printf("twin_doors: %d checks, %d failed\n", checks, failures);
    return failures ? 1 : 0;
}
