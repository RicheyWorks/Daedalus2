// SPDX-License-Identifier: MIT
// DSB 1 (island streaming budget manifest) and the resident-set picker (disk-saver). Plain C++17, no Unreal headers,
// so the same rules run in the plugin, in core-test and (ported line for line) in Java
// com.daedalus.world.streaming.StreamingBudget. Parity: engines/unreal/core-test/streaming_budget_parity.txt.
//
//   DSB 1
//   island <id> x <cm> y <cm> ram <kib> disk <kib>
//
// Integers only (Unreal centimetres, KiB). All or nothing: one bad line refuses the file.
// Pick: an island is wanted when it is within the load radius, or it is already resident and still within the
// (larger) unload radius (hysteresis, so islands on the edge do not thrash). Wanted islands are taken nearest first
// (ties by manifest index) while their RAM fits the budget; ones that do not fit are skipped, never partly loaded.
#pragma once
#include <algorithm>
#include <cstdint>
#include <set>
#include <string>
#include <vector>

namespace daedalus::streamingbudget
{
constexpr int64_t MaxIslands = 20000;
constexpr int64_t MaxCm = 1000000000;   // |x|,|y| <= 1e9 cm, so dx*dx + dy*dy < 2^63
constexpr int64_t MaxKib = 100000000;   // 100 GiB per island
constexpr size_t MaxLine = 512;

struct Island { std::string Id; int64_t X = 0, Y = 0, Ram = 0, Disk = 0; };
struct Manifest { std::vector<Island> Islands; };
struct ParseResult { bool Ok = false; Manifest Out; std::string Error; };
struct PickResult { std::vector<bool> Resident; int64_t Ram = 0, Disk = 0; int Count = 0; };

inline bool ParseInt(const std::string& S, bool AllowNeg, int64_t Lo, int64_t Hi, int64_t& Out)
{
	size_t I = 0; bool Neg = false;
	if (AllowNeg && !S.empty() && S[0] == '-') { Neg = true; I = 1; }
	if (I >= S.size() || S.size() - I > 12) return false;
	if (S[I] == '0' && S.size() - I > 1) return false;
	if (Neg && S.size() - I == 1 && S[I] == '0') return false;   // no "-0"
	int64_t V = 0;
	for (; I < S.size(); ++I) { if (S[I] < '0' || S[I] > '9') return false; V = V * 10 + (S[I] - '0'); }
	V = Neg ? -V : V;
	if (V < Lo || V > Hi) return false;
	Out = V; return true;
}

inline bool GoodId(const std::string& S)
{
	if (S.empty() || S.size() > 64) return false;
	for (char C : S) if (!((C >= 'a' && C <= 'z') || (C >= 'A' && C <= 'Z') || (C >= '0' && C <= '9') || C == '_')) return false;
	return true;
}

inline std::vector<std::string> Split(const std::string& L)
{
	std::vector<std::string> T; std::string Cur;
	for (char C : L) { if (C == ' ' || C == '\t') { if (!Cur.empty()) { T.push_back(Cur); Cur.clear(); } } else Cur += C; }
	if (!Cur.empty()) T.push_back(Cur);
	return T;
}

inline ParseResult Parse(const std::string& Text)
{
	ParseResult R;
	auto Fail = [&](size_t N, const std::string& Why) { R.Ok = false; R.Out = Manifest(); R.Error = "line " + std::to_string(N) + ": " + Why; return R; };
	bool Header = false; std::set<std::string> Seen;
	size_t Start = 0, N = 0;
	while (Start <= Text.size())
	{
		++N;
		const size_t Newline = Text.find('\n', Start);
		const size_t End = Newline == std::string::npos ? Text.size() : Newline;
		size_t Length = End - Start;
		if (Length && Text[End - 1] == '\r') --Length;
		if (Length > MaxLine) return Fail(N, "line too long");
		const std::string L = Text.substr(Start, Length);
		// The input already exists; copy at most one bounded line, never the entire manifest.
		Start = Newline == std::string::npos ? Text.size() + 1 : Newline + 1;
		std::vector<std::string> T = Split(L);
		if (T.empty() || T[0][0] == '#') continue;
		if (!Header)
		{
			if (T.size() == 2 && T[0] == "DSB") { if (T[1] != "1") return Fail(N, "unsupported version " + T[1]); Header = true; continue; }
			return Fail(N, "expected 'DSB 1'");
		}
		if (T[0] != "island") return Fail(N, "unknown record " + T[0]);
		if (T.size() != 10 || T[2] != "x" || T[4] != "y" || T[6] != "ram" || T[8] != "disk")
			return Fail(N, "expected 'island <id> x <cm> y <cm> ram <kib> disk <kib>'");
		Island I; I.Id = T[1];
		if (!GoodId(I.Id)) return Fail(N, "bad island id");
		if (!Seen.insert(I.Id).second) return Fail(N, "duplicate island " + I.Id);
		if (!ParseInt(T[3], true, -MaxCm, MaxCm, I.X)) return Fail(N, "bad x");
		if (!ParseInt(T[5], true, -MaxCm, MaxCm, I.Y)) return Fail(N, "bad y");
		if (!ParseInt(T[7], false, 1, MaxKib, I.Ram)) return Fail(N, "bad ram");
		if (!ParseInt(T[9], false, 1, MaxKib, I.Disk)) return Fail(N, "bad disk");
		if ((int64_t)R.Out.Islands.size() >= MaxIslands) return Fail(N, "too many islands");
		R.Out.Islands.push_back(I);
	}
	if (!Header) return Fail(1, "empty");
	R.Ok = true; return R;
}

// Canonical form: header, then islands sorted by id (byte order), single spaces, LF endings.
inline std::string Write(const Manifest& M)
{
	std::vector<const Island*> P; for (const Island& I : M.Islands) P.push_back(&I);
	std::sort(P.begin(), P.end(), [](const Island* A, const Island* B) { return A->Id < B->Id; });
	std::string O = "DSB 1\n";
	for (const Island* I : P)
		O += "island " + I->Id + " x " + std::to_string(I->X) + " y " + std::to_string(I->Y) + " ram " + std::to_string(I->Ram) + " disk " + std::to_string(I->Disk) + "\n";
	return O;
}

inline int64_t Dist2(const Island& I, int64_t Vx, int64_t Vy) { const int64_t Dx = I.X - Vx, Dy = I.Y - Vy; return Dx * Dx + Dy * Dy; }

// Viewer must be within +-MaxCm; radii within 0..MaxCm (unload < load is treated as unload == load).
inline PickResult Pick(const Manifest& M, int64_t Vx, int64_t Vy, int64_t LoadCm, int64_t UnloadCm, int64_t RamBudget, const std::vector<bool>& WasResident)
{
	const int64_t Load2 = LoadCm * LoadCm, Unload2 = std::max(LoadCm, UnloadCm) * std::max(LoadCm, UnloadCm);
	std::vector<std::pair<int64_t, size_t>> Want;
	for (size_t I = 0; I < M.Islands.size(); ++I)
	{
		const int64_t D = Dist2(M.Islands[I], Vx, Vy);
		const bool Was = I < WasResident.size() && WasResident[I];
		if (D <= Load2 || (Was && D <= Unload2)) Want.push_back({D, I});
	}
	std::sort(Want.begin(), Want.end());
	PickResult R; R.Resident.assign(M.Islands.size(), false);
	for (const auto& W : Want)
	{
		const Island& I = M.Islands[W.second];
		if (I.Ram > RamBudget - R.Ram) continue;
		R.Resident[W.second] = true; R.Ram += I.Ram; R.Disk += I.Disk; ++R.Count;
	}
	return R;
}

inline std::string Bits(const std::vector<bool>& B) { std::string S; for (bool V : B) S += V ? '1' : '0'; return S; }
} // namespace daedalus::streamingbudget
