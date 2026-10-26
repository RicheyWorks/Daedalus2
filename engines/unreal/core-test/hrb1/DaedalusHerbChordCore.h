// SPDX-License-Identifier: MIT
// HRB 1 decoder (docs/contracts/hrb-v1). Plain C++17, header-only, no engine dependencies.
// Strict: any deviation from the grammar fails the whole decode and leaves `out` untouched,
// so a caller can keep its previous valid chord.
#pragma once

#include <array>
#include <cstddef>
#include <string>
#include <string_view>
#include <vector>

namespace daedalus::herb {

struct Chord {
    int Root = 0;                 // pitch class 0-11
    std::string Quality;          // unison, fifth, major, minor, sus, dim, aug, maj7, min7, dom7, cluster
    std::string Effect;           // STEADY, HEAL, CALM, FOCUS, WARD, HASTE, CHAOS
    double Strength = 0.0;        // 0-1
    std::vector<double> Freqs;    // Hz, ascending, 1-12 entries
};

constexpr std::size_t kMaxBody = 4096;
constexpr std::size_t kMaxLine = 512;
constexpr std::size_t kMaxFreqs = 12;

namespace detail {
inline bool OneOf(std::string_view v, const std::string_view* set, std::size_t n) {
    for (std::size_t i = 0; i < n; ++i) if (v == set[i]) return true;
    return false;
}
inline bool IsDigit(char c) { return c >= '0' && c <= '9'; }
// Fixed "<digits>.<3 digits>", no sign, no exponent, at most 7 integer digits.
inline bool Fixed3(std::string_view s, double& out) {
    const std::size_t dot = s.find('.');
    if (dot == std::string_view::npos || dot == 0 || dot > 7 || s.size() != dot + 4) return false;
    if (dot > 1 && s[0] == '0') return false;
    long long whole = 0;
    for (std::size_t i = 0; i < dot; ++i) { if (!IsDigit(s[i])) return false; whole = whole * 10 + (s[i] - '0'); }
    int frac = 0;
    for (std::size_t i = dot + 1; i < s.size(); ++i) { if (!IsDigit(s[i])) return false; frac = frac * 10 + (s[i] - '0'); }
    out = static_cast<double>(whole) + frac / 1000.0;
    return true;
}
inline std::vector<std::string_view> Split(std::string_view line) {
    std::vector<std::string_view> parts;
    std::size_t start = 0;
    for (std::size_t i = 0; i <= line.size(); ++i) {
        if (i == line.size() || line[i] == ' ') { parts.push_back(line.substr(start, i - start)); start = i + 1; }
    }
    return parts;
}
}  // namespace detail

inline bool DecodeHrb1(std::string_view text, Chord& out, std::string& error) {
    static constexpr std::array<std::string_view, 11> kQualities{
        "unison", "fifth", "major", "minor", "sus", "dim", "aug", "maj7", "min7", "dom7", "cluster"};
    static constexpr std::array<std::string_view, 7> kEffects{
        "STEADY", "HEAL", "CALM", "FOCUS", "WARD", "HASTE", "CHAOS"};
    auto fail = [&error](const char* why) { error = why; return false; };
    if (text.empty() || text.size() > kMaxBody) return fail("body size");
    if (text.back() != '\n') return fail("missing final LF");
    for (char c : text) {
        const unsigned char u = static_cast<unsigned char>(c);
        if (u == 0 || u > 127 || u == '\r' || u == '\t') return fail("non-ASCII or control byte");
    }
    std::vector<std::string_view> lines;
    std::size_t start = 0;
    for (std::size_t i = 0; i < text.size(); ++i) {
        if (text[i] == '\n') {
            if (i - start > kMaxLine) return fail("line too long");
            lines.push_back(text.substr(start, i - start));
            start = i + 1;
        }
    }
    if (lines.size() < 4) return fail("too few records");
    if (lines[0] != "HRB 1") return fail("unsupported header");
    Chord chord;
    const auto c = detail::Split(lines[1]);
    if (c.size() != 5 || c[0] != "chord") return fail("chord record");
    if (c[1].empty() || c[1].size() > 2 || !detail::IsDigit(c[1][0]) || (c[1].size() == 2 && (c[1][0] == '0' || !detail::IsDigit(c[1][1]))))
        return fail("chord root");
    chord.Root = c[1].size() == 1 ? c[1][0] - '0' : (c[1][0] - '0') * 10 + (c[1][1] - '0');
    if (chord.Root > 11) return fail("chord root range");
    if (!detail::OneOf(c[2], kQualities.data(), kQualities.size())) return fail("chord quality");
    if (!detail::OneOf(c[3], kEffects.data(), kEffects.size())) return fail("chord effect");
    if (!detail::Fixed3(c[4], chord.Strength) || chord.Strength > 1.0) return fail("chord strength");
    chord.Quality = std::string(c[2]);
    chord.Effect = std::string(c[3]);
    std::size_t i = 2;
    for (; i < lines.size() && lines[i] != "end"; ++i) {
        const auto f = detail::Split(lines[i]);
        double hz = 0;
        if (f.size() != 2 || f[0] != "freq") return fail("unknown record");
        if (!detail::Fixed3(f[1], hz) || hz <= 0.0 || hz > 20000.0) return fail("freq value");
        if (!chord.Freqs.empty() && hz < chord.Freqs.back()) return fail("freq order");
        if (chord.Freqs.size() == kMaxFreqs) return fail("too many freqs");
        chord.Freqs.push_back(hz);
    }
    if (chord.Freqs.empty()) return fail("no freq");
    if (i != lines.size() - 1) return fail(i == lines.size() ? "missing end" : "data after end");
    out = std::move(chord);
    error.clear();
    return true;
}

}  // namespace daedalus::herb
