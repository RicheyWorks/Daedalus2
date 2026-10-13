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

int main()
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
	};
	int Refused = 0;
	for (const Bad& B : Bads)
	{
		ParseResult X = Parse(B.Text);
		if (!X.Ok && !X.Error.empty() && X.Out.Orders.empty()) ++Refused;
		else std::printf("  not refused: %s\n", B.Why);
	}
	Check("17 bad specs are each refused whole, with a reason", Refused == 17);
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
		if (M.Orders.size() != static_cast<size_t>(N)) Worst = 1e9;
	}
	Check("300 units decide in well under one 60 fps frame (16.7 ms)", Worst < 16.7);

	std::printf("%d/%d\n", Passed, Total);
	return Passed == Total ? 0 : 1;
}
