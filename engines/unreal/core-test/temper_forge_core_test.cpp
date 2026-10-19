// SPDX-License-Identifier: MIT
// G19 Anvil and Quench C++ port (G30), checked without Unreal. Build (MSVC):
//   cl /nologo /EHsc /std:c++17 /W4 /WX /I..\DaedalusLink\Source\DaedalusLink\Public temper_forge_core_test.cpp
// or g++ -std=c++17 -O1 -Wall -Wextra -Werror -I../DaedalusLink/Source/DaedalusLink/Public temper_forge_core_test.cpp
// Run with --write to regenerate temper_forge_parity.txt (read by TemperForgeParityTest.java, line for line).
#ifndef _CRT_SECURE_NO_WARNINGS
#define _CRT_SECURE_NO_WARNINGS 1 // MSVC /WX: allow fopen
#endif
#include "DaedalusTemperForgeCore.h"
#include <cstdio>
#include <cstring>
#include <string>
#include <vector>
using namespace daedalus::forge;
static int Passed = 0, Total = 0;
static void Check(const char* Name, bool OK) { ++Total; Passed += OK; std::printf("%s %s\n", OK ? "PASS" : "FAIL", Name); }

static const Material Metals[] = { Material::Copper, Material::Bronze, Material::Iron, Material::Steel, Material::Starmetal };
static const int Shifts[] = { 40, 75, 110, 150, 300 };
constexpr int Variants = 10;

// The parity variants; TemperForgeParityTest.java builds exactly the same runs.
static TemperRun Variant(const TemperBlank& B, Quench Q, int V)
{
	TemperRun R = IdealRun(B, Q);
	if (V >= 1 && V <= 5)
	{
		const int D = Shifts[V - 1];
		for (int& T : R.StrikesMs) T += D;
		R.QuenchMs += D;
	}
	else if (V == 6) R.PullMs -= 2000;
	else if (V == 7) R.QuenchMs += 900;
	else if (V == 8) { R.StrikesMs.push_back(R.StrikesMs.back() + 10); R.QuenchMs += 20; }
	else if (V == 9)
	{
		const int Cold = R.PullMs + (B.Mt.TargetC - B.WorkableC() + 40) * 1000 / TemperCoolCPerS;
		R.StrikesMs.back() = Cold;
		R.QuenchMs = Cold + 10;
	}
	return R;
}

static std::string Line(Material M, int Seed, Quench Q, int V)
{
	TemperBlank B; MakeBlank(M, Seed, B);
	TemperResult Res;
	char Head[96];
	std::snprintf(Head, sizeof(Head), "%s seed=%d v=%d n=%d beat=%d | ", MaterialName(M), Seed, V, B.Strikes, B.BeatMs);
	return std::string(Head) + (Judge(B, Variant(B, Q, V), Res) ? Encode(Res) : std::string("REFUSED"));
}

int main(int argc, char** argv)
{
	const bool WriteOut = argc > 1 && std::strcmp(argv[1], "--write") == 0;
	TemperBlank Wood;
	Check("wood is not tempered", !MakeBlank(Material::Wood, 1, Wood) && !Forgeable(Material::Obsidian) && Forgeable(Material::Iron));

	bool Top = true, Ranged = true;
	for (Material M : Metals)
		for (int Seed = 0; Seed < 100; ++Seed)
		{
			TemperBlank B; MakeBlank(M, Seed, B);
			if (B.Strikes < 5 || B.Strikes > 8 || B.BeatMs < 520 || B.BeatMs > 780 || (B.BeatMs - 520) % 20 != 0) Ranged = false;
			for (int q = 0; q < 3; ++q)
			{
				TemperResult Res; Judge(B, IdealRun(B, static_cast<Quench>(q)), Res);
				if (Res.Temper < 98 || Res.Cracked || Res.ArkPlate != (q == 2)) Top = false;
			}
		}
	Check("blanks in range (5 metals x 100 seeds)", Ranged);
	Check("ideal run tempers >= 98, dual stamps the ark plate", Top);

	bool Mono = true;
	for (Material M : Metals)
	{
		TemperBlank B; MakeBlank(M, 7, B);
		int Prev = 101;
		for (int V = 0; V <= 5; ++V) { TemperResult Res; Judge(B, Variant(B, Quench::Spring, V), Res); if (Res.Temper > Prev) Mono = false; Prev = Res.Temper; }
	}
	Check("mistiming never raises temper", Mono);

	{
		TemperBlank B; MakeBlank(Material::Steel, 4, B);
		TemperResult Res; Judge(B, Variant(B, Quench::Dual, 9), Res);
		Check("cold strike cracks and caps", Res.Cracked && Res.Temper <= TemperCrackedCap && !Res.ArkPlate && Res.Strikes.back() == TemperStrike::Crack);
	}
	{
		TemperBlank B; MakeBlank(Material::Iron, 2, B);
		TemperRun Bad = IdealRun(B, Quench::Magma); Bad.QuenchMs = Bad.PullMs - 1;
		TemperRun Order = IdealRun(B, Quench::Magma); Order.StrikesMs[1] = Order.StrikesMs[0] - 1;
		TemperResult Res;
		Check("malformed runs refused", !Judge(B, Bad, Res) && !Judge(B, Order, Res));
	}
	Check("deterministic", Line(Material::Copper, 13, Quench::Spring, 2) == Line(Material::Copper, 13, Quench::Spring, 2));

	if (WriteOut)
	{
		std::FILE* F = std::fopen("temper_forge_parity.txt", "wb");
		if (!F) { std::printf("FAIL cannot write parity\n"); return 1; }
		std::fputs("# temper_forge_core_test.cpp --write: TFG 1 parity (hephaestus). Metal x seed 0..19 x quench x variant 0..9.\n", F);
		for (Material M : Metals)
			for (int Seed = 0; Seed < 20; ++Seed)
				for (int q = 0; q < 3; ++q)
					for (int V = 0; V < Variants; ++V)
						std::fprintf(F, "%s\n", Line(M, Seed, static_cast<Quench>(q), V).c_str());
		std::fclose(F);
		std::printf("wrote temper_forge_parity.txt\n");
	}
	std::printf("%d/%d passed\n", Passed, Total);
	return Passed == Total ? 0 : 1;
}
