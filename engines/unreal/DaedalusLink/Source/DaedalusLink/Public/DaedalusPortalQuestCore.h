#pragma once
#include <cstddef>
#include <stdexcept>
#include <string>
#include <unordered_set>
#include <utility>
#include <vector>
#include <sstream>
#include <iomanip>
#include <charconv>

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
            if (s.Type.empty() || s.Target.empty() || s.Type.size()>128 || s.Target.size()>128 || s.Required == 0)
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
        History.push_back({eventId,amount});
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

    std::string SaveJournal(const std::string& scope) const
    {
        if (scope.empty() || scope.size()>256) return {};
        std::ostringstream out;
        out << "DQP1\n" << std::quoted(scope) << '\n' << Steps.size() << '\n';
        for (const auto& step:Steps)
            out << std::quoted(step.Type) << ' ' << std::quoted(step.Target) << ' ' << step.Required << '\n';
        out << History.size() << ' ' << (RewardClaimed?1:0) << '\n';
        for (const auto& event:History) out << std::quoted(event.Id) << ' ' << event.Amount << '\n';
        return out.str();
    }

    // Structural validation, NOT authenticity. Only load a host-trusted journal.
    // Replay in a temporary instance; failure never mutates the current quest.
    bool RestoreJournal(const std::string& text,const std::string& expectedScope)
    {
        if (text.size()>256*1024 || expectedScope.empty() || expectedScope.size()>256) return false;
        std::istringstream input(text);
        std::string magic;
        if (!(input>>magic) || magic!="DQP1") return false;
        std::string scope;
        if (!(input>>std::quoted(scope)) || scope!=expectedScope) return false;
        unsigned count=0;
        if (!ReadUnsigned(input,count) || count!=Steps.size()) return false;
        for (const auto& step:Steps)
        {
            std::string type,target;unsigned required=0;
            if (!(input>>std::quoted(type)>>std::quoted(target)) || !ReadUnsigned(input,required)
                || type!=step.Type || target!=step.Target || required!=step.Required) return false;
        }
        unsigned events=0,claimed=0;
        if (!ReadUnsigned(input,events) || events>512 || !ReadUnsigned(input,claimed) || claimed>1) return false;
        Progress candidate(Steps);
        for (unsigned i=0;i<events;++i)
        {
            std::string id;unsigned amount=0;
            if (!(input>>std::quoted(id)) || !ReadUnsigned(input,amount) || candidate.Complete()) return false;
            const auto& step=candidate.Steps[candidate.Current];
            const Result result=candidate.Apply(id,step.Type,step.Target,amount);
            if (result!=Result::Progressed && result!=Result::Completed) return false;
        }
        input>>std::ws;
        if (!input.eof() || (claimed && !candidate.ClaimReward())) return false;
        *this=std::move(candidate);
        return true;
    }
private:
    struct Event { std::string Id; unsigned Amount; };
    std::vector<Event> History;
    static bool ReadUnsigned(std::istream& input,unsigned& value)
    {
        std::string token;if (!(input>>token) || token.empty()) return false;
        const auto parsed=std::from_chars(token.data(),token.data()+token.size(),value);
        return parsed.ec==std::errc{} && parsed.ptr==token.data()+token.size();
    }
    std::vector<Step> Steps;
    std::unordered_set<std::string> Seen;
    std::size_t Current = 0;
    unsigned Count = 0;
    bool RewardClaimed = false;
};
}
