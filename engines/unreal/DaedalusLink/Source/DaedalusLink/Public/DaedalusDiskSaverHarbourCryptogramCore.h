// SPDX-License-Identifier: MIT
// G552 Harbour Cryptogram core, header-only C++17 port of tools/streaming/harbour_cryptogram.py
// (G576 batch 4). Takes the puzzle the Python tool made (cipher text, plain text, cipher->plain key
// and the given letters; the seeded sentence pick and derangement stay in Python and are carried in
// the golden file) and ports the number words, text cleaning, the cipher check, the letter
// frequency and board, the partial-key reading and the per-letter grade and verdict. Engine-free:
// no Unreal includes, no exceptions, no RTTI. Text is treated as ASCII (Python's Unicode upper()
// and strip() agree with it there); inputs over MaxText bytes are refused.
#pragma once

#include <algorithm>
#include <array>
#include <cstdint>
#include <string>
#include <utility>
#include <vector>

namespace DaedalusDiskSaver {
namespace HarbourCryptogram {

constexpr std::size_t MaxText = 1 << 16;
constexpr std::size_t MaxPairs = 4096;
constexpr std::int64_t MaxNumber = 1000000000000000000LL;
enum class Error { None, BadPuzzle, Negative, Letters, TooLong };
enum class Verdict { Decoded, Partial, Garbled };

inline const char* ErrorName(Error E) {
    switch (E) {
        case Error::None: return "none";
        case Error::BadPuzzle: return "puzzle";
        case Error::Negative: return "negative";
        case Error::Letters: return "letters";
        case Error::TooLong: return "toolong";
    }
    return "?";
}
inline const char* VerdictName(Verdict V) {
    switch (V) {
        case Verdict::Decoded: return "decoded";
        case Verdict::Partial: return "partial";
        case Verdict::Garbled: return "garbled";
    }
    return "?";
}

inline bool IsAlpha(char C) { return C >= 'A' && C <= 'Z'; }
inline char Upper(char C) { return C >= 'a' && C <= 'z' ? static_cast<char>(C - 'a' + 'A') : C; }

// number_words().
inline Error NumberWords(std::int64_t N, std::string& Out) {
    static const char* Ones[20] = {"ZERO", "ONE", "TWO", "THREE", "FOUR", "FIVE", "SIX", "SEVEN", "EIGHT", "NINE", "TEN",
                                   "ELEVEN", "TWELVE", "THIRTEEN", "FOURTEEN", "FIFTEEN", "SIXTEEN", "SEVENTEEN",
                                   "EIGHTEEN", "NINETEEN"};
    static const char* Tens[10] = {"_", "_", "TWENTY", "THIRTY", "FORTY", "FIFTY", "SIXTY", "SEVENTY", "EIGHTY", "NINETY"};
    if (N < 0) return Error::Negative;
    if (N > MaxNumber) return Error::TooLong;
    if (N < 20) {
        Out = Ones[N];
    } else if (N < 100) {
        Out = std::string(Tens[N / 10]) + (N % 10 == 0 ? "" : std::string(" ") + Ones[N % 10]);
    } else if (N < 1000) {
        std::string Rest;
        if (N % 100) NumberWords(N % 100, Rest);
        Out = std::string(Ones[N / 100]) + " HUNDRED" + (Rest.empty() ? "" : " AND " + Rest);
    } else {
        const std::string D = std::to_string(N);
        Out.clear();
        for (char C : D) {
            if (!Out.empty()) Out += ' ';
            Out += Ones[C - '0'];
        }
    }
    return Error::None;
}

// clean(): upper-case, runs of anything but A-Z become one space, trimmed.
inline std::string Clean(const std::string& T) {
    std::string Out;
    bool Gap = false;
    for (char Raw : T) {
        const char C = Upper(Raw);
        if (IsAlpha(C)) {
            if (Gap && !Out.empty()) Out += ' ';
            Out += C;
            Gap = false;
        } else {
            Gap = true;
        }
    }
    return Out;
}

struct Puzzle {
    std::string Cipher, Plain;
    std::array<char, 26> Key{};    // cipher letter -> plain letter, 0 where unused
    std::array<char, 26> Given{};  // given away cipher letters, 0 elsewhere
};

// The puzzle must be what make() builds: clean plain text, cipher = encode(plain) under a
// deranged one-to-one key that covers exactly the plain letters, given letters drawn from it.
inline bool ValidPuzzle(const Puzzle& P) {
    if (P.Plain.empty() || P.Plain.size() > MaxText || P.Cipher.size() != P.Plain.size() || Clean(P.Plain) != P.Plain)
        return false;
    std::array<bool, 26> Used{}, Hit{};
    for (int C = 0; C < 26; ++C) {
        const char V = P.Key[C];
        if (!V) continue;
        if (!IsAlpha(V) || V == 'A' + C || Hit[V - 'A']) return false;
        Hit[V - 'A'] = true;
        if (P.Given[C] && P.Given[C] != V) return false;
    }
    for (int C = 0; C < 26; ++C)
        if (P.Given[C] && !P.Key[C]) return false;
    for (std::size_t I = 0; I < P.Plain.size(); ++I) {
        const char Pc = P.Plain[I], Cc = P.Cipher[I];
        if (!IsAlpha(Pc)) {
            if (Cc != Pc) return false;
            continue;
        }
        if (!IsAlpha(Cc) || P.Key[Cc - 'A'] != Pc) return false;
        Used[Cc - 'A'] = true;
    }
    for (int C = 0; C < 26; ++C)
        if (static_cast<bool>(P.Key[C]) != Used[C]) return false;
    return true;
}

// frequency: cipher letters by count, most first, ties alphabetical.
inline std::vector<std::pair<char, int>> Frequency(const std::string& Cipher) {
    std::array<int, 26> N{};
    for (char C : Cipher)
        if (IsAlpha(C)) ++N[C - 'A'];
    std::vector<std::pair<char, int>> Out;
    for (int C = 0; C < 26; ++C)
        if (N[C]) Out.push_back({static_cast<char>('A' + C), N[C]});
    std::stable_sort(Out.begin(), Out.end(), [](const auto& A, const auto& B) { return A.second > B.second; });
    return Out;
}

// render()'s board: given letters shown, other cipher letters as '_'.
inline std::string Board(const Puzzle& P) {
    std::string Out;
    for (char C : P.Cipher) Out += IsAlpha(C) ? (P.Given[C - 'A'] ? P.Given[C - 'A'] : '_') : C;
    return Out;
}

struct Grade {
    Error Err = Error::None;
    int Right = 0, Letters = 0;
    Verdict V = Verdict::Garbled;
};

inline Grade GradeGuess(const Puzzle& P, const std::string& Guess) {
    Grade R;
    if (Guess.size() > MaxText) {
        R.Err = Error::TooLong;
        return R;
    }
    const std::string G = Clean(Guess);
    for (std::size_t I = 0; I < P.Plain.size(); ++I) {
        if (!IsAlpha(P.Plain[I])) continue;
        ++R.Letters;
        if (I < G.size() && G[I] == P.Plain[I]) ++R.Right;
    }
    R.V = G == P.Plain ? Verdict::Decoded : 2 * R.Right >= R.Letters ? Verdict::Partial : Verdict::Garbled;
    return R;
}

// str.strip() whitespace in ASCII: space, \t \n \v \f \r and \x1c-\x1f.
inline bool IsSpace(char C) { return C == ' ' || (C >= '\t' && C <= '\r') || (C >= '\x1c' && C <= '\x1f'); }
inline std::string StripUpper(const std::string& S) {
    std::size_t A = 0, B = S.size();
    while (A < B && IsSpace(S[A])) ++A;
    while (B > A && IsSpace(S[B - 1])) --B;
    std::string Out;
    for (std::size_t I = A; I < B; ++I) Out += Upper(S[I]);
    return Out;
}

// apply_mapping(): Pairs is the JSON object in order (a later key that strips to the same letter
// replaces the earlier one, as in the dict comprehension); given letters win; unknown letters read '?'.
inline Error ApplyMapping(const Puzzle& P, const std::vector<std::pair<std::string, std::string>>& Pairs, std::string& Out) {
    if (Pairs.size() > MaxPairs) return Error::TooLong;
    std::vector<std::pair<std::string, std::string>> M;
    for (const auto& KV : Pairs) {
        if (KV.first.size() > MaxText || KV.second.size() > MaxText) return Error::TooLong;
        const std::string K = StripUpper(KV.first), V = StripUpper(KV.second);
        bool Done = false;
        for (auto& E : M)
            if (E.first == K) {
                E.second = V;
                Done = true;
            }
        if (!Done) M.push_back({K, V});
    }
    std::array<char, 26> Map{};
    for (const auto& E : M) {
        if (E.first.size() != 1 || !IsAlpha(E.first[0]) || E.second.size() != 1 || !IsAlpha(E.second[0])) return Error::Letters;
        Map[E.first[0] - 'A'] = E.second[0];
    }
    for (int C = 0; C < 26; ++C)
        if (P.Given[C]) Map[C] = P.Given[C];
    Out.clear();
    for (char C : P.Cipher) Out += IsAlpha(C) ? (Map[C - 'A'] ? Map[C - 'A'] : '?') : C;
    return Error::None;
}

}  // namespace HarbourCryptogram
}  // namespace DaedalusDiskSaver
