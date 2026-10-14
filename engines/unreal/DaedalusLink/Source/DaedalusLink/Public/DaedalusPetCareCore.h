// SPDX-License-Identifier: MIT
// Original ComputerPets rules: Copyright (c) 2026 RicheyWorks.
// Rui's numeric care and ribbon rules, ported from RicheyWorks/computerpets.
// Source pins and executed Python oracle live in core-test/pet_care_parity.txt.
// Engine-free C++17. No Qt, editor, host clock, persistence, assets, or line picker.
// The adapter owns dialogue and chooses the host's civil hour (Rui rests 01:00-06:00).
#pragma once
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <functional>
#include <limits>
#include <string>
#include <vector>

namespace daedalus { namespace petcare {

enum class Pose { Idle, Walk, Sit, Eat, Sleep, Play };
enum class Command { Idle, Eat, Play, Hide, Enter, Sit, Sleep, Talk };
enum class Action { Feed, Treat, Play, Hide, Call, Clean, Medicine, Rest, Bath, Talk, Praise };
enum class CareError { None, InvalidState, InvalidInput, InvalidRandom };

struct Object { std::int64_t Id=0; double X=0; };
struct State {
    int Hunger=78, Mood=74, Energy=80, Hygiene=86, Health=92, Bond=18;
    bool Sick=false, Hidden=false;
    Pose Anim=Pose::Idle;
    std::int64_t LastTick=0;
    std::vector<Object> Mess, Gifts;
};
struct CareResult {
    State Value;
    Pose Anim=Pose::Idle;
    Command Cmd=Command::Idle;
    CareError Failure=CareError::None;
};

// Python round(), including half ties, rather than std::round()'s away-from-zero.
// Contract: finite input. Public mutations reject nonfinite elapsed time/randomness.
namespace detail {
inline int ClampFinite(double N) {
    if(N<=0) return 0;
    if(N>=100) return 100;
    const double Base=std::floor(N), Fraction=N-Base;
    const int I=static_cast<int>(Base);
    return I + ((Fraction>0.5 || (Fraction==0.5 && I%2!=0)) ? 1 : 0);
}
} // namespace detail
inline bool TryClamp(double N,int& Value) {
    if(!std::isfinite(N)) return false;
    Value=detail::ClampFinite(N); return true;
}
inline bool Valid(const State& S) {
    for(int N : {S.Hunger,S.Mood,S.Energy,S.Hygiene,S.Health,S.Bond})
        if(N<0 || N>100) return false;
    const int P=static_cast<int>(S.Anim);
    if(P<0 || P>static_cast<int>(Pose::Play)) return false;
    for(const auto& O:S.Mess) if(!std::isfinite(O.X)) return false;
    for(const auto& O:S.Gifts) if(!std::isfinite(O.X)) return false;
    return true;
}
inline bool RuiRestingHour(int CivilHour) { return CivilHour>=1 && CivilHour<6; }
inline const char* Vitals(const State& S,bool Blue=false) {
    if(S.Hidden) return "Hidden";
    if(Blue) return "Blue";
    if(S.Sick) return "Unwell";
    if(S.Hunger<22) return "Hungry";
    if(S.Hygiene<24) return "Unkempt";
    if(S.Energy<20) return "Tired";
    if(S.Mood<32) return "Moody";
    return "Settled";
}
inline CareResult Apply(const State& Before,Action Act) {
    CareResult R; R.Value=Before;
    if(!Valid(Before)) { R.Failure=CareError::InvalidState; return R; }
    const int A=static_cast<int>(Act);
    if(A<0 || A>static_cast<int>(Action::Praise)) { R.Failure=CareError::InvalidInput; return R; }
    if(Before.Hidden && (Act==Action::Feed || Act==Action::Treat || Act==Action::Play || Act==Action::Hide))
        return R; // The returned Idle pose does not overwrite the hidden state's existing pose.
    State& S=R.Value;
    switch(Act) {
    case Action::Feed:
        S.Hunger=detail::ClampFinite(S.Hunger+28); S.Mood=detail::ClampFinite(S.Mood+6);
        S.Energy=detail::ClampFinite(S.Energy-6); S.Bond=detail::ClampFinite(S.Bond+2);
        R.Anim=Pose::Eat; R.Cmd=Command::Eat; break;
    case Action::Treat:
        S.Hunger=detail::ClampFinite(S.Hunger+12); S.Mood=detail::ClampFinite(S.Mood+5); S.Bond=detail::ClampFinite(S.Bond+1);
        R.Anim=Pose::Eat; R.Cmd=Command::Eat; break;
    case Action::Play:
        S.Hunger=detail::ClampFinite(S.Hunger-8); S.Mood=detail::ClampFinite(S.Mood+26);
        S.Energy=detail::ClampFinite(S.Energy-14); S.Bond=detail::ClampFinite(S.Bond+3);
        R.Anim=Pose::Play; R.Cmd=Command::Play; break;
    case Action::Hide:
        S.Hidden=true; R.Anim=Pose::Walk; R.Cmd=Command::Hide; break;
    case Action::Call:
        S.Hidden=false; S.Mood=detail::ClampFinite(S.Mood+4); S.Bond=detail::ClampFinite(S.Bond+1);
        R.Anim=Pose::Walk; R.Cmd=Command::Enter; break;
    case Action::Clean:
        S.Hygiene=detail::ClampFinite(S.Hygiene+38); S.Mood=detail::ClampFinite(S.Mood+8); S.Bond=detail::ClampFinite(S.Bond+2);
        S.Mess.clear(); R.Anim=Pose::Sit; R.Cmd=Command::Sit; break;
    case Action::Medicine:
        S.Sick=false; S.Health=detail::ClampFinite(S.Health+28); S.Mood=detail::ClampFinite(S.Mood-2); S.Bond=detail::ClampFinite(S.Bond+3);
        R.Anim=Pose::Sit; R.Cmd=Command::Sit; break;
    case Action::Rest:
        S.Hunger=detail::ClampFinite(S.Hunger-3); S.Mood=detail::ClampFinite(S.Mood+4);
        S.Energy=detail::ClampFinite(S.Energy+34); S.Bond=detail::ClampFinite(S.Bond+1);
        R.Anim=Pose::Sleep; R.Cmd=Command::Sleep; break;
    case Action::Bath:
        S.Hygiene=detail::ClampFinite(S.Hygiene+48); S.Mood=detail::ClampFinite(S.Mood+6);
        S.Energy=detail::ClampFinite(S.Energy-6); S.Bond=detail::ClampFinite(S.Bond+2);
        R.Anim=Pose::Sit; R.Cmd=Command::Sit; break;
    case Action::Talk:
        S.Bond=detail::ClampFinite(S.Bond+1); R.Anim=Pose::Sit; R.Cmd=Command::Talk; break;
    case Action::Praise:
        S.Mood=detail::ClampFinite(S.Mood+12); S.Bond=detail::ClampFinite(S.Bond+2);
        R.Anim=Pose::Sit; R.Cmd=Command::Sit; break;
    }
    S.Anim=R.Anim;
    return R;
}
inline CareResult PickMess(const State& Before,std::int64_t Id) {
    CareResult R; R.Value=Before;
    if(!Valid(Before)) { R.Failure=CareError::InvalidState; return R; }
    State& S=R.Value;
    S.Mess.erase(std::remove_if(S.Mess.begin(),S.Mess.end(),[Id](const Object& O){return O.Id==Id;}),S.Mess.end());
    // Source awards these deltas even if the supplied ID is absent.
    S.Hygiene=detail::ClampFinite(S.Hygiene+8); S.Mood=detail::ClampFinite(S.Mood+3); S.Anim=Pose::Sit;
    R.Anim=Pose::Sit; R.Cmd=Command::Sit; return R;
}

struct DecayResult { State Value; CareError Failure=CareError::None; };
// Failure preserves State only; callback draws are consumed and callback exceptions propagate.
inline DecayResult Decay(const State& Before,double ElapsedMs,std::int64_t NowMs,
                        bool Resting,const std::function<double()>& Random) {
    DecayResult R; R.Value=Before;
    if(!Valid(Before)) { R.Failure=CareError::InvalidState; return R; }
    if(!std::isfinite(ElapsedMs) || !Random || NowMs>std::numeric_limits<std::int64_t>::max()-20) {
        R.Failure=CareError::InvalidInput; return R;
    }
    State Next=Before;
    const double Dt=std::max(0.0,ElapsedMs);
    const bool Asleep=Resting && !Before.Hidden && !Before.Sick;
    constexpr double HungerRate=100.0/(6*60*60*1000), MoodRate=100.0/(12*60*60*1000);
    constexpr double EnergyRate=100.0/(9*60*60*1000), HygieneRate=100.0/(14*60*60*1000);
    constexpr double HealthDown=(6.0/(10*60*60*1000))*100, HealthUp=(2.0/(10*60*60*1000))*100;
    Next.Hunger=detail::ClampFinite(Before.Hunger-Dt*HungerRate*(Asleep ? 0.45 : 1));
    Next.Mood=detail::ClampFinite(Before.Mood-Dt*(MoodRate*(Before.Sick ? 1.3 : 1)));
    Next.Energy=detail::ClampFinite(Asleep ? Before.Energy+Dt*(18.0/3600000) : Before.Energy-Dt*EnergyRate);
    Next.Hygiene=detail::ClampFinite(Before.Hygiene-Dt*HygieneRate);
    Next.Health=detail::ClampFinite(Next.Hunger<18 || Next.Hygiene<18 ? Before.Health-Dt*HealthDown : Before.Health+Dt*HealthUp);
    if(!Next.Sick && Next.Health<32) Next.Sick=true;
    if(Next.Sick && Next.Health>64 && Next.Hygiene>40) Next.Sick=false;
    bool BadRandom=false;
    const auto Draw=[&]() {
        const double N=Random();
        if(!std::isfinite(N) || N<0 || N>=1) BadRandom=true;
        return N;
    };
    // Preserve source draw order: a mess roll, optional position, a gift roll, optional position.
    const double MessRoll=Draw();
    if(Next.Hygiene<42 && Next.Mess.size()<5 && MessRoll<std::min(0.35,Dt/120000)) {
        const double X=12+Draw()*76;
        Next.Mess.push_back({NowMs+static_cast<std::int64_t>(Next.Mess.size()),X});
    }
    const double GiftRoll=Draw();
    if(Next.Bond>=25 && Next.Gifts.size()<2 && GiftRoll<std::min(0.2,Dt/180000)) {
        const double X=14+Draw()*72;
        Next.Gifts.push_back({NowMs+17+static_cast<std::int64_t>(Next.Gifts.size()),X});
    }
    if(BadRandom) { R.Failure=CareError::InvalidRandom; return R; }
    Next.LastTick=NowMs;
    R.Value=Next; return R;
}

enum class Via { Catch, Arrive };
enum class HopAct { None, Play, Snack, Hide, Idle };
struct Chase { bool Taken=false; std::string Cmd="seek", Mark="lure"; };
struct Hop {
    HopAct Act=HopAct::None;
    Chase Next;
    int ApplyPlay=0, PersistPlay=0, IssuePlay=0, IssueEat=0;
};
inline Hop PlayHop(const Chase& C,Via V,bool OnCare=false) {
    Hop H; H.Next=C;
    if(V==Via::Arrive && C.Cmd=="leave") H.Act=HopAct::Hide;
    else if(V==Via::Catch) {
        if(!C.Taken && C.Mark=="lure") H.Act=HopAct::Play;
    } else if(V==Via::Arrive) {
        if(C.Cmd=="seek" && C.Mark=="treat") H.Act=HopAct::Snack;
        else if(C.Cmd=="seek" && C.Mark=="lure" && !C.Taken) H.Act=HopAct::Play;
        else if(C.Cmd=="wander" || C.Cmd=="play" || C.Cmd=="eat" || C.Cmd=="enter") H.Act=HopAct::Idle;
    }
    switch(H.Act) {
    case HopAct::Play:
        H.Next={true,"play",""}; H.ApplyPlay=OnCare ? 0 : 1;
        H.PersistPlay=OnCare ? 1 : 0; H.IssuePlay=1; break;
    case HopAct::Snack: H.Next={true,"eat",""}; H.IssueEat=1; break;
    case HopAct::Hide: H.Next.Taken=true; break;
    case HopAct::Idle: H.Next.Cmd="idle"; break;
    case HopAct::None: break;
    }
    return H;
}
struct ChaseResult {
    Chase Next;
    std::vector<HopAct> Acts;
    int ApplyPlay=0, PersistPlay=0, IssuePlay=0, IssueEat=0;
};
inline ChaseResult PlayChase(const std::vector<Via>& Vias,const Chase& Start,bool OnCare=false) {
    ChaseResult R; R.Next=Start;
    for(Via V:Vias) {
        const Hop H=PlayHop(R.Next,V,OnCare);
        R.Next=H.Next; R.Acts.push_back(H.Act); R.ApplyPlay+=H.ApplyPlay;
        R.PersistPlay+=H.PersistPlay; R.IssuePlay+=H.IssuePlay; R.IssueEat+=H.IssueEat;
    }
    return R;
}

}} // namespace daedalus::petcare
