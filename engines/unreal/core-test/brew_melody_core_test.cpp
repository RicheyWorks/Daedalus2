// SPDX-License-Identifier: MIT
// G25 brew-melody client core, checked without Unreal against docs/contracts/brew-melody-v1/http-cases.json. Build (MSVC):
//   cl /nologo /EHsc /std:c++17 /W4 /WX /I..\DaedalusLink\Source\DaedalusLink\Public brew_melody_core_test.cpp
// or g++ -std=c++17 -O1 -Wall -Wextra -Werror -I../DaedalusLink/Source/DaedalusLink/Public brew_melody_core_test.cpp
// Run from this folder.
#ifndef _CRT_SECURE_NO_WARNINGS
#define _CRT_SECURE_NO_WARNINGS 1
#endif
#include "DaedalusBrewMelodyCore.h"
#include <cstdio>
#include <fstream>
#include <sstream>
using namespace daedalus::brewmelody;
static int Passed = 0, Total = 0;
static void Check(const std::string& Name, bool OK) { ++Total; Passed += OK; std::printf("%s %s\n", OK ? "PASS" : "FAIL", Name.c_str()); }

static std::vector<std::string> Strings(const Json* A) { std::vector<std::string> O; if (A) for (const Json& E : A->A) O.push_back(E.S); return O; }
static std::vector<int> Ints(const Json* A) { std::vector<int> O; if (A) for (const Json& E : A->A) O.push_back(static_cast<int>(E.N)); return O; }

/** Re-serialises a parsed value, so a case's "response" object can be fed to Parse() as the server would send it. */
static std::string Dump(const Json& V)
{
	switch (V.K)
	{
	case Json::Kind::Null: return "null";
	case Json::Kind::Bool: return V.B ? "true" : "false";
	case Json::Kind::Number: { char B[32]; std::snprintf(B, sizeof(B), "%.17g", V.N); return B; }
	case Json::Kind::String: return Quote(V.S);
	case Json::Kind::Array: { std::string S = "["; for (size_t I = 0; I < V.A.size(); ++I) S += (I ? "," : "") + Dump(V.A[I]); return S + "]"; }
	default: { std::string S = "{"; for (size_t I = 0; I < V.O.size(); ++I) S += (I ? "," : "") + Quote(V.O[I].first) + ":" + Dump(V.O[I].second); return S + "}"; }
	}
}

int main()
{
	std::ifstream In("../../../docs/contracts/brew-melody-v1/http-cases.json", std::ios::binary);
	std::stringstream SS; SS << In.rdbuf();
	Json Cases;
	Check("http-cases.json parses", ParseJson(SS.str(), Cases) && Cases.K == Json::Kind::Array && Cases.A.size() >= 4);
	for (const Json& C : Cases.A)
	{
		const std::string Name = C.Get("name") ? C.Get("name")->S : "?";
		const int Status = static_cast<int>(C.Get("status")->N);
		const Json* Rq = C.Get("request");
		std::string Body, Why;
		const bool Built = BuildRequest(Strings(Rq->Get("herbs")), Ints(Rq->Get("stages")), Strings(Rq->Get("records")), Body, Why);
		if (Status == 400) { Check(Name + ": client refuses before sending (" + Why + ")", !Built && !Why.empty()); continue; }
		Json Back;
		Check(Name + ": request round-trips", Built && ParseJson(Body, Back) && Dump(Back) == Dump(*Rq));
		if (Status != 200) { const Result R = Parse(Status, ""); Check(Name + ": " + std::to_string(Status) + " is an error", !R.Ok && R.Error.find(StatusMeaning(Status)) != std::string::npos); continue; }
		const Json& E = *C.Get("response");
		const Result R = Parse(200, Dump(E));
		bool Same = R.Ok && R.Item == E.Get("item")->S && R.Cadence == E.Get("cadence")->B && R.Contour == E.Get("contour")->S && R.Quality == E.Get("quality")->S &&
			R.Tier == static_cast<int>(E.Get("tier")->N) && R.Effect == E.Get("effect")->S && R.Magnitude == E.Get("magnitude")->N && R.DurationS == E.Get("durationS")->N &&
			R.Notes == Ints(E.Get("notes")) && R.HasFoundTune() == (E.Get("foundTune")->K == Json::Kind::String) &&
			(!R.HasFoundTune() || (R.FoundTune == E.Get("foundTune")->S && R.FoundTuneBonus == E.Get("foundTuneBonus")->S && R.RecordId == E.Get("recordId")->S));
		Check(Name + ": 200 body parses field for field", Same);
	}
	std::string Body, Why;
	Check("unknown herb refused", !BuildRequest({ "Doleaf", "Mimint", "Nettle" }, {}, {}, Body, Why) && Why == "unknown herb Nettle");
	Check("all twelve canon herbs accepted, any case (server pitchOf)", BuildRequest({ "Sharpcress", "Flatfern", "Hushmoss" }, {}, {}, Body, Why) && BuildRequest({ "Gloryroot", "Dronebloom", "tisquill" }, {}, {}, Body, Why) && Body == "{\"herbs\":[\"Gloryroot\",\"Dronebloom\",\"tisquill\"]}");
	Check("stage 5 refused", !BuildRequest({ "Doleaf", "Mimint", "Solthorn" }, { 1, 2, 5 }, {}, Body, Why));
	Check("stages must match herbs", !BuildRequest({ "Doleaf", "Mimint", "Solthorn" }, { 1, 2 }, {}, Body, Why));
	Check("six herbs refused", !BuildRequest({ "Doleaf", "Doleaf", "Doleaf", "Doleaf", "Doleaf", "Doleaf" }, {}, {}, Body, Why));
	Check("record id must be an id", !BuildRequest({ "Doleaf", "Mimint", "Solthorn" }, {}, { "x\",\"y" }, Body, Why));
	Check("malformed body is an error", !Parse(200, "{\"item\":").Ok && !Parse(200, "[]").Ok && !Parse(200, "{} x").Ok);
	Check("missing field is an error", !Parse(200, "{\"item\":\"I\",\"cadence\":true}").Ok);
	Check("deep nesting refused", !Parse(200, std::string(40, '[') + std::string(40, ']')).Ok);
	Check("statuses named", std::string(StatusMeaning(403)) == "not_the_host" && std::string(StatusMeaning(429)) == "rate_limited" && std::string(StatusMeaning(503)) == "server_error");
	std::printf("%d/%d passed\n", Passed, Total);
	return Passed == Total ? 0 : 1;
}