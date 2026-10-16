#include "../DaedalusLink/Source/DaedalusLink/Public/DaedalusShardsteadWorkerActivity.h"
#include <iostream>

using namespace DaedalusShardsteadWorkerActivity;
#define CHECK(x) do { if (!(x)) { std::cerr << "FAIL line " << __LINE__ << ": " #x "\n"; return 1; } ++checks; } while (0)

int main()
{
    int checks=0;
    Selector selector;
    Input input;
    input.HurtEvent=1;
    auto result=selector.Advance(input,0.0f);
    CHECK(result.Animation==Clip::Hurt && result.Changed && result.ReactionStarted && !result.Loop);
    input.HurtEvent=2;
    result=selector.Advance(input,0.1f);
    CHECK(result.Animation==Clip::Hurt && !result.Changed && result.ReactionStarted);
    result=selector.Advance(input,0.1f);
    CHECK(result.Animation==Clip::Hurt && !result.Changed && !result.ReactionStarted);
    input.HurtEvent=1;
    result=selector.Advance(input,0.1f);
    CHECK(result.Animation==Clip::Hurt && !result.ReactionStarted);
    result=selector.Advance(input,0.6f);
    CHECK(result.Animation==Clip::Idle && result.Changed && !result.ReactionStarted && result.Loop);
    input.HurtEvent=2;
    CHECK(!selector.Advance(input,0.0f).ReactionStarted);

    // Disabled snapshots consume event sequences instead of replaying on enable.
    selector.Reset();
    input=Input{};
    input.Enabled=false;input.HurtEvent=8;input.DefenceEvent=9;
    result=selector.Advance(input,0.0f);
    CHECK(result.Animation==Clip::Idle && !result.ReactionStarted);
    input.Enabled=true;
    result=selector.Advance(input,0.0f);
    CHECK(result.Animation==Clip::Idle && !result.ReactionStarted);
    input.DefenceEvent=10;
    result=selector.Advance(input,0.0f);
    CHECK(result.Animation==Clip::Attack && result.ReactionStarted && !result.Loop);
    input.DefenceEvent=11;
    result=selector.Advance(input,0.1f);
    CHECK(result.Animation==Clip::Attack && !result.Changed && result.ReactionStarted);

    // Hurt wins a simultaneous defence; defence arriving during Hurt is consumed.
    selector.Reset();input=Input{};
    input.HurtEvent=1;input.DefenceEvent=1;
    result=selector.Advance(input,0.0f);
    CHECK(result.Animation==Clip::Hurt && result.ReactionStarted);
    input.DefenceEvent=2;
    result=selector.Advance(input,0.1f);
    CHECK(result.Animation==Clip::Hurt && !result.ReactionStarted);
    result=selector.Advance(input,0.6f);
    CHECK(result.Animation==Clip::Idle && !result.ReactionStarted);
    input.DefenceEvent=3;
    CHECK(selector.Advance(input,0.0f).Animation==Clip::Attack);
    // Actor/session rebinding legitimately permits a fresh sequence starting at 1.
    selector.Reset();input=Input{};input.HurtEvent=1;
    result=selector.Advance(input,0.0f);
    CHECK(result.Animation==Clip::Hurt && result.Changed && result.ReactionStarted);

    struct WorkCase { Role role; Job job; Clip clip; };
    const WorkCase work[]={{Role::Prospector,Job::ExtractOre,Clip::Mine},
        {Role::Cachekeeper,Job::Maintain,Clip::Repair},
        {Role::Trader,Job::Exchange,Clip::Trade},
        {Role::Farmer,Job::TendCrop,Clip::Idle},
        {Role::Energywright,Job::Maintain,Clip::Repair},
        {Role::Rescuer,Job::Escort,Clip::Idle}};
    for (const auto& item : work)
    {
        selector.Reset();input=Input{};
        input.Worker=item.role;input.CommittedJob=item.job;input.AtWorksite=true;
        CHECK(selector.Advance(input,0.0f).Animation==Clip::Idle); // unconfirmed
        input.JobConfirmed=true;
        result=selector.Advance(input,0.0f);
        CHECK(result.Animation==item.clip && result.Loop && !result.ReactionStarted);
        input.SpeedMetresPerSecond=1.5f;
        result=selector.Advance(input,0.0f);
        CHECK(result.Animation==Clip::Walk && result.PlaybackRate==1.0f);
        input.HurtEvent=1;
        CHECK(selector.Advance(input,0.0f).Animation==Clip::Hurt);
        CHECK(selector.Advance(input,0.6f).Animation==Clip::Walk);
        input.SpeedMetresPerSecond=0.0f;
        CHECK(selector.Advance(input,0.0f).Animation==item.clip);
    }
    selector.Reset();input=Input{};
    input.Worker=Role::Trader;input.CommittedJob=Job::ExtractOre;
    input.JobConfirmed=true;input.AtWorksite=true;
    CHECK(selector.Advance(input,0.0f).Animation==Clip::Idle); // unsupported role/job
    input.Worker=Role::Prospector;input.AtWorksite=false;
    CHECK(selector.Advance(input,0.0f).Animation==Clip::Idle); // not at worksite
    std::cout << "SHARDSTEAD_WORKER_PULSE_PASS " << checks << " checks\n";
}
