// SPDX-License-Identifier: MIT
#pragma once
// Minecraft's "view distance" for Daedalus islands (ADR-062), in plain C++ with no Unreal types, tested in core-test.
//
// Minecraft holds only the chunks near a player in RAM, and loads and unloads them as the player moves. We do the
// same with whole islands: each island is a streaming sublevel with a known centre and radius.
// - Load an island when the player comes within LoadDistance of its edge.
// - Unload it only past UnloadDistance. The gap stops an island near the line flickering in and out.
// - Load nearest first, at most MaxLoadsPerTick at a time, so a teleport doesn't load the whole world in one frame.
// - Islands marked Always stay loaded.

#include <algorithm>
#include <cmath>
#include <string>
#include <vector>

namespace daedalus { namespace stream {

struct Island
{
	std::string Name;          // the streaming level's package name
	double X = 0, Y = 0, Z = 0;
	double Radius = 0;         // cm, from the centre to the farthest edge
	bool Loaded = false;
	bool Always = false;
};

struct Settings
{
	double LoadDistance = 150000;     // 1.5 km from the island's edge
	double UnloadDistance = 250000;   // 2.5 km: must be larger, for hysteresis
	int MaxLoadsPerTick = 1;
};

enum class Act { Load, Unload };

struct Step
{
	std::string Name;
	Act Do = Act::Load;
	double Distance = 0;   // from the player to the island's edge, cm
};

/** Distance from the player to the island's edge (0 inside it). */
inline double EdgeDistance(const Island& I, double PX, double PY, double PZ)
{
	const double DX = I.X - PX, DY = I.Y - PY, DZ = I.Z - PZ;
	const double D = std::sqrt(DX * DX + DY * DY + DZ * DZ) - I.Radius;
	return D > 0 ? D : 0;
}

/**
 * What to load and unload this tick. Unloads all happen at once, since they free RAM. Loads come nearest first,
 * capped at MaxLoadsPerTick, with ties broken by name. Settings with UnloadDistance <= LoadDistance are fixed up
 * (unload at LoadDistance * 1.5), so a bad config can't make islands thrash.
 */
inline std::vector<Step> Plan(const std::vector<Island>& Islands, double PX, double PY, double PZ, Settings S = Settings())
{
	if (!(S.LoadDistance >= 0)) S.LoadDistance = 0;
	if (!(S.UnloadDistance > S.LoadDistance)) S.UnloadDistance = S.LoadDistance * 1.5 + 1;
	if (S.MaxLoadsPerTick < 0) S.MaxLoadsPerTick = 0;
	std::vector<Step> Unloads, Loads;
	for (const Island& I : Islands)
	{
		const double D = EdgeDistance(I, PX, PY, PZ);
		if (!std::isfinite(D)) continue;
		if (I.Always)
		{
			if (!I.Loaded) Loads.push_back({I.Name, Act::Load, -1});   // always-loaded islands go first
			continue;
		}
		if (I.Loaded && D > S.UnloadDistance) Unloads.push_back({I.Name, Act::Unload, D});
		else if (!I.Loaded && D <= S.LoadDistance) Loads.push_back({I.Name, Act::Load, D});
	}
	auto ByDist = [](const Step& A, const Step& B) { return A.Distance != B.Distance ? A.Distance < B.Distance : A.Name < B.Name; };
	std::sort(Unloads.begin(), Unloads.end(), ByDist);
	std::sort(Loads.begin(), Loads.end(), ByDist);
	if (static_cast<int>(Loads.size()) > S.MaxLoadsPerTick) Loads.resize(static_cast<size_t>(S.MaxLoadsPerTick));
	Unloads.insert(Unloads.end(), Loads.begin(), Loads.end());
	return Unloads;
}

/** The islands an editor turn should keep loaded: the one being worked on and the always-loaded ones. */
inline std::vector<std::string> FocusSet(const std::vector<Island>& Islands, const std::string& Mine)
{
	std::vector<std::string> Keep;
	for (const Island& I : Islands)
		if (I.Always || I.Name == Mine) Keep.push_back(I.Name);
	std::sort(Keep.begin(), Keep.end());
	return Keep;
}

}}  // namespace daedalus::stream
