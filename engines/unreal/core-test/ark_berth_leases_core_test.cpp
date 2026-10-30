// SPDX-License-Identifier: MIT
// G524 The Berth Leases C++ port (G572), checked without Unreal:
//   g++ -std=c++17 -Wall -Wextra -Wshadow -Werror -I../DaedalusLink/Source/DaedalusLink/Public ark_berth_leases_core_test.cpp
//   ./a.out ark_berth_leases_parity.txt
#include "DaedalusArkBerthLeasesCore.h"
#include "ark_trees_test.h"
using namespace daedalus::ark;
using ark_test::S;
using stable_test::Check;

namespace {

struct Lease { int Id; int64_t From, To; };

std::vector<std::string> ParityLines()
{
	std::vector<std::string> Lines;
	for (int s = 1; s <= 60; ++s)
	{
		daedalus::stable::StableRng Rng(1000 + s);
		BerthLeases Ledger(s);
		std::vector<Lease> Held;
		std::string Ops;
		int NextId = 0;
		for (int k = 0; k < 16; ++k)
		{
			const int Kind = Rng.NextInt(4);
			const int64_t From = Rng.NextInt(30);
			const int64_t To = From + Rng.NextInt(8);
			if (Kind <= 1)
			{
				Ledger.Add(NextId, From, To);
				Held.push_back({ NextId, From, To });
				Ops += " add=" + S(NextId++) + ":" + S(From) + "-" + S(To);
			}
			else if (Kind == 2 && !Held.empty())
			{
				const auto Gone = Held.begin() + Rng.NextInt(static_cast<int>(Held.size()));
				Ops += " remove=" + S(Gone->Id) + ":" + (Ledger.Remove(Gone->Id, Gone->From) ? "true" : "false");
				Held.erase(Gone);
			}
			else
			{
				const std::optional<int> C = Ledger.Clash(From, To);
				Ops += " clash=" + S(From) + "-" + S(To) + ":" + (C ? S(*C) : "-");
			}
		}
		for (int k = 0; k < 3; ++k)
		{
			const int64_t X = Rng.NextInt(38);
			Ops += " stab=" + S(X) + ":" + ark_test::Join(Ledger.Stab(X));
		}
		Lines.push_back("seed=" + S(s) + " size=" + S(Ledger.Size()) + Ops);
	}
	return Lines;
}

// Random churn against a plain list: stabs exact, clashes really clash and are missed only when none exists.
bool MatchesBruteForce()
{
	daedalus::stable::StableRng Rng(524);
	BerthLeases Ledger(524);
	std::vector<Lease> Held;
	for (int k = 0; k < 4000; ++k)
	{
		const int64_t From = Rng.NextInt(500), To = From + Rng.NextInt(40);
		const int Kind = Rng.NextInt(5);
		if (Kind <= 1)
		{
			if (!Ledger.Add(k, From, To)) return false;
			Held.push_back({ k, From, To });
		}
		else if (Kind == 2 && !Held.empty())
		{
			const auto Gone = Held.begin() + Rng.NextInt(static_cast<int>(Held.size()));
			if (!Ledger.Remove(Gone->Id, Gone->From) || Ledger.Remove(Gone->Id, Gone->From)) return false;
			Held.erase(Gone);
		}
		else if (Kind == 3)
		{
			std::vector<int> Want;
			for (const Lease& L : Held)
				if (L.From <= From && From <= L.To) Want.push_back(L.Id);
			std::sort(Want.begin(), Want.end());
			if (Ledger.Stab(From) != Want || BerthQuest(Ledger, From) != static_cast<int>(Want.size())) return false;
		}
		else
		{
			const std::optional<int> C = Ledger.Clash(From, To);
			bool Any = false, Real = !C;
			for (const Lease& L : Held)
			{
				const bool Overlaps = L.From <= To && L.To >= From;
				Any = Any || Overlaps;
				Real = Real || (Overlaps && L.Id == *C);
			}
			if (Any != C.has_value() || !Real) return false;
		}
		if (Ledger.Size() != static_cast<int>(Held.size())) return false;
	}
	return true;
}

} // namespace

int main(int argc, char** argv)
{
	stable_test::CheckParity(argc > 1 ? argv[1] : "ark_berth_leases_parity.txt", ParityLines());
	Check("stabs and clashes match a plain list under churn", MatchesBruteForce());
	BerthLeases Ledger(7);
	Check("backwards span is refused", !Ledger.Add(1, 9, 3));
	Check("same lease twice is refused", Ledger.Add(1, 2, 6) && !Ledger.Add(1, 2, 8) && Ledger.Size() == 1);
	Check("touching ends clash, a gap does not", Ledger.Clash(6, 9) == 1 && !Ledger.Clash(7, 9));
	Check("unknown lease is not removed", !Ledger.Remove(1, 3) && Ledger.Remove(1, 2) && Ledger.Size() == 0);
	return stable_test::Finish();
}
