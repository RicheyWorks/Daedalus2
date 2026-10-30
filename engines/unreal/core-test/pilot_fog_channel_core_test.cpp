// SPDX-License-Identifier: MIT
// G586 Fog Channel Pilot C++ core, checked without Unreal:
//   g++ -std=c++17 -Wall -Wextra -Wshadow -Werror -I../DaedalusLink/Source/DaedalusLink/Public pilot_fog_channel_core_test.cpp
//   ./a.out pilot_fog_channel_parity.txt
#include "DaedalusPilotFogChannelCore.h"
#include "stable_parity.h"
using namespace daedalus::pilot;
using stable_test::Check;
using stable_test::Join;

static std::string Rows(const std::vector<std::vector<int>>& A)
{
	std::string Out;
	for (const auto& Row : A) Out += (Out.empty() ? "" : "/") + Join(Row);
	return Out;
}

int main(int argc, char** argv)
{
	const char* Path = argc > 1 ? argv[1] : "pilot_fog_channel_parity.txt";
	std::vector<std::string> Lines;
	for (int s = 1; s <= 60; ++s)
	{
		const FogHarbour H = FogSeed("fog-" + std::to_string(s));
		const FogTrack B = FogBest(H), G = FogLoudestEcho(H);
		Lines.push_back("seed=fog-" + std::to_string(s) + " open=" + Join(H.Open) + " drift=" + Rows(H.Drift) + " echo=" + Rows(H.Echo)
			+ " heard=" + Join(H.Heard) + " best=" + std::to_string(B.Cost) + ":" + Join(B.Lanes) + " loudest=" + std::to_string(G.Cost)
			+ ":" + Join(G.Lanes));
	}
	stable_test::CheckParity(Path, Lines);
	const FogHarbour H = FogSeed("fog-7");
	Check("best reading wins the quest", FogQuestDone(H, FogBest(H).Lanes));
	Check("trusting each echo never beats best", FogLoudestEcho(H).Cost >= FogBest(H).Cost);
	Check("missing lane is invalid", FogCost(H, std::vector<int>(H.Heard.size(), 9)) == FogInvalid);
	Check("wrong length is invalid", FogCost(H, std::vector<int>(H.Heard.size() + 1, 0)) == FogInvalid);
	return stable_test::Finish();
}
