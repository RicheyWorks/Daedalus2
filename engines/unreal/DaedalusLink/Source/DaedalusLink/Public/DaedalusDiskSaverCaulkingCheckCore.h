// SPDX-License-Identifier: MIT
// G544 Caulking Check (disk-saver), header-only C++17 port of the pure logic of
// tools/streaming/caulking_check.py: check_bytes() (BOM, strict UTF-8 with Python's error
// offset, CRLF/mixed endings, final newline, trailing spaces, tab indents) and the JSON /
// JSON Lines check, plus survey()'s sort, counts and sound/weeping/leaking verdict.
// The JSON check is a self-contained scanner that follows CPython 3.10's C json scanner
// (Modules/_json.c) step by step: the same value, string, escape, number and constant rules
// (NaN/Infinity accepted), duplicate keys reported when an object closes (as
// object_pairs_hook sees them), and the same error message, cut at its first ':' like the
// tool does. Known version limits: Python 3.10.7+ refuses integers over 4300 digits and
// 3.13 words trailing-comma errors differently; the golden file avoids both, and this port
// follows 3.10.0. Nesting deeper than MaxDepth is refused here (Python raises
// RecursionError, which the tool does not catch).
// Left in Python: walking folders (_files), reading files, the CLI. Paths use '/' only and
// extensions are lower-cased as ASCII. No Unreal includes, no exceptions, no RTTI.
#pragma once

#include "DaedalusDiskSaverPyJsonCore.h"

#include <algorithm>
#include <cstddef>
#include <cstdint>
#include <map>
#include <set>
#include <string>
#include <vector>

namespace DaedalusDiskSaver {
namespace CaulkingCheck {

constexpr std::size_t MaxFileBytes = 4 * 1024 * 1024;
constexpr std::size_t MaxFiles = 100000;
constexpr std::size_t MaxTotalBytes = 64 * 1024 * 1024;
constexpr int MaxDepth = 512;

// ERRORS then ADVISORIES, in Python's ORDER.
enum Kind { BadUtf8, BadJson, DuplicateKey, Bom, Crlf, NoFinalNewline, TrailingSpace, TabIndent, KindCount };

inline const char* KindName(int K) {
    static const char* const N[KindCount] = {"bad_utf8", "bad_json", "duplicate_key", "bom", "crlf", "no_final_newline", "trailing_space", "tab_indent"};
    return K >= 0 && K < KindCount ? N[K] : "?";
}

// ---- strict UTF-8 (Python's codec): returns false and the start of the first bad sequence
inline bool CheckUtf8(const std::string& S, std::size_t Begin, std::size_t& BadAt) {
    std::size_t I = Begin;
    auto At = [&](std::size_t K) { return static_cast<unsigned char>(S[K]); };
    auto In = [](unsigned char C, unsigned char Lo, unsigned char Hi) { return C >= Lo && C <= Hi; };
    while (I < S.size()) {
        const unsigned char C = At(I);
        int Len = 0;
        unsigned char Lo = 0x80, Hi = 0xBF;
        if (C < 0x80) Len = 1;
        else if (In(C, 0xC2, 0xDF)) Len = 2;
        else if (C == 0xE0) { Len = 3; Lo = 0xA0; }
        else if (In(C, 0xE1, 0xEC) || In(C, 0xEE, 0xEF)) Len = 3;
        else if (C == 0xED) { Len = 3; Hi = 0x9F; }
        else if (C == 0xF0) { Len = 4; Lo = 0x90; }
        else if (In(C, 0xF1, 0xF3)) Len = 4;
        else if (C == 0xF4) { Len = 4; Hi = 0x8F; }
        if (Len == 0) {
            BadAt = I - Begin;
            return false;
        }
        for (int K = 1; K < Len; ++K) {
            const std::size_t P = I + static_cast<std::size_t>(K);
            const bool Ok = P < S.size() && (K == 1 ? In(At(P), Lo, Hi) : In(At(P), 0x80, 0xBF));
            if (!Ok) {
                BadAt = I - Begin;
                return false;
            }
        }
        I += static_cast<std::size_t>(Len);
    }
    return true;
}

// Valid UTF-8 -> code points.
inline std::vector<std::uint32_t> Decode(const std::string& S, std::size_t Begin, std::size_t End) {
    std::vector<std::uint32_t> Out;
    std::string Part = S.substr(Begin, End - Begin);
    std::size_t I = 0;
    while (I < Part.size()) Out.push_back(PyJson::NextCodePoint(Part, I));
    return Out;
}

inline void Encode(std::uint32_t C, std::string& Out) {  // UTF-8, surrogates as three bytes (surrogatepass)
    if (C < 0x80) Out += static_cast<char>(C);
    else if (C < 0x800) { Out += static_cast<char>(0xC0 | (C >> 6)); Out += static_cast<char>(0x80 | (C & 0x3F)); }
    else if (C < 0x10000) {
        Out += static_cast<char>(0xE0 | (C >> 12));
        Out += static_cast<char>(0x80 | ((C >> 6) & 0x3F));
        Out += static_cast<char>(0x80 | (C & 0x3F));
    } else {
        Out += static_cast<char>(0xF0 | (C >> 18));
        Out += static_cast<char>(0x80 | ((C >> 12) & 0x3F));
        Out += static_cast<char>(0x80 | ((C >> 6) & 0x3F));
        Out += static_cast<char>(0x80 | (C & 0x3F));
    }
}

// Python's str.isspace() (what str.strip() removes).
inline bool PyIsSpace(std::uint32_t C) {
    return (C >= 9 && C <= 13) || (C >= 0x1C && C <= 0x20) || C == 0x85 || C == 0xA0 || C == 0x1680 || (C >= 0x2000 && C <= 0x200A) ||
           C == 0x2028 || C == 0x2029 || C == 0x202F || C == 0x205F || C == 0x3000;
}

// ---- the JSON check: CPython 3.10 json.loads(s, object_pairs_hook=_pairs)
enum class Problem { None, BadJson, DuplicateKey, Capacity };

struct JsonResult {
    Problem P = Problem::None;
    std::string Detail;  // the message before its first ':' or the duplicate key (UTF-8)
};

class Scanner {
public:
    explicit Scanner(const std::vector<std::uint32_t>& Text) : S(Text), N(Text.size()) {}

    JsonResult Loads() {
        if (N > 0 && S[0] == 0xFEFF) return Fail("Unexpected UTF-8 BOM (decode using utf-8-sig)");
        std::size_t Idx = SkipWs(0), Next = 0;
        if (!ScanOnce(Idx, Next)) return R;
        if (SkipWs(Next) != N) return Fail("Extra data");
        return R;
    }

private:
    const std::vector<std::uint32_t>& S;
    std::size_t N;
    int Depth = 0;
    JsonResult R;

    static bool Ws(std::uint32_t C) { return C == ' ' || C == '\t' || C == '\n' || C == '\r'; }
    static bool Digit(std::uint32_t C) { return C >= '0' && C <= '9'; }
    static int Hex(std::uint32_t C) {
        return C >= '0' && C <= '9' ? static_cast<int>(C - '0') : C >= 'a' && C <= 'f' ? static_cast<int>(C - 'a' + 10)
                                                                : C >= 'A' && C <= 'F' ? static_cast<int>(C - 'A' + 10) : -1;
    }
    std::size_t SkipWs(std::size_t I) const {
        while (I < N && Ws(S[I])) ++I;
        return I;
    }
    JsonResult Fail(const char* Msg) {
        R.P = Problem::BadJson;
        const std::string M = Msg;
        R.Detail = M.substr(0, M.find(':'));
        return R;
    }
    bool Stop() {  // StopIteration anywhere becomes "Expecting value"
        Fail("Expecting value");
        return false;
    }
    bool Err(const char* Msg) {
        Fail(Msg);
        return false;
    }
    bool Lit(std::size_t Idx, const char* Word) const {  // S[Idx..] starts with Word (ASCII)
        for (std::size_t K = 0; Word[K]; ++K)
            if (Idx + K >= N || S[Idx + K] != static_cast<unsigned char>(Word[K])) return false;
        return true;
    }
    bool Hex4(std::size_t At, std::uint32_t& V) const {
        V = 0;
        for (std::size_t K = 0; K < 4; ++K) {
            const int D = At + K < N ? Hex(S[At + K]) : -1;
            if (D < 0) return false;
            V = (V << 4) | static_cast<std::uint32_t>(D);
        }
        return true;
    }

    // scanstring_unicode(strict=True), Begin = just after the opening quote.
    bool ScanString(std::size_t Begin, std::size_t& NextOut, std::vector<std::uint32_t>* Key) {
        std::size_t End = Begin;
        while (true) {
            std::uint32_t C = 0;
            std::size_t Next = End;
            for (; Next < N; ++Next) {
                C = S[Next];
                if (C == '"' || C == '\\') break;
                if (C <= 0x1F) return Err("Invalid control character at");
            }
            if (!(C == '"' || C == '\\') || Next >= N) return Err("Unterminated string starting at");
            if (Key) Key->insert(Key->end(), S.begin() + static_cast<std::ptrdiff_t>(End), S.begin() + static_cast<std::ptrdiff_t>(Next));
            ++Next;
            if (C == '"') {
                End = Next;
                break;
            }
            if (Next == N) return Err("Unterminated string starting at");
            C = S[Next];
            if (C != 'u') {
                End = Next + 1;
                switch (C) {
                    case '"': case '\\': case '/': break;
                    case 'b': C = '\b'; break;
                    case 'f': C = '\f'; break;
                    case 'n': C = '\n'; break;
                    case 'r': C = '\r'; break;
                    case 't': C = '\t'; break;
                    default: return Err("Invalid \\escape");
                }
            } else {
                ++Next;
                End = Next + 4;
                if (End >= N) return Err("Invalid \\uXXXX escape");
                if (!Hex4(Next, C)) return Err("Invalid \\uXXXX escape");
                if (C >= 0xD800 && C <= 0xDBFF && End + 6 < N && S[End] == '\\' && S[End + 1] == 'u') {
                    std::uint32_t C2 = 0;
                    if (!Hex4(End + 2, C2)) return Err("Invalid \\uXXXX escape");
                    if (C2 >= 0xDC00 && C2 <= 0xDFFF) {
                        C = 0x10000 + (((C - 0xD800) << 10) | (C2 - 0xDC00));
                        End += 6;
                    }
                }
            }
            if (Key) Key->push_back(C);
        }
        NextOut = End;
        return true;
    }

    bool MatchNumber(std::size_t Start, std::size_t& Next) {
        const std::size_t EndIdx = N - 1;  // N > 0 here
        std::size_t Idx = Start;
        if (S[Idx] == '-') {
            ++Idx;
            if (Idx > EndIdx) return Stop();
        }
        if (S[Idx] >= '1' && S[Idx] <= '9') {
            ++Idx;
            while (Idx <= EndIdx && Digit(S[Idx])) ++Idx;
        } else if (S[Idx] == '0') {
            ++Idx;
        } else {
            return Stop();
        }
        if (Idx < EndIdx && S[Idx] == '.' && Digit(S[Idx + 1])) {
            Idx += 2;
            while (Idx <= EndIdx && Digit(S[Idx])) ++Idx;
        }
        if (Idx < EndIdx && (S[Idx] == 'e' || S[Idx] == 'E')) {
            const std::size_t EStart = Idx;
            ++Idx;
            if (Idx < EndIdx && (S[Idx] == '-' || S[Idx] == '+')) ++Idx;
            while (Idx <= EndIdx && Digit(S[Idx])) ++Idx;
            if (!Digit(S[Idx - 1])) Idx = EStart;
        }
        Next = Idx;
        return true;
    }

    bool ParseObject(std::size_t Idx, std::size_t& NextOut) {
        std::vector<std::vector<std::uint32_t>> Keys;
        Idx = SkipWs(Idx);
        if (Idx >= N || S[Idx] != '}') {
            while (true) {
                if (Idx >= N || S[Idx] != '"') return Err("Expecting property name enclosed in double quotes");
                std::vector<std::uint32_t> Key;
                std::size_t Next = 0;
                if (!ScanString(Idx + 1, Next, &Key)) return false;
                Idx = SkipWs(Next);
                if (Idx >= N || S[Idx] != ':') return Err("Expecting ':' delimiter");
                Idx = SkipWs(Idx + 1);
                if (!ScanOnce(Idx, Next)) return false;
                Keys.push_back(Key);
                Idx = SkipWs(Next);
                if (Idx < N && S[Idx] == '}') break;
                if (Idx >= N || S[Idx] != ',') return Err("Expecting ',' delimiter");
                Idx = SkipWs(Idx + 1);
            }
        }
        NextOut = Idx + 1;
        std::set<std::vector<std::uint32_t>> Seen;  // object_pairs_hook=_pairs
        for (const auto& K : Keys) {
            if (!Seen.insert(K).second) {
                R.P = Problem::DuplicateKey;
                R.Detail.clear();
                for (std::uint32_t C : K) Encode(C, R.Detail);
                return false;
            }
        }
        return true;
    }

    bool ParseArray(std::size_t Idx, std::size_t& NextOut) {
        Idx = SkipWs(Idx);
        if (Idx >= N || S[Idx] != ']') {
            while (true) {
                std::size_t Next = 0;
                if (!ScanOnce(Idx, Next)) return false;
                Idx = SkipWs(Next);
                if (Idx < N && S[Idx] == ']') break;
                if (Idx >= N || S[Idx] != ',') return Err("Expecting ',' delimiter");
                Idx = SkipWs(Idx + 1);
            }
        }
        NextOut = Idx + 1;
        return true;
    }

    bool ScanOnce(std::size_t Idx, std::size_t& Next) {
        if (Idx >= N) return Stop();
        const std::uint32_t C = S[Idx];
        switch (C) {
            case '"':
                return ScanString(Idx + 1, Next, nullptr);
            case '{':
            case '[': {
                if (++Depth > MaxDepth) {
                    R.P = Problem::Capacity;
                    R.Detail = "nesting";
                    return false;
                }
                const bool Ok = C == '{' ? ParseObject(Idx + 1, Next) : ParseArray(Idx + 1, Next);
                --Depth;
                return Ok;
            }
            case 'n': if (Idx + 3 < N && Lit(Idx, "null")) { Next = Idx + 4; return true; } break;
            case 't': if (Idx + 3 < N && Lit(Idx, "true")) { Next = Idx + 4; return true; } break;
            case 'f': if (Idx + 4 < N && Lit(Idx, "false")) { Next = Idx + 5; return true; } break;
            case 'N': if (Idx + 2 < N && Lit(Idx, "NaN")) { Next = Idx + 3; return true; } break;
            case 'I': if (Idx + 7 < N && Lit(Idx, "Infinity")) { Next = Idx + 8; return true; } break;
            case '-': if (Idx + 8 < N && Lit(Idx, "-Infinity")) { Next = Idx + 9; return true; } break;
            default: break;
        }
        return MatchNumber(Idx, Next);
    }
};

inline JsonResult JsonProblem(const std::vector<std::uint32_t>& Text) { return Scanner(Text).Loads(); }

// ---- check_bytes()
struct Finding {
    int K = 0;
    std::string File;
    std::string Json;  // json.dumps(finding, sort_keys=True)
    bool Capacity = false;
};

// os.path.splitext(rel)[1].lower() for '/'-separated paths (posixpath / genericpath._splitext).
inline std::string Ext(const std::string& P) {
    const std::size_t Sep = P.rfind('/');
    const std::size_t Dot = P.rfind('.');
    const std::size_t SepIdx = Sep == std::string::npos ? 0 : Sep + 1;
    if (Dot == std::string::npos || (Sep != std::string::npos && Dot < Sep)) return "";
    for (std::size_t F = SepIdx; F < Dot; ++F) {
        if (P[F] != '.') {
            std::string E = P.substr(Dot);
            for (char& C : E)
                if (C >= 'A' && C <= 'Z') C = static_cast<char>(C - 'A' + 'a');
            return E;
        }
    }
    return "";
}

inline std::vector<Finding> CheckBytes(const std::string& Rel, const std::string& RawIn) {
    std::vector<Finding> Out;
    auto Add = [&](int K, PyJson::Object O) {
        O.Add("file", PyJson::Str(Rel)).Add("kind", PyJson::Str(KindName(K)));
        Out.push_back(Finding{K, Rel, O.Dump(), false});
    };
    const std::string E = Ext(Rel);
    std::size_t Begin = 0;
    if (RawIn.size() >= 3 && RawIn.compare(0, 3, "\xEF\xBB\xBF") == 0) {
        Add(Bom, PyJson::Object{});
        Begin = 3;
    }
    std::size_t BadAt = 0;
    if (!CheckUtf8(RawIn, Begin, BadAt)) {
        Add(BadUtf8, PyJson::Object{}.Add("offset", PyJson::Int(static_cast<long long>(BadAt))));
        return Out;
    }
    const std::string T = RawIn.substr(Begin);
    long long CrLf = 0, Lf = 0;
    for (std::size_t I = 0; I < T.size(); ++I) {
        if (T[I] == '\n') ++Lf;
        if (T[I] == '\r' && I + 1 < T.size() && T[I + 1] == '\n') {
            ++CrLf;
            ++I;
            ++Lf;
        }
    }
    if (CrLf) Add(Crlf, PyJson::Object{}.Add("lines", PyJson::Int(CrLf)).Add("mixed", PyJson::Bool(Lf - CrLf > 0)));
    if (!T.empty() && T.back() != '\n') Add(NoFinalNewline, PyJson::Object{});
    std::vector<std::string> Lines(1);
    for (std::size_t I = 0; I < T.size(); ++I) {  // replace("\r\n", "\n").split("\n")
        if (T[I] == '\r' && I + 1 < T.size() && T[I + 1] == '\n') {
            Lines.emplace_back();
            ++I;
        } else if (T[I] == '\n') {
            Lines.emplace_back();
        } else {
            Lines.back() += T[I];
        }
    }
    if (E != ".md") {
        long long Count = 0, First = 0;
        for (std::size_t I = 0; I < Lines.size(); ++I)
            if (!Lines[I].empty() && (Lines[I].back() == ' ' || Lines[I].back() == '\t')) {
                if (!Count) First = static_cast<long long>(I + 1);
                ++Count;
            }
        if (Count) Add(TrailingSpace, PyJson::Object{}.Add("lines", PyJson::Int(Count)).Add("first", PyJson::Int(First)));
    }
    if (E == ".py" || E == ".yml" || E == ".yaml") {
        long long Count = 0, First = 0;
        for (std::size_t I = 0; I < Lines.size(); ++I) {
            bool Tab = false;
            for (char C : Lines[I]) {
                if (C == '\t') Tab = true;
                if (C != ' ' && C != '\t') break;
            }
            if (Tab) {
                if (!Count) First = static_cast<long long>(I + 1);
                ++Count;
            }
        }
        if (Count) Add(TabIndent, PyJson::Object{}.Add("lines", PyJson::Int(Count)).Add("first", PyJson::Int(First)));
    }
    auto Report = [&](const JsonResult& J, bool WithLine, long long Line) {
        if (J.P == Problem::None) return false;
        if (J.P == Problem::Capacity) {
            Out.push_back(Finding{BadJson, Rel, "", true});
            return true;
        }
        PyJson::Object O;
        O.Add("detail", PyJson::Str(J.Detail));
        if (WithLine) O.Add("line", PyJson::Int(Line));
        Add(J.P == Problem::DuplicateKey ? DuplicateKey : BadJson, O);
        return true;
    };
    if (E == ".json") {
        Report(JsonProblem(Decode(T, 0, T.size())), false, 0);
    } else if (E == ".jsonl") {
        for (std::size_t I = 0; I < Lines.size(); ++I) {
            const std::vector<std::uint32_t> L = Decode(Lines[I], 0, Lines[I].size());
            bool Blank = true;
            for (std::uint32_t C : L) Blank = Blank && PyIsSpace(C);
            if (Blank) continue;
            if (Report(JsonProblem(L), true, static_cast<long long>(I + 1))) break;
        }
    }
    return Out;
}

// ---- survey()'s ordering, counts and verdict over files already read (later duplicates win, like a dict).
struct Result {
    std::vector<Finding> Findings;
    std::uint64_t Counts[KindCount] = {0, 0, 0, 0, 0, 0, 0, 0};
    int Verdict = 0;  // 0 sound, 1 weeping, 2 leaking
    bool Capacity = false;
};

inline const char* VerdictName(int V) { return V == 2 ? "leaking" : V == 1 ? "weeping" : "sound"; }

inline Result Survey(const std::vector<std::pair<std::string, std::string>>& Files) {
    Result R;
    std::map<std::string, std::string> Sorted;
    std::size_t Total = 0;
    for (const auto& F : Files) {
        Total += F.second.size();
        if (F.second.size() > MaxFileBytes || Total > MaxTotalBytes || Sorted.size() >= MaxFiles) {
            R.Capacity = true;
            return R;
        }
        Sorted[F.first] = F.second;
    }
    for (const auto& F : Sorted)
        for (const Finding& X : CheckBytes(F.first, F.second)) {
            if (X.Capacity) {
                R.Capacity = true;
                return R;
            }
            R.Findings.push_back(X);
        }
    std::stable_sort(R.Findings.begin(), R.Findings.end(), [](const Finding& A, const Finding& B) {
        return A.K != B.K ? A.K < B.K : A.File < B.File;
    });
    for (const Finding& X : R.Findings) ++R.Counts[X.K];
    R.Verdict = (R.Counts[BadUtf8] || R.Counts[BadJson] || R.Counts[DuplicateKey]) ? 2 : R.Findings.empty() ? 0 : 1;
    return R;
}

}  // namespace CaulkingCheck
}  // namespace DaedalusDiskSaver
