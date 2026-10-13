#include "../DaedalusLink/Source/DaedalusLink/Public/DaedalusPortalQuestCore.h"
#include <iostream>
#include <limits>
#define CHECK(expr) do { if (!(expr)) { std::cerr << "Failed line " << __LINE__ << '\n'; return 1; } ++checks; } while (0)
using namespace DaedalusPortalQuest;
int main()
{
    int checks = 0;
    Progress rescue({{"talk", "king", 1}, {"rescue", "traveller", 2}, {"talk", "king", 1}});
    CHECK(!rescue.ClaimReward());
    CHECK(rescue.Apply("early", "rescue", "traveller") == Result::Ignored);
    CHECK(rescue.Apply("a", "talk", "king") == Result::Progressed);
    CHECK(rescue.Apply("a", "rescue", "traveller") == Result::Duplicate);
    CHECK(rescue.Apply("b", "rescue", "traveller") == Result::Progressed);
    CHECK(rescue.StepCount() == 1);
    CHECK(rescue.Apply("c", "rescue", "traveller", std::numeric_limits<unsigned>::max()) == Result::Progressed);
    CHECK(rescue.StepIndex() == 2 && rescue.StepCount() == 0);
    CHECK(rescue.Apply("d", "talk", "king") == Result::Completed);
    CHECK(rescue.ClaimReward());
    CHECK(!rescue.ClaimReward());
    CHECK(rescue.Apply("e", "talk", "king") == Result::Ignored);
    Progress unicorn({{"guide", "herd", 1}});
    CHECK(unicorn.Apply("", "guide", "herd") == Result::Ignored);
    CHECK(unicorn.Apply("x", "guide", "herd", 0) == Result::Ignored);
    CHECK(unicorn.Apply("x", "guide", "herd") == Result::Completed);
    Progress bounded({{"collect", "supplies", 513}});
    for (unsigned i=0; i<512; ++i)
        CHECK(bounded.Apply(std::to_string(i), "collect", "supplies") == Result::Progressed);
    CHECK(bounded.Apply("overflow", "collect", "supplies") == Result::CapacityReached);
    CHECK(bounded.StepCount() == 512 && !bounded.Complete());
    CHECK(bounded.Apply("0", "collect", "supplies") == Result::Duplicate);
    bool rejected=false;
    try { Progress invalid({}); } catch (const std::invalid_argument&) { rejected=true; }
    CHECK(rejected);
    std::cout << "PORTAL_QUEST_PASS " << checks << " checks\n";
}
