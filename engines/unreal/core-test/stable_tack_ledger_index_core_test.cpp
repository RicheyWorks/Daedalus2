// SPDX-License-Identifier: MIT
// G545 Tack Ledger Index C++ port (G567), checked without Unreal:
//   g++ -std=c++17 -Wall -Wextra -Wshadow -Werror -I../DaedalusLink/Source/DaedalusLink/Public stable_tack_ledger_index_core_test.cpp
//   ./a.out stable_tack_ledger_index_parity.txt
#include "DaedalusStableTackLedgerIndexCore.h"
#include "stable_parity.h"
using namespace daedalus::stable;
using stable_test::Check;
using stable_test::Join;

int main(int argc, char** argv)
{
	const char* Path = argc > 1 ? argv[1] : "stable_tack_ledger_index_parity.txt";
	std::vector<std::string> Lines;
	for (int s = 1; s <= 60; ++s)
	{
		const std::vector<int> F = LedgerFrequencies(s, s % 12, 20);
		const LedgerFiling B = LedgerBest(F), G = LedgerMostAskedRoot(F);
		Lines.push_back("seed=" + std::to_string(s) + " freq=" + Join(F) + " best=" + std::to_string(B.Flips) + ":" + Join(B.Order)
			+ " mostasked=" + std::to_string(G.Flips) + ":" + Join(G.Order));
	}
	stable_test::CheckParity(Path, Lines);
	const std::vector<int> F = LedgerFrequencies(7, 11, 20);
	Check("best filing wins the quest", LedgerQuestDone(F, LedgerBest(F).Order));
	Check("most asked root never beats best", LedgerMostAskedRoot(F).Flips >= LedgerBest(F).Flips);
	Check("repeated entry is invalid", LedgerFlips(F, std::vector<int>(11, 0)) == LedgerInvalid);
	Check("short order is invalid", LedgerFlips(F, { 0 }) == LedgerInvalid);
	return stable_test::Finish();
}
