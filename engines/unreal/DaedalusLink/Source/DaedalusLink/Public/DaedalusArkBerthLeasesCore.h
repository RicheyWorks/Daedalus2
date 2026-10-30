// SPDX-License-Identifier: MIT
// G524 The Berth Leases (art-master-flex), plain C++17, header-only, no Unreal types (G572 port).
// The harbourmaster's lease ledger: a treap keyed by (lease start, id), each node keeping the latest end in its
// subtree, for O(log n) expected add, remove and clash checks and O(k + log n) stabs. Treap priorities come from
// StableRng::NextLong, so the tree shape, and with it which clashing lease Clash reports, matches
// com.daedalus.world.ark.BerthLeases line for line (ark_berth_leases_parity.txt, checked by
// ArkTreesParityTest.java and ark_berth_leases_core_test.cpp).
#pragma once
#include "DaedalusStableRandom.h"
#include <algorithm>
#include <cstdint>
#include <limits>
#include <optional>
#include <vector>

namespace daedalus { namespace ark {

constexpr const char* BerthLeasesQuest = "q_berth_leases";
constexpr int BerthMaxLeases = 500000;

class BerthLeases
{
public:
	// An empty ledger; the seed fixes the treap shape.
	explicit BerthLeases(int64_t Seed) : Rng(Seed) {}

	int Size() const { return Count; }

	// Leases Id on closed span [From, To]. False (ledger unchanged) when From > To, the ledger is full, or a lease
	// with this Id already starts at From.
	bool Add(int Id, int64_t From, int64_t To)
	{
		if (From > To || Count >= BerthMaxLeases || Find(From, Id) != None) return false;
		const auto [Less, AtLeast] = Split(Root, From, Id);
		Nodes.push_back({ From, To, Id, Rng.NextLong(), To, None, None });
		Root = Merge(Merge(Less, static_cast<int>(Nodes.size()) - 1), AtLeast);
		++Count;
		return true;
	}

	// Removes lease Id that starts at From; returns whether it was on the ledger.
	bool Remove(int Id, int64_t From)
	{
		const int Before = Count;
		Root = Erase(Root, From, Id);
		return Count < Before;
	}

	// Ids of all leases holding tick X, ascending.
	std::vector<int> Stab(int64_t X) const
	{
		std::vector<int> Out;
		Stab(Root, X, Out);
		std::sort(Out.begin(), Out.end());
		return Out;
	}

	int CountAt(int64_t X) const { return static_cast<int>(Stab(X).size()); }

	// A lease sharing at least one tick with [From, To] (From <= To), or nothing when the span is free.
	std::optional<int> Clash(int64_t From, int64_t To) const
	{
		for (int T = Root; T != None;)
		{
			const Node& N = Nodes[T];
			if (N.From <= To && N.To >= From) return N.Id;
			if (N.Left != None && Nodes[N.Left].MaxTo >= From) T = N.Left;
			else T = N.From <= To ? N.Right : None;
		}
		return std::nullopt;
	}

private:
	static constexpr int None = -1;

	struct Node
	{
		int64_t From, To;
		int Id;
		int64_t Prio, MaxTo;
		int Left, Right;
	};

	struct Halves { int Less, AtLeast; };

	stable::StableRng Rng;
	std::vector<Node> Nodes; // removed leases stay as unreachable slots
	int Root = None, Count = 0;

	int64_t MaxTo(int T) const { return T == None ? std::numeric_limits<int64_t>::min() : Nodes[T].MaxTo; }

	void Pull(int T)
	{
		Node& N = Nodes[T];
		N.MaxTo = std::max(N.To, std::max(MaxTo(N.Left), MaxTo(N.Right)));
	}

	int Compare(int64_t From, int Id, int T) const
	{
		const Node& N = Nodes[T];
		if (From != N.From) return From < N.From ? -1 : 1;
		return Id == N.Id ? 0 : (Id < N.Id ? -1 : 1);
	}

	int Find(int64_t From, int Id) const
	{
		for (int T = Root; T != None;)
		{
			const int C = Compare(From, Id, T);
			if (C == 0) return T;
			T = C < 0 ? Nodes[T].Left : Nodes[T].Right;
		}
		return None;
	}

	// Keys below (From, Id) and keys at or above it.
	Halves Split(int T, int64_t From, int Id)
	{
		if (T == None) return { None, None };
		if (Compare(From, Id, T) > 0)
		{
			const Halves H = Split(Nodes[T].Right, From, Id);
			Nodes[T].Right = H.Less;
			Pull(T);
			return { T, H.AtLeast };
		}
		const Halves H = Split(Nodes[T].Left, From, Id);
		Nodes[T].Left = H.AtLeast;
		Pull(T);
		return { H.Less, T };
	}

	int Merge(int A, int B)
	{
		if (A == None) return B;
		if (B == None) return A;
		if (Nodes[A].Prio > Nodes[B].Prio)
		{
			Nodes[A].Right = Merge(Nodes[A].Right, B);
			Pull(A);
			return A;
		}
		Nodes[B].Left = Merge(A, Nodes[B].Left);
		Pull(B);
		return B;
	}

	int Erase(int T, int64_t From, int Id)
	{
		if (T == None) return None;
		const int C = Compare(From, Id, T);
		if (C == 0)
		{
			--Count;
			return Merge(Nodes[T].Left, Nodes[T].Right);
		}
		if (C < 0) Nodes[T].Left = Erase(Nodes[T].Left, From, Id);
		else Nodes[T].Right = Erase(Nodes[T].Right, From, Id);
		Pull(T);
		return T;
	}

	void Stab(int T, int64_t X, std::vector<int>& Out) const
	{
		if (T == None || Nodes[T].MaxTo < X) return;
		const Node& N = Nodes[T];
		Stab(N.Left, X, Out);
		if (N.From > X) return;
		if (N.To >= X) Out.push_back(N.Id);
		Stab(N.Right, X, Out);
	}
};

// Quest q_berth_leases: how many leases hold the shown tick.
inline int BerthQuest(const BerthLeases& Ledger, int64_t Tick) { return Ledger.CountAt(Tick); }

} } // namespace daedalus::ark
