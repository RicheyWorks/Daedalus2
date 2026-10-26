// SPDX-License-Identifier: MIT
#include "../DaedalusLink/Source/DaedalusLink/Public/DaedalusBricksSkylineCore.h"
#include <algorithm>
#include <array>
#include <iostream>
#include <string>
#include <vector>

namespace sky=daedalus::skyline;
namespace
{
    int Checks=0,Failures=0;
    void Check(bool Passed,const char* Name)
    { ++Checks; if (!Passed) { ++Failures; std::cerr<<"FAIL: "<<Name<<'\n'; } }
    constexpr int Left[3][4]={{4,3,2,1},{2,2,1,3},{2,1,3,2}};
    constexpr int Right[3][4]={{1,2,2,2},{2,2,3,1},{0,0,0,0}};
    constexpr int Top[3][4]={{4,3,2,1},{3,1,2,2},{2,4,1,2}};
    constexpr int Bottom[3][4]={{1,2,2,2},{2,2,3,1},{0,0,0,0}};
    sky::Grid Givens(int Rule)
    {
        sky::Grid Out{};
        if (Rule==0) { Out[0]=1; Out[15]=3; }
        if (Rule==1) { Out[5]=1; Out[10]=3; }
        return Out;
    }
    // Pairwise record-high predicate, independent of the running-max helper.
    int Sight(const std::array<std::uint8_t,4>& Line)
    {
        int Count=0;
        for (int At=0;At<4;++At)
        {
            if (Line[At]>4) return -1;
            if (!Line[At]) continue;
            bool Record=true;
            for (int Before=0;Before<At;++Before) if (Line[Before]>=Line[At]) Record=false;
            if (Record) ++Count;
        }
        return Count;
    }
    sky::Evaluation Oracle(int Rule,const sky::Grid& Canvas)
    {
        sky::Evaluation Out; const auto Fixed=Givens(Rule);
        for (int Cell=0;Cell<16;++Cell)
        {
            if (Canvas[Cell]) ++Out.Filled;
            if (Fixed[Cell] && Fixed[Cell]!=Canvas[Cell]) { Out.GivensMatch=false; Out.Conflicts[Cell]=true; }
            for (int Other=Cell+1;Other<16;++Other)
                if (Canvas[Cell] && Canvas[Cell]==Canvas[Other] && (Cell/4==Other/4 || Cell%4==Other%4))
                { Out.Conflicts[Cell]=Out.Conflicts[Other]=true; Out.LatinPossible=false; }
        }
        for (int Line=0;Line<4;++Line)
        {
            std::array<std::uint8_t,4> Row{},Column{},ReverseRow{},ReverseColumn{};
            bool FullRow=true,FullColumn=true,UniqueRow=true,UniqueColumn=true;
            for (int At=0;At<4;++At)
            {
                Row[At]=Canvas[Line*4+At]; Column[At]=Canvas[At*4+Line];
                FullRow=FullRow && Row[At]!=0; FullColumn=FullColumn && Column[At]!=0;
            }
            for (int At=0;At<4;++At)
            {
                ReverseRow[At]=Row[3-At]; ReverseColumn[At]=Column[3-At];
                for (int Other=At+1;Other<4;++Other)
                {
                    if (Row[At] && Row[At]==Row[Other]) UniqueRow=false;
                    if (Column[At] && Column[At]==Column[Other]) UniqueColumn=false;
                }
            }
            Out.RowFull[Line]=FullRow; Out.ColumnFull[Line]=FullColumn;
            Out.Left[Line]=Sight(Row); Out.Right[Line]=Sight(ReverseRow);
            Out.Top[Line]=Sight(Column); Out.Bottom[Line]=Sight(ReverseColumn);
            const int Expected[4]={Left[Rule][Line],Right[Rule][Line],Top[Rule][Line],Bottom[Rule][Line]};
            const int Seen[4]={Out.Left[Line],Out.Right[Line],Out.Top[Line],Out.Bottom[Line]};
            for (int Edge=0;Edge<4;++Edge) if (Expected[Edge])
            {
                ++Out.ClueCount; const bool Full=Edge<2?FullRow:FullColumn,Unique=Edge<2?UniqueRow:UniqueColumn;
                if (Full && Unique && Seen[Edge]==Expected[Edge]) ++Out.ClueMatches;
            }
        }
        Out.Complete=Out.Filled==16 && Out.GivensMatch && Out.LatinPossible && Out.ClueMatches==Out.ClueCount;
        return Out;
    }
    bool Equal(const sky::Evaluation& A,const sky::Evaluation& B)
    {
        return A.Conflicts==B.Conflicts && A.Left==B.Left && A.Right==B.Right && A.Top==B.Top && A.Bottom==B.Bottom &&
            A.RowFull==B.RowFull && A.ColumnFull==B.ColumnFull && A.Filled==B.Filled && A.ClueMatches==B.ClueMatches &&
            A.ClueCount==B.ClueCount && A.GivensMatch==B.GivensMatch && A.LatinPossible==B.LatinPossible && A.Complete==B.Complete;
    }
    bool DifferentColumns(const std::array<std::uint8_t,4>& A,const std::array<std::uint8_t,4>& B)
    { for (int Column=0;Column<4;++Column) if (A[Column]==B[Column]) return false; return true; }
    std::vector<sky::Grid> LatinGrids()
    {
        std::vector<std::array<std::uint8_t,4>> Rows; std::array<std::uint8_t,4> Row{{1,2,3,4}};
        do { Rows.push_back(Row); } while (std::next_permutation(Row.begin(),Row.end()));
        std::vector<sky::Grid> Out;
        // Whole-row permutations plus pairwise column comparisons, rather than
        // production's cell recursion and row/column bit constraints.
        for (const auto& A:Rows) for (const auto& B:Rows) if (DifferentColumns(A,B))
            for (const auto& C:Rows) if (DifferentColumns(A,C) && DifferentColumns(B,C))
                for (const auto& D:Rows) if (DifferentColumns(A,D) && DifferentColumns(B,D) && DifferentColumns(C,D))
                {
                    sky::Grid Grid{};
                    for (int I=0;I<4;++I) { Grid[I]=A[I]; Grid[4+I]=B[I]; Grid[8+I]=C[I]; Grid[12+I]=D[I]; }
                    Out.push_back(Grid);
                }
        std::sort(Out.begin(),Out.end()); return Out;
    }
    int Distance(const sky::Grid& A,const sky::Grid& B)
    { int Count=0; for (int I=0;I<16;++I) if (A[I]!=B[I]) ++Count; return Count; }
    int Nearest(const sky::Grid& Canvas,const std::vector<sky::Grid>& Solutions,int& Best)
    {
        int At=-1; Best=17;
        for (std::size_t I=0;I<Solutions.size();++I)
        { const int Steps=Distance(Canvas,Solutions[I]); if (Steps<Best) { Best=Steps; At=static_cast<int>(I); } }
        return At;
    }
    bool CheckHint(int Rule,const sky::Grid& Canvas,const std::vector<sky::Grid>& Solutions,bool& SawRepair,bool& SawEmpty,bool& SawTie)
    {
        sky::Clue Out{-9,-8,-7,true}; const auto Before=Oracle(Rule,Canvas);
        if (!Before.GivensMatch || Before.Complete)
            return !sky::HintFor(Rule,Canvas,Out) && Out.CellIndex==-9 && Out.Height==-8 && Out.Remaining==-7 && Out.Repair;
        int Best=17; const int At=Nearest(Canvas,Solutions,Best); if (At<0) return false;
        int Ties=0; for (const auto& Solution:Solutions) if (Distance(Canvas,Solution)==Best) ++Ties;
        SawTie=SawTie || Ties>1; const auto& Target=Solutions[At]; int Chosen=-1;
        for (int I=0;I<16;++I) if (Canvas[I] && Canvas[I]!=Target[I]) { Chosen=I; break; }
        if (Chosen<0) for (int I=0;I<16;++I) if (!Canvas[I]) { Chosen=I; break; }
        if (!sky::HintFor(Rule,Canvas,Out) || Out.CellIndex<0 || Out.CellIndex>=16) return false;
        SawRepair=SawRepair || Out.Repair; SawEmpty=SawEmpty || !Out.Repair;
        sky::Grid Next=Canvas; Next[Out.CellIndex]=static_cast<std::uint8_t>(Out.Height); int After=17; Nearest(Next,Solutions,After);
        return Out.CellIndex==Chosen && Out.Height==Target[Chosen] && Out.Repair==(Canvas[Chosen]!=0) && Out.Remaining==Best && After==Best-1;
    }
    bool Apply(sky::Session& Run,const sky::Grid& Canvas)
    {
        const auto Fixed=Givens(Run.CurrentRule());
        for (int I=0;I<16;++I) if (!Fixed[I])
        { const auto Changed=Run.SetHeight(I,Canvas[I]); if (Changed!=sky::Change::Changed && Changed!=sky::Change::Unchanged) return false; }
        return Run.Canvas()==Canvas;
    }
    bool Solve(sky::Session& Run)
    {
        for (int Turn=0;Turn<=16;++Turn)
        {
            sky::Evaluation View; if (!Run.View(View)) return false; if (View.Complete) return true;
            sky::Clue Hint; if (!Run.Hint(Hint) || Run.SetHeight(Hint.CellIndex,Hint.Height)!=sky::Change::Changed) return false;
        }
        return false;
    }
    sky::Grid HistoryGrid(int Step)
    {
        sky::Grid Out{}; const int Gray=Step^(Step>>1);
        for (int Cell=0;Cell<7;++Cell) if (Gray&(1<<Cell)) Out[Cell]=1;
        return Out;
    }
}

int main()
{
    bool Fixture=true; const char* Names[3]={"First Towers","Courtyard View","Open Skyline"};
    for (int Rule=0;Rule<3;++Rule)
    {
        Fixture=Fixture && std::string(sky::Blueprints[Rule].Name)==Names[Rule] && sky::Blueprints[Rule].Givens==Givens(Rule);
        for (int Line=0;Line<4;++Line) Fixture=Fixture && sky::Blueprints[Rule].Left[Line]==Left[Rule][Line] &&
            sky::Blueprints[Rule].Right[Line]==Right[Rule][Line] && sky::Blueprints[Rule].Top[Line]==Top[Rule][Line] && sky::Blueprints[Rule].Bottom[Line]==Bottom[Rule][Line];
    }
    Check(Fixture,"three authored blueprints pin side orientation, unspecified zero clues and exact givens");
    bool Sightlines=true;
    for (int Code=0;Code<625;++Code)
    {
        int Value=Code; std::array<std::uint8_t,4> Line{};
        for (auto& Height:Line) { Height=static_cast<std::uint8_t>(Value%5); Value/=5; }
        Sightlines=sky::Visible(Line)==Sight(Line) && Sightlines;
    }
    Check(Sightlines && sky::Visible({{1,0,4,2}})==2 && sky::Visible({{0,0,0,0}})==0 && sky::Visible({{1,2,5,4}})==-1,
        "all625 bounded sightlines match an independent pairwise visibility oracle, ignoring zeros");
    auto BadGrid=Givens(0); BadGrid[1]=5; sky::Grid HighGrid{}; HighGrid[8]=255;
    Check(sky::ValidGrid(sky::Grid{}) && !sky::ValidGrid(BadGrid) && !sky::ValidGrid(HighGrid) && sky::SolutionCount(-1)==-1 && sky::SolutionCount(3)==-1,
        "height bounds and invalid solution queries are unavailable");
    const auto Latin=LatinGrids(); std::array<std::vector<sky::Grid>,3> Solutions; bool Reports=true;
    for (int Rule=0;Rule<3;++Rule) for (const auto& Canvas:Latin)
    {
        const auto Expected=Oracle(Rule,Canvas); sky::Evaluation Actual; const bool Accepted=sky::Evaluate(Rule,Canvas,Actual);
        Reports=Accepted && Equal(Expected,Actual) && Reports; if (Expected.Complete) Solutions[Rule].push_back(Canvas);
    }
    Check(Latin.size()==576 && Solutions[0].size()==1 && Solutions[1].size()==2 && Solutions[2].size()==3 &&
        sky::SolutionCount(0)==1 && sky::SolutionCount(1)==2 && sky::SolutionCount(2)==3,
        "independent row permutations find all576 Latin4 grids and blueprint solution counts1/2/3");
    Check(Reports,"all1728 Latin-grid/blueprint reports match independent pairwise conflicts and visibility");
    sky::Session Run; bool AllSolutions=true;
    for (int Rule=0;Rule<3;++Rule) for (const auto& Canvas:Solutions[Rule])
    {
        Run.Begin(); if (Rule) Run.SelectRule(Rule); sky::Evaluation View;
        AllSolutions=Apply(Run,Canvas) && Run.View(View) && View.Complete && Run.EverCompleted(Rule) && Run.CompletedCount()==1 && AllSolutions;
    }
    Check(AllSolutions,"every valid completion is accepted, including both and all three multi-solution alternatives");
    sky::Grid Partial{}; Partial[0]=2; Partial[2]=4; sky::Evaluation View;
    Check(sky::Evaluate(2,Partial,View) && View.Left[0]==2 && !View.RowFull[0] && View.ClueCount==8 && View.ClueMatches==0 && !View.Complete,
        "a numerically matching partial sightline does not claim a matched clue");
    sky::Grid Repeats{}; Repeats[0]=Repeats[1]=Repeats[4]=2; std::array<bool,16> ExpectedConflicts{}; ExpectedConflicts[0]=ExpectedConflicts[1]=ExpectedConflicts[4]=true;
    Check(sky::Evaluate(2,Repeats,View) && View.Conflicts==ExpectedConflicts && !View.LatinPossible && View.GivensMatch && View.Filled==3,
        "all members of repeated positive rows and columns are marked, including their intersection");
    sky::Grid FullDuplicate{}; FullDuplicate[0]=2; FullDuplicate[1]=2; FullDuplicate[2]=1; FullDuplicate[3]=4;
    Check(sky::Evaluate(2,FullDuplicate,View) && View.RowFull[0] && View.Left[0]==2 && View.ClueMatches==0 && !View.LatinPossible,
        "a full duplicate line stays full but cannot match its otherwise equal side clue");
    auto WrongGiven=Givens(0); WrongGiven[0]=2;
    Check(sky::Evaluate(0,WrongGiven,View) && !View.GivensMatch && View.Conflicts[0] && View.LatinPossible && !View.Complete,
        "given mismatch is independent of positive Latin repeats");
    bool PartialReports=true;
    for (int Rule=0;Rule<3;++Rule)
    {
        const auto& Solution=Solutions[Rule].front();
        for (int Phase=0;Phase<16;++Phase)
        {
            auto Canvas=Givens(Rule);
            for (int I=0;I<16;++I) if (!Canvas[I] && (I+Phase)%3) Canvas[I]=Solution[I];
            if (!Givens(Rule)[Phase]) Canvas[Phase]=static_cast<std::uint8_t>(1+Solution[Phase]%4);
            sky::Evaluation Actual; const bool Accepted=sky::Evaluate(Rule,Canvas,Actual);
            PartialReports=Accepted && Equal(Actual,Oracle(Rule,Canvas)) && PartialReports;
        }
    }
    Check(PartialReports,"partial and contradictory reports match an independent all-field oracle");
    sky::Evaluation Sentinel; Sentinel.Conflicts.fill(true); Sentinel.RowFull.fill(true); Sentinel.ColumnFull.fill(true);
    Sentinel.Left.fill(-1); Sentinel.Right.fill(-2); Sentinel.Top.fill(-3); Sentinel.Bottom.fill(-4);
    Sentinel.Filled=-5; Sentinel.ClueMatches=-6; Sentinel.ClueCount=-7; Sentinel.GivensMatch=Sentinel.LatinPossible=false; Sentinel.Complete=true; View=Sentinel;
    Check(!sky::Evaluate(-1,sky::Grid{},View) && !sky::Evaluate(3,sky::Grid{},View) && !sky::Evaluate(0,BadGrid,View) &&
        !sky::Evaluate(0,HighGrid,View) && Equal(View,Sentinel),"invalid evaluation preserves every caller field");
    bool Hints=true,SawRepair=false,SawEmpty=false,SawTie=false;
    for (int Rule=0;Rule<3;++Rule)
    {
        Hints=CheckHint(Rule,Givens(Rule),Solutions[Rule],SawRepair,SawEmpty,SawTie) && Hints;
        for (const auto& Canvas:Latin) Hints=CheckHint(Rule,Canvas,Solutions[Rule],SawRepair,SawEmpty,SawTie) && Hints;
        for (int Phase=0;Phase<16;++Phase)
        {
            auto Canvas=Givens(Rule); const auto& Solution=Solutions[Rule].front();
            for (int I=0;I<16;++I) if (!Canvas[I] && (I+Phase)%3) Canvas[I]=Solution[I];
            if (!Givens(Rule)[Phase]) Canvas[Phase]=static_cast<std::uint8_t>(1+Solution[Phase]%4);
            Hints=CheckHint(Rule,Canvas,Solutions[Rule],SawRepair,SawEmpty,SawTie) && Hints;
        }
    }
    Check(Hints && SawRepair && SawEmpty && SawTie,"nearest lexicographic hints repair or fill one cell and reduce independent Hamming distance exactly one");
    auto Repair=Solutions[0].front(); Repair[1]=0; Repair[2]=1; sky::Clue Hint;
    const bool RepairFirst=sky::HintFor(0,Repair,Hint) && Hint.CellIndex==2 && Hint.Height==3 && Hint.Remaining==2 && Hint.Repair;
    Repair[2]=3;
    Check(RepairFirst && sky::HintFor(0,Repair,Hint) && Hint.CellIndex==1 && Hint.Height==2 && Hint.Remaining==1 && !Hint.Repair,
        "wrong nonzero repairs precede an earlier empty cell and directly assign the correct height");
    Check(sky::HintFor(2,sky::Grid{},Hint) && Hint.CellIndex==0 && Hint.Height==Solutions[2].front()[0] && Hint.Remaining==16 && !Hint.Repair,
        "an empty multi-solution skyline chooses its lexicographically first completion");
    Hint={-9,-8,-7,true}; auto MissingGiven=Givens(0); MissingGiven[0]=0;
    Check(!sky::HintFor(-1,sky::Grid{},Hint) && !sky::HintFor(3,sky::Grid{},Hint) && !sky::HintFor(0,BadGrid,Hint) &&
        !sky::HintFor(0,WrongGiven,Hint) && !sky::HintFor(0,MissingGiven,Hint) && !sky::HintFor(0,Solutions[0].front(),Hint) &&
        Hint.CellIndex==-9 && Hint.Height==-8 && Hint.Remaining==-7 && Hint.Repair,
        "invalid, missing/wrong given and solved hints refuse atomically");
    sky::Session Inactive; View=Sentinel;
    Check(!Inactive.Active() && Inactive.SetHeight(1,2)==sky::Change::Unavailable && !Inactive.SelectRule(1) && !Inactive.Undo() && !Inactive.Redo() &&
        !Inactive.Restart() && !Inactive.View(View) && Equal(View,Sentinel) && !Inactive.Hint(Hint) && Inactive.CompletedCount()==0 && !Inactive.EverCompleted(0),
        "inactive sessions refuse actions and leave outputs unchanged");
    Run.Begin(); const auto Initial=Run.Canvas(); Run.SetHeight(1,2); Run.Undo(); const auto OldUndo=Run.UndoCount(),OldRedo=Run.RedoCount();
    Check(Initial==Givens(0) && Run.SetHeight(1,0)==sky::Change::Unchanged && Run.SetHeight(0,1)==sky::Change::Fixed && Run.SetHeight(0,4)==sky::Change::Fixed &&
        Run.SetHeight(-1,1)==sky::Change::Unavailable && Run.SetHeight(16,1)==sky::Change::Unavailable && Run.SetHeight(1,-1)==sky::Change::Unavailable &&
        Run.SetHeight(1,5)==sky::Change::Unavailable && !Run.SelectRule(-1) && !Run.SelectRule(3) && !Run.SelectRule(0) && Run.Canvas()==Initial &&
        Run.UndoCount()==OldUndo && Run.RedoCount()==OldRedo && Run.Redo() && Run.Canvas()[1]==2,
        "fixed/no-op/invalid edits retain givens, canvas and the existing redo branch");
    Run.Begin();
    Check(Run.SetHeight(1,1)==sky::Change::Changed && Run.SetHeight(4,1)==sky::Change::Changed && Run.View(View) && !View.LatinPossible &&
        View.Conflicts[0] && View.Conflicts[1] && View.Conflicts[4] && Run.SetHeight(1,0)==sky::Change::Changed && Run.Canvas()[1]==0,
        "editable contradictions are accepted, reported and erasable");
    Run.Begin(); bool Separate=true; std::array<sky::Grid,3> Saved{}; std::array<std::size_t,3> SavedUndo{};
    for (int Rule=0;Rule<3;++Rule)
    {
        if (Rule) Separate=Run.SelectRule(Rule) && Separate;
        const bool Solved=Solve(Run); Saved[Rule]=Run.Canvas(); SavedUndo[Rule]=Run.UndoCount();
        Separate=Solved && Run.EverCompleted(Rule) && Run.CompletedCount()==Rule+1 && Separate;
    }
    Run.SelectRule(0);
    Separate=Separate && Run.Canvas()==Saved[0] && Run.UndoCount()==SavedUndo[0] && Run.Undo() && Run.View(View) && !View.Complete &&
        Run.EverCompleted(0) && Run.CompletedCount()==3 && Run.Redo() && Run.Canvas()==Saved[0];
    Check(Separate,"blueprints retain independent drawings/history and completion is reversible while first completion remains");
    Check(Run.Restart() && Run.Canvas()==Givens(0) && Run.UndoCount()==0 && Run.RedoCount()==0 && Run.EverCompleted(0) && Run.CompletedCount()==3 &&
        Run.SelectRule(1) && Run.Canvas()==Saved[1] && Run.UndoCount()==SavedUndo[1] && Run.SelectRule(2) && Run.Canvas()==Saved[2] && Run.UndoCount()==SavedUndo[2],
        "restart restores only current givens/history and retains other drawings and ever-completed flags");
    Run.Begin(); Run.SelectRule(2); bool History=true;
    for (int Step=1;Step<=73;++Step)
    {
        const auto Previous=HistoryGrid(Step-1),Next=HistoryGrid(Step); int Cell=0; while (Previous[Cell]==Next[Cell]) ++Cell;
        const auto Changed=Run.SetHeight(Cell,Next[Cell]);
        History=Changed==sky::Change::Changed && Run.Canvas()==Next && Run.UndoCount()==static_cast<std::size_t>(Step<64?Step:64) && Run.RedoCount()==0 && History;
    }
    for (int Step=72;Step>=9;--Step)
    {
        const bool Moved=Run.Undo();
        History=Moved && Run.Canvas()==HistoryGrid(Step) && Run.UndoCount()==static_cast<std::size_t>(Step-9) && Run.RedoCount()==static_cast<std::size_t>(73-Step) && History;
    }
    Check(History && HistoryGrid(9)!=HistoryGrid(73) && HistoryGrid(9)!=sky::Grid{} && !Run.Undo() && Run.Canvas()==HistoryGrid(9),
        "73 unique single-cell edits preserve every latest64 undo state and stop exactly at dropped9");
    for (int Step=10;Step<=73;++Step)
    {
        const bool Moved=Run.Redo();
        History=Moved && Run.Canvas()==HistoryGrid(Step) && Run.UndoCount()==static_cast<std::size_t>(Step-9) && Run.RedoCount()==static_cast<std::size_t>(73-Step) && History;
    }
    Check(History && !Run.Redo() && Run.Canvas()==HistoryGrid(73),"each intermediate redo grid returns exactly to state73");
    Run.Undo(); const auto Branch=Run.Canvas();
    Check(Run.SetHeight(15,4)==sky::Change::Changed && Run.Canvas()[15]==4 && Run.RedoCount()==0 && Run.Undo() && Run.Canvas()==Branch,
        "a new edit after undo clears redo and remains exactly undoable");
    Run.Begin();
    Check(Run.Canvas()==Givens(0) && Run.CompletedCount()==0 && Run.UndoCount()==0 && Run.RedoCount()==0 && !Run.Restart() &&
        !Run.EverCompleted(-1) && !Run.EverCompleted(3),"Begin resets every local attempt while a clean restart remains a no-op");
    std::cout<<Checks<<" checks, "<<Failures<<" failed;576 Latin row-permutation oracle,625 visibility lines, nearest completion hints and73-edit history\n";
    return Failures?1:0;
}
