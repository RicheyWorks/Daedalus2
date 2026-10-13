// SPDX-License-Identifier: MIT
// The squad-tactics contract (DTO 1) and the local director, checked without Unreal. Build:
//   g++ -std=c++17 -O1 -Wall -Wextra -Werror -fsanitize=address,undefined -I../DaedalusLink/Source/DaedalusLink/Public tactics_core_test.cpp
#include "DaedalusTacticsCore.h"
#include <chrono>
#include <cstdio>
#include <random>
using namespace daedalus::tactics;
static int Passed = 0, Total = 0;
static void Check(const char* Name, bool OK) { ++Total; Passed += OK; std::printf("%s %s\n", OK ? "PASS" : "FAIL", Name); }

static const Order* Find(const Spec& S, const std::string& U)
{
	for (const Order& O : S.Orders) if (O.Unit == U) return &O;
	return nullptr;
}
static double Dist(const Vec& A, const Vec& B) { return std::sqrt((A.X - B.X) * (A.X - B.X) + (A.Y - B.Y) * (A.Y - B.Y)); }

int main(int argc, char** argv)
{
	// --- the format
	const std::string Good = "DTO 1\nsquad orr-1 tick 42\norder foe-a FLANK LEFT 100 200 30 | player keeps to the ridge\n"
		"order foe-b RETREAT - -50.5 0 0\r\n# a comment\n\norder foe-c HOLD - 0 0 0\n";
	ParseResult R = Parse(Good);
	Check("a good spec parses", R.Ok && R.Out.Squad == "orr-1" && R.Out.Tick == 42 && R.Out.Orders.size() == 3);
	Check("the why survives", R.Ok && R.Out.Orders[0].Why == "player keeps to the ridge");
	Check("verbs, sides and points read", R.Ok && R.Out.Orders[0].Do == Verb::Flank && R.Out.Orders[0].Way == Side::Left
		&& R.Out.Orders[1].Do == Verb::Retreat && R.Out.Orders[1].At.X == -50.5);
	ParseResult Again = Parse(Write(R.Out));
	Check("write then parse gives the same spec", Again.Ok && Write(Again.Out) == Write(R.Out));
	struct Bad { const char* Text; const char* Why; };
	const Bad Bads[] = {
		{"", "empty"}, {"DTO 2\nsquad s tick 1\n", "version 2"}, {"DTX 1\n", "wrong magic"},
		{"DTO 1\norder a HOLD - 0 0 0\n", "order before squad"}, {"DTO 1\nsquad s tick 1\norder a JUMP - 0 0 0\n", "unknown verb"},
		{"DTO 1\nsquad s tick 1\norder a FLANK - 0 0 0\n", "flank without a side"},
		{"DTO 1\nsquad s tick 1\norder a HOLD - nan 0 0\n", "NaN point"}, {"DTO 1\nsquad s tick 1\norder a HOLD - 1e300 0 0\n", "huge point"},
		{"DTO 1\nsquad s tick 1\norder a HOLD - 0 0\n", "short order"}, {"DTO 1\nsquad s tick 1\norder a HOLD - 0 0 0\norder a ATTACK - 0 0 0\n", "two orders for one unit"},
		{"DTO 1\nsquad s tick -1\n", "negative tick"}, {"DTO 1\nsquad s tick 1.5\n", "fractional tick"},
		{"DTO 1\nsquad b@d tick 1\n", "bad squad id"}, {"DTO 1\nsquad s tick 1\nsquad t tick 2\n", "second squad"},
		{"DTO 1\n", "no squad"}, {"DTO 1\nsquad s tick 1\n| only a reason\n", "only a reason"},
		{"DTO 1\nsquad s tick 1\nfire everything\n", "unknown line"},
		{"DTO 1\nsquad s tick 1\norder a HOLD - 0x10 0 0\n", "hex number"}, {"DTO 1\nsquad s tick 1\norder a HOLD - 1.5d 0 0\n", "Java suffix"},
		{"DTO 1\nsquad s tick 1\norder a HOLD - inf 0 0\n", "inf"}, {"DTO 1\nsquad s tick 1\norder a HOLD - 1e 0 0\n", "bare exponent"},
	};
	int Refused = 0;
	for (const Bad& B : Bads)
	{
		ParseResult X = Parse(B.Text);
		if (!X.Ok && !X.Error.empty() && X.Out.Orders.empty()) ++Refused;
		else std::printf("  not refused: %s\n", B.Why);
	}
	Check("21 bad specs are each refused whole, with a reason", Refused == 21);
	std::string Big = "DTO 1\nsquad s tick 1\n";
	for (int i = 0; i <= static_cast<int>(MaxOrders); ++i) Big += "order u" + std::to_string(i) + " HOLD - 0 0 0\n";
	Check("more than MaxOrders is refused (bounded work)", !Parse(Big).Ok);
	Check("a refusal names the line", Parse("DTO 1\nsquad s tick 1\norder a JUMP - 0 0 0\n").Error.rfind("line 3", 0) == 0);

	// --- events
	const std::string Ev = WriteEvents(7, {{EventKind::Hit, "foe-a", {1, 2, 3}, 12.5}, {EventKind::Player, "player", {0, 0, 0}, 80}});
	Check("events write as DTE 1", Ev == "DTE 1\ntick 7\nevent HIT foe-a 1.0 2.0 3.0 12.5\nevent PLAYER player 0.0 0.0 0.0 80.0\n");

	// --- geometry
	const Vec P{0, 0, 0}, From{-1000, 0, 0};
	const Vec L = FlankPoint(P, From, Side::Left, 900), Rt = FlankPoint(P, From, Side::Right, 900);
	Check("flank points sit at the radius", std::fabs(Dist(L, P) - 900) < 1e-6 && std::fabs(Dist(Rt, P) - 900) < 1e-6);
	Check("left and right are opposite sides", std::fabs(L.X + Rt.X) < 1e-6 && std::fabs(L.Y + Rt.Y) < 1e-6 && L.Y != 0);
	Check("a flank point is beside the player, not behind the squad", std::fabs(L.X) < 1e-6);
	Check("away-from moves away", Dist(AwayFrom(P, From, 1500), P) > Dist(From, P));
	Check("coincident points still give a direction", std::isfinite(FlankPoint(P, P, Side::Left, 900).X));

	// --- the local director: three foes and one player
	const std::vector<Unit> Three = {{"foe-a", {-600, 0, 0}, 60, 60, true}, {"foe-b", {-900, 300, 0}, 60, 60, true},
		{"foe-c", {-1100, -200, 0}, 60, 60, false}};
	Spec D = Decide("orr-1", 1, Three, P);
	Check("one attacks, two flank", Find(D, "foe-a")->Do == Verb::Attack && Find(D, "foe-b")->Do == Verb::Flank
		&& Find(D, "foe-c")->Do == Verb::Flank);
	Check("the flanks go opposite ways", Find(D, "foe-b")->Way != Find(D, "foe-c")->Way);
	Check("every order says why", std::all_of(D.Orders.begin(), D.Orders.end(), [](const Order& O) { return !O.Why.empty(); }));
	std::vector<Unit> Hurt = Three;
	Hurt[0].Health = 10;
	Spec DH = Decide("orr-1", 2, Hurt, P);
	Check("a badly hurt foe retreats", Find(DH, "foe-a")->Do == Verb::Retreat && Find(DH, "foe-a")->Why == "health 16%");
	Check("the next nearest takes over the attack", Find(DH, "foe-b")->Do == Verb::Attack);
	Check("the retreat point is further from the player", Dist(Find(DH, "foe-a")->At, P) > Dist(Hurt[0].At, P));
	Spec DHigh = Decide("orr-1", 3, Three, Vec{0, 0, 500});
	Check("on high ground the lead defends instead of charging up", Find(DHigh, "foe-a")->Do == Verb::Defend);
	Spec Far = Decide("orr-1", 4, Three, Vec{9000, 0, 0});
	Check("out of range, all hold", std::all_of(Far.Orders.begin(), Far.Orders.end(), [](const Order& O) { return O.Do == Verb::Hold; }));
	Check("nobody, no orders", Decide("s", 5, {}, P).Orders.empty());
	std::vector<Unit> Shuffled = {Three[2], Three[0], Three[1]};
	Check("same world, same orders, whatever the input order", Write(Decide("orr-1", 1, Shuffled, P)) == Write(D));
	Check("the director's own spec parses", Parse(Write(D)).Ok);
	std::vector<Unit> Tie = {{"b", {-500, 0, 0}, 1, 1, true}, {"a", {500, 0, 0}, 1, 1, true}};
	Check("a distance tie goes by name", Find(Decide("s", 1, Tie, P), "a")->Do == Verb::Attack);
	std::vector<Unit> Zero = {{"z", {-500, 0, 0}, 0, 0, true}};
	Check("zero max health is not a division by zero", Find(Decide("s", 1, Zero, P), "z")->Do == Verb::Retreat);

	// --- integration requirements from Astra (team-codex): size cap, roster bootstrap, stale fencing
	{
		std::vector<Unit> Big;
		for (int i = 0; i < 300; ++i) Big.push_back({"b" + std::to_string(i), {-500.0 - i, 0, 0}, 60, 60, true});
		Spec SB = Decide("big", 1, Big, P);
		Check("a 300-unit squad orders its nearest 256 (MaxOrders)", SB.Orders.size() == MaxOrders && Find(SB, "b0") && !Find(SB, "b299"));
		Check("so its spec is never refused for size", Parse(Write(SB)).Ok);
		const std::string Ro = WriteRoster("a1b2c3", "pack-1", 9, {{"pack-1-1", "BLIGHT_SLIME", 42.5, 60, {1, 2, 3}, true}, {"pack-1-2", "STONE_KNIGHT", 0, 120, {4, 5, 6}, false}});
		Check("the roster writes as DTR 1", Ro == "DTR 1\nsession a1b2c3 squad pack-1 tick 9\nunit pack-1-1 BLIGHT_SLIME 42.5 60.0 1.0 2.0 3.0 1\nunit pack-1-2 STONE_KNIGHT 0.0 120.0 4.0 5.0 6.0 0\n");
		Check("first outside spec applies", Check(0, false, 5) == Fence::Apply);
		Check("a newer tick applies", Check(5, true, 6) == Fence::Apply);
		Check("the same tick is a repeat", Check(5, true, 5) == Fence::Repeat);
		Check("an older tick is stale", Check(5, true, 4) == Fence::Stale);
	}

	// --- bounded: latency by squad size (the director runs about once a second, not per frame)
	std::mt19937 Rng(7);
	std::uniform_real_distribution<double> U(-2500, 2500);
	double Worst = 0;
	for (int N : {3, 30, 300, 3000})
	{
		std::vector<Unit> Many;
		for (int i = 0; i < N; ++i) Many.push_back({"u" + std::to_string(i), {U(Rng), U(Rng), 0}, 60, 60, true});
		const auto T0 = std::chrono::steady_clock::now();
		Spec M = Decide("big", 1, Many, P);
		const double Ms = std::chrono::duration<double, std::milli>(std::chrono::steady_clock::now() - T0).count();
		std::printf("  decide %5d units: %.3f ms, %zu orders\n", N, Ms, M.Orders.size());
		if (N == 300) Worst = Ms;
		if (M.Orders.size() != std::min<size_t>(static_cast<size_t>(N), MaxOrders)) Worst = 1e9;   // capped at MaxOrders
	}
	Check("300 units decide in well under one 60 fps frame (16.7 ms)", Worst < 16.7);

	// --- the parity file for the Java port (VoxelIsle-style): 40 seeded squads, their decided specs, plus round-trips
	if (argc > 2 && std::string(argv[1]) == "--write")
	{
		FILE* F = std::fopen(argv[2], "w");
		std::fprintf(F, "# tactics_core_test.cpp --write: per case, the inputs then Write(Decide(...)) between 'spec' and 'end'\n");
		std::mt19937 G(2026);
		for (int Case = 0; Case < 40; ++Case)
		{
			std::uniform_real_distribution<double> Pos(-3000, 3000), Hgt(-400, 700), Hp(0, 60);
			const int N = 1 + static_cast<int>(G() % 7);
			const Vec Pl{std::round(Pos(G)) / 4, std::round(Pos(G)) / 4, std::round(Hgt(G)) / 2};   // quarter-cm points: exact ties
			std::vector<Unit> Us;
			for (int i = 0; i < N; ++i)
				Us.push_back({"u" + std::to_string((Case * 7 + i * 3) % 10), {std::round(Pos(G)) / 4, std::round(Pos(G)) / 4, std::round(Hgt(G) / 4)},
					std::round(Hp(G)), 60, (G() & 1) != 0});
			// unique names
			for (int i = 0; i < N; ++i) Us[i].Name += "-" + std::to_string(i);
			if (Case % 5 == 0)
				for (Unit& U : Us) U.At.X += 6000;   // out of range: everyone HOLDs
			std::fprintf(F, "case %d player %.17g %.17g %.17g\n", Case, Pl.X, Pl.Y, Pl.Z);
			for (const Unit& U : Us)
				std::fprintf(F, "unit %s %.17g %.17g %.17g %.17g %.17g %d\n", U.Name.c_str(), U.At.X, U.At.Y, U.At.Z, U.Health, U.MaxHealth, U.SeesPlayer ? 1 : 0);
			std::fprintf(F, "spec\n%send\n", Write(Decide("sq-" + std::to_string(Case), Case, Us, Pl)).c_str());
		}
		// every refusal, with its exact message (the Java port must refuse the same specs the same way)
		for (const Bad& B : Bads)
		{
			std::string T = B.Text, E;
			for (char C : T) E += C == '\n' ? std::string("\\n") : C == '\r' ? std::string("\\r") : std::string(1, C);
			std::fprintf(F, "bad\t%s\t%s\n", E.c_str(), Parse(B.Text).Error.c_str());
		}
		std::fprintf(F, "roster\t%s\n", [&] { std::string E; for (char C : WriteRoster("a1b2c3", "pack-1", 9, {{"pack-1-1", "BLIGHT_SLIME", 42.5, 60, {1, 2, 3}, true}, {"pack-1-2", "STONE_KNIGHT", 0, 120, {-4.25, 5, 6}, false}})) E += C == '\n' ? std::string("\\n") : std::string(1, C); return E; }().c_str());
		std::fprintf(F, "good\t%s\n", [&] { std::string E; for (char C : Good) E += C == '\n' ? std::string("\\n") : C == '\r' ? std::string("\\r") : std::string(1, C); return E; }().c_str());
		std::fclose(F);
		std::printf("wrote %s\n", argv[2]);
	}
	std::printf("%d/%d\n", Passed, Total);
	return Passed == Total ? 0 : 1;
}
