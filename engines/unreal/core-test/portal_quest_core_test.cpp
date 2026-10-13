#include "../DaedalusLink/Source/DaedalusLink/Public/DaedalusPortalQuestCore.h"
#include <iostream>
#include <limits>
#include <fstream>
#include <iterator>
#define CHECK(expr) do { if (!(expr)) { std::cerr << "Failed line " << __LINE__ << '\n'; return 1; } ++checks; } while (0)
using namespace DaedalusPortalQuest;
int main(int argc,char** argv)
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
    const std::string journal=rescue.SaveJournal("player/portal/royal");
    Progress restarted({{"talk", "king", 1}, {"rescue", "traveller", 2}, {"talk", "king", 1}});
    CHECK(restarted.RestoreJournal(journal,"player/portal/royal"));
    CHECK(restarted.Complete() && !restarted.ClaimReward());
    CHECK(restarted.Apply("a", "talk", "king") == Result::Duplicate);
    CHECK(restarted.SaveJournal("player/portal/royal")==journal);
    CHECK(!restarted.RestoreJournal(journal,"other-player/portal/royal"));
    CHECK(rescue.SaveJournal("").empty());
    CHECK(!restarted.RestoreJournal(journal+"unexpected","player/portal/royal"));
    CHECK(restarted.SaveJournal("player/portal/royal")==journal);
    Progress changed({{"talk", "king", 2}});
    CHECK(!changed.RestoreJournal(journal,"player/portal/royal"));
    CHECK(!changed.Complete() && changed.StepCount()==0);
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
    Progress savedBounded({{"collect", "supplies", 513}});
    CHECK(savedBounded.RestoreJournal(bounded.SaveJournal("player/portal/royal"),"player/portal/royal"));
    CHECK(savedBounded.StepCount()==512 && !savedBounded.Complete());
    CHECK(savedBounded.Apply("overflow", "collect", "supplies")==Result::CapacityReached);
    CHECK(!savedBounded.RestoreJournal(std::string(256*1024+1,'x'),"player/portal/royal"));
    Progress invalidReplay({{"talk", "king", 2}});
    CHECK(!invalidReplay.RestoreJournal("DQP1\n\"player/portal/royal\"\n1\n\"talk\" \"king\" 2\n2 0\n\"same\" 1\n\"same\" 1\n","player/portal/royal"));
    CHECK(!invalidReplay.RestoreJournal("DQP1\n\"player/portal/royal\"\n1\n\"talk\" \"king\" 2\n1 0\n\"x\" -1\n","player/portal/royal"));
    CHECK(!invalidReplay.RestoreJournal("DQP1\n\"player/portal/royal\"\n1\n\"talk\" \"king\" 2\n0 1\n","player/portal/royal"));
    CHECK(!invalidReplay.Complete() && invalidReplay.StepCount()==0);
    bool rejected=false;
    try { Progress invalid({}); } catch (const std::invalid_argument&) { rejected=true; }
    CHECK(rejected);
    if (argc==3 && std::string(argv[1])=="--write")
    {
        std::ofstream output(argv[2],std::ios::binary);output<<journal;output.flush();CHECK(output.good());
    }
    if (argc==3 && std::string(argv[1])=="--read")
    {
        std::ifstream input(argv[2],std::ios::binary);CHECK(input.good());
        const std::string stored((std::istreambuf_iterator<char>(input)),std::istreambuf_iterator<char>());
        Progress fresh({{"talk", "king", 1}, {"rescue", "traveller", 2}, {"talk", "king", 1}});
        CHECK(fresh.RestoreJournal(stored,"player/portal/royal"));
        CHECK(fresh.Complete() && !fresh.ClaimReward());
        CHECK(fresh.Apply("a","talk","king")==Result::Duplicate);
    }
    std::cout << "PORTAL_QUEST_PASS " << checks << " checks\n";
}
