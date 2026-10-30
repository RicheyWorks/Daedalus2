// SPDX-License-Identifier: MIT
// G581 seed spec check: DaedalusDiskSaverSeedSpecCore.h replays disksaver_seed_spec_parity.txt
// (written from CPython's random.Random and checked against a pure-Python reference by
// tools/streaming/disksaver_seed_spec.py): each case seeds, then every `D op` must give its `O` line.
#include "DaedalusDiskSaverSeedSpecCore.h"
#include "disksaver_parity.h"

#include <cstddef>
#include <cstdint>
#include <string>
#include <vector>

using namespace DiskSaverParity;
namespace SS = DaedalusDiskSaver::SeedSpec;

static std::string Rest(const std::vector<std::string>& T, std::size_t From) {
    std::string S;
    for (std::size_t I = From; I < T.size(); ++I) S += (I > From ? " " : "") + T[I];
    return S;
}

static void Compare(const std::string& Case, const std::vector<std::string>& Got, const std::vector<std::string>& Want) {
    if (Got == Want) return;
    std::size_t I = 0;
    while (I < Got.size() && I < Want.size() && Got[I] == Want[I]) ++I;
    Check(false, Case + ": output line " + std::to_string(I) + " got '" + (I < Got.size() ? Got[I] : "<end>") + "' want '" +
                     (I < Want.size() ? Want[I] : "<end>") + "'");
}

static bool ToI64(const std::string& S, std::int64_t& Out) {
    std::size_t I = 0;
    const bool Neg = !S.empty() && S[0] == '-';
    if (Neg) I = 1;
    if (I >= S.size() || S.size() - I > 19) return false;
    std::uint64_t V = 0;
    for (; I < S.size(); ++I) {
        if (S[I] < '0' || S[I] > '9') return false;
        const std::uint64_t D = static_cast<std::uint64_t>(S[I] - '0');
        if (V > (UINT64_C(9223372036854775807) - D) / 10) return false;
        V = V * 10 + D;
    }
    Out = Neg ? -static_cast<std::int64_t>(V) : static_cast<std::int64_t>(V);
    return true;
}

// Hex magnitude (optional '-') -> 32-bit limbs, least significant first.
static bool SeedWords(const std::string& S, std::vector<std::uint32_t>& W) {
    W.clear();
    std::size_t B = (!S.empty() && S[0] == '-') ? 1 : 0;
    if (B >= S.size() || S.size() - B > 8 * SS::MaxSeedWords) return false;
    std::size_t End = S.size();
    while (End > B) {
        const std::size_t Start = End - B >= 8 ? End - 8 : B;
        std::uint32_t V = 0;
        for (std::size_t I = Start; I < End; ++I) {
            const char C = S[I];
            const int D = C >= '0' && C <= '9' ? C - '0' : C >= 'a' && C <= 'f' ? C - 'a' + 10 : -1;
            if (D < 0) return false;
            V = (V << 4) | static_cast<std::uint32_t>(D);
        }
        W.push_back(V);
        End = Start;
    }
    return true;
}

static std::string JoinU(const std::vector<std::uint64_t>& V) {
    std::string S;
    for (std::size_t I = 0; I < V.size(); ++I) S += (I ? " " : "") + std::to_string(V[I]);
    return S;
}

static const std::string Err = "error ValueError", IdxErr = "error IndexError";

// One op's result text; Ok=false when the line itself is malformed.
static std::string Run(SS::Mt19937& R, const std::vector<std::string>& T, bool& Ok) {
    std::vector<std::int64_t> A;
    for (std::size_t I = 2; I < T.size(); ++I) {
        std::int64_t V = 0;
        if (!ToI64(T[I], V)) {
            Ok = false;
            return "";
        }
        A.push_back(V);
    }
    const std::string& Op = T[1];
    auto Need = [&](std::size_t N) {
        if (A.size() != N) Ok = false;
        return A.size() == N;
    };
    std::vector<std::uint64_t> L;
    std::uint64_t U = 0;
    std::int64_t S = 0;
    if (Op == "u32" && Need(0)) return std::to_string(R.U32());
    if (Op == "random" && Need(0)) return std::to_string(R.Random53());
    if (Op == "bits" && Need(1)) {
        if (A[0] < 0) return Err;
        if (A[0] > 64) {
            Ok = false;
            return "";
        }
        return std::to_string(R.Bits(static_cast<int>(A[0])));
    }
    if (Op == "below" && Need(1)) return A[0] <= 0 ? Err : std::to_string(R.Below(static_cast<std::uint64_t>(A[0])));
    if (Op == "range" && Need(3)) return R.RandRange(A[0], A[1], A[2], S) ? std::to_string(S) : Err;
    if (Op == "int" && Need(2)) return R.RandInt(A[0], A[1], S) ? std::to_string(S) : Err;
    if (Op == "choice" && Need(1)) {
        if (A[0] <= 0) return IdxErr;
        return R.Choice(static_cast<std::uint64_t>(A[0]), U) ? std::to_string(U) : Err;
    }
    if (Op == "shuffle" && Need(1)) {
        if (A[0] < 0 || !R.Shuffle(static_cast<std::uint64_t>(A[0]), L)) {
            Ok = false;
            return "";
        }
        return JoinU(L);
    }
    if (Op == "sample" && Need(2)) {
        if (A[0] < 0 || A[1] < 0) return Err;
        return R.Sample(static_cast<std::uint64_t>(A[0]), static_cast<std::uint64_t>(A[1]), L) ? JoinU(L) : Err;
    }
    if (Op == "skip" && Need(1)) {
        if (A[0] < 0 || A[0] > 10000000) {
            Ok = false;
            return "";
        }
        std::uint32_t Last = 0;
        for (std::int64_t I = 0; I < A[0]; ++I) Last = R.U32();
        return std::to_string(Last);
    }
    Ok = false;
    return "";
}

struct Case {
    std::string Name;
    bool Open = false, Ok = true, Seeded = false;
    SS::Mt19937 R;
    std::vector<std::string> Got, Want;
};

static int Plays = 0, Draws = 0;

static void Flush(Case& K) {
    if (!K.Open) return;
    K.Open = false;
    Check(K.Ok && K.Seeded, K.Name + ": input lines");
    if (!K.Ok || !K.Seeded) return;
    Compare(K.Name, K.Got, K.Want);
    ++Plays;
}

int main(int argc, char** argv) {
    int Cases = 0;
    Case* K = new Case;  // Mt19937 state is 2.5 KiB; keep it off the stack
    for (const auto& T : ReadLines(argc > 1 ? argv[1] : "disksaver_seed_spec_parity.txt")) {
        if (T[0] == "C" && T.size() == 2) {
            Flush(*K);
            delete K;
            K = new Case;
            K->Name = T[1];
            K->Open = true;
            ++Cases;
            continue;
        }
        if (!K->Open) {
            Check(false, "line before the first case: " + T[0]);
            continue;
        }
        if (T[0] == "K") {
            continue;  // sha256 key bytes: checked on the Python side
        } else if (T[0] == "S" && T.size() == 2 && !K->Seeded) {
            std::vector<std::uint32_t> W;
            K->Ok = SeedWords(T[1], W) && K->R.Seed(W) && K->Ok;
            K->Seeded = true;
        } else if (T[0] == "D" && T.size() >= 2 && K->Seeded) {
            K->Got.push_back(Run(K->R, T, K->Ok));
            ++Draws;
        } else if (T[0] == "O") {
            K->Want.push_back(Rest(T, 1));
        } else {
            K->Ok = false;
            Check(false, K->Name + ": unknown line " + T[0]);
        }
    }
    Flush(*K);
    delete K;
    Check(Draws > 1000, "seed spec draws replayed");
    return Finish("seed_spec", Cases, Plays);
}
