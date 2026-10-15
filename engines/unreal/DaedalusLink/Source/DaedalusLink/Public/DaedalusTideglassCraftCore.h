// SPDX-License-Identifier: MIT
// Standard C++17 transaction planning for Tideglass crafting and its one-time commission.
// Hosts supply clock, weather, clean-filter evidence and finite inventory; this core creates no water.
#pragma once

#include <cmath>
#include <cstdint>
#include <cctype>
#include <limits>
#include <iomanip>
#include <locale>
#include <map>
#include <sstream>
#include <string>
#include <utility>

namespace daedalus
{
namespace tideglass
{

using Inventory = std::map<std::string, int32_t>;

struct State
{
    int64_t revision = 0;
    Inventory items;
    bool valveCrafted = false;
    bool conduitOpen = false;
    bool commissionPaid = false;
    std::map<std::string, std::string> receipts;
};

struct Context
{
    int day = 1;
    double hour = 9;
    bool raining = false;
    bool cleanWaterAvailable = false;
};

struct Config
{
    Inventory valveInputs{{"copper_ingot", 2}, {"charcoal", 1}};
    std::string valveItem = "poot_pulse_valve";
    std::string waterItem = "water";
    std::string rewardItem = "poot_harbor_credit";
    int waterUnits = 2;
    int rewardUnits = 1;
    double installStartHour = 6;
    double installEndHour = 10;
};

enum class Action { CraftValve, InstallValve, SupplyWater };
enum class Status
{
    Ready, AlreadyCommitted, Invalid, Insufficient, WrongWindow, UnsafeWeather,
    WaterUnavailable, PrerequisiteMissing, AlreadyComplete, Stale, Overflow, ReceiptLimit
};

struct Plan
{
    Status status = Status::Invalid;
    State before, after;
    std::string operationId, signature;
    Inventory missing;
};

inline bool operator==(const State& left, const State& right)
{
    return left.revision == right.revision && left.items == right.items &&
        left.valveCrafted == right.valveCrafted && left.conduitOpen == right.conduitOpen &&
        left.commissionPaid == right.commissionPaid && left.receipts == right.receipts;
}
inline bool operator!=(const State& left, const State& right) { return !(left == right); }

namespace detail
{
inline bool validId(const std::string& id)
{
    if (id.empty() || id.size() > 128) return false;
    bool nonblank = false;
    for (unsigned char character : id)
    {
        if (std::iscntrl(character)) return false;
        if (!std::isspace(character)) nonblank = true;
    }
    return nonblank;
}
inline bool validState(const State& state)
{
    if (state.revision < 0 || state.revision >= std::numeric_limits<int64_t>::max() ||
        state.receipts.size() > 64 || (state.conduitOpen && !state.valveCrafted) ||
        (state.commissionPaid && !state.conduitOpen)) return false;
    for (const auto& item : state.items) if (!validId(item.first) || item.second < 0) return false;
    for (const auto& receipt : state.receipts)
        if (!validId(receipt.first) || receipt.second.empty()) return false;
    return true;
}
inline bool validConfig(const Config& config)
{
    if (config.valveInputs.empty() || !validId(config.valveItem) || !validId(config.waterItem) ||
        !validId(config.rewardItem) || config.waterUnits <= 0 || config.rewardUnits <= 0 ||
        config.waterUnits > std::numeric_limits<int32_t>::max() || config.rewardUnits > std::numeric_limits<int32_t>::max() ||
        !std::isfinite(config.installStartHour) || !std::isfinite(config.installEndHour) ||
        config.installStartHour < 0 || config.installStartHour >= config.installEndHour ||
        config.installEndHour > 24) return false;
    for (const auto& item : config.valveInputs) if (!validId(item.first) || item.second <= 0) return false;
    return true;
}
inline bool validContext(const Context& context)
{
    return context.day > 0 && std::isfinite(context.hour) && context.hour >= 0 && context.hour < 24;
}
inline bool validAction(Action action)
{
    return action == Action::CraftValve || action == Action::InstallValve || action == Action::SupplyWater;
}
inline std::string signature(const Config& config, Action action)
{
    // Length-prefixed IDs prevent collisions even when identifiers contain separators.
    std::ostringstream output;
    output.imbue(std::locale::classic());
    auto id = [&](const std::string& value) { output << value.size() << ':' << value << ';'; };
    output << "tideglass-v1;" << static_cast<int>(action) << ';' << config.valveInputs.size() << ';';
    for (const auto& input : config.valveInputs) { id(input.first); output << input.second << ';'; }
    id(config.valveItem); id(config.waterItem); id(config.rewardItem);
    output << config.waterUnits << ';' << config.rewardUnits << ';' << std::hexfloat
        << (config.installStartHour == 0 ? 0.0 : config.installStartHour) << ';' << config.installEndHour;
    return output.str();
}
inline int32_t quantity(const Inventory& inventory, const std::string& id)
{
    const auto found = inventory.find(id);
    return found == inventory.end() ? 0 : found->second;
}
} // namespace detail

/** Prepare never mutates state. Retries identify an already committed action/config independent of clock changes. */
inline Plan prepare(const State& state, const Config& config, Action action, const Context& context,
    const std::string& operationId, int64_t expectedRevision)
{
    Plan plan;
    plan.before = state;
    plan.after = state;
    plan.operationId = operationId;
    if (!detail::validState(state) || !detail::validConfig(config) || !detail::validAction(action) ||
        !detail::validId(operationId)) return plan;
    plan.signature = detail::signature(config, action);
    const auto receipt = state.receipts.find(operationId);
    if (receipt != state.receipts.end())
    {
        plan.status = receipt->second == plan.signature ? Status::AlreadyCommitted : Status::Invalid;
        return plan;
    }
    if (!detail::validContext(context) || expectedRevision < 0 || expectedRevision >= std::numeric_limits<int64_t>::max()) return plan;
    if (expectedRevision != state.revision) { plan.status = Status::Stale; return plan; }
    if ((action == Action::CraftValve && state.valveCrafted) ||
        (action == Action::InstallValve && state.conduitOpen) ||
        (action == Action::SupplyWater && state.commissionPaid))
    { plan.status = Status::AlreadyComplete; return plan; }
    if ((action == Action::InstallValve && !state.valveCrafted) ||
        (action == Action::SupplyWater && !state.conduitOpen))
    { plan.status = Status::PrerequisiteMissing; return plan; }
    if (action != Action::CraftValve && !context.cleanWaterAvailable)
    { plan.status = Status::WaterUnavailable; return plan; }
    if (action == Action::InstallValve)
    {
        if (context.raining) { plan.status = Status::UnsafeWeather; return plan; }
        if (context.hour < config.installStartHour || context.hour >= config.installEndHour)
        { plan.status = Status::WrongWindow; return plan; }
    }
    if (state.receipts.size() == 64) { plan.status = Status::ReceiptLimit; return plan; }
    if (state.revision == std::numeric_limits<int64_t>::max() - 1)
    { plan.status = Status::Overflow; return plan; }

    Inventory consumed, produced;
    if (action == Action::CraftValve) { consumed = config.valveInputs; produced[config.valveItem] = 1; }
    else if (action == Action::InstallValve) consumed[config.valveItem] = 1;
    else { consumed[config.waterItem] = config.waterUnits; produced[config.rewardItem] = config.rewardUnits; }
    for (const auto& input : consumed)
    {
        const int32_t available = detail::quantity(state.items, input.first);
        if (available < input.second) plan.missing[input.first] = input.second - available;
    }
    if (!plan.missing.empty()) { plan.status = Status::Insufficient; return plan; }

    Inventory changes = consumed;
    for (const auto& output : produced) changes.emplace(output.first, 0);
    Inventory next = state.items;
    for (const auto& change : changes)
    {
        const int64_t count = static_cast<int64_t>(detail::quantity(state.items, change.first)) -
            detail::quantity(consumed, change.first) + detail::quantity(produced, change.first);
        if (count < 0 || count > std::numeric_limits<int32_t>::max())
        { plan.status = Status::Overflow; return plan; }
        if (count == 0) next.erase(change.first);
        else next[change.first] = static_cast<int32_t>(count);
    }
    plan.after.items = std::move(next);
    plan.after.revision++;
    plan.after.receipts.emplace(operationId, plan.signature);
    if (action == Action::CraftValve) plan.after.valveCrafted = true;
    else if (action == Action::InstallValve) plan.after.conduitOpen = true;
    else plan.after.commissionPaid = true;
    plan.status = Status::Ready;
    return plan;
}

/** Commit on the inventory-owning thread. Caller serialization is required; plans are trusted prepare outputs. */
inline Status commit(State& host, const Plan& plan)
{
    if (plan.status != Status::Ready || host != plan.before || !detail::validState(plan.before) || !detail::validState(plan.after) ||
        plan.after.revision != plan.before.revision + 1) return Status::Stale;
    const auto receipt = plan.after.receipts.find(plan.operationId);
    if (!detail::validId(plan.operationId) || plan.signature.empty() ||
        plan.before.receipts.count(plan.operationId) != 0 || receipt == plan.after.receipts.end() ||
        receipt->second != plan.signature || plan.after.receipts.size() != plan.before.receipts.size() + 1 ||
        (plan.before.valveCrafted && !plan.after.valveCrafted) ||
        (plan.before.conduitOpen && !plan.after.conduitOpen) ||
        (plan.before.commissionPaid && !plan.after.commissionPaid)) return Status::Stale;
    const int changedFacts = static_cast<int>(plan.after.valveCrafted != plan.before.valveCrafted) +
        static_cast<int>(plan.after.conduitOpen != plan.before.conduitOpen) +
        static_cast<int>(plan.after.commissionPaid != plan.before.commissionPaid);
    if (changedFacts != 1) return Status::Stale;
    for (const auto& existing : plan.before.receipts)
    {
        const auto retained = plan.after.receipts.find(existing.first);
        if (retained == plan.after.receipts.end() || retained->second != existing.second) return Status::Stale;
    }
    // Build the replacement before swapping, so allocation failures cannot partially mutate the host.
    State replacement = plan.after;
    using std::swap;
    swap(host.revision, replacement.revision);
    host.items.swap(replacement.items);
    swap(host.valveCrafted, replacement.valveCrafted);
    swap(host.conduitOpen, replacement.conduitOpen);
    swap(host.commissionPaid, replacement.commissionPaid);
    host.receipts.swap(replacement.receipts);
    return Status::Ready;
}

} // namespace tideglass
} // namespace daedalus
