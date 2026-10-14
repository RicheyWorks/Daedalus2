// SPDX-License-Identifier: MIT
#pragma once
#include <array>
#include <cstdint>
#include <algorithm>
namespace daedalus { namespace refuge {
// Original daily survival simulation. Host applies a single authenticated decision per day.
struct Resident {int Health=100,Hunger=0,Thirst=0,Morale=70;bool Alive=true;};
struct Supplies {int Food=16,Water=20,Medicine=3,RepairParts=4;};
struct Decision {std::array<bool,4> Feed{{false,false,false,false}},Water{{false,false,false,false}},Treat{{false,false,false,false}};bool Repair=false;};
struct DayReport {unsigned Day=0;int Alive=4;bool Finished=false;};
class Shelter {
    std::array<Resident,4> Family;
    Supplies Store;
    unsigned Day=0;
    int Integrity=80;
public:
    const std::array<Resident,4>& Residents() const {return Family;}
    Supplies Stock() const {return Store;}
    int Condition() const {return Integrity;}
    unsigned DaysSurvived() const {return Day;}
    bool Finished() const {return std::none_of(Family.begin(),Family.end(),[](const Resident& R){return R.Alive;});}
    bool Advance(unsigned ExpectedDay,const Decision& D,DayReport& Report) {
        if(ExpectedDay!=Day||Finished()||Day>=36500)return false;
        int Food=0,Water=0,Medicine=0;
        for(unsigned I=0;I<Family.size();++I){if(!Family[I].Alive&&(D.Feed[I]||D.Water[I]||D.Treat[I]))return false;
            Food+=D.Feed[I]?1:0;Water+=D.Water[I]?1:0;Medicine+=D.Treat[I]?1:0;}
        if(Food>Store.Food||Water>Store.Water||Medicine>Store.Medicine||(D.Repair&&Store.RepairParts<1))return false;
        Store.Food-=Food;Store.Water-=Water;Store.Medicine-=Medicine;
        if(D.Repair){--Store.RepairParts;Integrity=std::min(100,Integrity+15);}
        ++Day;Integrity=std::max(0,Integrity-(Day%7==0?8:1));
        for(unsigned I=0;I<Family.size();++I){auto& R=Family[I];if(!R.Alive)continue;
            R.Hunger=D.Feed[I]?std::max(0,R.Hunger-30):std::min(100,R.Hunger+12);
            R.Thirst=D.Water[I]?std::max(0,R.Thirst-45):std::min(100,R.Thirst+22);
            if(D.Treat[I])R.Health=std::min(100,R.Health+25);
            int Harm=(R.Hunger>=72?10:0)+(R.Thirst>=66?18:0)+(Integrity<20?8:0);
            R.Health=std::max(0,R.Health-Harm);R.Morale=std::max(0,std::min(100,R.Morale+(D.Feed[I]&&D.Water[I]?2:-3)));
            R.Alive=R.Health>0;
        }
        int Alive=0;for(const auto& R:Family)Alive+=R.Alive?1:0;
        Report={Day,Alive,Alive==0};return true;
    }
    // Expedition/trade grants must be validated and deduplicated in the host ledger before invocation.
    bool Receive(const Supplies& S) {
        const int In[]={S.Food,S.Water,S.Medicine,S.RepairParts};
        const int Old[]={Store.Food,Store.Water,Store.Medicine,Store.RepairParts};
        for(int I=0;I<4;++I)if(In[I]<0||In[I]>100000-Old[I])return false;
        Store.Food+=S.Food;Store.Water+=S.Water;Store.Medicine+=S.Medicine;Store.RepairParts+=S.RepairParts;return true;
    }
};
}}
