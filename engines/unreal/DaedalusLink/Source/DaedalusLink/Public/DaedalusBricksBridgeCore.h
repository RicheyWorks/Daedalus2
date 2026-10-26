// SPDX-License-Identifier: MIT
#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <limits>

// Original local blueprint practice. Length is a puzzle allowance, not stock,
// structural physics, rewards, profiles or a Java random-generation mapping.
namespace daedalus::brickbridge
{
    inline constexpr int PadCount=9,LinkCount=12,RuleCount=3,HistoryLimit=64;
    struct Link { int From,To; };
    inline constexpr std::array<Link,LinkCount> Links{{
        {0,1},{1,2},{3,4},{4,5},{6,7},{7,8},{0,3},{1,4},{2,5},{3,6},{4,7},{5,8}
    }};
    struct Blueprint
    {
        const char* Name;
        std::array<int,3> Columns,Rows;
        int AllowedMask;
    };
    inline constexpr std::array<Blueprint,RuleCount> Blueprints{{
        {"Open Spans",{{0,2,5}},{{0,1,4}},4095},
        {"Side Repair",{{0,2,5}},{{0,1,4}},4095^(1<<2)^(1<<10)},
        {"Long Crossing",{{0,1,4}},{{0,2,5}},4095^(1<<0)^(1<<8)}
    }};
    struct Evaluation
    {
        std::array<bool,PadCount> LinkedToHome{};
        int UsedLength=0,PadsConnected=0,Components=PadCount,SelectedCount=0;
        bool WithinLength=false,Complete=false;
    };
    struct Clue { int LinkIndex=-1; bool ToSelected=false; int Remaining=0; };
    enum class Change { Changed,Unavailable,Closed,OverLength };
    inline int LinkLength(int Rule,int LinkIndex)
    {
        if (Rule<0 || Rule>=RuleCount || LinkIndex<0 || LinkIndex>=LinkCount) return -1;
        const auto& R=Blueprints[Rule]; const auto& L=Links[LinkIndex];
        const int X=R.Columns[L.From%3]-R.Columns[L.To%3],Y=R.Rows[L.From/3]-R.Rows[L.To/3];
        return (X<0?-X:X)+(Y<0?-Y:Y);
    }
    namespace detail
    {
        inline constexpr int StateCount=1<<LinkCount;
        inline bool LegalMask(int Rule,int Mask)
        { return Rule>=0 && Rule<RuleCount && Mask>=0 && Mask<StateCount && !(Mask&~Blueprints[Rule].AllowedMask); }
        /** Fixed-size adaptation of util/DSU.java: two-pass path compression and
         * union by rank. KruskalsGenerator uses the same successful-union test;
         * these weighted blueprints and exhaustive optimum cache are new rules. */
        struct DSU
        {
            std::array<int,PadCount> Parent{};
            std::array<std::uint8_t,PadCount> Rank{};
            int Components=PadCount;
            DSU() { for (int I=0;I<PadCount;++I) Parent[I]=I; }
            int Find(int At)
            {
                int Root=At; while (Parent[Root]!=Root) Root=Parent[Root];
                while (Parent[At]!=Root) { const int Next=Parent[At]; Parent[At]=Root; At=Next; }
                return Root;
            }
            bool Join(int A,int B)
            {
                A=Find(A); B=Find(B); if (A==B) return false;
                if (Rank[A]<Rank[B]) { const int Previous=A; A=B; B=Previous; }
                Parent[B]=A; if (Rank[A]==Rank[B]) ++Rank[A]; --Components; return true;
            }
        };
        inline Evaluation Analyse(int Rule,int Mask)
        {
            Evaluation Out; DSU Sets;
            for (int I=0;I<LinkCount;++I) if (Mask&(1<<I))
            { ++Out.SelectedCount; Out.UsedLength+=LinkLength(Rule,I); Sets.Join(Links[I].From,Links[I].To); }
            Out.Components=Sets.Components; const int Home=Sets.Find(0);
            for (int I=0;I<PadCount;++I)
            { Out.LinkedToHome[I]=Sets.Find(I)==Home; if (Out.LinkedToHome[I]) ++Out.PadsConnected; }
            return Out;
        }
        struct RuleCache
        {
            std::array<std::uint16_t,StateCount> Winners{};
            std::size_t Count=0;
            int Minimum=-1;
        };
        static_assert(sizeof(std::array<RuleCache,RuleCount>)<100*1024,"bounded blueprint cache");
        inline std::array<RuleCache,RuleCount> BuildCaches()
        {
            std::array<RuleCache,RuleCount> Out{};
            for (int Rule=0;Rule<RuleCount;++Rule)
            {
                auto& Cache=Out[Rule]; int Best=std::numeric_limits<int>::max();
                for (int Mask=0;Mask<StateCount;++Mask)
                {
                    if (!LegalMask(Rule,Mask)) continue;
                    const auto View=Analyse(Rule,Mask); if (View.Components!=1) continue;
                    if (View.UsedLength<Best) { Best=View.UsedLength; Cache.Count=0; }
                    if (View.UsedLength==Best) Cache.Winners[Cache.Count++]=static_cast<std::uint16_t>(Mask);
                }
                if (Cache.Count) Cache.Minimum=Best;
            }
            return Out;
        }
        inline const std::array<RuleCache,RuleCount>& Caches()
        { static const auto Value=BuildCaches(); return Value; }
        inline int Bits(int Mask)
        { int Count=0; while (Mask) { Mask&=Mask-1; ++Count; } return Count; }
    }
    inline int LengthLimit(int Rule)
    { return Rule>=0 && Rule<RuleCount?detail::Caches()[Rule].Minimum:-1; }
    inline bool Evaluate(int Rule,int Mask,Evaluation& Out)
    {
        if (!detail::LegalMask(Rule,Mask)) return false;
        auto Prepared=detail::Analyse(Rule,Mask); const int Limit=LengthLimit(Rule);
        Prepared.WithinLength=Limit>=0 && Prepared.UsedLength<=Limit;
        Prepared.Complete=Prepared.PadsConnected==PadCount && Prepared.WithinLength;
        Out=Prepared; return true;
    }
    inline bool HintFor(int Rule,int Mask,Clue& Out)
    {
        Evaluation View;
        if (!Evaluate(Rule,Mask,View) || !View.WithinLength || View.Complete) return false;
        const auto& Cache=detail::Caches()[Rule]; int Winner=-1,Distance=LinkCount+1;
        for (std::size_t I=0;I<Cache.Count;++I)
        {
            const int Candidate=Cache.Winners[I],Steps=detail::Bits(Mask^Candidate);
            // Cache order is numeric. Strict improvement keeps its tie winner.
            if (Steps<Distance) { Winner=Candidate; Distance=Steps; }
        }
        if (Winner<0) return false;
        const int Extras=Mask&~Winner,Choices=Extras?Extras:Winner&~Mask;
        Clue Prepared; Prepared.Remaining=Distance;
        for (int I=0;I<LinkCount;++I) if (Choices&(1<<I))
        { Prepared.LinkIndex=I; Prepared.ToSelected=(Winner&(1<<I))!=0; Out=Prepared; return true; }
        return false;
    }

    class Session
    {
    public:
        bool Begin()
        {
            for (const auto& Cache:detail::Caches()) if (!Cache.Count || Cache.Minimum<1) return false;
            *this=Session{}; bActive=true; return true;
        }
        bool Active() const { return bActive; }
        int CurrentRule() const { return Selected; }
        int Mask() const { return Attempts[Selected].Mask; }
        bool SelectRule(int Rule)
        { if (!bActive || Rule<0 || Rule>=RuleCount || Rule==Selected) return false; Selected=Rule; return true; }
        bool View(Evaluation& Out) const { return bActive && Evaluate(Selected,Mask(),Out); }
        bool Hint(Clue& Out) const { return bActive && HintFor(Selected,Mask(),Out); }
        std::size_t UndoCount() const { return Attempts[Selected].UndoSize; }
        std::size_t RedoCount() const { return Attempts[Selected].RedoSize; }
        bool EverCompleted(int Rule) const { return bActive && Rule>=0 && Rule<RuleCount && Attempts[Rule].Ever; }
        int CompletedCount() const
        { int Count=0; if (bActive) for (const auto& Entry:Attempts) if (Entry.Ever) ++Count; return Count; }
        Change Toggle(int LinkIndex)
        {
            if (!bActive || LinkIndex<0 || LinkIndex>=LinkCount) return Change::Unavailable;
            if (!(Blueprints[Selected].AllowedMask&(1<<LinkIndex))) return Change::Closed;
            const int Next=Mask()^(1<<LinkIndex); Evaluation Prepared;
            if (!Evaluate(Selected,Next,Prepared)) return Change::Unavailable;
            if (!Prepared.WithinLength) return Change::OverLength;
            auto& Entry=Attempts[Selected]; Push(Entry.Undo,Entry.UndoSize,Entry.Mask);
            Entry.Mask=Next; Entry.RedoSize=0; if (Prepared.Complete) Entry.Ever=true; return Change::Changed;
        }
        bool Undo()
        {
            if (!bActive) return false; auto& Entry=Attempts[Selected]; if (!Entry.UndoSize) return false;
            const int Next=Entry.Undo[Entry.UndoSize-1]; Evaluation Prepared;
            if (!Evaluate(Selected,Next,Prepared) || !Prepared.WithinLength) return false;
            Push(Entry.Redo,Entry.RedoSize,Entry.Mask); Entry.Mask=Next; --Entry.UndoSize;
            if (Prepared.Complete) Entry.Ever=true; return true;
        }
        bool Redo()
        {
            if (!bActive) return false; auto& Entry=Attempts[Selected]; if (!Entry.RedoSize) return false;
            const int Next=Entry.Redo[Entry.RedoSize-1]; Evaluation Prepared;
            if (!Evaluate(Selected,Next,Prepared) || !Prepared.WithinLength) return false;
            Push(Entry.Undo,Entry.UndoSize,Entry.Mask); Entry.Mask=Next; --Entry.RedoSize;
            if (Prepared.Complete) Entry.Ever=true; return true;
        }
        bool Restart()
        {
            if (!bActive) return false; auto& Entry=Attempts[Selected];
            if (!Entry.Mask && !Entry.UndoSize && !Entry.RedoSize) return false;
            Entry.Mask=0; Entry.UndoSize=Entry.RedoSize=0; return true;
        }
    private:
        struct Attempt
        {
            int Mask=0;
            std::array<std::uint16_t,HistoryLimit> Undo{},Redo{};
            std::size_t UndoSize=0,RedoSize=0;
            bool Ever=false;
        };
        static void Push(std::array<std::uint16_t,HistoryLimit>& History,std::size_t& Count,int Mask)
        {
            if (Count==History.size()) { for (std::size_t I=1;I<Count;++I) History[I-1]=History[I]; --Count; }
            History[Count++]=static_cast<std::uint16_t>(Mask);
        }
        std::array<Attempt,RuleCount> Attempts{};
        int Selected=0;
        bool bActive=false;
    };
}
