// SPDX-License-Identifier: MIT
#include "../DaedalusLink/Source/DaedalusLink/Public/DaedalusBricksBridgeWalkCore.h"
#include <algorithm>
#include <array>
#include <cmath>
#include <iostream>
#include <initializer_list>
#include <limits>

namespace walk=daedalus::bridgewalk;
namespace
{
    int Checks=0,Failures=0;
    void Check(bool Passed,const char* Name)
    { ++Checks; if (!Passed) { ++Failures; std::cerr<<"FAIL: "<<Name<<'\n'; } }
    constexpr int Winners[3]={1011,1011,766};
    constexpr int Columns[3][3]={{0,2,5},{0,2,5},{0,1,4}},Rows[3][3]={{0,1,4},{0,1,4},{0,2,5}};
    constexpr int Ends[12][2]={{0,1},{1,2},{3,4},{4,5},{6,7},{7,8},{0,3},{1,4},{2,5},{3,6},{4,7},{5,8}};
    bool Equal(const std::array<walk::Piece,21>& A,const std::array<walk::Piece,21>& B)
    {
        for (int I=0;I<21;++I)
            if (A[I].CentreX!=B[I].CentreX || A[I].CentreY!=B[I].CentreY || A[I].HalfX!=B[I].HalfX || A[I].HalfY!=B[I].HalfY || A[I].Active!=B[I].Active) return false;
        return true;
    }
}
int main()
{
    walk::Walk Empty; bool Inactive=true;
    for (const auto& Piece:Empty.Geometry()) Inactive=Inactive && !Piece.Active && Piece.CentreX==0 && Piece.CentreY==0 && Piece.HalfX==0 && Piece.HalfY==0;
    Check(Inactive && !Empty.Active() && Empty.Rule()==-1 && Empty.Mask()==0 && !Empty.PadCentre(0).Valid && Empty.Observe(700,-200,35,true)==-1 &&
        Empty.VisitedMask()==0 && Empty.VisitedCount()==0 && !Empty.WasVisited(0) && walk::PieceCount==21 && walk::DeckBottom==0 && walk::DeckTop==35 &&
        walk::DeckCentreZ-walk::DeckHalfZ==0 && walk::DeckCentreZ+walk::DeckHalfZ==35,
        "inactive geometry/visits are empty and all model pieces share the specified low0..35cm deck");
    std::array<walk::Walk,3> Models; bool Captures=true;
    for (int Rule=0;Rule<3;++Rule) Captures=Models[Rule].Capture(Rule,Winners[Rule]) && Models[Rule].Active() && Models[Rule].Rule()==Rule && Models[Rule].Mask()==Winners[Rule] && Captures;
    Check(Captures,"all three established winning masks capture their current solved blueprint once");
    bool Coordinates=true,Seams=true,Separate=true;
    for (int Rule=0;Rule<3;++Rule)
    {
        const auto& Pieces=Models[Rule].Geometry(); int Pads=0,Beams=0;
        for (int Pad=0;Pad<9;++Pad)
        {
            const auto At=Models[Rule].PadCentre(Pad); const auto& Piece=Pieces[Pad];
            Coordinates=At.Valid && At.X==700+100*Columns[Rule][Pad%3] && At.Y==-200+100*Rows[Rule][Pad/3] && Piece.Active &&
                Piece.CentreX==At.X && Piece.CentreY==At.Y && Piece.HalfX==45 && Piece.HalfY==45 && Coordinates; if (Piece.Active) ++Pads;
        }
        for (int Link=0;Link<12;++Link)
        {
            const auto& Piece=Pieces[9+Link]; const auto& A=Pieces[Ends[Link][0]]; const auto& B=Pieces[Ends[Link][1]];
            const bool Horizontal=A.CentreY==B.CentreY,Selected=(Winners[Rule]&(1<<Link))!=0;
            Coordinates=Piece.Active==Selected && Piece.HalfX>0 && Piece.HalfY>0 && Coordinates; if (Piece.Active) ++Beams;
            if (Horizontal)
                Seams=Piece.HalfY==45 && Piece.CentreY==A.CentreY && Piece.CentreX-Piece.HalfX==A.CentreX+A.HalfX &&
                    Piece.CentreX+Piece.HalfX==B.CentreX-B.HalfX && Piece.HalfX*2==B.CentreX-A.CentreX-90 && Seams;
            else
                Seams=Piece.HalfX==45 && Piece.CentreX==A.CentreX && Piece.CentreY-Piece.HalfY==A.CentreY+A.HalfY &&
                    Piece.CentreY+Piece.HalfY==B.CentreY-B.HalfY && Piece.HalfY*2==B.CentreY-A.CentreY-90 && Seams;
        }
        Coordinates=Pads==9 && Beams==8 && Coordinates;
        for (int A=0;A<21;++A) for (int B=A+1;B<21;++B) if (Pieces[A].Active && Pieces[B].Active)
        {
            const int X=std::min(Pieces[A].CentreX+Pieces[A].HalfX,Pieces[B].CentreX+Pieces[B].HalfX)-std::max(Pieces[A].CentreX-Pieces[A].HalfX,Pieces[B].CentreX-Pieces[B].HalfX);
            const int Y=std::min(Pieces[A].CentreY+Pieces[A].HalfY,Pieces[B].CentreY+Pieces[B].HalfY)-std::max(Pieces[A].CentreY-Pieces[A].HalfY,Pieces[B].CentreY-Pieces[B].HalfY);
            Separate=!(X>0 && Y>0) && Separate;
        }
    }
    Check(Coordinates,"literal three-blueprint coordinates derive9pads+8selected spans while all21stored boxes have positive dimensions");
    Check(Seams,"every horizontal/vertical span meets both pad faces exactly, trimming90cm from centre distance");
    Check(Separate,"active pieces have no positive-area planar overlap, including nearby parallel spans and shared-pad seams");
    const auto ShortVertical=Models[0].Geometry()[15],ShortHorizontal=Models[2].Geometry()[11];
    Check(ShortVertical.Active && ShortVertical.CentreX==700 && ShortVertical.CentreY==-150 && ShortVertical.HalfX==45 && ShortVertical.HalfY==5 &&
        ShortHorizontal.Active && ShortHorizontal.CentreX==750 && ShortHorizontal.CentreY==0 && ShortHorizontal.HalfX==5 && ShortHorizontal.HalfY==45,
        "100cm adjacency has a positive10cm beam in both axes rather than a120cm-pad trimming gap");
    const auto Before=Empty.Geometry();
    Check(!Empty.Capture(-1,1011) && !Empty.Capture(3,1011) && !Empty.Capture(0,-1) && !Empty.Capture(0,4096) && !Empty.Capture(0,0) &&
        !Empty.Capture(0,1010) && !Empty.Capture(0,4095) && !Empty.Capture(1,1<<2) && !Empty.Capture(2,1<<8) && !Empty.Active() &&
        Empty.Rule()==-1 && Empty.Mask()==0 && Equal(Empty.Geometry(),Before) && Empty.VisitedMask()==0,
        "invalid, incomplete, closed and over-allowance snapshots leave the inactive capture completely unchanged");
    walk::Walk Frozen; Frozen.Capture(0,1011); const auto FrozenPieces=Frozen.Geometry(); const auto Home=Frozen.PadCentre(0);
    const bool Marked=Frozen.Observe(Home.X,Home.Y,35,true)==0;
    Check(Marked && !Frozen.Capture(0,1011) && !Frozen.Capture(1,1011) && !Frozen.Capture(2,766) && !Frozen.Capture(-1,0) &&
        Frozen.Active() && Frozen.Rule()==0 && Frozen.Mask()==1011 && Equal(Frozen.Geometry(),FrozenPieces) && Frozen.VisitedMask()==1 && Frozen.VisitedCount()==1,
        "repeated or different captures cannot replace the frozen model or erase recorded visits");
    walk::Walk Detached; bool Copied=false; std::array<walk::Piece,21> DetachedPieces{};
    {
        daedalus::brickbridge::Session Source; Source.Begin();
        for (int Link=0;Link<12;++Link) if (1011&(1<<Link)) Source.Toggle(Link);
        Copied=Detached.Capture(Source.CurrentRule(),Source.Mask()); DetachedPieces=Detached.Geometry(); Source.Undo();
    }
    Check(Copied && Detached.Active() && Detached.Rule()==0 && Detached.Mask()==1011 && Equal(Detached.Geometry(),DetachedPieces),
        "copying a complete source by value survives source edits and lifetime end of the portable source session");
    walk::Walk Corners; Corners.Capture(0,1011); bool Inclusive=true;
    const int DX[4]={35,35,-35,-35},DY[4]={35,-35,35,-35};
    for (int Pad=0;Pad<4;++Pad)
    {
        const auto At=Corners.PadCentre(Pad); const double Height=Pad%2?39:31;
        Inclusive=Corners.Observe(At.X+DX[Pad],At.Y+DY[Pad],Height,true)==Pad && Corners.WasVisited(Pad) && Corners.VisitedCount()==Pad+1 && Inclusive;
    }
    Check(Inclusive && Corners.VisitedMask()==15 && Corners.Observe(Home.X,Home.Y,35,true)==-1,
        "all inclusive35cm axis-box corners and feet31..39cm count once, even beyond a35cm radial circle");
    walk::Walk Refusals; Refusals.Capture(0,1011); const double NaN=(std::numeric_limits<double>::quiet_NaN)(),Infinity=(std::numeric_limits<double>::infinity)();
    Check(Refusals.Observe(Home.X,Home.Y,35,false)==-1 && Refusals.Observe(Home.X,Home.Y,30.999,true)==-1 && Refusals.Observe(Home.X,Home.Y,39.001,true)==-1 &&
        Refusals.Observe(Home.X+35.001,Home.Y,35,true)==-1 && Refusals.Observe(Home.X-35.001,Home.Y,35,true)==-1 &&
        Refusals.Observe(NaN,Home.Y,35,true)==-1 && Refusals.Observe(Home.X,Infinity,35,true)==-1 && Refusals.Observe(Home.X,Home.Y,NaN,true)==-1 &&
        Refusals.VisitedMask()==0 && Refusals.VisitedCount()==0 && !Refusals.WasVisited(-1) && !Refusals.WasVisited(9) && !Refusals.PadCentre(-1).Valid && !Refusals.PadCentre(9).Valid,
        "foreign/absent support, outside bounds, nonfinite samples and invalid pad indices never add visits");
    const auto Beam=Refusals.Geometry()[9];
    Check(Beam.Active && Refusals.Observe(Beam.CentreX,Beam.CentreY,35,true)==-1 && Refusals.Observe(Home.X+40,Home.Y,35,true)==-1 &&
        Refusals.Observe(800,-100,35,true)==-1 && Refusals.VisitedMask()==0,
        "beam centres, the pad's outer safety fringe and an unselected-span gap are not pad visits");
    walk::Walk All; All.Capture(2,766); bool Sticky=true; int Count=0; unsigned ExpectedMask=0;
    for (int Pad:{8,0,4,2,6,1,3,5,7})
    {
        const auto At=All.PadCentre(Pad); const int Visited=All.Observe(At.X,At.Y,35,true); ExpectedMask|=1u<<Pad; ++Count;
        Sticky=Visited==Pad && All.VisitedMask()==ExpectedMask && All.VisitedCount()==Count && All.WasVisited(Pad) && Sticky;
    }
    for (int Pad=0;Pad<9;++Pad) { const auto At=All.PadCentre(Pad); Sticky=All.Observe(At.X,At.Y,35,true)==-1 && Sticky; }
    Check(Sticky && All.VisitedMask()==511 && All.VisitedCount()==9,
        "nine sticky bits track sampled pad occupancy idempotently without inferring a traversed span order");
    std::cout<<Checks<<" checks, "<<Failures<<" failed;three fixed solved plans;exact21-box seams and9-bit sampling;native physics untested\n";
    return Failures?1:0;
}
