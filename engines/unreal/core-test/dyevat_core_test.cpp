// SPDX-License-Identifier: MIT
// Dyevat parity (G601): DaedalusDyevatCore.h must regenerate every rack in dyevat_parity.txt from seed + difficulty
// alone (CPython-compatible seeding), pour the same demo path line for line, and match every hand-set vector.
// It also checks that pigment is conserved (every hue keeps Capacity layers) after each pour.
//   g++ -std=c++17 -O1 -Wall -Wextra -Wshadow -Werror -I../DaedalusLink/Source/DaedalusLink/Public dyevat_core_test.cpp -o dyevat_core_test && ./dyevat_core_test dyevat_parity.txt
#include "DaedalusDyevatCore.h"
#include <cstdio>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>

using namespace daedalus::dyevat;

namespace {

int Failures = 0;
void Check(bool Ok, const std::string& Want, const std::string& Got)
{
	if (Ok) return;
	if (++Failures <= 10) std::printf("MISMATCH\n want: %s\n  got: %s\n", Want.c_str(), Got.c_str());
}

std::string Field(const std::string& Line, const std::string& Key)
{
	const std::string Needle = " " + Key + "=";
	const size_t P = Line.find(Needle);
	if (P == std::string::npos) return "";
	const size_t S = P + Needle.size(), E = Line.find(' ', S);
	return Line.substr(S, E == std::string::npos ? std::string::npos : E - S);
}

std::string Status(const Game& G)
{
	std::ostringstream O;
	O << "vats=" << G.VatsString() << " sealed=" << G.SealedString() << " pours=" << G.Pours << " score=" << G.Score
	  << " over=" << (G.Over ? 1 : 0) << " won=" << (G.Won ? 1 : 0);
	return O.str();
}

std::string PourText(Pour P) { return std::to_string(P.From) + "," + std::to_string(P.To); }

bool Conserved(const Game& G)
{
	std::vector<int> Count(static_cast<size_t>(G.Hues + 1), 0);
	for (int V = 0; V < G.VatCount; ++V)
		for (int I = 0; I < G.At(V).Count; ++I)
		{
			const int H = G.At(V).Layers[static_cast<size_t>(I)];
			if (H < 1 || H > G.Hues) return false;
			++Count[static_cast<size_t>(H)];
		}
	for (int H = 1; H <= G.Hues; ++H) if (Count[static_cast<size_t>(H)] != Capacity) return false;
	return true;
}

/** A hand-set rack from the vector line (vats bottom to top, '-' empty). */
Game Rack(const std::string& Line)
{
	Game G; G.Start(1, "easy");
	G.Hues = std::stoi(Field(Line, "hues"));
	G.PourLimit = G.Pours = std::stoi(Field(Line, "pours"));
	const std::string Last = Field(Line, "last");
	const size_t Comma = Last.find(',');
	G.Last = { std::stoi(Last.substr(0, Comma)), std::stoi(Last.substr(Comma + 1)) };
	G.Vats = {}; G.Sealed = {}; G.VatCount = 0;
	std::stringstream S(Field(Line, "vats")); std::string Row;
	while (std::getline(S, Row, ';'))
	{
		Vat& V = G.Vats[static_cast<size_t>(G.VatCount)];
		if (Row != "-") for (char Ch : Row) V.Layers[static_cast<size_t>(V.Count++)] = Ch - '0';
		G.Sealed[static_cast<size_t>(G.VatCount)] = V.FullOneHue();
		++G.VatCount;
	}
	G.Score = 0; G.Over = G.Won = false;
	return G;
}

Pour ParsePour(const std::string& Text)
{
	const size_t Comma = Text.find(',');
	return { std::stoi(Text.substr(0, Comma)), std::stoi(Text.substr(Comma + 1)) };
}

} // namespace

int main(int Argc, char** Argv)
{
	if (Argc < 2) { std::printf("usage: dyevat_core_test dyevat_parity.txt\n"); return 2; }
	std::ifstream In(Argv[1]);
	if (!In) { std::printf("cannot open %s\n", Argv[1]); return 2; }
	std::vector<std::string> Lines; std::string L;
	while (std::getline(In, L)) if (!L.empty() && L[0] != '#') Lines.push_back(L);

	int Games = 0, Moves = 0, Vectors = 0;
	for (size_t I = 0; I < Lines.size(); ++I)
	{
		const std::string& Line = Lines[I];
		if (Line.rfind("game ", 0) == 0)
		{
			++Games;
			const std::uint32_t Seed = static_cast<std::uint32_t>(std::stoul(Field(Line, "s")));
			const std::string Diff = Field(Line, "d");
			Game G;
			Check(G.Start(Seed, Diff), Line, "start failed");
			const std::string Head = "game s=" + std::to_string(Seed) + " d=" + Diff + " vats=" + G.VatsString() + " sealed=" + G.SealedString() + " pours=" + std::to_string(G.Pours);
			Check(Head == Line, Line, Head);
			int Turn = 0;
			while (!G.Over && I + 1 < Lines.size() && Lines[I + 1].rfind("move ", 0) == 0)
			{
				++I; ++Moves; ++Turn;
				const Pour P = G.DemoAction();
				std::string Res;
				Check(G.Step(P, Res) == Game::Act::Ok, Lines[I], "pour refused");
				Check(Conserved(G), Lines[I], "pigment not conserved");
				const std::string Got = "move t=" + std::to_string(Turn) + " act=" + PourText(P) + " " + Status(G) + " res=" + Res;
				Check(Got == Lines[I], Lines[I], Got);
			}
			Check(G.Over, Line, "game did not end where the fixture ends");
			++I;
			const std::string End = "end  score=" + std::to_string(G.Score) + " won=" + std::to_string(G.Won ? 1 : 0) + " sealed=" + std::to_string(G.SealedCount()) + " pours=" + std::to_string(G.Pours);
			Check(I < Lines.size() && End == Lines[I], I < Lines.size() ? Lines[I] : "<eof>", End);
		}
		else if (Line.rfind("vector ", 0) == 0)
		{
			++Vectors;
			Game G = Rack(Line);
			Check(I + 1 < Lines.size(), Line, "vector without step");
			const std::string& Want = Lines[++I];
			const Pour Demo = G.DemoAction();
			const Pour Act = ParsePour(Field(Want, "act"));
			std::string Res;
			G.Step(Act, Res);
			const std::string Got = "step act=" + PourText(Act) + " demo=" + PourText(Demo) + " " + Status(G) + " res=" + Res;
			Check(Got == Want, Want, Got);
		}
		else
		{
			Check(false, "game/vector/move/end line", Line);
		}
	}
	Check(Games == 30, "30 games", std::to_string(Games));
	Check(Vectors >= 10, ">=10 vectors", std::to_string(Vectors));
	std::printf("dyevat parity: %d games, %d pours, %d vectors, %d failures\n", Games, Moves, Vectors, Failures);
	return Failures == 0 ? 0 : 1;
}
