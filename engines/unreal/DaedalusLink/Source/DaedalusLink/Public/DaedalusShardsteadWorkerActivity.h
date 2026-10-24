#pragma once

#include <cmath>
#include <cstdint>

// Cosmetic presentation only. The authoritative host owns jobs and rewards.
namespace DaedalusShardsteadWorkerActivity
{
enum class Role : std::uint8_t { Prospector, Cachekeeper, Trader, Farmer, Energywright, Rescuer };
enum class Job : std::uint8_t { None, ExtractOre, TendCrop, Exchange, Maintain, Escort };
enum class Clip : std::uint8_t { Idle, Walk, Attack, Hurt, Mine, Trade, Repair };

inline const char* ClipName(Clip clip)
{
    switch (clip)
    {
    case Clip::Walk: return "Walk";
    case Clip::Attack: return "Attack";
    case Clip::Hurt: return "Hurt";
    case Clip::Mine: return "Mine";
    case Clip::Trade: return "Trade";
    case Clip::Repair: return "Repair";
    default: return "Idle";
    }
}

inline bool Supports(Role role, Job job)
{
    if (job == Job::None) return true;
    switch (role)
    {
    case Role::Prospector: return job == Job::ExtractOre;
    case Role::Cachekeeper: return job == Job::Maintain || job == Job::Exchange;
    case Role::Trader: return job == Job::Exchange;
    case Role::Farmer: return job == Job::TendCrop;
    case Role::Energywright: return job == Job::Maintain;
    case Role::Rescuer: return job == Job::Escort;
    default: return false;
    }
}

struct Input
{
    Role Worker = Role::Prospector;
    Job CommittedJob = Job::None;
    // False for a pending/unconfirmed storage write or unavailable host snapshot.
    bool JobConfirmed = false;
    bool AtWorksite = false;
    bool Enabled = true;
    float SpeedMetresPerSecond = 0.0f;
    // Monotonic server event sequence; zero means no event. Not a reward receipt.
    std::uint64_t HurtEvent = 0;
    std::uint64_t DefenceEvent = 0;
};

struct Output
{
    Clip Animation = Clip::Idle;
    float BlendSeconds = 0.18f;
    float PlaybackRate = 1.0f;
    bool Loop = true;
    bool Changed = false;
    // One Advance pulse for an accepted reaction, including same-clip restarts.
    bool ReactionStarted = false;
};

class Selector
{
public:
    Output Advance(const Input& input, float elapsedSeconds)
    {
        const float dt = std::isfinite(elapsedSeconds) && elapsedSeconds > 0.0f
            ? elapsedSeconds : 0.0f;
        ReactionRemaining = dt >= ReactionRemaining ? 0.0f : ReactionRemaining - dt;
        const bool newHurt = input.HurtEvent > LastHurt;
        const bool newDefence = input.DefenceEvent > LastDefence;
        if (newHurt) LastHurt = input.HurtEvent;
        if (newDefence) LastDefence = input.DefenceEvent;

        const float speed = std::isfinite(input.SpeedMetresPerSecond)
            && input.SpeedMetresPerSecond > 0.0f ? input.SpeedMetresPerSecond : 0.0f;
        // Hysteresis prevents walk/idle flicker from small position corrections.
        Moving = speed >= (Moving ? 0.06f : 0.12f);
        bool reactionStarted = false;
        if (!input.Enabled)
        {
            ReactionRemaining = 0.0f;
            Moving = false;
        }
        else if (newHurt)
        {
            Reaction = Clip::Hurt;
            ReactionRemaining = 0.55f;
            reactionStarted = true;
        }
        else if (newDefence && (ReactionRemaining == 0.0f || Reaction != Clip::Hurt))
        {
            Reaction = Clip::Attack;
            ReactionRemaining = 0.70f;
            reactionStarted = true;
        }

        Clip next = Clip::Idle;
        if (input.Enabled)
        {
            if (ReactionRemaining > 0.0f) next = Reaction;
            else if (Moving) next = Clip::Walk;
            else if (input.JobConfirmed && input.AtWorksite && Supports(input.Worker, input.CommittedJob))
            {
                switch (input.CommittedJob)
                {
                case Job::ExtractOre: next = Clip::Mine; break;
                case Job::Exchange: next = Clip::Trade; break;
                case Job::Maintain: next = Clip::Repair; break;
                // No crop/escort stationary clip has been authored yet.
                default: break;
                }
            }
        }
        Output result;
        result.Animation = next;
        result.Changed = next != Current;
        result.ReactionStarted = reactionStarted;
        result.Loop = next != Clip::Hurt && next != Clip::Attack;
        result.BlendSeconds = next == Clip::Hurt ? 0.06f : 0.18f;
        if (next == Clip::Walk)
            result.PlaybackRate = speed < 0.75f ? 0.5f : speed > 2.25f ? 1.5f : speed / 1.5f;
        Current = next;
        return result;
    }

    // Call on actor rebinding/session changes, not every animation update.
    void Reset() { *this = Selector(); }

private:
    Clip Current = Clip::Idle;
    Clip Reaction = Clip::Hurt;
    float ReactionRemaining = 0.0f;
    std::uint64_t LastHurt = 0;
    std::uint64_t LastDefence = 0;
    bool Moving = false;
};
}
