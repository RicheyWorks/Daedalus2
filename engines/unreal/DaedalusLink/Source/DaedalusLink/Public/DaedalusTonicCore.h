// SPDX-License-Identifier: MIT
// TONIC 1 (Kennel Isle trough tonics): the Unreal side of docs/contracts/tonic-v1, plain C++17, no Unreal types.
// Java (TonicBrewer + KennelController, POST /api/v1/kennel/brew) does the calculation; this header
//   1. writes the JSON request (exact signed 64-bit seed, no floating point),
//   2. reads the multiline TONIC 1 reply all-or-nothing, with the contract's native bounds,
//   3. models the trough (herbs, steep, 3 drinks / 10 min decay) and the per-pet effect ledger.
// Authority stays with the Java host: this code never invents a brew or a modifier.
#pragma once
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <locale>
#include <sstream>
#include <string>
#include <vector>

namespace daedalus { namespace tonic {

// ---- contract bounds (docs/contracts/tonic-v1/README.md) ----
constexpr size_t MaxBytes = 4096, MaxLineBytes = 512, MaxIdent = 64, MaxMods = 32, MaxGrants = 32;
constexpr int MaxHerbs = 3;           // tonics.json vessel.maxHerbs
constexpr int DecayDrinks = 3;        // tonics.json vessel.decay.drinks
constexpr double DecaySeconds = 600;  // tonics.json vessel.decay.minutes (10) in seconds

struct Result { bool Ok = false; std::string Error; };
inline Result Fail(const std::string& Why) { Result R; R.Error = Why; return R; }
inline Result Pass() { Result R; R.Ok = true; return R; }

inline bool IsIdent(const std::string& S)
{
	if (S.empty() || S.size() > MaxIdent) { return false; }
	for (char C : S)
	{
		const bool Ok = (C >= 'a' && C <= 'z') || (C >= 'A' && C <= 'Z') || (C >= '0' && C <= '9') || C == '_';
		if (!Ok) { return false; }
	}
	return true;
}

// ---- request: one JSON object, field order and spelling as docs/contracts/tonic-v1/barkbalm-request.json ----
inline bool CoatOk(const std::string& S) { return S == "None" || S == "Spots" || S == "Stripes" || S == "Labyrinth"; }
inline bool DrinkerOk(const std::string& S) { return S == "cane_corso" || S == "packMember" || S == "other"; }

struct Drinker { std::string Coat = "None"; std::string Kind = "other"; int Stage = 1; bool Charm = false; };

inline Result BuildRequest(const std::vector<std::string>& Herbs, const Drinker& D, int64_t Seed, std::string& Out)
{
	Out.clear();
	if (Herbs.empty() || Herbs.size() > (size_t)MaxHerbs) { return Fail("herbs must be 1..3"); }
	for (size_t I = 0; I < Herbs.size(); ++I)
	{
		if (!IsIdent(Herbs[I])) { return Fail("bad herb name"); }
		for (size_t J = 0; J < I; ++J) { if (Herbs[J] == Herbs[I]) { return Fail("duplicate herb"); } }
	}
	if (!CoatOk(D.Coat)) { return Fail("unknown coat"); }
	if (!DrinkerOk(D.Kind)) { return Fail("unknown drinker"); }
	if (D.Stage < 1 || D.Stage > 3) { return Fail("stage must be 1..3"); }
	std::string S = "{\"herbs\":[";
	for (size_t I = 0; I < Herbs.size(); ++I) { if (I) { S += ','; } S += '"' + Herbs[I] + '"'; }
	S += "],\"coat\":\"" + D.Coat + "\",\"drinker\":\"" + D.Kind + "\",\"stage\":" + std::to_string(D.Stage)
		+ ",\"charm\":" + (D.Charm ? "true" : "false") + ",\"seed\":" + std::to_string((long long)Seed) + "}";
	Out = S;
	return Pass();
}

// ---- reply ----
enum class Mode { OverTime, Pulse };
struct Mod { std::string Stat; bool Mul = false; double Value = 0; };
struct Brew
{
	std::string RecipeId; double Factor = 0; int DurationSec = 0; bool SecondRoll = false;
	Mode Kind = Mode::OverTime; double BreedChancePct = 0;
	std::vector<Mod> Mods; std::vector<std::string> Grants;
};

namespace detail {
inline bool Decimal(const std::string& T, double& Out)
{
	// -?digits[.digits][e[+-]digits]; Java's Double.toString may print 5.0E-4 for tiny values.
	size_t I = 0; const size_t N = T.size();
	if (I < N && T[I] == '-') { ++I; }
	size_t Digits = 0; while (I < N && T[I] >= '0' && T[I] <= '9') { ++I; ++Digits; }
	if (!Digits) { return false; }
	if (I < N && T[I] == '.') { ++I; size_t Frac = 0; while (I < N && T[I] >= '0' && T[I] <= '9') { ++I; ++Frac; } if (!Frac) { return false; } }
	if (I < N && (T[I] == 'e' || T[I] == 'E'))
	{
		++I; if (I < N && (T[I] == '+' || T[I] == '-')) { ++I; }
		size_t Exp = 0; while (I < N && T[I] >= '0' && T[I] <= '9') { ++I; ++Exp; }
		if (!Exp) { return false; }
	}
	if (I != N) { return false; }
	std::istringstream In(T); In.imbue(std::locale::classic());
	double V = 0; In >> V;
	if (In.fail() || !std::isfinite(V)) { return false; }
	Out = V; return true;
}
inline bool Whole(const std::string& T, long long Max, long long& Out)
{
	if (T.empty() || T.size() > 9) { return false; }
	long long V = 0;
	for (char C : T) { if (C < '0' || C > '9') { return false; } V = V * 10 + (C - '0'); }
	if (V > Max) { return false; }
	Out = V; return true;
}
inline std::vector<std::string> Split(const std::string& Line, bool& Clean)
{
	std::vector<std::string> Out; std::string Cur; Clean = true;
	for (char C : Line)
	{
		if (C == ' ') { if (Cur.empty()) { Clean = false; } Out.push_back(Cur); Cur.clear(); } else { Cur += C; }
	}
	if (Cur.empty()) { Clean = false; }
	Out.push_back(Cur);
	return Out;
}
inline Result Line(int N, const std::string& Why) { return Fail("line " + std::to_string(N) + ": " + Why); }
}

// All-or-nothing: on any error Out is left empty and nothing may be applied.
inline Result Parse(const std::string& Text, Brew& Out)
{
	Out = Brew();
	if (Text.size() > MaxBytes) { return Fail("reply over 4096 bytes"); }
	for (char C : Text) { if (C != '\n' && (C < 0x20 || C > 0x7E)) { return Fail("reply is not LF/ASCII"); } }
	std::vector<std::string> Lines; { std::string Cur; for (char C : Text) { if (C == '\n') { Lines.push_back(Cur); Cur.clear(); } else { Cur += C; } } if (!Cur.empty()) { Lines.push_back(Cur); } }
	for (const std::string& L : Lines) { if (L.size() > MaxLineBytes) { return Fail("line over 512 bytes"); } }
	if (Lines.empty() || Lines[0] != "TONIC 1") { return detail::Line(1, "expected 'TONIC 1'"); }
	Brew B; bool SawBrew = false, SawEnd = false, SawGrant = false;
	for (size_t I = 1; I < Lines.size(); ++I)
	{
		const int N = (int)I + 1; const std::string& L = Lines[I];
		if (SawEnd) { return detail::Line(N, "content after end"); }
		bool Clean = true; const std::vector<std::string> T = detail::Split(L, Clean);
		if (!Clean) { return detail::Line(N, "empty field or double space"); }
		if (T[0] == "brew")
		{
			if (SawBrew) { return detail::Line(N, "second brew line"); }
			if (T.size() != 7) { return detail::Line(N, "brew needs 6 fields"); }
			long long Dur = 0, Roll = 0; double Factor = 0, Breed = 0;
			if (!detail::Decimal(T[2], Factor) || Factor < 0 || Factor > 2) { return detail::Line(N, "factor must be 0..2"); }
			if (!detail::Whole(T[3], 1000000, Dur)) { return detail::Line(N, "bad duration"); }
			if (!detail::Whole(T[4], 1, Roll)) { return detail::Line(N, "secondRoll must be 0 or 1"); }
			if (!detail::Decimal(T[6], Breed) || Breed < 0 || Breed > 100) { return detail::Line(N, "breed chance must be 0..100"); }
			if (!IsIdent(T[1])) { return detail::Line(N, "bad recipe id"); }
			if (T[5] == "overTime") { B.Kind = Mode::OverTime; } else if (T[5] == "pulse") { B.Kind = Mode::Pulse; } else { return detail::Line(N, "unknown mode"); }
			B.RecipeId = T[1]; B.Factor = Factor; B.DurationSec = (int)Dur; B.SecondRoll = Roll == 1; B.BreedChancePct = Breed; SawBrew = true;
		}
		else if (T[0] == "mod")
		{
			if (!SawBrew) { return detail::Line(N, "mod before brew"); }
			if (SawGrant) { return detail::Line(N, "mod after grant"); }
			if (T.size() != 4) { return detail::Line(N, "mod needs 3 fields"); }
			if (B.Mods.size() >= MaxMods) { return detail::Line(N, "more than 32 mods"); }
			Mod M; double V = 0;
			if (!IsIdent(T[1])) { return detail::Line(N, "bad stat"); }
			if (T[2] != "add" && T[2] != "mul") { return detail::Line(N, "op must be add or mul"); }
			if (!detail::Decimal(T[3], V)) { return detail::Line(N, "bad mod value"); }
			M.Stat = T[1]; M.Mul = T[2] == "mul"; M.Value = V; B.Mods.push_back(M);
		}
		else if (T[0] == "grant")
		{
			if (!SawBrew) { return detail::Line(N, "grant before brew"); }
			if (T.size() != 2 || !IsIdent(T[1])) { return detail::Line(N, "grant needs one ability name"); }
			if (B.Grants.size() >= MaxGrants) { return detail::Line(N, "more than 32 grants"); }
			B.Grants.push_back(T[1]); SawGrant = true;
		}
		else if (T[0] == "end")
		{
			if (T.size() != 1) { return detail::Line(N, "end takes no fields"); }
			if (!SawBrew) { return detail::Line(N, "end before brew"); }
			SawEnd = true;
		}
		else { return detail::Line(N, "unknown record '" + T[0].substr(0, 16) + "'"); }
	}
	if (!SawEnd) { return Fail("missing end"); }
	Out = B; return Pass();
}

// ---- host-chosen seed: deterministic, 64-bit, from the trough key + steep number + drink number ----
inline uint64_t Mix64(uint64_t Z)
{
	Z += 0x9E3779B97F4A7C15ULL;
	Z = (Z ^ (Z >> 30)) * 0xBF58476D1CE4E5B9ULL;
	Z = (Z ^ (Z >> 27)) * 0x94D049BB133111EBULL;
	return Z ^ (Z >> 31);
}
inline uint64_t HashName(const std::string& S) { uint64_t H = 0xCBF29CE484222325ULL; for (char C : S) { H = (H ^ (uint8_t)C) * 0x100000001B3ULL; } return H; }
inline int64_t DeriveSeed(const std::string& TroughKey, uint32_t Steep, uint32_t Drink)
{
	return (int64_t)Mix64(HashName(TroughKey) ^ Mix64(((uint64_t)Steep << 32) | Drink));
}

// ---- who is drinking: read from actor tags/label (the Kennel Isle scripts set these) ----
// Coat_Spots | Coat_Stripes | Coat_Labyrinth; Pack_Member; Stage_2 | Stage_3; Tonic_Charm. The Cane Corso is AMF_Companion plus the tag Cane_Corso\n// (or, in the editor, a label with CaneCorso: actor labels do not exist in packaged builds).
inline Drinker DrinkerFromTags(const std::vector<std::string>& Tags, const std::string& Label)
{
	Drinker D;
	auto Has = [&](const char* T) { return std::find(Tags.begin(), Tags.end(), std::string(T)) != Tags.end(); };
	if (Has("Coat_Spots")) { D.Coat = "Spots"; } else if (Has("Coat_Stripes")) { D.Coat = "Stripes"; } else if (Has("Coat_Labyrinth")) { D.Coat = "Labyrinth"; }
	if (Has("Stage_3")) { D.Stage = 3; } else if (Has("Stage_2")) { D.Stage = 2; }
	D.Charm = Has("Tonic_Charm");
	if (Has("AMF_Companion") && (Has("Cane_Corso") || Label.find("CaneCorso") != std::string::npos)) { D.Kind = "cane_corso"; }
	else if (Has("Pack_Member")) { D.Kind = "packMember"; }
	return D;
}

// ---- herbs on a plant: tags look like Tonic_Herb_Barkbalm ----
inline bool HerbFromTag(const std::string& Tag, std::string& Herb)
{
	static const std::string P = "Tonic_Herb_";
	if (Tag.size() <= P.size() || Tag.compare(0, P.size(), P) != 0) { return false; }
	const std::string H = Tag.substr(P.size());
	if (!IsIdent(H)) { return false; }
	Herb = H; return true;
}

// ---- server origin: https anywhere, plain http only to 127.0.0.1 (same rule as UDaedalusOceanHostClient) ----
inline bool OriginAllowed(std::string Origin)
{
	bool Secure = false;
	if (Origin.compare(0, 8, "https://") == 0) { Secure = true; Origin.erase(0, 8); }
	else if (Origin.compare(0, 7, "http://") == 0) { Origin.erase(0, 7); }
	else { return false; }
	std::string Host = Origin, Port; const size_t Colon = Origin.find(':');
	if (Colon != std::string::npos)
	{
		Host = Origin.substr(0, Colon); Port = Origin.substr(Colon + 1);
		if (Port.empty() || Port.size() > 5) { return false; }
		for (char C : Port) { if (C < '0' || C > '9') { return false; } }
		const int Number = std::stoi(Port); if (Number < 1 || Number > 65535) { return false; }
	}
	if (!Secure && Host != "127.0.0.1") { return false; }
	if (Host.empty() || Host.size() > 253) { return false; }
	size_t Start = 0;
	while (true)
	{
		const size_t Dot = Host.find('.', Start);
		const std::string Label = Host.substr(Start, Dot == std::string::npos ? std::string::npos : Dot - Start);
		if (Label.empty() || Label.size() > 63 || Label.front() == '-' || Label.back() == '-') { return false; }
		for (char C : Label) { if (!((C >= 'a' && C <= 'z') || (C >= 'A' && C <= 'Z') || (C >= '0' && C <= '9') || C == '-')) { return false; } }
		if (Dot == std::string::npos) { break; }
		Start = Dot + 1;
	}
	return true;
}

// ---- the trough ----
// Empty -> Gathering (herbs in) -> Steeped (Java confirmed a recipe; 3 drinks, flat after 10 min) -> Empty again.
// A refusal (422 etc.) leaves the herbs in the trough: nothing is spent unless Java answered 200.
enum class Phase { Empty, Gathering, Steeping, Steeped };
class Trough
{
public:
	Phase PhaseNow(double Now) { Settle(Now); return Phase_; }
	int HerbCount() const { return (int)Herbs_.size(); }
	const std::vector<std::string>& Herbs() const { return Herbs_; }
	int DrinksLeft(double Now) { Settle(Now); return Phase_ == Phase::Steeped ? Drinks_ : 0; }
	uint32_t Steeps() const { return Steeps_; }
	uint32_t DrinkOrdinal() const { return Ordinal_; }
	const std::string& RecipeId() const { return Recipe_; }

	bool Deposit(const std::string& Herb, double Now)
	{
		Settle(Now);
		if (Phase_ == Phase::Steeping || Phase_ == Phase::Steeped || !IsIdent(Herb) || (int)Herbs_.size() >= MaxHerbs) { return false; }
		if (std::find(Herbs_.begin(), Herbs_.end(), Herb) != Herbs_.end()) { return false; }
		Herbs_.push_back(Herb); Phase_ = Phase::Gathering; return true;
	}
	void Empty() { Herbs_.clear(); Phase_ = Phase::Empty; Drinks_ = 0; Pending_ = 0; Recipe_.clear(); }
	// Steeping is the one request that proves the herb set makes a tonic. Herbs are locked while it is in flight.
	bool BeginSteep(double Now)
	{
		Settle(Now);
		if (Phase_ != Phase::Gathering || Herbs_.empty()) { return false; }
		Phase_ = Phase::Steeping; return true;
	}
	void SteepRefused() { if (Phase_ == Phase::Steeping) { Phase_ = Phase::Gathering; } }
	void SteepDone(const std::string& RecipeId, double Now)
	{
		if (Phase_ != Phase::Steeping) { return; }
		Phase_ = Phase::Steeped; Recipe_ = RecipeId; Drinks_ = DecayDrinks; FlatAt_ = Now + DecaySeconds; ++Steeps_; Ordinal_ = 0;
	}
	// A pet drinks: reserves one of the 3 drinks and returns the ordinal for the seed. False when nothing to drink.
	// Call ConfirmDrink() when Java answered 200, RefundDrink() when it did not.
	bool ReserveDrink(double Now, uint32_t& Ordinal)
	{
		Settle(Now);
		if (Phase_ != Phase::Steeped || Drinks_ <= 0) { return false; }
		--Drinks_; ++Pending_; Ordinal = ++Ordinal_;
		return true;
	}
	void ConfirmDrink(double Now) { if (Pending_ > 0) { --Pending_; } Settle(Now); }
	void RefundDrink(double Now)
	{
		if (Pending_ > 0) { --Pending_; }
		if (Phase_ == Phase::Steeped && Now < FlatAt_ && Drinks_ < DecayDrinks) { ++Drinks_; }
		Settle(Now);
	}	double FlatAt() const { return FlatAt_; }
private:
	void Settle(double Now)
	{
		if (Phase_ == Phase::Steeped && ((Drinks_ <= 0 && Pending_ == 0) || Now >= FlatAt_)) { Empty(); }
	}
	std::vector<std::string> Herbs_; Phase Phase_ = Phase::Empty; int Drinks_ = 0; double FlatAt_ = 0;
	uint32_t Steeps_ = 0, Ordinal_ = 0; int Pending_ = 0; std::string Recipe_;
};

// ---- per-pet effect ledger ----
// overTime: mods and grants last DurationSec. pulse: mods are handed back once (the caller applies them), then forgotten.
// A second drink of the same recipe refreshes the first, it does not stack (one pot, one effect).
struct Entry { std::string Recipe; std::vector<Mod> Mods; std::vector<std::string> Grants; double ExpiresAt = 0; double BreedChancePct = 0; };
class Ledger
{
public:
	// Returns the one-shot mods of a pulse brew (empty for overTime).
	std::vector<Mod> Apply(const Brew& B, double Now)
	{
		Entries_.erase(std::remove_if(Entries_.begin(), Entries_.end(), [&](const Entry& E) { return E.Recipe == B.RecipeId; }), Entries_.end());
		if (B.Kind == Mode::Pulse) { return B.Mods; }
		Entry E; E.Recipe = B.RecipeId; E.Mods = B.Mods; E.Grants = B.Grants; E.ExpiresAt = Now + B.DurationSec; E.BreedChancePct = B.BreedChancePct;
		Entries_.push_back(E); return {};
	}
	// Names of recipes that just ran out.
	std::vector<std::string> Expire(double Now)
	{
		std::vector<std::string> Gone;
		for (const Entry& E : Entries_) { if (Now >= E.ExpiresAt) { Gone.push_back(E.Recipe); } }
		Entries_.erase(std::remove_if(Entries_.begin(), Entries_.end(), [&](const Entry& E) { return Now >= E.ExpiresAt; }), Entries_.end());
		return Gone;
	}
	bool Active(const std::string& Recipe, double Now) const { for (const Entry& E : Entries_) { if (E.Recipe == Recipe && Now < E.ExpiresAt) { return true; } } return false; }
	// (Base + every active add) * every active mul.
	double Stat(const std::string& Name, double Base, double Now) const
	{
		double Add = 0, Mul = 1;
		for (const Entry& E : Entries_) { if (Now >= E.ExpiresAt) { continue; } for (const Mod& M : E.Mods) { if (M.Stat == Name) { if (M.Mul) { Mul *= M.Value; } else { Add += M.Value; } } } }
		return (Base + Add) * Mul;
	}
	bool HasGrant(const std::string& Name, double Now) const { for (const Entry& E : Entries_) { if (Now >= E.ExpiresAt) { continue; } for (const std::string& G : E.Grants) { if (G == Name) { return true; } } } return false; }
	double BreedChancePct(double Now) const { double Best = 0; for (const Entry& E : Entries_) { if (Now < E.ExpiresAt) { Best = std::max(Best, E.BreedChancePct); } } return Best; }
	size_t Count() const { return Entries_.size(); }
private:
	std::vector<Entry> Entries_;
};

}}  // namespace daedalus::tonic