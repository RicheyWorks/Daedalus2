// SPDX-License-Identifier: MIT
// Prismheart hall chord (DaedalusHallChordCore.h): golden vectors from the Python reference (300 halls,
// hall_chord_golden.txt, re-run from the inputs in each line) plus properties: input order and duplicates never matter,
// at most 8 voices, no semitone clash between voices, every voice ear-safe, total gain at most 600, empty hall drones.
// Build: g++ -std=c++17 -Wall -Wextra -Werror -ffp-contract=off hall_chord_core_test.cpp
#include "../DaedalusLink/Source/DaedalusLink/Public/DaedalusHallChordCore.h"

#include <algorithm>
#include <cstdio>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>

using namespace daedalus;
using namespace daedalus::hallchord;

static int Failures = 0, Checks = 0;
static void Check(bool Ok, const std::string& What)
{
	++Checks;
	if (!Ok && ++Failures <= 25) std::printf("FAIL %s\n", What.c_str());
}

static std::string Format(const std::vector<std::pair<std::string, std::uint64_t>>& In, const Chord& C)
{
	std::string L = "in ";
	if (In.empty()) L += "-";
	for (size_t I = 0; I < In.size(); ++I) L += (I ? "," : "") + In[I].first + ":" + std::to_string(In[I].second);
	L += " | voices";
	for (int I = 0; I < C.Count; ++I) L += " " + std::to_string(C.V[I].Hz) + "/" + std::to_string(C.V[I].Gain);
	L += " | env " + std::to_string(C.AttackMs) + "/" + std::to_string(C.ReleaseMs) + "/" + std::to_string(C.SwellMs);
	L += " | dropped " + std::to_string(C.Dropped) + " over " + std::to_string(C.OverCap);
	return L;
}

static Chord Run(const std::vector<std::pair<std::string, std::uint64_t>>& In)
{
	std::vector<Cabinet> Cs(In.size());
	for (size_t I = 0; I < In.size(); ++I) { Cs[I].Id = In[I].first.c_str(); Cs[I].Token = In[I].second; }
	return MakeChord(Cs.data(), static_cast<int>(Cs.size()));
}

static bool Same(const Chord& A, const Chord& B)
{
	if (A.Count != B.Count || A.AttackMs != B.AttackMs || A.SwellMs != B.SwellMs || A.Dropped != B.Dropped || A.OverCap != B.OverCap) return false;
	for (int I = 0; I < A.Count; ++I) if (A.V[I].Hz != B.V[I].Hz || A.V[I].Gain != B.V[I].Gain) return false;
	return true;
}

static void Properties(const std::vector<std::pair<std::string, std::uint64_t>>& In, const Chord& C, int Case)
{
	const std::string Tag = "case " + std::to_string(Case);
	Check(C.Count >= 1 && C.Count <= MaxVoices, Tag + ": voice count 1-8");
	Check(C.TotalGain() <= GainBudget && C.TotalGain() > 0, Tag + ": total gain bounded");
	for (int I = 0; I < C.Count; ++I)
	{
		const earrule::CallSpec S = VoiceCall(C.V[I], C);
		Check(earrule::Ok(S.BaseHz) && earrule::Ok(earrule::PeakHz(S)) && S.Harmonics <= 2 && S.Sweep == 0, Tag + ": voice ear-safe");
		Check(C.V[I].Gain <= GainCap, Tag + ": voice gain cap");
		if (I) Check(C.V[I - 1].Hz < C.V[I].Hz && 100 * (C.V[I].Hz - C.V[I - 1].Hz) >= 6 * C.V[I - 1].Hz, Tag + ": no semitone clash");
	}
	Check(C.AttackMs >= 3000 && C.SwellMs >= 12000, Tag + ": slow swell");
	// Order and duplicates: reversed, rotated, and doubled input give the same chord.
	auto R = In; std::reverse(R.begin(), R.end());
	Check(Same(Run(R), C), Tag + ": reversed input");
	if (!In.empty())
	{
		auto Rot = In; std::rotate(Rot.begin(), Rot.begin() + (Case % In.size()), Rot.end());
		Check(Same(Run(Rot), C), Tag + ": rotated input");
	}
	auto D = In; D.insert(D.end(), In.begin(), In.end());
	Check(Same(Run(D), C), Tag + ": duplicated input");
}

int main(int Argc, char** Argv)
{
	const char* Path = Argc > 1 ? Argv[1] : "engines/unreal/core-test/hall_chord_golden.txt";
	std::ifstream F(Path);
	if (!F) { std::printf("cannot open %s\n", Path); return 2; }
	std::string L;
	int Lines = 0;
	while (std::getline(F, L))
	{
		if (L.empty() || L[0] == '#') continue;
		std::istringstream S(L);
		int Case = 0; std::string In, List;
		S >> Case >> In >> List;
		std::vector<std::pair<std::string, std::uint64_t>> Pairs;
		if (List != "-")
		{
			std::istringstream P(List); std::string Item;
			while (std::getline(P, Item, ','))
			{
				const size_t Colon = Item.rfind(':');
				Pairs.emplace_back(Item.substr(0, Colon), std::stoull(Item.substr(Colon + 1)));
			}
		}
		const Chord C = Run(Pairs);
		const std::string Got = std::to_string(Case) + " " + Format(Pairs, C);
		Check(Got == L, "golden line " + std::to_string(Case) + "\n  want " + L + "\n  got  " + Got);
		Properties(Pairs, C, Case);
		++Lines;
	}
	Check(Lines == 300, "golden has 300 halls");
	const Chord E = MakeChord(nullptr, 0);
	Check(E.Drone && E.Count == 1 && E.V[0].Hz == DroneHz && E.V[0].Gain == DroneGain, "empty hall drones quietly");
	std::printf("%d checks, %d failures\n", Checks, Failures);
	return Failures ? 1 : 0;
}
