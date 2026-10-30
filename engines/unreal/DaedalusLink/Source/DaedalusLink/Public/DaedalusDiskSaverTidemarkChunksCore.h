// SPDX-License-Identifier: MIT
// G175 Tidemark Chunks core, header-only C++17 port of tools/streaming/tidemark_chunks.py (G578 batch 6).
// The seeded save history comes from Python's random, so the core replays the tool's recorded draws
// (randrange/randint results in call order, carried in the golden file) through the ported edit
// rules to rebuild every save byte for byte. Ported: config range checks (locked window/mask), the
// polynomial window hash and its rolling form, the whole/fixed/content-defined chunkers, the
// inserted/deleted/overwritten runs, and the vault cost and status. The vault dedupes chunks by
// their bytes (the tool's cost_oracle); the tool keys by sha256, which gives the same count unless
// sha256 collides. Left in Python: the JSON config schema and npc lines, the G86 shoals and G39
// byte-spring file reads and the CLI. Engine-free: no Unreal includes, no exceptions, no RTTI.
// Saves stop at MaxBytes bytes in total.
#pragma once

#include <algorithm>
#include <cstdint>
#include <string>
#include <unordered_set>
#include <vector>

namespace DaedalusDiskSaver {
namespace TidemarkChunks {

constexpr std::uint64_t Base = 257;
constexpr std::uint64_t Prime = 2147483647;  // 2**31 - 1
constexpr long long Window = 16, MaskBits = 7;  // locked chunker (G175 approval 50444)
constexpr std::size_t MaxBytes = 64u << 20;
constexpr std::size_t MaxIslands = 1000;
enum class Error { None, BadConfig, Capped, Tape };
enum class Mode { Whole, Fixed, Cdc };

inline const char* ErrorName(Error E) {
    switch (E) {
        case Error::None: return "none";
        case Error::BadConfig: return "config";
        case Error::Capped: return "capped";
        case Error::Tape: return "tape";
    }
    return "?";
}

struct Config {
    std::vector<long long> Weights;  // one save per G86 island
    long long Versions = 0, BytesPerWeight = 0, Edits = 0, MaxRun = 0, InsertPermille = 0, DeletePermille = 0, WindowBytes = 0,
              Mask = 0, MinChunk = 0, MaxChunk = 0, FixedSize = 0, RefBytes = 0, Quota = 0, ByteUnit = 1;
};

// validate()'s numeric rules.
inline bool ValidConfig(const Config& C) {
    auto In = [](long long V, long long Lo, long long Hi) { return V >= Lo && V <= Hi; };
    if (C.Weights.empty() || C.Weights.size() > MaxIslands) return false;
    for (long long W : C.Weights)
        if (W < 0 || W > 1000000) return false;
    return In(C.InsertPermille, 0, 1000) && In(C.DeletePermille, 0, 1000 - C.InsertPermille) && In(C.WindowBytes, 2, 64) &&
           C.WindowBytes == Window && C.Mask == MaskBits && In(C.MinChunk, 1, 1 << 16) && In(C.MaxChunk, C.MinChunk, 1 << 20) &&
           In(C.ByteUnit, 1, 1 << 20) && In(C.Versions, 1, 1000) && In(C.BytesPerWeight, 1, 1 << 16) && In(C.Edits, 0, 1000) &&
           In(C.MaxRun, 1, 1 << 12) && In(C.FixedSize, 1, 1 << 20) && In(C.RefBytes, 0, 1024) && C.Quota >= 0;
}

// window_hash(): oldest byte has the highest power.
inline std::uint64_t WindowHash(const std::string& W) {
    std::uint64_t H = 0;
    for (unsigned char B : W) H = (H * Base + B + 1) % Prime;
    return H;
}

using Chunks = std::vector<std::string>;

// chunk_cdc(): cut after byte i when the rolling hash's low bits are zero, within the size limits.
inline Chunks ChunkCdc(const std::string& D, long long Win, long long Bits, long long Min, long long Max) {
    Chunks Out;
    if (Win < 1 || Win > 64 || Bits < 0 || Bits > 30 || Min < 1 || Max < 1) return Out;
    const std::uint64_t MaskV = (std::uint64_t{1} << Bits) - 1;
    std::uint64_t Top = 1;
    for (long long K = 0; K < Win - 1; ++K) Top = Top * Base % Prime;
    std::uint64_t H = 0;
    std::size_t Start = 0;
    for (std::size_t I = 0; I < D.size(); ++I) {
        if (I >= static_cast<std::size_t>(Win)) {
            const std::uint64_t Old = (static_cast<unsigned char>(D[I - Win]) + 1) * Top % Prime;
            H = (H + Prime - Old) % Prime;
        }
        H = (H * Base + static_cast<unsigned char>(D[I]) + 1) % Prime;
        const long long Size = static_cast<long long>(I + 1 - Start);
        const bool HasHash = I + 1 >= static_cast<std::size_t>(Win);
        if (Size >= Max || (Size >= Min && HasHash && (H & MaskV) == 0)) {
            Out.push_back(D.substr(Start, I + 1 - Start));
            Start = I + 1;
        }
    }
    if (Start < D.size()) Out.push_back(D.substr(Start));
    return Out;
}

inline Chunks Chunk(const std::string& D, const Config& C, Mode M) {
    if (M == Mode::Whole) return D.empty() ? Chunks{} : Chunks{D};
    if (M == Mode::Fixed) {
        Chunks Out;
        const std::size_t S = C.FixedSize < 1 ? 1 : static_cast<std::size_t>(C.FixedSize);
        for (std::size_t I = 0; I < D.size(); I += S) Out.push_back(D.substr(I, S));
        return Out;
    }
    return ChunkCdc(D, C.WindowBytes, C.Mask, C.MinChunk, C.MaxChunk);
}

class Tape {
public:
    explicit Tape(const std::vector<long long>& V) : Vals(V) {}
    long long Next(long long Lo, long long Hi) {
        if (Bad || Pos >= Vals.size() || Vals[Pos] < Lo || Vals[Pos] > Hi) {
            Bad = true;
            return Lo;
        }
        return Vals[Pos++];
    }
    bool Ok() const { return !Bad && Pos == Vals.size(); }
    bool Failed() const { return Bad; }

private:
    const std::vector<long long>& Vals;
    std::size_t Pos = 0;
    bool Bad = false;
};

// saves(): History[v][k] is island k's save at version v.
inline Error Saves(const Config& C, const std::vector<long long>& Draws, std::vector<std::vector<std::string>>& History) {
    if (!ValidConfig(C)) return Error::BadConfig;
    Tape T(Draws);
    std::size_t Total = 0;
    std::vector<std::string> Cur;
    for (long long W : C.Weights) {
        const long long Len = W * C.BytesPerWeight;
        if (static_cast<std::size_t>(Len) > MaxBytes) return Error::Capped;
        std::string S;
        for (long long K = 0; K < Len && !T.Failed(); ++K) S += static_cast<char>(T.Next(0, 255));
        Cur.push_back(S);
        Total += S.size();
    }
    History.assign(1, Cur);
    for (long long V = 1; V < C.Versions && !T.Failed(); ++V) {
        for (std::string& B : Cur) {
            const long long Count = T.Next(0, C.Edits);
            for (long long E = 0; E < Count && !T.Failed(); ++E) {
                const long long Run = T.Next(1, C.MaxRun);
                long long Pos = T.Next(0, static_cast<long long>(B.size()));
                const long long Roll = T.Next(0, 999);
                if (Roll < C.InsertPermille || B.empty()) {
                    std::string Ins;
                    for (long long K = 0; K < Run && !T.Failed(); ++K) Ins += static_cast<char>(T.Next(0, 255));
                    B.insert(static_cast<std::size_t>(Pos), Ins);
                } else if (Roll < C.InsertPermille + C.DeletePermille) {
                    B.erase(static_cast<std::size_t>(Pos), static_cast<std::size_t>(Run));
                } else {
                    Pos = std::min(Pos, static_cast<long long>(B.size()) - 1);
                    const long long End = std::min(static_cast<long long>(B.size()), Pos + Run);
                    for (long long K = Pos; K < End && !T.Failed(); ++K) B[static_cast<std::size_t>(K)] = static_cast<char>(T.Next(0, 255));
                }
                if (B.size() > MaxBytes) return Error::Capped;
            }
        }
        for (const std::string& B : Cur) Total += B.size();
        if (Total > MaxBytes) return Error::Capped;
        History.push_back(Cur);
    }
    return T.Ok() ? Error::None : Error::Tape;
}

struct Result {
    Error Err = Error::None;
    long long Raw = 0, Refs = 0, Unique = 0, Stored = 0, Cost = 0;
    bool Won = false;
};

// run(): vault cost of every version's chunk recipes.
inline Result Run(const Config& C, Mode M, const std::vector<std::vector<std::string>>& History) {
    Result R;
    if (!ValidConfig(C)) {
        R.Err = Error::BadConfig;
        return R;
    }
    std::unordered_set<std::string> Store;
    for (const auto& Ver : History)
        for (const std::string& S : Ver) {
            R.Raw += static_cast<long long>(S.size());
            for (const std::string& Ch : Chunk(S, C, M)) {
                ++R.Refs;
                if (Store.insert(Ch).second) R.Stored += static_cast<long long>(Ch.size());
            }
        }
    R.Unique = static_cast<long long>(Store.size());
    R.Cost = R.Stored + C.RefBytes * (R.Unique + R.Refs);
    R.Won = R.Cost <= C.Quota;
    return R;
}

}  // namespace TidemarkChunks
}  // namespace DaedalusDiskSaver
