// SPDX-License-Identifier: MIT
// G143: plain C++17 port of G132 Meteor Scar Dig (daedalus-core world/forge/ScarDig.java), header-only and Unreal-ready.
// A seeded 8x8 scar with visible veins, rock hardness, caldera thirst, vent scalds, canteens, Scar Prospector ore luck
// and Drydock Shift double strikes; fainting drops half the haul. Encode() gives the same SCR 1 line as
// ScarDig.Result.encode(); ScarDigParityTest.java checks that line for line.
#pragma once

#include "DaedalusTemperForgeCore.h"
#include <cstdint>
#include <string>
#include <vector>

namespace daedalus { namespace forge {

constexpr int ScarSize = 8;
constexpr int ScarCells = ScarSize * ScarSize;
constexpr int ScarStartWater = 60;
constexpr int ScarThirstPerSwing = 2;
constexpr int ScarVentScald = 10;
constexpr int ScarCanteen = 25;
constexpr int ScarMaxCanteens = 3;
constexpr int ScarProspectorLuckPct = 10;
constexpr int ScarOrePerIngot = 2;

enum class ScarCell : int { Rock = 0, Slag, Emberite, Starmetal, Vent };
inline const char* ScarCellName(ScarCell C)
{
	static const char* N[] = { "ROCK", "SLAG", "EMBERITE", "STARMETAL", "VENT" };
	return N[static_cast<int>(C)];
}
inline int ScarHardness(ScarCell C) { static const int H[] = { 2, 1, 3, 4, 1 }; return H[static_cast<int>(C)]; }

struct ScarPlan
{
	std::vector<ScarCell> Cells;
	ScarCell At(int X, int Y) const { return Cells[Y * ScarSize + X]; }
};

// Same draw as ScarDig.plan: SplittableRandom(seed ^ 0x5CA2), one nextInt(100) per cell.
inline ScarPlan MakeScarPlan(int64_t Seed)
{
	SplitRng Rng(Seed ^ 0x5CA2LL);
	ScarPlan P;
	P.Cells.reserve(ScarCells);
	for (int i = 0; i < ScarCells; ++i)
	{
		const int R = Rng.NextInt(100);
		P.Cells.push_back(R < 6 ? ScarCell::Starmetal : R < 14 ? ScarCell::Emberite : R < 30 ? ScarCell::Slag : R < 36 ? ScarCell::Vent : ScarCell::Rock);
	}
	return P;
}

struct ScarKit
{
	bool Prospector, DrydockShift;
	int Canteens;
	bool Valid() const { return Canteens >= 0 && Canteens <= ScarMaxCanteens; }
	int Strike() const { return DrydockShift ? 2 : 1; }
};

struct ScarAction
{
	bool IsDrink; int X, Y;
	static ScarAction Swing(int X, int Y) { return { false, X, Y }; }
	static ScarAction Drink() { return { true, -1, -1 }; }
};

struct ScarResult { int Starmetal, Emberite, Slag, Broken, Swings, Wasted, Water; bool Fainted; int Ingots; std::string Line; };

inline int ScarLuck(int Ore) { return (Ore * (100 + ScarProspectorLuckPct) + 99) / 100; }

inline const char* ScarLine(bool Fainted, int Ingots, int Ore)
{
	if (Fainted) return "The scar took your water before your ore. Canteen first, pick second.";
	if (Ingots >= 3) return "Starmetal enough for a plate. Weighed, logged, off to the drydock.";
	if (Ore > 0) return "Some shine in the sack. Swing where the veins glow.";
	return "Rock and slag. The veins glow; the rock doesn't.";
}

// Play Actions on the scar with Kit; false (Out untouched) for a bad plan or kit, where Java throws.
inline bool RunScarDig(const ScarPlan& P, const ScarKit& Kit, const std::vector<ScarAction>& Actions, ScarResult& Out)
{
	if (static_cast<int>(P.Cells.size()) != ScarCells || !Kit.Valid()) return false;
	int Hits[ScarCells];
	for (int i = 0; i < ScarCells; ++i) Hits[i] = ScarHardness(P.Cells[i]);
	int Water = ScarStartWater, Canteens = Kit.Canteens, Star = 0, Ember = 0, Slag = 0, Broken = 0, Swings = 0, Wasted = 0;
	bool Fainted = false;
	for (const ScarAction& A : Actions)
	{
		if (A.IsDrink)
		{
			if (Canteens > 0) { --Canteens; Water = Water + ScarCanteen < ScarStartWater ? Water + ScarCanteen : ScarStartWater; }
			else ++Wasted;
			continue;
		}
		++Swings;
		Water -= ScarThirstPerSwing;
		const bool Inside = A.X >= 0 && A.X < ScarSize && A.Y >= 0 && A.Y < ScarSize;
		const int I = A.Y * ScarSize + A.X;
		if (!Inside || Hits[I] == 0) ++Wasted;
		else
		{
			Hits[I] = Hits[I] - Kit.Strike() > 0 ? Hits[I] - Kit.Strike() : 0;
			if (Hits[I] == 0)
			{
				++Broken;
				const ScarCell C = P.Cells[I];
				Star += C == ScarCell::Starmetal ? 1 : 0;
				Ember += C == ScarCell::Emberite ? 1 : 0;
				Slag += C == ScarCell::Slag ? 1 : 0;
				Water -= C == ScarCell::Vent ? ScarVentScald : 0;
			}
		}
		if (Water <= 0) { Water = 0; Fainted = true; break; }
	}
	if (Kit.Prospector) { Star = ScarLuck(Star); Ember = ScarLuck(Ember); }
	if (Fainted) { Star /= 2; Ember /= 2; Slag /= 2; }
	const int Ingots = Star / ScarOrePerIngot;
	Out = { Star, Ember, Slag, Broken, Swings, Wasted, Water, Fainted, Ingots, ScarLine(Fainted, Ingots, Star + Ember) };
	return true;
}

// The scar miner's dig: starmetal veins first, then emberite, row by row; never a vent; drink before running dry.
inline std::vector<ScarAction> ScarProspector(const ScarPlan& P, const ScarKit& Kit)
{
	std::vector<ScarAction> Out;
	int Water = ScarStartWater, Canteens = Kit.Canteens;
	const ScarCell Wants[2] = { ScarCell::Starmetal, ScarCell::Emberite };
	for (ScarCell Want : Wants)
		for (int i = 0; i < ScarCells; ++i)
		{
			if (P.Cells[i] != Want) continue;
			const int Need = (ScarHardness(Want) + Kit.Strike() - 1) / Kit.Strike();
			for (int s = 0; s < Need; ++s)
			{
				if (Water - ScarThirstPerSwing <= 0)
				{
					if (Canteens == 0) return Out;
					--Canteens;
					Water = Water + ScarCanteen < ScarStartWater ? Water + ScarCanteen : ScarStartWater;
					Out.push_back(ScarAction::Drink());
				}
				Water -= ScarThirstPerSwing;
				Out.push_back(ScarAction::Swing(i % ScarSize, i / ScarSize));
			}
		}
	return Out;
}

// SCR 1 single-line encoding, the same text as ScarDig.Result.encode().
inline std::string Encode(const ScarResult& R)
{
	return "SCR 1 star=" + std::to_string(R.Starmetal) + " ember=" + std::to_string(R.Emberite) + " slag=" + std::to_string(R.Slag)
		+ " broken=" + std::to_string(R.Broken) + " swings=" + std::to_string(R.Swings) + " wasted=" + std::to_string(R.Wasted)
		+ " water=" + std::to_string(R.Water) + " fainted=" + (R.Fainted ? "1" : "0") + " ingots=" + std::to_string(R.Ingots) + " | " + R.Line;
}

}} // namespace daedalus::forge
