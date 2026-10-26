// SPDX-License-Identifier: MIT
#pragma once
#include "DaedalusBricksBridgeCore.h"
#include <array>
#include <cmath>
#include <cstdlib>
#include <cstdint>

// Frozen low model of one completed local practice blueprint. Pad visits do
// not certify span crossings, structural safety, rewards or saved progress.
// Native callers must independently verify exact owned-deck floor support.
namespace daedalus::bridgewalk
{
    inline constexpr int PieceCount=21,PadHalfWidth=45,BeamHalfWidth=45,VisitHalfWidth=35;
    inline constexpr double DeckBottom=0,DeckTop=35,DeckCentreZ=17.5,DeckHalfZ=17.5,FootTolerance=4;
    struct Piece { int CentreX=0,CentreY=0,HalfX=0,HalfY=0; bool Active=false; };
    struct Centre { int X=0,Y=0; bool Valid=false; };
    class Walk
    {
    public:
        bool Capture(int RuleIndex,int SelectedMask)
        {
            if (bActive) return false;
            brickbridge::Evaluation View;
            if (!brickbridge::Evaluate(RuleIndex,SelectedMask,View) || !View.Complete) return false;
            const auto& Plan=brickbridge::Blueprints[RuleIndex]; std::array<Piece,PieceCount> Prepared{};
            for (int Pad=0;Pad<9;++Pad)
                Prepared[Pad]={700+100*Plan.Columns[Pad%3],-200+100*Plan.Rows[Pad/3],PadHalfWidth,PadHalfWidth,true};
            for (int LinkIndex=0;LinkIndex<12;++LinkIndex)
            {
                const auto& Link=brickbridge::Links[LinkIndex]; const auto& A=Prepared[Link.From]; const auto& B=Prepared[Link.To];
                const int DX=std::abs(B.CentreX-A.CentreX),DY=std::abs(B.CentreY-A.CentreY),Distance=DX+DY;
                if ((DX==0)==(DY==0) || Distance<=2*PadHalfWidth) return false;
                // The longitudinal interval begins/ends at the pad faces.
                // At100cm adjacency this leaves a positive10cm beam, not a gap
                // caused by trimming a previous120cm-wide pad assumption.
                Prepared[9+LinkIndex]={(A.CentreX+B.CentreX)/2,(A.CentreY+B.CentreY)/2,
                    DX?(Distance-2*PadHalfWidth)/2:BeamHalfWidth,
                    DY?(Distance-2*PadHalfWidth)/2:BeamHalfWidth,(SelectedMask&(1<<LinkIndex))!=0};
            }
            Pieces=Prepared; CapturedRule=RuleIndex; CapturedMask=SelectedMask; bActive=true; return true;
        }
        bool Active() const { return bActive; }
        int Rule() const { return CapturedRule; }
        int Mask() const { return CapturedMask; }
        const std::array<Piece,PieceCount>& Geometry() const { return Pieces; }
        Centre PadCentre(int Pad) const
        {
            if (!bActive || Pad<0 || Pad>=9) return {};
            return {Pieces[Pad].CentreX,Pieces[Pad].CentreY,true};
        }
        int Observe(double LocalX,double LocalY,double FeetZ,bool GroundedOnExactOwnedDeck)
        {
            if (!bActive || !GroundedOnExactOwnedDeck || !std::isfinite(LocalX) || !std::isfinite(LocalY) || !std::isfinite(FeetZ) || std::abs(FeetZ-DeckTop)>FootTolerance) return -1;
            for (int Pad=0;Pad<9;++Pad)
            {
                const auto& At=Pieces[Pad];
                if (std::abs(LocalX-At.CentreX)<=VisitHalfWidth && std::abs(LocalY-At.CentreY)<=VisitHalfWidth)
                {
                    if (WasVisited(Pad)) return -1;
                    Visits=static_cast<std::uint16_t>(Visits|(1<<Pad)); return Pad;
                }
            }
            return -1;
        }
        std::uint16_t VisitedMask() const { return Visits; }
        int VisitedCount() const
        { int Count=0; for (int Pad=0;Pad<9;++Pad) if (Visits&(1<<Pad)) ++Count; return Count; }
        bool WasVisited(int Pad) const { return bActive && Pad>=0 && Pad<9 && (Visits&(1<<Pad))!=0; }
    private:
        std::array<Piece,PieceCount> Pieces{};
        int CapturedRule=-1,CapturedMask=0;
        std::uint16_t Visits=0;
        bool bActive=false;
    };
}
