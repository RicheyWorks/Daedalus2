// SPDX-License-Identifier: MIT
// TONIC 1 (docs/contracts/tonic-v1): the C++ request writer, reply parser, trough and effect ledger agree with the Java
// fixtures, checked without Unreal.
//   g++ -std=c++17 -O1 -Wall -Wextra -Werror -fsanitize=address,undefined -I../DaedalusLink/Source/DaedalusLink/Public tonic_core_test.cpp -o tonic_core_test && ./tonic_core_test ../../../docs/contracts/tonic-v1
#include "DaedalusTonicCore.h"
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <limits>
using namespace daedalus::tonic;
static int Passed = 0, Total = 0;
static void Check(const char* Name, bool OK) { ++Total; Passed += OK; std::printf("%s %s\n", OK ? "PASS" : "FAIL", Name); }
static std::string Slurp(const std::string& Path)
{
	std::ifstream In(Path, std::ios::binary); std::string S((std::istreambuf_iterator<char>(In)), std::istreambuf_iterator<char>()); return S;
}
static bool Refuses(const std::string& S, const char* Needle) { Brew B; Result R = Parse(S, B); return !R.Ok && R.Error.find(Needle) != std::string::npos && B.RecipeId.empty() && B.Mods.empty(); }
static const std::string Head = "TONIC 1\nbrew tonic_x 1.0 120 0 overTime 0.0\n";

int main(int Argc, char** Argv)
{
	const std::string Dir = Argc > 1 ? Argv[1] : "../../../docs/contracts/tonic-v1";

	// ---- request: byte-exact against the Java fixture ----
	{
		std::string Req; Drinker D; D.Kind = "cane_corso";
		Result R = BuildRequest({"Barkbalm"}, D, 0, Req);
		std::string Want = Slurp(Dir + "/barkbalm-request.json");
		while (!Want.empty() && (Want.back() == '\n' || Want.back() == '\r')) { Want.pop_back(); }
		Check("request is byte-exact with barkbalm-request.json", R.Ok && Want.size() > 10 && Req == Want);
		Drinker S; S.Coat = "Labyrinth"; S.Kind = "packMember"; S.Stage = 3; S.Charm = true;
		BuildRequest({"Dewclaw", "Pawmint", "Barkbalm"}, S, std::numeric_limits<int64_t>::max(), Req);
		Check("int64 max seed stays exact", Req == "{\"herbs\":[\"Dewclaw\",\"Pawmint\",\"Barkbalm\"],\"coat\":\"Labyrinth\",\"drinker\":\"packMember\",\"stage\":3,\"charm\":true,\"seed\":9223372036854775807}");
		BuildRequest({"Barkbalm"}, D, std::numeric_limits<int64_t>::min(), Req);
		Check("int64 min seed stays exact", Req.find("\"seed\":-9223372036854775808}") != std::string::npos);
		Check("refuses 0 herbs", !BuildRequest({}, D, 0, Req).Ok && Req.empty());
		Check("refuses 4 herbs", !BuildRequest({"A", "B", "C", "D"}, D, 0, Req).Ok);
		Check("refuses duplicate herb", !BuildRequest({"Barkbalm", "Barkbalm"}, D, 0, Req).Ok);
		Check("refuses a herb name with a quote", !BuildRequest({"Bark\"balm"}, D, 0, Req).Ok);
		Drinker Bad = D; Bad.Coat = "Plaid";
		Check("refuses unknown coat", !BuildRequest({"Barkbalm"}, Bad, 0, Req).Ok);
		Bad = D; Bad.Kind = "dragon";
		Check("refuses unknown drinker", !BuildRequest({"Barkbalm"}, Bad, 0, Req).Ok);
		Bad = D; Bad.Stage = 4;
		Check("refuses stage 4", !BuildRequest({"Barkbalm"}, Bad, 0, Req).Ok);
	}

	// ---- reply: the two Java fixtures ----
	{
		Brew B; Result R = Parse(Slurp(Dir + "/barkbalm.tonic"), B);
		Check("reads barkbalm.tonic", R.Ok && B.RecipeId == "tonic_barkbalm" && B.Factor == 1.0 && B.DurationSec == 120 && !B.SecondRoll
			&& B.Kind == Mode::OverTime && B.BreedChancePct == 0.0 && B.Mods.size() == 1 && B.Mods[0].Stat == "hearts" && !B.Mods[0].Mul && B.Mods[0].Value == 1.0 && B.Grants.empty());
		R = Parse(Slurp(Dir + "/swim.tonic"), B);
		Check("reads swim.tonic with 2 mods and 2 grants in order", R.Ok && B.Mods.size() == 2 && B.Mods[1].Stat == "cooldownPct" && B.Mods[1].Value == -0.05
			&& B.Grants.size() == 2 && B.Grants[0] == "swim" && B.Grants[1] == "livestockWaterCross");
	}

	// ---- reply: refusals (all-or-nothing) ----
	Check("refuses TONIC 2", Refuses("TONIC 2\n", "line 1"));
	Check("refuses empty reply", Refuses("", "line 1"));
	Check("refuses missing end", Refuses(Head + "mod hearts add 1.0\n", "missing end"));
	Check("refuses content after end", Refuses(Head + "end\nmod hearts add 1.0\n", "after end"));
	Check("refuses a second brew line", Refuses(Head + "brew tonic_y 1.0 1 0 pulse 0.0\nend\n", "second brew"));
	Check("refuses mod after grant", Refuses(Head + "grant swim\nmod hearts add 1.0\nend\n", "mod after grant"));
	Check("refuses unknown record", Refuses(Head + "heal 5\nend\n", "unknown record"));
	Check("refuses a double space", Refuses("TONIC 1\nbrew tonic_x  1.0 120 0 overTime 0.0\nend\n", "double space"));
	Check("refuses a bare CR", Refuses("TONIC 1\r\n", "LF/ASCII"));
	Check("refuses non-ASCII", Refuses(Head + "grant sw\xC3\xAFm\nend\n", "LF/ASCII"));
	Check("refuses NaN value", Refuses(Head + "mod hearts add nan\nend\n", "mod value"));
	Check("refuses inf value", Refuses(Head + "mod hearts add inf\nend\n", "mod value"));
	Check("refuses a comma decimal", Refuses(Head + "mod hearts add 1,5\nend\n", "mod value"));
	Check("refuses factor 2.5", Refuses("TONIC 1\nbrew tonic_x 2.5 120 0 overTime 0.0\nend\n", "factor"));
	Check("refuses negative duration", Refuses("TONIC 1\nbrew tonic_x 1.0 -1 0 overTime 0.0\nend\n", "duration"));
	Check("refuses secondRoll 2", Refuses("TONIC 1\nbrew tonic_x 1.0 120 2 overTime 0.0\nend\n", "secondRoll"));
	Check("refuses unknown mode", Refuses("TONIC 1\nbrew tonic_x 1.0 120 0 forever 0.0\nend\n", "mode"));
	Check("refuses breed 100.5", Refuses("TONIC 1\nbrew tonic_x 1.0 120 0 overTime 100.5\nend\n", "breed"));
	Check("refuses op set", Refuses(Head + "mod hearts set 1.0\nend\n", "add or mul"));
	Check("refuses a 65 char identifier", Refuses(Head + "mod " + std::string(65, 'a') + " add 1.0\nend\n", "bad stat"));
	{
		std::string Many = Head; for (int I = 0; I < 33; ++I) { Many += "mod hearts add 1.0\n"; } Many += "end\n";
		Check("refuses 33 mods", Refuses(Many, "more than 32 mods"));
		std::string Ok32 = Head; for (int I = 0; I < 32; ++I) { Ok32 += "mod hearts add 1.0\n"; } Ok32 += "end\n";
		Brew B; Check("accepts exactly 32 mods", Parse(Ok32, B).Ok && B.Mods.size() == 32);
		std::string Gr = Head; for (int I = 0; I < 33; ++I) { Gr += "grant g" + std::to_string(I) + "\n"; } Gr += "end\n";
		Check("refuses 33 grants", Refuses(Gr, "more than 32 grants"));
		std::string Big = Head; for (int I = 0; I < 700; ++I) { Big += "grant a\n"; } Big += "end\n";
		Check("refuses a reply over 4096 bytes", Refuses(Big, "4096"));
		Check("refuses a 513 byte line", Refuses(Head + "grant " + std::string(507, 'a') + "\nend\n", "512"));
	}
	{
		Brew B;
		Check("accepts Java exponent form 5.0E-4", Parse(Head + "mod hearts add 5.0E-4\nend\n", B).Ok && B.Mods[0].Value == 5.0e-4);
		Check("accepts pulse and breed chance", Parse("TONIC 1\nbrew tonic_bond 1.25 0 1 pulse 20.0\nmod loyalty add 6.25\nend\n", B).Ok
			&& B.Kind == Mode::Pulse && B.SecondRoll && B.BreedChancePct == 20.0 && B.DurationSec == 0);
		Check("accepts a mul op", Parse(Head + "mod speed mul 1.1\nend\n", B).Ok && B.Mods[0].Mul);
	}

	// ---- seed ----
	{
		Check("seed is deterministic", DeriveSeed("Brew_W9_Trough_3", 1, 1) == DeriveSeed("Brew_W9_Trough_3", 1, 1));
		Check("seed changes per drink", DeriveSeed("Brew_W9_Trough_3", 1, 1) != DeriveSeed("Brew_W9_Trough_3", 1, 2));
		Check("seed changes per steep", DeriveSeed("Brew_W9_Trough_3", 1, 1) != DeriveSeed("Brew_W9_Trough_3", 2, 1));
		Check("seed changes per trough", DeriveSeed("Brew_W9_Trough_3", 1, 1) != DeriveSeed("W9_Trough_3", 1, 1));
		int Neg = 0; for (uint32_t I = 0; I < 200; ++I) { if (DeriveSeed("t", 1, I) < 0) { ++Neg; } }
		Check("seeds use the full signed range", Neg > 60 && Neg < 140);
	}

	// ---- drinker from tags ----
	{
		Drinker C = DrinkerFromTags({"AMF_Pets", "AMF_Companion", "Coat_Stripes", "Stage_2"}, "AMF_Companion_CaneCorso");
		Check("Corso is cane_corso, Stripes, stage 2", C.Kind == "cane_corso" && C.Coat == "Stripes" && C.Stage == 2 && !C.Charm);
		Drinker P = DrinkerFromTags({"AMF_Companion", "Pack_Member", "Coat_Labyrinth", "Stage_3", "Tonic_Charm"}, "AMF_Camp_CorsoPup");
		Check("pack member with charm, Labyrinth, stage 3", P.Kind == "packMember" && P.Coat == "Labyrinth" && P.Stage == 3 && P.Charm);
		Drinker W = DrinkerFromTags({"AMF_Wild", "AMF_B_Meadow"}, "AMF_Meadow_Sheep_1");
		Check("a wild animal is other, None, stage 1", W.Kind == "other" && W.Coat == "None" && W.Stage == 1);
		Check("the Cane_Corso tag works in a packaged build (no label)", DrinkerFromTags({"AMF_Companion", "Cane_Corso"}, "StaticMeshActor_7").Kind == "cane_corso");
		Check("Cane_Corso without AMF_Companion is not the Corso", DrinkerFromTags({"Cane_Corso"}, "x").Kind == "other");
		Check("a CaneCorso label without AMF_Companion is not the Corso", DrinkerFromTags({"AMF_Wild"}, "AMF_X_CaneCorso").Kind == "other");
		std::string H;
		Check("herb tag Tonic_Herb_Barkbalm", HerbFromTag("Tonic_Herb_Barkbalm", H) && H == "Barkbalm");
		Check("Tonic_Herb_ alone is not a herb", !HerbFromTag("Tonic_Herb_", H));
		Check("Tonic_Role_base is not a herb", !HerbFromTag("Tonic_Role_base", H));
	}

	// ---- origin ----
	Check("https host ok", OriginAllowed("https://game.example.com"));
	Check("loopback http with port ok", OriginAllowed("http://127.0.0.1:8088"));
	Check("remote http refused", !OriginAllowed("http://game.example.com"));
	Check("localhost name over http refused", !OriginAllowed("http://localhost:8088"));
	Check("no scheme refused", !OriginAllowed("127.0.0.1:8088"));
	Check("port 0 refused", !OriginAllowed("https://a.b:0"));
	Check("port 70000 refused", !OriginAllowed("https://a.b:70000"));
	Check("path in origin refused", !OriginAllowed("https://a.b/x"));
	Check("empty label refused", !OriginAllowed("https://a..b"));

	// ---- trough: gather -> steep -> 3 drinks -> plain ----
	{
		Trough T; double Now = 100;
		Check("starts empty", T.PhaseNow(Now) == Phase::Empty);
		Check("cannot steep when empty", !T.BeginSteep(Now));
		Check("deposits Barkbalm", T.Deposit("Barkbalm", Now) && T.PhaseNow(Now) == Phase::Gathering);
		Check("refuses the same herb twice", !T.Deposit("Barkbalm", Now));
		Check("deposits Pawmint and Furfern", T.Deposit("Pawmint", Now) && T.Deposit("Furfern", Now));
		Check("refuses a 4th herb", !T.Deposit("Dewclaw", Now) && T.HerbCount() == 3);
		Check("steep starts", T.BeginSteep(Now) && T.PhaseNow(Now) == Phase::Steeping);
		Check("herbs locked while steeping", !T.Deposit("Dewclaw", Now));
		T.SteepRefused();
		Check("a refusal keeps the herbs", T.PhaseNow(Now) == Phase::Gathering && T.HerbCount() == 3);
		T.BeginSteep(Now); T.SteepDone("tonic_mend", Now);
		Check("steeped with 3 drinks", T.PhaseNow(Now) == Phase::Steeped && T.DrinksLeft(Now) == 3 && T.RecipeId() == "tonic_mend" && T.Steeps() == 1);
		uint32_t O1 = 0, O2 = 0, O3 = 0, O4 = 0;
		Check("drink 1 ordinal 1", T.ReserveDrink(Now, O1) && O1 == 1 && T.DrinksLeft(Now) == 2);
		T.RefundDrink(Now);
		Check("a refused drink is refunded", T.DrinksLeft(Now) == 3);
		Check("drinks 1..3 reserve", T.ReserveDrink(Now, O1) && T.ReserveDrink(Now, O2) && T.ReserveDrink(Now, O3) && O2 == O1 + 1 && O3 == O2 + 1);
		Check("the 4th drink is refused", !T.ReserveDrink(Now, O4));
		Check("last reserved drink can still be refunded before it settles", (T.RefundDrink(Now), T.DrinksLeft(Now) == 1));
		T.ReserveDrink(Now, O4); T.ConfirmDrink(Now); T.ConfirmDrink(Now); T.ConfirmDrink(Now);
		Check("3 confirmed drinks make the trough plain", T.PhaseNow(Now) == Phase::Empty && T.HerbCount() == 0);
	}
	{
		Trough T; double Now = 0; uint32_t O = 0;
		T.Deposit("Dozeleaf", Now); T.BeginSteep(Now); T.SteepDone("tonic_calm", Now);
		Check("still drinkable at 599 s", T.ReserveDrink(599, O));
		T.ConfirmDrink(599);
		Check("flat at 600 s", T.PhaseNow(600) == Phase::Empty && !T.ReserveDrink(600, O));
		Check("a flat trough takes new herbs", T.Deposit("Barkbalm", 601));
	}

	// ---- ledger ----
	{
		Ledger L; Brew B; Parse(Slurp(Dir + "/swim.tonic"), B);
		Check("starts with no effects", L.Count() == 0 && L.Stat("hearts", 3.0, 0) == 3.0);
		std::vector<Mod> One = L.Apply(B, 10);
		Check("overTime returns no one-shot mods", One.empty() && L.Count() == 1);
		Check("hearts add 1 on base 3", L.Stat("hearts", 3.0, 11) == 4.0);
		Check("cooldownPct add -0.05", std::fabs(L.Stat("cooldownPct", 0.0, 11) + 0.05) < 1e-12);
		Check("swim grant active, unknown grant not", L.HasGrant("swim", 11) && !L.HasGrant("fly", 11));
		Check("recipe active until 130 s", L.Active(B.RecipeId, 129) && !L.Active(B.RecipeId, 130));
		L.Apply(B, 100);
		Check("a second drink refreshes, never stacks", L.Count() == 1 && L.Stat("hearts", 3.0, 101) == 4.0);
		Check("not expired at 219", L.Expire(219).empty());
		std::vector<std::string> Gone = L.Expire(220);
		Check("expires at 220 and reports it", Gone.size() == 1 && Gone[0] == B.RecipeId && L.Count() == 0 && L.Stat("hearts", 3.0, 221) == 3.0 && !L.HasGrant("swim", 221));
		Brew M; Parse("TONIC 1\nbrew tonic_dash 1.0 0 0 pulse 0.0\nmod speed mul 1.1\nend\n", M);
		std::vector<Mod> Pulse = L.Apply(M, 0);
		Check("pulse hands back its mods once and keeps nothing", Pulse.size() == 1 && Pulse[0].Mul && L.Count() == 0);
		Brew S1, S2; Parse("TONIC 1\nbrew tonic_a 1.0 60 0 overTime 0.0\nmod speed mul 1.1\nmod hearts add 1.0\nend\n", S1);
		Parse("TONIC 1\nbrew tonic_b 1.0 60 0 overTime 20.0\nmod speed mul 1.2\nend\n", S2);
		L.Apply(S1, 0); L.Apply(S2, 0);
		Check("two different tonics stack: (base+add)*mul*mul", std::fabs(L.Stat("speed", 5.0, 1) - 5.0 * 1.1 * 1.2) < 1e-9 && L.Stat("hearts", 1.0, 1) == 2.0);
		Check("breed chance is the best active one", L.BreedChancePct(1) == 20.0 && L.BreedChancePct(61) == 0.0);
	}

	std::printf("%d/%d passed\n", Passed, Total);
	return Passed == Total ? 0 : 1;
}