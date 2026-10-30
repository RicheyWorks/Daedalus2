// SPDX-License-Identifier: MIT
// Shared helpers for the ark tree core tests (G572): text builders matching ArkTreesParityTest.java.
#pragma once
#include "stable_parity.h"
#include <cstdint>
#include <string>
#include <vector>

namespace ark_test {

template <typename T>
std::string Join(const std::vector<T>& V)
{
	if (V.empty()) return "-";
	std::string S;
	for (size_t i = 0; i < V.size(); ++i) S += (i ? "," : "") + std::to_string(V[i]);
	return S;
}

inline std::string S(int64_t V) { return std::to_string(V); }

} // namespace ark_test
