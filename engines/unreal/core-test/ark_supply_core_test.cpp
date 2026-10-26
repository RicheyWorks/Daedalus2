// SPDX-License-Identifier: MIT
// G29 Ark Supply Run C++ port, checked without Unreal. Build (MSVC, from this folder, vcvars64):
//   cl /nologo /EHs-c- /D_HAS_EXCEPTIONS=0 /std:c++17 /W4 /WX /I ..\DaedalusLink\Source\DaedalusLink\Public ark_supply_core_test.cpp
// --write regenerates ark_supply_parity.txt, which ArkSupplyParityTest (daedalus-core) replays line for line.
#ifndef _CRT_SECURE_NO_WARNINGS
#define _CRT_SECURE_NO_WARNINGS 1
#endif
#include "DaedalusArkSupplyCore.h"
#include <cstdio>
#include <cstring>
#include <string>
using namespace daedalus::supply;
static int Passed = 0, Total = 0;
static void Expect(const char* Name, bool OK) { ++Total; Passed += OK; std::printf("%s %s\n", OK ? "PASS" : "FAIL", Name); }

static int64_t IslandSeed(int S) { return S % 2 == 0 ? static_cast<int64_t>(S) * 1000003LL : -static_cast<int64_t>(S) * 1000003LL - 1; }

static std::vector<std::string> Scenario(int S)
{
	std::vector<std::string> Out;
	const int64_t Isle = IslandSeed(S);
	const std::vector<Request> Reqs = ForIsland(Isle);
	std::vector<Passenger> P; for (int I = 0; I < S % 5; ++I) P.push_back({ "p" + std::to_string(I), "sheep", 1 + I % 3, (I % 2) * 2 });
	std::vector<Crew> C; for (int I = 0; I < 1 + S % 3; ++I) C.push_back({ "c" + std::to_string(I), "deckhand", 40 + 15 * I, 2 + (S + I) % 4 });
	Run R;
	const bool Ok = R.Init("ark-" + std::to_string(S), { 0, 64, 0 }, { S * 37 % 500, 64 + S % 7, S * 53 % 400 }, P, C, Reqs);
	std::string L = "run s=" + std::to_string(S) + " isle=" + std::to_string(Isle) + " ok=" + (Ok ? "1" : "0") + " dur=" + std::to_string(R.DurationMs) + " watches=" + std::to_string(R.Watches)
		+ " water=" + std::to_string(R.WaterNeeded()) + " fodder=" + std::to_string(R.FodderNeeded()) + " cap=" + std::to_string(R.CrewCapacityKg()) + " reqs=";
	for (const Request& Q : Reqs) L += Q.RequestId + ":" + CargoName(Q.What) + ":" + std::to_string(Q.Units) + "|";
	Out.push_back(L);
	std::string Ld = "load s=" + std::to_string(S);
	auto Do = [&](Cargo X, int N) { if (N > 0) Ld += std::string(" ") + CargoName(X) + "x" + std::to_string(N) + "=" + LoadName(R.Load(X, N)); };
	Do(Cargo::WaterCask, R.WaterNeeded());
	Do(Cargo::FodderBale, R.FodderNeeded());
	for (const Request& Q : Reqs) Do(Q.What, Q.Units);
	Do(Cargo::TimberBundle, 3);
	Do(Cargo::SalveJar, 50);
	Do(Cargo::WaterCask, 60);
	const daedalus::supply::Check K = R.CheckHold();
	Ld += " kg=" + std::to_string(R.HeldKg) + " vol=" + std::to_string(R.HeldVolume) + " check=" + std::to_string(K.WaterShort) + "," + std::to_string(K.FodderShort) + " short=";
	for (const std::string& X : K.RequestsShort) Ld += X + "|";
	Ld += std::string(" ready=") + (K.Ready() ? "1" : "0");
	Out.push_back(Ld);
	R.Depart(1000);
	const int64_t At = 1000 + R.DurationMs;
	Delivery D;
	std::string Dv = "sail s=" + std::to_string(S) + " status=" + StatusName(R.State) + " early=" + (R.Arrived(At - 1) ? "1" : "0") + "," + (R.Deliver(At - 1, D) ? "1" : "0");
	const bool Got = R.Deliver(At, D);
	Dv += " got=" + std::string(Got ? "1" : "0") + " ark=" + D.ArkId + " watches=" + std::to_string(D.Watches) + " kg=" + std::to_string(D.KgCarried) + " met=" + std::to_string(D.RequestsMet) + "/" + std::to_string(D.RequestsTotal)
		+ " fed=" + std::to_string(D.PassengersFed) + "/" + std::to_string(D.PassengersTotal) + " at=" + std::to_string(D.ArrivedAtMs) + " complete=" + (D.Complete() ? "1" : "0");
	Delivery D2;
	R.Deliver(At + 99999, D2);
	Dv += " again=" + std::to_string(D2.ArrivedAtMs) + " status=" + StatusName(R.State);
	Out.push_back(Dv);
	return Out;
}

int main(int argc, char** argv)
{
	const bool WriteOut = argc > 1 && std::strcmp(argv[1], "--write") == 0;
	Expect("cargo table", Kg(Cargo::WaterCask) == 10 && Volume(Cargo::TimberBundle) == 4 && Kg(Cargo::SalveJar) == 1);
	Expect("key pattern", Key("a") && Key("isle-0-1") && Key("a_b.c:d") && !Key("") && !Key("Ab") && !Key("-a") && Key(std::string(96, 'a')) && !Key(std::string(97, 'a')));
	Expect("duration = harbour + round(cubes*1000/12)", Duration({ 0, 0, 0 }, { 12, 0, 0 }) == 5000 && Duration({ 0, 0, 0 }, { 0, 0, 0 }) == 4000);
	Expect("base36 unsigned", Base36(0) == "0" && Base36(35) == "z" && Base36(36) == "10" && Base36(static_cast<uint64_t>(-1LL)) == "3w5e11264sgsf");
	Run R; std::vector<Crew> Cw = { { "c0", "deckhand", 100, 10 } };
	Expect("init refuses no crew / bad id", !R.Init("ark", { 0, 0, 0 }, { 1, 0, 0 }, {}, {}, {}) && !R.Init("Ark", { 0, 0, 0 }, { 1, 0, 0 }, {}, Cw, {}) && R.Init("ark", { 0, 0, 0 }, { 1, 0, 0 }, {}, Cw, {}));
	Expect("load limits", R.Load(Cargo::TimberBundle, 31) == LoadResult::OverVolume && R.Load(Cargo::WaterCask, 101) == LoadResult::OverWeight && R.Load(Cargo::WaterCask, 0) == LoadResult::Refused && R.Load(Cargo::WaterCask, 5) == LoadResult::Loaded);
	std::vector<std::string> Lines;
	for (int S = 0; S < 20; ++S) for (const std::string& L : Scenario(S)) Lines.push_back(L);
	bool AnyComplete = false, AnyShort = false;
	for (const std::string& L : Lines) { AnyComplete = AnyComplete || L.find(" complete=1") != std::string::npos; AnyShort = AnyShort || L.find(" complete=0") != std::string::npos; }
	Expect("scripted runs include complete and short deliveries", AnyComplete && AnyShort);
	if (WriteOut)
	{
		std::FILE* F = std::fopen("ark_supply_parity.txt", "wb");
		if (!F) { std::printf("FAIL cannot write parity\n"); return 1; }
		std::fputs("# ark_supply_core_test.cpp --write: G29 Ark Supply Run parity (unreal-epic-boss). 20 islands x load/check/sail/deliver.\n", F);
		for (const std::string& L : Lines) std::fprintf(F, "%s\n", L.c_str());
		std::fclose(F);
		std::printf("wrote ark_supply_parity.txt (%d lines)\n", static_cast<int>(Lines.size()));
	}
	std::printf("%d/%d passed\n", Passed, Total);
	return Passed == Total ? 0 : 1;
}