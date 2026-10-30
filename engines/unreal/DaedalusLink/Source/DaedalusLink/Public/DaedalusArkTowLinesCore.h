// SPDX-License-Identifier: MIT
// G569 The Tow Lines (art-master-flex), plain C++17, header-only, no Unreal types (G584 port).
// Link-cut tree (Sleator-Tarjan) over the ark's towing forest: tie and cut tow lines, ask whether two skiffs are
// joined, change a skiff's load, and read the heaviest and total load on the tow path between two skiffs, each in
// amortized O(log n). Splaying is iterative, so long chains cannot overflow the stack. Must agree with
// com.daedalus.world.ark.TowLines line for line (ark_tow_lines_parity.txt, checked by TowLinesParityTest.java and
// ark_tow_lines_core_test.cpp).
#pragma once
#include <algorithm>
#include <cstdint>
#include <initializer_list>
#include <limits>
#include <vector>

namespace daedalus { namespace ark {

constexpr const char* TowLinesQuest = "q_tow_lines";
constexpr int TowMaxSkiffs = 300000;
// What PathMax returns when two skiffs are not joined or not on the board.
constexpr int64_t TowUnjoined = std::numeric_limits<int64_t>::min();

struct TowLine { int A, B; };

// The bosun's tow board. Build with one load per skiff (1..TowMaxSkiffs skiffs, no lines tied); Valid() is false
// otherwise. Every call checks its skiffs with Has() and refuses quietly, so nothing here can fault.
class TowLines
{
public:
	explicit TowLines(const std::vector<int64_t>& Loads)
	{
		const int N = static_cast<int>(Loads.size());
		if (N < 1 || N > TowMaxSkiffs) return;
		Left.assign(N, -1);
		Right.assign(N, -1);
		Parent.assign(N, -1);
		Flip.assign(N, 0);
		Weight = Heaviest = Total = Loads;
		Stack.assign(N, 0);
		Skiffs = N;
	}

	bool Valid() const { return Skiffs > 0; }
	int Size() const { return Skiffs; }
	bool Has(int A) const { return A >= 0 && A < Skiffs; }

	// Ties a tow line between two skiffs; false when they are already joined (no loops) or off the board.
	bool Link(int A, int B)
	{
		if (!Joinable(A, B) || Joined(A, B)) return false;
		MakeRoot(A);
		Parent[A] = B;
		return true;
	}

	// Cuts the tow line between two skiffs; false when no such line is tied.
	bool Cut(int A, int B)
	{
		if (!Joinable(A, B) || A == B) return false;
		MakeRoot(A);
		Access(B);
		if (Left[B] != A || Right[A] != -1 || Left[A] != -1) return false;
		Left[B] = -1;
		Parent[A] = -1;
		Pull(B);
		return true;
	}

	// True when some path of tow lines joins the two skiffs.
	bool Joined(int A, int B) { return Joinable(A, B) && FindRoot(A) == FindRoot(B); }

	// Changes the load on one skiff (ignored off the board).
	void SetLoad(int A, int64_t Value)
	{
		if (!Has(A)) return;
		Access(A);
		Weight[A] = Value;
		Pull(A);
	}

	int64_t Load(int A) const { return Has(A) ? Weight[A] : 0; }

	// Heaviest load along the tow path from A to B, both ends included; TowUnjoined when not joined.
	int64_t PathMax(int A, int B) { return ExposePath(A, B) ? Heaviest[B] : TowUnjoined; }
	// Total load along the tow path from A to B, both ends included; 0 when not joined (check Joined first).
	int64_t PathSum(int A, int B) { return ExposePath(A, B) ? Total[B] : 0; }

private:
	int Skiffs = 0;
	std::vector<int> Left, Right, Parent, Stack;
	std::vector<char> Flip;
	std::vector<int64_t> Weight, Heaviest, Total;

	bool Joinable(int A, int B) const { return Has(A) && Has(B); }

	bool ExposePath(int A, int B)
	{
		if (!Joined(A, B)) return false;
		MakeRoot(A);
		Access(B);
		return true;
	}

	bool IsRoot(int X) const
	{
		const int P = Parent[X];
		return P == -1 || (Left[P] != X && Right[P] != X);
	}

	void Pull(int X)
	{
		int64_t M = Weight[X], S = Weight[X];
		for (int C : { Left[X], Right[X] })
		{
			if (C == -1) continue;
			M = std::max(M, Heaviest[C]);
			S += Total[C];
		}
		Heaviest[X] = M;
		Total[X] = S;
	}

	void Push(int X)
	{
		if (!Flip[X]) return;
		std::swap(Left[X], Right[X]);
		if (Left[X] != -1) Flip[Left[X]] ^= 1;
		if (Right[X] != -1) Flip[Right[X]] ^= 1;
		Flip[X] = 0;
	}

	void Rotate(int X)
	{
		const int P = Parent[X], G = Parent[P];
		const bool ParentIsRoot = IsRoot(P);
		if (Left[P] == X)
		{
			Left[P] = Right[X];
			if (Right[X] != -1) Parent[Right[X]] = P;
			Right[X] = P;
		}
		else
		{
			Right[P] = Left[X];
			if (Left[X] != -1) Parent[Left[X]] = P;
			Left[X] = P;
		}
		Parent[P] = X;
		Parent[X] = G;
		if (!ParentIsRoot) (Left[G] == P ? Left[G] : Right[G]) = X;
		Pull(P);
		Pull(X);
	}

	void Splay(int X)
	{
		int Top = 0;
		Stack[Top++] = X;
		for (int Y = X; !IsRoot(Y);) Stack[Top++] = Y = Parent[Y];
		while (Top > 0) Push(Stack[--Top]);
		while (!IsRoot(X))
		{
			const int P = Parent[X];
			if (!IsRoot(P))
			{
				const int G = Parent[P];
				Rotate((Left[G] == P) == (Left[P] == X) ? P : X);
			}
			Rotate(X);
		}
	}

	void Access(int X)
	{
		for (int Y = X, Last = -1; Y != -1; Last = Y, Y = Parent[Y])
		{
			Splay(Y);
			Right[Y] = Last;
			Pull(Y);
		}
		Splay(X);
	}

	void MakeRoot(int X)
	{
		Access(X);
		Flip[X] ^= 1;
		Push(X);
	}

	int FindRoot(int X)
	{
		Access(X);
		int Y = X;
		Push(Y);
		while (Left[Y] != -1)
		{
			Y = Left[Y];
			Push(Y);
		}
		Splay(Y);
		return Y;
	}
};

// Quest q_tow_lines: ties Lines in order (a line that would close a loop stays untied) and returns the heaviest
// load on the tow path between skiffs A and B, or -1 when they end up not joined (as TowLines.quest in Java).
inline int64_t TowQuest(const std::vector<int64_t>& Loads, const std::vector<TowLine>& Lines, int A, int B)
{
	TowLines Board(Loads);
	if (!Board.Valid()) return -1;
	for (const TowLine& L : Lines) Board.Link(L.A, L.B);
	return Board.Joined(A, B) ? Board.PathMax(A, B) : -1;
}

} } // namespace daedalus::ark
