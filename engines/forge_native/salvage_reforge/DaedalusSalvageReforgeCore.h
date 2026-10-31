// SPDX-License-Identifier: MIT
//
// Salvage and Reforge (Prismheart Crafting + rewards lane): break unwanted ingots into scrap at a fixed loss,
// then reforge scrap at full value into the ingot you want. Builds on the Shard Smelter core. Rules authority:
// salvage_reforge_ref.py in this folder; salvage_reforge_golden.txt pins this header to it.
//
// Conservation: ledger value (Value(inventory) + scrap) never rises. Smelt keeps it equal, Salvage lowers it
// (an ingot of value v gives floor(3v/4) scrap) and Reforge keeps it equal (an ingot costs its full value).
// So no loop of operations can gain value; static_asserts and the core test check it.
//
// Header-only, engine-free C++17: integer only, constexpr, no allocation, exceptions, RTTI, I/O, randomness or
// Unreal headers. Any refusal leaves the ledger exactly as it was.
#ifndef DAEDALUS_SALVAGE_REFORGE_CORE_H
#define DAEDALUS_SALVAGE_REFORGE_CORE_H

#include <cstdint>

#include "../shard_smelter/DaedalusShardSmelterCore.h"

namespace daedalus {
namespace prism {
namespace reforge {

namespace sm = ::daedalus::prism::smelter;

inline constexpr std::int64_t kMaxScrap = 999999999;
inline constexpr std::int64_t kMaxOps = 1000000;
inline constexpr int kFirstIngot = 5;

/** Inventory plus a scrap pool. Plain data. */
struct ForgeLedger {
    sm::ShardInventory inv{};
    std::int64_t scrap = 0;
};

/** Result of a ledger operation; stable values (0..6). */
enum class Status : std::uint8_t {
    Ok = 0,
    NullPointer = 1,  // a null ledger pointer
    NotAnIngot = 2,   // material is a shard or out of range (for Smelt: unknown recipe)
    BadCount = 3,     // count outside 1..kMaxOps (for Smelt: batches outside 1..kMaxBatch)
    BadLedger = 4,    // a count or the scrap outside its range
    Short = 5,        // not enough ingots (Salvage), scrap (Reforge) or inputs (Smelt)
    Overflow = 6      // scrap or an ingot count would pass its ceiling
};

constexpr const char* StatusName(Status s) {
    switch (s) {
        case Status::Ok:
            return "OK";
        case Status::NullPointer:
            return "NULL_POINTER";
        case Status::NotAnIngot:
            return "NOT_AN_INGOT";
        case Status::BadCount:
            return "BAD_COUNT";
        case Status::BadLedger:
            return "BAD_LEDGER";
        case Status::Short:
            return "SHORT";
        case Status::Overflow:
            return "OVERFLOW";
    }
    return "UNKNOWN";
}

/** Scrap from salvaging one unit: floor(3 * value / 4); 0 for shards (not salvageable). */
constexpr std::int64_t ScrapPerUnit(int material) {
    return material >= kFirstIngot && material < sm::kMaterials ? (3 * sm::kValue[material]) / 4 : 0;
}

/** Scrap to reforge one unit: its full shard value; 0 for shards (not reforgeable). */
constexpr std::int64_t CostPerUnit(int material) {
    return material >= kFirstIngot && material < sm::kMaterials ? sm::kValue[material] : 0;
}

constexpr bool ValidLedger(const ForgeLedger& l) {
    return sm::ValidInventory(l.inv) && l.scrap >= 0 && l.scrap <= kMaxScrap;
}

/** Inventory value plus scrap (each scrap is worth one shard). */
constexpr std::int64_t LedgerValue(const ForgeLedger& l) {
    return sm::Value(l.inv) + l.scrap;
}

/** Break `count` ingots of `material` into scrap. */
constexpr Status Salvage(ForgeLedger* l, int material, std::int64_t count) {
    if (l == nullptr) {
        return Status::NullPointer;
    }
    if (material < kFirstIngot || material >= sm::kMaterials) {
        return Status::NotAnIngot;
    }
    if (count < 1 || count > kMaxOps) {
        return Status::BadCount;
    }
    if (!ValidLedger(*l)) {
        return Status::BadLedger;
    }
    if (l->inv.count[material] < count) {
        return Status::Short;
    }
    if (l->scrap + ScrapPerUnit(material) * count > kMaxScrap) {
        return Status::Overflow;
    }
    l->inv.count[material] -= count;
    l->scrap += ScrapPerUnit(material) * count;
    return Status::Ok;
}

/** Spend scrap to make `count` ingots of `material`. */
constexpr Status Reforge(ForgeLedger* l, int material, std::int64_t count) {
    if (l == nullptr) {
        return Status::NullPointer;
    }
    if (material < kFirstIngot || material >= sm::kMaterials) {
        return Status::NotAnIngot;
    }
    if (count < 1 || count > kMaxOps) {
        return Status::BadCount;
    }
    if (!ValidLedger(*l)) {
        return Status::BadLedger;
    }
    if (l->scrap < CostPerUnit(material) * count) {
        return Status::Short;
    }
    if (l->inv.count[material] + count > sm::kMaxCount) {
        return Status::Overflow;
    }
    l->inv.count[material] += count;
    l->scrap -= CostPerUnit(material) * count;
    return Status::Ok;
}

/** Smelt on the ledger's inventory, with the smelter's statuses mapped onto this ledger's. */
constexpr Status Smelt(ForgeLedger* l, int recipe, std::int64_t batches) {
    if (l == nullptr) {
        return Status::NullPointer;
    }
    if (l->scrap < 0 || l->scrap > kMaxScrap) {
        return Status::BadLedger;
    }
    switch (sm::Smelt(&l->inv, recipe, batches)) {
        case sm::Status::Ok:
            return Status::Ok;
        case sm::Status::NullPointer:
            return Status::NullPointer;
        case sm::Status::UnknownRecipe:
            return Status::NotAnIngot;
        case sm::Status::BadBatch:
            return Status::BadCount;
        case sm::Status::BadInventory:
            return Status::BadLedger;
        case sm::Status::Short:
            return Status::Short;
        case sm::Status::Overflow:
            return Status::Overflow;
    }
    return Status::BadLedger;
}

namespace detail {

// Every ingot loses value on salvage and costs at least its value to reforge, so a salvage-reforge cycle loses.
constexpr bool CycleAlwaysLoses() {
    for (int m = kFirstIngot; m < sm::kMaterials; ++m) {
        if (!(ScrapPerUnit(m) < sm::kValue[m]) || !(CostPerUnit(m) >= sm::kValue[m])) {
            return false;
        }
    }
    return true;
}

}  // namespace detail

static_assert(detail::CycleAlwaysLoses(), "salvage must lose value and reforge must cost full value");
static_assert(ScrapPerUnit(0) == 0 && CostPerUnit(4) == 0, "shards are not salvageable or reforgeable");

}  // namespace reforge
}  // namespace prism
}  // namespace daedalus

#endif  // DAEDALUS_SALVAGE_REFORGE_CORE_H
