// SPDX-License-Identifier: MIT
// CPython-compatible random.Random(str) for native parity with Python minigame rules, plain C++17.
// Mirrors CPython's random.seed(str, version=2): key = utf-8 bytes + sha512(bytes), split into little-endian
// 32-bit words (trailing zero words dropped), fed to MT19937 init_by_array; getrandbits(32) is the tempered
// output; _randbelow_with_getrandbits is the rejection loop; choice(seq) = seq[randbelow(len)].
// The same seed string therefore gives the same draws as tools/minigames/prism_shard.py and the web port in
// tools/minigames/web/shardring/index.html (PyRandom). Nothing here is cryptographic.
#pragma once
#include <array>
#include <cstdint>
#include <cstring>
#include <string>
#include <vector>

namespace daedalus { namespace pyrandom {

/** SHA-512 of `Data`, 64 bytes. Straight FIPS 180-4; used only for seeding. */
inline std::array<std::uint8_t, 64> Sha512(const std::uint8_t* Data, std::size_t Len)
{
	static const std::uint64_t K[80] = {
		0x428a2f98d728ae22ULL, 0x7137449123ef65cdULL, 0xb5c0fbcfec4d3b2fULL, 0xe9b5dba58189dbbcULL, 0x3956c25bf348b538ULL, 0x59f111f1b605d019ULL, 0x923f82a4af194f9bULL, 0xab1c5ed5da6d8118ULL,
		0xd807aa98a3030242ULL, 0x12835b0145706fbeULL, 0x243185be4ee4b28cULL, 0x550c7dc3d5ffb4e2ULL, 0x72be5d74f27b896fULL, 0x80deb1fe3b1696b1ULL, 0x9bdc06a725c71235ULL, 0xc19bf174cf692694ULL,
		0xe49b69c19ef14ad2ULL, 0xefbe4786384f25e3ULL, 0x0fc19dc68b8cd5b5ULL, 0x240ca1cc77ac9c65ULL, 0x2de92c6f592b0275ULL, 0x4a7484aa6ea6e483ULL, 0x5cb0a9dcbd41fbd4ULL, 0x76f988da831153b5ULL,
		0x983e5152ee66dfabULL, 0xa831c66d2db43210ULL, 0xb00327c898fb213fULL, 0xbf597fc7beef0ee4ULL, 0xc6e00bf33da88fc2ULL, 0xd5a79147930aa725ULL, 0x06ca6351e003826fULL, 0x142929670a0e6e70ULL,
		0x27b70a8546d22ffcULL, 0x2e1b21385c26c926ULL, 0x4d2c6dfc5ac42aedULL, 0x53380d139d95b3dfULL, 0x650a73548baf63deULL, 0x766a0abb3c77b2a8ULL, 0x81c2c92e47edaee6ULL, 0x92722c851482353bULL,
		0xa2bfe8a14cf10364ULL, 0xa81a664bbc423001ULL, 0xc24b8b70d0f89791ULL, 0xc76c51a30654be30ULL, 0xd192e819d6ef5218ULL, 0xd69906245565a910ULL, 0xf40e35855771202aULL, 0x106aa07032bbd1b8ULL,
		0x19a4c116b8d2d0c8ULL, 0x1e376c085141ab53ULL, 0x2748774cdf8eeb99ULL, 0x34b0bcb5e19b48a8ULL, 0x391c0cb3c5c95a63ULL, 0x4ed8aa4ae3418acbULL, 0x5b9cca4f7763e373ULL, 0x682e6ff3d6b2b8a3ULL,
		0x748f82ee5defb2fcULL, 0x78a5636f43172f60ULL, 0x84c87814a1f0ab72ULL, 0x8cc702081a6439ecULL, 0x90befffa23631e28ULL, 0xa4506cebde82bde9ULL, 0xbef9a3f7b2c67915ULL, 0xc67178f2e372532bULL,
		0xca273eceea26619cULL, 0xd186b8c721c0c207ULL, 0xeada7dd6cde0eb1eULL, 0xf57d4f7fee6ed178ULL, 0x06f067aa72176fbaULL, 0x0a637dc5a2c898a6ULL, 0x113f9804bef90daeULL, 0x1b710b35131c471bULL,
		0x28db77f523047d84ULL, 0x32caab7b40c72493ULL, 0x3c9ebe0a15c9bebcULL, 0x431d67c49c100d4cULL, 0x4cc5d4becb3e42b6ULL, 0x597f299cfc657e2aULL, 0x5fcb6fab3ad6faecULL, 0x6c44198c4a475817ULL };
	std::uint64_t H[8] = { 0x6a09e667f3bcc908ULL, 0xbb67ae8584caa73bULL, 0x3c6ef372fe94f82bULL, 0xa54ff53a5f1d36f1ULL,
	                       0x510e527fade682d1ULL, 0x9b05688c2b3e6c1fULL, 0x1f83d9abfb41bd6bULL, 0x5be0cd19137e2179ULL };
	const std::size_t Total = ((Len + 17 + 127) / 128) * 128;
	std::vector<std::uint8_t> M(Total, 0);
	if (Len) std::memcpy(M.data(), Data, Len);
	M[Len] = 0x80;
	const std::uint64_t Bits = static_cast<std::uint64_t>(Len) * 8;
	for (int I = 0; I < 8; ++I) M[Total - 1 - static_cast<std::size_t>(I)] = static_cast<std::uint8_t>((Bits >> (8 * I)) & 0xff);
	auto Rotr = [](std::uint64_t X, unsigned N) { return (X >> N) | (X << (64 - N)); };
	for (std::size_t Off = 0; Off < Total; Off += 128)
	{
		std::uint64_t W[80];
		for (int T = 0; T < 16; ++T)
		{
			std::uint64_t V = 0;
			for (int B = 0; B < 8; ++B) V = (V << 8) | M[Off + static_cast<std::size_t>(T) * 8 + static_cast<std::size_t>(B)];
			W[T] = V;
		}
		for (int T = 16; T < 80; ++T)
		{
			const std::uint64_t S0 = Rotr(W[T - 15], 1) ^ Rotr(W[T - 15], 8) ^ (W[T - 15] >> 7);
			const std::uint64_t S1 = Rotr(W[T - 2], 19) ^ Rotr(W[T - 2], 61) ^ (W[T - 2] >> 6);
			W[T] = W[T - 16] + S0 + W[T - 7] + S1;
		}
		std::uint64_t A = H[0], B = H[1], C = H[2], D = H[3], E = H[4], F = H[5], G = H[6], Hh = H[7];
		for (int T = 0; T < 80; ++T)
		{
			const std::uint64_t S1 = Rotr(E, 14) ^ Rotr(E, 18) ^ Rotr(E, 41), Ch = (E & F) ^ (~E & G);
			const std::uint64_t T1 = Hh + S1 + Ch + K[T] + W[T];
			const std::uint64_t S0 = Rotr(A, 28) ^ Rotr(A, 34) ^ Rotr(A, 39), Mj = (A & B) ^ (A & C) ^ (B & C);
			const std::uint64_t T2 = S0 + Mj;
			Hh = G; G = F; F = E; E = D + T1; D = C; C = B; B = A; A = T1 + T2;
		}
		H[0] += A; H[1] += B; H[2] += C; H[3] += D; H[4] += E; H[5] += F; H[6] += G; H[7] += Hh;
	}
	std::array<std::uint8_t, 64> Out{};
	for (int I = 0; I < 8; ++I) for (int B = 7; B >= 0; --B) Out[static_cast<std::size_t>(I * 8 + (7 - B))] = static_cast<std::uint8_t>((H[I] >> (8 * B)) & 0xff);
	return Out;
}

inline std::string HexLower(const std::uint8_t* Data, std::size_t Len)
{
	static const char* Digits = "0123456789abcdef";
	std::string S; S.reserve(Len * 2);
	for (std::size_t I = 0; I < Len; ++I) { S.push_back(Digits[Data[I] >> 4]); S.push_back(Digits[Data[I] & 15]); }
	return S;
}

/** CPython random.Random seeded from a str (version 2). */
class PyRandom
{
	std::uint32_t Mt[624]; int Index = 624; std::uint64_t Consumed = 0;

	void InitGenrand(std::uint32_t S)
	{
		Mt[0] = S;
		for (int I = 1; I < 624; ++I) Mt[I] = 1812433253u * (Mt[I - 1] ^ (Mt[I - 1] >> 30)) + static_cast<std::uint32_t>(I);
		Index = 624;
	}
	void InitByArray(const std::vector<std::uint32_t>& Key)
	{
		InitGenrand(19650218u);
		int I = 1; std::size_t J = 0;
		for (std::size_t Kk = (Key.size() > 624 ? Key.size() : 624); Kk; --Kk)
		{
			Mt[I] = (Mt[I] ^ ((Mt[I - 1] ^ (Mt[I - 1] >> 30)) * 1664525u)) + Key[J] + static_cast<std::uint32_t>(J);
			++I; ++J;
			if (I >= 624) { Mt[0] = Mt[623]; I = 1; }
			if (J >= Key.size()) J = 0;
		}
		for (int Kk = 623; Kk; --Kk)
		{
			Mt[I] = (Mt[I] ^ ((Mt[I - 1] ^ (Mt[I - 1] >> 30)) * 1566083941u)) - static_cast<std::uint32_t>(I);
			++I;
			if (I >= 624) { Mt[0] = Mt[623]; I = 1; }
		}
		Mt[0] = 0x80000000u;
	}
public:
	PyRandom() { Seed(""); }
	explicit PyRandom(const std::string& SeedString) { Seed(SeedString); }

	/** random.seed(str): key words from utf-8 bytes + sha512(bytes), little-endian, trailing zeros dropped. */
	void Seed(const std::string& SeedString)
	{
		std::vector<std::uint8_t> Bytes(SeedString.begin(), SeedString.end());
		const std::array<std::uint8_t, 64> Digest = Sha512(Bytes.data(), Bytes.size());
		Bytes.insert(Bytes.end(), Digest.begin(), Digest.end());
		// CPython: int.from_bytes(bytes, 'big') split into 32-bit limbs, least significant first.
		std::vector<std::uint32_t> Key;
		for (std::size_t End = Bytes.size(); End > 0; End = (End >= 4 ? End - 4 : 0))
		{
			std::uint32_t V = 0;
			for (std::size_t B = (End >= 4 ? End - 4 : 0); B < End; ++B) V = (V << 8) | Bytes[B];
			Key.push_back(V);
		}
		while (Key.size() > 1 && Key.back() == 0) Key.pop_back();
		if (Key.empty()) Key.push_back(0);
		InitByArray(Key);
		Consumed = 0;
	}

	/** getrandbits(32). */
	std::uint32_t U32()
	{
		if (Index >= 624)
		{
			for (int Kk = 0; Kk < 624; ++Kk)
			{
				const std::uint32_t Y = (Mt[Kk] & 0x80000000u) | (Mt[(Kk + 1) % 624] & 0x7fffffffu);
				Mt[Kk] = Mt[(Kk + 397) % 624] ^ (Y >> 1) ^ ((Y & 1u) ? 0x9908b0dfu : 0u);
			}
			Index = 0;
		}
		std::uint32_t Z = Mt[Index++];
		Z ^= Z >> 11; Z ^= (Z << 7) & 0x9d2c5680u; Z ^= (Z << 15) & 0xefc60000u; Z ^= Z >> 18;
		++Consumed;
		return Z;
	}

	/** _randbelow_with_getrandbits for 0 < N < 2^32. */
	std::uint32_t Below(std::uint32_t N)
	{
		if (N == 0) return 0;   // CPython raises on an empty choice; callers never pass 0
		// N == 1 still draws: getrandbits(1) loops until it returns 0, exactly as CPython does.
		int KBits = 0; for (std::uint32_t T = N; T; T >>= 1) ++KBits;
		std::uint32_t R = U32() >> (32 - KBits);
		while (R >= N) R = U32() >> (32 - KBits);
		return R;
	}

	/** choice(seq) index. */
	std::size_t ChoiceIndex(std::size_t Size) { return static_cast<std::size_t>(Below(static_cast<std::uint32_t>(Size))); }

	/** randrange(n) for 0 < n < 2^32. */
	std::uint32_t RandRange(std::uint32_t N) { return Below(N); }

	/** random(): 53-bit float in [0, 1), exactly CPython's genrand_res53. */
	double RandomDouble()
	{
		const std::uint32_t A = U32() >> 5, B = U32() >> 6;
		return (A * 67108864.0 + B) * (1.0 / 9007199254740992.0);
	}

	/** sample(population, k) as indices into the population, CPython's two-branch algorithm (setsize 21 + 4^ceil(log4(3k)) for k > 5). */
	std::vector<std::size_t> SampleIndices(std::size_t N, std::size_t K)
	{
		std::vector<std::size_t> Result(K, 0);
		if (K > N) return {};
		std::size_t SetSize = 21;
		if (K > 5)
		{
			// 4 ** ceil(log(k*3, 4)); integer form of the same power
			std::size_t Target = K * 3, Pow = 1; while (Pow < Target) Pow *= 4;
			SetSize += Pow;
		}
		if (N <= SetSize)
		{
			std::vector<std::size_t> Pool(N); for (std::size_t I = 0; I < N; ++I) Pool[I] = I;
			for (std::size_t I = 0; I < K; ++I)
			{
				const std::size_t J = static_cast<std::size_t>(Below(static_cast<std::uint32_t>(N - I)));
				Result[I] = Pool[J]; Pool[J] = Pool[N - I - 1];
			}
		}
		else
		{
			std::vector<bool> Selected(N, false);
			for (std::size_t I = 0; I < K; ++I)
			{
				std::size_t J = static_cast<std::size_t>(Below(static_cast<std::uint32_t>(N)));
				while (Selected[J]) J = static_cast<std::size_t>(Below(static_cast<std::uint32_t>(N)));
				Selected[J] = true; Result[I] = J;
			}
		}
		return Result;
	}

	/** 32-bit words drawn since Seed(); re-seeding and discarding this many reproduces the state exactly. */
	std::uint64_t Drawn() const { return Consumed; }
	void Discard(std::uint64_t Count) { while (Count--) U32(); }
};

} } // namespace daedalus::pyrandom
