// SPDX-License-Identifier: MIT
#pragma once
#include <array>
#include <cstddef>
#include <cstdint>

// Original local tower-blueprint practice. Heights and clues are puzzle data,
// not construction physics, stock, rewards, profiles or a Sudoku integration.
namespace daedalus::skyline
{
    inline constexpr int Side=4,CellCount=16,RuleCount=3,HistoryLimit=64;
    using Grid=std::array<std::uint8_t,CellCount>;
    struct Blueprint
    {
        const char* Name;
        std::array<int,Side> Left,Right,Top,Bottom;
        Grid Givens;
    };
    inline constexpr std::array<Blueprint,RuleCount> Blueprints{{
        {"First Towers",{{4,3,2,1}},{{1,2,2,2}},{{4,3,2,1}},{{1,2,2,2}},
            {{1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,3}}},
        {"Courtyard View",{{2,2,1,3}},{{2,2,3,1}},{{3,1,2,2}},{{2,2,3,1}},
            {{0,0,0,0,0,1,0,0,0,0,3,0,0,0,0,0}}},
        {"Open Skyline",{{2,1,3,2}},{{0,0,0,0}},{{2,4,1,2}},{{0,0,0,0}},Grid{}}
    }};
    struct Evaluation
    {
        std::array<bool,CellCount> Conflicts{};
        std::array<int,Side> Left{},Right{},Top{},Bottom{};
        std::array<bool,Side> RowFull{},ColumnFull{};
        int Filled=0,ClueMatches=0,ClueCount=0;
        bool GivensMatch=true,LatinPossible=true,Complete=false;
    };
    struct Clue { int CellIndex=-1,Height=0,Remaining=0; bool Repair=false; };
    enum class Change { Changed,Unavailable,Fixed,Unchanged };
    inline bool ValidGrid(const Grid& Canvas)
    { for (auto Height:Canvas) if (Height>Side) return false; return true; }
    inline int Visible(const std::array<std::uint8_t,Side>& Line)
    {
        int Highest=0,Count=0;
        for (auto Height:Line)
        {
            if (Height>Side) return -1;
            if (Height>Highest) { Highest=Height; ++Count; }
        }
        return Count;
    }
    inline bool Evaluate(int Rule,const Grid& Canvas,Evaluation& Out)
    {
        if (Rule<0 || Rule>=RuleCount || !ValidGrid(Canvas)) return false;
        Evaluation Prepared; const auto& Plan=Blueprints[Rule];
        for (int Cell=0;Cell<CellCount;++Cell)
        {
            if (Canvas[Cell]) ++Prepared.Filled;
            if (Plan.Givens[Cell] && Canvas[Cell]!=Plan.Givens[Cell])
            { Prepared.GivensMatch=false; Prepared.Conflicts[Cell]=true; }
        }
        const auto CountClue=[&Prepared](int Expected,int Seen,bool Full,bool Unique)
        { if (Expected) { ++Prepared.ClueCount; if (Full && Unique && Expected==Seen) ++Prepared.ClueMatches; } };
        for (int Line=0;Line<Side;++Line)
        {
            std::array<std::uint8_t,Side> Row{},Column{},ReverseRow{},ReverseColumn{};
            std::array<int,Side+1> RowCounts{},ColumnCounts{};
            bool RowFull=true,ColumnFull=true,RowUnique=true,ColumnUnique=true;
            for (int At=0;At<Side;++At)
            {
                Row[At]=Canvas[Line*Side+At]; Column[At]=Canvas[At*Side+Line];
                if (Row[At]) ++RowCounts[Row[At]]; else RowFull=false;
                if (Column[At]) ++ColumnCounts[Column[At]]; else ColumnFull=false;
            }
            for (int At=0;At<Side;++At)
            {
                ReverseRow[At]=Row[Side-1-At]; ReverseColumn[At]=Column[Side-1-At];
                if (Row[At] && RowCounts[Row[At]]>1)
                { Prepared.Conflicts[Line*Side+At]=true; RowUnique=false; }
                if (Column[At] && ColumnCounts[Column[At]]>1)
                { Prepared.Conflicts[At*Side+Line]=true; ColumnUnique=false; }
            }
            Prepared.RowFull[Line]=RowFull; Prepared.ColumnFull[Line]=ColumnFull;
            Prepared.Left[Line]=Visible(Row); Prepared.Right[Line]=Visible(ReverseRow);
            Prepared.Top[Line]=Visible(Column); Prepared.Bottom[Line]=Visible(ReverseColumn);
            if (!RowUnique || !ColumnUnique) Prepared.LatinPossible=false;
            CountClue(Plan.Left[Line],Prepared.Left[Line],RowFull,RowUnique);
            CountClue(Plan.Right[Line],Prepared.Right[Line],RowFull,RowUnique);
            CountClue(Plan.Top[Line],Prepared.Top[Line],ColumnFull,ColumnUnique);
            CountClue(Plan.Bottom[Line],Prepared.Bottom[Line],ColumnFull,ColumnUnique);
        }
        Prepared.Complete=Prepared.Filled==CellCount && Prepared.GivensMatch && Prepared.LatinPossible && Prepared.ClueMatches==Prepared.ClueCount;
        Out=Prepared; return true;
    }
    namespace detail
    {
        inline constexpr int LatinCount=576;
        struct Catalogue
        {
            std::array<Grid,LatinCount> Latin{};
            std::array<std::array<std::uint16_t,LatinCount>,RuleCount> Matching{};
            std::array<int,RuleCount> Counts{};
            int Count=0;
        };
        static_assert(sizeof(Catalogue)<100*1024,"bounded skyline catalogue");
        // Cell-wise row/column bit constraints enumerate every Latin4 grid in
        // lexicographic order. Tests use a separate row-permutation oracle.
        inline void Enumerate(int Cell,Grid& Canvas,std::array<int,Side>& Rows,std::array<int,Side>& Columns,Catalogue& Out)
        {
            if (Cell==CellCount)
            { if (Out.Count<LatinCount) Out.Latin[Out.Count]=Canvas; ++Out.Count; return; }
            const int Row=Cell/Side,Column=Cell%Side;
            for (int Height=1;Height<=Side;++Height)
            {
                const int Bit=1<<Height; if ((Rows[Row]|Columns[Column])&Bit) continue;
                Canvas[Cell]=static_cast<std::uint8_t>(Height); Rows[Row]|=Bit; Columns[Column]|=Bit;
                Enumerate(Cell+1,Canvas,Rows,Columns,Out);
                Rows[Row]&=~Bit; Columns[Column]&=~Bit;
            }
        }
        inline Catalogue BuildCatalogue()
        {
            Catalogue Out; Grid Canvas{}; std::array<int,Side> Rows{},Columns{};
            Enumerate(0,Canvas,Rows,Columns,Out); if (Out.Count!=LatinCount) return Out;
            for (int Rule=0;Rule<RuleCount;++Rule) for (int I=0;I<Out.Count;++I)
            {
                Evaluation View;
                if (Evaluate(Rule,Out.Latin[I],View) && View.Complete)
                    Out.Matching[Rule][Out.Counts[Rule]++]=static_cast<std::uint16_t>(I);
            }
            return Out;
        }
        inline const Catalogue& Cache() { static const auto Value=BuildCatalogue(); return Value; }
    }
    inline int SolutionCount(int Rule)
    { return Rule>=0 && Rule<RuleCount?detail::Cache().Counts[Rule]:-1; }
    inline bool HintFor(int Rule,const Grid& Canvas,Clue& Out)
    {
        Evaluation View;
        if (!Evaluate(Rule,Canvas,View) || !View.GivensMatch || View.Complete) return false;
        const auto& Cache=detail::Cache(); const Grid* Nearest=nullptr; int Distance=CellCount+1;
        for (int At=0;At<Cache.Counts[Rule];++At)
        {
            const auto& Candidate=Cache.Latin[Cache.Matching[Rule][At]]; int Steps=0;
            for (int Cell=0;Cell<CellCount;++Cell) if (Canvas[Cell]!=Candidate[Cell]) ++Steps;
            if (Steps<Distance) { Distance=Steps; Nearest=&Candidate; }
        }
        if (!Nearest) return false;
        int Chosen=-1;
        for (int Cell=0;Cell<CellCount;++Cell) if (Canvas[Cell] && Canvas[Cell]!=(*Nearest)[Cell]) { Chosen=Cell; break; }
        if (Chosen<0) for (int Cell=0;Cell<CellCount;++Cell) if (!Canvas[Cell]) { Chosen=Cell; break; }
        if (Chosen<0) return false;
        Clue Prepared; Prepared.CellIndex=Chosen; Prepared.Height=(*Nearest)[Chosen]; Prepared.Remaining=Distance; Prepared.Repair=Canvas[Chosen]!=0;
        Out=Prepared; return true;
    }
    class Session
    {
    public:
        bool Begin()
        {
            if (detail::Cache().Count!=detail::LatinCount) return false;
            for (int Rule=0;Rule<RuleCount;++Rule) if (SolutionCount(Rule)<1) return false;
            *this=Session{}; for (int Rule=0;Rule<RuleCount;++Rule) Attempts[Rule].Canvas=Blueprints[Rule].Givens;
            bActive=true; return true;
        }
        bool Active() const { return bActive; }
        int CurrentRule() const { return Selected; }
        const Grid& Canvas() const { return Attempts[Selected].Canvas; }
        bool SelectRule(int Rule)
        { if (!bActive || Rule<0 || Rule>=RuleCount || Rule==Selected) return false; Selected=Rule; return true; }
        std::size_t UndoCount() const { return Attempts[Selected].UndoSize; }
        std::size_t RedoCount() const { return Attempts[Selected].RedoSize; }
        bool EverCompleted(int Rule) const { return bActive && Rule>=0 && Rule<RuleCount && Attempts[Rule].Ever; }
        int CompletedCount() const
        { int Count=0; if (bActive) for (const auto& Entry:Attempts) if (Entry.Ever) ++Count; return Count; }
        bool View(Evaluation& Out) const { return bActive && Evaluate(Selected,Canvas(),Out); }
        bool Hint(Clue& Out) const { return bActive && HintFor(Selected,Canvas(),Out); }
        Change SetHeight(int Cell,int Height)
        {
            if (!bActive || Cell<0 || Cell>=CellCount || Height<0 || Height>Side) return Change::Unavailable;
            if (Blueprints[Selected].Givens[Cell]) return Change::Fixed;
            if (Canvas()[Cell]==Height) return Change::Unchanged;
            auto& Entry=Attempts[Selected]; Grid Next=Entry.Canvas; Next[Cell]=static_cast<std::uint8_t>(Height); Evaluation Prepared;
            if (!Evaluate(Selected,Next,Prepared)) return Change::Unavailable;
            Push(Entry.Undo,Entry.UndoSize,Entry.Canvas); Entry.Canvas=Next; Entry.RedoSize=0;
            if (Prepared.Complete) Entry.Ever=true; return Change::Changed;
        }
        bool Undo()
        {
            if (!bActive) return false; auto& Entry=Attempts[Selected]; if (!Entry.UndoSize) return false;
            const Grid Next=Entry.Undo[Entry.UndoSize-1]; Evaluation Prepared;
            if (!Evaluate(Selected,Next,Prepared)) return false;
            Push(Entry.Redo,Entry.RedoSize,Entry.Canvas); Entry.Canvas=Next; --Entry.UndoSize;
            if (Prepared.Complete) Entry.Ever=true; return true;
        }
        bool Redo()
        {
            if (!bActive) return false; auto& Entry=Attempts[Selected]; if (!Entry.RedoSize) return false;
            const Grid Next=Entry.Redo[Entry.RedoSize-1]; Evaluation Prepared;
            if (!Evaluate(Selected,Next,Prepared)) return false;
            Push(Entry.Undo,Entry.UndoSize,Entry.Canvas); Entry.Canvas=Next; --Entry.RedoSize;
            if (Prepared.Complete) Entry.Ever=true; return true;
        }
        bool Restart()
        {
            if (!bActive) return false; auto& Entry=Attempts[Selected];
            if (Entry.Canvas==Blueprints[Selected].Givens && !Entry.UndoSize && !Entry.RedoSize) return false;
            Entry.Canvas=Blueprints[Selected].Givens; Entry.UndoSize=Entry.RedoSize=0; return true;
        }
    private:
        struct Attempt
        {
            Grid Canvas{}; std::array<Grid,HistoryLimit> Undo{},Redo{};
            std::size_t UndoSize=0,RedoSize=0; bool Ever=false;
        };
        static void Push(std::array<Grid,HistoryLimit>& History,std::size_t& Count,const Grid& Canvas)
        {
            if (Count==History.size()) { for (std::size_t I=1;I<Count;++I) History[I-1]=History[I]; --Count; }
            History[Count++]=Canvas;
        }
        std::array<Attempt,RuleCount> Attempts{}; int Selected=0; bool bActive=false;
    };
}
