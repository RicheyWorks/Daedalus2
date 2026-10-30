// SPDX-License-Identifier: MIT
// G441 The Star Mesh (art-master-flex), plain C++17, header-only, no Unreal types (G588 port).
// Exact Delaunay triangulation of integer stars: insert in x order, join each star to the hull edges it sees, then
// flip edges (Lawson) until every edge is locally Delaunay. StarMeshBuild also returns the hull and the flip count;
// StarMeshNeighbours and StarMeshLocate answer adjacency and point-location queries; StarMeshProblem names why a sky
// is refused. Orientation fits in int64; the in-circle determinant is
// summed exactly in 128-bit two's complement, so no floating point and no big integers. Must agree with
// com.daedalus.world.ark.StarMesh line for line (ark_star_mesh_parity.txt, checked by StarMeshParityTest.java and
// ark_star_mesh_core_test.cpp).
#pragma once
#include <algorithm>
#include <cstdint>
#include <cstdlib>
#include <numeric>
#include <unordered_map>
#include <vector>

namespace daedalus { namespace ark {

constexpr const char* StarMeshQuest = "q_star_mesh";
constexpr int StarMeshMaxPoints = 400;
constexpr int64_t StarMeshMaxCoord = 1000000;

struct StarPoint { int64_t X, Y; };
struct StarTriangle { int A, B, C; }; // counter-clockwise indices into the input stars

// A built mesh: triangles in StarMesh.triangulate order, the hull counter-clockwise from the lowest-x (then lowest-y)
// star, and how many Lawson flips the build made. Empty when the sky is refused.
struct StarMesh
{
	std::vector<StarTriangle> Triangles;
	std::vector<int> Hull;
	int Flips = 0;
};

// Why a sky is refused, checked in this order (names match StarMesh.problem in Java).
enum class StarMeshProblem { None, Few, Many, Range, Duplicate, Collinear };

inline const char* StarMeshProblemName(StarMeshProblem P)
{
	switch (P)
	{
	case StarMeshProblem::None: return "ok";
	case StarMeshProblem::Few: return "few";
	case StarMeshProblem::Many: return "many";
	case StarMeshProblem::Range: return "range";
	case StarMeshProblem::Duplicate: return "duplicate";
	case StarMeshProblem::Collinear: return "collinear";
	}
	return "?";
}

namespace star_detail {

// Signed 128-bit value as two 64-bit words, just enough for a sum of six int64 x int64 products.
struct Wide
{
	uint64_t Lo = 0, Hi = 0;

	static Wide Product(int64_t A, int64_t B)
	{
		const bool Negative = (A < 0) != (B < 0);
		const uint64_t UA = A < 0 ? 0 - static_cast<uint64_t>(A) : static_cast<uint64_t>(A);
		const uint64_t UB = B < 0 ? 0 - static_cast<uint64_t>(B) : static_cast<uint64_t>(B);
		const uint64_t A0 = UA & 0xffffffffULL, A1 = UA >> 32, B0 = UB & 0xffffffffULL, B1 = UB >> 32;
		const uint64_t P00 = A0 * B0, P01 = A0 * B1, P10 = A1 * B0, P11 = A1 * B1;
		const uint64_t Mid = (P00 >> 32) + (P01 & 0xffffffffULL) + (P10 & 0xffffffffULL);
		Wide W;
		W.Lo = (Mid << 32) | (P00 & 0xffffffffULL);
		W.Hi = P11 + (P01 >> 32) + (P10 >> 32) + (Mid >> 32);
		return Negative ? W.Negated() : W;
	}

	Wide Negated() const
	{
		Wide W;
		W.Lo = ~Lo + 1;
		W.Hi = ~Hi + (W.Lo == 0 ? 1 : 0);
		return W;
	}

	Wide operator+(const Wide& O) const
	{
		Wide W;
		W.Lo = Lo + O.Lo;
		W.Hi = Hi + O.Hi + (W.Lo < Lo ? 1 : 0);
		return W;
	}

	Wide operator-(const Wide& O) const { return *this + O.Negated(); }

	int Sign() const { return (Hi >> 63) ? -1 : (Hi | Lo) ? 1 : 0; }
};

inline int64_t Orient(const StarPoint& A, const StarPoint& B, const StarPoint& C)
{
	return (B.X - A.X) * (C.Y - A.Y) - (B.Y - A.Y) * (C.X - A.X);
}

inline int64_t Key(int A, int B) { return static_cast<int64_t>(A) << 32 | static_cast<uint32_t>(B); }

} // namespace star_detail

// Positive when D lies inside the circumcircle of counter-clockwise A, B, C (exact for coordinates within 10^6).
inline int StarInCircle(const StarPoint& A, const StarPoint& B, const StarPoint& C, const StarPoint& D)
{
	using star_detail::Wide;
	const StarPoint P[3] = { A, B, C };
	int64_t Dx[3], Dy[3], Sq[3];
	for (int i = 0; i < 3; ++i)
	{
		Dx[i] = P[i].X - D.X;
		Dy[i] = P[i].Y - D.Y;
		Sq[i] = Dx[i] * Dx[i] + Dy[i] * Dy[i];
	}
	// Laplace expansion of | Dx Dy Sq | as six products (Dx_i * Dy_j) * Sq_k, each well inside 128 bits.
	const Wide Det = Wide::Product(Dx[0] * Dy[1], Sq[2]) - Wide::Product(Dx[0] * Dy[2], Sq[1])
		- Wide::Product(Dx[1] * Dy[0], Sq[2]) + Wide::Product(Dx[1] * Dy[2], Sq[0])
		+ Wide::Product(Dx[2] * Dy[0], Sq[1]) - Wide::Product(Dx[2] * Dy[1], Sq[0]);
	return Det.Sign();
}

// Needs 3..StarMeshMaxPoints distinct stars within +-StarMeshMaxCoord, no three collinear.
inline StarMeshProblem StarMeshCheck(const std::vector<StarPoint>& Pts)
{
	const int N = static_cast<int>(Pts.size());
	if (N < 3) return StarMeshProblem::Few;
	if (N > StarMeshMaxPoints) return StarMeshProblem::Many;
	for (const StarPoint& P : Pts)
		if (std::llabs(P.X) > StarMeshMaxCoord || std::llabs(P.Y) > StarMeshMaxCoord) return StarMeshProblem::Range;
	for (int i = 0; i < N; ++i)
		for (int j = i + 1; j < N; ++j)
			if (Pts[i].X == Pts[j].X && Pts[i].Y == Pts[j].Y) return StarMeshProblem::Duplicate;
	for (int i = 0; i < N; ++i)
		for (int j = i + 1; j < N; ++j)
			for (int k = j + 1; k < N; ++k)
				if (star_detail::Orient(Pts[i], Pts[j], Pts[k]) == 0) return StarMeshProblem::Collinear;
	return StarMeshProblem::None;
}

inline bool StarMeshValid(const std::vector<StarPoint>& Pts) { return StarMeshCheck(Pts) == StarMeshProblem::None; }

// The Delaunay mesh (same order as StarMesh.build); empty when the stars are not StarMeshValid.
inline StarMesh StarMeshBuild(const std::vector<StarPoint>& Pts)
{
	using star_detail::Key;
	using star_detail::Orient;
	StarMesh Mesh;
	std::vector<StarTriangle> Tris;
	if (!StarMeshValid(Pts)) return Mesh;
	const int N = static_cast<int>(Pts.size());
	std::vector<int> Order(N);
	std::iota(Order.begin(), Order.end(), 0);
	std::stable_sort(Order.begin(), Order.end(), [&](int I, int J) {
		return Pts[I].X != Pts[J].X ? Pts[I].X < Pts[J].X : Pts[I].Y < Pts[J].Y;
	});
	std::vector<bool> Alive;
	std::unordered_map<int64_t, int> Edge;
	// Presized for a typical build (about 2n live triangles plus two per flip, 3 directed edges per live one).
	Tris.reserve(static_cast<size_t>(4 * N));
	Alive.reserve(static_cast<size_t>(4 * N));
	Edge.reserve(static_cast<size_t>(6 * N));
	auto Add = [&](int A, int B, int C) {
		const int Id = static_cast<int>(Tris.size());
		Tris.push_back({ A, B, C });
		Alive.push_back(true);
		Edge[Key(A, B)] = Id;
		Edge[Key(B, C)] = Id;
		Edge[Key(C, A)] = Id;
	};
	auto Third = [](const StarTriangle& T, int U, int V) {
		return T.A != U && T.A != V ? T.A : T.B != U && T.B != V ? T.B : T.C;
	};
	std::vector<StarTriangle> Stack; // pending edges (A, B); C unused
	auto Legalize = [&](int U, int V) {
		const auto E1 = Edge.find(Key(U, V)), E2 = Edge.find(Key(V, U));
		if (E1 == Edge.end() || E2 == Edge.end()) return;
		const int T1 = E1->second, T2 = E2->second;
		const int C = Third(Tris[T1], U, V), D = Third(Tris[T2], U, V);
		if (StarInCircle(Pts[U], Pts[V], Pts[C], Pts[D]) <= 0) return;
		++Mesh.Flips;
		for (int Id : { T1, T2 })
		{
			const StarTriangle T = Tris[Id];
			Edge.erase(Key(T.A, T.B));
			Edge.erase(Key(T.B, T.C));
			Edge.erase(Key(T.C, T.A));
			Alive[Id] = false;
		}
		Add(U, D, C);
		Add(D, V, C);
		Stack.push_back({ U, D, 0 });
		Stack.push_back({ D, V, 0 });
		Stack.push_back({ V, C, 0 });
		Stack.push_back({ C, U, 0 });
	};

	int A = Order[0], B = Order[1], C = Order[2];
	if (Orient(Pts[A], Pts[B], Pts[C]) < 0) std::swap(B, C);
	Add(A, B, C);
	std::vector<int> Hull{ A, B, C }, Next;
	std::vector<bool> Sees;
	for (int s = 3; s < N; ++s)
	{
		const int P = Order[s];
		const int H = static_cast<int>(Hull.size());
		Sees.assign(H, false);
		for (int i = 0; i < H; ++i) Sees[i] = Orient(Pts[Hull[i]], Pts[Hull[(i + 1) % H]], Pts[P]) < 0;
		int Start = 0;
		while (!(Sees[Start] && !Sees[(Start + H - 1) % H])) ++Start;
		Next.clear();
		int i = Start;
		Next.push_back(Hull[i]);
		while (Sees[i])
		{
			const int U = Hull[i], V = Hull[(i + 1) % H];
			Add(V, U, P);
			Stack.push_back({ U, V, 0 });
			i = (i + 1) % H;
		}
		Next.push_back(P);
		for (int j = i; j != Start; j = (j + 1) % H) Next.push_back(Hull[j]);
		Hull.swap(Next);
		while (!Stack.empty())
		{
			const StarTriangle E = Stack.back();
			Stack.pop_back();
			Legalize(E.A, E.B);
		}
	}
	for (size_t t = 0; t < Tris.size(); ++t)
		if (Alive[t]) Mesh.Triangles.push_back(Tris[t]);
	const int First = static_cast<int>(std::find(Hull.begin(), Hull.end(), Order[0]) - Hull.begin());
	for (size_t k = 0; k < Hull.size(); ++k) Mesh.Hull.push_back(Hull[(First + k) % Hull.size()]);
	return Mesh;
}

// Delaunay triangles in the same order as StarMesh.triangulate; empty when the stars are not StarMeshValid.
inline std::vector<StarTriangle> StarMeshTriangulate(const std::vector<StarPoint>& Pts)
{
	return StarMeshBuild(Pts).Triangles;
}

// Each star's mesh neighbours, ascending.
inline std::vector<std::vector<int>> StarMeshNeighbours(int N, const std::vector<StarTriangle>& Tris)
{
	std::vector<std::vector<int>> Out(static_cast<size_t>(N));
	for (const StarTriangle& T : Tris)
	{
		const int V[3] = { T.A, T.B, T.C };
		for (int k = 0; k < 3; ++k)
		{
			Out[static_cast<size_t>(V[k])].push_back(V[(k + 1) % 3]);
			Out[static_cast<size_t>(V[(k + 1) % 3])].push_back(V[k]);
		}
	}
	for (std::vector<int>& L : Out)
	{
		std::sort(L.begin(), L.end());
		L.erase(std::unique(L.begin(), L.end()), L.end());
	}
	return Out;
}

struct StarEdge { int A, B; }; // A < B

// Every mesh edge once, sorted by A then B; there are 3n - 3 - hull of them.
inline std::vector<StarEdge> StarMeshEdges(int N, const std::vector<StarTriangle>& Tris)
{
	std::vector<StarEdge> Out;
	const std::vector<std::vector<int>> Nb = StarMeshNeighbours(N, Tris);
	for (int A = 0; A < N; ++A)
		for (int B : Nb[static_cast<size_t>(A)])
			if (A < B) Out.push_back({ A, B });
	return Out;
}

// The navigator's chart lines: the Euclidean minimum spanning tree, taken from the mesh edges (it always lies inside
// the Delaunay mesh). Kruskal over edges ordered by exact squared length, then A, then B; n - 1 edges.
inline std::vector<StarEdge> StarMeshChartLines(const std::vector<StarPoint>& Pts, const std::vector<StarTriangle>& Tris)
{
	const int N = static_cast<int>(Pts.size());
	std::vector<StarEdge> All = StarMeshEdges(N, Tris);
	auto Length = [&Pts](const StarEdge& E) {
		const int64_t Dx = Pts[E.A].X - Pts[E.B].X, Dy = Pts[E.A].Y - Pts[E.B].Y;
		return Dx * Dx + Dy * Dy;
	};
	std::sort(All.begin(), All.end(), [&](const StarEdge& L, const StarEdge& R) {
		const int64_t Ll = Length(L), Rl = Length(R);
		return Ll != Rl ? Ll < Rl : L.A != R.A ? L.A < R.A : L.B < R.B;
	});
	std::vector<int> Parent(static_cast<size_t>(N));
	std::iota(Parent.begin(), Parent.end(), 0);
	auto Root = [&Parent](int X) {
		while (Parent[X] != X) X = Parent[X] = Parent[Parent[X]];
		return X;
	};
	std::vector<StarEdge> Out;
	for (const StarEdge& E : All)
	{
		const int Ra = Root(E.A), Rb = Root(E.B);
		if (Ra != Rb)
		{
			Parent[Ra] = Rb;
			Out.push_back(E);
		}
	}
	return Out;
}

// The first triangle (in mesh order) holding Q, edges and corners included, or -1 when Q is outside the hull.
inline int StarMeshLocate(const std::vector<StarPoint>& Pts, const std::vector<StarTriangle>& Tris, const StarPoint& Q)
{
	using star_detail::Orient;
	for (size_t i = 0; i < Tris.size(); ++i)
	{
		const StarTriangle& T = Tris[i];
		if (Orient(Pts[T.A], Pts[T.B], Q) >= 0 && Orient(Pts[T.B], Pts[T.C], Q) >= 0 && Orient(Pts[T.C], Pts[T.A], Q) >= 0)
			return static_cast<int>(i);
	}
	return -1;
}

// True when no star lies strictly inside any triangle's circumcircle.
inline bool StarMeshEmptyCircles(const std::vector<StarPoint>& Pts, const std::vector<StarTriangle>& Tris)
{
	for (const StarTriangle& T : Tris)
		for (int i = 0; i < static_cast<int>(Pts.size()); ++i)
			if (i != T.A && i != T.B && i != T.C && StarInCircle(Pts[T.A], Pts[T.B], Pts[T.C], Pts[i]) > 0)
				return false;
	return true;
}

// Quest q_star_mesh: the navigator names how many triangles the star mesh has (false for invalid stars).
inline bool StarMeshQuestAnswer(const std::vector<StarPoint>& Pts, int Answer)
{
	return StarMeshValid(Pts) && static_cast<int>(StarMeshTriangulate(Pts).size()) == Answer;
}

} } // namespace daedalus::ark
