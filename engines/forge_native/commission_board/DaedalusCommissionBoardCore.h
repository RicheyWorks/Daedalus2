// SPDX-License-Identifier: MIT
//
// Forgemaster's Commission Board (Prismheart Crafting + rewards lane): each calendar day the Forgemaster posts three
// commissions for three different ingots. Delivering one takes its ingots from the Shard Smelter inventory and pays
// Forge Marks; filling the whole board pays a bonus. Rules authority: commission_board_ref.py; the golden file
// commission_board_golden.txt pins this header to it.
//
// Header-only, engine-free C++17, integer only, no exceptions, RTTI or Unreal headers. Deliver and date checks are
// constexpr and allocation-free; only MakeBoard draws randomness, through DaedalusPyRandomCore.h seeded with
// "commission|YYYY-MM-DD", so every player sees the same board on the same day. Any refusal changes nothing.
// Marks are a reward currency, not shard value: nothing here turns marks back into shards or ingots, so the
// Smelter / Salvage conservation property is untouched.
#ifndef DAEDALUS_COMMISSION_BOARD_CORE_H
#define DAEDALUS_COMMISSION_BOARD_CORE_H

#include <cstddef>
#include <cstdint>
#include <string>

#include "../../unreal/DaedalusLink/Source/DaedalusLink/Public/DaedalusPyRandomCore.h"
#include "../shard_smelter/DaedalusShardSmelterCore.h"

namespace daedalus {
namespace prism {
namespace commission {

namespace sm = ::daedalus::prism::smelter;

inline constexpr int kSlots = 3;
inline constexpr int kFirstIngot = 5;
inline constexpr int kIngots = 5;
inline constexpr int kMaxQty = 3;
inline constexpr std::int64_t kMarkBonus = 2;
inline constexpr std::int64_t kBoardBonus = 5;
inline constexpr std::int64_t kMaxMarks = 999999999;

/** Result; stable values (0..7). */
enum class Status : std::uint8_t {
    Ok = 0,
    NullPointer = 1,
    BadDate = 2,       // not a real YYYY-MM-DD date (year 0001..9999)
    BadSlot = 3,       // slot outside 0..2
    AlreadyDone = 4,   // that commission was already delivered
    BadInventory = 5,  // an inventory count or the marks outside its range
    Short = 6,         // not enough of the ingot
    Overflow = 7       // marks would pass kMaxMarks
};

constexpr const char* StatusName(Status s) {
    switch (s) {
        case Status::Ok:
            return "OK";
        case Status::NullPointer:
            return "NULL_POINTER";
        case Status::BadDate:
            return "BAD_DATE";
        case Status::BadSlot:
            return "BAD_SLOT";
        case Status::AlreadyDone:
            return "ALREADY_DONE";
        case Status::BadInventory:
            return "BAD_INVENTORY";
        case Status::Short:
            return "SHORT";
        case Status::Overflow:
            return "OVERFLOW";
    }
    return "UNKNOWN";
}

struct Commission {
    int material = 0;        // smelter Material index, 5..9 (an ingot)
    std::int64_t qty = 0;    // 1..3; a heartglass ingot is always 1
    std::int64_t marks = 0;  // qty * shard value + kMarkBonus
};

/** One day's board plus progress. Plain data. */
struct Board {
    Commission slot[kSlots] = {};
    bool done[kSlots] = {};
    std::int64_t marks = 0;  // the player's Forge Marks balance
};

/** True for a real YYYY-MM-DD date with year 0001..9999 (proleptic Gregorian leap years). */
constexpr bool ValidDate(const char* d, std::size_t n) {
    if (d == nullptr || n != 10 || d[4] != '-' || d[7] != '-') {
        return false;
    }
    for (std::size_t i = 0; i < n; ++i) {
        if (i != 4 && i != 7 && (d[i] < '0' || d[i] > '9')) {
            return false;
        }
    }
    const int y = (d[0] - '0') * 1000 + (d[1] - '0') * 100 + (d[2] - '0') * 10 + (d[3] - '0');
    const int m = (d[5] - '0') * 10 + (d[6] - '0');
    const int day = (d[8] - '0') * 10 + (d[9] - '0');
    if (y < 1 || m < 1 || m > 12) {
        return false;
    }
    const bool leap = (y % 4 == 0 && y % 100 != 0) || y % 400 == 0;
    constexpr int kDim[12] = {31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31};
    const int dim = m == 2 && leap ? 29 : kDim[m - 1];
    return day >= 1 && day <= dim;
}

/** Post the board for `date` into *out (progress cleared, marks kept). Refusals leave *out unchanged. */
inline Status MakeBoard(const std::string& date, Board* out) {
    if (out == nullptr) {
        return Status::NullPointer;
    }
    if (!ValidDate(date.data(), date.size())) {
        return Status::BadDate;
    }
    daedalus::pyrandom::PyRandom r(std::string("commission|") + date);
    const std::vector<std::size_t> picks = r.SampleIndices(static_cast<std::size_t>(kIngots), kSlots);
    Board b;
    b.marks = out->marks;
    for (int i = 0; i < kSlots; ++i) {
        Commission& c = b.slot[i];
        c.material = kFirstIngot + static_cast<int>(picks[static_cast<std::size_t>(i)]);
        c.qty = c.material == static_cast<int>(sm::Material::HeartglassIngot)
                    ? 1
                    : 1 + static_cast<std::int64_t>(r.RandRange(kMaxQty));
        c.marks = c.qty * sm::kValue[c.material] + kMarkBonus;
    }
    *out = b;
    return Status::Ok;
}

/** Deliver commission `slot`: take its ingots from *inv, pay its marks (plus kBoardBonus when it fills the board). */
constexpr Status Deliver(sm::ShardInventory* inv, Board* b, int slot) {
    if (inv == nullptr || b == nullptr) {
        return Status::NullPointer;
    }
    if (slot < 0 || slot >= kSlots) {
        return Status::BadSlot;
    }
    if (b->done[slot]) {
        return Status::AlreadyDone;
    }
    if (!sm::ValidInventory(*inv) || b->marks < 0 || b->marks > kMaxMarks) {
        return Status::BadInventory;
    }
    const Commission& c = b->slot[slot];
    if (c.material < kFirstIngot || c.material >= sm::kMaterials) {
        return Status::BadInventory;  // a hand-built board with a non-ingot commission
    }
    if (inv->count[c.material] < c.qty) {
        return Status::Short;
    }
    bool all = true;
    for (int i = 0; i < kSlots; ++i) {
        all = all && (i == slot || b->done[i]);
    }
    const std::int64_t gain = c.marks + (all ? kBoardBonus : 0);
    if (b->marks + gain > kMaxMarks) {
        return Status::Overflow;
    }
    inv->count[c.material] -= c.qty;
    b->done[slot] = true;
    b->marks += gain;
    return Status::Ok;
}

static_assert(ValidDate("2024-02-29", 10) && !ValidDate("2026-02-29", 10) && !ValidDate("1900-02-29", 10),
              "leap years");
static_assert(kSlots <= kIngots, "three different ingots per board");

}  // namespace commission
}  // namespace prism
}  // namespace daedalus

#endif  // DAEDALUS_COMMISSION_BOARD_CORE_H
