// SPDX-License-Identifier: MIT
// Stable-lane seeding (G567 port), plain C++17, header-only: java.util.SplittableRandom as used by the
// com.daedalus.world.stable cores (new SplittableRandom(seed), nextInt(bound), nextBoolean()), bit for bit.
// nextLong() too, for the ark treap priorities (G572).
#pragma once
#include <cstdint>

namespace daedalus { namespace stable {

class StableRng
{
public:
	explicit StableRng(int64_t Seed) : State(static_cast<uint64_t>(Seed)) {}

	int32_t NextInt() { return Mix32(Next()); }

	// Uniform in [0, Bound), Bound > 0, same rejection loop as Java.
	int32_t NextInt(int32_t Bound)
	{
		int32_t R = NextInt();
		const int32_t M = Bound - 1;
		if ((Bound & M) == 0) return R & M;
		for (uint32_t U = static_cast<uint32_t>(R) >> 1;; U = static_cast<uint32_t>(NextInt()) >> 1)
		{
			R = static_cast<int32_t>(U % static_cast<uint32_t>(Bound));
			if (static_cast<int32_t>(U + static_cast<uint32_t>(M) - static_cast<uint32_t>(R)) >= 0) return R;
		}
	}

	bool NextBoolean() { return NextInt() < 0; }

	int64_t NextLong() { return static_cast<int64_t>(Mix64(Next())); }

private:
	static constexpr uint64_t Golden = 0x9e3779b97f4a7c15ULL;
	uint64_t State;

	uint64_t Next() { return State += Golden; }

	static int32_t Mix32(uint64_t Z)
	{
		Z = (Z ^ (Z >> 33)) * 0x62a9d9ed799705f5ULL;
		return static_cast<int32_t>(static_cast<uint32_t>(((Z ^ (Z >> 28)) * 0xcb24d0a5c88c35b3ULL) >> 32));
	}

	static uint64_t Mix64(uint64_t Z)
	{
		Z = (Z ^ (Z >> 30)) * 0xbf58476d1ce4e5b9ULL;
		Z = (Z ^ (Z >> 27)) * 0x94d049bb133111ebULL;
		return Z ^ (Z >> 31);
	}
};

} } // namespace daedalus::stable
