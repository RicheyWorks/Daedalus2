// SPDX-License-Identifier: MIT
#include "DaedalusSolReachCore.h"
#include <cstdio>
#include <limits>
using namespace daedalus::sol;
int Passed=0,Total=0;
void Check(const char* Name,bool OK) { ++Total; Passed+=OK; std::printf("%s %s\n",OK?"PASS":"FAIL",Name); }
bool Same(const State& A,const State& B) {
    return A.CleanWater==B.CleanWater && A.DirtyWater==B.DirtyWater && A.Eggs==B.Eggs && A.Milk==B.Milk &&
           A.Herbs==B.Herbs && A.Facts==B.Facts && A.Discoveries==B.Discoveries && A.KeeperMeals==B.KeeperMeals;
}
int main() {
    Effects Table; Table[1]={"heat_shield",120}; Table[2]={"fire_resist",120};
    Table[3]={"slow_hunger",300}; Table[4]={"stamina_regen_x2",90};
    const std::array<Herb,3> Good{{Herb::Dawnleaf,Herb::Rillprism,Herb::Dawnleaf}};
    State S; Check("starts at actual waterworks task",AdventureStage(S)==Stage::RestoreWaterworks);
    State Before=S; Check("empty well refuses atomically",FilterWell(S)==Error::NoDirtyWater && Same(S,Before));
    S.DirtyWater=1; Check("filter conserves water",FilterWell(S)==Error::None && S.DirtyWater==0 && S.CleanWater==21);
    Check("filter unlocks clue",AdventureStage(S)==Stage::DiscoverRing);
    Before=S;
    Check("unclosed ring consumes nothing",Brew(S,{{Herb::Dawnleaf,Herb::Rillprism,Herb::Cinderbud}},Table).Failure==Error::InvalidRecipe && Same(S,Before));
    auto Result=Brew(S,Good,Table);
    Check("ring applies shared effect",Result.Failure==Error::None && Result.EffectId=="heat_shield" && Result.Duration==240);
    Check("herbs and water consumed exactly",S.CleanWater==20 && S.Herbs[0]==1 && S.Herbs[1]==2);
    Check("discovery and quest recorded",S.Discoveries==2 && AdventureStage(S)==Stage::FeedKeeper);
    Before=S; Check("missing herbs atomic",Brew(S,Good,Table).Failure==Error::MissingHerbs && Same(S,Before));
    State Dry; Dry.CleanWater=0; Before=Dry;
    Check("dry brew atomic",Brew(Dry,Good,Table).Failure==Error::MissingWater && Same(Dry,Before));
    State Mono; Result=Brew(Mono,{{Herb::Rillprism,Herb::Rillprism,Herb::Rillprism}},Table);
    Check("single essence normal duration",Result.Failure==Error::None && Result.Duration==120 && Mono.Herbs[1]==0);
    State Invalid; Before=Invalid;
    Check("invalid enum refused before indexing",Brew(Invalid,{{static_cast<Herb>(-1),Herb::Rillprism,Herb::Dawnleaf}},Table).Failure==Error::InvalidRecipe && Same(Invalid,Before));
    Table[1].Duration=std::numeric_limits<double>::infinity();
    Check("nonfinite effect refused atomically",Brew(Invalid,Good,Table).Failure==Error::InvalidRecipe && Same(Invalid,Before));
    Table[1].Duration=120;
    Check("unknown centre has no effect",Brew(Invalid,{{Herb::Dawnleaf,Herb::Clearbell,Herb::Dawnleaf}},Table).Failure==Error::InvalidRecipe && Same(Invalid,Before));
    S.Eggs=1; S.Milk=1;
    Check("cooking consumes real products",CookForKeeper(S)==Error::None && S.Eggs==0 && S.Milk==0 && S.CleanWater==19);
    Check("sharing unlocks portal",AdventureStage(S)==Stage::PortalReady && S.KeeperMeals==1);
    Before=S; Check("no free second meal",CookForKeeper(S)==Error::MissingFood && Same(S,Before));
    Check("keeper remembers player",KeeperLine(S).find("back to life")!=std::string::npos);
    Sky Dawn{6.5,0,Weather::Clear},Noon{12,0,Weather::Clear},Wet{12,.7,Weather::Rain};
    Check("dawn clue visible",CisternClueVisible(Dawn));
    Check("noon clue hidden",!CisternClueVisible(Noon));
    Check("rain creates another discovery route",CisternClueVisible(Wet));
    Before=S; Check("cannot discover remotely",!DiscoverCistern(S,Dawn,false) && Same(S,Before));
    Check("actual stair discovery recorded",DiscoverCistern(S,Dawn,true) && (S.Facts&CisternFound));
    Check("repeat discovery is idempotent",!DiscoverCistern(S,Wet,true));
    Check("keeper walks to dawn well",KeeperLocation(S,Dawn)==KeeperPlace::Well);
    Check("keeper gardens at noon",KeeperLocation(S,Noon)==KeeperPlace::Garden);
    Check("keeper shelters from storm",KeeperLocation(S,{12,.7,Weather::Storm})==KeeperPlace::Home);
    Check("remembered meal changes evening route",KeeperLocation(S,{17,0,Weather::Clear})==KeeperPlace::Kitchen);
    Check("invalid clock does not reveal secrets",!CisternClueVisible({std::numeric_limits<double>::quiet_NaN(),.9,Weather::Rain}));
    State Overflow; Overflow.CleanWater=2147483647; Overflow.DirtyWater=1; Before=Overflow;
    Check("resource overflow refused",FilterWell(Overflow)==Error::InvalidState && Same(Overflow,Before));
    int Accepted=0; bool Exhaustive=true;
    for(int A=0;A<6;++A) for(int B=0;B<6;++B) for(int C=0;C<6;++C) {
        State Trial,Original=Trial;
        auto R=Brew(Trial,{{static_cast<Herb>(A),static_cast<Herb>(B),static_cast<Herb>(C)}},Table);
        bool Expected=A==C && B>=1 && B<=4;
        if((R.Failure==Error::None)!=Expected) Exhaustive=false;
        if(Expected) {
            ++Accepted;
            std::array<int,6> Counts{{0,0,0,0,0,0}}; ++Counts[A]; ++Counts[B]; ++Counts[C];
            for(int I=0;I<6;++I) if(Trial.Herbs[I]!=3-Counts[I]) Exhaustive=false;
            if(Trial.CleanWater!=19 || R.Duration!=Table[B].Duration*(A==B?1:2)) Exhaustive=false;
        } else if(!Same(Trial,Original)) Exhaustive=false;
    }
    Check("all 216 ordered recipes conserve resources and match rules",Exhaustive && Accepted==24);
    Check("invalid weather cannot reveal secret",!CisternClueVisible({7,.9,static_cast<Weather>(99)}));
    std::printf("%d/%d\n",Passed,Total); return Passed==Total?0:1;
}
