// try { this comment does not count } catch (...) "nor does this"
#pragma once
#include <string>
inline bool ParseInt(const std::string& S, long long& Out)
{
	size_t P = 0; try { Out = std::stoll(S, &P); } catch (...) { return false; }
	const char* Why = "a string with throw and try { in it";
	(void)Why;
	return P == S.size();
}
