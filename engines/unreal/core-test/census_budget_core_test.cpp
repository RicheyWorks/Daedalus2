// SPDX-License-Identifier: MIT
// G206 port check: DaedalusCensusBudgetCore.h must replay census_budget_parity.txt (written by
// tools/streaming/census_budget_parity.py from census_budget.py) line for line, plus direct
// asserts on the 40000 KiB RAM / 32768 KiB disk edges. No test framework; exit 0 = pass.
#include "DaedalusCensusBudgetCore.h"

#include <cstdio>
#include <fstream>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

namespace CB = DaedalusCensusBudget;

static int Failures = 0;
static void Check(bool Ok, const std::string& What) {
    if (!Ok) {
        ++Failures;
        std::cerr << "FAIL: " << What << "\n";
    }
}

static std::string FlagText(unsigned F) {
    std::string S;
    const auto Add = [&S](const char* N) { S += S.empty() ? N : std::string(",") + N; };
    if (F & CB::RamOver) Add("ram_over");
    if (F & CB::DiskOver) Add("disk_over");
    if (F & CB::RamNear) Add("ram_near");
    if (F & CB::DiskNear) Add("disk_near");
    return S.empty() ? "-" : S;
}

struct PendingWorld {
    std::string Id;
    std::uint64_t Count = 0, Ram = 0, Disk = 0, Fits = 0, MaxRes = 0;
    std::vector<std::uint64_t> Assets;
    std::vector<std::string> Expected;  // "ram disk flags colour" per island
};

static CB::Budget Current;
static std::uint64_t SumG = 0, SumA = 0, SumR = 0, SumW = 0, SumI = 0, SumSpill = 0;
static std::string CaseName;

static void Flush(PendingWorld& W) {
    if (W.Id.empty()) return;
    const std::string Tag = CaseName + "/" + W.Id;
    Check(W.Assets.size() == W.Count, Tag + " island count");
    CB::WorldVerdict V;
    std::vector<CB::IslandVerdict> Isl;
    Check(CB::PlanWorld(W.Assets, Current, V, Isl), Tag + " plan refused");
    Check(V.TotalRamKiB == W.Ram, Tag + " total_ram");
    Check(V.TotalDiskKiB == W.Disk, Tag + " total_disk");
    Check(V.FitsAllResident == (W.Fits == 1), Tag + " fits_all_resident");
    Check(V.MaxResident == W.MaxRes, Tag + " max_resident");
    for (std::size_t i = 0; i < Isl.size() && i < W.Expected.size(); ++i) {
        std::ostringstream Got;
        Got << Isl[i].Cost.RamKiB << ' ' << Isl[i].Cost.DiskKiB << ' ' << FlagText(Isl[i].Flags) << ' '
            << CB::BeaconName(Isl[i].Colour);
        Check(Got.str() == W.Expected[i], Tag + " island " + std::to_string(i) + ": got " + Got.str() +
                                              " want " + W.Expected[i]);
    }
    SumW += 1;
    SumI += Isl.size();
    SumG += V.Green;
    SumA += V.Amber;
    SumR += V.Red;
    SumSpill += V.FitsAllResident ? 0 : 1;
    W = PendingWorld{};
}

static int Replay(const char* Path) {
    std::ifstream In(Path);
    if (!In) {
        std::cerr << "cannot open " << Path << "\n";
        return 2;
    }
    std::string Line;
    PendingWorld W;
    std::size_t Cases = 0, Islands = 0;
    while (std::getline(In, Line)) {
        if (Line.empty() || Line[0] == '#') continue;
        std::istringstream L(Line);
        char Kind = 0;
        L >> Kind;
        if (Kind == 'M') {
            std::uint64_t a, b, c, d;
            L >> a >> b >> c >> d;
            Check(a == CB::BaseRamKiB && b == CB::PerAssetRamKiB && c == CB::BaseDiskKiB &&
                      d == CB::PerAssetDiskKiB, "cost model constants");
        } else if (Kind == 'C') {
            std::string Budget;
            L >> CaseName >> Budget >> Current.RamKiB >> Current.DiskKiB >> Current.WarnPermille;
            CaseName += "@" + Budget;
            Check(CB::ValidBudget(Current), CaseName + " budget valid");
            SumG = SumA = SumR = SumW = SumI = SumSpill = 0;
            ++Cases;
        } else if (Kind == 'W') {
            Flush(W);
            L >> W.Id >> W.Count >> W.Ram >> W.Disk >> W.Fits >> W.MaxRes;
        } else if (Kind == 'I') {
            std::uint64_t Slot, N;
            std::string Ram, Disk, Flags, Colour;
            L >> Slot >> N >> Ram >> Disk >> Flags >> Colour;
            W.Assets.push_back(N);
            W.Expected.push_back(Ram + " " + Disk + " " + Flags + " " + Colour);
            ++Islands;
        } else if (Kind == 'S') {
            Flush(W);
            std::uint64_t w, i, g, a, r, s;
            L >> w >> i >> g >> a >> r >> s;
            Check(w == SumW && i == SumI && g == SumG && a == SumA && r == SumR && s == SumSpill,
                  CaseName + " summary");
        } else {
            Check(false, "unknown line: " + Line);
        }
        Check(!L.fail(), "parse: " + Line);
    }
    Check(Cases >= 27, "expected at least 27 parity cases");
    std::cout << "census_budget parity: " << Cases << " cases, " << Islands << " islands replayed\n";
    return 0;
}

static void Edges() {
    const CB::Budget B;  // shipped defaults
    Check(CB::ValidBudget(B), "default budget valid");
    const auto At = [&B](std::uint64_t N) {
        CB::IslandCost C;
        Check(CB::CostOf(N, C), "cost in range");
        return CB::Judge(C, B);
    };
    Check(At(0).Cost.RamKiB == 16384 && At(0).Cost.DiskKiB == 4096 && At(0).Colour == CB::Beacon::Green, "empty island");
    Check(At(984).Cost.RamKiB == 40000 && !(At(984).Flags & CB::RamOver), "ram exactly at budget is not over");
    Check(At(985).Flags & CB::RamOver, "ram one asset over budget");
    Check(At(298).Cost.DiskKiB == 32704 && At(298).Colour != CB::Beacon::Red, "disk 298 fits");
    Check(At(299).Cost.DiskKiB == 32800 && At(299).Flags == CB::DiskOver && At(299).Colour == CB::Beacon::Red,
          "disk 299 over; near flags suppressed");
    Check(At(264).Flags == 0 && At(265).Flags == CB::DiskNear, "disk warn line 264/265");
    Check(At(265).Colour == CB::Beacon::Amber, "near is amber");
    CB::IslandCost Big;
    Check(!CB::CostOf(CB::MaxAssetDefinitions + 1, Big), "port refuses counts past its range");
    CB::Budget Bad;
    Bad.WarnPermille = 0;
    Check(!CB::ValidBudget(Bad), "warn 0 refused");
    Bad = CB::Budget{};
    Bad.RamKiB = CB::MaxKiB + 1;
    Check(!CB::ValidBudget(Bad), "ram budget over MAX_KIB refused");
    Check(CB::MaxResident({40000, 16384, 16384, 16384}, 40000) == 2, "lightest first count");
    Check(CB::MaxResident({}, 40000) == 0, "empty world holds none");
}

int main(int argc, char** argv) {
    Edges();
    const int Rc = Replay(argc > 1 ? argv[1] : "census_budget_parity.txt");
    if (Rc) return Rc;
    if (Failures) {
        std::cerr << Failures << " failure(s)\n";
        return 1;
    }
    std::cout << "census_budget core: OK\n";
    return 0;
}
