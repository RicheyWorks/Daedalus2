// SPDX-License-Identifier: MIT
//
// Shard Smelter (Prismheart Crafting + rewards lane): the forge bench on Hephaestus Island where Prism Shards
// are smelted into ingots by fixed recipes. Rules authority: shard_smelter_ref.py (Python) in this folder;
// shard_smelter_golden.txt pins this header to it.
//
// Header-only, engine-free C++17: integer only, no allocation, no exceptions, no RTTI, no I/O, no randomness,
// no Unreal headers. Every function is constexpr. A refusal never changes the inventory.
//
// Shard input: this header defines its own minimal inventory (ShardInventory). Its first five slots are the
// five Prism Shard hues in Prism Satchel order (ember, tide, verdant, gale, umbra), so a caller copies the
// Satchel wallet's five counts in and the spent counts back out. It does not include or depend on the Satchel core.
#ifndef DAEDALUS_SHARD_SMELTER_CORE_H
#define DAEDALUS_SHARD_SMELTER_CORE_H

#include <cstdint>

namespace daedalus {
namespace prism {
namespace smelter {

/** Materials: five shard hues (Satchel order), then five ingots. */
enum class Material : std::uint8_t {
    Ember = 0,
    Tide = 1,
    Verdant = 2,
    Gale = 3,
    Umbra = 4,
    Glowsteel = 5,
    Tidebrass = 6,
    Galeiron = 7,
    UmbralAlloy = 8,
    HeartglassIngot = 9
};

inline constexpr int kMaterials = 10;
inline constexpr int kShardHues = 5;
/** Largest count in one slot (the same 9-digit ceiling as a Satchel count). */
inline constexpr std::int64_t kMaxCount = 999999999;
/** Most batches in one Smelt call. */
inline constexpr std::int64_t kMaxBatch = 1000000;

/** Counts per material, indexed by Material. Plain data so a wrapper can copy it in and out freely. */
struct ShardInventory {
    std::int64_t count[kMaterials] = {};
};

/** Result of a Smelt call; stable values (0..6). */
enum class Status : std::uint8_t {
    Ok = 0,
    NullPointer = 1,    // a null inventory pointer
    UnknownRecipe = 2,  // recipe id outside the table
    BadBatch = 3,       // batches outside 1..kMaxBatch
    BadInventory = 4,   // a count below 0 or above kMaxCount
    Short = 5,          // not enough of some input for every batch; nothing is taken
    Overflow = 6        // an output slot would pass kMaxCount; nothing is taken
};

/** Stable status name (the golden file uses these). */
constexpr const char* StatusName(Status s) {
    switch (s) {
        case Status::Ok:
            return "OK";
        case Status::NullPointer:
            return "NULL_POINTER";
        case Status::UnknownRecipe:
            return "UNKNOWN_RECIPE";
        case Status::BadBatch:
            return "BAD_BATCH";
        case Status::BadInventory:
            return "BAD_INVENTORY";
        case Status::Short:
            return "SHORT";
        case Status::Overflow:
            return "OVERFLOW";
    }
    return "UNKNOWN";
}

/** One recipe: per-batch inputs and outputs. */
struct Recipe {
    const char* name;
    std::int64_t in[kMaterials];
    std::int64_t out[kMaterials];
};

inline constexpr int kRecipes = 5;

//                                         ember tide verd gale umbr glow tbrs gale umbA hglI
inline constexpr Recipe kRecipeTable[kRecipes] = {
    {"glowsteel",        {3, 1, 0, 0, 0, 0, 0, 0, 0, 0}, {0, 0, 0, 0, 0, 1, 0, 0, 0, 0}},
    {"tidebrass",        {0, 2, 2, 0, 0, 0, 0, 0, 0, 0}, {0, 0, 0, 0, 0, 0, 1, 0, 0, 0}},
    {"galeiron",         {0, 0, 0, 2, 1, 0, 0, 0, 0, 0}, {0, 0, 0, 0, 0, 0, 0, 1, 0, 0}},
    {"umbral_alloy",     {1, 0, 0, 0, 3, 0, 0, 0, 0, 0}, {0, 0, 0, 0, 0, 0, 0, 0, 1, 0}},
    {"heartglass_ingot", {0, 0, 0, 0, 0, 1, 1, 1, 1, 0}, {0, 0, 0, 0, 0, 0, 0, 0, 0, 1}},
};

/** Material names in Material order. */
inline constexpr const char* kMaterialNames[kMaterials] = {
    "ember", "tide", "verdant", "gale", "umbra", "glowsteel", "tidebrass", "galeiron", "umbral_alloy",
    "heartglass_ingot"};

/** Shard value of one unit: a shard is 1, an ingot is worth exactly its inputs, so smelting conserves value. */
inline constexpr std::int64_t kValue[kMaterials] = {1, 1, 1, 1, 1, 4, 4, 3, 4, 15};

/** True when every count is within 0..kMaxCount. */
constexpr bool ValidInventory(const ShardInventory& inv) {
    for (int i = 0; i < kMaterials; ++i) {
        if (inv.count[i] < 0 || inv.count[i] > kMaxCount) {
            return false;
        }
    }
    return true;
}

/** Total shard value of a valid inventory (at most 10 * 15 * kMaxCount, well inside int64_t). */
constexpr std::int64_t Value(const ShardInventory& inv) {
    std::int64_t v = 0;
    for (int i = 0; i < kMaterials; ++i) {
        v += inv.count[i] * kValue[i];
    }
    return v;
}

/**
 * Largest batch count Smelt would accept for this inventory (0 when none), or -1 for an unknown recipe or an
 * invalid inventory. Capped at kMaxBatch.
 */
constexpr std::int64_t MaxBatches(const ShardInventory& inv, int recipe) {
    if (recipe < 0 || recipe >= kRecipes || !ValidInventory(inv)) {
        return -1;
    }
    const Recipe& r = kRecipeTable[recipe];
    std::int64_t best = kMaxBatch;
    for (int i = 0; i < kMaterials; ++i) {
        if (r.in[i] > 0) {
            const std::int64_t can = inv.count[i] / r.in[i];
            best = can < best ? can : best;
        }
        const std::int64_t net = r.out[i] - r.in[i];
        if (net > 0) {
            const std::int64_t room = (kMaxCount - inv.count[i]) / net;
            best = room < best ? room : best;
        }
    }
    return best;
}

/**
 * Smelt `batches` batches of `recipe` in place. Checks run in order: pointer, recipe, batch count, inventory,
 * then inputs (Short) and outputs (Overflow). Any refusal leaves *inv exactly as it was.
 */
constexpr Status Smelt(ShardInventory* inv, int recipe, std::int64_t batches) {
    if (inv == nullptr) {
        return Status::NullPointer;
    }
    if (recipe < 0 || recipe >= kRecipes) {
        return Status::UnknownRecipe;
    }
    if (batches < 1 || batches > kMaxBatch) {
        return Status::BadBatch;
    }
    if (!ValidInventory(*inv)) {
        return Status::BadInventory;
    }
    const Recipe& r = kRecipeTable[recipe];
    // All products below stay under 1e6 * 3 = 3e6 per unit, far inside int64_t.
    for (int i = 0; i < kMaterials; ++i) {
        if (inv->count[i] < r.in[i] * batches) {
            return Status::Short;
        }
    }
    for (int i = 0; i < kMaterials; ++i) {
        if (inv->count[i] - r.in[i] * batches + r.out[i] * batches > kMaxCount) {
            return Status::Overflow;
        }
    }
    for (int i = 0; i < kMaterials; ++i) {
        inv->count[i] = inv->count[i] - r.in[i] * batches + r.out[i] * batches;
    }
    return Status::Ok;
}

namespace detail {

constexpr bool ValuesMatchRecipes() {
    for (int k = 0; k < kRecipes; ++k) {
        std::int64_t in = 0;
        std::int64_t out = 0;
        for (int i = 0; i < kMaterials; ++i) {
            in += kRecipeTable[k].in[i] * kValue[i];
            out += kRecipeTable[k].out[i] * kValue[i];
        }
        if (in != out) {
            return false;
        }
    }
    return true;
}

}  // namespace detail

static_assert(detail::ValuesMatchRecipes(), "every recipe must conserve shard value");
static_assert(kValue[0] == 1 && kValue[4] == 1, "a shard is worth 1");
static_assert(kMaxCount * 15 * kMaterials < INT64_MAX / 2, "Value() cannot overflow");

}  // namespace smelter
}  // namespace prism
}  // namespace daedalus

#endif  // DAEDALUS_SHARD_SMELTER_CORE_H
