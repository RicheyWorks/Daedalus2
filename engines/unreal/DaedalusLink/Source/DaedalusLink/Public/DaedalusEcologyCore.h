// SPDX-License-Identifier: MIT
// DBE 1 / DBE-E 1 (ADR-061): the Unreal side of Reactive Battlefield Ecology, plain C++17, no Unreal types.
// Mirrors com.daedalus.world.battlefield.Dbe: all-or-nothing parsing with the line number and reason.
#pragma once
#include <cerrno>
#include <cmath>
#include <cstdlib>
#include <cstdint>
#include <sstream>
#include <string>
#include <vector>

namespace daedalus { namespace ecology {

struct Veg { char Code; double Cover, Concealment, Flammability; };
inline const Veg* VegOf(char C)
{
	static const Veg Table[] = {
		{'.', 0.00, 0.00, 0.00}, {'m', 0.05, 0.35, 0.60}, {'s', 0.25, 0.65, 0.45},
		{'p', 0.55, 0.70, 0.35}, {'o', 0.80, 0.60, 0.12}, {'w', 0.10, 0.40, 0.00}};
	for (const Veg& V : Table) { if (V.Code == C) { return &V; } }
	return nullptr;
}

struct Field
{
	int W = 0, H = 0; double CellCm = 0, OriginX = 0, OriginY = 0; long long Seed = 0, Tick = 0;
	std::vector<char> Cells; std::vector<int> Burn;
	int CellI(double X) const { return Clamp((int)std::floor((X - OriginX) / CellCm), W); }
	int CellJ(double Y) const { return Clamp((int)std::floor((Y - OriginY) / CellCm), H); }
	char CodeAt(double X, double Y) const { return Cells[(size_t)CellJ(Y) * W + CellI(X)]; }
	double CoverAt(double X, double Y) const { return VegOf(CodeAt(X, Y))->Cover; }
	double ConcealmentAt(double X, double Y) const { return VegOf(CodeAt(X, Y))->Concealment; }
	bool BurningAt(double X, double Y) const { return Burn[(size_t)CellJ(Y) * W + CellI(X)] > 0; }
	double CentreX(int I) const { return OriginX + (I + 0.5) * CellCm; }
	double CentreY(int J) const { return OriginY + (J + 0.5) * CellCm; }
	static int Clamp(int V, int N) { return V < 0 ? 0 : (V >= N ? N - 1 : V); }
};

struct Result { bool Ok = false; std::string Error; };

namespace detail {
inline std::vector<std::string> Split(const std::string& L)
{
	std::vector<std::string> F; std::istringstream S(L); std::string T;
	while (S >> T) { F.push_back(T); }
	return F;
}
inline bool Int(const std::string& S, long long& Out)
{
	if (S.empty()) { return false; }
	char* E = nullptr; errno = 0; Out = std::strtoll(S.c_str(), &E, 10);
	return errno == 0 && E == S.c_str() + S.size(); // no exceptions: Unreal game builds compile without /EHsc
}
inline bool Num(const std::string& S, double& Out)
{
	if (S.empty()) { return false; }
	char* E = nullptr; errno = 0; Out = std::strtod(S.c_str(), &E);
	return errno == 0 && E == S.c_str() + S.size() && std::isfinite(Out);
}
inline Result Bad(size_t Line, const std::string& Why) { return {false, "DBE line " + std::to_string(Line) + ": " + Why}; }
inline std::vector<std::string> Lines(const std::string& Spec)
{
	std::vector<std::string> L; std::string Cur;
	for (char C : Spec) { if (C == '\n') { L.push_back(Cur); Cur.clear(); } else if (C != '\r') { Cur += C; } }
	L.push_back(Cur);
	while (!L.empty() && L.back().find_first_not_of(" \t") == std::string::npos) { L.pop_back(); }
	return L;
}
} // namespace detail

inline Result ReadSnapshot(const std::string& Spec, Field& Out)
{
	using namespace detail;
	const std::vector<std::string> L = Lines(Spec);
	if (L.size() < 3 || L[0] != "DBE 1") { return Bad(1, "first line must be 'DBE 1'"); }
	std::vector<std::string> G = Split(L[1]);
	if (G.size() != 7 || G[0] != "grid") { return Bad(2, "'grid' needs 6 values"); }
	long long W, H, Seed; double Cell, Ox, Oy;
	if (!Int(G[1], W) || !Int(G[2], H) || W < 1 || H < 1 || W > 4096 || H > 4096) { return Bad(2, "width/height must be 1..4096"); }
	if (!Num(G[3], Cell) || Cell <= 0 || !Num(G[4], Ox) || !Num(G[5], Oy) || !Int(G[6], Seed)) { return Bad(2, "bad grid numbers"); }
	std::vector<std::string> T = Split(L[2]);
	long long Tick;
	if (T.size() != 2 || T[0] != "tick" || !Int(T[1], Tick) || Tick < 0) { return Bad(3, "'tick' needs one integer >= 0"); }
	if (L.size() < 3 + (size_t)H) { return Bad(L.size() + 1, "expected " + std::to_string(H) + " row lines"); }
	Field F; F.W = (int)W; F.H = (int)H; F.CellCm = Cell; F.OriginX = Ox; F.OriginY = Oy; F.Seed = Seed; F.Tick = Tick;
	F.Cells.assign((size_t)(W * H), '.'); F.Burn.assign((size_t)(W * H), 0);
	for (long long J = 0; J < H; ++J)
	{
		const size_t Ln = 4 + (size_t)J; std::vector<std::string> R = Split(L[3 + J]); long long Idx;
		if (R.size() != 3 || R[0] != "row") { return Bad(Ln, "'row' needs 2 values"); }
		if (!Int(R[1], Idx) || Idx != J) { return Bad(Ln, "rows must be in order, expected row " + std::to_string(J)); }
		if ((long long)R[2].size() != W) { return Bad(Ln, "row has " + std::to_string(R[2].size()) + " cells, grid width is " + std::to_string(W)); }
		for (long long I = 0; I < W; ++I)
		{
			if (!VegOf(R[2][I])) { return Bad(Ln, std::string("unknown vegetation code '") + R[2][I] + "'"); }
			F.Cells[(size_t)(J * W + I)] = R[2][I];
		}
	}
	for (size_t K = 3 + (size_t)H; K < L.size(); ++K)
	{
		const size_t Ln = K + 1; std::vector<std::string> R = Split(L[K]); long long I, J, Left;
		if (R.size() != 4 || R[0] != "fire") { return Bad(Ln, "'fire' needs 3 values"); }
		if (!Int(R[1], I) || !Int(R[2], J) || !Int(R[3], Left)) { return Bad(Ln, "fire values must be integers"); }
		if (I < 0 || J < 0 || I >= W || J >= H) { return Bad(Ln, "fire cell outside grid"); }
		if (Left < 1 || Left > 64) { return Bad(Ln, "fire ticks must be 1..64"); }
		if (VegOf(F.Cells[(size_t)(J * W + I)])->Flammability <= 0) { return Bad(Ln, "cell cannot burn"); }
		F.Burn[(size_t)(J * W + I)] = (int)Left;
	}
	Out = std::move(F);
	return {true, ""};
}

enum class EventKind { IGNITE, BLAST, DOUSE };
struct Event { EventKind Kind; double X, Y, Z, RadiusCm; };
constexpr int MaxEvents = 256;

// Writes combat events Unreal -> Java; refuses what Dbe.readEvents would refuse.
inline Result WriteEvents(const std::vector<Event>& Events, std::string& Out)
{
	if ((int)Events.size() > MaxEvents) { return {false, "at most 256 events"}; }
	std::ostringstream S; S.precision(17); S << "DBE-E 1\n";
	for (const Event& E : Events)
	{
		if (!std::isfinite(E.X) || !std::isfinite(E.Y) || !std::isfinite(E.Z) || !(E.RadiusCm >= 0 && E.RadiusCm <= 100000)) { return {false, "bad event values"}; }
		const char* K = E.Kind == EventKind::IGNITE ? "IGNITE" : (E.Kind == EventKind::BLAST ? "BLAST" : "DOUSE");
		S << "event " << K << ' ' << E.X << ' ' << E.Y << ' ' << E.Z << ' ' << E.RadiusCm << '\n';
	}
	Out = S.str();
	return {true, ""};
}

}} // namespace daedalus::ecology