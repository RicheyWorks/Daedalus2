// SPDX-License-Identifier: MIT
// G608 Replay Notary core test: replays every entry in disksaver_replay_notary_parity.txt (written by
// tools/streaming/replay_notary_parity.py from the Python rules of G590, G597 and G598) through
// DaedalusDiskSaverReplayNotaryCore.h and checks the result line, then checks claim, determinism and fuzz
// properties. Framework-free: prints failures and a summary, exits 1 on any failure.
#include "DaedalusDiskSaverReplayNotaryCore.h"

#include <cstdint>
#include <cstdio>
#include <fstream>
#include <string>
#include <vector>

namespace RN = DaedalusDiskSaver::ReplayNotary;

static int Fails = 0, Checks = 0;

static void Check(bool Ok, const std::string& What) {
    ++Checks;
    if (!Ok && Fails++ < 20) std::printf("FAIL %s\n", What.c_str());
}

static bool Unhex(const std::string& H, std::string& Out) {
    Out.clear();
    if (H.size() % 2) return false;
    for (std::size_t I = 0; I < H.size(); I += 2) {
        int V = 0;
        for (int K = 0; K < 2; ++K) {
            const char C = H[I + K];
            V = V * 16 + (C >= '0' && C <= '9' ? C - '0' : C >= 'a' && C <= 'f' ? C - 'a' + 10 : -1000);
        }
        if (V < 0) return false;
        Out += static_cast<char>(V);
    }
    return true;
}

static std::string Head(const std::string& L) { return L.substr(0, L.find(' ')); }

// A result is well formed: its line starts with its status, bad results name a reason, refusals a code.
static bool WellFormed(const RN::Result& R) {
    const std::string L = RN::FormatResult(R);
    switch (R.S) {
        case RN::Status::Bad: return R.Why != RN::Bad::None && Head(L) == "bad";
        case RN::Status::Refused: return !R.Refusal.empty() && Head(L) == "refused";
        case RN::Status::Ok: return R.Claim < 0 || R.Claim == R.Score ? Head(L) == "ok" && R.Score >= 0 : false;
        case RN::Status::Forged: return R.Claim >= 0 && R.Claim != R.Score && Head(L) == "forged";
    }
    return false;
}

// The entry with its claim field replaced.
static std::string WithClaim(const std::string& E, const std::string& C) { return E.substr(0, E.rfind('|') + 1) + C; }

struct XorShift {
    std::uint64_t S;
    std::uint64_t Next() {
        S ^= S << 13;
        S ^= S >> 7;
        S ^= S << 17;
        return S;
    }
    std::size_t Below(std::size_t N) { return static_cast<std::size_t>(Next() % N); }
};

int main(int Argc, char** Argv) {
    const char* Path = Argc > 1 ? Argv[1] : "disksaver_replay_notary_parity.txt";
    std::ifstream In(Path);
    if (!In) {
        std::printf("FAIL cannot open %s\n", Path);
        return 1;
    }
    std::vector<std::string> Entries;
    std::string Line, Entry;
    std::size_t Cases = 0, Scored = 0;
    bool HaveEntry = false;
    while (std::getline(In, Line)) {
        if (!Line.empty() && Line.back() == '\r') Line.pop_back();
        if (Line.empty() || Line[0] == '#') continue;
        if (Line.rfind("E x", 0) == 0) {
            HaveEntry = Unhex(Line.substr(3), Entry);
            Check(HaveEntry, "hex " + Line.substr(0, 60));
            continue;
        }
        if (Line.rfind("R ", 0) == 0 && HaveEntry) {
            ++Cases;
            HaveEntry = false;
            const RN::Result R = RN::Notarise(Entry);
            const std::string Got = RN::FormatResult(R), Want = Line.substr(2);
            Check(Got == Want, "case " + std::to_string(Cases) + ": got '" + Got + "' want '" + Want + "'");
            Check(WellFormed(R), "well formed " + Got);
            Check(RN::FormatResult(RN::Notarise(Entry)) == Got, "deterministic " + Got);
            Entries.push_back(Entry);
            if (R.S == RN::Status::Ok || R.S == RN::Status::Forged) {
                ++Scored;
                // A true claim notarises ok and a false one forged, with the same replayed score and verdict.
                const RN::Result T = RN::Notarise(WithClaim(Entry, std::to_string(R.Score)));
                const RN::Result F = RN::Notarise(WithClaim(Entry, std::to_string(R.Score + 1)));
                const RN::Result N = RN::Notarise(WithClaim(Entry, "-"));
                Check(T.S == RN::Status::Ok && T.Score == R.Score && T.Verdict == R.Verdict, "true claim " + Got);
                Check(F.S == RN::Status::Forged && F.Score == R.Score && F.Claim == R.Score + 1, "false claim " + Got);
                Check(N.S == RN::Status::Ok && RN::FormatResult(N) == RN::FormatResult(T), "no claim " + Got);
            }
            continue;
        }
        Check(false, "unexpected line " + Line.substr(0, 60));
    }
    Check(Cases > 1000 && Scored > 400, "golden has enough cases");
    // Fuzz: mutated golden entries and random bytes never crash and always give a well-formed, repeatable result.
    XorShift X{0x9E3779B97F4A7C15ull};
    const std::string Alphabet = "notary1|gantry-calmberthsgolf0123456789,-/DW579SCPX: \t\x7f\x80";
    std::size_t Fuzz = 0;
    for (int I = 0; I < 1500 && !Entries.empty(); ++I) {
        std::string E = Entries[X.Below(Entries.size())];
        const int Edits = 1 + static_cast<int>(X.Below(4));
        for (int K = 0; K < Edits; ++K) {
            const std::size_t At = E.empty() ? 0 : X.Below(E.size() + 1);
            const char C = Alphabet[X.Below(Alphabet.size())];
            switch (X.Below(4)) {
                case 0: if (At < E.size()) E[At] = C; break;
                case 1: E.insert(E.begin() + static_cast<std::ptrdiff_t>(At), C); break;
                case 2: if (At < E.size()) E.erase(At, 1); break;
                default: E.resize(At); break;
            }
        }
        if (X.Below(10) == 0) {
            E.clear();
            const std::size_t N = X.Below(64);
            for (std::size_t K = 0; K < N; ++K) E += static_cast<char>(X.Below(256));
        }
        const RN::Result R = RN::Notarise(E);
        Check(WellFormed(R), "fuzz well formed " + RN::FormatResult(R));
        Check(RN::FormatResult(RN::Notarise(E)) == RN::FormatResult(R), "fuzz deterministic");
        ++Fuzz;
    }
    std::printf("disksaver_replay_notary_core_test: %zu cases (%zu scored), %zu fuzz entries, %d checks, %d failures\n",
                Cases, Scored, Fuzz, Checks, Fails);
    return Fails ? 1 : 0;
}
