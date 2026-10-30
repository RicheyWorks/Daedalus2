// SPDX-License-Identifier: MIT
// C++ = Java for the ear rule (DaedalusEarRuleCore.h): reads ear_rule_parity.txt, written by the Java
// EarRuleParityTest from the real CallSynth (300 seeds x 7 species), and recomputes every line.
// Raw PCS 1 lines, ear-safe base pitches and octave drops must match exactly; peak Hz within 1e-9 relative.
// Build: g++ -std=c++17 -Wall -Wextra -Werror -ffp-contract=off ear_rule_core_test.cpp
// Run from the repo root, or pass the parity file path as the first argument.
#include "../DaedalusLink/Source/DaedalusLink/Public/DaedalusEarRuleCore.h"

#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <sstream>
#include <string>

using namespace daedalus::earrule;

static int Failures = 0, Checks = 0, Exact = 0;
static void Check(bool Ok_, const std::string& What)
{
	++Checks;
	if (!Ok_ && ++Failures <= 25) std::printf("FAIL %s\n", What.c_str());
}

static std::string Fmt(const char* F, double V)
{
	char B[64];
	std::snprintf(B, sizeof B, F, V);
	return B;
}

static void Units()
{
	Check(Ok(799.9) && !Ok(800) && !Ok(0) && !Ok(-1), "Ok boundaries");
	Check(JavaRound(-2.5) == -2.0 && JavaRound(2.5) == 3.0 && JavaRound(0.49999999999999994) == 0.0, "JavaRound half up");
	Check(Round3(-0.0005) == 0.0 && Round3(0.0005) == 0.001, "Round3 ties toward +inf like Java");
	CallSpec At800; At800.BaseHz = 800; At800.PulseMs = 100;
	Check(EarSafe(At800).BaseHz == 400.0, "800 Hz folds to 400");
	CallSpec Risky; Risky.BaseHz = 700; Risky.Sweep = 0.4; Risky.VibratoDepth = 0.8; Risky.PulseMs = 300;
	Check(EarSafe(Risky).BaseHz == 700.0 && EarSafePeak(Risky).BaseHz == 350.0, "peak check drops a base-safe call");
	Genome G;
	Check(Genome::FromHex(" 0xAB ", G) && G.Length == 1 && G.Gene(5) == 171 / 255.0, "FromHex prefix, case, wrap");
	Check(!Genome::FromHex("abc", G) && !Genome::FromHex("zz", G) && !Genome::FromHex("", G) && !Genome::FromHex("0x", G),
		"FromHex rejects bad input");
	Genome Top;
	Genome::FromHex("ff808080808080808080", Top);
	char L[256];
	Design(Species::Songbird, Top).ToLine(L, sizeof L);
	Check(std::strncmp(L, "PCS 1 hz=5200.000 ", 18) == 0, "design keeps the PCS 1 line (songbird top 5200 Hz)");
	Check(DesignEarSafe(Species::Songbird, Top).BaseHz == 650.0, "earSafe songbird top -> 650");
}

int main(int argc, char** argv)
{
	Units();
	const char* Path = argc > 1 ? argv[1] : "engines/unreal/core-test/ear_rule_parity.txt";
	std::ifstream In(Path);
	if (!In) { std::printf("FAIL cannot open %s\n", Path); return 1; }
	std::string Line;
	int Cases = 0, PeakStrDiff = 0, MaxDrop = 0;
	double WorstRel = 0;
	while (std::getline(In, Line))
	{
		if (Line.empty() || Line[0] == '#') continue;
		// SPECIES seed hex | PCS line | raw_peak | safe_hz safe_drop | peak_base peak_drop peak_hz
		std::string Parts[5];
		std::size_t Start = 0;
		for (int I = 0; I < 5; ++I)
		{
			const std::size_t Bar = Line.find(" | ", Start);
			Parts[I] = Line.substr(Start, Bar == std::string::npos ? std::string::npos : Bar - Start);
			Start = Bar == std::string::npos ? Line.size() : Bar + 3;
		}
		std::istringstream Head(Parts[0]);
		std::string Name, Hex;
		long Seed = 0;
		Head >> Name >> Seed >> Hex;
		Species S;
		Genome G;
		const std::string At = Name + " seed " + std::to_string(Seed);
		if (!SpeciesFromName(Name.c_str(), S) || !Genome::FromHex(Hex.c_str(), G)) { Check(false, At + " unparsable"); continue; }
		++Cases;
		const CallSpec Raw = Design(S, G);
		const CallSpec Safe = EarSafe(Raw);
		const CallSpec Peak = EarSafePeak(Raw);
		char Buf[256];
		Raw.ToLine(Buf, sizeof Buf);
		const bool LineSame = Parts[1] == Buf;
		Check(LineSame, At + " raw PCS: java [" + Parts[1] + "] c++ [" + Buf + "]");
		std::istringstream SafeIn(Parts[3]), PeakIn(Parts[4]);
		std::string SafeHz, PeakBase, PeakHzStr;
		int SafeDrop = -1, PeakDrop = -1;
		SafeIn >> SafeHz >> SafeDrop;
		PeakIn >> PeakBase >> PeakDrop >> PeakHzStr;
		Check(Fmt("%.3f", Safe.BaseHz) == SafeHz, At + " earSafe base " + SafeHz + " vs " + Fmt("%.3f", Safe.BaseHz));
		Check(OctaveDrops(Raw, Safe) == SafeDrop, At + " earSafe drops");
		Check(Fmt("%.3f", Peak.BaseHz) == PeakBase, At + " earSafePeak base " + PeakBase + " vs " + Fmt("%.3f", Peak.BaseHz));
		Check(OctaveDrops(Raw, Peak) == PeakDrop, At + " earSafePeak drops");
		const double JavaRawPeak = std::strtod(Parts[2].c_str(), nullptr), JavaPeak = std::strtod(PeakHzStr.c_str(), nullptr);
		const double R1 = std::fabs(PeakHz(Raw) - JavaRawPeak) / JavaRawPeak, R2 = std::fabs(PeakHz(Peak) - JavaPeak) / JavaPeak;
		// The file keeps 6 decimals, so allow half a unit in the 6th decimal on top of 1e-9 relative.
		Check(std::fabs(PeakHz(Raw) - JavaRawPeak) <= 5e-7 + 1e-9 * JavaRawPeak, At + " raw peak Hz");
		Check(std::fabs(PeakHz(Peak) - JavaPeak) <= 5e-7 + 1e-9 * JavaPeak, At + " ear-safe peak Hz");
		Check(Ok(Safe.BaseHz) && Ok(Peak.BaseHz) && Ok(PeakHz(Peak)), At + " ear rule holds");
		if (Fmt("%.6f", PeakHz(Peak)) != PeakHzStr || Fmt("%.6f", PeakHz(Raw)) != Parts[2]) ++PeakStrDiff;
		WorstRel = std::fmax(WorstRel, std::fmax(R1, R2));
		if (LineSame) ++Exact;
		if (PeakDrop > MaxDrop) MaxDrop = PeakDrop;
	}
	Check(Cases == 300 * SpeciesCount, "parity file has 300 seeds x 7 species (" + std::to_string(Cases) + ")");
	std::printf("ear_rule_core: %d cases, raw PCS lines identical %d/%d, peak %%.6f strings differing %d, worst peak rel diff %.3g,"
		" max octave drop %d; %d checks, %d failures\n", Cases, Exact, Cases, PeakStrDiff, WorstRel, MaxDrop, Checks, Failures);
	return Failures == 0 ? 0 : 1;
}
