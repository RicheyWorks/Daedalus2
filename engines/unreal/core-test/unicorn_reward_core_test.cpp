// SPDX-License-Identifier: MIT
#include "../DaedalusLink/Source/DaedalusLink/Public/DaedalusUnicornRewardCore.h"
#include <iostream>
using namespace DaedalusUnicornReward;
#define CHECK(x) do { if (!(x)) { std::cerr << "line " << __LINE__ << '\n'; return 1; } ++checks; } while (0)
int main()
{
    int checks = 0;
    Gate gate;
    CHECK(gate.RecordBullAtSea("bull", false, true) == Outcome::Ignored);
    CHECK(gate.RecordBullAtSea("bull", true, false) == Outcome::Ignored);
    CHECK(gate.RecordPackEncounter("pack", 8, true) == Outcome::Ignored);
    CHECK(gate.RecordPackEncounter("pack", 12, true) == Outcome::Progressed);
    CHECK(!gate.ClaimReward());
    for (unsigned i = 0; i < 10; ++i)
    {
        const auto id = std::to_string(i);
        CHECK(gate.RecordBullAtSea(id, true, true) == (i == 9 ? Outcome::Eligible : Outcome::Progressed));
        CHECK(gate.RecordBullAtSea(id, true, true) == Outcome::Duplicate);
    }
    CHECK(gate.BullsAtSea() == 10 && gate.Eligible());
    CHECK(gate.ClaimReward());
    CHECK(!gate.ClaimReward());
    const auto saved = gate.Export();
    Gate restored;
    CHECK(restored.Restore(saved));
    CHECK(restored.Eligible() && restored.RewardClaimed());
    CHECK(!restored.ClaimReward());
    CHECK(!restored.Restore(saved));
    Snapshot invalid = saved;
    invalid.BullIds.push_back("overflow");
    Gate fresh;
    CHECK(!fresh.Restore(invalid) && fresh.Pristine());
    invalid = saved; invalid.BullIds[1] = invalid.BullIds[0];
    CHECK(!fresh.Restore(invalid) && fresh.Pristine());
    invalid = saved; invalid.PackId.clear();
    CHECK(!fresh.Restore(invalid) && fresh.Pristine());
    std::cout << "UNICORN_REWARD_PASS " << checks << '\n';
}
