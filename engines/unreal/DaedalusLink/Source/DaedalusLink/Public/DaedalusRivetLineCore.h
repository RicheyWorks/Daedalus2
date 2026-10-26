// SPDX-License-Identifier: MIT
// G112: plain C++17 port of G104 Rivet Line (daedalus-core world/forge/RivetLine.java), header-only and Unreal-ready.
// Head the ark's hull rivets: a seeded tray (one rivet per hole, ArkRivetsPerSeam per seam), an 800 ms setting
// window, TIGHT/SNUG/LOOSE/SPOILED seats, and good rivets per seam ready for Ark::Rivets. Encode() gives the same
// RVL 1 line as RivetLine.Result.encode(); RivetLineParityTest.java checks that line for line.
#pragma once

#include "DaedalusArkDrydockCore.h"
#include <cstdint>
#include <string>
#include <vector>

namespace daedalus { namespace forge {

constexpr int RivetWindowMs = 800;
constexpr int RivetTightStrikes = 3;

enum class RivetSeat : int { Tight = 0, Snug, Loose, Spoiled };
constexpr int RivetSeatCount = 4;
inline const char* RivetSeatName(RivetSeat S)
{
	static const char* N[RivetSeatCount] = { "TIGHT", "SNUG", "LOOSE", "SPOILED" };
	return N[static_cast<int>(S)];
}
// One letter per seat in Encode(): T(ight), N (sNug), L(oose), X (spoiled).
inline char RivetSeatLetter(RivetSeat S) { static const char L[] = "TNLX"; return L[static_cast<int>(S)]; }

struct RivetTray { ArkClass C; std::vector<int> ReadyMs; int Holes() const { return static_cast<int>(ReadyMs.size()); } };
struct RivetSet { int AtMs; int Strikes; };

// Same draw as RivetLine.tray: SplittableRandom(seed ^ 0x51E7), ready 1500 + 50 * nextInt(20) ms per hole.
inline RivetTray MakeRivetTray(ArkClass C, int64_t Seed)
{
	SplitRng Rng(Seed ^ 0x51E7LL);
	RivetTray T{ C, {} };
	const int Holes = ArkInfo(C).Plates * ArkRivetsPerSeam;
	T.ReadyMs.reserve(Holes);
	for (int i = 0; i < Holes; ++i) T.ReadyMs.push_back(1500 + 50 * Rng.NextInt(20));
	return T;
}

// How one rivet seated; a null set (no set at all) spoils it, as in Java.
inline RivetSeat SeatRivet(int ReadyMs, const RivetSet* S)
{
	if (!S || S->AtMs < ReadyMs) return RivetSeat::Spoiled;
	if (S->AtMs > ReadyMs + RivetWindowMs || S->Strikes < 2) return RivetSeat::Loose;
	return S->Strikes >= RivetTightStrikes ? RivetSeat::Tight : RivetSeat::Snug;
}

inline const char* RivetLineLine(int Good, int Holes, int Spoiled)
{
	if (Good == Holes) return "Every hole filled hot. She'll hold the void.";
	if (Spoiled * 4 >= Holes) return "You're hitting them before they glow. Wait for the colour.";
	if (Good * 4 >= Holes * 3) return "A few loose heads. Drill them out or the seams pay for it.";
	return "Hull wants tempered rivets, not soft iron.";
}

struct RivetResult
{
	ArkClass C;
	std::vector<RivetSeat> Seats;
	std::vector<int> RivetsPerSeam;
	int Tight, Snug, Loose, Spoiled;
	std::string Line;
};

// Judge the line. Fewer sets than holes spoils the rest.
inline RivetResult JudgeRivets(const RivetTray& T, const std::vector<RivetSet>& Sets)
{
	RivetResult R{ T.C, {}, {}, 0, 0, 0, 0, {} };
	int N[RivetSeatCount] = {};
	R.Seats.reserve(T.Holes());
	for (int i = 0; i < T.Holes(); ++i)
	{
		const RivetSeat S = SeatRivet(T.ReadyMs[i], i < static_cast<int>(Sets.size()) ? &Sets[i] : nullptr);
		R.Seats.push_back(S);
		++N[static_cast<int>(S)];
	}
	const int Plates = ArkInfo(T.C).Plates;
	for (int Seam = 0; Seam < Plates; ++Seam)
	{
		int Good = 0;
		for (int k = 0; k < ArkRivetsPerSeam; ++k)
		{
			const RivetSeat S = R.Seats[Seam * ArkRivetsPerSeam + k];
			Good += S == RivetSeat::Tight || S == RivetSeat::Snug ? 1 : 0;
		}
		R.RivetsPerSeam.push_back(Good);
	}
	R.Tight = N[0]; R.Snug = N[1]; R.Loose = N[2]; R.Spoiled = N[3];
	R.Line = RivetLineLine(R.Tight + R.Snug, T.Holes(), R.Spoiled);
	return R;
}

// The riveter's run: every rivet set the moment it's ready, three strikes each.
inline std::vector<RivetSet> RivetMaster(const RivetTray& T)
{
	std::vector<RivetSet> Out;
	Out.reserve(T.ReadyMs.size());
	for (int Ms : T.ReadyMs) Out.push_back({ Ms, RivetTightStrikes });
	return Out;
}

// RVL 1 single-line encoding, the same text as RivetLine.Result.encode().
inline std::string Encode(const RivetResult& R)
{
	std::string S = std::string("RVL 1 ") + ArkInfo(R.C).Name + " holes=" + std::to_string(R.Seats.size()) + " tight=" + std::to_string(R.Tight)
		+ " snug=" + std::to_string(R.Snug) + " loose=" + std::to_string(R.Loose) + " spoiled=" + std::to_string(R.Spoiled) + " seams=";
	for (size_t i = 0; i < R.RivetsPerSeam.size(); ++i) S += (i ? "," : "") + std::to_string(R.RivetsPerSeam[i]);
	S += " seats=";
	for (RivetSeat Q : R.Seats) S += RivetSeatLetter(Q);
	return S + " | " + R.Line;
}

}} // namespace daedalus::forge
