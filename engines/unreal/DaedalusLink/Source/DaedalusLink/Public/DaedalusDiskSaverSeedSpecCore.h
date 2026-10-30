// SPDX-License-Identifier: MIT
// G581 DiskSaver seed and draw spec, reference port: CPython's random.Random as the DiskSaver tools
// use it (docs/islands/DISKSAVER-SEED-SPEC.md). An integer seed (abs value, 32-bit limbs least
// significant first) feeds MT19937 init_by_array. The draws are getrandbits(32), random() as its
// 53-bit integer, getrandbits(k <= 64), _randbelow (bit-length rejection), randrange, randint,
// choice, shuffle (Fisher-Yates from the top) and sample (CPython's pool/set branches).
// This is a spec reference, not a game core. The ports of the shared DaedalusPyRandomCore.h (#1018)
// differ in their seeding; see the spec. Header-only C++17; no Unreal includes, no exceptions, no RTTI.
#pragma once
#include <cstddef>
#include <cstdint>
#include <vector>

namespace DaedalusDiskSaver {
namespace SeedSpec {

constexpr std::size_t MaxSeedWords = 1u << 16;   // 2 Mbit seeds
constexpr std::uint64_t MaxPopulation = 1u << 20;  // shuffle / sample / choice sizes
constexpr std::int64_t MaxMagnitude = std::int64_t(1) << 61;  // |range/int bounds|, so widths and step sums fit in 64 bits

class Mt19937 {
public:
    static constexpr int N = 624, M = 397;

    // random.Random(n) for n = sum(Words[i] << 32i): CPython's init_by_array. Empty means 0.
    bool Seed(const std::vector<std::uint32_t>& WordsIn) {
        if (WordsIn.size() > MaxSeedWords) return false;
        std::vector<std::uint32_t> Key = WordsIn;
        while (Key.size() > 1 && Key.back() == 0) Key.pop_back();
        if (Key.empty()) Key.push_back(0);
        InitGenrand(19650218u);
        int I = 1;
        std::size_t J = 0;
        for (std::size_t K = Key.size() > std::size_t(N) ? Key.size() : std::size_t(N); K; --K) {
            Mt[I] = (Mt[I] ^ ((Mt[I - 1] ^ (Mt[I - 1] >> 30)) * 1664525u)) + Key[J] + static_cast<std::uint32_t>(J);
            ++I;
            ++J;
            if (I >= N) {
                Mt[0] = Mt[N - 1];
                I = 1;
            }
            if (J >= Key.size()) J = 0;
        }
        for (int K = N - 1; K; --K) {
            Mt[I] = (Mt[I] ^ ((Mt[I - 1] ^ (Mt[I - 1] >> 30)) * 1566083941u)) - static_cast<std::uint32_t>(I);
            ++I;
            if (I >= N) {
                Mt[0] = Mt[N - 1];
                I = 1;
            }
        }
        Mt[0] = 0x80000000u;
        Words = 0;
        return true;
    }

    std::uint32_t U32() {
        if (Index >= N) {
            for (int K = 0; K < N; ++K) {
                const std::uint32_t Y = (Mt[K] & 0x80000000u) | (Mt[(K + 1) % N] & 0x7fffffffu);
                Mt[K] = Mt[(K + M) % N] ^ (Y >> 1) ^ ((Y & 1u) ? 0x9908b0dfu : 0u);
            }
            Index = 0;
        }
        std::uint32_t Y = Mt[Index++];
        Y ^= Y >> 11;
        Y ^= (Y << 7) & 0x9d2c5680u;
        Y ^= (Y << 15) & 0xefc60000u;
        Y ^= Y >> 18;
        ++Words;
        return Y;
    }

    // random() == Random53() / 2^53.
    std::uint64_t Random53() {
        const std::uint64_t A = U32() >> 5, B = U32() >> 6;
        return A * 67108864u + B;
    }

    // getrandbits(K) for 0 <= K <= 64: words least significant first, the last one shifted down.
    std::uint64_t Bits(int K) {
        if (K <= 0) return 0;
        if (K <= 32) return U32() >> (32 - K);
        const std::uint64_t Lo = U32();
        const std::uint64_t Hi = U32() >> (64 - K);
        return Lo | (Hi << 32);
    }

    // _randbelow_with_getrandbits(N), N >= 1 (CPython's own loop never ends for 0; callers guard).
    std::uint64_t Below(std::uint64_t Limit) {
        int K = 0;
        for (std::uint64_t T = Limit; T; T >>= 1) ++K;
        std::uint64_t R = Bits(K);
        while (R >= Limit) R = Bits(K);
        return R;
    }

    // randrange(Start, Stop, Step); false where Python raises ValueError (nothing drawn).
    bool RandRange(std::int64_t Start, std::int64_t Stop, std::int64_t Step, std::int64_t& Out) {
        if (!InRange(Start) || !InRange(Stop) || !InRange(Step) || Step == 0) return false;
        const std::int64_t Width = Stop - Start;
        std::int64_t Count = 0;
        if (Step == 1) Count = Width;
        else if (Step > 0) Count = FloorDiv(Width + Step - 1, Step);
        else Count = FloorDiv(Width + Step + 1, Step);
        if (Count <= 0) return false;
        Out = Start + Step * static_cast<std::int64_t>(Below(static_cast<std::uint64_t>(Count)));
        return true;
    }
    bool RandInt(std::int64_t A, std::int64_t B, std::int64_t& Out) { return B < MaxMagnitude && RandRange(A, B + 1, 1, Out); }

    // choice(seq) index; false (IndexError) for an empty sequence.
    bool Choice(std::uint64_t Size, std::uint64_t& Out) {
        if (Size == 0 || Size > MaxPopulation) return false;
        Out = Below(Size);
        return true;
    }

    // shuffle(list(range(Size))).
    bool Shuffle(std::uint64_t Size, std::vector<std::uint64_t>& Out) {
        if (Size > MaxPopulation) return false;
        Out.resize(static_cast<std::size_t>(Size));
        for (std::size_t I = 0; I < Out.size(); ++I) Out[I] = I;
        for (std::size_t I = Out.size() > 0 ? Out.size() - 1 : 0; I > 0; --I) {
            const std::size_t J = static_cast<std::size_t>(Below(I + 1));
            const std::uint64_t T = Out[I];
            Out[I] = Out[J];
            Out[J] = T;
        }
        return true;
    }

    // 21 + 4^ceil(log4(3K)) for K > 5, else 21 (3K is never a power of 4, so the float log agrees).
    static std::uint64_t SetSize(std::uint64_t K) {
        std::uint64_t S = 21;
        if (K > 5) {
            std::uint64_t P = 1;
            while (P < 3 * K) P *= 4;
            S += P;
        }
        return S;
    }

    // sample(range(Size), K) indices; false (ValueError) unless 0 <= K <= Size.
    bool Sample(std::uint64_t Size, std::uint64_t K, std::vector<std::uint64_t>& Out) {
        if (K > Size || Size > MaxPopulation) return false;
        Out.assign(static_cast<std::size_t>(K), 0);
        if (Size <= SetSize(K)) {
            std::vector<std::uint64_t> Pool(static_cast<std::size_t>(Size));
            for (std::size_t I = 0; I < Pool.size(); ++I) Pool[I] = I;
            for (std::size_t I = 0; I < Out.size(); ++I) {
                const std::size_t J = static_cast<std::size_t>(Below(Size - I));
                Out[I] = Pool[J];
                Pool[J] = Pool[static_cast<std::size_t>(Size - I - 1)];
            }
        } else {
            std::vector<bool> Seen(static_cast<std::size_t>(Size), false);
            for (std::size_t I = 0; I < Out.size(); ++I) {
                std::size_t J = static_cast<std::size_t>(Below(Size));
                while (Seen[J]) J = static_cast<std::size_t>(Below(Size));
                Seen[J] = true;
                Out[I] = J;
            }
        }
        return true;
    }

    std::uint64_t WordsDrawn() const { return Words; }

private:
    std::uint32_t Mt[N] = {};
    int Index = N;
    std::uint64_t Words = 0;

    void InitGenrand(std::uint32_t S) {
        Mt[0] = S;
        for (int I = 1; I < N; ++I) Mt[I] = 1812433253u * (Mt[I - 1] ^ (Mt[I - 1] >> 30)) + static_cast<std::uint32_t>(I);
        Index = N;
    }
    static bool InRange(std::int64_t V) { return V >= -MaxMagnitude && V <= MaxMagnitude; }
    static std::int64_t FloorDiv(std::int64_t A, std::int64_t B) {
        std::int64_t Q = A / B;
        if ((A % B != 0) && ((A < 0) != (B < 0))) --Q;
        return Q;
    }
};

}  // namespace SeedSpec
}  // namespace DaedalusDiskSaver
