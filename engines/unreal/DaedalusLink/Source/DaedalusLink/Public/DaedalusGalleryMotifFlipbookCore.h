// SPDX-License-Identifier: MIT
#pragma once
#include "DaedalusGalleryMotifCore.h"
#include <array>
#include <cmath>
#include <utility>

// Frozen actor-life playback of existing local motif documents. Metadata is
// copied without new IDs, lineage rules, file access, profiles or saved state.
namespace daedalus::flipbook
{
    class Player
    {
    public:
        bool Capture(const std::array<motif::Document,4>& Documents,int CountToUse)
        {
            if (bActive || CountToUse<2 || CountToUse>4) return false;
            std::array<motif::Document,4> Prepared{};
            for (int I=0;I<CountToUse;++I)
            {
                const auto& Document=Documents[I];
                if (Document.Id.empty() || motif::CanonicalId(Document.Id)!=Document.Id ||
                    (!Document.Parent.empty() && motif::CanonicalId(Document.Parent)!=Document.Parent)) return false;
                const auto Encoded=motif::EncodeDocument(Document); motif::Document Decoded;
                if (Encoded.empty() || !motif::DecodeDocument(Encoded,Decoded) || Decoded.Id!=Document.Id || Decoded.Parent!=Document.Parent || Decoded.Pixels!=Document.Pixels) return false;
                for (int Previous=0;Previous<I;++Previous) if (Documents[Previous].Id==Document.Id) return false;
                Prepared[I]=Document;
            }
            Frames=std::move(Prepared); FrameCount=CountToUse; Current=0; Rate=2; Facing=1; Phase=0; bPlaying=false; bActive=true; return true;
        }
        bool Active() const { return bActive; }
        int Count() const { return FrameCount; }
        int Index() const { return bActive?Current:-1; }
        const motif::Document* Frame(int IndexToRead) const
        { return bActive && IndexToRead>=0 && IndexToRead<FrameCount?&Frames[IndexToRead]:nullptr; }
        bool Playing() const { return bActive && bPlaying; }
        int Fps() const { return Rate; }
        int Direction() const { return Facing; }
        bool TogglePlay()
        { if (!bActive) return false; bPlaying=!bPlaying; Phase=0; return true; }
        bool Step(int StepDirection)
        {
            if (!bActive || (StepDirection!=1 && StepDirection!=-1)) return false;
            Current=(Current+StepDirection+FrameCount)%FrameCount; bPlaying=false; Phase=0; return true;
        }
        bool Reverse()
        { if (!bActive) return false; Facing=-Facing; Phase=0; return true; }
        bool CycleSpeed()
        { if (!bActive) return false; Rate=Rate==2?4:2; Phase=0; return true; }
        bool FirstFrame()
        { if (!bActive) return false; Current=0; bPlaying=false; Phase=0; return true; }
        bool Advance(double DeltaSeconds)
        {
            if (!bActive || !std::isfinite(DeltaSeconds) || DeltaSeconds<0 || !bPlaying) return false;
            // Reduce seconds before multiplying by FPS: even DBL_MAX stays
            // bounded, with no per-frame loop or intermediate-frame events.
            const double CycleSeconds=static_cast<double>(FrameCount)/Rate;
            const double FramesPassed=Phase+std::fmod(DeltaSeconds,CycleSeconds)*Rate;
            const int Whole=static_cast<int>(std::floor(FramesPassed));
            Phase=FramesPassed-Whole;
            const int Previous=Current,Steps=Whole%FrameCount;
            Current=(Current+Facing*Steps+FrameCount)%FrameCount;
            return Current!=Previous;
        }
    private:
        std::array<motif::Document,4> Frames{};
        int FrameCount=0,Current=0,Rate=2,Facing=1;
        double Phase=0; // Fraction of one frame, always in [0,1).
        bool bActive=false,bPlaying=false;
    };
}
