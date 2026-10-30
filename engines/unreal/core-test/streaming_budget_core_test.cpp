// SPDX-License-Identifier: MIT
// DSB 1 (island streaming budget manifest) and the resident-set picker, checked without Unreal. Build:
//   g++ -std=c++17 -O1 -Wall -Wextra -Werror -fsanitize=address,undefined -I../DaedalusLink/Source/DaedalusLink/Public streaming_budget_core_test.cpp
// Run with --write to regenerate streaming_budget_parity.txt (read by StreamingBudgetParityTest.java).
#include "DaedalusStreamingBudgetCore.h"
#include <cstdio>
#include <cstring>
using namespace daedalus::streamingbudget;
static int Passed = 0, Total = 0;
static void Check(const char* Name, bool OK) { ++Total; Passed += OK; std::printf("%s %s\n", OK ? "PASS" : "FAIL", Name); }
static uint64_t Seed = 0xD15C5A7E12345678ull;
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
	const std::string Good = "# from the island census\nDSB 1\r\nisland Iz_B x 1000 y 0 ram 300 disk 900\n\n"
		"island Ia_A  x 0 y 0 ram 500 disk 2000\nisland Ic_C x -4000 y 3000 ram 400 disk 100\n";
	ParseResult R = Parse(Good);
	Check("a good manifest parses", R.Ok && R.Out.Islands.size() == 3);
	Check("negative coordinates read", R.Ok && R.Out.Islands[2].X == -4000 && R.Out.Islands[2].Y == 3000);
	Check("write is canonical (sorted by id)", R.Ok && Write(R.Out) == "DSB 1\nisland Ia_A x 0 y 0 ram 500 disk 2000\nisland Ic_C x -4000 y 3000 ram 400 disk 100\nisland Iz_B x 1000 y 0 ram 300 disk 900\n");
	ParseResult Again = Parse(Write(R.Out));
	Check("write then parse gives the same manifest", Again.Ok && Write(Again.Out) == Write(R.Out));
	Check("a header-only manifest is empty, not an error", Parse("DSB 1\n").Ok && Parse("DSB 1\n").Out.Islands.empty());
	Check("maximum comment line accepts CRLF", Parse("DSB 1\r\n#" + std::string(MaxLine - 1, 'x') + "\r\n").Ok);
	ParseResult Huge = Parse("DSB 1\nisland a x 0 y 0 ram 1 disk 1\n" + std::string(1024 * 1024, 'x'));
	Check("huge final line refuses without partial output", !Huge.Ok && Huge.Out.Islands.empty()
		&& Huge.Error == "line 3: line too long");
	Check("empty lines preserve diagnostic line numbers", Parse("\n\nDSB 1\n\ninvalid").Error == "line 5: unknown record invalid");
	Check("no trailing newline remains valid", Parse("DSB 1\nisland a x 0 y 0 ram 1 disk 1").Ok);
	const Manifest& M = R.Out;   // file order: Iz_B (d 1000), Ia_A (d 0), Ic_C (d 5000)
	{
		PickResult P = Pick(M, 0, 0, 2000, 6000, 10000, {});
		Check("within load radius loads nearest first", Bits(P.Resident) == "110" && P.Ram == 800 && P.Disk == 2900 && P.Count == 2);
		P = Pick(M, 0, 0, 2000, 6000, 10000, {false, false, true});
		Check("hysteresis keeps a resident island inside the unload radius", Bits(P.Resident) == "111" && P.Ram == 1200);
		P = Pick(M, 0, 0, 2000, 4999, 10000, {false, false, true});
		Check("outside the unload radius it is dropped", Bits(P.Resident) == "110");
		P = Pick(M, 0, 0, 2000, 5000, 10000, {false, false, true});
		Check("exactly on the unload radius it stays", Bits(P.Resident) == "111");
		P = Pick(M, 0, 0, 6000, 6000, 700, {});
		Check("over budget skips what does not fit, keeps going", Bits(P.Resident) == "010" && P.Ram == 500);
		P = Pick(M, 0, 0, 6000, 6000, 450, {});
		Check("a smaller farther island can still fit", Bits(P.Resident) == "100" && P.Ram == 300);
		P = Pick(M, 0, 0, 6000, 6000, 0, {true, true, true});
		Check("a zero budget loads nothing", Bits(P.Resident) == "000" && P.Count == 0);
		P = Pick(M, 0, 0, 3000, 1000, 10000, {false, false, true});
		Check("unload below load acts as load", Bits(P.Resident) == "110");
		P = Pick(M, 500, 0, 500, 500, 10000, {});
		Check("distance ties go to the lower index", Bits(P.Resident) == "110");
		Manifest Far; Far.Islands = {{"F1", MaxCm, MaxCm, 1, 1}, {"F2", -MaxCm, -MaxCm, 1, 1}};
		P = Pick(Far, -MaxCm, -MaxCm, MaxCm, MaxCm, 10, {});
		Check("extreme coordinates do not overflow", Bits(P.Resident) == "01");
	}
	struct Bad { const char* Text; const char* Why; };
	const Bad Bads[] = {
		{"", "line 1: empty"}, {"# only a comment\n", "line 1: empty"}, {"DSB 2\n", "line 1: unsupported version 2"}, {"DSX 1\n", "line 1: expected 'DSB 1'"},
		{"# c\nisland a x 0 y 0 ram 1 disk 1\n", "line 2: expected 'DSB 1'"},
		{"DSB 1\nthing a\n", "line 2: unknown record thing"},
		{"DSB 1\nisland a x 0 y 0 ram 1\n", "line 2: expected 'island <id> x <cm> y <cm> ram <kib> disk <kib>'"},
		{"DSB 1\nisland a y 0 x 0 ram 1 disk 1\n", "line 2: expected 'island <id> x <cm> y <cm> ram <kib> disk <kib>'"},
		{"DSB 1\nisland b@d x 0 y 0 ram 1 disk 1\n", "line 2: bad island id"},
		{"DSB 1\nisland a x 0 y 0 ram 1 disk 1\nisland a x 1 y 1 ram 1 disk 1\n", "line 3: duplicate island a"},
		{"DSB 1\nisland a x 1.5 y 0 ram 1 disk 1\n", "line 2: bad x"},
		{"DSB 1\nisland a x -0 y 0 ram 1 disk 1\n", "line 2: bad x"},
		{"DSB 1\nisland a x 1000000001 y 0 ram 1 disk 1\n", "line 2: bad x"},
		{"DSB 1\nisland a x 0 y 007 ram 1 disk 1\n", "line 2: bad y"},
		{"DSB 1\nisland a x 0 y 0 ram 0 disk 1\n", "line 2: bad ram"},
		{"DSB 1\nisland a x 0 y 0 ram -3 disk 1\n", "line 2: bad ram"},
		{"DSB 1\nisland a x 0 y 0 ram 1 disk 100000001\n", "line 2: bad disk"},
	};
	for (const Bad& B : Bads)
	{
		ParseResult P = Parse(B.Text);
		const bool OK = !P.Ok && P.Error == B.Why && P.Out.Islands.empty();
		if (!OK) std::printf("  got '%s' want '%s'\n", P.Error.c_str(), B.Why);
		Check(B.Why, OK);
	}
	Check("an over-long line is refused", Parse("DSB 1\n# " + std::string(600, 'x') + "\n").Error == "line 2: line too long");

	// Parity cases: random manifests (raw form with odd spacing/comments/CRLF), canonical Write, then picks.
	std::string Out = "# streaming_budget_core_test.cpp --write: DSB 1 parity (disk-saver). Per case: raw manifest, canonical Write,\n"
		"# then 'pick <vx> <vy> <load> <unload> <budget> <was bits> = <ram> <disk> <count> <resident bits>'\n";
	int Picks = 0;
	for (int C = 0; C < 40; ++C)
	{
		const int N = 1 + (int)Rnd(24);
		std::string Raw = (C % 3 == 0) ? "# case\n" : ""; Raw += (C % 4 == 0) ? "DSB 1\r\n" : "DSB 1\n";
		for (int I = 0; I < N; ++I)
		{
			Raw += "island I" + std::to_string(Rnd(1000)) + "_" + std::to_string(C) + "_" + std::to_string(I);
			Raw += (I % 5 == 3 ? "  x " : " x ") + std::to_string(Rnd(2000001) - 1000000) + " y " + std::to_string(Rnd(2000001) - 1000000);
			Raw += " ram " + std::to_string(1 + Rnd(4000000)) + " disk " + std::to_string(1 + Rnd(20000000)) + (I % 7 == 6 ? "\n\n" : "\n");
		}
		ParseResult P = Parse(Raw);
		if (!P.Ok) { Check("random manifest parses", false); continue; }
		Out += "case " + std::to_string(C) + "\nraw\t" + Esc(Raw) + "\ncanon\t" + Esc(Write(P.Out)) + "\n";
		std::vector<bool> Was(P.Out.Islands.size(), false);
		for (int K = 0; K < 6; ++K)
		{
			const int64_t Vx = Rnd(2000001) - 1000000, Vy = Rnd(2000001) - 1000000, Ld = Rnd(1500000), Ul = Rnd(2000000), Bg = Rnd(30000000);
			PickResult Pk = Pick(P.Out, Vx, Vy, Ld, Ul, Bg, Was);
			Out += "pick " + std::to_string(Vx) + " " + std::to_string(Vy) + " " + std::to_string(Ld) + " " + std::to_string(Ul) + " " + std::to_string(Bg) + " " + Bits(Was)
				+ " = " + std::to_string(Pk.Ram) + " " + std::to_string(Pk.Disk) + " " + std::to_string(Pk.Count) + " " + Bits(Pk.Resident) + "\n";
			Was = Pk.Resident; ++Picks;   // the next pick walks on from this one, as a moving player would
		}
	}
	for (const Bad& B : Bads) Out += "bad\t" + Esc(B.Text) + "\t" + B.Why + "\n";
	Check("240 parity picks generated", Picks == 240);
	if (WriteOut)
	{
		FILE* F = std::fopen("streaming_budget_parity.txt", "wb");
		if (!F) { std::printf("cannot write parity\n"); return 1; }
		std::fwrite(Out.data(), 1, Out.size(), F); std::fclose(F);
		std::printf("wrote streaming_budget_parity.txt\n");
	}
	std::printf("%d/%d passed\n", Passed, Total);
	return Passed == Total ? 0 : 1;
}
