// SPDX-License-Identifier: MIT
// Island streaming (ADR-062): Minecraft's view distance for islands, checked without Unreal.
//   g++ -std=c++17 -O1 -Wall -Wextra -Werror -fsanitize=address,undefined -I../DaedalusLink/Source/DaedalusLink/Public stream_core_test.cpp
#include "DaedalusStreamCore.h"
#include <chrono>
#include <cstdio>
#include <limits>
using namespace daedalus::stream;
static int Passed = 0, Total = 0;
static void Check(const char* Name, bool OK) { ++Total; Passed += OK; std::printf("%s %s\n", OK ? "PASS" : "FAIL", Name); }
static int Count(const std::vector<Step>& S, Act A) { int n = 0; for (const Step& s : S) n += s.Do == A; return n; }

int main()
{
	// The real islands' rough layout (cm): Claude Island, Buffffff, Pythagoras, Hephaestus far away.
	std::vector<Island> W = {
		{"/Game/Claude/ClaudeIsland_Sub", 400000, 0, 5000, 60000, false, false},
		{"/Game/Buffffff/Island", 290000, 148500, 0, 40000, false, false},
		{"/Game/Pythagoras/Island", -60000, 60000, 2500, 40000, false, false},
		{"/Game/Hephaestus/Maps/HephaestusIsland", 6000000, 2000000, 0, 60000, false, false},
		{"/Game/Daedalus/Hub", 0, 0, 0, 10000, false, true},
	};
	Settings S;
	S.MaxLoadsPerTick = 2;
	// standing on Claude Island
	std::vector<Step> P = Plan(W, 400000, 0, 5000, S);
	Check("the always-loaded hub loads first", !P.empty() && P[0].Name == "/Game/Daedalus/Hub" && P[0].Do == Act::Load);
	Check("then the island you stand on, capped per tick", P.size() == 2 && P[1].Name == "/Game/Claude/ClaudeIsland_Sub");
	for (Island& I : W) if (I.Name == "/Game/Claude/ClaudeIsland_Sub" || I.Always) I.Loaded = true;
	P = Plan(W, 400000, 0, 5000, S);
	Check("next tick: the neighbour within 1.5 km loads", P.size() == 1 && P[0].Name == "/Game/Buffffff/Island");
	Check("the far island (6 km) never loads", [&] { for (const Step& s : P) if (s.Name.find("Hephaestus") != std::string::npos) return false; return true; }());
	// hysteresis: Buffffff loaded; player walks to 2 km from its edge -> stays; 3 km -> unloads
	for (Island& I : W) if (I.Name == "/Game/Buffffff/Island") I.Loaded = true;
	const double BX = 290000, BY = 148500;
	P = Plan(W, BX + 40000 + 200000, BY, 0, S);
	bool BuffStays = true;
	for (const Step& s : P) if (s.Name == "/Game/Buffffff/Island" && s.Do == Act::Unload) BuffStays = false;
	Check("between load and unload distance an island stays (no flicker)", BuffStays);
	P = Plan(W, BX + 40000 + 300000, BY, 0, S);
	bool BuffGoes = false;
	for (const Step& s : P) if (s.Name == "/Game/Buffffff/Island" && s.Do == Act::Unload) BuffGoes = true;
	Check("past unload distance it unloads", BuffGoes);
	Check("unloads come before loads (free RAM first)", P.empty() || P.front().Do == Act::Unload);
	Check("the always-loaded hub never unloads", [&] { for (const Step& s : Plan(W, 9e6, 9e6, 0, S)) if (s.Name == "/Game/Daedalus/Hub") return false; return true; }());
	// teleport into a crowd: loads capped
	std::vector<Island> Crowd;
	for (int i = 0; i < 50; ++i) Crowd.push_back({"isle" + std::to_string(i), i * 1000.0, 0, 0, 500, false, false});
	S.MaxLoadsPerTick = 3;
	P = Plan(Crowd, 0, 0, 0, S);
	Check("a teleport loads at most MaxLoadsPerTick, nearest first", P.size() == 3 && P[0].Name == "isle0" && P[1].Name == "isle1" && P[2].Name == "isle2");
	// bad settings can't thrash
	Settings Bad;
	Bad.LoadDistance = 1000;
	Bad.UnloadDistance = 500;
	std::vector<Island> One = {{"a", 0, 0, 0, 0, true, false}};
	Check("unload <= load is fixed up (no thrash at 900 cm)", Plan(One, 900, 0, 0, Bad).empty());
	Check("a NaN position does nothing", Plan(One, std::numeric_limits<double>::quiet_NaN(), 0, 0, Settings()).empty());
	Check("inside the island the distance is 0", EdgeDistance({"a", 0, 0, 0, 1000, false, false}, 10, 10, 10) == 0);
	Check("focus keeps mine and the always-loaded", FocusSet(W, "/Game/Claude/ClaudeIsland_Sub") == std::vector<std::string>{"/Game/Claude/ClaudeIsland_Sub", "/Game/Daedalus/Hub"});
	// determinism + cost
	std::vector<Island> Many;
	for (int i = 0; i < 10000; ++i) Many.push_back({"i" + std::to_string(i), (i % 100) * 50000.0, (i / 100) * 50000.0, 0, 20000, (i % 7) == 0, false});
	const auto T0 = std::chrono::steady_clock::now();
	const std::vector<Step> A = Plan(Many, 2500000, 2500000, 0, S), B = Plan(Many, 2500000, 2500000, 0, S);
	const double Ms = std::chrono::duration<double, std::milli>(std::chrono::steady_clock::now() - T0).count() / 2;
	std::printf("  plan over 10000 islands: %.3f ms, %d unloads, %d loads\n", Ms, Count(A, Act::Unload), Count(A, Act::Load));
	bool Same = A.size() == B.size();
	for (size_t i = 0; Same && i < A.size(); ++i) Same = A[i].Name == B[i].Name && A[i].Do == B[i].Do;
	Check("the same world plans the same", Same);
	Check("10000 islands plan in under 5 ms (run every half second, not every frame)", Ms < 5.0);
	std::printf("%d/%d\n", Passed, Total);
	return Passed == Total ? 0 : 1;
}
