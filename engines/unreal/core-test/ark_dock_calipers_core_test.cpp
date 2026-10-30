// SPDX-License-Identifier: MIT
// G461 The Dock Calipers C++ port (G592), checked without Unreal:
//   g++ -std=c++17 -Wall -Wextra -Wshadow -Werror -I../DaedalusLink/Source/DaedalusLink/Public ark_dock_calipers_core_test.cpp
//   ./a.out ark_dock_calipers_parity.txt
#include "DaedalusArkDockCalipersCore.h"
#include "DaedalusStableRandom.h"
#include "ark_trees_test.h"
#include <cinttypes>
#include <cstring>
using namespace daedalus::ark;
using ark_test::S;
using stable_test::Check;

namespace {

// Java's Long.toHexString(Double.doubleToRawLongBits(V)).
std::string Bits(double V)
{
	uint64_t U = 0;
	std::memcpy(&U, &V, sizeof U);
	char Buf[24];
	std::snprintf(Buf, sizeof Buf, "%" PRIx64, U);
	return Buf;
}

std::vector<DockBuoy> Buoys(daedalus::stable::StableRng& Rng, int N, int Span)
{
	std::vector<DockBuoy> Pts;
	for (int i = 0; i < N; ++i)
	{
		const int64_t X = Rng.NextInt(2 * Span + 1) - Span;
		Pts.push_back({ X, Rng.NextInt(2 * Span + 1) - Span });
	}
	return Pts;
}

// Same seeds and spans as DockCalipersParityTest.dockCalipers.
std::vector<std::string> ParityLines()
{
	std::vector<std::string> Out;
	for (int s = 1; s <= 60; ++s)
	{
		daedalus::stable::StableRng Rng(s);
		const int N = 1 + Rng.NextInt(40);
		const int Span = s <= 30 ? 5 : s <= 50 ? 1000 : static_cast<int>(DockCalipersMaxCoord);
		const std::vector<DockBuoy> Pts = Buoys(Rng, N, Span);
		std::string Line = "seed=" + S(s) + " n=" + S(N) + " buoys=";
		for (int i = 0; i < N; ++i) Line += (i ? "," : "") + S(Pts[i].X) + ":" + S(Pts[i].Y);
		const std::vector<DockBuoy> H = DockHull(Pts);
		Line += " hull=";
		for (size_t i = 0; i < H.size(); ++i) Line += (i ? "," : "") + S(H[i].X) + ":" + S(H[i].Y);
		Line += " diam2=" + S(DockDiameterSquared(Pts)) + " width=" + Bits(DockWidth(Pts));
		Out.push_back(Line);
	}
	return Out;
}

int64_t BruteDiameter(const std::vector<DockBuoy>& P)
{
	int64_t Best = 0;
	for (const DockBuoy& A : P)
		for (const DockBuoy& B : P) Best = std::max(Best, DockDist2(A, B));
	return Best;
}

// Brute width: over every pair direction with all buoys on one side, the farthest buoy.
double BruteWidth(const std::vector<DockBuoy>& P)
{
	double Best = std::numeric_limits<double>::max();
	bool Any = false;
	for (const DockBuoy& A : P)
		for (const DockBuoy& B : P)
		{
			if (A.X == B.X && A.Y == B.Y) continue;
			Any = true;
			int64_t Lo = 0, Hi = 0;
			for (const DockBuoy& Q : P)
			{
				const int64_t C = DockCross(A, B, Q);
				Lo = std::min(Lo, C);
				Hi = std::max(Hi, C);
			}
			if (Lo == 0 || Hi == 0) Best = std::min(Best, static_cast<double>(Hi - Lo) / std::sqrt(static_cast<double>(DockDist2(A, B))));
		}
	return Any ? Best : 0;
}

// The hull turns strictly left at every corner and no buoy lies to the right of any hull edge.
bool HullIsConvexAndHoldsAll(const std::vector<DockBuoy>& P, const std::vector<DockBuoy>& H)
{
	const size_t M = H.size();
	if (M < 3) return true;
	for (size_t i = 0; i < M; ++i)
	{
		if (DockCross(H[i], H[(i + 1) % M], H[(i + 2) % M]) <= 0) return false;
		for (const DockBuoy& Q : P)
			if (DockCross(H[i], H[(i + 1) % M], Q) < 0) return false;
	}
	return true;
}

// Random fields from crowded to full range: diameter equal to brute force exactly, width within 1e-9 relative.
bool MatchesBruteForce()
{
	daedalus::stable::StableRng Rng(461);
	for (int Round = 0; Round < 300; ++Round)
	{
		const int N = 1 + Rng.NextInt(30);
		const int Span = Round % 3 == 0 ? 3 : Round % 3 == 1 ? 50 : static_cast<int>(DockCalipersMaxCoord);
		const std::vector<DockBuoy> P = Buoys(Rng, N, Span);
		const double W = DockWidth(P), BW = BruteWidth(P);
		if (DockDiameterSquared(P) != BruteDiameter(P) || std::fabs(W - BW) > 1e-9 * std::max(1.0, BW)) return false;
		if (!HullIsConvexAndHoldsAll(P, DockHull(P))) return false;
	}
	return true;
}

// The largest allowed field: 100,000 buoys inside the +-10^6 square, plus its four corners.
bool FullHarbour()
{
	daedalus::stable::StableRng Rng(592);
	std::vector<DockBuoy> P = Buoys(Rng, DockCalipersMaxBuoys - 4, static_cast<int>(DockCalipersMaxCoord) - 1);
	const int64_t M = DockCalipersMaxCoord;
	P.insert(P.end(), { { -M, -M }, { M, -M }, { M, M }, { -M, M } });
	const std::vector<DockBuoy> H = DockHull(P);
	return H.size() == 4 && DockDiameterSquared(P) == 8 * M * M && DockWidth(P) == 2.0 * static_cast<double>(M);
}

} // namespace

int main(int argc, char** argv)
{
	stable_test::CheckParity(argc > 1 ? argv[1] : "ark_dock_calipers_parity.txt", ParityLines());
	Check("diameter and width match brute force on random fields", MatchesBruteForce());
	Check("100,000-buoy harbour measures its corners", FullHarbour());
	Check("collinear and repeated buoys", DockWidth({ { 0, 0 }, { 2, 2 }, { 5, 5 }, { 2, 2 } }) == 0
		&& DockDiameterSquared({ { 0, 0 }, { 2, 2 }, { 5, 5 } }) == 50 && DockHull({ { 3, 3 }, { 3, 3 }, { 3, 3 } }).size() == 1
		&& DockDiameterSquared({ { 7, -7 } }) == 0);
	Check("bad fields are refused", DockHull({}).empty() && DockDiameterSquared({ { 0, DockCalipersMaxCoord + 1 } }) == -1
		&& DockWidth(std::vector<DockBuoy>(DockCalipersMaxBuoys + 1)) == -1);
	Check("the quest names the squared widest span", DockCalipersQuestAnswer({ { 0, 0 }, { 3, 0 }, { 3, 4 } }, 25)
		&& !DockCalipersQuestAnswer({ { 0, 0 }, { 3, 0 }, { 3, 4 } }, 24) && !DockCalipersQuestAnswer({}, 0));
	return stable_test::Finish();
}
