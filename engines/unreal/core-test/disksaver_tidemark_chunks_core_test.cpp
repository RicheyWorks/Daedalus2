// SPDX-License-Identifier: MIT
// G175 port check: DaedalusDiskSaverTidemarkChunksCore.h replays disksaver_tidemark_chunks_parity.txt
// (written from tidemark_chunks.py by tools/streaming/disksaver_cpp_parity.py, recorded draws included) line for line.
#include <algorithm>
#include "DaedalusDiskSaverTidemarkChunksCore.h"
#include "disksaver_parity.h"

namespace TM = DaedalusDiskSaver::TidemarkChunks;
using namespace DiskSaverParity;

// Signed decimal lists for the recorded tapes: optional '-', then up to 18 strict digits, no leading zeros.
static bool ToLong(const std::string& S, long long& Out) {
    const bool Neg = !S.empty() && S[0] == '-';
    const std::string D = Neg ? S.substr(1) : S;
    if (D.empty() || D.size() > 18 || (D.size() > 1 && D[0] == '0') || (Neg && D == "0")) return false;
    long long V = 0;
    for (char Ch : D) {
        if (Ch < '0' || Ch > '9') return false;
        V = V * 10 + (Ch - '0');
    }
    Out = Neg ? -V : V;
    return true;
}
static std::vector<long long> Longs(const std::string& S, bool& Ok) {
    std::vector<long long> Out;
    for (const std::string& T : Split(S, ',')) {
        long long V = 0;
        Ok = ToLong(T, V) && Ok;
        Out.push_back(V);
    }
    return Out;
}
static std::string JoinL(const std::vector<long long>& V) {
    std::string S;
    for (std::size_t I = 0; I < V.size(); ++I) S += (I ? "," : "") + std::to_string(V[I]);
    return S.empty() ? "-" : S;
}

static bool Unhex(const std::string& S, std::string& Out) {
    if (S.empty() || S[0] != 'x' || S.size() % 2 == 0) return false;
    Out.clear();
    auto Nib = [](char C) { return C >= '0' && C <= '9' ? C - '0' : C >= 'a' && C <= 'f' ? C - 'a' + 10 : -1; };
    for (std::size_t I = 1; I < S.size(); I += 2) {
        const int A = Nib(S[I]), B = Nib(S[I + 1]);
        if (A < 0 || B < 0) return false;
        Out += static_cast<char>(A * 16 + B);
    }
    return true;
}

static bool ParseConfig(const std::vector<std::string>& T, TM::Config& X, bool WithUnit) {
    bool Ok = T.size() == (WithUnit ? 16u : 15u);
    if (!Ok) return false;
    X.Weights = Longs(T[1], Ok);
    Ok = Ok && ToLong(T[2], X.Versions) && ToLong(T[3], X.BytesPerWeight) && ToLong(T[4], X.Edits) && ToLong(T[5], X.MaxRun) &&
         ToLong(T[6], X.InsertPermille) && ToLong(T[7], X.DeletePermille) && ToLong(T[8], X.WindowBytes) && ToLong(T[9], X.Mask) &&
         ToLong(T[10], X.MinChunk) && ToLong(T[11], X.MaxChunk) && ToLong(T[12], X.FixedSize) && ToLong(T[13], X.RefBytes) &&
         ToLong(T[14], X.Quota);
    if (WithUnit) Ok = Ok && ToLong(T[15], X.ByteUnit);
    return Ok;
}

int main(int argc, char** argv) {
    const std::string D(5000, 'a');
    for (const std::string& Ch : TM::ChunkCdc(D, 16, 7, 32, 1024)) Check(Ch.size() <= 1024, "cdc respects max_chunk");
    std::string Back;
    for (const std::string& Ch : TM::ChunkCdc(D, 16, 7, 32, 1024)) Back += Ch;
    Check(Back == D, "cdc chunks rebuild the save");
    TM::Config C;
    std::vector<std::vector<std::string>> Hist;
    Check(TM::Saves(C, {}, Hist) == TM::Error::BadConfig, "empty config refused");

    std::string Case;
    int Cases = 0, Trials = 0;
    TM::Config Base;
    bool Built = false;
    std::vector<std::string> BaseTokens;
    bool SeenLayout = false;
    long long BudgetCap = 0;
    for (const auto& T : ReadLines(argc > 1 ? argv[1] : "disksaver_tidemark_chunks_parity.txt")) {
        const std::string Line = Case + ":" + T[0] + (T.size() > 1 ? " " + T[1] : "");
        if (T[0] == "B") {
            BaseTokens.assign(T.begin() + 1, T.end());
            SeenLayout = false;
        } else if (T[0] == "L" && !SeenLayout) {
            SeenLayout = true;
            Check(BaseTokens.size() + 1 >= T.size() && std::equal(T.begin() + 1, T.end(), BaseTokens.begin()),
                  Line + " first layout must be the B base config");
        }
        if (T[0] == "S") {
            Check(T.size() == 2 && ToLong(T[1], BudgetCap) && BudgetCap > 0 && BudgetCap <= (1LL << 40), Line + " budget cap");
            continue;
        }
        bool Ok = true;
        if (T[0] == "H" && T.size() == 3) {
            std::string W;
            long long H = -1;
            Check(Unhex(T[1], W) && ToLong(T[2], H) && TM::WindowHash(W) == static_cast<std::uint64_t>(H), Line + " hash");
        } else if (T[0] == "B") {
            Check(ParseConfig(T, Base, true), Line + " config");
            Check(BudgetCap > 0 && Base.ByteUnit <= (1 << 20) && Base.Quota == BudgetCap * Base.ByteUnit, Line + " quota is budget cap times byte_unit");
        } else if (T[0] == "L") {
            C = TM::Config{};
            Check(ParseConfig(T, C, false), Line + " config");
        } else if (T[0] == "V" && T.size() == 4) {
            TM::Config X = Base;
            long long V = 0;
            Check(ToLong(T[2], V), Line + " value");
            const std::string& F = T[1];
            if (F == "versions") X.Versions = V;
            else if (F == "insert_permille") X.InsertPermille = V;
            else if (F == "delete_permille") X.DeletePermille = V;
            else if (F == "window") X.WindowBytes = V;
            else if (F == "mask_bits") X.Mask = V;
            else if (F == "min_chunk") X.MinChunk = V;
            else if (F == "max_chunk") X.MaxChunk = V;
            else if (F == "fixed_size") X.FixedSize = V;
            else if (F == "ref_bytes") X.RefBytes = V;
            else if (F == "byte_unit") X.ByteUnit = V;
            else if (F == "edits") X.Edits = V;
            else if (F == "max_run") X.MaxRun = V;
            else if (F == "bytes_per_weight") X.BytesPerWeight = V;
            else Check(false, Line + " field");
            Check((TM::ValidConfig(X) ? "ok" : "err") == T[3], Line + " validate");
        } else if (T[0] == "C" && T.size() == 2) {
            Case = T[1];
            ++Cases;
        } else if (T[0] == "R" && T.size() == 2) {
            const std::vector<long long> Draws = Longs(T[1], Ok);
            Built = Ok && TM::Saves(C, Draws, Hist) == TM::Error::None;
            Check(Built, Line + " saves from the tape");
        } else if (T[0] == "T" && T.size() == 10) {
            ++Trials;
            Check(Built, Line + " run without saves");
            const TM::Mode M = T[1] == "whole" ? TM::Mode::Whole : T[1] == "fixed" ? TM::Mode::Fixed : TM::Mode::Cdc;
            const TM::Result R = TM::Run(C, M, Built ? Hist : std::vector<std::vector<std::string>>{});
            std::vector<long long> Sizes;
            if (Built && !Hist.empty() && !Hist.back().empty())
                for (const std::string& Ch : TM::Chunk(Hist.back()[0], C, M)) Sizes.push_back(static_cast<long long>(Ch.size()));
            const std::string Got = std::to_string(R.Raw) + " " + std::to_string(R.Refs) + " " + std::to_string(R.Unique) + " " +
                                    std::to_string(R.Stored) + " " + std::to_string(R.Cost) + " " + std::to_string(R.Cost) + " " +
                                    (R.Won ? "won" : "failed") + " " + JoinL(Sizes);
            const std::string Want = T[2] + " " + T[3] + " " + T[4] + " " + T[5] + " " + T[6] + " " + T[7] + " " + T[8] + " " + T[9];
            Check(R.Err == TM::Error::None && Got == Want, Line + " " + T[1] + " got " + Got);
        } else {
            Check(false, "unknown line " + Line);
        }
    }
    Check(!BaseTokens.empty() && SeenLayout, "base config and layouts present");
    return Finish("tidemark_chunks", Cases, Trials);
}
