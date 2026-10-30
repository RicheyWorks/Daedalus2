// SPDX-License-Identifier: MIT
// G546 Census Riddles core, header-only C++17 port of the grading in tools/streaming/census_riddles.py
// (G577 batch 5). Takes the quiz as the Python tool drew and answered it from the census (riddle
// ids, kinds, questions and answers; the seeded draw and the G206 answers stay in Python and are
// carried in the golden file) and ports the count check, the answer normalisation (strip, lower,
// commas and underscores dropped, Python int() for numbers of any length) and the grade and
// verdict. Engine-free: no Unreal includes, no exceptions, no RTTI. Text is ASCII: Python's
// Unicode strip(), lower() and int() (other scripts' digits) can differ from this port outside ASCII.
#pragma once

#include <cstdint>
#include <string>
#include <utility>
#include <vector>

namespace DaedalusDiskSaver {
namespace CensusRiddles {

constexpr int MaxCount = 20;  // same cap as Python's MAX_COUNT
constexpr std::size_t MaxText = 1 << 16;
constexpr std::size_t MaxAnswers = 4096;
enum class Error { None, Count, BadQuiz, TooLong };
enum class Verdict { Shipshape, Adrift, Aground };

inline const char* ErrorName(Error E) {
    switch (E) {
        case Error::None: return "none";
        case Error::Count: return "count";
        case Error::BadQuiz: return "quiz";
        case Error::TooLong: return "toolong";
    }
    return "?";
}
inline const char* VerdictName(Verdict V) {
    switch (V) {
        case Verdict::Shipshape: return "shipshape";
        case Verdict::Adrift: return "adrift";
        case Verdict::Aground: return "aground";
    }
    return "?";
}

inline bool ValidCount(long long N) { return N >= 1 && N <= MaxCount; }

struct Riddle {
    std::string Id, Kind, Question, Answer;
};

inline bool KnownKind(const std::string& K) {
    static const char* Kinds[9] = {"islands_total", "cargo_total", "empty_islands", "widest_world", "heaviest_island",
                                   "world_ram", "world_disk", "islands_fit", "max_resident"};
    for (const char* X : Kinds)
        if (K == X) return true;
    return false;
}

// draw() numbers its riddles r1..rN, N = 1..MaxCount.
inline bool ValidQuiz(const std::vector<Riddle>& Q) {
    if (!ValidCount(static_cast<long long>(Q.size()))) return false;
    for (std::size_t I = 0; I < Q.size(); ++I)
        if (Q[I].Id != "r" + std::to_string(I + 1) || !KnownKind(Q[I].Kind) || Q[I].Question.empty() ||
            Q[I].Question.size() > MaxText || Q[I].Answer.size() > MaxText)
            return false;
    return true;
}

inline bool IsSpace(char C) { return C == ' ' || (C >= '\t' && C <= '\r') || (C >= '\x1c' && C <= '\x1f'); }
inline std::string Strip(const std::string& S) {
    std::size_t A = 0, B = S.size();
    while (A < B && IsSpace(S[A])) ++A;
    while (B > A && IsSpace(S[B - 1])) --B;
    return S.substr(A, B - A);
}

// _norm(): s = str(v).strip().lower(); str(int(s without , and _)) when that parses, else s.
inline std::string Norm(const std::string& V) {
    std::string S = Strip(V);
    for (char& C : S)
        if (C >= 'A' && C <= 'Z') C = static_cast<char>(C - 'A' + 'a');
    std::string T;
    for (char C : S)
        if (C != ',' && C != '_') T += C;
    T = Strip(T);  // int() allows surrounding whitespace
    std::size_t K = 0;
    bool Neg = false;
    if (K < T.size() && (T[K] == '+' || T[K] == '-')) Neg = T[K++] == '-';
    if (K == T.size()) return S;
    for (std::size_t I = K; I < T.size(); ++I)
        if (T[I] < '0' || T[I] > '9') return S;
    while (K + 1 < T.size() && T[K] == '0') ++K;
    const std::string Digits = T.substr(K);
    return (Neg && Digits != "0" ? "-" : "") + Digits;
}

struct Grade {
    Error Err = Error::None;
    int Score = 0, OutOf = 0;
    std::vector<bool> Correct;
    Verdict V = Verdict::Aground;
};

// grade(): Answers is the JSON object in order (a repeated id keeps its last value, as json.load does).
inline Grade GradeQuiz(const std::vector<Riddle>& Q, const std::vector<std::pair<std::string, std::string>>& Answers) {
    Grade G;
    if (!ValidQuiz(Q)) {
        G.Err = Error::BadQuiz;
        return G;
    }
    if (Answers.size() > MaxAnswers) {
        G.Err = Error::TooLong;
        return G;
    }
    for (const auto& A : Answers)
        if (A.first.size() > MaxText || A.second.size() > MaxText) {
            G.Err = Error::TooLong;
            return G;
        }
    for (const Riddle& R : Q) {
        const std::string* Given = nullptr;
        for (const auto& A : Answers)
            if (A.first == R.Id) Given = &A.second;
        const bool Ok = Given && Norm(*Given) == Norm(R.Answer);
        G.Score += Ok;
        G.Correct.push_back(Ok);
    }
    G.OutOf = static_cast<int>(Q.size());
    G.V = G.Score == G.OutOf ? Verdict::Shipshape : 2 * G.Score >= G.OutOf ? Verdict::Adrift : Verdict::Aground;
    return G;
}

}  // namespace CensusRiddles
}  // namespace DaedalusDiskSaver
