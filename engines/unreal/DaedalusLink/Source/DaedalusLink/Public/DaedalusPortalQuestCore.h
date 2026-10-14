#pragma once
#include <cstddef>
#include <stdexcept>
#include <string>
#include <unordered_set>
#include <utility>
#include <vector>

// Ordered, per-player quest progress. Caller supplies authoritative events.
// No inventory awards, networking, persistence or client trust is implied.
namespace DaedalusPortalQuest
{
struct Step
{
    std::string Type;
    std::string Target;
    unsigned Required = 1;
};
enum class Result { Ignored, Duplicate, Progressed, Completed, CapacityReached };

class Progress
{
public:
    explicit Progress(std::vector<Step> steps) : Steps(std::move(steps))
    {
        if (Steps.empty() || Steps.size() > 32)
            throw std::invalid_argument("Quest needs one to thirty-two steps");
        for (const auto& s : Steps)
            if (s.Type.empty() || s.Target.empty() || s.Required == 0)
                throw std::invalid_argument("Quest step needs type, target and positive count");
    }

    Result Apply(const std::string& eventId, const std::string& type,
                 const std::string& target, unsigned amount = 1)
    {
        if (eventId.empty() || eventId.size() > 128 || amount == 0)
            return Result::Ignored;
        if (Seen.count(eventId)) return Result::Duplicate;
        if (Complete()) return Result::Ignored;
        const Step& s = Steps[Current];
        if (s.Type != type || s.Target != target) return Result::Ignored;
        // Never evict processed IDs and thereby permit old replay.
        if (Seen.size() >= 512) return Result::CapacityReached;
        Seen.insert(eventId);
        const unsigned remaining = s.Required - Count;
        Count += amount < remaining ? amount : remaining;
        if (Count == s.Required) { ++Current; Count = 0; }
        return Complete() ? Result::Completed : Result::Progressed;
    }

    bool Complete() const { return Current == Steps.size(); }
    std::size_t StepIndex() const { return Current; }
    unsigned StepCount() const { return Count; }
    bool ClaimReward()
    {
        if (!Complete() || RewardClaimed) return false;
        RewardClaimed = true;
        return true; // A signal only. Host must persist/award atomically.
    }
private:
    std::vector<Step> Steps;
    std::unordered_set<std::string> Seen;
    std::size_t Current = 0;
    unsigned Count = 0;
    bool RewardClaimed = false;
};
}
