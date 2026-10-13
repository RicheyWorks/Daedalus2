// SPDX-License-Identifier: MIT
// The voxel isle's shape, checked without Unreal, and the parity file the Java port must match. Build:
//   g++ -std=c++17 -Wall -Wextra -Werror -fsanitize=address,undefined -I../DaedalusLink/Source/DaedalusLink/Public voxel_isle_core_test.cpp
//   ./a.out [--write voxel_isle_parity.txt]
#include "DaedalusVoxelIsleCore.h"
#include <cstdio>
#include <cstring>
#include <string>
#include <vector>
using namespace daedalus::isle;
static int Passed = 0, Total = 0;
static void Check(const char* Name, bool OK) { ++Total; Passed += OK; std::printf("%s %s\n", OK ? "PASS" : "FAIL", Name); }

struct Summary { int Columns = 0; long Cubes = 0; long Layers[LayerCount] = {}; uint64_t Hash = 14695981039346656037ull; };

static Summary Run(const Params& P)
{
	Summary S;
	S.Columns = Build(P, [&](int X, int Y, int Z, Layer L) {
		++S.Cubes; ++S.Layers[L];
		const int V[4] = {X, Y, Z, static_cast<int>(L)};
		for (int v : V) { S.Hash ^= static_cast<uint32_t>(v); S.Hash *= 1099511628211ull; }   // FNV-1a over the ints
	});
	return S;
}

// The parity set: the isles Claude Island and the Orrery Reach actually use, plus small odd ones.
static const Params Set[] = {
	{7, 140, 16, 70, -70, 45, 14},    // Claude Island (orr_place.py)
	{31, 70, 6, 40, 20, -15, 10},     // Bloomfields
	{47, 60, 8, 50, 0, 0, 22},        // Tidewells
	{53, 38, 14, 45, 0, 0, 0},        // Lens Forge
	{61, 46, 20, 60, 0, 0, 0},        // Vault
	{-5, 9, 3, 6, 2, 2, 3},           // tiny, negative seed
	{2147483647, 24, 30, 10, -10, 0, 6},
};

int main(int argc, char** argv)
{
	const char* Out = (argc > 2 && std::strcmp(argv[1], "--write") == 0) ? argv[2] : nullptr;
	// --- the shape's own rules
	Params P = Set[1];
	Check("noise stays in 0..1", [&] { for (int i = -500; i < 500; ++i) { double n = Noise(P, i * 0.37, i * -0.21, i & 7); if (n < 0 || n > 1) return false; } return true; }());
	Check("noise is the same for the same seed", Noise(P, 3.3, -7.1, 2) == Noise(P, 3.3, -7.1, 2));
	Params Q = P; Q.Seed = 32;
	Check("noise changes with the seed", Noise(P, 3.3, -7.1, 2) != Noise(Q, 3.3, -7.1, 2));
	Check("the centre is land", ColumnTop(P, 0, 0) != Off);
	Check("nothing past the radius", ColumnTop(P, P.Radius, 0) == Off && ColumnTop(P, 0, -P.Radius - 1) == Off);
	Check("terraces are even", [&] { for (int x = -60; x <= 60; x += 3) { int t = ColumnTop(P, x, 7); if (t != Off && t != -2 && t % 2) return false; } return true; }());
	Check("the pond is sunk", ColumnTop(P, P.PondX, P.PondY) == -2);
	Check("the rock hangs below the top", [&] { for (int x = -60; x <= 60; x += 5) { int t = ColumnTop(P, x, 0); if (t != Off && ColumnBottom(P, x, 0) >= t) return false; } return true; }());
	Check("the centre hangs deepest", ColumnBottom(P, 0, 0) < ColumnBottom(P, 50, 0));
	Summary A = Run(P), B = Run(P);
	Check("a build is the same every time", A.Hash == B.Hash && A.Cubes == B.Cubes);
	Check("every layer is used on Bloomfields", A.Layers[Grass] && A.Layers[Sand] && A.Layers[Dirt] && A.Layers[Stone] && A.Layers[Heart] && A.Layers[Meadow]);
	Check("only open cubes: far fewer than a solid isle", A.Cubes < static_cast<long>(A.Columns) * 20);
	Params NoPond = P; NoPond.PondRadius = 0;
	Check("no pond when its radius is 0", ColumnTop(NoPond, P.PondX, P.PondY) != -2);
	Summary C = Run(Set[0]);
	Check("Claude Island is about 100k cubes (budget for one HISM per layer)", C.Cubes > 40000 && C.Cubes < 250000);

	// --- the parity file for the Java port
	if (Out)
	{
		FILE* F = std::fopen(Out, "w");
		std::fprintf(F, "# voxel_isle_core_test.cpp: seed radius summit depth pondX pondY pondR | columns cubes grass sand dirt stone heart meadow fnv | tops\n");
		for (const Params& S : Set)
		{
			Summary R = Run(S);
			std::fprintf(F, "%d %d %d %d %d %d %d | %d %ld", S.Seed, S.Radius, S.SummitHeight, S.Depth, S.PondX, S.PondY, S.PondRadius, R.Columns, R.Cubes);
			for (long L : R.Layers) std::fprintf(F, " %ld", L);
			std::fprintf(F, " %llu |", static_cast<unsigned long long>(R.Hash));
			for (int i = 0; i < 24; ++i)
			{
				const int X = (i * 37) % (2 * S.Radius + 1) - S.Radius, Y = (i * 53) % (2 * S.Radius + 1) - S.Radius;
				std::fprintf(F, " %d,%d,%d,%d", X, Y, ColumnTop(S, X, Y), ColumnTop(S, X, Y) == Off ? 0 : ColumnBottom(S, X, Y));
			}
			std::fprintf(F, "\n");
		}
		std::fclose(F);
		std::printf("wrote %s\n", Out);
	}
	std::printf("%d/%d\n", Passed, Total);
	return Passed == Total ? 0 : 1;
}
