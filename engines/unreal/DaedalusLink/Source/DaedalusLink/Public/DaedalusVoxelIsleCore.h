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

}}  // namespace daedalus::isle
