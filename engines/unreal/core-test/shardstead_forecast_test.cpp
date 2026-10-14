#include "DaedalusShardsteadCore.h"
#include <iostream>
using namespace daedalus::shardstead;
int main(){
    Economy E(730);
    for(int P=0;P<4;++P)if(!E.Join("crew"+std::to_string(P)))return 1;
    for(unsigned I=0;I<120;++I){
        auto Owner="crew"+std::to_string(I%4);
        if(!E.Claim(Owner,I,true)||!E.Assign(Owner,I,"worker"+std::to_string(I),static_cast<Resource>(I%6)))return 2;
    }
    for(unsigned Cycle=0;Cycle<200;++Cycle){
        const auto Before=E.Export();
        Economy Reference=E;if(!Reference.Produce(E.Cycle()+1))return 3;
        for(int P=0;P<4;++P){
            auto Owner="crew"+std::to_string(P);Stock Net{};
            if(!E.ForecastNet(Owner,Net))return 4;
            for(unsigned K=0;K<Slot(Resource::Count);++K)
                if(Net[K]!=Reference.Stats(Owner)->Cargo[K]-E.Stats(Owner)->Cargo[K])return 5;
        }
        if(!SameState(Before,E.Export()))return 6;
        E=std::move(Reference);
    }
    Stock Unknown{{7,7,7,7,7,7}},Unchanged=Unknown;
    if(E.ForecastNet("missing",Unknown)||Unknown!=Unchanged)return 7;
    std::cout<<"PASS forecast matches 800 crew cycle outcomes without mutating realm state\n";
    return 0;
}
