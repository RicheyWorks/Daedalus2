// SPDX-License-Identifier: MIT
// BBA 1 (asset LOD manifest) and the LOD picker, checked without Unreal. Build:
//   g++ -std=c++17 -O1 -Wall -Wextra -Werror -fsanitize=address,undefined -I../DaedalusLink/Source/DaedalusLink/Public asset_lod_core_test.cpp
// Run with --write to regenerate asset_lod_parity.txt (read by AssetLodParityTest.java).
#include "DaedalusAssetLodCore.h"
#include <cstdio>
#include <cstring>
using namespace daedalus::assetlod;
static int Passed = 0, Total = 0;
static void Check(const char* Name, bool OK) { ++Total; Passed += OK; std::printf("%s %s\n", OK ? "PASS" : "FAIL", Name); }
static uint64_t Seed = 0x9E3779B97F4A7C15ull;
static int64_t Rnd(int64_t N) { Seed = Seed * 6364136223846793005ull + 1442695040888963407ull; return (int64_t)((Seed >> 33) % (uint64_t)N); }
static std::string Esc(const std::string& S)
{
	std::string O;
	for (char C : S) { if (C == '\n') O += "\\n"; else if (C == '\r') O += "\\r"; else if (C == '\t') O += "\\t"; else O += C; }
	return O;
}

int main(int argc, char** argv)
{
	const bool WriteOut = argc > 1 && std::strcmp(argv[1], "--write") == 0;
	const std::string Good = "# from bba_manifest.py\nBBA 1\r\nasset Prop_Rock_A lod0 1200 lod1 700 radius 90 switch 1800\n\n"
		"asset Tree_Oak  lod0 5400 lod1 - radius 420 switch 8400\n";
	ParseResult R = Parse(Good);
	Check("a good manifest parses", R.Ok && R.Out.Assets.size() == 2);
	Check("a missing LOD1 reads as -1", R.Ok && R.Out.Assets[1].Lod1 == -1 && R.Out.Assets[1].Radius == 420);
	Check("write is canonical", R.Ok && Write(R.Out) == "BBA 1\nasset Prop_Rock_A lod0 1200 lod1 700 radius 90 switch 1800\nasset Tree_Oak lod0 5400 lod1 - radius 420 switch 8400\n");
	ParseResult Again = Parse(Write(R.Out));
	Check("write then parse gives the same manifest", Again.Ok && Write(Again.Out) == Write(R.Out));
	Check("near draws LOD0", R.Ok && Select(R.Out.Assets[0], 1799) == 0);
	Check("at the switch distance draws LOD1", R.Ok && Select(R.Out.Assets[0], 1800) == 1);
	Check("no LOD1 never switches", R.Ok && Select(R.Out.Assets[1], 99999999) == 0);
	Check("switch rule: 20 radii, at least 5 m", SwitchFor(10) == 500 && SwitchFor(90) == 1800);
	{
		std::vector<Instance> In = {{0, 100}, {0, 900}, {1, 50}, {0, 900}};
		BudgetResult B = Budget(R.Out, In, 100000);
		Check("a big budget keeps the distance rule", B.Faces == 1200 * 3 + 5400 && B.Lods == std::vector<int>({0, 0, 0, 0}));
		B = Budget(R.Out, In, 8500);
		Check("over budget drops the farthest first, ties by index", B.Faces == 8500 && B.Lods == std::vector<int>({0, 1, 0, 0}));
		B = Budget(R.Out, In, 0);
		Check("an impossible budget drops all it can", B.Faces == 700 * 3 + 5400 && B.Lods == std::vector<int>({1, 1, 0, 1}));
	}
	struct Bad { const char* Text; const char* Why; };
	const Bad Bads[] = {
		{"", "line 1: empty"}, {"BBA 2\n", "line 1: unsupported version 2"}, {"BBX 1\n", "line 1: expected 'BBA 1'"},
		{"# c\nasset a lod0 1 lod1 - radius 1 switch 0\n", "line 2: expected 'BBA 1'"},
		{"BBA 1\nthing a\n", "line 2: unknown record thing"},
		{"BBA 1\nasset a lod0 1 lod1 - radius 1\n", "line 2: expected 'asset <id> lod0 <n> lod1 <n|-> radius <cm> switch <cm>'"},
		{"BBA 1\nasset a lod1 1 lod0 - radius 1 switch 0\n", "line 2: expected 'asset <id> lod0 <n> lod1 <n|-> radius <cm> switch <cm>'"},
		{"BBA 1\nasset b@d lod0 1 lod1 - radius 1 switch 0\n", "line 2: bad asset id"},
		{"BBA 1\nasset a lod0 0 lod1 - radius 1 switch 0\n", "line 2: bad lod0"},
		{"BBA 1\nasset a lod0 -5 lod1 - radius 1 switch 0\n", "line 2: bad lod0"},
		{"BBA 1\nasset a lod0 1.5 lod1 - radius 1 switch 0\n", "line 2: bad lod0"},
		{"BBA 1\nasset a lod0 010 lod1 - radius 1 switch 0\n", "line 2: bad lod0"},
		{"BBA 1\nasset a lod0 10000001 lod1 - radius 1 switch 0\n", "line 2: bad lod0"},
		{"BBA 1\nasset a lod0 10 lod1 0 radius 1 switch 0\n", "line 2: bad lod1"},
		{"BBA 1\nasset a lod0 10 lod1 11 radius 1 switch 0\n", "line 2: lod1 has more faces than lod0"},
		{"BBA 1\nasset a lod0 10 lod1 - radius 0 switch 0\n", "line 2: bad radius"},
		{"BBA 1\nasset a lod0 10 lod1 - radius 1 switch 100000001\n", "line 2: bad switch"},
		{"BBA 1\nasset a lod0 10 lod1 - radius 1 switch nan\n", "line 2: bad switch"},
		{"BBA 1\nasset a\tlod0 10 lod1 - radius 1 switch 0\n", "line 2: tab"},
		{"BBA 1\nasset a lod0 1 lod1 - radius 1 switch 0\nasset a lod0 2 lod1 - radius 1 switch 0\n", "duplicate asset a"},
	};
	int BadOk = 0;
	for (const Bad& B : Bads) { ParseResult P = Parse(B.Text); BadOk += !P.Ok && P.Error == B.Why && P.Out.Assets.empty(); if (P.Error != B.Why) std::printf("  got [%s] want [%s]\n", P.Error.c_str(), B.Why); }
	Check("20 bad manifests refused with the exact message", BadOk == 20);
	{
		std::string Long = "BBA 1\nasset a lod0 1 lod1 - radius 1 switch 0 " + std::string(600, 'x') + "\n";
		ParseResult P = Parse(Long); Check("an over-long line is refused", !P.Ok && P.Error == "line 2: line too long");
	}

	// --- parity cases: random manifests (shuffled order, comments, CRLF), selections and budgets
	std::string Par = "# asset_lod_core_test.cpp --write: BBA 1 parity (blender-team). Per case: raw manifest, canonical Write,\n"
		"# then 'sel <asset index> <distance> <lod>' and 'budget <budget> <asset:distance ...> = <faces> <lods>'\n";
	int SelN = 0, BudN = 0;
	for (int K = 0; K < 40; ++K)
	{
		std::string Raw = (K % 3 == 0 ? "# case\n" : "") + std::string("BBA 1") + (K % 4 == 1 ? "\r\n" : "\n");
		const int N = 1 + (int)Rnd(12);
		for (int I = 0; I < N; ++I)
		{
			const int64_t L0 = 1 + Rnd(200000), Rad = 1 + Rnd(5000);
			const bool Has = Rnd(5) != 0;
			const int64_t L1 = Has ? 1 + Rnd(L0) : -1;
			const int64_t Sw = Rnd(3) == 0 ? Rnd(200000) : SwitchFor(Rad);
			Raw += "asset A" + std::to_string(Rnd(1000)) + "_" + std::to_string(K) + "_" + std::to_string(I) + " lod0 " + std::to_string(L0) + " lod1 "
				+ (Has ? std::to_string(L1) : std::string("-")) + (I % 2 ? "  radius " : " radius ") + std::to_string(Rad) + " switch " + std::to_string(Sw) + "\n";
		}
		ParseResult P = Parse(Raw);
		if (!P.Ok) { Check("parity manifest parses", false); continue; }
		Par += "case " + std::to_string(K) + "\nraw\t" + Esc(Raw) + "\ncanon\t" + Esc(Write(P.Out)) + "\n";
		for (int Q = 0; Q < 6; ++Q)
		{
			const size_t A = (size_t)Rnd(N); const int64_t D = Rnd(3) == 0 ? P.Out.Assets[A].Switch : Rnd(250000);
			Par += "sel " + std::to_string(A) + " " + std::to_string(D) + " " + std::to_string(Select(P.Out.Assets[A], D)) + "\n"; ++SelN;
		}
		for (int Q = 0; Q < 3; ++Q)
		{
			std::vector<Instance> In; int64_t All = 0;
			const int M = 1 + (int)Rnd(20);
			for (int I = 0; I < M; ++I) { Instance X; X.Asset = (size_t)Rnd(N); X.Distance = Rnd(4) == 0 ? 5000 : Rnd(250000); In.push_back(X); All += P.Out.Assets[X.Asset].Lod0; }
			const int64_t Bud = Rnd(All + 1);
			BudgetResult B = Budget(P.Out, In, Bud);
			Par += "budget " + std::to_string(Bud);
			for (const Instance& X : In) Par += " " + std::to_string(X.Asset) + ":" + std::to_string(X.Distance);
			Par += " = " + std::to_string(B.Faces) + " ";
			for (int L : B.Lods) Par += char('0' + L);
			Par += "\n"; ++BudN;
		}
		Par += "end\n";
	}
	for (const Bad& B : Bads) Par += std::string("bad\t") + Esc(B.Text) + "\t" + B.Why + "\n";
	Check("240 selections and 120 budgets written", SelN == 240 && BudN == 120);
	if (WriteOut) { FILE* F = std::fopen("asset_lod_parity.txt", "wb"); std::fwrite(Par.data(), 1, Par.size(), F); std::fclose(F); std::printf("wrote asset_lod_parity.txt\n"); }
	std::printf("%d/%d passed\n", Passed, Total);
	return Passed == Total ? 0 : 1;
}
