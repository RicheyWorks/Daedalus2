// SPDX-License-Identifier: MIT
// BBA 1, the asset LOD manifest from the Blender pipeline, and the LOD picker (Blender Boss / blender-team).
// Plain C++17, header-only, no Unreal types: core-test/asset_lod_core_test.cpp checks it, and
// com.daedalus.world.assets.AssetLodManifest must agree with it byte for byte (asset_lod_parity.txt).
//
//   BBA 1
//   asset <id> lod0 <faces> lod1 <faces|-> radius <cm> switch <cm>
//
// All numbers are integers (faces, Unreal centimetres), so there is no float formatting to drift. Manifests are all
// or nothing: one bad line refuses the whole file with "line N: why".
#pragma once
#include <algorithm>
#include <cstdint>
#include <string>
#include <vector>

namespace daedalus { namespace assetlod {

static constexpr int Version = 1;
static constexpr int64_t MaxAssets = 200000;
static constexpr int64_t MaxFaces = 10000000;
static constexpr int64_t MaxCm = 100000000;
static constexpr size_t MaxLine = 512;

struct Asset { std::string Id; int64_t Lod0 = 0; int64_t Lod1 = -1; int64_t Radius = 0; int64_t Switch = 0; };
struct Manifest { std::vector<Asset> Assets; };
struct ParseResult { bool Ok = false; std::string Error; Manifest Out; };
struct Instance { size_t Asset = 0; int64_t Distance = 0; };
struct BudgetResult { std::vector<int> Lods; int64_t Faces = 0; };

// The default switch distance the generator writes: 20 bounding radii, never closer than 5 m.
inline int64_t SwitchFor(int64_t RadiusCm) { return std::max<int64_t>(500, RadiusCm * 20); }

inline bool Token(const std::string& S)
{
	if (S.empty() || S.size() > 96) return false;
	for (char C : S)
		if (!((C >= 'a' && C <= 'z') || (C >= 'A' && C <= 'Z') || (C >= '0' && C <= '9') || C == '_' || C == '-' || C == '.')) return false;
	return true;
}
inline bool Int(const std::string& S, int64_t Lo, int64_t Hi, int64_t& Out)
{
	if (S.empty() || S.size() > 12) return false;
	int64_t V = 0;
	for (char C : S) { if (C < '0' || C > '9') return false; V = V * 10 + (C - '0'); }
	if (S.size() > 1 && S[0] == '0') return false;
	if (V < Lo || V > Hi) return false;
	Out = V; return true;
}
inline std::vector<std::string> Split(const std::string& L)
{
	std::vector<std::string> W; std::string Cur;
	for (char C : L) { if (C == ' ') { if (!Cur.empty()) W.push_back(Cur); Cur.clear(); } else Cur += C; }
	if (!Cur.empty()) W.push_back(Cur);
	return W;
}

inline ParseResult Parse(const std::string& Text)
{
	ParseResult R; std::vector<std::string> Lines; std::string Cur;
	for (char C : Text) { if (C == '\n') { Lines.push_back(Cur); Cur.clear(); } else Cur += C; }
	if (!Cur.empty()) Lines.push_back(Cur);
	auto Fail = [&](size_t N, const std::string& Why) { ParseResult F; F.Error = "line " + std::to_string(N) + ": " + Why; return F; };
	bool Head = false; std::vector<std::string> Seen;
	for (size_t I = 0; I < Lines.size(); ++I)
	{
		std::string L = Lines[I]; const size_t N = I + 1;
		if (!L.empty() && L.back() == '\r') L.pop_back();
		if (L.size() > MaxLine) return Fail(N, "line too long");
		if (L.empty() || L[0] == '#') continue;
		if (L.find('\t') != std::string::npos) return Fail(N, "tab");
		std::vector<std::string> W = Split(L);
		if (!Head)
		{
			if (W.size() != 2 || W[0] != "BBA") return Fail(N, "expected 'BBA 1'");
			if (W[1] != "1") return Fail(N, "unsupported version " + W[1]);
			Head = true; continue;
		}
		if (W[0] != "asset") return Fail(N, "unknown record " + W[0]);
		if (W.size() != 10 || W[2] != "lod0" || W[4] != "lod1" || W[6] != "radius" || W[8] != "switch")
			return Fail(N, "expected 'asset <id> lod0 <n> lod1 <n|-> radius <cm> switch <cm>'");
		Asset A; A.Id = W[1];
		if (!Token(A.Id)) return Fail(N, "bad asset id");
		if (!Int(W[3], 1, MaxFaces, A.Lod0)) return Fail(N, "bad lod0");
		if (W[5] != "-" && !Int(W[5], 1, MaxFaces, A.Lod1)) return Fail(N, "bad lod1");
		if (A.Lod1 > A.Lod0) return Fail(N, "lod1 has more faces than lod0");
		if (!Int(W[7], 1, MaxCm, A.Radius)) return Fail(N, "bad radius");
		if (!Int(W[9], 0, MaxCm, A.Switch)) return Fail(N, "bad switch");
		R.Out.Assets.push_back(A); Seen.push_back(A.Id);
		if ((int64_t)R.Out.Assets.size() > MaxAssets) return Fail(N, "too many assets");
	}
	if (!Head) return Fail(Lines.size() + 1, "empty");
	std::sort(Seen.begin(), Seen.end());
	for (size_t I = 1; I < Seen.size(); ++I) if (Seen[I] == Seen[I - 1]) { ParseResult F; F.Error = "duplicate asset " + Seen[I]; return F; }
	R.Ok = true; return R;
}

// Canonical form: assets sorted by id, single spaces, '\n' line ends.
inline std::string Write(const Manifest& M)
{
	std::vector<Asset> A = M.Assets;
	std::sort(A.begin(), A.end(), [](const Asset& X, const Asset& Y) { return X.Id < Y.Id; });
	std::string S = "BBA 1\n";
	for (const Asset& X : A)
		S += "asset " + X.Id + " lod0 " + std::to_string(X.Lod0) + " lod1 " + (X.Lod1 < 0 ? std::string("-") : std::to_string(X.Lod1))
			+ " radius " + std::to_string(X.Radius) + " switch " + std::to_string(X.Switch) + "\n";
	return S;
}

// 1 = draw LOD1: it exists and the camera is at or beyond the switch distance.
inline int Select(const Asset& A, int64_t DistanceCm) { return (A.Lod1 >= 0 && DistanceCm >= A.Switch) ? 1 : 0; }
inline int64_t Faces(const Asset& A, int Lod) { return Lod == 1 ? A.Lod1 : A.Lod0; }

// Distance rule first; then, while over the face budget, drop the farthest LOD0 instances that have a LOD1
// (ties: lower asset id, then lower instance index). Can stay over budget when nothing is left to drop.
inline BudgetResult Budget(const Manifest& M, const std::vector<Instance>& In, int64_t FaceBudget)
{
	BudgetResult R; R.Lods.resize(In.size());
	std::vector<size_t> Cand;
	for (size_t I = 0; I < In.size(); ++I)
	{
		const Asset& A = M.Assets[In[I].Asset];
		R.Lods[I] = Select(A, In[I].Distance); R.Faces += Faces(A, R.Lods[I]);
		if (R.Lods[I] == 0 && A.Lod1 >= 0) Cand.push_back(I);
	}
	std::sort(Cand.begin(), Cand.end(), [&](size_t X, size_t Y) {
		if (In[X].Distance != In[Y].Distance) return In[X].Distance > In[Y].Distance;
		const std::string& IX = M.Assets[In[X].Asset].Id; const std::string& IY = M.Assets[In[Y].Asset].Id;
		if (IX != IY) return IX < IY;
		return X < Y; });
	for (size_t I : Cand)
	{
		if (R.Faces <= FaceBudget) break;
		const Asset& A = M.Assets[In[I].Asset];
		R.Faces -= A.Lod0 - A.Lod1; R.Lods[I] = 1;
	}
	return R;
}

}} // namespace daedalus::assetlod
