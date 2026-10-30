// SPDX-License-Identifier: MIT
// G529 Budget Fathoms (disk-saver), header-only C++17 port of the pure logic of
// tools/streaming/budget_fathoms.py: green_kib (smallest budget keeping an island green),
// clear and fit budgets, fleet needs and slack per dimension, the --sweep-ram/--sweep-disk
// list parser (parse_list) and the re-priced sweep states, and the deep/shoal/aground
// verdict. Prices with the G206 port through DaedalusDiskSaverCensusPlanCore.h.
// Left in Python: JSON loading, reading an existing G206 report (to_report), text output
// and the CLI. Sweep text is ASCII: Python's str.isdigit()/strip() also accept non-ASCII
// digits and spaces, which this port refuses. No Unreal includes, no exceptions, no RTTI.
#pragma once

#include "DaedalusDiskSaverCensusPlanCore.h"

#include <algorithm>
#include <cstddef>
#include <cstdint>
#include <string>
#include <vector>

namespace DaedalusDiskSaver {
namespace BudgetFathoms {

namespace CB = ::DaedalusCensusBudget;

constexpr std::size_t MaxSweep = 64;
constexpr std::size_t MaxSweepBytes = 1 << 20;

enum class Error { None, Census, SweepRam, SweepDisk, Capacity };

struct Sweep {
    bool Given = false;  // false = the option was not passed
    std::string Text;
};

// parse_list(): comma pieces, each stripped, ASCII digits only, 1..MAX_KIB; at most 64; sorted, unique.
inline bool ParseList(const Sweep& S, std::vector<std::uint64_t>& Out) {
    Out.clear();
    if (!S.Given) return true;
    if (S.Text.size() > MaxSweepBytes) return false;
    std::size_t Start = 0;
    while (true) {
        std::size_t End = S.Text.find(',', Start);
        if (End == std::string::npos) End = S.Text.size();
        std::size_t A = Start, B = End;
        while (A < B && CensusPlan::IsSpace(static_cast<unsigned char>(S.Text[A]))) ++A;
        while (B > A && CensusPlan::IsSpace(static_cast<unsigned char>(S.Text[B - 1]))) --B;
        if (A == B) return false;
        for (std::size_t K = A; K < B; ++K)
            if (S.Text[K] < '0' || S.Text[K] > '9') return false;
        while (A < B && S.Text[A] == '0') ++A;
        if (A == B || B - A > 9) return false;  // zero, or above MAX_KIB (9 digits)
        std::uint64_t V = 0;
        for (std::size_t K = A; K < B; ++K) V = V * 10 + static_cast<std::uint64_t>(S.Text[K] - '0');
        if (V > CB::MaxKiB) return false;
        Out.push_back(V);
        if (End == S.Text.size()) break;
        Start = End + 1;
    }
    if (Out.size() > MaxSweep) return false;
    std::sort(Out.begin(), Out.end());
    Out.erase(std::unique(Out.begin(), Out.end()), Out.end());
    return true;
}

// green_kib(): smallest B with cost*1000 <= B*warn and cost <= B.
inline std::uint64_t GreenKiB(std::uint64_t Cost, std::uint64_t Warn) {
    const std::uint64_t Ceil = (Cost * 1000 + Warn - 1) / Warn;
    return std::max(Cost, Ceil);
}

enum class Depth { Deep, Shoal, Aground };

inline const char* DepthName(Depth D) { return D == Depth::Deep ? "deep" : D == Depth::Shoal ? "shoal" : "aground"; }

struct State {
    std::uint64_t Green = 0, Amber = 0, Red = 0, Spilling = 0;
    Depth Verdict = Depth::Deep;
};

inline State StateOf(const CensusPlan::Report& R) {
    State S{R.Green, R.Amber, R.Red, R.Spilling, Depth::Deep};
    S.Verdict = (S.Red || S.Spilling) ? Depth::Aground : S.Amber ? Depth::Shoal : Depth::Deep;
    return S;
}

struct Need {
    std::uint64_t AllGreen = 0, NoRed = 0, AllFit = 0, Deep = 0;
};

struct IslandNeed {
    std::uint64_t Slot = 0, RamGreen = 0, RamClear = 0, DiskGreen = 0, DiskClear = 0;
};

struct WorldNeed {
    std::string Id;
    std::uint64_t RamFit = 0, DiskFit = 0;
    std::vector<IslandNeed> Islands;
};

struct SweepRow {
    bool Ram = true;
    std::uint64_t BudgetKiB = 0;
    State S;
};

struct Result {
    Need Ram, Disk;
    long long RamSlack[4] = {0, 0, 0, 0}, DiskSlack[4] = {0, 0, 0, 0};  // all_green, no_red, all_fit, deep
    std::vector<WorldNeed> Worlds;
    std::vector<SweepRow> Sweeps;
    State Now;
};

inline void Slack(const Need& N, std::uint64_t Budget, long long* Out) {
    const std::uint64_t V[4] = {N.AllGreen, N.NoRed, N.AllFit, N.Deep};
    for (int K = 0; K < 4; ++K) Out[K] = static_cast<long long>(Budget) - static_cast<long long>(V[K]);
}

// main()'s order: price the census (to_report), parse --sweep-ram, then --sweep-disk, then build().
inline Error Build(const std::vector<CensusPlan::InWorld>& Census, const CB::Budget& B, const Sweep& SR, const Sweep& SD,
                   Result& Out, CensusPlan::Error& CensusError) {
    Out = Result{};
    CensusPlan::Report Cur;
    CensusError = CensusPlan::Plan(Census, B, Cur);
    if (CensusError != CensusPlan::Error::None) return Error::Census;
    std::vector<std::uint64_t> Ram, Disk;
    if (!ParseList(SR, Ram)) return Error::SweepRam;
    if (!ParseList(SD, Disk)) return Error::SweepDisk;
    for (const CensusPlan::World& W : Cur.Worlds) {
        WorldNeed O;
        O.Id = W.Id;
        O.RamFit = W.V.TotalRamKiB;
        O.DiskFit = W.V.TotalDiskKiB;
        for (const CensusPlan::Island& I : W.Islands) {
            const IslandNeed N{I.Slot, GreenKiB(I.V.Cost.RamKiB, B.WarnPermille), I.V.Cost.RamKiB,
                               GreenKiB(I.V.Cost.DiskKiB, B.WarnPermille), I.V.Cost.DiskKiB};
            O.Islands.push_back(N);
            Out.Ram.AllGreen = std::max(Out.Ram.AllGreen, N.RamGreen);
            Out.Ram.NoRed = std::max(Out.Ram.NoRed, N.RamClear);
            Out.Disk.AllGreen = std::max(Out.Disk.AllGreen, N.DiskGreen);
            Out.Disk.NoRed = std::max(Out.Disk.NoRed, N.DiskClear);
        }
        Out.Ram.AllFit = std::max(Out.Ram.AllFit, O.RamFit);
        Out.Disk.AllFit = std::max(Out.Disk.AllFit, O.DiskFit);
        Out.Worlds.push_back(O);
    }
    Out.Ram.Deep = std::max(Out.Ram.AllGreen, Out.Ram.AllFit);
    Out.Disk.Deep = std::max(Out.Disk.AllGreen, Out.Disk.AllFit);
    Slack(Out.Ram, B.RamKiB, Out.RamSlack);
    Slack(Out.Disk, B.DiskKiB, Out.DiskSlack);
    for (int Dim = 0; Dim < 2; ++Dim) {
        for (std::uint64_t V : Dim == 0 ? Ram : Disk) {
            CB::Budget NB = B;
            (Dim == 0 ? NB.RamKiB : NB.DiskKiB) = V;
            CensusPlan::Report R;
            if (CensusPlan::Plan(Census, NB, R) != CensusPlan::Error::None) return Error::Capacity;
            Out.Sweeps.push_back(SweepRow{Dim == 0, V, StateOf(R)});
        }
    }
    Out.Now = StateOf(Cur);
    return Error::None;
}

}  // namespace BudgetFathoms
}  // namespace DaedalusDiskSaver
