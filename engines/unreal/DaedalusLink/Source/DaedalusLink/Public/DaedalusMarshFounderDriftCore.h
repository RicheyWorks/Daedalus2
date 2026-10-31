// SPDX-License-Identifier: MIT
// FounderDrift "Studbook" (G163, C++ port G614), plain C++17, header-only, standard library only, no Unreal types.
// Port of daedalus-core/src/main/java/com/daedalus/world/battlefield/FounderDrift.java, which stays the rules
// authority. Wright-Fisher drift with separate sexes in the sky-crane aviary: each chick draws a father and a mother
// from the generation before and one allele from each at every locus; migrants are swapped in with fresh alleles.
// Golden vectors: engines/unreal/core-test/marsh_founder_drift_parity.txt, written by MarshCoresParityTest.java and
// replayed by marsh_founder_drift_core_test.cpp.
//
// Seeding: FounderDrift hashes (seed, generation, chick, locus, salt) through the SplitMix64 finalizer with its own
// key layout, so Roll() below mirrors the Java core line for line (Java long arithmetic wraps like uint64_t here). It
// is not a new generator, and every allele draw is integer, so allele counts replay exactly. Gene diversity sums
// p^2 over a Java HashMap in hash order; here the counts are summed in sorted-allele order, so diversity can differ
// from Java in the last ulp (the test compares it to 1e-12). AlleeRelease is not ported, so Report.marsh(...) is
// left to the Java side; Survival(base) is ported (std::exp for Math.exp).
#pragma once
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <vector>

namespace daedalus { namespace marsh {

struct FounderDriftSettings
{
	int Founders = 20;
	int Capacity = 20;
	int Generations = 20;
	int Loci = 40;
	int MigrantPool = 40;
	double Lethal = 0.2;

	bool Valid() const
	{
		return Founders >= 2 && Capacity >= 2 && Generations >= 1 && Loci >= 1 && MigrantPool >= 0 && Lethal >= 0
			&& !std::isinf(Lethal);
	}
};

enum class DriftOutcome : int { Diverse = 0, Thinning, Inbred };
inline const char* DriftOutcomeName(DriftOutcome O)
{
	return O == DriftOutcome::Diverse ? "DIVERSE" : O == DriftOutcome::Thinning ? "THINNING" : "INBRED";
}

struct DriftGeneration { int Index = 0, Males = 0, Females = 0, Migrants = 0; double Diversity = 0; int Alleles = 0; };

struct DriftReport
{
	DriftOutcome Outcome = DriftOutcome::Inbred;
	double FounderDiversity = 0, Retained = 0, Expected = 0, Lethal = 0;
	std::vector<DriftGeneration> Generations;
	bool Ok = false;
	/** Inbreeding F = 1 - retained (never below 0). */
	double Inbreeding() const { return std::max(0.0, 1 - Retained); }
	/** Marsh survival base * exp(-lethal * F). */
	double Survival(double Base) const { return Base * std::exp(-Lethal * Inbreeding()); }
};

class FounderDrift
{
public:
	static constexpr double DiverseShare = 0.85;
	static constexpr double ThinningShare = 0.7;

	FounderDrift(const FounderDriftSettings& S, int64_t Seed) : Set(S), SeedBits(static_cast<uint64_t>(Seed))
	{
		const int Gens = std::max(0, Set.Generations);
		const int M = std::min(Set.Capacity, Set.Founders) / 2;
		Males.assign(static_cast<size_t>(Gens), M);
		Females.assign(static_cast<size_t>(Gens), std::min(Set.Capacity, Set.Founders) - M);
	}

	/** Cocks and hens raised in generation Gen (1-based). False if out of range or over capacity. */
	bool Breed(int Gen, int Cocks, int Hens)
	{
		if (Gen < 1 || Gen > Set.Generations || Cocks < 1 || Hens < 1 || Cocks + Hens > Set.Capacity) return false;
		Males[static_cast<size_t>(Gen - 1)] = Cocks;
		Females[static_cast<size_t>(Gen - 1)] = Hens;
		return true;
	}

	/** Migrants swapped in each generation. False if the other arks cannot lend that many over the run. */
	bool Migrants(int PerGeneration)
	{
		if (PerGeneration < 0 || static_cast<long long>(PerGeneration) * Set.Generations > Set.MigrantPool) return false;
		MigrantsPerGen = PerGeneration;
		return true;
	}

	/** Effective size 4mf/(m+f) (0 for no breeders; negative input returns -1, where Java throws). */
	static double EffectiveSize(int M, int F)
	{
		if (M < 0 || F < 0) return -1;
		return M + F == 0 ? 0 : 4.0 * M * F / (M + F);
	}

	/** Harmonic mean of effective sizes; 0 if any is not positive or the list is empty. */
	static double HarmonicMean(const std::vector<double>& Sizes)
	{
		if (Sizes.empty()) return 0;
		double Inv = 0;
		for (double N : Sizes)
		{
			if (!(N > 0)) return 0;
			Inv += 1 / N;
		}
		return static_cast<double>(Sizes.size()) / Inv;
	}

	/** Expected retained diversity with no migrants: product of (1 - 1/(2Ne)) over the planned generations. */
	double ExpectedRetained() const
	{
		int Pm = Set.Founders / 2, Pf = Set.Founders - Pm;
		double R = 1;
		for (int G = 0; G < Set.Generations; G++)
		{
			R *= 1 - 1 / (2 * EffectiveSize(Pm, Pf));
			Pm = Males[static_cast<size_t>(G)];
			Pf = Females[static_cast<size_t>(G)];
		}
		return R;
	}

	/** Runs the studbook. Ok=false when the settings are invalid. */
	DriftReport Run() const
	{
		DriftReport R;
		if (!Set.Valid()) return R;
		const int N = Set.Founders, Width = 2 * Set.Loci;
		int Pm = N / 2;
		std::vector<std::vector<int>> Genes(static_cast<size_t>(N), std::vector<int>(static_cast<size_t>(Width)));
		int Next = 0;
		for (auto& Bird : Genes) for (int& A : Bird) A = Next++;
		const double H0 = Diversity(Genes);
		for (int G = 0; G < Set.Generations; G++)
		{
			const int Pf = static_cast<int>(Genes.size()) - Pm;
			const int Size = Males[static_cast<size_t>(G)] + Females[static_cast<size_t>(G)];
			std::vector<std::vector<int>> Kids(static_cast<size_t>(Size), std::vector<int>(static_cast<size_t>(Width)));
			for (int C = 0; C < Size; C++)
			{
				const size_t Dad = static_cast<size_t>(static_cast<int>(Roll(G, C, 0, 1) * Pm));
				const size_t Mum = static_cast<size_t>(Pm + static_cast<int>(Roll(G, C, 0, 2) * Pf));
				std::vector<int>& Kid = Kids[static_cast<size_t>(C)];
				for (int L = 0; L < Set.Loci; L++)
				{
					Kid[static_cast<size_t>(2 * L)] = Genes[Dad][static_cast<size_t>(2 * L + (Roll(G, C, L, 3) < 0.5 ? 0 : 1))];
					Kid[static_cast<size_t>(2 * L + 1)] = Genes[Mum][static_cast<size_t>(2 * L + (Roll(G, C, L, 4) < 0.5 ? 0 : 1))];
				}
			}
			const int In = std::min(MigrantsPerGen, Size);
			for (int J = 0; J < In; J++)
			{
				const size_t C = static_cast<size_t>(static_cast<int>(Roll(G, J, 0, 5) * Size));
				for (int& A : Kids[C]) A = Next++;
			}
			Genes.swap(Kids);
			Pm = Males[static_cast<size_t>(G)];
			R.Generations.push_back(DriftGeneration{G + 1, Males[static_cast<size_t>(G)], Females[static_cast<size_t>(G)], In,
				Diversity(Genes), Distinct(Genes)});
		}
		R.FounderDiversity = H0;
		R.Retained = H0 <= 0 ? 0 : Diversity(Genes) / H0;
		R.Outcome = R.Retained >= DiverseShare ? DriftOutcome::Diverse : R.Retained >= ThinningShare ? DriftOutcome::Thinning : DriftOutcome::Inbred;
		R.Expected = ExpectedRetained();
		R.Lethal = Set.Lethal;
		R.Ok = true;
		return R;
	}

private:
	FounderDriftSettings Set;
	uint64_t SeedBits;
	std::vector<int> Males, Females;
	int MigrantsPerGen = 0;

	/** Mean over loci of 1 - sum p^2 (counts summed in sorted-allele order). */
	double Diversity(const std::vector<std::vector<int>>& Genes) const
	{
		double Total = 0;
		const int Copies = 2 * static_cast<int>(Genes.size());
		std::vector<int> Col;
		for (int L = 0; L < Set.Loci; L++)
		{
			Col.clear();
			for (const auto& Bird : Genes)
			{
				Col.push_back(Bird[static_cast<size_t>(2 * L)]);
				Col.push_back(Bird[static_cast<size_t>(2 * L + 1)]);
			}
			std::sort(Col.begin(), Col.end());
			double Sq = 0;
			for (size_t I = 0; I < Col.size();)
			{
				size_t J = I;
				while (J < Col.size() && Col[J] == Col[I]) J++;
				const double P = static_cast<double>(J - I) / Copies;
				Sq += P * P;
				I = J;
			}
			Total += 1 - Sq;
		}
		return Total / Set.Loci;
	}

	static int Distinct(const std::vector<std::vector<int>>& Genes)
	{
		std::vector<int> All;
		for (const auto& Bird : Genes) All.insert(All.end(), Bird.begin(), Bird.end());
		std::sort(All.begin(), All.end());
		return static_cast<int>(std::unique(All.begin(), All.end()) - All.begin());
	}

	double Roll(int Gen, int64_t Chick, int Locus, int Salt) const
	{
		uint64_t Z = SeedBits + 0x9E3779B97F4A7C15ULL * static_cast<uint64_t>(static_cast<int64_t>(Gen) + 1)
			+ 0xBF58476D1CE4E5B9ULL * static_cast<uint64_t>(Chick + 1)
			+ 0x94D049BB133111EBULL * static_cast<uint64_t>(static_cast<int64_t>(Salt) + 8 * (static_cast<int64_t>(Locus) + 1));
		Z = (Z ^ (Z >> 30)) * 0xBF58476D1CE4E5B9ULL;
		Z = (Z ^ (Z >> 27)) * 0x94D049BB133111EBULL;
		Z = Z ^ (Z >> 31);
		return static_cast<double>(Z >> 11) * 0x1.0p-53;
	}
};

}} // namespace daedalus::marsh
