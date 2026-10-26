// SPDX-License-Identifier: MIT
#pragma once
#include <array>
#include <cstddef>
#include <cstdint>

// Original Gallery colour/light practice. Channel presence, not photometry,
// server art, player identity, rewards or durable profile authority.
namespace daedalus::spectrum
{
    inline constexpr int RouterCount=6,WindowCount=4,PictureCount=3,HistoryLimit=64;
    struct Router { std::uint8_t Channel; std::array<int,2> Windows; };
    inline constexpr std::array<Router,RouterCount> Routers{{
        {1,{{0,1}}},{2,{{0,2}}},{4,{{0,3}}},{1,{{2,1}}},{2,{{1,3}}},{4,{{1,2}}}
    }};
    struct Picture { const char* Name; int StartMask; std::array<std::uint8_t,WindowCount> Targets; };
    inline constexpr std::array<Picture,PictureCount> Pictures{{
        {"Green Window",63,{{2,5,1,6}}},
        {"Paper Light",63,{{7,6,1,0}}},
        {"Sunset Glass",0,{{5,3,6,0}}}
    }};
    inline const char* ColourName(int Channels)
    {
        static const char* Names[]={"Unlit","Red","Green","Yellow","Blue","Magenta","Cyan","White"};
        return Channels>=0 && Channels<8?Names[Channels]:"Unavailable";
    }
    struct Evaluation
    {
        std::array<std::uint8_t,WindowCount> Channels{};
        int Matched=0;
        bool Complete=false;
    };
    inline bool Evaluate(int PictureIndex,int Mask,Evaluation& Out)
    {
        if (PictureIndex<0 || PictureIndex>=PictureCount || Mask<0 || Mask>=(1<<RouterCount)) return false;
        Evaluation Prepared;
        for (int I=0;I<RouterCount;++I)
        {
            const auto& Beam=Routers[I]; const int Destination=Beam.Windows[(Mask>>I)&1];
            Prepared.Channels[Destination]=static_cast<std::uint8_t>(Prepared.Channels[Destination]|Beam.Channel);
        }
        for (int I=0;I<WindowCount;++I) if (Prepared.Channels[I]==Pictures[PictureIndex].Targets[I]) ++Prepared.Matched;
        Prepared.Complete=Prepared.Matched==WindowCount;
        Out=Prepared; return true;
    }
    struct Clue { int RouterIndex=-1; bool ToB=false; int Remaining=0; };
    inline bool HintFor(int PictureIndex,int Mask,Clue& Out)
    {
        Evaluation Current; if (!Evaluate(PictureIndex,Mask,Current) || Current.Complete) return false;
        int BestMask=-1,BestDistance=RouterCount+1;
        // Small complete state space. Ties keep the first numeric winning mask;
        // a matched-window greedy rule can strand a useful intermediate turn.
        for (int Candidate=0;Candidate<(1<<RouterCount);++Candidate)
        {
            Evaluation View; Evaluate(PictureIndex,Candidate,View); if (!View.Complete) continue;
            int Distance=0; for (int I=0;I<RouterCount;++I) if ((Mask^Candidate)&(1<<I)) ++Distance;
            if (Distance<BestDistance) { BestMask=Candidate; BestDistance=Distance; }
        }
        if (BestMask<0) return false;
        Clue Prepared; Prepared.Remaining=BestDistance;
        for (int I=0;I<RouterCount;++I) if ((Mask^BestMask)&(1<<I))
        { Prepared.RouterIndex=I; Prepared.ToB=(BestMask&(1<<I))!=0; break; }
        Out=Prepared; return true;
    }

    class Session
    {
    public:
        bool Begin()
        {
            *this=Session{};
            for (int I=0;I<PictureCount;++I) Attempts[I].Mask=Pictures[I].StartMask;
            bActive=true; return true;
        }
        bool Active() const { return bActive; }
        int CurrentPicture() const { return Selected; }
        int Mask() const { return Attempts[Selected].Mask; }
        bool SelectPicture(int Index)
        {
            if (!bActive || Index<0 || Index>=PictureCount || Selected==Index) return false;
            Selected=Index; return true;
        }
        bool View(Evaluation& Out) const { return bActive && Evaluate(Selected,Mask(),Out); }
        bool Hint(Clue& Out) const { return bActive && HintFor(Selected,Mask(),Out); }
        std::size_t UndoCount() const { return Attempts[Selected].UndoSize; }
        std::size_t RedoCount() const { return Attempts[Selected].RedoSize; }
        bool EverCompleted(int Index) const
        { return bActive && Index>=0 && Index<PictureCount && Attempts[Index].bEverCompleted; }
        int CompletedCount() const
        { int Count=0; if (bActive) for (const auto& Entry:Attempts) if (Entry.bEverCompleted) ++Count; return Count; }
        bool Toggle(int RouterIndex)
        {
            if (!bActive || RouterIndex<0 || RouterIndex>=RouterCount) return false;
            auto& Entry=Attempts[Selected]; const int Next=Entry.Mask^(1<<RouterIndex);
            Push(Entry.Undo,Entry.UndoSize,Entry.Mask); Entry.Mask=Next; Entry.RedoSize=0;
            Remember(); return true;
        }
        bool Undo()
        {
            if (!bActive) return false; auto& Entry=Attempts[Selected]; if (!Entry.UndoSize) return false;
            Push(Entry.Redo,Entry.RedoSize,Entry.Mask); Entry.Mask=Entry.Undo[--Entry.UndoSize];
            Remember(); return true;
        }
        bool Redo()
        {
            if (!bActive) return false; auto& Entry=Attempts[Selected]; if (!Entry.RedoSize) return false;
            Push(Entry.Undo,Entry.UndoSize,Entry.Mask); Entry.Mask=Entry.Redo[--Entry.RedoSize];
            Remember(); return true;
        }
        /** Caller confirms reset. Only this picture's attempt/history is reset;
         * previous first-completion information and other pictures remain. */
        bool Restart()
        {
            if (!bActive) return false; auto& Entry=Attempts[Selected];
            if (Entry.Mask==Pictures[Selected].StartMask && !Entry.UndoSize && !Entry.RedoSize) return false;
            Entry.Mask=Pictures[Selected].StartMask; Entry.UndoSize=Entry.RedoSize=0;
            return true;
        }
    private:
        struct Attempt
        {
            int Mask=0;
            std::array<std::uint8_t,HistoryLimit> Undo{},Redo{};
            std::size_t UndoSize=0,RedoSize=0;
            bool bEverCompleted=false;
        };
        static void Push(std::array<std::uint8_t,HistoryLimit>& History,std::size_t& Count,int Mask)
        {
            if (Count==History.size())
            { for (std::size_t I=1;I<Count;++I) History[I-1]=History[I]; --Count; }
            History[Count++]=static_cast<std::uint8_t>(Mask);
        }
        void Remember()
        { Evaluation Result; Evaluate(Selected,Mask(),Result); if (Result.Complete) Attempts[Selected].bEverCompleted=true; }
        std::array<Attempt,PictureCount> Attempts{};
        int Selected=0;
        bool bActive=false;
    };
}
