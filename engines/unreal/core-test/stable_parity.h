// SPDX-License-Identifier: MIT
// Shared helpers for the stable-lane core tests (G567): read a Java-written parity file and compare lines.
#pragma once
#ifndef _CRT_SECURE_NO_WARNINGS
#define _CRT_SECURE_NO_WARNINGS 1 // MSVC /WX: allow fopen
#endif
#include <cstdio>
#include <fstream>
#include <string>
#include <vector>

namespace stable_test {

inline int Passed = 0, Total = 0;

inline void Check(const char* Name, bool OK)
{
	++Total;
	Passed += OK;
	std::printf("%s %s\n", OK ? "PASS" : "FAIL", Name);
}

inline std::string Join(const std::vector<int>& V)
{
	if (V.empty()) return "-";
	std::string S;
	for (size_t i = 0; i < V.size(); ++i) S += (i ? "," : "") + std::to_string(V[i]);
	return S;
}

// Lines of a parity file, skipping comments and blank lines (StableCoresParityTest writes them).
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

// Compares C++ lines with the Java-written file, reporting the first mismatch.
inline void CheckParity(const char* Path, const std::vector<std::string>& Actual)
{
	const std::vector<std::string> Expected = ParityLines(Path);
	bool Same = Expected.size() == Actual.size() && !Expected.empty();
	for (size_t i = 0; Same && i < Actual.size(); ++i)
	{
		if (Actual[i] != Expected[i])
		{
			std::printf("line %zu\n  java: %s\n  c++:  %s\n", i, Expected[i].c_str(), Actual[i].c_str());
			Same = false;
		}
	}
	Check("C++ = Java on every parity line", Same);
}

inline int Finish()
{
	std::printf("%d/%d passed\n", Passed, Total);
	return Passed == Total ? 0 : 1;
}

} // namespace stable_test
