// SPDX-License-Identifier: MIT
// G556 Manifest Match core, header-only C++17 port of tools/streaming/manifest_match.py (G573).
// Takes an already-dealt table (one pair id per card, as laid out by the Python tool) and ports the
// perfect-memory par, the turn validation and the verdict. Engine-free: no Unreal includes, no
// exceptions, no RTTI; errors come back as an Error code.
#pragma once

#include <cstdint>
#include <utility>
#include <vector>

namespace DaedalusDiskSaver {
namespace ManifestMatch {

constexpr int MaxCards = 64;
enum class Error { None, BadTable, Range, Matched, Same, Over };
enum class Verdict { Sharp, Matched, Unfinished };
using Turn = std::pair<int, int>;  // 1-based positions

struct Result {
    Error Err = Error::None;
    int MatchedPairs = 0;
    std::vector<bool> Hits;
    Verdict V = Verdict::Unfinished;
};

// Every pair id appears exactly twice; at most MaxCards cards.
inline bool ValidTable(const std::vector<int>& Ids) {
    if (Ids.empty() || Ids.size() % 2 || Ids.size() > static_cast<std::size_t>(MaxCards)) return false;
    for (int Id : Ids) {
        if (Id < 0 || Id >= MaxCards) return false;
        int Count = 0;
        for (int J : Ids) Count += J == Id;
        if (Count != 2) return false;
    }
    return true;
}

// perfect_turns: insertion-ordered "known" map, exactly as the Python dict behaves. 0-based turns.
inline bool PerfectTurns(const std::vector<int>& Ids, std::vector<Turn>& Out) {
    Out.clear();
    if (!ValidTable(Ids)) return false;
    const int N = static_cast<int>(Ids.size());
    std::vector<bool> Matched(N, false);
    int MatchedCount = 0;
    std::vector<std::pair<int, std::vector<int>>> Known;  // pair -> seen unmatched positions
    int Cursor = 0;
    const auto Find = [&Known](int P) -> int {
        for (std::size_t i = 0; i < Known.size(); ++i)
            if (Known[i].first == P) return static_cast<int>(i);
        return -1;
    };
    const auto InKnown = [&Known](int Pos) {
        for (const auto& K : Known)
            for (int X : K.second)
                if (X == Pos) return true;
        return false;
    };
    const auto TakeUnknown = [&]() -> int {
        while (Cursor < N && (Matched[Cursor] || InKnown(Cursor))) ++Cursor;
        return Cursor < N ? Cursor : -1;
    };
    const auto Match = [&](int A, int B) {
        Out.emplace_back(A, B);
        Matched[A] = Matched[B] = true;
        MatchedCount += 2;
    };
    int Guard = 0;
    while (MatchedCount < N) {
        if (++Guard > 4 * N + 4) return false;
        int Ready = -1;
        for (std::size_t i = 0; i < Known.size(); ++i)
            if (Known[i].second.size() == 2) {
                Ready = static_cast<int>(i);
                break;
            }
        if (Ready >= 0) {
            int A = Known[Ready].second[0], B = Known[Ready].second[1];
            if (A > B) std::swap(A, B);
            Known.erase(Known.begin() + Ready);
            Match(A, B);
            continue;
        }
        const int A = TakeUnknown();
        if (A < 0) return false;
        const int Pa = Ids[A];
        const int Ka = Find(Pa);
        if (Ka >= 0) {
            const int B = Known[Ka].second[0];
            Known.erase(Known.begin() + Ka);
            Match(A, B);
            continue;
        }
        Known.push_back({Pa, {A}});
        ++Cursor;
        const int B = TakeUnknown();
        if (B < 0) return false;
        ++Cursor;
        const int Pb = Ids[B];
        if (Pa == Pb) {
            Known.erase(Known.begin() + Find(Pa));
            Match(A, B);
        } else {
            Out.emplace_back(A, B);
            const int Kb = Find(Pb);
            if (Kb >= 0) Known[Kb].second.push_back(B);
            else Known.push_back({Pb, {B}});
        }
    }
    return true;
}

inline Result Play(const std::vector<int>& Ids, const std::vector<Turn>& Turns) {
    Result R;
    std::vector<Turn> Best;
    if (!PerfectTurns(Ids, Best)) {
        R.Err = Error::BadTable;
        return R;
    }
    const int N = static_cast<int>(Ids.size());
    std::vector<bool> Matched(N, false);
    int Count = 0;
    for (const Turn& T : Turns) {
        if (Count == N) { R.Err = Error::Over; return R; }
        for (int P : {T.first, T.second}) {
            if (P < 1 || P > N) { R.Err = Error::Range; return R; }
            if (Matched[P - 1]) { R.Err = Error::Matched; return R; }
        }
        if (T.first == T.second) { R.Err = Error::Same; return R; }
        const bool Hit = Ids[T.first - 1] == Ids[T.second - 1];
        if (Hit) {
            Matched[T.first - 1] = Matched[T.second - 1] = true;
            Count += 2;
        }
        R.Hits.push_back(Hit);
    }
    R.MatchedPairs = Count / 2;
    R.V = Count < N ? Verdict::Unfinished
                    : (Turns.size() <= Best.size() ? Verdict::Sharp : Verdict::Matched);
    return R;
}

inline const char* VerdictName(Verdict V) {
    return V == Verdict::Sharp ? "sharp" : V == Verdict::Matched ? "matched" : "unfinished";
}
inline const char* ErrorName(Error E) {
    switch (E) {
        case Error::Range: return "range";
        case Error::Matched: return "matched";
        case Error::Same: return "same";
        case Error::Over: return "over";
        case Error::BadTable: return "table";
        default: return "none";
    }
}

}  // namespace ManifestMatch
}  // namespace DaedalusDiskSaver
