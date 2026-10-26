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
    const std::vector<std::vector<Step>> invalidConfigs = {
        {}, {{"", "king", 1}}, {{"talk", "", 1}}, {{"talk", "king", 0}},
        std::vector<Step>(33, Step{"talk", "king", 1}),
        {{"talk", "king", 1}, {"rescue", "traveller", 0}}
    };
    for (const auto& config : invalidConfigs)
    {
        Progress invalid(config);
        CHECK(!invalid.Valid() && !invalid.Why().empty());
        CHECK(!invalid.Complete());
        CHECK(!invalid.ClaimReward());
        CHECK(invalid.Apply("invalid-event", "talk", "king") == Result::Ignored);
        CHECK(invalid.StepIndex() == 0 && invalid.StepCount() == 0);
        CHECK(!invalid.Complete() && !invalid.ClaimReward());
    }
    Progress maximum(std::vector<Step>(32, Step{"talk", "king", 1}));
    CHECK(maximum.Valid() && maximum.Why().empty());
    for (unsigned i=0; i<32; ++i)
        CHECK(maximum.Apply(std::to_string(i), "talk", "king") ==
              (i == 31 ? Result::Completed : Result::Progressed));
    CHECK(maximum.Complete() && maximum.ClaimReward());
    CHECK(!maximum.ClaimReward());
    std::cout << "PORTAL_QUEST_PASS " << checks << " checks\n";
}
