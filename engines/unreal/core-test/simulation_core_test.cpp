// SPDX-License-Identifier: MIT
#include "DaedalusSimulationCore.h"
#include <cstdlib>
#include <iostream>
#include <fstream>
#include <iterator>
#include <limits>
#include <thread>

using namespace daedalus::simulation;
static int Checks = 0;
static void Check(bool Value) { ++Checks; if (!Value) { std::cerr << "failed check " << Checks << '\n'; std::exit(1); } }
static View State(std::int64_t Revision = 1, std::string Task = "REQUEST_WATER") {
    View V;
    V.SchemaVersion = 1; V.WorldId = "world-zero"; V.NpcId = "npc-zero";
    V.Tick = Revision; V.Revision = Revision; V.EventSequence = 0;
    V.StateHash = std::string(64, 'a'); V.Task = std::move(Task);
    V.Reason = "keeper reserve empty"; V.CisternWater = 3;
    return V;
}
static View Fixture(const char* Name) {
    std::ifstream In(std::string(SIMULATION_FIXTURE_DIR) + "/" + Name, std::ios::binary);
    Check(In.good());
    const std::string Json{std::istreambuf_iterator<char>(In), std::istreambuf_iterator<char>()};
    View V; Check(DecodeView(Json, V)); return V;
}

int main() {
    Mailbox M;
    auto Epoch = M.Begin("world-zero", "npc-zero");
    Check(M.Desired(0) == Intent::Stop);
    Check(M.TryPush(Epoch, State(), 1) == Intake::Accepted);
    Check(M.Pump(1) == Intake::Accepted);
    Check(M.Desired(1) == Intent::RequestWater);
    Check(M.Current()->CisternWater == 3 && M.Current()->KeeperWater == 0);
    Check(M.TryPush(Epoch, State(), 4) == Intake::Accepted);
    Check(M.Pump(4) == Intake::Duplicate && M.Fresh(8.999));
    Check(!M.Fresh(9) && M.Desired(9) == Intent::Stop);
    Check(M.TryPush(Epoch, State(0), 9) == Intake::Accepted);
    Check(M.Pump(9) == Intake::Stale && !M.Fresh(9));
    auto Wrong = State(2); Wrong.WorldId = "other-world";
    Check(M.TryPush(Epoch, Wrong, 9) == Intake::Accepted);
    Check(M.Pump(9) == Intake::Invalid);
    Check(M.TryPush(Epoch, State(2, "WORK"), 10) == Intake::Accepted);
    Check(M.Pump(10) == Intake::Accepted && M.Desired(10) == Intent::Work);
    Check(M.Current()->Revision == 2);
    auto Clash = State(2); Clash.StateHash[0] = 'b';
    Check(M.TryPush(Epoch, Clash, 11) == Intake::Accepted);
    Check(M.Pump(11) == Intake::Conflict && M.NeedsReconcile() && !M.Fresh(11));
    Check(M.TryPush(Epoch, State(3), 12) == Intake::Accepted);
    M.Pump(12);
    Check(!M.Fresh(12)); // Conflicting histories cannot recover themselves with an arbitrary later packet.

    const auto OldEpoch = Epoch;
    Epoch = M.Begin("world-zero", "npc-zero");
    Check(M.TryPush(OldEpoch, State(20), 20) == Intake::WrongSession);
    Check(!M.Current() && !M.Fresh(20));
    for (int I = 0; I < 4; ++I) Check(M.TryPush(Epoch, State(I + 1), 20) == Intake::Accepted);
    Check(M.TryPush(Epoch, State(10), 20) == Intake::Full);
    M.Pump(20); Check(M.Current()->Revision == 4);
    Check(M.TryPush(Epoch, State(3), 21) == Intake::Accepted);
    Check(M.TryPush(Epoch, State(5, "REST"), 21) == Intake::Accepted);
    M.Pump(21); Check(M.Current()->Revision == 5 && M.Desired(21) == Intent::Rest);
    Check(M.TryPush(Epoch, State(6), 30) == Intake::Accepted);
    Check(M.Pump(35) == Intake::Stale && M.Current()->Revision == 5);
    Check(M.TryPush(Epoch, State(6), 40) == Intake::Accepted);
    Check(M.Pump(39) == Intake::Stale);
    Check(M.TryPush(Epoch, State(6), std::numeric_limits<double>::quiet_NaN()) == Intake::Invalid);
    Check(M.Pump(std::numeric_limits<double>::infinity()) == Intake::Invalid);
    Check(!M.Fresh(0));
    auto Rewind = State(6); Rewind.Tick = 1;
    Check(M.TryPush(Epoch, Rewind, 41) == Intake::Accepted);
    Check(M.Pump(41) == Intake::Conflict);

    Epoch = M.Begin("world-zero", "npc-zero");
    auto Precise = State(9007199254740993LL, "WORK");
    Check(M.TryPush(Epoch, Precise, 50) == Intake::Accepted);
    M.Pump(50); Check(M.Current()->Revision == 9007199254740993LL);
    // A detached world discards queued work already produced under the old epoch.
    Check(M.TryPush(Epoch, State(9007199254740994LL), 51) == Intake::Accepted);
    Epoch = M.Begin("world-one", "npc-zero");
    Check(M.Pump(51) == Intake::WrongSession && !M.Current());

    Epoch = M.Begin("world-zero", "npc-zero");
    std::atomic<int> Accepted{0};
    std::array<std::thread, 4> Producers;
    for (auto& T : Producers) T = std::thread([&] {
        for (int I = 0; I < 1000; ++I) if (M.TryPush(Epoch, State(), 60) == Intake::Accepted) ++Accepted;
    });
    for (auto& T : Producers) T.join();
    Check(Accepted == 4); M.Pump(60); Check(M.Fresh(60));

    auto Delta = Step({0,0,100}, {1000,0,100}, 180, 1);
    Check(Delta.X == 9 && Delta.Y == 0 && Delta.Z == 0);
    Delta = Step({0,0,100}, {55,0,100}, 180, 1); Check(Delta.X == 5);
    Check(Step({0,0,0}, {40,0,0}, 180, 1).X == 0);
    Check(Step({0,0,0}, {1000,0,0}, 180, -1).X == 0);
    Check(Step({0,0,0}, {1000,0,0}, 1e9, 1e9).X == 15);
    Check(Step({0,0,0}, {std::numeric_limits<double>::quiet_NaN(),0,0}, 180, 1).X == 0);

    // Actual Java LivingWorldService/View trace, serialized by Jackson at PR29 source2ca96368.
    // This proves decoder+mailbox execution against its producer; it does not claim playable Unreal behavior.
    Epoch = M.Begin("world-zero", "npc-zero");
    auto Initial = Fixture("initial.json");
    Check(M.TryPush(Epoch, Initial, 70) == Intake::Accepted); M.Pump(70);
    Check(M.Desired(70) == Intent::Rest);
    auto Request = Fixture("request-water.json");
    Check(M.TryPush(Epoch, Request, 71) == Intake::Accepted); M.Pump(71);
    Check(M.Desired(71) == Intent::RequestWater && M.Current()->EventSequence == 2);
    auto Work = Fixture("work.json");
    Check(M.TryPush(Epoch, Work, 72) == Intake::Accepted); M.Pump(72);
    Check(M.Desired(72) == Intent::Work && M.Current()->QuestCompleted && M.Current()->RememberedActor == "alice");
    Check(M.Current()->CisternWater == 1 && M.Current()->KeeperWater == 3);
    Check(M.TryPush(Epoch, Work, 71.5) == Intake::Accepted);
    Check(M.Pump(72) == Intake::Duplicate && M.Fresh(76.99)); // Older duplicate never shortens lease.
    Check(M.TryPush(Epoch, Request, 73) == Intake::Accepted);
    Check(M.Pump(73) == Intake::Stale && M.Current()->QuestCompleted);
    Check(M.Desired(77) == Intent::Stop && M.Current()->RememberedActor == "alice");
    auto Activity = Work; ++Activity.Revision; Activity.StateHash[0] = 'b';
    Check(M.TryPush(Epoch, Activity, 78) == Intake::Accepted);
    Check(M.Pump(78) == Intake::Accepted); // Same tick/sequence with higher revision is legitimate.
    auto SequenceRollback = Activity; ++SequenceRollback.Revision; --SequenceRollback.EventSequence;
    Check(M.TryPush(Epoch, SequenceRollback, 79) == Intake::Accepted);
    Check(M.Pump(79) == Intake::Conflict);
    std::cout << Checks << " native mailbox/keeper policy checks passed\n";
}
