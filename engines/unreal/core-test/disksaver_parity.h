// SPDX-License-Identifier: MIT
// Shared, framework-free helpers for the DiskSaver core parity tests (disksaver_*_core_test.cpp).
#pragma once

#include <cstdint>
#include <fstream>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

namespace DiskSaverParity {

inline int& Failures() {
    static int F = 0;
    return F;
}

inline void Check(bool Ok, const std::string& What) {
    if (!Ok) {
        ++Failures();
        if (Failures() <= 20) std::cerr << "FAIL: " << What << "\n";
    }
}

inline std::vector<std::string> Split(const std::string& S, char Sep) {
    std::vector<std::string> Out;
    if (S == "-" || S.empty()) return Out;
    std::string Cur;
    for (char C : S) {
        if (C == Sep) {
            Out.push_back(Cur);
            Cur.clear();
        } else {
            Cur += C;
        }
    }
    Out.push_back(Cur);
    return Out;
}

// Strict nonnegative decimal; false on anything else (no exceptions).
inline bool ToInt(const std::string& S, int& Out) {
    if (S.empty() || S.size() > 9 || (S.size() > 1 && S[0] == '0')) return false;  // canonical digits only
    int V = 0;
    for (char C : S) {
        if (C < '0' || C > '9') return false;
        V = V * 10 + (C - '0');
    }
    Out = V;
    return true;
}

inline std::vector<int> Ints(const std::string& S, char Sep) {
    std::vector<int> Out;
    for (const std::string& T : Split(S, Sep)) {
        int V = -1;
        Check(ToInt(T, V), "bad integer '" + T + "'");
        Out.push_back(V);
    }
    return Out;
}

inline std::string Join(const std::vector<int>& V, char Sep) {
    if (V.empty()) return "-";
    std::string S;
    for (std::size_t i = 0; i < V.size(); ++i) {
        if (i) S += Sep;
        S += std::to_string(V[i]);
    }
    return S;
}

inline std::vector<std::vector<std::string>> ReadLines(const char* Path) {
    std::vector<std::vector<std::string>> Out;
    std::ifstream In(Path);
    Check(static_cast<bool>(In), std::string("cannot open ") + Path);
    std::string Line;
    while (std::getline(In, Line)) {
        if (Line.empty() || Line[0] == '#') continue;
        std::istringstream L(Line);
        std::vector<std::string> Tok;
        std::string T;
        while (L >> T) Tok.push_back(T);
        Out.push_back(Tok);
    }
    return Out;
}

inline int Finish(const char* Game, int Cases, int Trials) {
    Check(Cases >= 8, std::string(Game) + ": too few cases");
    std::cout << Game << " parity: " << Cases << " layouts, " << Trials << " plays replayed\n";
    if (Failures()) {
        std::cerr << Failures() << " failure(s)\n";
        return 1;
    }
    std::cout << Game << " core: OK\n";
    return 0;
}

}  // namespace DiskSaverParity
