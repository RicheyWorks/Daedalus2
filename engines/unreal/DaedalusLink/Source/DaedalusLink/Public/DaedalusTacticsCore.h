// SPDX-License-Identifier: MIT
#pragma once
// The squad-tactics contract between the Java combat director and Unreal (ADR-060), in plain C++. There are no
// Unreal types, so core-test builds and checks it with ASan/UBSan.
//
// Java decides at squad timescale (about once a second): who flanks, who holds, who falls back. Unreal executes at
// frame timescale: movement, attacks and hits stay in ADaedalusTarget. Neither waits on the other inside a frame.
//
// DTO 1 (Daedalus Tactical Orders), a versioned plain-text spec like the retro realm's "DRR 1":
//     DTO 1
//     squad <id> tick <n>
//     order <unit> <VERB> <SIDE> <x> <y> <z> | <why, free text>
// VERB is HOLD, ATTACK, FLANK, DEFEND, RETREAT or REINFORCE. SIDE is LEFT, RIGHT or - . The point is in Unreal cm.
// Events flow back as "DTE 1" lines: "event <KIND> <unit> <x> <y> <z> <value>", where KIND is SEEN, HIT, DOWN or
// PLAYER (the PLAYER line's unit is "player").
//
// When no Java director is attached, Decide() is a small deterministic, explainable director for one squad and one
// player. It is the "3 foes vs 1 player" baseline, and it writes the same DTO 1 that Java will.

#include <algorithm>
#include <cctype>
#include <charconv>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <sstream>
#include <string>
#include <unordered_set>
#include <vector>

namespace daedalus { namespace tactics {

enum class Verb { Hold, Attack, Flank, Defend, Retreat, Reinforce };
enum class Side { None, Left, Right };

constexpr int Version = 1;
constexpr std::size_t MaxOrders = 256;        // a spec bigger than this is refused (bounded work per frame)
constexpr std::size_t MaxLine = 512;
constexpr double MaxCoord = 1.0e8;            // 1000 km: anything beyond is a bug, not a place

inline const char* VerbName(Verb V)
{
	static const char* N[] = {"HOLD", "ATTACK", "FLANK", "DEFEND", "RETREAT", "REINFORCE"};
	return N[static_cast<int>(V)];
}
inline const char* SideName(Side S) { return S == Side::Left ? "LEFT" : S == Side::Right ? "RIGHT" : "-"; }

inline bool ParseVerb(const std::string& S, Verb& Out)
{
	for (int i = 0; i < 6; ++i)
		if (S == VerbName(static_cast<Verb>(i))) { Out = static_cast<Verb>(i); return true; }
	return false;
}
inline bool ParseSide(const std::string& S, Side& Out)
{
	if (S == "LEFT") { Out = Side::Left; return true; }
	if (S == "RIGHT") { Out = Side::Right; return true; }
	if (S == "-") { Out = Side::None; return true; }
	return false;
}

struct Vec { double X = 0, Y = 0, Z = 0; };

struct Order
{
	std::string Unit;
	Verb Do = Verb::Hold;
	Side Way = Side::None;
	Vec At;
	std::string Why;
};

struct Spec
{
	std::string Squad;
	long long Tick = 0;
	std::vector<Order> Orders;
};

struct ParseResult
{
	bool Ok = false;
	std::string Error;   // first problem, with its line number
	Spec Out;
};

inline bool Token(const std::string& S)
{
	if (S.empty() || S.size() > 64) return false;
	for (char C : S)
		if (!(std::isalnum(static_cast<unsigned char>(C)) || C == '_' || C == '-' || C == '.')) return false;
	return true;
}

/** Plain decimals only, the same grammar in every language: [+-]? (digits [. digits?] | . digits) ([eE] [+-]? digits)?
 * (strtod alone would also take hex, "inf" and "nan"; Java's parser takes a "d" suffix). */
inline bool Decimal(const std::string& S)
{
	std::size_t i = 0, n = S.size();
	auto Digits = [&]() { const std::size_t b = i; while (i < n && std::isdigit(static_cast<unsigned char>(S[i]))) ++i; return i - b; };
	if (i < n && (S[i] == '+' || S[i] == '-')) ++i;
	const std::size_t Whole = Digits();
	std::size_t Frac = 0;
	if (i < n && S[i] == '.') { ++i; Frac = Digits(); }
	if (Whole == 0 && Frac == 0) return false;
	if (i < n && (S[i] == 'e' || S[i] == 'E'))
	{
		++i;
		if (i < n && (S[i] == '+' || S[i] == '-')) ++i;
		if (Digits() == 0) return false;
	}
	return i == n;
}

inline bool Number(const std::string& S, double& Out)
{
	if (S.empty() || !Decimal(S)) return false;
	// from_chars: correctly rounded like strtod, no locale, no allocation. It doesn't take a leading '+'.
	const char* B = S.data() + (S[0] == '+' ? 1 : 0);
	const std::from_chars_result R = std::from_chars(B, S.data() + S.size(), Out);
	return R.ec == std::errc() && R.ptr == S.data() + S.size() && std::isfinite(Out) && std::fabs(Out) <= MaxCoord;
}

/**
 * Reads a DTO 1 spec. All or nothing: any bad line refuses the whole spec, so a squad never gets half an order.
 * Runs on the game thread, so it walks the text once with indices: no stringstreams, tokens as views into the line,
 * and a hash set for duplicate units (a full 256-order spec was 263 us with streams; see tactics_core_test).
 */
inline ParseResult Parse(const std::string& Text)
{
	ParseResult R;
	int N = 0;
	bool Head = false, SquadSeen = false;
	std::unordered_set<std::string> Units;
	auto Fail = [&](const std::string& Why) { R.Ok = false; R.Error = "line " + std::to_string(N) + ": " + Why; R.Out = Spec(); return R; };
	auto Space = [](char C) { return C == ' ' || C == '\t' || C == '\n' || C == '\v' || C == '\f' || C == '\r'; };
	constexpr int MaxTokens = 8;   // more than any line takes; a 9th only has to make the count wrong
	std::string T[MaxTokens];
	const std::size_t Size = Text.size();
	std::size_t Pos = 0;
	while (Pos < Size)
	{
		std::size_t End = Text.find('\n', Pos);
		if (End == std::string::npos) End = Size;
		std::size_t LineEnd = End;
		const std::size_t LineStart = Pos;
		Pos = End + 1;
		++N;
		if (LineEnd > LineStart && Text[LineEnd - 1] == '\r') --LineEnd;
		if (LineEnd - LineStart > MaxLine) return Fail("line too long");
		if (LineEnd == LineStart || Text[LineStart] == '#') continue;
		std::size_t BodyEnd = LineEnd;
		std::string Why;
		for (std::size_t i = LineStart; i < LineEnd; ++i)
			if (Text[i] == '|')
			{
				BodyEnd = i;
				std::size_t W = i + 1;
				while (W < LineEnd && Text[W] == ' ') ++W;
				Why.assign(Text, W, LineEnd - W);
				break;
			}
		int Count = 0;
		for (std::size_t i = LineStart; i < BodyEnd;)
		{
			while (i < BodyEnd && Space(Text[i])) ++i;
			if (i >= BodyEnd) break;
			const std::size_t B = i;
			while (i < BodyEnd && !Space(Text[i])) ++i;
			if (Count < MaxTokens) T[Count].assign(Text, B, i - B);
			++Count;
		}
		if (Count == 0) return Fail("a line with only a reason");
		if (!Head)
		{
			if (Count != 2 || T[0] != "DTO") return Fail("expected 'DTO 1'");
			if (T[1] != std::to_string(Version)) return Fail("unsupported version " + T[1]);
			Head = true;
			continue;
		}
		if (T[0] == "squad")
		{
			if (SquadSeen) return Fail("second squad line");
			if (Count != 4 || T[2] != "tick" || !Token(T[1])) return Fail("expected 'squad <id> tick <n>'");
			double Tk;
			if (!Number(T[3], Tk) || Tk < 0 || Tk != std::floor(Tk)) return Fail("bad tick");
			R.Out.Squad = T[1];
			R.Out.Tick = static_cast<long long>(Tk);
			SquadSeen = true;
			continue;
		}
		if (T[0] == "order")
		{
			if (!SquadSeen) return Fail("order before the squad line");
			if (Count != 7) return Fail("expected 'order <unit> <VERB> <SIDE> <x> <y> <z>'");
			if (R.Out.Orders.size() >= MaxOrders) return Fail("more than " + std::to_string(MaxOrders) + " orders");
			Order O;
			if (!Token(T[1])) return Fail("bad unit id");
			O.Unit = T[1];
			if (!ParseVerb(T[2], O.Do)) return Fail("unknown verb " + T[2]);
			if (!ParseSide(T[3], O.Way)) return Fail("unknown side " + T[3]);
			if (O.Do == Verb::Flank && O.Way == Side::None) return Fail("FLANK needs LEFT or RIGHT");
			if (!Number(T[4], O.At.X) || !Number(T[5], O.At.Y) || !Number(T[6], O.At.Z)) return Fail("bad point");
			if (!Units.insert(O.Unit).second) return Fail("two orders for " + O.Unit);
			O.Why = std::move(Why);
			if (R.Out.Orders.empty()) R.Out.Orders.reserve(64);
			R.Out.Orders.push_back(std::move(O));
			continue;
		}
		return Fail("unknown line '" + T[0] + "'");
	}
	if (!Head) { N = 0; return Fail("empty spec"); }
	if (!SquadSeen) return Fail("no squad line");
	R.Ok = true;
	return R;
}

/** printf %.1f, appended in place (the exact bytes Java and JS match). std::to_chars is specified to give printf's
 * bytes and is several times faster; tactics_core_test checks the two agree on a million values. */
inline void AppendNum(std::string& Out, double V)
{
	char B[352];   // %.1f of the largest double is 309 digits + sign + ".0"
	const std::to_chars_result R = std::to_chars(B, B + sizeof B, V, std::chars_format::fixed, 1);
	if (R.ec == std::errc()) { Out.append(B, R.ptr); return; }
	const int L = std::snprintf(B, sizeof B, "%.1f", V);
	Out.append(B, L > 0 ? static_cast<std::size_t>(L) : 0);
}

inline std::string Num(double V)
{
	std::string S;
	AppendNum(S, V);
	return S;
}

inline std::string Write(const Spec& S)
{
	std::string Out;
	Out.reserve(32 + S.Orders.size() * 72);
	Out += "DTO 1\nsquad ";
	Out += S.Squad;
	Out += " tick ";
	Out += std::to_string(S.Tick);
	Out += '\n';
	for (const Order& O : S.Orders)
	{
		Out += "order ";
		Out += O.Unit;
		Out += ' ';
		Out += VerbName(O.Do);
		Out += ' ';
		Out += SideName(O.Way);
		Out += ' ';
		AppendNum(Out, O.At.X);
		Out += ' ';
		AppendNum(Out, O.At.Y);
		Out += ' ';
		AppendNum(Out, O.At.Z);
		if (!O.Why.empty())
		{
			Out += " | ";
			const std::size_t From = Out.size();
			Out += O.Why;
			std::replace(Out.begin() + static_cast<std::ptrdiff_t>(From), Out.end(), '\n', ' ');
		}
		Out += '\n';
	}
	return Out;
}

// ------------------------------------------------------------------------------------------------ events (DTE 1)

enum class EventKind { Seen, Hit, Down, Player };

struct Event
{
	EventKind Kind = EventKind::Seen;
	std::string Unit;
	Vec At;
	double Value = 0;   // HIT: damage taken; SEEN: 1/0; DOWN: 0; PLAYER: health
};

inline std::string WriteEvents(long long Tick, const std::vector<Event>& E)
{
	static const char* K[] = {"SEEN", "HIT", "DOWN", "PLAYER"};
	std::string Out;
	Out.reserve(24 + E.size() * 56);
	Out += "DTE 1\ntick ";
	Out += std::to_string(Tick);
	Out += '\n';
	for (const Event& Ev : E)
	{
		Out += "event ";
		Out += K[static_cast<int>(Ev.Kind)];
		Out += ' ';
		Out += Ev.Unit;
		for (double V : {Ev.At.X, Ev.At.Y, Ev.At.Z, Ev.Value})
		{
			Out += ' ';
			AppendNum(Out, V);
		}
		Out += '\n';
	}
	return Out;
}

// ------------------------------------------------------------------------------------------------ roster (DTR 1)

/** One unit as the host knows it: the trusted bootstrap Java needs (DTE 1 events alone can't build a Frame). */
struct RosterUnit
{
	std::string Unit, Kind;
	double Health = 0, MaxHealth = 0;
	Vec At;
	bool SeesPlayer = false;
};

/**
 * DTR 1 (Daedalus Tactical Roster), written by the host on request:
 *     DTR 1
 *     session <id> squad <id> tick <n>
 *     unit <id> <KIND> <health> <maxHealth> <x> <y> <z> <sees 0|1>
 * The session changes whenever the Unreal world starts (a new Play or game), so Java knows to start a new encounter.
 */
inline std::string WriteRoster(const std::string& Session, const std::string& Squad, long long Tick, const std::vector<RosterUnit>& Units)
{
	std::string Out;
	Out.reserve(64 + Units.size() * 64);
	Out += "DTR 1\nsession ";
	Out += Session;
	Out += " squad ";
	Out += Squad;
	Out += " tick ";
	Out += std::to_string(Tick);
	Out += '\n';
	for (const RosterUnit& U : Units)
	{
		Out += "unit ";
		Out += U.Unit;
		Out += ' ';
		Out += U.Kind;
		for (double V : {U.Health, U.MaxHealth, U.At.X, U.At.Y, U.At.Z})
		{
			Out += ' ';
			AppendNum(Out, V);
		}
		Out += U.SeesPlayer ? " 1\n" : " 0\n";
	}
	return Out;
}

// ------------------------------------------------------------------------------------------------ fencing

/** What a squad's latest outside (Java) spec tick allows: newer applies, the same tick is a repeat, older is stale. */
enum class Fence { Apply, Repeat, Stale };
inline Fence Check(long long LastTick, bool HaveLast, long long Tick)
{
	if (!HaveLast || Tick > LastTick) return Fence::Apply;
	return Tick == LastTick ? Fence::Repeat : Fence::Stale;
}

// ------------------------------------------------------------------------------------------------ geometry

/** Where to stand to flank: a point Radius from the player, 90 degrees round from the squad's side of them. */
inline Vec FlankPoint(const Vec& Player, const Vec& From, Side Way, double Radius)
{
	double DX = From.X - Player.X, DY = From.Y - Player.Y;
	const double L = std::sqrt(DX * DX + DY * DY);
	if (L < 1e-6) { DX = 1; DY = 0; }
	else { DX /= L; DY /= L; }
	// Left of the line squad -> player (seen from the squad) is a quarter turn; right is the other quarter.
	const double S = Way == Side::Left ? 1.0 : -1.0;
	return Vec{Player.X + -DY * S * Radius, Player.Y + DX * S * Radius, Player.Z};
}

/** A point Distance from the player, straight away from them through From. */
inline Vec AwayFrom(const Vec& Player, const Vec& From, double Distance)
{
	double DX = From.X - Player.X, DY = From.Y - Player.Y;
	const double L = std::sqrt(DX * DX + DY * DY);
	if (L < 1e-6) { DX = 1; DY = 0; }
	else { DX /= L; DY /= L; }
	return Vec{From.X + DX * Distance, From.Y + DY * Distance, From.Z};
}

// ------------------------------------------------------------------------------------------------ local director

struct Unit
{
	std::string Name;
	Vec At;
	double Health = 1, MaxHealth = 1;
	bool SeesPlayer = false;
};

struct Settings
{
	double RetreatBelow = 0.3;     // fraction of health
	double FlankRadius = 900;      // cm
	double RetreatDistance = 1500; // cm
	double HighGround = 300;       // the player this much above the squad's mean counts as holding high ground
	double Engage = 2600;          // nobody acts beyond this (the foes' aggro range)
};

/**
 * One squad's orders for this tick. It is deterministic and does not depend on the input order (units are ranked
 * by distance, then name). Its cost is O(n log n). Every order says why.
 * - Below RetreatBelow health: RETREAT, straight away from the player.
 * - The nearest healthy unit ATTACKs, or DEFENDs the squad's centre if the player holds high ground (no free kills
 *   on a slope).
 * - The next two FLANK, LEFT then RIGHT, to cut off escape.
 * - Everyone else DEFENDs the centre.
 * - If nobody is in range, everyone HOLDs where they are.
 */
inline Spec Decide(const std::string& Squad, long long Tick, std::vector<Unit> Units, const Vec& Player,
	const Settings& S = Settings())
{
	Spec Out;
	Out.Squad = Squad;
	Out.Tick = Tick;
	if (Units.empty()) return Out;
	auto D2 = [&](const Unit& U) {
		const double DX = U.At.X - Player.X, DY = U.At.Y - Player.Y, DZ = U.At.Z - Player.Z;
		return DX * DX + DY * DY + DZ * DZ;
	};
	std::sort(Units.begin(), Units.end(), [&](const Unit& A, const Unit& B) {
		const double DA = D2(A), DB = D2(B);
		return DA != DB ? DA < DB : A.Name < B.Name;
	});
	// A spec carries at most MaxOrders orders (the parser refuses more, whole). A bigger squad orders its nearest
	// MaxOrders units; the rest fight alone this tick. Split big packs into several squads to order them all.
	if (Units.size() > MaxOrders) Units.resize(MaxOrders);
	Vec Mid;
	for (const Unit& U : Units) { Mid.X += U.At.X; Mid.Y += U.At.Y; Mid.Z += U.At.Z; }
	Mid.X /= Units.size(); Mid.Y /= Units.size(); Mid.Z /= Units.size();
	const bool InRange = std::sqrt(D2(Units.front())) <= S.Engage;
	const bool High = Player.Z - Mid.Z > S.HighGround;
	int Healthy = 0;
	for (const Unit& U : Units)
	{
		Order O;
		O.Unit = U.Name;
		const double Frac = U.MaxHealth > 0 ? U.Health / U.MaxHealth : 0;
		const int Dist = static_cast<int>(std::sqrt(D2(U)));
		if (!InRange)
		{
			O.Do = Verb::Hold;
			O.At = U.At;
			O.Why = "player out of range (" + std::to_string(Dist) + " cm)";
		}
		else if (Frac < S.RetreatBelow)
		{
			O.Do = Verb::Retreat;
			O.At = AwayFrom(Player, U.At, S.RetreatDistance);
			O.Why = "health " + std::to_string(static_cast<int>(Frac * 100)) + "%";
		}
		else
		{
			const int Rank = Healthy++;
			if (Rank == 0)
			{
				O.Do = High ? Verb::Defend : Verb::Attack;
				O.At = High ? Mid : Player;
				O.Why = High ? "player holds high ground; hold the approach" : "closest (" + std::to_string(Dist) + " cm)";
			}
			else if (Rank <= 2)
			{
				O.Do = Verb::Flank;
				O.Way = Rank == 1 ? Side::Left : Side::Right;
				O.At = FlankPoint(Player, Mid, O.Way, S.FlankRadius);
				O.Why = std::string("cut off escape, ") + (Rank == 1 ? "left" : "right");
			}
			else
			{
				O.Do = Verb::Defend;
				O.At = Mid;
				O.Why = "hold the squad's centre";
			}
		}
		Out.Orders.push_back(O);
	}
	// Keep the orders in name order, so the written spec doesn't depend on who happened to be nearest.
	std::sort(Out.Orders.begin(), Out.Orders.end(), [](const Order& A, const Order& B) { return A.Unit < B.Unit; });
	return Out;
}

}}  // namespace daedalus::tactics
