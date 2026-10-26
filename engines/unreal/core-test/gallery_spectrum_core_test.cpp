// SPDX-License-Identifier: MIT
#include "../DaedalusLink/Source/DaedalusLink/Public/DaedalusGallerySpectrumCore.h"
#include <array>
#include <iostream>
#include <vector>

namespace sp=daedalus::spectrum;
namespace
{
    int Checks=0,Failures=0;
    void Check(bool Passed,const char* Name)
    { ++Checks; if (!Passed) { ++Failures; std::cout<<"FAIL: "<<Name<<'\n'; } }
    // Independent authored fixture, not values read back from the implementation.
    constexpr int ChannelIndex[6]={0,1,2,0,1,2};
    constexpr int Destination[6][2]={{0,1},{0,2},{0,3},{2,1},{1,3},{1,2}};
    constexpr int Goal[3]={21,0,42};
    constexpr int Targets[3][4]={{2,5,1,6},{7,6,1,0},{5,3,6,0}};
    sp::Evaluation Oracle(int Picture,int Mask)
    {
        bool Present[4][3]{};
        for (int I=0;I<6;++I) Present[Destination[I][(Mask>>I)&1]][ChannelIndex[I]]=true;
        sp::Evaluation Result;
        for (int Window=0;Window<4;++Window)
        {
            int Value=0; for (int C=0;C<3;++C) if (Present[Window][C]) Value+=1<<C;
            Result.Channels[Window]=static_cast<std::uint8_t>(Value);
            if (Value==Targets[Picture][Window]) ++Result.Matched;
        }
        Result.Complete=Result.Matched==4; return Result;
    }
    bool Equal(const sp::Evaluation& A,const sp::Evaluation& B)
    { return A.Channels==B.Channels && A.Matched==B.Matched && A.Complete==B.Complete; }
    std::array<int,64> Distances(int WinningMask)
    {
        std::array<int,64> Out,Queue{}; Out.fill(-1); Out[WinningMask]=0;
        int Head=0,Tail=1; Queue[0]=WinningMask;
        while (Head<Tail)
        {
            const int At=Queue[Head++];
            for (int I=0;I<6;++I)
            { const int Next=At^(1<<I); if (Out[Next]<0) { Out[Next]=Out[At]+1; Queue[Tail++]=Next; } }
        }
        return Out;
    }
    bool Solve(sp::Session& Session)
    {
        for (int Turn=0;Turn<6;++Turn)
        {
            sp::Evaluation View; if (!Session.View(View)) return false; if (View.Complete) return true;
            sp::Clue Hint; if (!Session.Hint(Hint) || !Session.Toggle(Hint.RouterIndex)) return false;
        }
        sp::Evaluation View; return Session.View(View) && View.Complete;
    }
}
int main()
{
    bool Fixture=true;
    for (int I=0;I<6;++I) Fixture=Fixture && sp::Routers[I].Channel==(1<<ChannelIndex[I]) &&
        sp::Routers[I].Windows[0]==Destination[I][0] && sp::Routers[I].Windows[1]==Destination[I][1];
    for (int P=0;P<3;++P) for (int W=0;W<4;++W) Fixture=Fixture && sp::Pictures[P].Targets[W]==Targets[P][W];
    Check(Fixture && sp::Pictures[0].StartMask==63 && sp::Pictures[1].StartMask==63 && sp::Pictures[2].StartMask==0,
        "authored source routing, targets and initial choices are pinned independently");
    bool Truth=true,Unique=true;
    for (int P=0;P<3;++P)
    {
        int Wins=0;
        for (int Mask=0;Mask<64;++Mask)
        {
            sp::Evaluation View; Truth=sp::Evaluate(P,Mask,View) && Equal(View,Oracle(P,Mask)) && Truth;
            if (View.Complete) { ++Wins; Unique=Unique && Mask==Goal[P]; }
        }
        Unique=Unique && Wins==1;
    }
    Check(Truth,"all192 picture states match independent per-window channel presence oracle");
    Check(Unique,"each authored picture has exactly its intended unique solution");
    sp::Evaluation View;
    Check(sp::Evaluate(0,63,View) && View.Channels[1]==1 && View.Channels[2]==6 && View.Channels[3]==6,
        "two red beams remain red rather than cancel or introduce another channel");
    Check(sp::Evaluate(1,0,View) && View.Channels[0]==7 && View.Channels[1]==6 && View.Channels[3]==0,
        "RGB white, GB cyan and an intentionally unlit window are explicit states");
    const sp::Evaluation Sentinel{{{7,6,5,4}},-7,true}; View=Sentinel;
    Check(!sp::Evaluate(-1,0,View) && !sp::Evaluate(3,0,View) && !sp::Evaluate(0,-1,View) && !sp::Evaluate(0,64,View) && Equal(View,Sentinel),
        "invalid picture or route state preserves complete evaluation output");
    bool Clues=true;
    for (int P=0;P<3;++P)
    {
        const auto Distance=Distances(Goal[P]);
        for (int Mask=0;Mask<64;++Mask)
        {
            sp::Clue Hint{-4,true,73};
            if (Mask==Goal[P])
            { Clues=Clues && !sp::HintFor(P,Mask,Hint) && Hint.RouterIndex==-4 && Hint.ToB && Hint.Remaining==73; continue; }
            int Expected=0; while (!((Mask^Goal[P])&(1<<Expected))) ++Expected;
            const bool Accepted=sp::HintFor(P,Mask,Hint);
            Clues=Clues && Accepted && Hint.RouterIndex==Expected && Hint.Remaining==Distance[Mask] &&
                Hint.ToB==((Goal[P]&(1<<Expected))!=0) && Distance[Mask^(1<<Expected)]==Distance[Mask]-1;
        }
    }
    Check(Clues,"all192 hint cases agree with independent hypercube BFS and lowest-router tie order");
    sp::Clue Guard{-4,true,73};
    Check(!sp::HintFor(-1,0,Guard) && !sp::HintFor(3,0,Guard) && !sp::HintFor(0,-1,Guard) && !sp::HintFor(0,64,Guard) &&
        Guard.RouterIndex==-4 && Guard.ToB && Guard.Remaining==73,"invalid hints preserve caller fields");
    sp::Session Session; View=Sentinel;
    Check(!Session.Active() && !Session.View(View) && Equal(View,Sentinel) && !Session.Hint(Guard) &&
        !Session.Toggle(0) && !Session.Undo() && !Session.Redo() && !Session.Restart() && !Session.SelectPicture(1) &&
        !Session.EverCompleted(0) && Session.CompletedCount()==0,"inactive session cannot mutate or fake a view");
    Check(Session.Begin() && Session.Active() && Session.CurrentPicture()==0 && Session.Mask()==63 &&
        Session.UndoCount()==0 && Session.RedoCount()==0 && Session.CompletedCount()==0,"practice begins at authored first picture");
    Check(Session.Toggle(1) && Session.Mask()==61 && Session.UndoCount()==1 && Session.Undo() && Session.Mask()==63 &&
        Session.RedoCount()==1 && Session.SelectPicture(1) && Session.Mask()==63 && Session.UndoCount()==0 &&
        Session.Toggle(0) && Session.Mask()==62 && Session.SelectPicture(0) && Session.Mask()==63 && Session.RedoCount()==1 &&
        Session.Redo() && Session.Mask()==61,"picture switching retains each independent route and history branches");
    const int Before=Session.Mask(); const auto BeforeUndo=Session.UndoCount(),BeforeRedo=Session.RedoCount();
    Check(!Session.Toggle(-1) && !Session.Toggle(6) && !Session.SelectPicture(-1) && !Session.SelectPicture(3) && !Session.SelectPicture(0) &&
        !Session.EverCompleted(-1) && !Session.EverCompleted(3) && Session.CurrentPicture()==0 && Session.Mask()==Before &&
        Session.UndoCount()==BeforeUndo && Session.RedoCount()==BeforeRedo,"invalid choices leave selection and history unchanged");
    Check(Solve(Session) && Session.Mask()==21 && Session.EverCompleted(0) && Session.CompletedCount()==1 &&
        Session.Undo() && Session.View(View) && !View.Complete && Session.EverCompleted(0) &&
        Session.Redo() && Session.View(View) && View.Complete && Session.CompletedCount()==1,
        "current completion is reversible while first-study information remains once per picture");
    Check(Session.Restart() && Session.Mask()==63 && Session.UndoCount()==0 && Session.RedoCount()==0 && Session.EverCompleted(0) &&
        !Session.Restart() && Session.SelectPicture(1) && Session.Mask()==62 && Session.UndoCount()==1,
        "confirmed host reset clears only selected attempt and retains other picture plus first study");
    Check(Solve(Session) && Session.Mask()==0 && Session.SelectPicture(2) && Solve(Session) && Session.Mask()==42 &&
        Session.CompletedCount()==3 && Session.SelectPicture(1) && Session.View(View) && View.Complete,
        "all three pictures can be studied with retained independent completed states");
    Session.Begin(); std::vector<int> States{Session.Mask()};
    bool History=true;
    for (int I=0;I<70;++I) { History=Session.Toggle(I%6) && History; States.push_back(Session.Mask()); }
    for (int I=0;I<64;++I) History=Session.Undo() && Session.Mask()==States[69-I] && History;
    History=History && Session.Mask()==States[6] && Session.UndoCount()==0 && Session.RedoCount()==64 && !Session.Undo();
    for (int I=0;I<64;++I) History=Session.Redo() && Session.Mask()==States[7+I] && History;
    Check(History && Session.Mask()==States[70] && Session.UndoCount()==64 && Session.RedoCount()==0 && !Session.Redo(),
        "exact latest64 edit undo and redo boundaries retain the correct states");
    Check(Session.Undo() && Session.RedoCount()==1 && Session.Toggle(3) && Session.RedoCount()==0 && !Session.Redo(),
        "a new route edit branches redo exactly once");
    auto Copy=Session; const int Original=Session.Mask();
    Check(Copy.Toggle(2) && Copy.Mask()!=Original && Session.Mask()==Original && Copy.SelectPicture(2) && Session.CurrentPicture()==0,
        "copied local practice state does not alias route or selection history");
    Session.Begin(); int Matches[4]{}; const int Path[4]={63,61,53,21};
    bool PathHints=true;
    for (int I=0;I<4;++I)
    {
        sp::Evaluate(0,Session.Mask(),View); Matches[I]=View.Matched; PathHints=PathHints && Session.Mask()==Path[I];
        if (I<3) { sp::Clue Hint; PathHints=Session.Hint(Hint) && Session.Toggle(Hint.RouterIndex) && PathHints; }
    }
    Check(PathHints && Matches[0]==1 && Matches[1]==2 && Matches[2]==2 && Matches[3]==4,
        "optimal clue path tolerates a turn without immediate matched-window improvement");
    std::cout<<Checks<<" checks, "<<Failures<<" failed;192 complete states,192 independent BFS hint cases and64-edit history\n";
    return Failures?1:0;
}
