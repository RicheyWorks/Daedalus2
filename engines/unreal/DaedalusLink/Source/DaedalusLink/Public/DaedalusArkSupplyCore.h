// SPDX-License-Identifier: MIT
// G29 Ark Supply Run (2hot2trot), plain C++17 for the Unreal binding. A port of daedalus-core world/ark/supply
// (Cargo, CrewMember, Passenger, SupplyRequest, SupplyRun) plus ArkFleet.duration. Java's IllegalArgumentException
// constructors become Valid() checks; IllegalStateException paths return false. Byte parity with Java goes through
// engines/unreal/core-test/ark_supply_parity.txt (ArkSupplyParityTest).
#pragma once
#include "DaedalusTemperForgeCore.h" // daedalus::forge::SplitRng (java.util.SplittableRandom)
#include <cmath>
#include <cstdint>
#include <map>
#include <string>
#include <vector>

namespace daedalus { namespace supply {

enum class Cargo : int { WaterCask = 0, FodderBale, SeedCache, SalveJar, TimberBundle };
inline const char* CargoName(Cargo C) { static const char* const N[] = { "WATER_CASK", "FODDER_BALE", "SEED_CACHE", "SALVE_JAR", "TIMBER_BUNDLE" }; return N[static_cast<int>(C)]; }
inline int Kg(Cargo C) { static const int K[] = { 10, 5, 2, 1, 20 }; return K[static_cast<int>(C)]; }
inline int Volume(Cargo C) { static const int V[] = { 1, 2, 1, 1, 4 }; return V[static_cast<int>(C)]; }

constexpr int HoldKg = 1000, HoldVolume = 120;
constexpr int64_t WatchMs = 15000, HarbourMs = 4000;
constexpr double Speed = 12.0;

/** SupplyRun.KEY: [a-z0-9][a-z0-9_.:-]{0,95} */
inline bool Key(const std::string& V)
{
	if (V.empty() || V.size() > 96) return false;
	for (size_t I = 0; I < V.size(); ++I)
	{
		const char C = V[I];
		const bool AlNum = (C >= 'a' && C <= 'z') || (C >= '0' && C <= '9');
		if (!(AlNum || (I > 0 && (C == '_' || C == '.' || C == ':' || C == '-')))) return false;
	}
	return true;
}

struct Coord { int X, Y, Z; };
/** ArkFleet.duration: harbour time plus Math.round(cubes * 1000 / SPEED). */
inline int64_t Duration(Coord From, Coord To)
{
	const double Dx = static_cast<double>(To.X) - From.X, Dy = static_cast<double>(To.Y) - From.Y, Dz = static_cast<double>(To.Z) - From.Z;
	const double Cubes = std::sqrt(Dx * Dx + Dy * Dy + Dz * Dz);
	return HarbourMs + static_cast<int64_t>(std::floor(Cubes * 1000.0 / Speed + 0.5));
}

struct Crew { std::string InstanceId, Profile; int CarryKg, MaxTrips; bool Valid() const { return Key(InstanceId) && Key(Profile) && CarryKg >= 1 && CarryKg <= 500 && MaxTrips >= 1 && MaxTrips <= 100; } int CapacityKg() const { return CarryKg * MaxTrips; } };
struct Passenger { std::string InstanceId, Profile; int WaterPerWatch, FodderPerWatch; bool Valid() const { return Key(InstanceId) && Key(Profile) && WaterPerWatch >= 0 && FodderPerWatch >= 0 && WaterPerWatch <= 50 && FodderPerWatch <= 50; } };
struct Request { std::string RequestId; Cargo What; int Units; bool Valid() const { return Key(RequestId) && Units >= 1 && Units <= 200; } };

/** Long.toUnsignedString(v, 36) */
inline std::string Base36(uint64_t V)
{
	if (V == 0) return "0";
	std::string S;
	while (V) { const int D = static_cast<int>(V % 36); S.insert(S.begin(), static_cast<char>(D < 10 ? '0' + D : 'a' + D - 10)); V /= 36; }
	return S;
}

/** SupplyRequest.forIsland */
inline std::vector<Request> ForIsland(int64_t Seed)
{
	forge::SplitRng Rng(Seed);
	const int Count = 2 + Rng.NextInt(3);
	std::vector<Cargo> Pool = { Cargo::FodderBale, Cargo::SalveJar, Cargo::TimberBundle };
	std::vector<Request> Out;
	const std::string Prefix = "isle-" + Base36(static_cast<uint64_t>(Seed)) + "-";
	const int SeedUnits = 2 + Rng.NextInt(6);
	Out.push_back({ Prefix + "0", Cargo::SeedCache, SeedUnits });
	const int WaterUnits = 3 + Rng.NextInt(8);
	Out.push_back({ Prefix + "1", Cargo::WaterCask, WaterUnits });
	for (int I = 2; I < Count; ++I)
	{
		const int K = Rng.NextInt(static_cast<int32_t>(Pool.size()));
		const Cargo C = Pool[K]; Pool.erase(Pool.begin() + K);
		const int Units = 1 + Rng.NextInt(C == Cargo::TimberBundle ? 4 : 10);
		Out.push_back({ Prefix + std::to_string(I), C, Units });
	}
	return Out;
}

enum class LoadResult : int { Loaded = 0, OverWeight, OverVolume, CrewTired, Refused };
inline const char* LoadName(LoadResult R) { static const char* const N[] = { "LOADED", "OVER_WEIGHT", "OVER_VOLUME", "CREW_TIRED", "REFUSED" }; return N[static_cast<int>(R)]; }
enum class Status : int { Loading = 0, Sailing, Delivered };
inline const char* StatusName(Status S) { static const char* const N[] = { "LOADING", "SAILING", "DELIVERED" }; return N[static_cast<int>(S)]; }

struct Check { int WaterShort = 0, FodderShort = 0; std::vector<std::string> RequestsShort; bool Ready() const { return WaterShort == 0 && FodderShort == 0 && RequestsShort.empty(); } };
struct Delivery
{
	std::string ArkId; int Watches = 0, KgCarried = 0, RequestsMet = 0, RequestsTotal = 0, PassengersFed = 0, PassengersTotal = 0; int64_t ArrivedAtMs = 0;
	bool Complete() const { return RequestsMet == RequestsTotal && PassengersFed == PassengersTotal; }
};

struct Run
{
	std::string ArkId; int64_t DurationMs = 0; int Watches = 1;
	std::vector<Passenger> Passengers; std::vector<Crew> CrewList; std::vector<Request> Requests;
	std::map<int, int> Hold; int HeldKg = 0, HeldVolume = 0; Status State = Status::Loading; int64_t DepartAt = 0; bool HasDelivery = false; Delivery Done;

	/** False where the Java constructor throws. */
	bool Init(const std::string& Ark, Coord From, Coord To, std::vector<Passenger> P, std::vector<Crew> C, std::vector<Request> R)
	{
		if (!Key(Ark) || C.empty() || P.size() > 64 || C.size() > 16 || R.size() > 16) return false;
		for (const Passenger& X : P) if (!X.Valid()) return false;
		for (const Crew& X : C) if (!X.Valid()) return false;
		for (const Request& X : R) if (!X.Valid()) return false;
		ArkId = Ark; Passengers = std::move(P); CrewList = std::move(C); Requests = std::move(R);
		DurationMs = Duration(From, To);
		const int64_t W = (DurationMs + WatchMs - 1) / WatchMs;
		Watches = static_cast<int>(W < 1 ? 1 : W);
		return true;
	}
	int WaterNeeded() const { int S = 0; for (const Passenger& P : Passengers) S += P.WaterPerWatch * Watches; return S; }
	int FodderNeeded() const { int S = 0; for (const Passenger& P : Passengers) S += P.FodderPerWatch * Watches; return S; }
	int CrewCapacityKg() const { int S = 0; for (const Crew& C : CrewList) S += C.CapacityKg(); return S; }
	int Units(Cargo C) const { const auto It = Hold.find(static_cast<int>(C)); return It == Hold.end() ? 0 : It->second; }

	/** Refused where Java throws (sailed, or units outside 1..1000). */
	LoadResult Load(Cargo C, int N)
	{
		if (State != Status::Loading || N < 1 || N > 1000) return LoadResult::Refused;
		const int AddKg = Kg(C) * N, AddVol = Volume(C) * N;
		if (HeldKg + AddKg > HoldKg) return LoadResult::OverWeight;
		if (HeldVolume + AddVol > HoldVolume) return LoadResult::OverVolume;
		if (HeldKg + AddKg > CrewCapacityKg()) return LoadResult::CrewTired;
		Hold[static_cast<int>(C)] += N; HeldKg += AddKg; HeldVolume += AddVol;
		return LoadResult::Loaded;
	}
	static int Take(std::map<int, int>& M, Cargo C, int N)
	{
		const int Have = M.count(static_cast<int>(C)) ? M[static_cast<int>(C)] : 0;
		const int Used = Have < N ? Have : N;
		M[static_cast<int>(C)] = Have - Used;
		return N - Used;
	}
	Check CheckHold() const
	{
		std::map<int, int> Left = Hold; Check Out;
		Out.WaterShort = Take(Left, Cargo::WaterCask, WaterNeeded());
		Out.FodderShort = Take(Left, Cargo::FodderBale, FodderNeeded());
		for (const Request& R : Requests) if (Take(Left, R.What, R.Units) > 0) Out.RequestsShort.push_back(R.RequestId);
		return Out;
	}
	bool Depart(int64_t NowMs) { if (State != Status::Loading) return false; State = Status::Sailing; DepartAt = NowMs; return true; }
	bool Arrived(int64_t NowMs) const { return State != Status::Loading && NowMs >= DepartAt + DurationMs; }
	/** Java deliver(): empty Optional = false. */
	bool Deliver(int64_t NowMs, Delivery& Out)
	{
		if (HasDelivery) { Out = Done; return true; }
		if (!Arrived(NowMs)) return false;
		std::map<int, int> Left = Hold;
		auto Get = [&Left](Cargo C) { const auto It = Left.find(static_cast<int>(C)); return It == Left.end() ? 0 : It->second; };
		int Fed = 0;
		for (const Passenger& P : Passengers)
		{
			const int W = P.WaterPerWatch * Watches, F = P.FodderPerWatch * Watches;
			if (Get(Cargo::WaterCask) >= W && Get(Cargo::FodderBale) >= F) { Take(Left, Cargo::WaterCask, W); Take(Left, Cargo::FodderBale, F); ++Fed; }
		}
		int Met = 0;
		for (const Request& R : Requests) if (Get(R.What) >= R.Units) { Take(Left, R.What, R.Units); ++Met; }
		State = Status::Delivered;
		Done = { ArkId, Watches, HeldKg, Met, static_cast<int>(Requests.size()), Fed, static_cast<int>(Passengers.size()), DepartAt + DurationMs };
		HasDelivery = true; Out = Done;
		return true;
	}
};

}} // namespace daedalus::supply