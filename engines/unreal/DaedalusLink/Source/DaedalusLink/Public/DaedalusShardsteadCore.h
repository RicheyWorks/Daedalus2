// SPDX-License-Identifier: MIT
#pragma once
#include <array>
#include <utility>
#include <vector>
#include <cstdint>
#include <string>
#include <map>
#include <set>
#include <algorithm>
namespace daedalus { namespace shardstead {
enum class Resource : unsigned { Food, Energy, Iron, Copper, Crystal, Stone, Count };
using Stock=std::array<int,static_cast<unsigned>(Resource::Count)>;
inline unsigned Slot(Resource R){return static_cast<unsigned>(R);}
inline bool Valid(Resource R){return Slot(R)<Slot(Resource::Count);}
inline bool Identity(const std::string& S){return !S.empty()&&S.size()<=100&&std::all_of(S.begin(),S.end(),[](unsigned char C){return C>32&&C!=127;});}
// Server-owned deterministic survey, keyed by immutable realm seed and island number.
inline Stock Survey(std::uint64_t Seed,std::uint32_t Island) {
    std::uint64_t S=Seed^(static_cast<std::uint64_t>(Island)*0x9e3779b97f4a7c15ULL);
    auto Next=[&](){S+=0x9e3779b97f4a7c15ULL;auto Z=S;Z=(Z^(Z>>30))*0xbf58476d1ce4e5b9ULL;Z=(Z^(Z>>27))*0x94d049bb133111ebULL;return Z^(Z>>31);};
    Stock Out{};for(auto& V:Out)V=40+static_cast<int>(Next()%161);
    Out[2+Island%4]+=200;return Out;
}
struct Crew {Stock Cargo{{12,12,0,0,0,0}};int Friendship=0,Infamy=0;};
struct Plot {std::string Owner,Worker;Resource Task=Resource::Stone;Stock Remaining{};bool Assigned=false;};
struct Snapshot {
    unsigned Version=1;std::uint64_t Seed=0,Cycle=0;
    std::map<std::string,Crew> Crews;std::map<std::uint32_t,Plot> Plots;
};
inline bool SameState(const Snapshot& A,const Snapshot& B){
    if(A.Version!=B.Version||A.Seed!=B.Seed||A.Cycle!=B.Cycle||A.Crews.size()!=B.Crews.size()||A.Plots.size()!=B.Plots.size())return false;
    for(const auto& Pair:A.Crews){auto I=B.Crews.find(Pair.first);if(I==B.Crews.end()||Pair.second.Cargo!=I->second.Cargo||Pair.second.Friendship!=I->second.Friendship||Pair.second.Infamy!=I->second.Infamy)return false;}
    for(const auto& Pair:A.Plots){auto I=B.Plots.find(Pair.first);if(I==B.Plots.end())return false;
        const auto& X=Pair.second;const auto& Y=I->second;
        if(X.Owner!=Y.Owner||X.Worker!=Y.Worker||X.Task!=Y.Task||X.Remaining!=Y.Remaining||X.Assigned!=Y.Assigned)return false;}
    return true;
}
struct TabRow {std::uint32_t Island;Resource Task;int Remaining;bool Working;std::string Worker;};
// Not an NFT ownership service. Host must authorize proximity, realm access and land rights.
class Economy {
    std::uint64_t Seed,LastCycle=0;
    std::map<std::string,Crew> Crews;
    std::map<std::uint32_t,Plot> Plots;
    std::set<std::string> Workers;
    static constexpr int MaxStock=1000000;
    static bool Amounts(const Stock& A){return std::all_of(A.begin(),A.end(),[](int V){return V>=0&&V<=MaxStock;});}
public:
    explicit Economy(std::uint64_t RealmSeed):Seed(RealmSeed){}
    bool Join(const std::string& Player){return Identity(Player)&&Crews.size()<256&&Crews.emplace(Player,Crew{}).second;}
    const Crew* Stats(const std::string& Player) const {auto I=Crews.find(Player);return I==Crews.end()?nullptr:&I->second;}
    bool Claim(const std::string& Player,std::uint32_t Island,bool HostLandPermission) {
        if(!HostLandPermission||!Stats(Player)||Island>=10000||Plots.size()>=10000||Plots.count(Island))return false;
        Plot P;P.Owner=Player;P.Remaining=Survey(Seed,Island);Plots.emplace(Island,P);return true;
    }
    bool Assign(const std::string& Player,std::uint32_t Island,const std::string& Worker,Resource Task) {
        auto I=Plots.find(Island);
        if(I==Plots.end()||I->second.Owner!=Player||!Identity(Worker)||!Valid(Task))return false;
        if(I->second.Worker==Worker){I->second.Task=Task;return true;}
        if(Workers.count(Worker))return false;
        if(!I->second.Worker.empty())Workers.erase(I->second.Worker);
        Workers.insert(Worker);I->second.Worker=Worker;I->second.Task=Task;I->second.Assigned=true;return true;
    }
    // Monotonic host cycles; no offline catch-up or client timestamp authority.
    bool Produce(std::uint64_t Cycle) {
        if(LastCycle==UINT64_MAX||Cycle==0||Cycle!=LastCycle+1)return false;
        // Renewable food first, then energy, then finite mineral extraction.
        // A hungry farmer can grow one emergency ration without inputs.
        for(int Pass=0;Pass<3;++Pass)for(auto& Pair:Plots){
            auto& P=Pair.second;int Job=P.Task==Resource::Food?0:P.Task==Resource::Energy?1:2;
            if(!P.Assigned||Job!=Pass)continue;
            auto& C=Crews.find(P.Owner)->second;unsigned K=Slot(P.Task);
            int Yield=Job<2?1+P.Remaining[K]/100:std::min(3,P.Remaining[K]);
            if(Job==0 && C.Cargo[0]==0)Yield=1;
            if(Job!=0 && C.Cargo[0]<1)continue;
            if(Job==2 && C.Cargo[1]<1)continue;
            Yield=std::min(Yield,MaxStock-C.Cargo[K]);if(Yield<=0)continue;
            if(Job!=0)--C.Cargo[0];if(Job==2)--C.Cargo[1];
            C.Cargo[K]+=Yield;if(Job==2)P.Remaining[K]-=Yield;
        }
        LastCycle=Cycle;return true;
    }
    bool Mine(const std::string& Player,std::uint32_t Island,Resource R,int Quantity,bool HostAtDeposit) {
        auto I=Plots.find(Island);if(!HostAtDeposit||I==Plots.end()||I->second.Owner!=Player||!Valid(R)||Slot(R)<Slot(Resource::Iron)||Quantity<=0||Quantity>25)return false;
        auto& C=Crews.find(Player)->second;unsigned K=Slot(R);
        if(I->second.Remaining[K]<Quantity||C.Cargo[K]>MaxStock-Quantity)return false;
        C.Cargo[K]+=Quantity;I->second.Remaining[K]-=Quantity;return true;
    }
    // Both offers must already be authenticated and accepted by the host. Atomic in-memory exchange.
    bool Trade(const std::string& A,const std::string& B,const Stock& OfferA,const Stock& OfferB,bool BothAccepted) {
        if(A==B||!BothAccepted||!Amounts(OfferA)||!Amounts(OfferB)||!Stats(A)||!Stats(B))return false;
        auto& CA=Crews.find(A)->second;auto& CB=Crews.find(B)->second;Stock NA{},NB{};
        int Total=0;for(unsigned K=0;K<Slot(Resource::Count);++K){
            if(CA.Cargo[K]<OfferA[K]||CB.Cargo[K]<OfferB[K])return false;
            NA[K]=CA.Cargo[K]-OfferA[K]+OfferB[K];NB[K]=CB.Cargo[K]-OfferB[K]+OfferA[K];Total+=OfferA[K]+OfferB[K];
        }
        if(!Total||!Amounts(NA)||!Amounts(NB))return false;
        CA.Cargo=NA;CB.Cargo=NB;CA.Friendship=std::min(100,CA.Friendship+1);CB.Friendship=std::min(100,CB.Friendship+1);return true;
    }
    bool RaidCargo(const std::string& Pirate,const std::string& Victim,Resource R,int Quantity,bool HostCombatWon,bool HostPiracyZone) {
        if(!HostCombatWon||!HostPiracyZone||Pirate==Victim||!Valid(R)||Quantity<=0||Quantity>25||!Stats(Pirate)||!Stats(Victim))return false;
        auto& A=Crews.find(Pirate)->second;auto& B=Crews.find(Victim)->second;unsigned K=Slot(R);
        if(B.Cargo[K]<Quantity||A.Cargo[K]>MaxStock-Quantity)return false;
        B.Cargo[K]-=Quantity;A.Cargo[K]+=Quantity;A.Infamy=std::min(100,A.Infamy+5);return true;
    }
    std::uint64_t Cycle() const{return LastCycle;}
    Snapshot Export() const{return {1,Seed,LastCycle,Crews,Plots};}
    // Validate a complete candidate before assigning; reject partial/cross-realm restores.
    bool Restore(const Snapshot& Saved) {
        if(!Crews.empty()||!Plots.empty()||LastCycle!=0||Saved.Version!=1||Saved.Seed!=Seed||Saved.Crews.size()>256||Saved.Plots.size()>10000)return false;
        std::set<std::string> LoadedWorkers;
        for(const auto& Pair:Saved.Crews){const auto& C=Pair.second;
            if(!Identity(Pair.first)||!Amounts(C.Cargo)||C.Friendship<0||C.Friendship>100||C.Infamy<0||C.Infamy>100)return false;}
        for(const auto& Pair:Saved.Plots){const auto& P=Pair.second;
            if(Pair.first>=10000||!Saved.Crews.count(P.Owner)||!Valid(P.Task)||!Amounts(P.Remaining))return false;
            Stock Initial=Survey(Seed,Pair.first);
            for(unsigned K=0;K<Slot(Resource::Count);++K)if(P.Remaining[K]>Initial[K]||(K<2&&P.Remaining[K]!=Initial[K]))return false;
            if(P.Assigned){if(!Identity(P.Worker)||!LoadedWorkers.insert(P.Worker).second)return false;}
            else if(!P.Worker.empty())return false;
        }
        Crews=Saved.Crews;Plots=Saved.Plots;Workers=std::move(LoadedWorkers);LastCycle=Saved.Cycle;return true;
    }
    std::vector<TabRow> Tab(const std::string& Player) const {
        std::vector<TabRow> Rows;for(const auto& Pair:Plots)if(Pair.second.Owner==Player)
            Rows.push_back({Pair.first,Pair.second.Task,Pair.second.Remaining[Slot(Pair.second.Task)],Pair.second.Assigned,Pair.second.Worker});
        return Rows;
    }
};
}}
