// SPDX-License-Identifier: MIT
// Portable Sol Reach transactions and environmental adventure. No engine/global state.
#pragma once
#include <array>
#include <cmath>
#include <cstdint>
#include <string>

namespace daedalus { namespace sol {
enum class Herb : int { Dawnleaf, Rillprism, Cinderbud, Stillmoss, Stridefern, Clearbell };
enum class Weather { Clear, Overcast, Rain, Storm, Fog };
enum class Error { None, InvalidState, InvalidRecipe, MissingHerbs, MissingWater, MissingFood, NoDirtyWater };
enum class Stage { RestoreWaterworks, DiscoverRing, FeedKeeper, PortalReady };
enum class KeeperPlace { Well, Garden, Kitchen, Home };
enum Fact : uint32_t { Filtered=1, Brewed=2, Cooked=4, Shared=8, CisternFound=16 };

struct Effect { std::string Id; double Duration=0; };
using Effects=std::array<Effect,6>; // Indexed by middle herb; empty ID means no same-essence effect.
struct State {
    int CleanWater=20, DirtyWater=0, Eggs=0, Milk=0;
    std::array<int,6> Herbs{{3,3,3,3,3,3}};
    uint32_t Facts=0, Discoveries=0;
    int KeeperMeals=0;
};
struct BrewResult { Error Failure=Error::None; std::string EffectId; double Duration=0; bool Doubled=false; };
struct Sky { double Hour=9, Wetness=0; Weather Conditions=Weather::Clear; };

inline bool Valid(const State& S) {
    if(S.CleanWater<0 || S.DirtyWater<0 || S.Eggs<0 || S.Milk<0 || S.KeeperMeals<0) return false;
    if((S.Facts & ~uint32_t(31)) || (S.Discoveries & ~uint32_t(63))) return false;
    for(int N:S.Herbs) if(N<0) return false;
    return true;
}
inline bool ValidSky(const Sky& S) {
    int W=static_cast<int>(S.Conditions);
    return W>=0 && W<=4 && std::isfinite(S.Hour) && S.Hour>=0 && S.Hour<24 &&
           std::isfinite(S.Wetness) && S.Wetness>=0 && S.Wetness<=1;
}
inline Stage AdventureStage(const State& S) {
    if(!(S.Facts & Filtered)) return Stage::RestoreWaterworks;
    if(!(S.Facts & Brewed)) return Stage::DiscoverRing;
    if(!(S.Facts & Shared)) return Stage::FeedKeeper;
    return Stage::PortalReady;
}
inline Error FilterWell(State& S) {
    if(!Valid(S)) return Error::InvalidState;
    if(S.DirtyWater<1) return Error::NoDirtyWater;
    if(S.CleanWater==2147483647) return Error::InvalidState;
    --S.DirtyWater; ++S.CleanWater; S.Facts |= Filtered; return Error::None;
}
inline BrewResult Brew(State& S,const std::array<Herb,3>& Ring,const Effects& Table) {
    BrewResult R;
    if(!Valid(S)) { R.Failure=Error::InvalidState; return R; }
    std::array<int,6> Needed{{0,0,0,0,0,0}};
    for(Herb H:Ring) {
        int I=static_cast<int>(H);
        if(I<0 || I>=6) { R.Failure=Error::InvalidRecipe; return R; }
        ++Needed[I];
    }
    int Middle=static_cast<int>(Ring[1]); const Effect& E=Table[Middle];
    R.Doubled=Ring[0]!=Ring[1];
    double Duration=E.Duration*(R.Doubled?2:1);
    if(Ring[0]!=Ring[2] || E.Id.empty() || !std::isfinite(Duration) || Duration<0) {
        R.Failure=Error::InvalidRecipe; return R;
    }
    if(S.CleanWater<1) { R.Failure=Error::MissingWater; return R; }
    for(int I=0;I<6;++I) if(S.Herbs[I]<Needed[I]) { R.Failure=Error::MissingHerbs; return R; }
    --S.CleanWater;
    for(int I=0;I<6;++I) S.Herbs[I]-=Needed[I];
    S.Facts |= Brewed; S.Discoveries |= uint32_t(1)<<Middle;
    R.EffectId=E.Id; R.Duration=Duration; return R;
}
inline Error CookForKeeper(State& S) {
    if(!Valid(S)) return Error::InvalidState;
    if(S.Eggs<1 || S.Milk<1) return Error::MissingFood;
    if(S.CleanWater<1) return Error::MissingWater;
    if(S.KeeperMeals==2147483647) return Error::InvalidState;
    --S.Eggs; --S.Milk; --S.CleanWater; ++S.KeeperMeals; S.Facts |= Cooked|Shared;
    return Error::None;
}
// The secret can be found through either clear dawn shadows or wet footprints.
// Brewing remains available all day; the optional secret never blocks the main journey.
inline bool CisternClueVisible(const Sky& S) {
    if(!ValidSky(S)) return false;
    return (S.Hour>=6 && S.Hour<8 && S.Conditions==Weather::Clear) || S.Wetness>=.6;
}
inline bool DiscoverCistern(State& S,const Sky& Context,bool AtHiddenStair) {
    if(!Valid(S) || !AtHiddenStair || !CisternClueVisible(Context)) return false;
    bool New=!(S.Facts&CisternFound); S.Facts |= CisternFound; return New;
}
inline KeeperPlace KeeperLocation(const State& S,const Sky& Context) {
    if(!ValidSky(Context) || Context.Conditions==Weather::Storm || Context.Hour<6 || Context.Hour>=20)
        return KeeperPlace::Home;
    if((S.Facts&Shared) && Context.Hour>=16) return KeeperPlace::Kitchen;
    return Context.Hour<10 ? KeeperPlace::Well : KeeperPlace::Garden;
}
inline std::string KeeperLine(const State& S) {
    if(S.KeeperMeals>1) return "You remembered the old kitchen again. The garden remembers you.";
    if(S.Facts&Shared) return "You brought the waterworks back to life. Follow the arch when you are ready.";
    if(S.Facts&Brewed) return "A closed ring! Now our flock and goat need water, and the kitchen needs their gifts.";
    if(S.Facts&Filtered) return "The beginning returns at the end; the middle tells the spring what to remember.";
    return "The well is cloudy. Bring its water through the filter, and I will show you the broken circle.";
}
}} // namespace daedalus::sol
