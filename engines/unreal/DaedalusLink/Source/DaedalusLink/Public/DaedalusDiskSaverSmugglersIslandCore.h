// SPDX-License-Identifier: MIT
// G553 Smuggler's Island core, header-only C++17 port of tools/streaming/smugglers_island.py
// (G576 batch 4). Takes the suspects as the Python tool read them from the census (label, world,
// realm, slot, cargo, sorted by label) and the hidden island it picked (the seeded pick stays in
// Python and is carried in the golden file), and ports the question list (same candidate order
// and duplicate-split rule), the exact minimax depth memoised on the suspect set, the auto
// strategy, ask/accuse validation and the verdict. Engine-free: no Unreal includes, no exceptions,
// no RTTI. Suspect sets are uint64 bits (Python caps at 40); the memo stops at MaxStates.
#pragma once

#include <algorithm>
#include <cstdint>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <vector>

namespace DaedalusDiskSaver {
namespace SmugglersIsland {

constexpr int MaxSuspects = 40;  // same cap as Python's MAX_SUSPECTS
constexpr int MaxCount = 1000000000;
constexpr std::size_t MaxStates = 4000000;
constexpr std::size_t MaxAsks = 4096;
constexpr int NoSplit = 1000000;  // Python's 10 ** 6 for a set no question splits
enum class Error { None, BadSuspects, Capped, Mode, Accuse, Question, Island, Stuck, TooLong };
enum class Verdict { Sharp, Caught, Escaped };

inline const char* ErrorName(Error E) {
    switch (E) {
        case Error::None: return "none";
        case Error::BadSuspects: return "suspects";
        case Error::Capped: return "capped";
        case Error::Mode: return "mode";
        case Error::Accuse: return "accuse";
        case Error::Question: return "question";
        case Error::Island: return "island";
        case Error::Stuck: return "stuck";
        case Error::TooLong: return "toolong";
    }
    return "?";
}
inline const char* VerdictName(Verdict V) {
    switch (V) {
        case Verdict::Sharp: return "sharp";
        case Verdict::Caught: return "caught";
        case Verdict::Escaped: return "escaped";
    }
    return "?";
}

struct Suspect {
    std::string Label, World, Realm;  // Realm is "none" for worlds without one
    int Slot = 0, Cargo = 0;
};
struct Question {
    std::string Id;
    std::uint64_t Yes = 0;
};

inline std::uint64_t Bit(int I) { return std::uint64_t{1} << I; }
inline int Bits(std::uint64_t X) {
    int C = 0;
    while (X) {
        X &= X - 1;
        ++C;
    }
    return C;
}
inline int Lowest(std::uint64_t X) {
    int I = 0;
    while (!(X >> I & 1)) ++I;
    return I;
}

inline bool ValidSuspects(const std::vector<Suspect>& S, int Hidden) {
    const int N = static_cast<int>(S.size());
    if (N < 1 || N > MaxSuspects || Hidden < 0 || Hidden >= N) return false;
    for (int I = 0; I < N; ++I) {
        if (S[I].Label.empty() || S[I].Slot < 0 || S[I].Slot > MaxCount || S[I].Cargo < 0 || S[I].Cargo > MaxCount) return false;
        if (I && !(S[I - 1].Label < S[I].Label)) return false;  // sorted, unique
    }
    return true;
}

// questions(): world:W, realm:R, slot>=K, cargo>=K (K > 0), empty; trivial or repeated splits dropped.
// Empty when there are more than MaxSuspects suspects.
inline std::vector<Question> Questions(const std::vector<Suspect>& S) {
    if (S.size() > static_cast<std::size_t>(MaxSuspects)) return {};
    const int N = static_cast<int>(S.size());
    std::vector<std::string> Worlds, Realms;
    std::vector<int> Slots, Cargos;
    for (const Suspect& X : S) {
        Worlds.push_back(X.World);
        Realms.push_back(X.Realm);
        Slots.push_back(X.Slot);
        if (X.Cargo > 0) Cargos.push_back(X.Cargo);
    }
    auto Uniq = [](auto& V) {
        std::sort(V.begin(), V.end());
        V.erase(std::unique(V.begin(), V.end()), V.end());
    };
    Uniq(Worlds);
    Uniq(Realms);
    Uniq(Slots);
    Uniq(Cargos);
    std::vector<Question> Cand;
    auto Add = [&](const std::string& Id, auto Pred) {
        Question Q;
        Q.Id = Id;
        for (int I = 0; I < N; ++I)
            if (Pred(S[I])) Q.Yes |= Bit(I);
        Cand.push_back(Q);
    };
    for (const std::string& W : Worlds) Add("world:" + W, [&](const Suspect& X) { return X.World == W; });
    for (const std::string& R : Realms) Add("realm:" + R, [&](const Suspect& X) { return X.Realm == R; });
    for (int K : Slots) Add("slot>=" + std::to_string(K), [&](const Suspect& X) { return X.Slot >= K; });
    for (int K : Cargos) Add("cargo>=" + std::to_string(K), [&](const Suspect& X) { return X.Cargo >= K; });
    Add("empty", [](const Suspect& X) { return X.Cargo == 0; });
    const std::uint64_t Every = N >= 64 ? ~std::uint64_t{0} : Bit(N) - 1;
    std::vector<Question> Out;
    std::unordered_set<std::uint64_t> Seen;
    for (const Question& Q : Cand) {
        if (!Q.Yes || Q.Yes == Every) continue;
        const std::uint64_t Key = (Q.Yes & 1) ? Q.Yes : (Every & ~Q.Yes);  // one name per split
        if (!Seen.insert(Key).second) continue;
        Out.push_back(Q);
    }
    return Out;
}

class Solver {
public:
    explicit Solver(const std::vector<Question>& Q) : Qs(Q) {}
    bool Capped() const { return Cap; }

    int Depth(std::uint64_t Group) {
        if (Bits(Group) <= 1) return 0;
        auto It = Memo.find(Group);
        if (It != Memo.end()) return It->second;
        if (Cap || Memo.size() >= MaxStates) {
            Cap = true;
            return NoSplit;
        }
        int Best = -1;
        for (const Question& Q : Qs) {
            const std::uint64_t A = Group & Q.Yes, B = Group & ~Q.Yes;
            if (A && B) {
                const int Da = Depth(A), Db = Depth(B);
                const int D = 1 + std::max(Da, Db);
                if (Best < 0 || D < Best) Best = D;
            }
        }
        const int R = Best < 0 ? NoSplit : Best;
        Memo.emplace(Group, R);
        return R;
    }

    // best_question(): first question with the smallest depth; -1 if none splits.
    int BestQuestion(std::uint64_t Group) {
        int Pick = -1, BestD = 0;
        for (std::size_t I = 0; I < Qs.size(); ++I) {
            const std::uint64_t A = Group & Qs[I].Yes, B = Group & ~Qs[I].Yes;
            if (A && B) {
                const int D = 1 + std::max(Depth(A), Depth(B));
                if (Pick < 0 || D < BestD) {
                    Pick = static_cast<int>(I);
                    BestD = D;
                }
            }
        }
        return Pick;
    }

private:
    const std::vector<Question>& Qs;
    std::unordered_map<std::uint64_t, int> Memo;
    bool Cap = false;
};

struct Asked {
    std::string Id;
    bool Yes = false;
    int Left = 0;
};
struct Result {
    Error Err = Error::None;
    int Optimal = 0;
    std::vector<Asked> Log;
    std::string Accused;
    std::vector<int> Still;
    Verdict V = Verdict::Escaped;
};

// play(): Auto plays the minimax strategy; otherwise HasAsks/Asks and HasAccuse/Accuse are the
// --ask list and --accuse island (HasAsks with an empty list is an empty --ask).
inline Result Play(const std::vector<Suspect>& S, int Hidden, bool Auto, bool HasAsks, const std::vector<std::string>& Asks,
                   bool HasAccuse, const std::string& Accuse) {
    Result R;
    if (Auto == (HasAsks || HasAccuse)) {
        R.Err = Error::Mode;
        return R;
    }
    if (!Auto && !HasAccuse) {
        R.Err = Error::Accuse;
        return R;
    }
    if (!ValidSuspects(S, Hidden)) {
        R.Err = Error::BadSuspects;
        return R;
    }
    if (Asks.size() > MaxAsks) {
        R.Err = Error::TooLong;
        return R;
    }
    const std::vector<Question> Qs = Questions(S);
    Solver Sv(Qs);
    const int N = static_cast<int>(S.size());
    std::uint64_t Group = N >= 64 ? ~std::uint64_t{0} : Bit(N) - 1;
    R.Optimal = Sv.Depth(Group);
    if (Sv.Capped()) {
        R.Err = Error::Capped;
        return R;
    }
    std::size_t Next = 0;
    while (true) {
        int Q = -1;
        if (Auto) {
            if (Bits(Group) == 1) break;
            Q = Sv.BestQuestion(Group);
            if (Q < 0) {
                R.Err = Error::Stuck;
                return R;
            }
        } else {
            if (Next == Asks.size()) break;
            const std::string& Id = Asks[Next++];
            for (std::size_t I = 0; I < Qs.size() && Q < 0; ++I)
                if (Qs[I].Id == Id) Q = static_cast<int>(I);
            if (Q < 0) {
                R.Err = Error::Question;
                return R;
            }
        }
        const bool Yes = Qs[Q].Yes >> Hidden & 1;
        Group = Yes ? (Group & Qs[Q].Yes) : (Group & ~Qs[Q].Yes);
        R.Log.push_back({Qs[Q].Id, Yes, Bits(Group)});
    }
    if (Sv.Capped()) {
        R.Err = Error::Capped;
        return R;
    }
    if (Auto) {
        R.Accused = S[Lowest(Group)].Label;
    } else {
        bool Known = false;
        for (const Suspect& X : S) Known = Known || X.Label == Accuse;
        if (!Known) {
            R.Err = Error::Island;
            return R;
        }
        R.Accused = Accuse;
    }
    for (int I = 0; I < N; ++I)
        if (Group >> I & 1) R.Still.push_back(I);
    const bool Correct = R.Accused == S[Hidden].Label;
    R.V = !Correct ? Verdict::Escaped : static_cast<int>(R.Log.size()) <= R.Optimal ? Verdict::Sharp : Verdict::Caught;
    return R;
}

}  // namespace SmugglersIsland
}  // namespace DaedalusDiskSaver
