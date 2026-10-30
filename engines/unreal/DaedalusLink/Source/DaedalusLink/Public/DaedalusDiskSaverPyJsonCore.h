// SPDX-License-Identifier: MIT
// Shared by the batch 8 DiskSaver cores (G531, G517, G544): Python's json.dumps(...,
// sort_keys=True) text for the small flat objects those tools print or sort by, with the
// default ensure_ascii escaping (\uXXXX in lowercase hex, astral characters as surrogate
// pairs). Strings are UTF-8 bytes; lone surrogates (as Python's "surrogatepass" writes them)
// are accepted. Header-only C++17; no Unreal includes, no exceptions, no RTTI.
#pragma once

#include <algorithm>
#include <cstddef>
#include <cstdint>
#include <string>
#include <utility>
#include <vector>

namespace DaedalusDiskSaver {
namespace PyJson {

// Next code point of a UTF-8 (or surrogate-pass) byte string; malformed bytes read as U+FFFD, one byte each.
inline std::uint32_t NextCodePoint(const std::string& S, std::size_t& I) {
    const unsigned char C = static_cast<unsigned char>(S[I]);
    int Len = C < 0x80 ? 1 : (C >> 5) == 6 ? 2 : (C >> 4) == 14 ? 3 : (C >> 3) == 30 ? 4 : 0;
    if (Len == 0 || I + static_cast<std::size_t>(Len) > S.size()) {
        ++I;
        return 0xFFFD;
    }
    std::uint32_t V = Len == 1 ? C : Len == 2 ? (C & 0x1Fu) : Len == 3 ? (C & 0x0Fu) : (C & 0x07u);
    for (int K = 1; K < Len; ++K) {
        const unsigned char D = static_cast<unsigned char>(S[I + static_cast<std::size_t>(K)]);
        if ((D & 0xC0) != 0x80) {
            ++I;
            return 0xFFFD;
        }
        V = (V << 6) | (D & 0x3Fu);
    }
    I += static_cast<std::size_t>(Len);
    return V;
}

inline void AppendU4(std::string& Out, std::uint32_t V) {
    static const char* const H = "0123456789abcdef";
    Out += "\\u";
    for (int K = 3; K >= 0; --K) Out += H[(V >> (4 * K)) & 15];
}

// json.dumps of a str with ensure_ascii=True.
inline std::string Str(const std::string& S) {
    std::string Out = "\"";
    std::size_t I = 0;
    while (I < S.size()) {
        const std::uint32_t C = NextCodePoint(S, I);
        if (C == '"') Out += "\\\"";
        else if (C == '\\') Out += "\\\\";
        else if (C == '\n') Out += "\\n";
        else if (C == '\r') Out += "\\r";
        else if (C == '\t') Out += "\\t";
        else if (C == '\b') Out += "\\b";
        else if (C == '\f') Out += "\\f";
        else if (C >= 0x20 && C <= 0x7E) Out += static_cast<char>(C);
        else if (C >= 0x10000) {
            const std::uint32_t V = C - 0x10000;
            AppendU4(Out, 0xD800 | (V >> 10));
            AppendU4(Out, 0xDC00 | (V & 0x3FF));
        } else {
            AppendU4(Out, C);
        }
    }
    return Out + "\"";
}

inline std::string Int(long long V) { return std::to_string(V); }
inline std::string Bool(bool B) { return B ? "true" : "false"; }
inline std::string Null() { return "null"; }

// A JSON object with sort_keys=True; Compact = separators (",", ":") instead of (", ", ": ").
struct Object {
    std::vector<std::pair<std::string, std::string>> Fields;  // key (UTF-8) -> already-dumped value
    Object& Add(const std::string& Key, const std::string& Value) {
        Fields.emplace_back(Key, Value);
        return *this;
    }
    std::string Dump(bool Compact = false) const {
        std::vector<std::pair<std::string, std::string>> F = Fields;
        std::stable_sort(F.begin(), F.end(), [](const std::pair<std::string, std::string>& A, const std::pair<std::string, std::string>& B) {
            return A.first < B.first;
        });
        std::string Out = "{";
        for (std::size_t K = 0; K < F.size(); ++K) {
            if (K) Out += Compact ? "," : ", ";
            Out += Str(F[K].first) + (Compact ? ":" : ": ") + F[K].second;
        }
        return Out + "}";
    }
};

inline std::string List(const std::vector<std::string>& Values, bool Compact = false) {
    std::string Out = "[";
    for (std::size_t K = 0; K < Values.size(); ++K) Out += (K ? (Compact ? "," : ", ") : "") + Values[K];
    return Out + "]";
}

}  // namespace PyJson
}  // namespace DaedalusDiskSaver
