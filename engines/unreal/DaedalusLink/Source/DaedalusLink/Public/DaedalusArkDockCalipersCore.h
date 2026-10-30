// SPDX-License-Identifier: MIT
// G461 The Dock Calipers (art-master-flex), plain C++17, header-only, no Unreal types (G592 port).
// The harbour master measures a field of integer buoys: the widest span between two buoys (exact squared diameter)
// and the narrowest dock that holds them all (minimum width between two parallel lines). Convex hull by Andrew's
// monotone chain, then rotating calipers, O(n log n). Bad input gives an empty hull and -1 instead of throwing.
// Must agree with com.daedalus.world.ark.DockCalipers line for line (ark_dock_calipers_parity.txt, checked by
// DockCalipersParityTest.java and ark_dock_calipers_core_test.cpp).
#pragma once
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <limits>
#include <vector>

namespace daedalus { namespace ark {

constexpr const char* DockCalipersQuest = "q_dock_calipers";
constexpr int DockCalipersMaxBuoys = 100000;
constexpr int64_t DockCalipersMaxCoord = 1000000;

struct DockBuoy { int64_t X, Y; };

inline int64_t DockCross(const DockBuoy& O, const DockBuoy& A, const DockBuoy& B)
{
	return (A.X - O.X) * (B.Y - O.Y) - (A.Y - O.Y) * (B.X - O.X);
}

inline int64_t DockDist2(const DockBuoy& A, const DockBuoy& B)
{
	const int64_t DX = A.X - B.X, DY = A.Y - B.Y;
	return DX * DX + DY * DY;
}

inline bool DockCalipersValid(const std::vector<DockBuoy>& Pts)
{
	if (Pts.empty() || static_cast<int64_t>(Pts.size()) > DockCalipersMaxBuoys) return false;
	for (const DockBuoy& P : Pts)
		if (std::llabs(P.X) > DockCalipersMaxCoord || std::llabs(P.Y) > DockCalipersMaxCoord) return false;
	return true;
}

// Convex hull corners, counter-clockwise from the lowest-x (then lowest-y) buoy, no collinear corners.
inline std::vector<DockBuoy> DockHull(const std::vector<DockBuoy>& Pts)
{
	if (!DockCalipersValid(Pts)) return {};
	std::vector<DockBuoy> P = Pts;
	std::sort(P.begin(), P.end(), [](const DockBuoy& A, const DockBuoy& B) { return A.X != B.X ? A.X < B.X : A.Y < B.Y; });
	const int N = static_cast<int>(P.size());
	std::vector<DockBuoy> H(2 * static_cast<size_t>(N));
	int K = 0;
	for (int i = 0; i < N; ++i)
	{
		while (K >= 2 && DockCross(H[K - 2], H[K - 1], P[i]) <= 0) --K;
		H[K++] = P[i];
	}
	for (int i = N - 2, Lo = K + 1; i >= 0; --i)
	{
		while (K >= Lo && DockCross(H[K - 2], H[K - 1], P[i]) <= 0) --K;
		H[K++] = P[i];
	}
	H.resize(static_cast<size_t>(std::max(1, K - 1)));
	if (H.size() == 2 && H[0].X == H[1].X && H[0].Y == H[1].Y) H.resize(1);
	return H;
}

// Squared diameter: the largest squared distance between two buoys; -1 for bad input.
inline int64_t DockDiameterSquared(const std::vector<DockBuoy>& Pts)
{
	const std::vector<DockBuoy> H = DockHull(Pts);
	const int M = static_cast<int>(H.size());
	if (M == 0) return -1;
	if (M == 1) return 0;
	if (M == 2) return DockDist2(H[0], H[1]);
	int64_t Best = 0;
	int J = 1;
	for (int i = 0; i < M; ++i)
	{
		const DockBuoy& A = H[i];
		const DockBuoy& B = H[(i + 1) % M];
		while (DockCross(A, B, H[(J + 1) % M]) > DockCross(A, B, H[J])) J = (J + 1) % M;
		Best = std::max(Best, std::max(DockDist2(A, H[J]), DockDist2(B, H[J])));
	}
	return Best;
}

// Minimum width between two parallel lines enclosing every buoy; 0 when collinear, -1 for bad input. The same IEEE
// steps as Java (exact int64 -> double, correctly rounded sqrt and divide), so the bits match.
inline double DockWidth(const std::vector<DockBuoy>& Pts)
{
	const std::vector<DockBuoy> H = DockHull(Pts);
	const int M = static_cast<int>(H.size());
	if (M == 0) return -1;
	if (M < 3) return 0;
	double Best = std::numeric_limits<double>::max();
	int J = 1;
	for (int i = 0; i < M; ++i)
	{
		const DockBuoy& A = H[i];
		const DockBuoy& B = H[(i + 1) % M];
		while (DockCross(A, B, H[(J + 1) % M]) > DockCross(A, B, H[J])) J = (J + 1) % M;
		Best = std::min(Best, static_cast<double>(DockCross(A, B, H[J])) / std::sqrt(static_cast<double>(DockDist2(A, B))));
	}
	return Best;
}

// Quest q_dock_calipers: the harbour master names the squared widest span.
inline bool DockCalipersQuestAnswer(const std::vector<DockBuoy>& Pts, int64_t Answer)
{
	return DockCalipersValid(Pts) && DockDiameterSquared(Pts) == Answer;
}

}} // namespace daedalus::ark
