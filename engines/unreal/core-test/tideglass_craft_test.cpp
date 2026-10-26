// SPDX-License-Identifier: MIT
//
// Source-only regression cases for the engine-free Tideglass crafting core.
// Native compilation and execution are paused pending the Norton investigation.

#include "DaedalusTideglassCraftCore.h"

#include <cmath>
#include <cstdio>
#include <limits>
#include <string>

using namespace daedalus::tideglass;

static int Passed = 0, Total = 0;

static void Check(const std::string& Label, bool Ok)
{
    ++Total;
    Passed += Ok;
    std::printf("%s %s\n", Ok ? "PASS" : "FAIL", Label.c_str());
}

static bool Same(const State& A, const State& B)
{
    return A.revision == B.revision && A.items == B.items
        && A.valveCrafted == B.valveCrafted && A.conduitOpen == B.conduitOpen
        && A.commissionPaid == B.commissionPaid && A.receipts == B.receipts;
}

static State Stock()
{
    State S;
    S.revision = 7;
    S.items = {{"copper_ingot", 4}, {"charcoal", 2}, {"water", 4}, {"unrelated", 0}};
    return S;
}

static State Crafted()
{
    State S = Stock();
    S.valveCrafted = true;
    S.items["poot_pulse_valve"] = 1;
    return S;
}

static State Installed()
{
    State S = Stock();
    S.valveCrafted = true;
    S.conduitOpen = true;
    return S;
}

static Context Clean()
{
    Context C;
    C.cleanWaterAvailable = true;
    return C;
}

static Plan Blocked(const std::string& Label, const State& Initial, const Config& Rules,
                    Action Act, const Context& C, const std::string& Id,
                    std::int64_t ExpectedRevision, Status Expected)
{
    State Host = Initial;
    const Plan P = prepare(Host, Rules, Act, C, Id, ExpectedRevision);
    Check(Label + " status", P.status == Expected);
    Check(Label + " prepare is pure", Same(Host, Initial));
    Check(Label + " snapshots unchanged", Same(P.before, Initial) && Same(P.after, Initial));
    Check(Label + " blocked commit is stale", commit(Host, P) == Status::Stale);
    Check(Label + " blocked commit preserves state", Same(Host, Initial));
    return P;
}

static void Blocked(const std::string& Label, const State& Initial, const Config& Rules,
                    Action Act, const Context& C, Status Expected)
{
    Blocked(Label, Initial, Rules, Act, C, Label, Initial.revision, Expected);
}

static void SuccessChainAndReplay()
{
    const Config Rules;
    const Context C = Clean();
    State Host = Stock();
    const State Original = Host;
    const Plan Craft = prepare(Host, Rules, Action::CraftValve, C, "craft-1", 7);
    Check("craft prepares", Craft.status == Status::Ready);
    Check("craft leaves input untouched", Same(Host, Original) && Same(Craft.before, Original));
    Check("craft names operation", Craft.operationId == "craft-1" && !Craft.signature.empty());
    const Inventory CraftedItems = {{"copper_ingot", 2}, {"charcoal", 1}, {"water", 4},
                                    {"unrelated", 0}, {"poot_pulse_valve", 1}};
    Check("craft has exact inventory delta", Craft.after.items == CraftedItems);
    Check("craft has exact fact and revision delta", Craft.after.revision == 8
        && Craft.after.valveCrafted && !Craft.after.conduitOpen && !Craft.after.commissionPaid);
    Check("craft has no shortages", Craft.missing.empty());
    Check("craft commits", commit(Host, Craft) == Status::Ready && Same(Host, Craft.after));
    Check("craft records receipt", Host.receipts.size() == 1
        && Host.receipts.at("craft-1") == Craft.signature);
    Check("committing original plan twice is stale", commit(Host, Craft) == Status::Stale);
    Check("double commit leaves after snapshot intact", Same(Host, Craft.after));

    Context Later = C;
    Later.hour = 15;
    Later.raining = true;
    Blocked("craft replay with original revision", Host, Rules, Action::CraftValve, Later,
            "craft-1", 7, Status::AlreadyCommitted);
    Context InvalidClock = Later;
    InvalidClock.day = 0;
    InvalidClock.hour = std::numeric_limits<double>::quiet_NaN();
    Blocked("receipt recognized before clock and revision validation", Host, Rules,
            Action::CraftValve, InvalidClock, "craft-1", -1, Status::AlreadyCommitted);
    Blocked("operation action collision", Host, Rules, Action::InstallValve, C,
            "craft-1", Host.revision, Status::Invalid);
    Config Changed = Rules;
    Changed.waterUnits = 3;
    Blocked("operation config collision", Host, Changed, Action::CraftValve, C,
            "craft-1", Host.revision, Status::Invalid);
    Blocked("craft only once", Host, Rules, Action::CraftValve, C, Status::AlreadyComplete);

    Context Dawn = C;
    Dawn.hour = 6;
    const Plan Install = prepare(Host, Rules, Action::InstallValve, Dawn, "install-1", 8);
    Check("install starts at inclusive hour six", Install.status == Status::Ready);
    Check("install consumes valve", Install.after.items.count("poot_pulse_valve") == 0);
    Check("install preserves unrelated zero entry", Install.after.items.at("unrelated") == 0);
    Check("install changes only conduit fact", Install.after.revision == 9
        && Install.after.valveCrafted && Install.after.conduitOpen && !Install.after.commissionPaid);
    Check("install commits", commit(Host, Install) == Status::Ready && Same(Host, Install.after));
    Blocked("install replay ignores changed context", Host, Rules, Action::InstallValve, Later,
            "install-1", 8, Status::AlreadyCommitted);
    Blocked("install only once", Host, Rules, Action::InstallValve, C, Status::AlreadyComplete);

    const Plan Supply = prepare(Host, Rules, Action::SupplyWater, C, "supply-1", 9);
    Check("supply prepares", Supply.status == Status::Ready);
    Check("supply consumes two and rewards one", Supply.after.items.at("water") == 2
        && Supply.after.items.at("poot_harbor_credit") == 1);
    Check("supply has exact fact and revision delta", Supply.after.revision == 10
        && Supply.after.valveCrafted && Supply.after.conduitOpen && Supply.after.commissionPaid);
    Check("supply commits", commit(Host, Supply) == Status::Ready && Same(Host, Supply.after));
    Check("successful chain records three receipts", Host.receipts.size() == 3);
    Blocked("supply replay with original revision", Host, Rules, Action::SupplyWater, Later,
            "supply-1", 9, Status::AlreadyCommitted);
    Blocked("commission only once", Host, Rules, Action::SupplyWater, C, Status::AlreadyComplete);
}

static void PrerequisitesAndAtomicShortages()
{
    const Config Rules;
    const Context C = Clean();
    State S = Stock();
    S.items["poot_pulse_valve"] = 1;
    Blocked("stocked valve cannot bypass craft fact", S, Rules, Action::InstallValve, C,
            Status::PrerequisiteMissing);
    Blocked("unopened conduit cannot supply", Crafted(), Rules, Action::SupplyWater, C,
            Status::PrerequisiteMissing);

    S = Crafted();
    S.items.erase("poot_pulse_valve");
    const Plan ValveMissing = Blocked("install needs actual valve stock", S, Rules,
        Action::InstallValve, C, "missing-valve", S.revision, Status::Insufficient);
    Check("install reports valve shortage", ValveMissing.missing == Inventory{{"poot_pulse_valve", 1}});

    S = Stock();
    S.items["copper_ingot"] = 1;
    S.items["charcoal"] = 0;
    const Plan Missing = Blocked("all crafting shortages preflighted", S, Rules,
        Action::CraftValve, C, "missing-inputs", S.revision, Status::Insufficient);
    Check("craft reports every missing quantity", Missing.missing == Inventory{{"copper_ingot", 1}, {"charcoal", 1}});

    S = Installed();
    S.items["water"] = 1;
    const Plan WaterMissing = Blocked("clean signal cannot create water stock", S, Rules,
        Action::SupplyWater, C, "missing-water", S.revision, Status::Insufficient);
    Check("supply reports water shortage", WaterMissing.missing == Inventory{{"water", 1}});

    S = Stock();
    S.items["copper_ingot"] = 2;
    S.items["charcoal"] = 1;
    const Plan Exact = prepare(S, Rules, Action::CraftValve, C, "exact-inputs", S.revision);
    Check("exact inputs prepare", Exact.status == Status::Ready);
    Check("consumed zero entries removed", Exact.after.items.count("copper_ingot") == 0
        && Exact.after.items.count("charcoal") == 0 && Exact.after.items.at("unrelated") == 0);
    S = Installed();
    S.items["water"] = 2;
    const Plan ExactWater = prepare(S, Rules, Action::SupplyWater, C, "exact-water", S.revision);
    Check("supply removes consumed zero entry", ExactWater.status == Status::Ready
        && ExactWater.after.items.count("water") == 0);
}

static void WindowWeatherAndWater()
{
    const Config Rules;
    const State S = Crafted();
    Context C = Clean();
    C.hour = 5.999;
    Blocked("before install window", S, Rules, Action::InstallValve, C, Status::WrongWindow);
    C.hour = 10;
    Blocked("install end hour exclusive", S, Rules, Action::InstallValve, C, Status::WrongWindow);
    C.hour = 9.999;
    Check("just before install end allowed", prepare(S, Rules, Action::InstallValve, C,
        "inside-window", S.revision).status == Status::Ready);
    C.hour = 9;
    C.raining = true;
    Blocked("rain blocks installation", S, Rules, Action::InstallValve, C, Status::UnsafeWeather);
    C.raining = false;
    C.cleanWaterAvailable = false;
    Blocked("installation requires clean filter", S, Rules, Action::InstallValve, C, Status::WaterUnavailable);
    Blocked("supply requires clean filter", Installed(), Rules, Action::SupplyWater, C, Status::WaterUnavailable);
    C = Clean();
    C.hour = 15;
    C.raining = true;
    Check("supply uses no install weather or window gate", prepare(Installed(), Rules,
        Action::SupplyWater, C, "rainy-supply", S.revision).status == Status::Ready);
    C.cleanWaterAvailable = false;
    Check("craft uses no installation environment gate", prepare(Stock(), Rules,
        Action::CraftValve, C, "rainy-craft", S.revision).status == Status::Ready);

    Config WholeDay = Rules;
    WholeDay.installStartHour = 0;
    WholeDay.installEndHour = 24;
    C = Clean();
    C.hour = 0;
    Check("valid all day window at zero", prepare(S, WholeDay, Action::InstallValve, C,
        "midnight", S.revision).status == Status::Ready);
    C.hour = 23.999;
    Check("valid all day window before twenty four", prepare(S, WholeDay, Action::InstallValve, C,
        "late", S.revision).status == Status::Ready);
}

static void OverflowAndOverlap()
{
    const auto Max = std::numeric_limits<std::int32_t>::max();
    const Config Rules;
    const Context C = Clean();
    State S = Stock();
    S.items[Rules.valveItem] = Max;
    Blocked("craft output overflow", S, Rules, Action::CraftValve, C, Status::Overflow);
    S = Installed();
    S.items[Rules.rewardItem] = Max;
    Blocked("reward overflow", S, Rules, Action::SupplyWater, C, Status::Overflow);

    Config Balanced = Rules;
    Balanced.valveInputs = {{Balanced.valveItem, 1}};
    S = Stock();
    S.items[Balanced.valveItem] = Max;
    const Plan SameItem = prepare(S, Balanced, Action::CraftValve, C, "balanced-valve", S.revision);
    Check("balanced input output does not overflow", SameItem.status == Status::Ready
        && SameItem.after.items.at(Balanced.valveItem) == Max);
    Check("balanced plan commits", commit(S, SameItem) == Status::Ready && Same(S, SameItem.after));

    Config Shared = Rules;
    Shared.rewardItem = Shared.waterItem;
    S = Installed();
    S.items[Shared.waterItem] = Max;
    const Plan WaterReward = prepare(S, Shared, Action::SupplyWater, C, "water-reward", S.revision);
    Check("overlapping reward uses net delta", WaterReward.status == Status::Ready
        && WaterReward.after.items.at(Shared.waterItem) == Max - 1);
    S.items[Shared.waterItem] = 1;
    Blocked("overlapping output cannot satisfy input shortage", S, Shared, Action::SupplyWater,
            C, Status::Insufficient);

    S = Stock();
    S.revision = std::numeric_limits<std::int64_t>::max() - 1;
    Blocked("next revision must stay representable and valid", S, Rules, Action::CraftValve, C, Status::Overflow);
}

static void OptimisticCommit()
{
    const Config Rules;
    const Context C = Clean();
    const State Initial = Stock();
    Blocked("stale expected revision", Initial, Rules, Action::CraftValve, C,
            "stale-prepare", Initial.revision - 1, Status::Stale);
    const Plan P = prepare(Initial, Rules, Action::CraftValve, C, "pending", Initial.revision);
    Check("pending plan ready", P.status == Status::Ready);

    State Host = Initial;
    ++Host.revision;
    State Before = Host;
    Check("commit detects changed revision", commit(Host, P) == Status::Stale && Same(Host, Before));
    Host = Initial;
    ++Host.items["copper_ingot"];
    Before = Host;
    Check("commit detects same revision changed inventory", commit(Host, P) == Status::Stale && Same(Host, Before));
    Host = Initial;
    Host.valveCrafted = true;
    Before = Host;
    Check("commit detects same revision changed facts", commit(Host, P) == Status::Stale && Same(Host, Before));
    Host = Initial;
    Host.receipts["external"] = P.signature;
    Before = Host;
    Check("commit detects same revision changed receipts", commit(Host, P) == Status::Stale && Same(Host, Before));
    Host = Initial;
    Host.items.erase("unrelated");
    Before = Host;
    Check("commit compares zero entries too", commit(Host, P) == Status::Stale && Same(Host, Before));
    Host = Initial;
    Check("unchanged snapshot can commit after rejected attempts", commit(Host, P) == Status::Ready
        && Same(Host, P.after));

    Plan InvalidPlan = P;
    InvalidPlan.after.items["copper_ingot"] = -1;
    Host = Initial;
    Check("commit rejects malformed after inventory", commit(Host, InvalidPlan) == Status::Stale
        && Same(Host, Initial));
    InvalidPlan = P;
    InvalidPlan.after.revision += 1;
    Check("commit rejects nonadjacent after revision", commit(Host, InvalidPlan) == Status::Stale
        && Same(Host, Initial));
    InvalidPlan = P;
    InvalidPlan.after.valveCrafted = false;
    InvalidPlan.after.conduitOpen = true;
    Check("commit rejects inconsistent after facts", commit(Host, InvalidPlan) == Status::Stale
        && Same(Host, Initial));
    InvalidPlan = P;
    InvalidPlan.before.revision = std::numeric_limits<std::int64_t>::max();
    Host = InvalidPlan.before;
    Before = Host;
    Check("commit rejects invalid maximum before without revision overflow", commit(Host, InvalidPlan) == Status::Stale
        && Same(Host, Before));
}

static void CommitIntegrity()
{
    const Config Rules;
    const Context C = Clean();
    const State Initial = Stock();
    const Plan P = prepare(Initial, Rules, Action::CraftValve, C, "integrity", Initial.revision);
    Check("commit integrity fixture ready", P.status == Status::Ready);
    State Host = Initial;
    Plan Changed = P;
    Changed.after.receipts.erase(P.operationId);
    Check("commit rejects missing new receipt", commit(Host, Changed) == Status::Stale
        && Same(Host, Initial));
    Changed = P;
    Changed.after.receipts[P.operationId] = "different-signature";
    Check("commit rejects changed new receipt signature", commit(Host, Changed) == Status::Stale
        && Same(Host, Initial));
    Changed = P;
    Changed.after.valveCrafted = false;
    Check("commit rejects no business fact transition", commit(Host, Changed) == Status::Stale
        && Same(Host, Initial));
    Changed = P;
    Changed.after.conduitOpen = true;
    Check("commit rejects multiple business fact transitions", commit(Host, Changed) == Status::Stale
        && Same(Host, Initial));

    State WithReceipt = Initial;
    WithReceipt.receipts["previous"] = P.signature;
    const Plan Preserving = prepare(WithReceipt, Rules, Action::CraftValve, C,
        "preserving", WithReceipt.revision);
    Check("existing receipt fixture ready", Preserving.status == Status::Ready);
    Host = WithReceipt;
    Changed = Preserving;
    Changed.after.receipts["previous"] = "changed-existing-signature";
    Check("commit rejects changed existing receipt", commit(Host, Changed) == Status::Stale
        && Same(Host, WithReceipt));
    Changed = Preserving;
    Changed.after.receipts.erase("previous");
    Check("commit rejects removed existing receipt", commit(Host, Changed) == Status::Stale
        && Same(Host, WithReceipt));

    const State CraftedBefore = Crafted();
    Changed = prepare(CraftedBefore, Rules, Action::InstallValve, C,
        "backward-fact", CraftedBefore.revision);
    Check("backward fact fixture ready", Changed.status == Status::Ready);
    Changed.after.valveCrafted = false;
    Changed.after.conduitOpen = false;
    Host = CraftedBefore;
    Check("commit rejects valid snapshot with backward fact transition", commit(Host, Changed) == Status::Stale
        && Same(Host, CraftedBefore));
}

static void ReceiptBoundary()
{
    const Config Rules;
    const Context C = Clean();
    State S = Stock();
    const Plan Seed = prepare(S, Rules, Action::CraftValve, C, "seed", S.revision);
    Check("receipt fixture ready", Seed.status == Status::Ready);
    for (int I = 0; I < 63; ++I) S.receipts["historic-" + std::to_string(I)] = Seed.signature;
    const Plan Last = prepare(S, Rules, Action::CraftValve, C, "last-slot", S.revision);
    Check("sixty fourth receipt can commit", Last.status == Status::Ready
        && Last.after.receipts.size() == 64 && commit(S, Last) == Status::Ready);
    Blocked("receipt limit blocks new operation", S, Rules, Action::InstallValve, C, Status::ReceiptLimit);
    Blocked("full ledger still recognizes original retry", S, Rules, Action::CraftValve, C,
            "last-slot", 7, Status::AlreadyCommitted);
    S.receipts["too-many"] = Seed.signature;
    Blocked("oversized receipt ledger invalid", S, Rules, Action::CraftValve, C, Status::Invalid);
}

static void MalformedStateAndContext()
{
    const Config Rules;
    const Context Good = Clean();
    State S = Stock();
    S.items["copper_ingot"] = -1;
    Blocked("negative stock", S, Rules, Action::CraftValve, Good, Status::Invalid);
    S = Stock();
    S.items["   "] = 1;
    Blocked("blank inventory id", S, Rules, Action::CraftValve, Good, Status::Invalid);
    S = Stock();
    S.items[std::string(129, 'i')] = 1;
    Blocked("oversized inventory id", S, Rules, Action::CraftValve, Good, Status::Invalid);
    S = Stock();
    S.items["bad\nid"] = 1;
    Blocked("control character inventory id", S, Rules, Action::CraftValve, Good, Status::Invalid);
    S = Stock();
    S.items[std::string(128, 'i')] = 0;
    Check("maximum sized inventory id accepted", prepare(S, Rules, Action::CraftValve,
        Good, "long-stock-id", S.revision).status == Status::Ready);
    S = Stock();
    S.revision = -1;
    Blocked("negative revision", S, Rules, Action::CraftValve, Good, Status::Invalid);
    S.revision = std::numeric_limits<std::int64_t>::max();
    Blocked("maximum revision invalid", S, Rules, Action::CraftValve, Good, Status::Invalid);
    S = Stock();
    S.conduitOpen = true;
    Blocked("conduit requires crafted fact", S, Rules, Action::CraftValve, Good, Status::Invalid);
    S = Crafted();
    S.commissionPaid = true;
    Blocked("paid commission requires open conduit", S, Rules, Action::SupplyWater, Good, Status::Invalid);
    S = Stock();
    S.receipts[" "] = "signature";
    Blocked("blank receipt id", S, Rules, Action::CraftValve, Good, Status::Invalid);
    S = Stock();
    S.receipts[std::string(129, 'r')] = "signature";
    Blocked("oversized receipt id", S, Rules, Action::CraftValve, Good, Status::Invalid);
    S = Stock();
    S.receipts["empty-signature"].clear();
    Blocked("empty receipt signature", S, Rules, Action::CraftValve, Good, Status::Invalid);

    Context C = Good;
    C.day = 0;
    Blocked("day zero invalid", Stock(), Rules, Action::CraftValve, C, Status::Invalid);
    C = Good;
    C.day = -1;
    Blocked("negative day invalid", Stock(), Rules, Action::CraftValve, C, Status::Invalid);
    C = Good;
    C.hour = -0.01;
    Blocked("negative hour invalid", Stock(), Rules, Action::CraftValve, C, Status::Invalid);
    C.hour = 24;
    Blocked("hour twenty four invalid", Stock(), Rules, Action::CraftValve, C, Status::Invalid);
    C.hour = std::numeric_limits<double>::infinity();
    Blocked("infinite hour invalid", Stock(), Rules, Action::CraftValve, C, Status::Invalid);
    C.hour = std::numeric_limits<double>::quiet_NaN();
    Blocked("nan hour invalid", Stock(), Rules, Action::CraftValve, C, Status::Invalid);
    Blocked("unknown action invalid", Stock(), Rules, static_cast<Action>(99), Good, Status::Invalid);
    Blocked("blank operation id", Stock(), Rules, Action::CraftValve, Good, " \t", 7, Status::Invalid);
    Blocked("oversized operation id", Stock(), Rules, Action::CraftValve, Good,
            std::string(129, 'o'), 7, Status::Invalid);
    Blocked("control character operation id", Stock(), Rules, Action::CraftValve, Good,
            "bad\noperation", 7, Status::Invalid);
    Blocked("negative expected revision", Stock(), Rules, Action::CraftValve, Good,
            "negative-expected", -1, Status::Invalid);
    Blocked("maximum expected revision", Stock(), Rules, Action::CraftValve, Good,
            "maximum-expected", std::numeric_limits<std::int64_t>::max(), Status::Invalid);
    Check("maximum sized operation id accepted", prepare(Stock(), Rules, Action::CraftValve,
        Good, std::string(128, 'o'), 7).status == Status::Ready);
}

static void MalformedConfig()
{
    const State S = Stock();
    const Context C = Clean();
    Config Rules;
    Rules.valveInputs.clear();
    Blocked("empty recipe inputs", S, Rules, Action::CraftValve, C, Status::Invalid);
    Rules = Config{};
    Rules.valveInputs["copper_ingot"] = 0;
    Blocked("zero recipe input", S, Rules, Action::CraftValve, C, Status::Invalid);
    Rules.valveInputs["copper_ingot"] = -1;
    Blocked("negative recipe input", S, Rules, Action::CraftValve, C, Status::Invalid);
    Rules = Config{};
    Rules.valveInputs["\t"] = 1;
    Blocked("blank recipe input id", S, Rules, Action::CraftValve, C, Status::Invalid);
    Rules = Config{};
    Rules.valveInputs[std::string(129, 'r')] = 1;
    Blocked("oversized recipe input id", S, Rules, Action::CraftValve, C, Status::Invalid);
    Rules = Config{};
    Rules.valveItem.clear();
    Blocked("blank valve output", S, Rules, Action::CraftValve, C, Status::Invalid);
    Rules = Config{};
    Rules.waterItem = "\n";
    Blocked("blank water id", S, Rules, Action::CraftValve, C, Status::Invalid);
    Rules = Config{};
    Rules.rewardItem = std::string(129, 'x');
    Blocked("oversized reward id", S, Rules, Action::CraftValve, C, Status::Invalid);
    Rules = Config{};
    Rules.waterUnits = 0;
    Blocked("zero water units", S, Rules, Action::CraftValve, C, Status::Invalid);
    Rules.waterUnits = -1;
    Blocked("negative water units", S, Rules, Action::CraftValve, C, Status::Invalid);
    Rules = Config{};
    Rules.rewardUnits = 0;
    Blocked("zero reward units", S, Rules, Action::CraftValve, C, Status::Invalid);
    Rules.rewardUnits = -1;
    Blocked("negative reward units", S, Rules, Action::CraftValve, C, Status::Invalid);
    Rules = Config{};
    Rules.installStartHour = -1;
    Blocked("negative window start", S, Rules, Action::CraftValve, C, Status::Invalid);
    Rules = Config{};
    Rules.installEndHour = 25;
    Blocked("window beyond day", S, Rules, Action::CraftValve, C, Status::Invalid);
    Rules = Config{};
    Rules.installEndHour = Rules.installStartHour;
    Blocked("empty install window", S, Rules, Action::CraftValve, C, Status::Invalid);
    Rules.installEndHour = 5;
    Blocked("reversed install window", S, Rules, Action::CraftValve, C, Status::Invalid);
    Rules = Config{};
    Rules.installStartHour = std::numeric_limits<double>::quiet_NaN();
    Blocked("nan window start", S, Rules, Action::CraftValve, C, Status::Invalid);
    Rules = Config{};
    Rules.installEndHour = std::numeric_limits<double>::infinity();
    Blocked("infinite window end", S, Rules, Action::CraftValve, C, Status::Invalid);
}

int main()
{
    SuccessChainAndReplay();
    PrerequisitesAndAtomicShortages();
    WindowWeatherAndWater();
    OverflowAndOverlap();
    OptimisticCommit();
    CommitIntegrity();
    ReceiptBoundary();
    MalformedStateAndContext();
    MalformedConfig();
    std::printf("%d/%d\n", Passed, Total);
    return Passed == Total && Total > 0 ? 0 : 1;
}
