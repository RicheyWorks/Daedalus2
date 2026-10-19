// SPDX-License-Identifier: MIT
// G25 server route, plain C++17 for the Unreal binding: the client half of POST /api/v1/brew/melody
// (docs/contracts/brew-melody-v1, youtube-master #316). Builds the request, refuses what the server would 400,
// parses the 200 body and names the error statuses. No Unreal types; ADaedalusBrewBench does the HTTP (the kennel
// trough pattern in DaedalusTonic.cpp). Checked by engines/unreal/core-test/brew_melody_core_test.cpp against
// the contract's http-cases.json.
#pragma once
#include <cerrno>
#include <cstdint>
#include <cstdlib>
#include <cstdio>
#include <map>
#include <memory>
#include <string>
#include <vector>

namespace daedalus { namespace brewmelody {

inline const char* Route() { return "/api/v1/brew/melody"; }
constexpr int MinHerbs = 3, MaxHerbs = 5, MinStage = 1, MaxStage = 4, DefaultStage = 3, MaxRecords = 64, MaxBody = 64 * 1024;

/** PitchTable.ISLAND_CANON: the twelve chromatic island herbs, matched case-insensitively like pitchOf (the server's 400 rule). */
inline bool KnownHerb(const std::string& H)
{
	static const char* const N[] = { "doleaf", "sharpcress", "rebell", "flatfern", "mimint", "fasage", "hushmoss", "solthorn", "gloryroot", "lavine", "dronebloom", "tisquill" };
	std::string L = H;
	for (char& C : L) if (C >= 'A' && C <= 'Z') C = static_cast<char>(C - 'A' + 'a');
	for (const char* K : N) if (L == K) return true;
	return false;
}

// ------------------------------------------------------------------ tiny JSON
struct Json
{
	enum class Kind { Null, Bool, Number, String, Array, Object } K = Kind::Null;
	bool B = false; double N = 0; std::string S; std::vector<Json> A; std::vector<std::pair<std::string, Json>> O;
	const Json* Get(const std::string& Key) const { for (const auto& P : O) if (P.first == Key) return &P.second; return nullptr; }
};

struct Reader
{
	const std::string& T; size_t I = 0; int Depth = 0;
	explicit Reader(const std::string& Text) : T(Text) {}
	void Ws() { while (I < T.size() && (T[I] == ' ' || T[I] == '\t' || T[I] == '\n' || T[I] == '\r')) ++I; }
	bool Lit(const char* L) { size_t N = 0; while (L[N]) ++N; if (T.compare(I, N, L) != 0) return false; I += N; return true; }
	bool Str(std::string& Out)
	{
		if (I >= T.size() || T[I] != '"') return false;
		++I; Out.clear();
		while (I < T.size() && T[I] != '"')
		{
			char C = T[I++];
			if (C == '\\')
			{
				if (I >= T.size()) return false;
				const char E = T[I++];
				if (E == 'n') C = '\n'; else if (E == 't') C = '\t'; else if (E == 'r') C = '\r'; else if (E == 'b') C = '\b'; else if (E == 'f') C = '\f';
				else if (E == 'u')
				{
					if (I + 4 > T.size()) return false;
					const unsigned V = static_cast<unsigned>(std::stoul(T.substr(I, 4), nullptr, 16)); I += 4;
					if (V < 0x80) Out += static_cast<char>(V);
					else if (V < 0x800) { Out += static_cast<char>(0xC0 | (V >> 6)); Out += static_cast<char>(0x80 | (V & 0x3F)); }
					else { Out += static_cast<char>(0xE0 | (V >> 12)); Out += static_cast<char>(0x80 | ((V >> 6) & 0x3F)); Out += static_cast<char>(0x80 | (V & 0x3F)); }
					continue;
				}
				else C = E;
			}
			Out += C;
		}
		if (I >= T.size()) return false;
		++I; return true;
	}
	bool Value(Json& V)
	{
		if (++Depth > 32) return false;
		Ws();
		bool Ok = false;
		if (I >= T.size()) Ok = false;
		else if (T[I] == '{')
		{
			V.K = Json::Kind::Object; ++I; Ws();
			if (I < T.size() && T[I] == '}') { ++I; Ok = true; }
			else for (;;)
			{
				std::string Key; Json Item; Ws();
				if (!Str(Key)) break;
				Ws(); if (I >= T.size() || T[I] != ':') break; ++I;
				if (!Value(Item)) break;
				V.O.emplace_back(Key, Item); Ws();
				if (I < T.size() && T[I] == ',') { ++I; continue; }
				if (I < T.size() && T[I] == '}') { ++I; Ok = true; }
				break;
			}
		}
		else if (T[I] == '[')
		{
			V.K = Json::Kind::Array; ++I; Ws();
			if (I < T.size() && T[I] == ']') { ++I; Ok = true; }
			else for (;;)
			{
				Json Item; if (!Value(Item)) break;
				V.A.push_back(Item); Ws();
				if (I < T.size() && T[I] == ',') { ++I; continue; }
				if (I < T.size() && T[I] == ']') { ++I; Ok = true; }
				break;
			}
		}
		else if (T[I] == '"') { V.K = Json::Kind::String; Ok = Str(V.S); }
		else if (Lit("true")) { V.K = Json::Kind::Bool; V.B = true; Ok = true; }
		else if (Lit("false")) { V.K = Json::Kind::Bool; Ok = true; }
		else if (Lit("null")) { V.K = Json::Kind::Null; Ok = true; }
		else
		{
			const size_t S = I;
			while (I < T.size() && (T[I] == '-' || T[I] == '+' || T[I] == '.' || T[I] == 'e' || T[I] == 'E' || (T[I] >= '0' && T[I] <= '9'))) ++I;
			if (I > S)
			{
				// strtod, not std::stod: exceptions are off in Unreal targets (preflight P8). Same refusals: the whole token must
				// parse and must not overflow/underflow (std::stod threw out_of_range on ERANGE).
				const std::string Num = T.substr(S, I - S);
				char* End = nullptr;
				errno = 0;
				const double D = std::strtod(Num.c_str(), &End);
				if (End == Num.c_str() + Num.size() && errno != ERANGE) { V.K = Json::Kind::Number; V.N = D; Ok = true; }
			}
		}
		--Depth;
		return Ok;
	}
};

/** Whole-text parse; false on trailing garbage, depth > 32 or bodies over 64 KB. */
inline bool ParseJson(const std::string& Text, Json& Out)
{
	if (Text.size() > static_cast<size_t>(MaxBody)) return false;
	Reader R(Text);
	if (!R.Value(Out)) return false;
	R.Ws();
	return R.I == Text.size();
}

inline std::string Quote(const std::string& S)
{
	std::string O = "\"";
	for (unsigned char C : S)
	{
		if (C == '"' || C == '\\') { O += '\\'; O += static_cast<char>(C); }
		else if (C < 0x20) { char B[8]; std::snprintf(B, sizeof(B), "\\u%04x", C); O += B; }
		else O += static_cast<char>(C);
	}
	return O + "\"";
}

// ------------------------------------------------------------------ request
/** Builds the body, or returns false with Why for what the server would 400 (and for record ids that are not ids). */
inline bool BuildRequest(const std::vector<std::string>& Herbs, const std::vector<int>& Stages, const std::vector<std::string>& Records, std::string& Body, std::string& Why)
{
	Why.clear(); Body.clear();
	if (Herbs.size() < static_cast<size_t>(MinHerbs) || Herbs.size() > static_cast<size_t>(MaxHerbs)) { Why = "herbs must be 3 to 5"; return false; }
	for (const std::string& H : Herbs) if (!KnownHerb(H)) { Why = "unknown herb " + H; return false; }
	if (!Stages.empty() && Stages.size() != Herbs.size()) { Why = "stages must match herbs"; return false; }
	for (int S : Stages) if (S < MinStage || S > MaxStage) { Why = "stage out of range"; return false; }
	if (Records.size() > static_cast<size_t>(MaxRecords)) { Why = "too many records"; return false; }
	for (const std::string& R : Records)
	{
		bool Id = !R.empty() && R.size() <= 128;
		for (char C : R) Id = Id && ((C >= 'A' && C <= 'Z') || (C >= 'a' && C <= 'z') || (C >= '0' && C <= '9') || C == '_');
		if (!Id) { Why = "record id"; return false; }
	}
	Body = "{\"herbs\":[";
	for (size_t I = 0; I < Herbs.size(); ++I) Body += (I ? "," : "") + Quote(Herbs[I]);
	Body += "]";
	if (!Stages.empty()) { Body += ",\"stages\":["; for (size_t I = 0; I < Stages.size(); ++I) Body += (I ? "," : "") + std::to_string(Stages[I]); Body += "]"; }
	if (!Records.empty()) { Body += ",\"records\":["; for (size_t I = 0; I < Records.size(); ++I) Body += (I ? "," : "") + Quote(Records[I]); Body += "]"; }
	Body += "}";
	return true;
}

// ------------------------------------------------------------------ response
struct Result
{
	bool Ok = false; int Status = 0; std::string Error;
	std::string Item, Contour, Quality, Effect, FoundTune, FoundTuneBonus, RecordId, Why;
	bool Cadence = false; int Tier = 0; double Magnitude = 0, DurationS = 0; std::vector<int> Notes;
	bool HasFoundTune() const { return !FoundTune.empty(); }
};

/** What a non-200 means to the player and the log (403 = this host is not the configured engine subject). */
inline const char* StatusMeaning(int Status)
{
	switch (Status)
	{
	case 200: return "ok";
	case 400: return "bad_input";
	case 401: return "unauthenticated";
	case 403: return "not_the_host";
	case 429: return "rate_limited";
	default: return Status >= 500 ? "server_error" : "unexpected";
	}
}

inline bool Field(const Json& O, const char* K, std::string& Out, bool Nullable)
{
	const Json* V = O.Get(K);
	if (!V) return false;
	if (V->K == Json::Kind::Null) { Out.clear(); return Nullable; }
	if (V->K != Json::Kind::String) return false;
	Out = V->S; return true;
}

/** Parses a reply; anything but a well-formed 200 body is Ok=false with Error set. */
inline Result Parse(int Status, const std::string& Text)
{
	Result R; R.Status = Status;
	if (Status != 200) { R.Error = std::string("HTTP ") + std::to_string(Status) + " " + StatusMeaning(Status); return R; }
	Json J;
	if (!ParseJson(Text, J) || J.K != Json::Kind::Object) { R.Error = "malformed body"; return R; }
	const Json* C = J.Get("cadence"); const Json* T = J.Get("tier"); const Json* M = J.Get("magnitude"); const Json* D = J.Get("durationS"); const Json* N = J.Get("notes");
	bool Ok = Field(J, "item", R.Item, false) && Field(J, "contour", R.Contour, false) && Field(J, "quality", R.Quality, false) && Field(J, "effect", R.Effect, false) &&
		Field(J, "foundTune", R.FoundTune, true) && Field(J, "foundTuneBonus", R.FoundTuneBonus, true) && Field(J, "recordId", R.RecordId, true) && Field(J, "why", R.Why, true) &&
		C && C->K == Json::Kind::Bool && T && T->K == Json::Kind::Number && M && M->K == Json::Kind::Number && D && D->K == Json::Kind::Number && N && N->K == Json::Kind::Array;
	if (Ok)
	{
		R.Cadence = C->B; R.Tier = static_cast<int>(T->N); R.Magnitude = M->N; R.DurationS = D->N;
		for (const Json& E : N->A) { if (E.K != Json::Kind::Number) { Ok = false; break; } R.Notes.push_back(static_cast<int>(E.N)); }
	}
	if (!Ok || R.Item.empty() || R.Tier < 0 || R.Tier > 4) { R = Result(); R.Status = Status; R.Error = "body does not match brew-melody-v1"; return R; }
	R.Ok = true;
	return R;
}

}} // namespace daedalus::brewmelody