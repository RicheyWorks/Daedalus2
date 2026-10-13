// SPDX-License-Identifier: MIT
#pragma once
#include <array>

// Proposed default placement, not deed ownership or current placement after a tug.
namespace DaedalusLandGrid {
constexpr int Side=100, Count=10000, PitchCm=12800;
struct Cell {
    int X=0, Z=0;
    bool Valid() const {return X>=-49 && X<=50 && Z>=-49 && Z<=50;}
    int District() const {return Valid()?((Z+49)/10)*10+(X+49)/10:-1;}
    int OffsetXcm() const {return X*PitchCm;}
    int OffsetZcm() const {return Z*PitchCm;}
    bool FitsSquare(int N) const {
        return Valid() && N>=1 && N<=10 && X+N-1<=50 && Z+N-1<=50
            && (X+49)/10==(X+49+N-1)/10 && (Z+49)/10==(Z+49+N-1)/10;
    }
};
struct Layout {
    int PitchCm=12800, ClearanceCm=3600;
    bool Valid() const {return PitchCm>=100 && PitchCm<=1000000 && ClearanceCm>=0 && ClearanceCm<PitchCm;}
    bool Fits(int WidthCm,int DepthCm) const {
        return Valid() && WidthCm>0 && DepthCm>0 && WidthCm<=PitchCm-ClearanceCm;
    }
    bool CanGrow(int OldWidthCm,int OldDepthCm,int WidthCm,int DepthCm) const {
        return Fits(OldWidthCm,OldDepthCm) && Fits(WidthCm,DepthCm) && WidthCm>=OldWidthCm && DepthCm>=OldDepthCm;
    }
    bool Offsets(const Cell& C,int& Xcm,int& Zcm) const {
        if(!Valid() || !C.Valid()) return false;
        Xcm=C.X*PitchCm;Zcm=C.Z*PitchCm;return true;
    }
};
constexpr Layout LegacyLayout{12800,3600}, ExpansionLayout{51200,1600};
inline const std::array<Cell,Count>& Cells() {
    static const auto Table=[] {
        std::array<Cell,Count> Result{};
        int Used=1,X=0,Z=0,Direction=0;
        constexpr int Dx[]={1,0,-1,0}, Dz[]={0,1,0,-1};
        for(int Length=1;Used<Count;++Length) {
            for(int Repeat=0;Repeat<2 && Used<Count;++Repeat) {
                for(int Step=0;Step<Length && Used<Count;++Step) {
                    X+=Dx[Direction];Z+=Dz[Direction];Cell C{X,Z};
                    if(C.Valid()) Result[Used++]=C;
                }
                Direction=(Direction+1)%4;
            }
        }
        return Result;
    }();
    return Table;
}
inline bool DefaultCell(int Number,Cell& Out) {
    if(Number<0 || Number>=Count) return false;
    Out=Cells()[Number];return true;
}
}
