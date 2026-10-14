// SPDX-License-Identifier: MIT
#pragma once
#include "DaedalusShardsteadCore.h"
namespace daedalus { namespace refuge {
enum class RunState {Active,RescuePending,Rescued,Lost};
struct RescuePolicy {unsigned DailyChanceBasisPoints=500;bool AutomaticRescue=true;};
struct RunSnapshot {unsigned Version=1;std::string RunId,Player;std::uint64_t Seed=0;unsigned Day=0;RescuePolicy Policy;bool RankedLongest=false;RunState State=RunState::Active;std::string RescueVoyage;unsigned LivesSaved=0;};
// Original metaverse run policy. One host roll per completed survival day.
class Run {
    RunSnapshot S;
    static unsigned Roll(std::uint64_t Seed,unsigned Day){
        auto X=Seed^(static_cast<std::uint64_t>(Day)*0x9e3779b97f4a7c15ULL);X=(X^(X>>30))*0xbf58476d1ce4e5b9ULL;X=(X^(X>>27))*0x94d049bb133111ebULL;
        return static_cast<unsigned>((X^(X>>31))%10000);
    }
public:
    Run(const std::string& RunId,const std::string& Player,std::uint64_t HostSeed,RescuePolicy Policy):S{1,RunId,Player,HostSeed,0,Policy,!Policy.AutomaticRescue,RunState::Active,{},0}{}
    bool Valid() const{return shardstead::Identity(S.RunId)&&shardstead::Identity(S.Player)&&S.Policy.DailyChanceBasisPoints<=10000;}
    const RunSnapshot& View() const{return S;}
    bool SetAutomaticRescue(bool Enabled){
        if(!Valid()||S.State!=RunState::Active)return false;
        S.Policy.AutomaticRescue=Enabled;
        // Enabling even once permanently removes this run from the no-rescue leaderboard.
        if(Enabled)S.RankedLongest=false;
        else if(S.Day==0)S.RankedLongest=true;return true;
    }
    bool CompleteDay(unsigned ExpectedDay,bool HostSurvivorsRemain){
        if(!Valid()||ExpectedDay!=S.Day||S.Day>=36500||S.State==RunState::Rescued||S.State==RunState::Lost)return false;
        ++S.Day;
        if(!HostSurvivorsRemain){S.State=RunState::Lost;return true;}
        if(S.State==RunState::Active&&S.Policy.AutomaticRescue&&Roll(S.Seed,S.Day)<S.Policy.DailyChanceBasisPoints)S.State=RunState::RescuePending;
        return true;
    }
    bool BindIslandArk(const std::string& VoyageId,bool HostDepartureVerified){
        if(!Valid()||S.State!=RunState::RescuePending||!HostDepartureVerified||!shardstead::Identity(VoyageId))return false;
        if(!S.RescueVoyage.empty())return S.RescueVoyage==VoyageId;
        S.RescueVoyage=VoyageId;return true;
    }
    // Luck requests a rescue; only an actual host-verified ark arrival ends the run.
    bool ConfirmRescue(const std::string& VoyageId,unsigned LivesSaved,bool HostSafeLandingVerified){
        if(!Valid()||!HostSafeLandingVerified||!shardstead::Identity(VoyageId)||VoyageId!=S.RescueVoyage||LivesSaved==0||LivesSaved>1000000)return false;
        if(S.State==RunState::Rescued)return S.LivesSaved==LivesSaved;
        if(S.State!=RunState::RescuePending)return false;
        S.State=RunState::Rescued;S.LivesSaved=LivesSaved;return true;
    }
    bool Restore(const RunSnapshot& Saved){
        if(!Valid()||S.Day!=0||S.State!=RunState::Active||Saved.Version!=1||Saved.RunId!=S.RunId||Saved.Player!=S.Player||Saved.Seed!=S.Seed||Saved.Policy.DailyChanceBasisPoints!=S.Policy.DailyChanceBasisPoints||Saved.Day>36500||static_cast<unsigned>(Saved.State)>static_cast<unsigned>(RunState::Lost))return false;
        if(Saved.Day==0&&Saved.State!=RunState::Active)return false;
        if((Saved.State==RunState::RescuePending||Saved.State==RunState::Rescued||!Saved.RescueVoyage.empty())&&!Saved.Policy.AutomaticRescue)return false;
        if(Saved.RankedLongest&&(Saved.Policy.AutomaticRescue||!Saved.RescueVoyage.empty()||Saved.State==RunState::RescuePending||Saved.State==RunState::Rescued))return false;
        if(!Saved.RescueVoyage.empty()&&!shardstead::Identity(Saved.RescueVoyage))return false;
        if(Saved.State==RunState::Rescued&&(Saved.RescueVoyage.empty()||Saved.LivesSaved==0||Saved.LivesSaved>1000000))return false;
        if(Saved.State!=RunState::Rescued&&Saved.LivesSaved!=0)return false;
        if(Saved.State==RunState::Active&&!Saved.RescueVoyage.empty())return false;
        S=Saved;return Valid();
    }
};
struct SurvivalScore {std::string Player,RunId;unsigned Days=0;bool Finished=false;};
class LongestLivedBoard {
    std::map<std::string,SurvivalScore> Runs;
public:
    bool Record(const RunSnapshot& S,bool HostDurableRunVerified){
        if(!HostDurableRunVerified||S.Version!=1||S.Policy.DailyChanceBasisPoints>10000||!S.RescueVoyage.empty()||S.LivesSaved!=0||!shardstead::Identity(S.Player)||!shardstead::Identity(S.RunId)||!S.RankedLongest||S.Policy.AutomaticRescue||(S.State!=RunState::Active&&S.State!=RunState::Lost)||S.Day==0||S.Day>36500)return false;
        auto I=Runs.find(S.RunId);
        bool Finished=S.State==RunState::Lost;
        if(I!=Runs.end()){
            if(I->second.Player!=S.Player||S.Day<I->second.Days||(I->second.Finished&&(!Finished||S.Day!=I->second.Days)))return false;
            I->second.Days=S.Day;I->second.Finished=Finished;return true;
        }
        if(Runs.size()>=10000)return false;
        Runs.emplace(S.RunId,SurvivalScore{S.Player,S.RunId,S.Day,Finished});return true;
    }
    const std::map<std::string,SurvivalScore>& Export() const{return Runs;}
    bool Restore(const std::map<std::string,SurvivalScore>& Saved){
        if(!Runs.empty()||Saved.size()>10000)return false;
        for(const auto& Pair:Saved){const auto& V=Pair.second;if(Pair.first!=V.RunId||!shardstead::Identity(V.RunId)||!shardstead::Identity(V.Player)||V.Days==0||V.Days>36500)return false;}
        Runs=Saved;return true;
    }
    std::vector<SurvivalScore> Top(unsigned Limit=20) const{
        std::map<std::string,SurvivalScore> Best;
        for(const auto& Pair:Runs){const auto& V=Pair.second;auto I=Best.find(V.Player);if(I==Best.end()||I->second.Days<V.Days||(I->second.Days==V.Days&&I->second.RunId>V.RunId))Best[V.Player]=V;}
        std::vector<SurvivalScore> Out;for(const auto& Pair:Best)Out.push_back(Pair.second);
        std::sort(Out.begin(),Out.end(),[](const SurvivalScore& A,const SurvivalScore& B){return A.Days!=B.Days?A.Days>B.Days:A.Player<B.Player;});
        if(Out.size()>std::min(Limit,100u))Out.resize(std::min(Limit,100u));return Out;
    }
};
// The save-count board consumes unique, protected ecosystem rescue identities, not species names.
class MostSavedBoard {
    std::map<std::string,std::string> SavedLife;
public:
    bool Record(const std::string& LifeId,const std::string& Rescuer,bool HostSafeLandingVerified){
        if(!HostSafeLandingVerified||!shardstead::Identity(LifeId)||!shardstead::Identity(Rescuer))return false;
        auto I=SavedLife.find(LifeId);if(I!=SavedLife.end())return I->second==Rescuer;
        if(SavedLife.size()>=100000)return false;SavedLife.emplace(LifeId,Rescuer);return true;
    }
    const std::map<std::string,std::string>& Export() const{return SavedLife;}
    bool Restore(const std::map<std::string,std::string>& Saved){
        if(!SavedLife.empty()||Saved.size()>100000)return false;
        for(const auto& Pair:Saved)if(!shardstead::Identity(Pair.first)||!shardstead::Identity(Pair.second))return false;
        SavedLife=Saved;return true;
    }
    std::vector<std::pair<std::string,unsigned>> Top(unsigned Limit=20) const{
        std::map<std::string,unsigned> Counts;for(const auto& Pair:SavedLife)++Counts[Pair.second];
        std::vector<std::pair<std::string,unsigned>> Out(Counts.begin(),Counts.end());
        std::sort(Out.begin(),Out.end(),[](const auto& A,const auto& B){return A.second!=B.second?A.second>B.second:A.first<B.first;});
        if(Out.size()>std::min(Limit,100u))Out.resize(std::min(Limit,100u));return Out;
    }
};
}}
