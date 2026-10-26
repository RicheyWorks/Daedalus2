// SPDX-License-Identifier: MIT
#include "../DaedalusLink/Source/DaedalusLink/Public/DaedalusBricksBridgeCore.h"
#include <algorithm>
#include <array>
#include <iostream>
#include <string>
#include <vector>

namespace bb=daedalus::brickbridge;
namespace
{
    int Checks=0,Failures=0;
    void Check(bool Passed,const char* Name)
    { ++Checks; if (!Passed) { ++Failures; std::cerr<<"FAIL: "<<Name<<'\n'; } }
    constexpr int Ends[12][2]={{0,1},{1,2},{3,4},{4,5},{6,7},{7,8},{0,3},{1,4},{2,5},{3,6},{4,7},{5,8}};
    constexpr int Columns[3][3]={{0,2,5},{0,2,5},{0,1,4}},Rows[3][3]={{0,1,4},{0,1,4},{0,2,5}};
    constexpr int Allowed[3]={4095,4095&~(1<<2)&~(1<<10),4095&~(1<<0)&~(1<<8)};
    constexpr int Minimum[3]={16,16,18},WinnerCount[3]={24,7,7},FirstWinner[3]={1011,1011,766};
    int Bits(int Mask) { int Count=0; for (int I=0;I<12;++I) if (Mask&(1<<I)) ++Count; return Count; }
    int Length(int Rule,int Link)
    {
        const int A=Ends[Link][0],B=Ends[Link][1];
        const int X=Columns[Rule][A%3]-Columns[Rule][B%3],Y=Rows[Rule][A/3]-Rows[Rule][B/3];
        return (X<0?-X:X)+(Y<0?-Y:Y);
    }
    int Cost(int Rule,int Mask)
    { int Sum=0; for (int I=0;I<12;++I) if (Mask&(1<<I)) Sum+=Length(Rule,I); return Sum; }
    // Independent adjacency BFS; no production union-find or Evaluate helper.
    bb::Evaluation Oracle(int Rule,int Mask,int Limit)
    {
        bool Adjacent[9][9]{};
        for (int I=0;I<12;++I) if (Mask&(1<<I)) Adjacent[Ends[I][0]][Ends[I][1]]=Adjacent[Ends[I][1]][Ends[I][0]]=true;
        std::array<int,9> Component{}; Component.fill(-1); int Components=0;
        for (int Seed=0;Seed<9;++Seed) if (Component[Seed]<0)
        {
            std::array<int,9> Queue{}; int Head=0,Tail=1; Queue[0]=Seed; Component[Seed]=Components;
            while (Head<Tail)
            {
                const int At=Queue[Head++];
                for (int To=0;To<9;++To) if (Adjacent[At][To] && Component[To]<0)
                { Component[To]=Components; Queue[Tail++]=To; }
            }
            ++Components;
        }
        bb::Evaluation Out; Out.Components=Components; Out.UsedLength=Cost(Rule,Mask); Out.SelectedCount=Bits(Mask);
        for (int I=0;I<9;++I) { Out.LinkedToHome[I]=Component[I]==Component[0]; if (Out.LinkedToHome[I]) ++Out.PadsConnected; }
        Out.WithinLength=Out.UsedLength<=Limit; Out.Complete=Out.WithinLength && Out.PadsConnected==9; return Out;
    }
    bool Equal(const bb::Evaluation& A,const bb::Evaluation& B)
    { return A.LinkedToHome==B.LinkedToHome && A.UsedLength==B.UsedLength && A.PadsConnected==B.PadsConnected &&
        A.Components==B.Components && A.SelectedCount==B.SelectedCount && A.WithinLength==B.WithinLength && A.Complete==B.Complete; }
    struct TreeProof { int Minimum=99999; std::vector<int> Winners; };
    void Combinations(int Rule,int Start,int Selected,int Mask,TreeProof& Proof)
    {
        if (Selected==8)
        {
            const auto View=Oracle(Rule,Mask,99999); if (View.PadsConnected!=9) return;
            if (View.UsedLength<Proof.Minimum) { Proof.Minimum=View.UsedLength; Proof.Winners.clear(); }
            if (View.UsedLength==Proof.Minimum) Proof.Winners.push_back(Mask);
            return;
        }
        for (int I=Start;I<12;++I) if ((Allowed[Rule]&(1<<I)) && 12-I>=8-Selected)
            Combinations(Rule,I+1,Selected+1,Mask|(1<<I),Proof);
    }
    std::array<int,4096> Distances(int Rule,const TreeProof& Proof)
    {
        std::array<int,4096> Out{},Queue{}; Out.fill(-1); int Head=0,Tail=0;
        for (int Mask:Proof.Winners) { Out[Mask]=0; Queue[Tail++]=Mask; }
        while (Head<Tail)
        {
            const int At=Queue[Head++];
            for (int I=0;I<12;++I) if (Allowed[Rule]&(1<<I))
            {
                const int Next=At^(1<<I);
                if (Out[Next]<0 && Cost(Rule,Next)<=Proof.Minimum) { Out[Next]=Out[At]+1; Queue[Tail++]=Next; }
            }
        }
        return Out;
    }
    bool Apply(bb::Session& Run,int Mask)
    {
        for (int I=0;I<12;++I) if (Mask&(1<<I)) if (Run.Toggle(I)!=bb::Change::Changed) return false;
        return Run.Mask()==Mask;
    }
    bool Solve(bb::Session& Run)
    {
        for (int Turn=0;Turn<=12;++Turn)
        {
            bb::Evaluation View; if (!Run.View(View)) return false; if (View.Complete) return true;
            bb::Clue Clue; if (!Run.Hint(Clue) || Run.Toggle(Clue.LinkIndex)!=bb::Change::Changed) return false;
        }
        return false;
    }
    int GraySubset(int Step)
    {
        constexpr int Edges[8]={0,1,4,5,6,7,8,9}; const int Gray=Step^(Step>>1); int Mask=0;
        for (int I=0;I<8;++I) if (Gray&(1<<I)) Mask|=1<<Edges[I]; return Mask;
    }
}

int main()
{
    bool Fixture=true;
    const char* Names[3]={"Open Spans","Side Repair","Long Crossing"};
    for (int I=0;I<12;++I) Fixture=Fixture && bb::Links[I].From==Ends[I][0] && bb::Links[I].To==Ends[I][1];
    for (int Rule=0;Rule<3;++Rule)
    {
        Fixture=Fixture && std::string(bb::Blueprints[Rule].Name)==Names[Rule] && bb::Blueprints[Rule].AllowedMask==Allowed[Rule];
        for (int I=0;I<3;++I) Fixture=Fixture && bb::Blueprints[Rule].Columns[I]==Columns[Rule][I] && bb::Blueprints[Rule].Rows[I]==Rows[Rule][I];
        for (int I=0;I<12;++I) Fixture=Fixture && bb::LinkLength(Rule,I)==Length(Rule,I) && Length(Rule,I)>0;
    }
    Check(Fixture,"three authored blueprints, closed links, fixed link order and Manhattan lengths are pinned");
    Check(bb::LinkLength(-1,0)==-1 && bb::LinkLength(3,0)==-1 && bb::LinkLength(0,-1)==-1 && bb::LinkLength(0,12)==-1 &&
        bb::LengthLimit(-1)==-1 && bb::LengthLimit(3)==-1,"invalid geometry queries return unavailable rather than a usable length");
    std::array<TreeProof,3> Proofs; bool Optimum=true;
    for (int Rule=0;Rule<3;++Rule)
    {
        Combinations(Rule,0,0,0,Proofs[Rule]); std::sort(Proofs[Rule].Winners.begin(),Proofs[Rule].Winners.end());
        Optimum=Optimum && Proofs[Rule].Minimum==Minimum[Rule] && Proofs[Rule].Winners.size()==static_cast<size_t>(WinnerCount[Rule]) &&
            !Proofs[Rule].Winners.empty() && Proofs[Rule].Winners.front()==FirstWinner[Rule] && bb::LengthLimit(Rule)==Minimum[Rule];
    }
    Check(Optimum,"independent eight-edge combinations and BFS pin minima16/16/18, winners24/7/7 and first masks1011/1011/766");
    bool Truth=true; int AllowedStates=0;
    for (int Rule=0;Rule<3;++Rule)
    {
        int Wins=0,First=-1;
        for (int Mask=0;Mask<4096;++Mask) if (!(Mask&~Allowed[Rule]))
        {
            ++AllowedStates; bb::Evaluation View; const bool Accepted=bb::Evaluate(Rule,Mask,View);
            Truth=Accepted && Equal(View,Oracle(Rule,Mask,Proofs[Rule].Minimum)) && Truth;
            if (View.Complete) { ++Wins; if (First<0) First=Mask; }
        }
        Truth=Truth && Wins==WinnerCount[Rule] && First==FirstWinner[Rule];
    }
    Check(Truth && AllowedStates==6144,"all6144 allowed subsets match independent BFS home reach, components, cost, cap and completion");
    bb::Evaluation View;
    Check(bb::Evaluate(0,0,View) && View.PadsConnected==1 && View.Components==9 && View.WithinLength && !View.Complete &&
        bb::Evaluate(0,4095,View) && View.PadsConnected==9 && View.SelectedCount==12 && View.UsedLength==27 && !View.WithinLength && !View.Complete,
        "empty cheap forest and connected overlength cycles are not winning networks");
    bb::Evaluation Sentinel; Sentinel.LinkedToHome.fill(true); Sentinel.UsedLength=-1; Sentinel.PadsConnected=-2; Sentinel.Components=-3; Sentinel.SelectedCount=-4; Sentinel.WithinLength=Sentinel.Complete=true;
    View=Sentinel;
    Check(!bb::Evaluate(-1,0,View) && !bb::Evaluate(3,0,View) && !bb::Evaluate(0,-1,View) && !bb::Evaluate(0,4096,View) &&
        !bb::Evaluate(1,1<<2,View) && !bb::Evaluate(2,1<<8,View) && Equal(View,Sentinel),"invalid rule, high bits and closed selections preserve complete evaluation output");

    bool Hints=true,Refusals=true,NonGreedy=false; int LegalHintStates=0,FullRule=-1,FullMask=-1;
    for (int Rule=0;Rule<3;++Rule)
    {
        const auto Distance=Distances(Rule,Proofs[Rule]);
        for (int Mask=0;Mask<4096;++Mask) if (!(Mask&~Allowed[Rule]))
        {
            const auto Before=Oracle(Rule,Mask,Proofs[Rule].Minimum); bb::Clue Hint{-7,true,99};
            if (!Before.WithinLength || Before.Complete)
            { Refusals=Refusals && !bb::HintFor(Rule,Mask,Hint) && Hint.LinkIndex==-7 && Hint.ToSelected && Hint.Remaining==99; continue; }
            ++LegalHintStates; int Winner=-1,Best=99;
            for (int Candidate:Proofs[Rule].Winners)
                if (Bits(Mask^Candidate)<Best) { Winner=Candidate; Best=Bits(Mask^Candidate); }
            const int Extras=Mask&~Winner,Choices=Extras?Extras:Winner&~Mask; int Expected=0; while (!(Choices&(1<<Expected))) ++Expected;
            const bool Accepted=bb::HintFor(Rule,Mask,Hint);
            if (!Accepted || Hint.LinkIndex<0 || Hint.LinkIndex>=12) { Hints=false; continue; }
            const int Next=Mask^(1<<Hint.LinkIndex); const auto After=Oracle(Rule,Next,Proofs[Rule].Minimum);
            Hints=Hints && Hint.LinkIndex==Expected && Hint.ToSelected==((Winner&(1<<Expected))!=0) &&
                Hint.Remaining==Best && Hint.Remaining==Distance[Mask] && !(Next&~Allowed[Rule]) && After.WithinLength && Distance[Next]==Distance[Mask]-1;
            if (After.PadsConnected<=Before.PadsConnected) NonGreedy=true;
            if (FullRule<0 && Before.UsedLength==Proofs[Rule].Minimum && Extras)
            { FullRule=Rule; FullMask=Mask; }
        }
    }
    Check(Hints && LegalHintStates>0,"every valid unsolved hint follows legal multi-source BFS distance with exact winner and removal-first ties");
    Check(Refusals,"solved and valid-but-overlength states refuse hints without changing caller output");
    Check(NonGreedy,"a useful shortest hint can keep or reduce home connectivity");
    bb::Clue Clue{-7,true,99};
    Check(!bb::HintFor(-1,0,Clue) && !bb::HintFor(3,0,Clue) && !bb::HintFor(0,-1,Clue) && !bb::HintFor(0,4096,Clue) &&
        !bb::HintFor(1,1<<2,Clue) && Clue.LinkIndex==-7 && Clue.ToSelected && Clue.Remaining==99,"invalid hints retain every caller field");
    bb::Session Run;
    Check(!Run.Active() && Run.Toggle(0)==bb::Change::Unavailable && !Run.SelectRule(1) && !Run.Undo() && !Run.Redo() && !Run.Restart() &&
        !Run.View(View) && !Run.Hint(Clue) && Run.CompletedCount()==0,"inactive session refuses all operations");
    Check(Run.Begin() && Run.CurrentRule()==0 && Run.Mask()==0 && Run.UndoCount()==0 && Run.RedoCount()==0 && Run.View(View) && View.PadsConnected==1,
        "all attempts start empty with just home connected");
    bool FullRemoval=FullRule>=0;
    if (FullRule>=0)
    {
        Run.Begin(); if (FullRule) Run.SelectRule(FullRule); FullRemoval=Apply(Run,FullMask) && Run.Hint(Clue) && !Clue.ToSelected;
        const auto OldMask=Run.Mask(); const auto OldLength=Cost(FullRule,OldMask);
        FullRemoval=FullRemoval && Run.Toggle(Clue.LinkIndex)==bb::Change::Changed && Cost(FullRule,Run.Mask())<OldLength &&
            Run.Undo() && Run.Mask()==OldMask && Run.Redo() && Run.Mask()==(OldMask^(1<<Clue.LinkIndex));
    }
    Check(FullRemoval,"a full-length unsolved stock uses a legal removal first and remains undoable");
    Run.Begin(); Run.SelectRule(1); Run.Toggle(6); Run.Undo(); const auto UndoBefore=Run.UndoCount(),RedoBefore=Run.RedoCount();
    Check(Run.Toggle(2)==bb::Change::Closed && Run.Toggle(10)==bb::Change::Closed && Run.Toggle(-1)==bb::Change::Unavailable && Run.Toggle(12)==bb::Change::Unavailable &&
        !Run.SelectRule(-1) && !Run.SelectRule(3) && !Run.SelectRule(1) && Run.Mask()==0 && Run.CurrentRule()==1 &&
        Run.UndoCount()==UndoBefore && Run.RedoCount()==RedoBefore && Run.Redo() && Run.Mask()==(1<<6),"closed/invalid edits and rule selections retain the existing history branch");
    Run.Begin(); const bool Won=Apply(Run,1011); Run.Toggle(0); Run.Undo(); const auto WonUndo=Run.UndoCount(),WonRedo=Run.RedoCount();
    Check(Won && Run.Toggle(2)==bb::Change::OverLength && Run.Mask()==1011 && Run.UndoCount()==WonUndo && Run.RedoCount()==WonRedo &&
        Run.Toggle(0)==bb::Change::Changed && Run.Mask()==1010 && Run.RedoCount()==0 && Run.EverCompleted(0),"overlength addition is atomic while removal is legal and keeps first completion");

    Run.Begin(); bool Separate=true; std::array<int,3> Saved{}; std::array<size_t,3> SavedUndo{};
    for (int Rule=0;Rule<3;++Rule)
    {
        if (Rule) Separate=Run.SelectRule(Rule) && Separate;
        const bool Solved=Solve(Run); Saved[Rule]=Run.Mask(); SavedUndo[Rule]=Run.UndoCount();
        Separate=Solved && Run.EverCompleted(Rule) && Run.CompletedCount()==Rule+1 && Separate;
    }
    Run.SelectRule(0);
    Separate=Separate && Run.Mask()==Saved[0] && Run.UndoCount()==SavedUndo[0] && Run.Undo() && Run.View(View) && !View.Complete &&
        Run.EverCompleted(0) && Run.CompletedCount()==3 && Run.Redo() && Run.Mask()==Saved[0];
    Check(Separate,"three blueprints retain independent routes/history and reversible completion with once-ever information");
    Check(Run.Restart() && Run.Mask()==0 && Run.UndoCount()==0 && Run.RedoCount()==0 && Run.EverCompleted(0) && Run.CompletedCount()==3 &&
        Run.SelectRule(1) && Run.Mask()==Saved[1] && Run.UndoCount()==SavedUndo[1] && Run.SelectRule(2) && Run.Mask()==Saved[2] && Run.UndoCount()==SavedUndo[2],
        "restart resets only current attempts/history while preserving other blueprints and first completions");
    Run.Begin(); bool History=true;
    for (int Step=1;Step<=73;++Step)
    {
        const int Previous=GraySubset(Step-1),Next=GraySubset(Step),Difference=Previous^Next; int Link=0; while (!(Difference&(1<<Link))) ++Link;
        const auto Changed=Run.Toggle(Link); bb::Evaluation State; const bool Evaluated=Run.View(State);
        History=Changed==bb::Change::Changed && Bits(Difference)==1 && Run.Mask()==Next && Evaluated && State.WithinLength &&
            Run.UndoCount()==static_cast<size_t>(Step<64?Step:64) && Run.RedoCount()==0 && History;
    }
    for (int Step=72;Step>=9;--Step)
    {
        const bool Moved=Run.Undo();
        History=Moved && Run.Mask()==GraySubset(Step) && Run.UndoCount()==static_cast<size_t>(Step-9) && Run.RedoCount()==static_cast<size_t>(73-Step) && History;
    }
    Check(History && GraySubset(9)!=GraySubset(73) && GraySubset(9)!=0 && !Run.Undo() && Run.Mask()==GraySubset(9),
        "73 unique Gray-subset edits keep exact latest64 undo snapshots and stop at dropped9 boundary");
    for (int Step=10;Step<=73;++Step)
    {
        const bool Moved=Run.Redo();
        History=Moved && Run.Mask()==GraySubset(Step) && Run.UndoCount()==static_cast<size_t>(Step-9) && Run.RedoCount()==static_cast<size_t>(73-Step) && History;
    }
    Check(History && !Run.Redo() && Run.Mask()==GraySubset(73),"every intermediate redo snapshot returns exactly to state73");
    std::cout<<Checks<<" checks, "<<Failures<<" failed;6144 subset/BFS evaluations, minimum-tree combinations, legal multi-source hints and73-edit history\n";
    return Failures?1:0;
}
