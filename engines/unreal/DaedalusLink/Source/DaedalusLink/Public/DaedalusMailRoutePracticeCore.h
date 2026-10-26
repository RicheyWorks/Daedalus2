// SPDX-License-Identifier: MIT
#pragma once
#include "DaedalusMailRouteCore.h"
#include <cmath>
#include <cstdint>
#include <limits>
#include <utility>

// Standalone practice adapter only. The native caller supplies actual grounded
// local-player feet relative to a frozen depot frame and game time. No courier
// identity, canonical position validation, settlement or persistence is added.
namespace daedalus::mailpractice
{
    inline constexpr double CentimetresPerCube=100.0,FootTolerance=25.0,ReachCentimetres=200.0;
    enum class Error { None,Inactive,AlreadyStarted,InvalidPosition,InvalidTime,TooFar,CoreRefused };
    inline bool SamplePosition(double EastCm,double NorthCm,double FeetHeightCm,parcels::Coord& Out)
    {
        if (!std::isfinite(EastCm) || !std::isfinite(NorthCm) || !std::isfinite(FeetHeightCm) || std::abs(FeetHeightCm)>FootTolerance) return false;
        const auto Depot=parcels::Depot().At();
        const double X=std::floor(EastCm/CentimetresPerCube+Depot.X+0.5);
        const double Y=std::floor(FeetHeightCm/CentimetresPerCube+1.0+0.5);
        const double Z=std::floor(NorthCm/CentimetresPerCube+Depot.Z+0.5);
        const double Low=(std::numeric_limits<int>::min)(),High=(std::numeric_limits<int>::max)();
        if (!std::isfinite(X) || !std::isfinite(Y) || !std::isfinite(Z) || X<Low || X>High || Y<Low || Y>High || Z<Low || Z>High) return false;
        const parcels::Coord Prepared{static_cast<int>(X),static_cast<int>(Y),static_cast<int>(Z)}; Out=Prepared; return true;
    }
    // The helper compares floored elapsed values. Practice additionally retains
    // raw accepted time, so a .9 -> .8 reversal cannot hide inside one second.
    inline bool Elapsed(double Start,double Now,int Previous,int& Out)
    {
        if (!std::isfinite(Start) || !std::isfinite(Now) || Start<0 || Now<Start || Previous<0) return false;
        const double Difference=Now-Start; if (!std::isfinite(Difference)) return false;
        const double Whole=std::floor(Difference);
        if (Whole<Previous || Whole>(std::numeric_limits<int>::max)()) return false;
        Out=static_cast<int>(Whole); return true;
    }
    class Practice
    {
    public:
        bool Begin(std::int64_t Seed,double Now)
        {
            if (Active()) { Diagnostic=Error::AlreadyStarted; return false; }
            if (!std::isfinite(Now) || Now<0) { Diagnostic=Error::InvalidTime; return false; }
            parcels::Day Day;
            if (!parcels::MakeDay(Seed,Day)) { Diagnostic=Error::CoreRefused; return false; }
            return BeginPrepared(Day,Now);
        }
        bool BeginPrepared(const parcels::Day& Day,double Now)
        {
            if (Active()) { Diagnostic=Error::AlreadyStarted; return false; }
            if (!std::isfinite(Now) || Now<0) { Diagnostic=Error::InvalidTime; return false; }
            parcels::Session Prepared;
            if (!Prepared.Start(Day)) { Diagnostic=Error::CoreRefused; return false; }
            Route=std::move(Prepared); StartedAt=AcceptedAt=Now; AcceptedElapsed=0; Station=parcels::Depot(); Diagnostic=Error::None; return true;
        }
        bool Active() const { return Route.Active(); }
        const parcels::Session& ReadRoute() const { return Route; }
        int LastElapsed() const { return AcceptedElapsed; }
        parcels::Stop LastStation() const { return Station; }
        Error LastError() const { return Diagnostic; }
        int NextLetter() const
        {
            if (!Active()) return -1;
            for (int Id:Route.CurrentDay().ParOrder) if (!Route.IsDone(Id)) return Id;
            return -1;
        }
        parcels::Outcome Deliver(int Id,double EastCm,double NorthCm,double FeetHeightCm,double Now)
        {
            if (!Active()) { Diagnostic=Error::Inactive; return parcels::Outcome::UnknownLetter; }
            int Seconds=0;
            if (!SampleClock(Now,Seconds)) { Diagnostic=Error::InvalidTime; return parcels::Outcome::UnknownLetter; }
            if (Id<0 || static_cast<std::size_t>(Id)>=Route.CurrentDay().Letters.size())
            { Diagnostic=Error::CoreRefused; return parcels::Outcome::UnknownLetter; }
            if (Route.IsDone(Id)) { Diagnostic=Error::CoreRefused; return parcels::Outcome::AlreadyDone; }
            parcels::Coord Courier;
            if (!SamplePosition(EastCm,NorthCm,FeetHeightCm,Courier)) { Diagnostic=Error::InvalidPosition; return parcels::Outcome::TooFar; }
            // Preserve the existing plot refusal before considering distance.
            if (parcels::Trespass(Courier.X,Courier.Z)) { Diagnostic=Error::CoreRefused; return parcels::Outcome::Trespass; }
            const auto& Letter=Route.CurrentDay().Letters[static_cast<std::size_t>(Id)];
            if (!WithinReach(EastCm,NorthCm,Letter.Mailbox)) { Diagnostic=Error::TooFar; return parcels::Outcome::TooFar; }
            const auto Result=Route.Deliver(Id,Courier,Seconds);
            if (Result==parcels::Outcome::OnTime || Result==parcels::Outcome::Late || Result==parcels::Outcome::PickedUp)
            { AcceptClock(Now,Seconds); Station=Letter.Mailbox; Diagnostic=Error::None; }
            else Diagnostic=Error::CoreRefused;
            return Result;
        }
        bool Receipt(double EastCm,double NorthCm,double FeetHeightCm,double Now,parcels::Receipt& Out)
        {
            if (!Active()) { Diagnostic=Error::Inactive; return false; }
            int Seconds=0;
            if (!SampleClock(Now,Seconds)) { Diagnostic=Error::InvalidTime; return false; }
            parcels::Coord Courier;
            if (!SamplePosition(EastCm,NorthCm,FeetHeightCm,Courier)) { Diagnostic=Error::InvalidPosition; return false; }
            if (!WithinReach(EastCm,NorthCm,parcels::Depot())) { Diagnostic=Error::TooFar; return false; }
            parcels::Receipt Prepared;
            if (!Route.Finish(Courier,Seconds,Prepared)) { Diagnostic=Error::CoreRefused; return false; }
            AcceptClock(Now,Seconds); Station=parcels::Depot(); Diagnostic=Error::None; Out=Prepared; return true;
        }
    private:
        parcels::Session Route;
        double StartedAt=0,AcceptedAt=0;
        int AcceptedElapsed=0;
        parcels::Stop Station=parcels::Depot();
        Error Diagnostic=Error::None; // Diagnostic changes never commit a sample.
        bool SampleClock(double Now,int& Seconds) const
        { return std::isfinite(Now) && Now>=AcceptedAt && Elapsed(StartedAt,Now,AcceptedElapsed,Seconds); }
        static bool WithinReach(double EastCm,double NorthCm,parcels::Stop Target)
        {
            const auto Depot=parcels::Depot().At();
            const double East=(static_cast<double>(Target.X())-Depot.X)*CentimetresPerCube;
            const double North=(static_cast<double>(Target.Z)-Depot.Z)*CentimetresPerCube;
            return std::hypot(EastCm-East,NorthCm-North)<=ReachCentimetres;
        }
        void AcceptClock(double Now,int Seconds) { AcceptedAt=Now; AcceptedElapsed=Seconds; }
    };
}
