// SPDX-License-Identifier: MIT
#pragma once
// Arcade host scoreboard consumer. The host reads Status.Score (the scoreboard
// hook, catalog capability "scoreboard") and keeps the best score per game here.
// Persisted as one small text file (best_scores.dgs) next to the save slots:
//   DSB1\n<game_id> <score>\n...   ids sorted, one line per game, max 64 games.
// Old ids resolve through CanonicalGameId so renamed games keep their bests.
// Engine-free; the host owns file IO.
#include "DaedalusDesktopSaveSlots.h"
#include <cstdint>
#include <map>
#include <sstream>
#include <string>

namespace daedalus { namespace desktop {
class BestScores {
public:
    static constexpr std::int64_t MaxScore=1000000000000LL; // same clamp the host shows
    static constexpr std::size_t MaxGames=64;
    static constexpr const char* FileName="best_scores.dgs";
    // Returns true when Score is a new best for the game.
    bool Record(const std::string& RawId,std::int64_t Score) {
        if(!ValidId(RawId) || Score<0) return false;
        if(Score>MaxScore) Score=MaxScore;
        const std::string Id=CanonicalGameId(RawId);
        auto It=Best.find(Id);
        if(It==Best.end()) {
            if(Best.size()>=MaxGames) return false;
            Best.emplace(Id,Score); return true;
        }
        if(Score<=It->second) return false;
        It->second=Score; return true;
    }
    std::int64_t Get(const std::string& RawId) const {
        auto It=Best.find(CanonicalGameId(RawId));
        return It==Best.end()?0:It->second;
    }
    bool Has(const std::string& RawId) const { return Best.count(CanonicalGameId(RawId))!=0; }
    std::size_t Size() const { return Best.size(); }
    void Clear() { Best.clear(); }
    std::string Save() const {
        std::string Out="DSB1\n";
        for(const auto& Pair:Best) Out+=Pair.first+" "+std::to_string(Pair.second)+"\n";
        return Out;
    }
    // All-or-nothing: a bad file leaves the current table untouched.
    bool Restore(const std::string& Text) {
        if(Text.size()>4096) return false;
        std::istringstream In(Text);std::string Line;
        if(!std::getline(In,Line) || Line!="DSB1") return false;
        std::map<std::string,std::int64_t> Next;
        while(std::getline(In,Line)) {
            if(Line.empty()) continue;
            std::istringstream Row(Line);std::string Id,Extra;long long Score=-1;
            if(!(Row>>Id>>Score) || (Row>>Extra) || !ValidId(Id) || Score<0 || Score>MaxScore) return false;
            const std::string Canon=CanonicalGameId(Id);
            auto It=Next.find(Canon);
            if(It==Next.end()) Next.emplace(Canon,Score); else if(Score>It->second) It->second=Score;
            if(Next.size()>MaxGames) return false;
        }
        Best.swap(Next); return true;
    }
private:
    std::map<std::string,std::int64_t> Best;
    static bool ValidId(const std::string& Id) {
        if(Id.empty() || Id.size()>32) return false;
        for(char C:Id) if(!((C>='a' && C<='z') || (C>='0' && C<='9') || C=='_')) return false;
        return true;
    }
};
}} // namespace daedalus::desktop
