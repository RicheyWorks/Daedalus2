// SPDX-License-Identifier: MIT
// PyRandom parity: DaedalusPyRandomCore.h must reproduce CPython's random.Random(str) bit for bit, method by method,
// from pyrandom_parity.txt (tools/minigames/pyrandom_parity.py). Each seed block is one continuous stream, so a
// mismatch names the first call that drifted. The trailing "drawn" line checks Drawn()/Discard() fast-forward.
//   g++ -std=c++17 -O1 -Wall -Wextra -Wshadow -Werror -I../DaedalusLink/Source/DaedalusLink/Public pyrandom_core_test.cpp -o pyrandom_core_test && ./pyrandom_core_test pyrandom_parity.txt
#include "DaedalusPyRandomCore.h"
#include <cstdio>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>

using daedalus::pyrandom::PyRandom;

namespace {

/** The value after "key=" in a line, or "" when absent. */
std::string Field(const std::string& Line, const std::string& Key)
{
	const std::string Needle = " " + Key + "=";
	const size_t P = Line.find(Needle);
	if (P == std::string::npos) return "";
	const size_t S = P + Needle.size(), E = Line.find(' ', S);
	return Line.substr(S, E == std::string::npos ? std::string::npos : E - S);
}


/** "0aff" -> {0x0a, 0xff}; the fixture only writes even-length lowercase hex. */
std::vector<std::uint8_t> HexBytes(const std::string& Hex)
{
	std::vector<std::uint8_t> Out;
	for (std::size_t I = 0; I + 1 < Hex.size(); I += 2) Out.push_back(static_cast<std::uint8_t>(std::stoul(Hex.substr(I, 2), nullptr, 16)));
	return Out;
}

/** Seeds `Rng` the way the fixture block header says. */
void Reseed(PyRandom& Rng, const std::string& Kind, const std::string& Text)
{
	if (Kind == "seedint") Rng.SeedInt(std::stoll(Text));
	else if (Kind == "seedhex") { const std::vector<std::uint8_t> Bytes = HexBytes(Text); Rng.SeedBigEndian(Bytes.data(), Bytes.size()); }
	else Rng.Seed(Text);
}

/** The last space-separated token of a line (the recorded result). */
std::string Last(const std::string& Line)
{
	const size_t P = Line.rfind(' ');
	return P == std::string::npos ? Line : Line.substr(P + 1);
}

std::string Join(const std::vector<std::size_t>& V)
{
	std::string S;
	for (std::size_t I = 0; I < V.size(); ++I) { if (I) S.push_back(','); S += std::to_string(V[I]); }
	return S;
}

/** repr(float) round-trips through 17 significant digits; compare by re-parsing rather than by text. */
bool SameDouble(const std::string& Text, double Value)
{
	std::istringstream In(Text);
	double Parsed = 0;
	return (In >> Parsed) && Parsed == Value;
}

int UnitChecks()
{
	int Fails = 0;
	PyRandom A, B;
	A.Seed("twin"); B.Seed("twin");
	if (A.U32() != B.U32()) { std::printf("FAIL same seed, same stream\n"); ++Fails; }
	A.Seed("one"); B.Seed("two");
	if (A.U32() == B.U32()) { std::printf("FAIL different seeds should diverge\n"); ++Fails; }
	PyRandom C; C.Seed("count");
	if (C.Drawn() != 0) { std::printf("FAIL fresh generator has drawn nothing\n"); ++Fails; }
	C.U32(); C.RandomDouble();
	if (C.Drawn() != 3) { std::printf("FAIL U32 draws one word and RandomDouble two (got %llu)\n", static_cast<unsigned long long>(C.Drawn())); ++Fails; }
	if (C.Below(0) != 0 || C.Drawn() != 3) { std::printf("FAIL Below(0) is 0 and draws nothing\n"); ++Fails; }
	if (!C.SampleIndices(3, 5).empty()) { std::printf("FAIL sample k > n is empty\n"); ++Fails; }
	PyRandom Pos, Neg, Hex, Str;
	Pos.SeedInt(12345); Neg.SeedInt(-12345);
	if (Pos.U32() != Neg.U32()) { std::printf("FAIL negative integer seeds hash as abs(n)\n"); ++Fails; }
	const std::uint8_t Seven[] = { 0, 0, 0, 0, 0, 0, 0, 7 };
	Hex.SeedBigEndian(Seven, sizeof Seven); Pos.SeedInt(7);
	if (Hex.U32() != Pos.U32()) { std::printf("FAIL big-endian bytes and the integer agree\n"); ++Fails; }
	Hex.SeedBigEndian(nullptr, 0); Pos.SeedInt(0);
	if (Hex.U32() != Pos.U32()) { std::printf("FAIL an empty byte string is the integer 0\n"); ++Fails; }
	Str.Seed("7"); Pos.SeedInt(7);
	if (Str.U32() == Pos.U32()) { std::printf("FAIL the str path must differ from the int path (CPython appends sha512 for str)\n"); ++Fails; }
	std::vector<int> One{ 7 }; C.Shuffle(One);
	if (One.size() != 1 || One[0] != 7) { std::printf("FAIL shuffle of one element is a no-op\n"); ++Fails; }
	return Fails;
}

} // namespace

int main(int Argc, char** Argv)
{
	if (Argc < 2) { std::printf("usage: pyrandom_core_test pyrandom_parity.txt\n"); return 2; }
	std::ifstream In(Argv[1]);
	if (!In) { std::printf("FAIL cannot open %s\n", Argv[1]); return 2; }
	int Fails = UnitChecks(), Seeds = 0, Calls = 0;
	std::string Line, SeedText, Kind2;
	PyRandom Rng;
	bool Skip = false;
	while (std::getline(In, Line))
	{
		if (Line.empty() || Line[0] == '#') continue;
		const std::string Kind = Line.substr(0, Line.find(' '));
		std::string Got;
		if (Kind == "seed" || Kind == "seedint" || Kind == "seedhex")
		{
			SeedText = Line.size() > Kind.size() + 1 ? Line.substr(Kind.size() + 1) : "";
			Kind2 = Kind;
			Reseed(Rng, Kind, SeedText);
			Skip = false; ++Seeds;
			continue;
		}
		if (Skip) continue;
		++Calls;
		if (Kind == "u32") Got = std::to_string(Rng.U32());
		else if (Kind == "below") Got = std::to_string(Rng.Below(static_cast<std::uint32_t>(std::stoul(Field(Line, "n")))));
		else if (Kind == "randrange") Got = std::to_string(Rng.RandRange(static_cast<std::uint32_t>(std::stoul(Field(Line, "n")))));
		else if (Kind == "double")
		{
			const double V = Rng.RandomDouble();
			if (SameDouble(Last(Line), V)) continue;
			std::printf("FAIL seed '%s': %s\n  got  %.17g\n", SeedText.c_str(), Line.c_str(), V); ++Fails; Skip = true; continue;
		}
		else if (Kind == "sample") Got = Join(Rng.SampleIndices(std::stoul(Field(Line, "n")), std::stoul(Field(Line, "k"))));
		else if (Kind == "shuffle")
		{
			std::vector<std::size_t> Order(std::stoul(Field(Line, "n")));
			for (std::size_t I = 0; I < Order.size(); ++I) Order[I] = I;
			Rng.Shuffle(Order);
			Got = Join(Order);
		}
		else if (Kind == "drawn")
		{
			Got = std::to_string(Rng.Drawn());
			// Prove the save fast-forward: a fresh generator discarded this far must continue identically.
			PyRandom Fresh; Reseed(Fresh, Kind2, SeedText); Fresh.Discard(Rng.Drawn());
			std::string Next;
			if (std::getline(In, Next) && Next.rfind("u32 ", 0) == 0)
			{
				++Calls;
				const std::uint32_t A = Rng.U32(), B = Fresh.U32();
				if (A != B || std::to_string(A) != Last(Next))
				{
					std::printf("FAIL seed '%s': fast-forward diverges (%u vs %u, want %s)\n", SeedText.c_str(), A, B, Last(Next).c_str()); ++Fails; Skip = true;
				}
			}
		}
		else { std::printf("FAIL unknown line: %s\n", Line.c_str()); return 1; }
		if (!Got.empty() && Got != Last(Line))
		{
			std::printf("FAIL seed '%s': %s\n  got  %s\n", SeedText.c_str(), Line.c_str(), Got.c_str()); ++Fails; Skip = true;
		}
	}
	std::printf("%s pyrandom: %d seeds, %d calls matched CPython, %d failures\n", Fails ? "FAIL" : "OK", Seeds, Calls, Fails);
	return Fails ? 1 : 0;
}
