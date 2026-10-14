// SPDX-License-Identifier: MIT
#pragma once
#include <cmath>
#include <algorithm>
namespace daedalus { namespace hushveil {
enum class Mode {Patrol,Investigate,Search,Chase};
struct Point {double X=0,Y=0;};
inline bool Finite(Point P){return std::isfinite(P.X)&&std::isfinite(P.Y)&&std::abs(P.X)<=1000000&&std::abs(P.Y)<=1000000;}
inline double Distance(Point A,Point B){return std::hypot(A.X-B.X,A.Y-B.Y);}
// Host supplies visibility and sound attenuation from the room/door graph.
class Pursuer {
    Mode State=Mode::Patrol;
    Point Target;
    double Suspicion=0,SearchSeconds=0;
    bool SawHiding=false;
public:
    Mode Current() const{return State;}
    Point InvestigateTarget() const{return Target;}
    double Alertness() const{return Suspicion;}
    bool Hear(Point Source,Point Listener,double Loudness,double Attenuation){
        if(!Finite(Source)||!Finite(Listener)||!std::isfinite(Loudness)||!std::isfinite(Attenuation)||Loudness<0||Loudness>100||Attenuation<0||Attenuation>1)return false;
        double Heard=Loudness*Attenuation/(1+Distance(Source,Listener)*.1);
        if(Heard<8||State==Mode::Chase)return false;
        Target=Source;State=Mode::Investigate;Suspicion=std::min(100.0,Suspicion+Heard);SearchSeconds=0;return true;
    }
    bool Observe(Point Player,bool Visible,bool EnteringHide){
        if(!Finite(Player))return false;
        if(Visible){Target=Player;State=Mode::Chase;Suspicion=100;SawHiding=EnteringHide;SearchSeconds=0;}
        return true;
    }
    bool SafeHidden(bool InsideHide,bool Visible) const{return InsideHide&&!Visible&&!SawHiding;}
    void ReachLastKnown(){if(State==Mode::Investigate||State==Mode::Chase){State=Mode::Search;SearchSeconds=0;}}
    bool Advance(double Seconds){
        if(!std::isfinite(Seconds)||Seconds<0||Seconds>1)return false;
        if(State==Mode::Search){SearchSeconds+=Seconds;Suspicion=std::max(0.0,Suspicion-Seconds*3);
            if(SearchSeconds>=20){State=Mode::Patrol;SawHiding=false;}}
        return true;
    }
};
}}
