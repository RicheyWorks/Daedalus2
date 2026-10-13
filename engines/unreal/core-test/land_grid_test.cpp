// SPDX-License-Identifier: MIT
#include "../DaedalusLink/Source/DaedalusLink/Public/DaedalusLandGridCore.h"
#include <iostream>
#include <set>
#include <cstdlib>
using namespace DaedalusLandGrid;
void Require(bool B) {if(!B) std::exit(1);}
int main() {
    std::set<std::pair<int,int>> Seen;std::array<int,100> Districts{};Cell C{7,8};
    Require(!DefaultCell(-1,C) && C.X==7 && !DefaultCell(Count,C));
    Require(!(Cell{-50,0}.FitsSquare(1)) && !(Cell{0,0}.FitsSquare(2147483647)));
    Require(ExpansionLayout.CanGrow(9200,4600,25600,12800));
    Require(!LegacyLayout.Fits(25600,12800));
    Require(!ExpansionLayout.CanGrow(25600,12800,9200,4600));
    Require(!ExpansionLayout.Fits(50000,12800));
    for(int I=0;I<Count;++I) {
        Require(DefaultCell(I,C) && C.Valid());Require(Seen.insert({C.X,C.Z}).second);
        Require(C.District()>=0 && C.District()<100);++Districts[C.District()];
        Require(C.FitsSquare(1) && !C.FitsSquare(0) && !C.FitsSquare(11));
        std::cout<<I<<','<<C.X<<','<<C.Z<<','<<C.District()<<','<<C.OffsetXcm()<<','<<C.OffsetZcm();
        for(int N=1;N<=10;++N) std::cout<<','<<(C.FitsSquare(N)?1:0);
        int X=0,Z=0;Require(ExpansionLayout.Offsets(C,X,Z));std::cout<<','<<X<<','<<Z;
        std::cout<<'\n';
    }
    Require(Seen.size()==Count);for(int N:Districts) Require(N==100);
}
