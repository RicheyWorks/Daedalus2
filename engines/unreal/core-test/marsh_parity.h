// SPDX-License-Identifier: MIT
// Shared helpers for marsh-lane core tests (G570 and later ecology ports): read a Java-written golden-vector file
// of "key=value" lines and compare fields, integers exactly and floats with a relative tolerance.
#pragma once
#ifndef _CRT_SECURE_NO_WARNINGS
#define _CRT_SECURE_NO_WARNINGS 1 // MSVC /WX: allow fopen
#endif
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <string>
#include <vector>

namespace marsh_test {

inline int Passed = 0, Total = 0;

inline void Check(const std::string& Name, bool OK)
{
	++Total;
	Passed += OK;
	if (!OK) std::printf("FAIL %s\n", Name.c_str());
}

inline std::vector<std::string> ParityLines(const char* Path)
{
	std::vector<std::string> Out;
	std::ifstream In(Path);
	std::string Line;
	while (std::getline(In, Line))
	{
		if (!Line.empty() && Line.back() == '\r') Line.pop_back();
		if (!Line.empty() && Line[0] != '#') Out.push_back(Line);
	}
	return Out;
}

inline std::string Field(const std::string& Line, const std::string& Key)
{
	const std::string Needle = Key + "=";
	size_t P = Line.rfind(" " + Needle);
	P = (P == std::string::npos) ? (Line.rfind(Needle, 0) == 0 ? 0 : std::string::npos) : P + 1;
	if (P == std::string::npos) return "";
	const size_t S = P + Needle.size(), E = Line.find(' ', S);
	return Line.substr(S, E == std::string::npos ? std::string::npos : E - S);
}
inline double Num(const std::string& Line, const std::string& Key) { return std::strtod(Field(Line, Key).c_str(), nullptr); }
inline long long Int(const std::string& Line, const std::string& Key) { return std::atoll(Field(Line, Key).c_str()); }

// |a - b| <= Rel * max(1, |b|); infinities must match exactly.
inline bool Close(double A, double B, double Rel)
{
	if (std::isinf(A) || std::isinf(B)) return A == B;
	return std::fabs(A - B) <= Rel * std::fmax(1.0, std::fabs(B));
}

inline int Summary(const char* Name)
{
	std::printf("%s %s: %d/%d checks passed\n", Passed == Total ? "OK" : "FAIL", Name, Passed, Total);
	return Passed == Total ? 0 : 1;
}

} // namespace marsh_test
