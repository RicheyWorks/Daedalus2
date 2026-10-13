// SPDX-License-Identifier: MIT
//
// DaedalusMeshCore.h — the Daedalus cube mesher with no engine in it (ADR-032).
//
// The same rules as com.daedalus.world.export.WorldMesher and the web realm, line for line:
//   * a face is drawn when the cube beyond it is see-through and not the same type;
//   * faces are shaded +X/-X 0.86, +Y 1.00, -Y 0.62, +Z 0.94, -Z 0.78, times the per-cube grain;
//   * colours are linear RGB (sRGB decoded), clamped to 0..1;
//   * opaque and translucent cubes go to separate parts;
//   * coordinates are Daedalus/glTF: metres, +Y up, right-handed, counter-clockwise from outside.
//
// Standard C++17 only, so it compiles in Unreal, Godot GDExtension, a command-line tool or the parity test
// in engines/unreal/core-test, which checks it against the Java mesher's output for the same cubes.

#pragma once

#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <string>
#include <unordered_map>
#include <vector>

namespace daedalus
{

constexpr int ChunkSize = 16;
constexpr int ChunkVolume = ChunkSize * ChunkSize * ChunkSize;

/** One cube type: colour and how light passes it. Index = the byte in a chunk payload. */
struct CubeType
{
    std::string Name;
    uint32_t Rgb = 0x888888;
    bool bTranslucent = false;
    bool bSeeThrough = false;
};

/** Every cube type in ordinal order; byte 0 is always AIR. */
struct Palette
{
    std::vector<CubeType> Types;

    const CubeType& Of(uint8_t Ordinal) const
    {
        static const CubeType Air{"AIR", 0, false, true};
        return Ordinal < Types.size() ? Types[Ordinal] : Air;
    }
};

/** One drawable part: 3 floats per vertex for positions, normals and colours; 6 indices per face. */
struct Part
{
    std::vector<float> Positions;
    std::vector<float> Normals;
    std::vector<float> Colors;
    std::vector<uint32_t> Indices;

    int VertexCount() const { return static_cast<int>(Positions.size() / 3); }
    int FaceCount() const { return static_cast<int>(Indices.size() / 6); }
    bool IsEmpty() const { return Indices.empty(); }
};

struct ChunkKey
{
    int X = 0, Y = 0, Z = 0;
    bool operator==(const ChunkKey& O) const { return X == O.X && Y == O.Y && Z == O.Z; }
};

struct ChunkKeyHash
{
    size_t operator()(const ChunkKey& K) const
    {
        return (static_cast<size_t>(static_cast<uint32_t>(K.X)) * 73856093u)
             ^ (static_cast<size_t>(static_cast<uint32_t>(K.Y)) * 19349663u)
             ^ (static_cast<size_t>(static_cast<uint32_t>(K.Z)) * 83492791u);
    }
};

inline int FloorDiv(int A, int B) { return (A >= 0) ? A / B : -((-A + B - 1) / B); }

/** The world's cubes, chunk by chunk: index = x + 16 * (y + 16 * z), as /chunk/blocks sends them. */
class ChunkStore
{
public:
    using Cubes = std::array<uint8_t, ChunkVolume>;

    void Put(const ChunkKey& K, const Cubes& C) { Chunks[K] = C; }
    void Drop(const ChunkKey& K) { Chunks.erase(K); }
    const Cubes* Find(const ChunkKey& K) const
    {
        auto It = Chunks.find(K);
        return It == Chunks.end() ? nullptr : &It->second;
    }
    const std::unordered_map<ChunkKey, Cubes, ChunkKeyHash>& All() const { return Chunks; }

    uint8_t Get(int X, int Y, int Z) const
    {
        const Cubes* C = Find({FloorDiv(X, ChunkSize), FloorDiv(Y, ChunkSize), FloorDiv(Z, ChunkSize)});
        if (!C) return 0;
        const int Lx = X - FloorDiv(X, ChunkSize) * ChunkSize;
        const int Ly = Y - FloorDiv(Y, ChunkSize) * ChunkSize;
        const int Lz = Z - FloorDiv(Z, ChunkSize) * ChunkSize;
        return (*C)[Lx + ChunkSize * (Ly + ChunkSize * Lz)];
    }

    /** Set one cube (live block frames); clearing a cube in a chunk that is not loaded does nothing. */
    void Set(int X, int Y, int Z, uint8_t Type)
    {
        const ChunkKey K{FloorDiv(X, ChunkSize), FloorDiv(Y, ChunkSize), FloorDiv(Z, ChunkSize)};
        auto It = Chunks.find(K);
        if (It == Chunks.end())
        {
            if (Type == 0) return;
            It = Chunks.emplace(K, Cubes{}).first;
        }
        const int Lx = X - K.X * ChunkSize, Ly = Y - K.Y * ChunkSize, Lz = Z - K.Z * ChunkSize;
        It->second[Lx + ChunkSize * (Ly + ChunkSize * Lz)] = Type;
    }

private:
    std::unordered_map<ChunkKey, Cubes, ChunkKeyHash> Chunks;
};

/** The realm's per-cube brightness, 0.94..1.06: Java int arithmetic reproduced with uint32 wrap-around. */
inline double Jitter(int X, int Y, int Z)
{
    uint32_t H = static_cast<uint32_t>(X) * 374761393u + static_cast<uint32_t>(Y) * 668265263u
               + static_cast<uint32_t>(Z) * 2147483647u;
    H = (H ^ (H >> 13)) * 1274126177u;
    const uint64_t U = static_cast<uint64_t>(H ^ (H >> 16));
    return 0.94 + static_cast<double>(U % 1000) / 1000.0 * 0.12;
}

inline double SrgbToLinear(int C)
{
    const double V = C / 255.0;
    return V < 0.04045 ? V / 12.92 : std::pow((V + 0.055) / 1.055, 2.4);
}

inline float Clamp01(double V) { return static_cast<float>(V < 0.0 ? 0.0 : (V > 1.0 ? 1.0 : V)); }

/** Mesh one chunk into an opaque and a translucent part, reading neighbours across chunk edges. */
inline void MeshChunk(const ChunkStore& Store, const Palette& Pal, const ChunkKey& At, Part& Opaque, Part& Translucent)
{
    static const int N[6][3] = {{1, 0, 0}, {-1, 0, 0}, {0, 1, 0}, {0, -1, 0}, {0, 0, 1}, {0, 0, -1}};
    static const double Shade[6] = {0.86, 0.86, 1.0, 0.62, 0.94, 0.78};
    static const int Corner[6][4][3] = {
        {{1, 0, 0}, {1, 1, 0}, {1, 1, 1}, {1, 0, 1}},
        {{0, 0, 1}, {0, 1, 1}, {0, 1, 0}, {0, 0, 0}},
        {{0, 1, 1}, {1, 1, 1}, {1, 1, 0}, {0, 1, 0}},
        {{0, 0, 0}, {1, 0, 0}, {1, 0, 1}, {0, 0, 1}},
        {{1, 0, 1}, {1, 1, 1}, {0, 1, 1}, {0, 0, 1}},
        {{0, 0, 0}, {0, 1, 0}, {1, 1, 0}, {1, 0, 0}},
    };
    const ChunkStore::Cubes* Cubes = Store.Find(At);
    if (!Cubes) return;
    const int Ox = At.X * ChunkSize, Oy = At.Y * ChunkSize, Oz = At.Z * ChunkSize;
    for (int I = 0; I < ChunkVolume; ++I)
    {
        const uint8_t T = (*Cubes)[I];
        if (T == 0) continue;
        const int X = Ox + I % ChunkSize;
        const int Y = Oy + (I / ChunkSize) % ChunkSize;
        const int Z = Oz + I / (ChunkSize * ChunkSize);
        const CubeType& Type = Pal.Of(T);
        Part& P = Type.bTranslucent ? Translucent : Opaque;
        const double Lin[3] = {SrgbToLinear((Type.Rgb >> 16) & 255), SrgbToLinear((Type.Rgb >> 8) & 255),
                               SrgbToLinear(Type.Rgb & 255)};
        // Java keeps the decoded colour as a float before shading; so do we, to the last bit.
        const float LinF[3] = {static_cast<float>(Lin[0]), static_cast<float>(Lin[1]), static_cast<float>(Lin[2])};
        for (int F = 0; F < 6; ++F)
        {
            const uint8_t Nb = Store.Get(X + N[F][0], Y + N[F][1], Z + N[F][2]);
            if (!Pal.Of(Nb).bSeeThrough || Nb == T) continue;
            const double S = Shade[F] * Jitter(X, Y, Z);
            const uint32_t Base = static_cast<uint32_t>(P.VertexCount());
            for (int C = 0; C < 4; ++C)
            {
                P.Positions.insert(P.Positions.end(), {static_cast<float>(X + Corner[F][C][0]),
                    static_cast<float>(Y + Corner[F][C][1]), static_cast<float>(Z + Corner[F][C][2])});
                P.Normals.insert(P.Normals.end(), {static_cast<float>(N[F][0]), static_cast<float>(N[F][1]),
                    static_cast<float>(N[F][2])});
                P.Colors.insert(P.Colors.end(), {Clamp01(LinF[0] * S), Clamp01(LinF[1] * S), Clamp01(LinF[2] * S)});
            }
            P.Indices.insert(P.Indices.end(), {Base, Base + 1, Base + 2, Base, Base + 2, Base + 3});
        }
    }
}

/**
 * MeshChunk's faces merged into rectangles: per face direction and slice, runs of one cube type become one quad
 * (ADR-064 rule 3, one greedy mesh per chunk). No per-cube grain (that is what made every face unique), so far fewer
 * vertices. Same order, positions, colours and winding as Java's WorldMesher.meshGreedy, to the last bit.
 */
inline void MeshChunkGreedy(const ChunkStore& Store, const Palette& Pal, const ChunkKey& At, Part& Opaque, Part& Translucent)
{
    static const int N[6][3] = {{1, 0, 0}, {-1, 0, 0}, {0, 1, 0}, {0, -1, 0}, {0, 0, 1}, {0, 0, -1}};
    static const double Shade[6] = {0.86, 0.86, 1.0, 0.62, 0.94, 0.78};
    static const int Corner[6][4][3] = {
        {{1, 0, 0}, {1, 1, 0}, {1, 1, 1}, {1, 0, 1}},
        {{0, 0, 1}, {0, 1, 1}, {0, 1, 0}, {0, 0, 0}},
        {{0, 1, 1}, {1, 1, 1}, {1, 1, 0}, {0, 1, 0}},
        {{0, 0, 0}, {1, 0, 0}, {1, 0, 1}, {0, 0, 1}},
        {{1, 0, 1}, {1, 1, 1}, {0, 1, 1}, {0, 0, 1}},
        {{0, 0, 0}, {0, 1, 0}, {1, 1, 0}, {1, 0, 0}},
    };
    const ChunkStore::Cubes* Cubes = Store.Find(At);
    if (!Cubes) return;
    const int S = ChunkSize;
    const int Origin[3] = {At.X * S, At.Y * S, At.Z * S};
    int Mask[ChunkSize * ChunkSize];
    for (int F = 0; F < 6; ++F)
    {
        const int* Nf = N[F];
        const int D = Nf[0] != 0 ? 0 : Nf[1] != 0 ? 1 : 2;
        const int U = D == 0 ? 1 : 0;
        const int V = D == 2 ? 1 : 2;
        for (int K = 0; K < S; ++K)
        {
            for (int VV = 0; VV < S; ++VV)
                for (int UU = 0; UU < S; ++UU)
                {
                    int L[3];
                    L[D] = K;
                    L[U] = UU;
                    L[V] = VV;
                    const uint8_t T = (*Cubes)[L[0] + S * (L[1] + S * L[2])];
                    int M = 0;
                    if (T != 0)
                    {
                        const int Ax = L[0] + Nf[0], Ay = L[1] + Nf[1], Az = L[2] + Nf[2];
                        const uint8_t Nb = (Ax >= 0 && Ax < S && Ay >= 0 && Ay < S && Az >= 0 && Az < S)
                            ? (*Cubes)[Ax + S * (Ay + S * Az)]
                            : Store.Get(Origin[0] + Ax, Origin[1] + Ay, Origin[2] + Az);
                        if (Pal.Of(Nb).bSeeThrough && Nb != T) M = T;
                    }
                    Mask[UU + S * VV] = M;
                }
            for (int VV = 0; VV < S; ++VV)
            {
                for (int UU = 0; UU < S;)
                {
                    const int T = Mask[UU + S * VV];
                    if (T == 0) { ++UU; continue; }
                    int W = 1;
                    while (UU + W < S && Mask[UU + W + S * VV] == T) ++W;
                    int H = 1;
                    for (bool Grow = true; Grow && VV + H < S;)
                    {
                        for (int I = 0; I < W; ++I)
                            if (Mask[UU + I + S * (VV + H)] != T) { Grow = false; break; }
                        if (Grow) ++H;
                    }
                    for (int J = 0; J < H; ++J)
                        for (int I = 0; I < W; ++I) Mask[UU + I + S * (VV + J)] = 0;
                    const CubeType& Type = Pal.Of(static_cast<uint8_t>(T));
                    Part& P = Type.bTranslucent ? Translucent : Opaque;
                    const float LinF[3] = {static_cast<float>(SrgbToLinear((Type.Rgb >> 16) & 255)),
                        static_cast<float>(SrgbToLinear((Type.Rgb >> 8) & 255)), static_cast<float>(SrgbToLinear(Type.Rgb & 255))};
                    const double Sh = Shade[F];
                    int O[3], Ext[3];
                    O[D] = Origin[D] + K;
                    O[U] = Origin[U] + UU;
                    O[V] = Origin[V] + VV;
                    Ext[D] = 1;
                    Ext[U] = W;
                    Ext[V] = H;
                    const uint32_t Base = static_cast<uint32_t>(P.VertexCount());
                    for (int C = 0; C < 4; ++C)
                    {
                        P.Positions.insert(P.Positions.end(), {static_cast<float>(O[0] + Corner[F][C][0] * Ext[0]),
                            static_cast<float>(O[1] + Corner[F][C][1] * Ext[1]), static_cast<float>(O[2] + Corner[F][C][2] * Ext[2])});
                        P.Normals.insert(P.Normals.end(), {static_cast<float>(Nf[0]), static_cast<float>(Nf[1]), static_cast<float>(Nf[2])});
                        P.Colors.insert(P.Colors.end(), {Clamp01(LinF[0] * Sh), Clamp01(LinF[1] * Sh), Clamp01(LinF[2] * Sh)});
                    }
                    P.Indices.insert(P.Indices.end(), {Base, Base + 1, Base + 2, Base, Base + 2, Base + 3});
                    UU += W;
                }
            }
        }
    }
}

/** Standard base64 (as /chunk/blocks sends it). Returns false on a malformed or wrong-sized payload. */
inline bool DecodeChunk(const std::string& B64, ChunkStore::Cubes& Out)
{
    auto Val = [](char C) -> int {
        if (C >= 'A' && C <= 'Z') return C - 'A';
        if (C >= 'a' && C <= 'z') return C - 'a' + 26;
        if (C >= '0' && C <= '9') return C - '0' + 52;
        if (C == '+') return 62;
        if (C == '/') return 63;
        return -1;
    };
    size_t N = 0;
    uint32_t Acc = 0;
    int Bits = 0;
    for (char C : B64)
    {
        if (C == '=') break;
        const int V = Val(C);
        if (V < 0) return false;
        Acc = (Acc << 6) | static_cast<uint32_t>(V);
        Bits += 6;
        if (Bits >= 8)
        {
            Bits -= 8;
            if (N >= Out.size()) return false;
            Out[N++] = static_cast<uint8_t>((Acc >> Bits) & 0xFF);
        }
    }
    return N == Out.size();
}

/** Base64 to bytes (standard alphabet, '=' padding); false on a bad character or more than MaxBytes. */
inline bool DecodeBase64(const std::string& B64, std::vector<uint8_t>& Out, size_t MaxBytes = 3 * ChunkVolume)
{
    Out.clear();
    uint32_t Acc = 0;
    int Bits = 0;
    for (char C : B64)
    {
        if (C == '=') break;
        int V = (C >= 'A' && C <= 'Z') ? C - 'A' : (C >= 'a' && C <= 'z') ? C - 'a' + 26
            : (C >= '0' && C <= '9') ? C - '0' + 52 : C == '+' ? 62 : C == '/' ? 63 : -1;
        if (V < 0) return false;
        Acc = (Acc << 6) | static_cast<uint32_t>(V);
        Bits += 6;
        if (Bits >= 8)
        {
            Bits -= 8;
            if (Out.size() >= MaxBytes) return false;
            Out.push_back(static_cast<uint8_t>((Acc >> Bits) & 0xFF));
        }
    }
    return true;
}

/**
 * A chunk from the batch endpoint's run-length form (GET /world/{id}/chunks/blocks, Java Chunk.runs()):
 * (ordinal, length low byte, length high byte) triples in index order, exactly 4,096 cubes. False otherwise.
 */
inline bool DecodeRuns(const std::string& B64, ChunkStore::Cubes& Out)
{
    std::vector<uint8_t> R;
    if (!DecodeBase64(B64, R) || R.empty() || R.size() % 3 != 0) return false;
    size_t At = 0;
    for (size_t K = 0; K < R.size(); K += 3)
    {
        const size_t N = static_cast<size_t>(R[K + 1]) | (static_cast<size_t>(R[K + 2]) << 8);
        if (N == 0 || At + N > Out.size()) return false;
        std::fill(Out.begin() + static_cast<std::ptrdiff_t>(At), Out.begin() + static_cast<std::ptrdiff_t>(At + N), R[K]);
        At += N;
    }
    return At == Out.size();
}

} // namespace daedalus
