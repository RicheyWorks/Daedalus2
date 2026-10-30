// SPDX-License-Identifier: MIT
// G441 The Star Mesh C++ port (G588), checked without Unreal:
//   g++ -std=c++17 -Wall -Wextra -Wshadow -Werror -I../DaedalusLink/Source/DaedalusLink/Public ark_star_mesh_core_test.cpp
//   ./a.out ark_star_mesh_parity.txt
#include "DaedalusArkStarMeshCore.h"
#include "DaedalusStableRandom.h"
#include "ark_trees_test.h"
#include <set>
#include <tuple>
using namespace daedalus::ark;
using ark_test::S;
using stable_test::Check;

namespace {

int64_t Orient(const StarPoint& A, const StarPoint& B, const StarPoint& C)
{
	return (B.X - A.X) * (C.Y - A.Y) - (B.Y - A.Y) * (C.X - A.X);
}

// Same draw as StarMeshParityTest.stars: distinct stars, no three collinear, by rejection.
std::vector<StarPoint> Stars(daedalus::stable::StableRng& Rng, int N, int Span)
{
	std::vector<StarPoint> Pts;
	while (static_cast<int>(Pts.size()) < N)
	{
		const StarPoint P{ Rng.NextInt(2 * Span + 1) - Span, Rng.NextInt(2 * Span + 1) - Span };
		bool Bad = false;
		for (size_t j = 0; j < Pts.size() && !Bad; ++j)
		{
			Bad = Pts[j].X == P.X && Pts[j].Y == P.Y;
			for (size_t k = j + 1; k < Pts.size() && !Bad; ++k) Bad = Orient(Pts[j], Pts[k], P) == 0;
		}
		if (!Bad) Pts.push_back(P);
	}
	return Pts;
}

std::string JoinWith(const std::vector<int>& V, const char* Sep)
{
	if (V.empty()) return "-";
	std::string Out;
	for (size_t i = 0; i < V.size(); ++i) Out += (i ? Sep : "") + S(V[i]);
	return Out;
}

// Same bad skies as StarMeshParityTest.REFUSED, one per refusal reason, then a good one.
std::vector<std::vector<StarPoint>> RefusedSkies()
{
	std::vector<StarPoint> Many;
	for (int64_t i = 0; i <= StarMeshMaxPoints; ++i) Many.push_back({ i, i * i });
	return { { { 0, 0 }, { 1, 1 } }, Many, { { 0, 0 }, { 1, 0 }, { 0, StarMeshMaxCoord + 1 } },
		{ { 0, 0 }, { 0, 0 }, { 2, 3 } }, { { 0, 0 }, { 1, 1 }, { 2, 2 } },
		{ { 0, 0 }, { 5, 1 }, { 2, 3 }, { 7, 4 }, { 9, 9 }, { -3, -3 } }, { { 0, 0 }, { 4, 0 }, { 0, 4 } } };
}

std::vector<std::string> ParityLines()
{
	std::vector<std::string> Out;
	for (int s = 1; s <= 60; ++s)
	{
		daedalus::stable::StableRng Rng(s);
		const int N = 3 + Rng.NextInt(14);
		const std::vector<StarPoint> Pts = Stars(Rng, N, s <= 40 ? 100 : static_cast<int>(StarMeshMaxCoord));
		std::string Line = "seed=" + S(s) + " n=" + S(N) + " stars=";
		for (int i = 0; i < N; ++i) Line += (i ? "," : "") + S(Pts[i].X) + ":" + S(Pts[i].Y);
		const StarMesh Mesh = StarMeshBuild(Pts);
		const std::vector<StarTriangle>& Tris = Mesh.Triangles;
		Line += " tris=" + S(static_cast<int64_t>(Tris.size())) + " ";
		for (size_t i = 0; i < Tris.size(); ++i)
			Line += (i ? "," : "") + S(Tris[i].A) + "." + S(Tris[i].B) + "." + S(Tris[i].C);
		Line += " hull=" + JoinWith(Mesh.Hull, ",") + " flips=" + S(Mesh.Flips) + " nbrs=";
		const std::vector<std::vector<int>> Nbrs = StarMeshNeighbours(N, Tris);
		for (int i = 0; i < N; ++i) Line += (i ? "|" : "") + JoinWith(Nbrs[static_cast<size_t>(i)], ".");
		const int Span = s <= 40 ? 100 : static_cast<int>(StarMeshMaxCoord);
		Line += " locate=";
		for (int q = 0; q < 5; ++q)
		{
			StarPoint At = Pts[0];
			if (q < 4)
			{
				const int64_t X = Rng.NextInt(2 * Span + 1) - Span;
				At = { X, Rng.NextInt(2 * Span + 1) - Span };
			}
			Line += (q ? "," : "") + S(At.X) + ":" + S(At.Y) + ">" + S(StarMeshLocate(Pts, Tris, At));
		}
		Out.push_back(Line);
	}
	const std::vector<std::vector<StarPoint>> Refused = RefusedSkies();
	for (size_t i = 0; i < Refused.size(); ++i)
		Out.push_back("refused=" + S(static_cast<int64_t>(i)) + " why=" + StarMeshProblemName(StarMeshCheck(Refused[i])));
	return Out;
}

using Tri = std::tuple<int, int, int>;

std::set<Tri> Canon(const std::vector<StarTriangle>& Tris)
{
	std::set<Tri> Out;
	for (const StarTriangle& T : Tris)
	{
		int V[3] = { T.A, T.B, T.C };
		std::sort(V, V + 3);
		Out.insert({ V[0], V[1], V[2] });
	}
	return Out;
}

// Brute force: every triple whose circumcircle holds no other star (unique when no four are cocircular).
std::set<Tri> Brute(const std::vector<StarPoint>& P)
{
	std::set<Tri> Out;
	const int N = static_cast<int>(P.size());
	for (int i = 0; i < N; ++i)
		for (int j = i + 1; j < N; ++j)
			for (int k = j + 1; k < N; ++k)
			{
				const StarTriangle T = Orient(P[i], P[j], P[k]) > 0 ? StarTriangle{ i, j, k } : StarTriangle{ i, k, j };
				if (StarMeshEmptyCircles(P, { T })) Out.insert({ i, j, k });
			}
	return Out;
}

bool NoFourCocircular(const std::vector<StarPoint>& P)
{
	const int N = static_cast<int>(P.size());
	for (int i = 0; i < N; ++i)
		for (int j = i + 1; j < N; ++j)
			for (int k = j + 1; k < N; ++k)
				for (int l = k + 1; l < N; ++l)
					if (StarInCircle(P[i], P[j], P[k], P[l]) == 0) return false;
	return true;
}

int HullSize(const std::vector<StarPoint>& P)
{
	int H = 0;
	for (size_t i = 0; i < P.size(); ++i)
		for (size_t j = 0; j < P.size(); ++j)
		{
			bool Edge = i != j;
			for (size_t k = 0; k < P.size() && Edge; ++k) Edge = k == i || k == j || Orient(P[i], P[j], P[k]) > 0;
			H += Edge;
		}
	return H;
}

// Small random skies, near and across the full +-10^6 range: same triangles as brute force, all counter-clockwise,
// and 2n - 2 - hull of them.
bool MatchesBruteForce()
{
	daedalus::stable::StableRng Rng(441);
	for (int Round = 0; Round < 120; ++Round)
	{
		const int N = 3 + Rng.NextInt(10);
		const std::vector<StarPoint> P = Stars(Rng, N, Round % 2 ? static_cast<int>(StarMeshMaxCoord) : 30);
		if (!NoFourCocircular(P)) continue;
		const std::vector<StarTriangle> T = StarMeshTriangulate(P);
		for (const StarTriangle& X : T)
			if (Orient(P[X.A], P[X.B], P[X.C]) <= 0) return false;
		if (Canon(T) != Brute(P) || static_cast<int>(T.size()) != 2 * N - 2 - HullSize(P)) return false;
	}
	return true;
}

// The largest allowed sky: 400 stars, every circumcircle empty.
bool FullSky()
{
	daedalus::stable::StableRng Rng(588);
	const std::vector<StarPoint> P = Stars(Rng, StarMeshMaxPoints, static_cast<int>(StarMeshMaxCoord));
	const std::vector<StarTriangle> T = StarMeshTriangulate(P);
	return static_cast<int>(T.size()) == 2 * StarMeshMaxPoints - 2 - HullSize(P) && StarMeshEmptyCircles(P, T);
}

// Hull, neighbours and locate against brute force on random skies (same checks as StarMeshTest).
bool QueriesMatchBruteForce()
{
	daedalus::stable::StableRng Rng(4411);
	for (int Round = 0; Round < 60; ++Round)
	{
		const std::vector<StarPoint> P = Stars(Rng, 3 + Rng.NextInt(25), 1000);
		const StarMesh Mesh = StarMeshBuild(P);
		const std::vector<int>& H = Mesh.Hull;
		const int N = static_cast<int>(P.size()), Hn = static_cast<int>(H.size());
		if (Hn != HullSize(P)) return false;
		for (int i = 0; i < Hn; ++i)
			for (int k = 0; k < N; ++k)
				if (k != H[i] && k != H[(i + 1) % Hn] && Orient(P[H[i]], P[H[(i + 1) % Hn]], P[k]) <= 0) return false;
		const std::vector<std::vector<int>> Nb = StarMeshNeighbours(N, Mesh.Triangles);
		int Degrees = 0;
		for (int i = 0; i < N; ++i)
		{
			Degrees += static_cast<int>(Nb[i].size());
			for (int j : Nb[i])
				if (!std::binary_search(Nb[j].begin(), Nb[j].end(), i)) return false;
		}
		if (Degrees != 2 * (3 * N - 3 - Hn)) return false;
		for (int q = 0; q < 50; ++q)
		{
			const int64_t X = Rng.NextInt(2401) - 1200;
			const StarPoint At{ X, Rng.NextInt(2401) - 1200 };
			const int Found = StarMeshLocate(P, Mesh.Triangles, At);
			bool Inside = true;
			for (int i = 0; i < Hn; ++i) Inside = Inside && Orient(P[H[i]], P[H[(i + 1) % Hn]], At) >= 0;
			if ((Found >= 0) != Inside) return false;
			if (Found >= 0)
			{
				const StarTriangle& T = Mesh.Triangles[static_cast<size_t>(Found)];
				if (Orient(P[T.A], P[T.B], At) < 0 || Orient(P[T.B], P[T.C], At) < 0 || Orient(P[T.C], P[T.A], At) < 0)
					return false;
			}
		}
	}
	return true;
}

} // namespace

int main(int argc, char** argv)
{
	stable_test::CheckParity(argc > 1 ? argv[1] : "ark_star_mesh_parity.txt", ParityLines());
	Check("triangles match brute force on random skies", MatchesBruteForce());
	Check("400-star sky has empty circumcircles", FullSky());
	const int64_t M = StarMeshMaxCoord;
	Check("in-circle is exact at the sky's corners",
		StarInCircle({ -M, -M }, { M, -M }, { M, M }, { -M, M }) == 0
		&& StarInCircle({ -M, -M }, { M, -M }, { M, M }, { 0, 0 }) == 1
		&& StarInCircle({ -M, -M }, { M, -M }, { M, M }, { -M, M - 1 }) == 1
		&& StarInCircle({ -M, -M + 1 }, { M, -M }, { M, M }, { -M, M }) == -1);
	Check("bad skies are refused", StarMeshTriangulate({ { 0, 0 }, { 1, 1 } }).empty()
		&& StarMeshTriangulate({ { 0, 0 }, { 1, 1 }, { 2, 2 } }).empty()
		&& StarMeshTriangulate({ { 0, 0 }, { 0, 0 }, { 2, 3 } }).empty()
		&& StarMeshTriangulate({ { 0, 0 }, { 1, 0 }, { 0, M + 1 } }).empty()
		&& StarMeshTriangulate(std::vector<StarPoint>(StarMeshMaxPoints + 1)).empty());
	Check("hull, neighbours and locate match brute force", QueriesMatchBruteForce());
	const StarMesh Quad = StarMeshBuild({ { 0, 0 }, { 1, 5 }, { 2, -5 }, { 3, 0 } });
	Check("a badly inserted quadrilateral takes one flip", Quad.Flips == 1 && Quad.Hull == std::vector<int>{ 0, 2, 3, 1 });
	Check("refusals are named", StarMeshCheck({ { 0, 0 }, { 0, 0 }, { 2, 3 } }) == StarMeshProblem::Duplicate
		&& StarMeshBuild({ { 0, 0 }, { 1, 1 }, { 2, 2 } }).Hull.empty()
		&& std::string(StarMeshProblemName(StarMeshProblem::Collinear)) == "collinear");
	Check("the quest counts triangles", StarMeshQuestAnswer({ { 0, 0 }, { 4, 0 }, { 0, 4 }, { 5, 5 } }, 2)
		&& !StarMeshQuestAnswer({ { 0, 0 }, { 4, 0 }, { 0, 4 } }, 2) && !StarMeshQuestAnswer({ { 0, 0 } }, 0));
	return stable_test::Finish();
}
