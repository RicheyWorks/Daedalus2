// SPDX-License-Identifier: MIT
#pragma once
// The voxel isle's shape in plain C++ (ADR-058). There are no Unreal types here, so the same numbers come out of:
// - ADaedalusVoxelIsle in Unreal;
// - core-test/voxel_isle_core_test.cpp;
// - the Java port, com.daedalus.world.island.VoxelIsle, which the web realm draws.
// voxel_isle_core_test writes core-test/voxel_isle_parity.txt, and the Java test reads it, so a change on either side
// that moves one cube fails the build.
//
// Everything is in double and avoids trig: cos(atan2(y, x)) is x / r, so only sqrt, floor and pow are used, and
// sqrt and floor are exact in IEEE on both sides. Cube coordinates: X, Y across, Z up, (0, 0) the centre column.

#include <cmath>
#include <cstdint>
#include <climits>
#include <vector>

namespace daedalus { namespace isle {

constexpr int Off = INT_MIN;   // "no column here"

enum Layer : int { Grass = 0, Sand, Dirt, Stone, Heart, Meadow, LayerCount };

struct Params
{
	int Seed = 7;
	int Radius = 120;
	int SummitHeight = 16;
	int Depth = 70;
	int PondX = -70, PondY = 45, PondRadius = 14;
};

/** Value noise on an integer lattice, smoothly interpolated; 0..1, the same for a given seed and salt everywhere. */
inline double Noise(const Params& P, double X, double Y, int Salt)
{
	auto Hash = [&](int IX, int IY)
	{
		uint32_t H = static_cast<uint32_t>(IX) * 374761393u + static_cast<uint32_t>(IY) * 668265263u
			+ static_cast<uint32_t>(P.Seed) * 2246822519u + static_cast<uint32_t>(Salt) * 3266489917u;
		H = (H ^ (H >> 13)) * 1274126177u;
		return static_cast<double>((H ^ (H >> 16)) & 0xFFFFu) / 65535.0;
	};
	const double FX0 = std::floor(X), FY0 = std::floor(Y);
	const int X0 = static_cast<int>(FX0), Y0 = static_cast<int>(FY0);
	const double FX = X - FX0, FY = Y - FY0;
	const double SX = FX * FX * (3.0 - 2.0 * FX), SY = FY * FY * (3.0 - 2.0 * FY);
	const double A = Hash(X0, Y0) + (Hash(X0 + 1, Y0) - Hash(X0, Y0)) * SX;
	const double B = Hash(X0, Y0 + 1) + (Hash(X0 + 1, Y0 + 1) - Hash(X0, Y0 + 1)) * SX;
	return A + (B - A) * SY;
}

inline double Dist(double X, double Y) { return std::sqrt(X * X + Y * Y); }

inline bool InPond(const Params& P, int X, int Y)
{
	if (P.PondRadius <= 0) return false;
	const double R = P.PondRadius * (0.85 + 0.3 * Noise(P, X * 0.15, Y * 0.15, 9));
	return Dist(X - P.PondX, Y - P.PondY) < R;
}

/** The column's top in cubes above the rim level, -2 in the pond, or Off past the isle's (noisy) rim. */
inline int ColumnTop(const Params& P, int X, int Y)
{
	const double R = Dist(X, Y);
	const double CX = R > 0 ? X / R : 1.0, CY = R > 0 ? Y / R : 0.0;   // the direction: cos and sin of the angle
	const double Edge = P.Radius * (0.84 + 0.16 * Noise(P, CX * 3.0 + 10.0, CY * 3.0 + 10.0, 1));
	if (R >= Edge) return Off;
	const double T = 1.0 - R / Edge;                                    // 1 at the centre, 0 at the rim
	double H = P.SummitHeight * std::pow(T, 1.6) + 2.5 * Noise(P, X * 0.07, Y * 0.07, 2) + 1.2 * Noise(P, X * 0.2, Y * 0.2, 3);
	H = std::floor(H / 2.0) * 2.0;                                      // gentle two-cube terraces
	if (InPond(P, X, Y)) return -2;
	return H > 0 ? static_cast<int>(H) : 0;
}

/** The lowest cube of the hanging rock under the column. */
inline int ColumnBottom(const Params& P, int X, int Y)
{
	double T = 1.0 - Dist(X, Y) / P.Radius;
	T = T < 0 ? 0 : (T > 1 ? 1 : T);
	return -3 - static_cast<int>(P.Depth * std::pow(T, 1.1) * (0.8 + 0.4 * Noise(P, X * 0.1, Y * 0.1, 4)));
}

/** Sand only on a narrow beach: within two cubes of the rim, and round the pond. */
inline bool Shore(const Params& P, int X, int Y)
{
	if (InPond(P, X, Y)) return true;
	if (P.PondRadius > 0 && Dist(X - P.PondX, Y - P.PondY) < P.PondRadius + 2.5) return true;
	return ColumnTop(P, X + 2, Y) == Off || ColumnTop(P, X - 2, Y) == Off || ColumnTop(P, X, Y + 2) == Off
		|| ColumnTop(P, X, Y - 2) == Off;
}

/** What a cube at height Z in a column (Top T, Bottom B) is made of. */
inline Layer LayerOf(const Params& P, int X, int Y, int Z, int T, int B, bool IsShore)
{
	Layer L = Stone;
	if (Z == T) L = IsShore ? Sand : (Noise(P, X * 0.09, Y * 0.09, 7) > 0.55 ? Meadow : Grass);
	else if (Z >= T - 2) L = Dirt;
	if (Z <= B + 1 && Dist(X, Y) < 4.0) L = Heart;   // the glowing tip that holds the isle up
	return L;
}

/** Every visible cube (one with an open face), in Y-major, X, then Z order: Emit(X, Y, Z, Layer). Returns the
 * column count. */
template <typename F>
inline int Build(const Params& P, F&& Emit)
{
	const int N = P.Radius + 2;
	const int W = 2 * N + 1;
	// Each column's top and bottom, so neighbours are cheap to check.
	std::vector<int> Tops(static_cast<size_t>(W) * W), Bots(static_cast<size_t>(W) * W);
	for (int Y = -N; Y <= N; ++Y)
		for (int X = -N; X <= N; ++X)
		{
			const int I = (Y + N) * W + (X + N);
			Tops[I] = ColumnTop(P, X, Y);
			Bots[I] = Tops[I] == Off ? 0 : ColumnBottom(P, X, Y);
		}
	auto Top = [&](int X, int Y) { return (X < -N || X > N || Y < -N || Y > N) ? Off : Tops[(Y + N) * W + (X + N)]; };
	auto Bot = [&](int X, int Y) { return (X < -N || X > N || Y < -N || Y > N) ? 0 : Bots[(Y + N) * W + (X + N)]; };
	int Columns = 0;
	const int NX[] = {1, -1, 0, 0}, NY[] = {0, 0, 1, -1};
	for (int Y = -N; Y <= N; ++Y)
		for (int X = -N; X <= N; ++X)
		{
			const int T = Top(X, Y);
			if (T == Off) continue;
			++Columns;
			const int B = Bot(X, Y);
			const bool IsShore = Shore(P, X, Y);
			for (int Z = B; Z <= T; ++Z)
			{
				bool Open = Z == T || Z == B;
				for (int k = 0; k < 4 && !Open; ++k)
				{
					const int NT = Top(X + NX[k], Y + NY[k]);
					Open = NT == Off || NT < Z || Bot(X + NX[k], Y + NY[k]) > Z;
				}
				if (Open) Emit(X, Y, Z, LayerOf(P, X, Y, Z, T, B, IsShore));
			}
		}
	return Columns;
}

/** One face rectangle of the isle's surface, in cube units. Normal: 0 +X, 1 -X, 2 +Y, 3 -Y, 4 +Z (top), 5 -Z (bottom).
 * The quad lies in the plane of its normal axis at Plane. It covers U0..U1 and V0..V1 on the other two axes, which are
 * (Y, Z) for X normals, (X, Z) for Y normals and (X, Y) for Z normals. */
struct Quad
{
	int Layer, Normal, Plane, U0, U1, V0, V1;
};

/**
 * The isle's visible surface as merged quads, exactly the faces the cube build shows and no others. Instead of a
 * cube instance per visible cube (Claude Island: 117k), it is a few tens of thousands of quads in one mesh per layer,
 * with one collision body.
 * - Tops and bottoms: rectangles of equal height and layer, merged greedily on the column grid.
 * - Sides: the faces of a column not covered by its neighbour's [bottom, top], in runs of one layer, merged along
 *   the wall with the next column when they line up.
 */
inline std::vector<Quad> Mesh(const Params& P)
{
	const int N = P.Radius + 2, W = 2 * N + 1;
	std::vector<int> Tops(static_cast<size_t>(W) * W), Bots(static_cast<size_t>(W) * W);
	std::vector<char> Sh(static_cast<size_t>(W) * W, 0);
	for (int Y = -N; Y <= N; ++Y)
		for (int X = -N; X <= N; ++X)
		{
			const int I = (Y + N) * W + (X + N);
			Tops[I] = ColumnTop(P, X, Y);
			Bots[I] = Tops[I] == Off ? 0 : ColumnBottom(P, X, Y);
		}
	auto Idx = [&](int X, int Y) { return (Y + N) * W + (X + N); };
	auto Top = [&](int X, int Y) { return (X < -N || X > N || Y < -N || Y > N) ? Off : Tops[Idx(X, Y)]; };
	auto Bot = [&](int X, int Y) { return (X < -N || X > N || Y < -N || Y > N) ? 0 : Bots[Idx(X, Y)]; };
	for (int Y = -N; Y <= N; ++Y)
		for (int X = -N; X <= N; ++X)
			if (Top(X, Y) != Off) Sh[Idx(X, Y)] = Shore(P, X, Y) ? 1 : 0;
	auto LayerAt = [&](int X, int Y, int Z) { return LayerOf(P, X, Y, Z, Top(X, Y), Bot(X, Y), Sh[Idx(X, Y)] != 0); };

	std::vector<Quad> Out;
	// --- tops (Normal 4) and bottoms (Normal 5): greedy rectangles over (height, layer)
	for (int Face = 4; Face <= 5; ++Face)
	{
		std::vector<char> Done(static_cast<size_t>(W) * W, 0);
		auto Key = [&](int X, int Y, int& H, int& L) {
			const int T = Top(X, Y);
			if (T == Off) return false;
			H = Face == 4 ? T : Bot(X, Y);
			L = LayerAt(X, Y, H);
			return true;
		};
		for (int Y = -N; Y <= N; ++Y)
			for (int X = -N; X <= N; ++X)
			{
				int H, L;
				if (Done[Idx(X, Y)] || !Key(X, Y, H, L)) continue;
				auto Same = [&](int AX, int AY) {
					int H2, L2;
					return AX <= N && AY <= N && !Done[Idx(AX, AY)] && Key(AX, AY, H2, L2) && H2 == H && L2 == L;
				};
				int X1 = X;
				while (Same(X1 + 1, Y)) ++X1;
				int Y1 = Y;
				for (bool Grow = true; Grow;)
				{
					for (int AX = X; AX <= X1 && Grow; ++AX) Grow = Same(AX, Y1 + 1);
					if (Grow) ++Y1;
				}
				for (int AY = Y; AY <= Y1; ++AY)
					for (int AX = X; AX <= X1; ++AX) Done[Idx(AX, AY)] = 1;
				Out.push_back({L, Face, Face == 4 ? H + 1 : H, X, X1 + 1, Y, Y1 + 1});
			}
	}
	// --- sides: per wall line, per z, merge runs along the wall; each cell is one exposed face (X, Y, Z, layer)
	const int DX[] = {1, -1, 0, 0}, DY[] = {0, 0, 1, -1};
	for (int D = 0; D < 4; ++D)
	{
		const bool AlongY = D < 2;   // an X-facing wall runs along Y
		for (int Line = -N; Line <= N; ++Line)
		{
			// Exposed faces on this wall line as (z, layer) per position along it; build a small z-range map.
			struct Cell { int B, T; };
			std::vector<Cell> Span(static_cast<size_t>(W));
			int ZMin = 0, ZMax = -1;
			for (int K = -N; K <= N; ++K)
			{
				const int X = AlongY ? Line : K, Y = AlongY ? K : Line;
				Span[K + N] = {1, 0};
				if (Top(X, Y) == Off) continue;
				Span[K + N] = {Bot(X, Y), Top(X, Y)};
				if (ZMax < ZMin) { ZMin = Bot(X, Y); ZMax = Top(X, Y); }
				ZMin = ZMin < Bot(X, Y) ? ZMin : Bot(X, Y);
				ZMax = ZMax > Top(X, Y) ? ZMax : Top(X, Y);
			}
			if (ZMax < ZMin) continue;
			const int H = ZMax - ZMin + 1;
			std::vector<int> Face(static_cast<size_t>(W) * H, -1);   // layer of the exposed face, or -1
			for (int K = -N; K <= N; ++K)
			{
				const int X = AlongY ? Line : K, Y = AlongY ? K : Line;
				const Cell C = Span[K + N];
				if (C.B > C.T) continue;
				const int NT = Top(X + DX[D], Y + DY[D]), NB = Bot(X + DX[D], Y + DY[D]);
				for (int Z = C.B; Z <= C.T; ++Z)
					if (NT == Off || Z > NT || Z < NB) Face[(Z - ZMin) * W + (K + N)] = LayerAt(X, Y, Z);
			}
			// greedy rectangles on (along, z)
			for (int Z = 0; Z < H; ++Z)
				for (int K = 0; K < W; ++K)
				{
					const int L = Face[Z * W + K];
					if (L < 0) continue;
					int K1 = K;
					while (K1 + 1 < W && Face[Z * W + K1 + 1] == L) ++K1;
					int Z1 = Z;
					for (bool Grow = true; Grow;)
					{
						for (int A = K; A <= K1 && Grow; ++A) Grow = Z1 + 1 < H && Face[(Z1 + 1) * W + A] == L;
						if (Grow) ++Z1;
					}
					for (int AZ = Z; AZ <= Z1; ++AZ)
						for (int A = K; A <= K1; ++A) Face[AZ * W + A] = -1;
					const int Plane = (D == 0 || D == 2) ? Line + 1 : Line;   // a +X face sits on the cube's far side
					Out.push_back({L, D, Plane, K - N, K1 + 1 - N, Z + ZMin, Z1 + 1 + ZMin});
				}
		}
	}
	return Out;
}

}}  // namespace daedalus::isle
