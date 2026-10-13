// SPDX-License-Identifier: MIT
//
// Parity test (ADR-032): the Unreal plugin's engine-free mesher against the Java mesher.
// Reads isle8.mesh.txt (written by MeshFixtureTest), meshes every chunk with DaedalusMeshCore.h and
// compares faces and checksums chunk by chunk; or a live capture (live_parity.py) and compares the total
// with the server's own world.glb. Prints n/m last; exits nonzero on any difference.
//
//   g++ -std=c++17 -O2 -Wall -Wextra -Werror -I../DaedalusLink/Source/DaedalusLink/Public mesh_core_test.cpp -o mesh_core_test
//   ./mesh_core_test isle8.mesh.txt

#include "DaedalusMeshCore.h"

#include <cmath>
#include <cstdio>
#include <fstream>
#include <sstream>
#include <string>

using namespace daedalus;

struct Sums
{
    long long Faces = 0, Pos = 0, NormalDotPos = 0, Color = 0, Winding = 0;
};

static Sums SumsOf(const Part& P)
{
    Sums S;
    S.Faces = P.FaceCount();
    for (size_t I = 0; I < P.Positions.size(); ++I)
    {
        S.Pos += static_cast<long long>(P.Positions[I]) * static_cast<long long>(I % 3 + 1);
        S.NormalDotPos += static_cast<long long>(P.Normals[I] * P.Positions[I]);
        S.Color += std::llround(static_cast<double>(P.Colors[I]) * 10000.0);
    }
    for (size_t I = 0; I < P.Indices.size(); ++I)
        S.Winding += static_cast<long long>(P.Indices[I]) * static_cast<long long>(I % 6 + 1);
    return S;
}

int main(int Argc, char** Argv)
{
    const char* Path = Argc > 1 ? Argv[1] : "isle8.mesh.txt";
    std::ifstream In(Path);
    if (!In)
    {
        std::printf("cannot read %s\n0/1\n", Path);
        return 1;
    }
    Palette Pal;
    ChunkStore Store;
    std::string Line;
    int Pass = 0, Total = 0;
    long long Faces = 0;
    long long WantTriangles = -1;
    while (std::getline(In, Line))
    {
        std::istringstream L(Line);
        std::string Kind;
        L >> Kind;
        if (Kind == "type")
        {
            unsigned Ord;
            std::string Name, Hex;
            int Tr, See;
            L >> Ord >> Name >> Hex >> Tr >> See;
            if (Pal.Types.size() <= Ord) Pal.Types.resize(Ord + 1);
            Pal.Types[Ord] = CubeType{Name, static_cast<uint32_t>(std::stoul(Hex, nullptr, 16)), Tr != 0, See != 0};
        }
        else if (Kind == "chunk")
        {
            ChunkKey K;
            std::string B64;
            L >> K.X >> K.Y >> K.Z >> B64;
            ChunkStore::Cubes C{};
            ++Total;
            if (DecodeChunk(B64, C))
            {
                Store.Put(K, C);
                ++Pass;
            }
            else
            {
                std::printf("FAIL decode chunk %d %d %d\n", K.X, K.Y, K.Z);
            }
        }
        else if (Kind == "runs")
        {
            ChunkKey K;
            std::string B64;
            L >> K.X >> K.Y >> K.Z >> B64;
            ChunkStore::Cubes C{};
            const ChunkStore::Cubes* Dense = Store.Find(K);
            ++Total;
            if (DecodeRuns(B64, C) && Dense && C == *Dense) ++Pass;
            else std::printf("FAIL runs chunk %d %d %d\n", K.X, K.Y, K.Z);
        }
        else if (Kind == "triangles")
        {
            L >> WantTriangles;
        }
        else if (Kind == "expect" || Kind == "greedy")
        {
            ChunkKey K;
            Sums Want[2];
            L >> K.X >> K.Y >> K.Z;
            for (Sums& W : Want) L >> W.Faces >> W.Pos >> W.NormalDotPos >> W.Color >> W.Winding;
            Part Opaque, Translucent;
            if (Kind == "greedy") MeshChunkGreedy(Store, Pal, K, Opaque, Translucent);
            else MeshChunk(Store, Pal, K, Opaque, Translucent);
            const Sums Got[2] = {SumsOf(Opaque), SumsOf(Translucent)};
            for (int P = 0; P < 2; ++P)
            {
                ++Total;
                const bool Ok = Got[P].Faces == Want[P].Faces && Got[P].Pos == Want[P].Pos
                    && Got[P].NormalDotPos == Want[P].NormalDotPos && Got[P].Color == Want[P].Color
                    && Got[P].Winding == Want[P].Winding;
                if (Ok)
                {
                    ++Pass;
                    Faces += Got[P].Faces;
                }
                else
                {
                    std::printf("FAIL %s chunk %d %d %d %s: faces %lld/%lld pos %lld/%lld n.p %lld/%lld colour %lld/%lld winding %lld/%lld\n",
                        Kind.c_str(), K.X, K.Y, K.Z, P == 0 ? "opaque" : "translucent", Got[P].Faces, Want[P].Faces, Got[P].Pos,
                        Want[P].Pos, Got[P].NormalDotPos, Want[P].NormalDotPos, Got[P].Color, Want[P].Color, Got[P].Winding,
                        Want[P].Winding);
                }
            }
        }
    }
    // A capture from a live server (live_parity.py) carries the server GLB's triangle count instead of
    // per-chunk sums: every chunk, meshed here, must add up to exactly that.
    if (WantTriangles >= 0)
    {
        ++Total;
        long long Tris = 0;
        for (const auto& KV : Store.All())
        {
            Part O, T;
            MeshChunk(Store, Pal, KV.first, O, T);
            Tris += 2LL * (O.FaceCount() + T.FaceCount());
        }
        if (Tris == WantTriangles) ++Pass;
        else std::printf("FAIL triangles %lld, the server's world.glb has %lld\n", Tris, WantTriangles);
        Faces = Tris / 2;
    }
    // Runs must refuse what isn't exactly 4,096 cubes.
    {
        ChunkStore::Cubes C{};
        ++Total;
        if (!DecodeRuns("AQAB", C) && !DecodeRuns("", C) && !DecodeRuns("AQAQAQ==", C) && !DecodeRuns("AAAQ!", C)) ++Pass;
        else std::printf("FAIL bad runs were accepted\n");
    }
    // Canary: the grader must be able to say no. Turning stone see-through must change the faces.
    ++Total;
    {
        Palette Broken = Pal;
        for (CubeType& T : Broken.Types)
            if (T.Name == "STONE") T.bSeeThrough = true;
        long long A = 0, B = 0;
        for (const auto& KV : Store.All())
        {
            Part O1, T1, O2, T2;
            MeshChunk(Store, Pal, KV.first, O1, T1);
            MeshChunk(Store, Broken, KV.first, O2, T2);
            A += O1.FaceCount() + T1.FaceCount();
            B += O2.FaceCount() + T2.FaceCount();
        }
        if (A != B) ++Pass; else std::printf("FAIL canary: a broken palette meshed the same\n");
    }
    std::printf("faces %lld across %zu chunks\n%d/%d\n", Faces, Store.All().size(), Pass, Total);
    return Pass == Total && Total > 1 ? 0 : 1;
}
