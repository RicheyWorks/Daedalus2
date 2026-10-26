// SPDX-License-Identifier: MIT
#include "../DaedalusLink/Source/DaedalusLink/Public/DaedalusMailRoutePracticeCore.h"
#include <cmath>
#include <cstdint>
#include <iostream>
#include <limits>
#include <vector>

namespace mail=daedalus::parcels;
namespace practice=daedalus::mailpractice;
namespace
{
    int Checks=0,Failures=0;
    void Check(bool Passed,const char* Name)
    { ++Checks; if (!Passed) { ++Failures; std::cerr<<"FAIL: "<<Name<<'\n'; } }
    double East(mail::Stop Stop) { return (static_cast<double>(Stop.X())-48)*100; }
    double North(mail::Stop Stop) { return (static_cast<double>(Stop.Z)+74)*100; }
    bool Same(const mail::Receipt& A,const mail::Receipt& B)
    { return A.Delivered==B.Delivered && A.Late==B.Late && A.Undelivered==B.Undelivered && A.GhostReturned==B.GhostReturned &&
        A.Stamps==B.Stamps && A.Seconds==B.Seconds && A.ParSeconds==B.ParSeconds && A.Award==B.Award; }
    bool Same(const mail::Day& A,const mail::Day& B)
    {
        if (A.Seed!=B.Seed || A.ParOrder!=B.ParOrder || A.ParCubes!=B.ParCubes || A.ParSeconds!=B.ParSeconds || A.Letters.size()!=B.Letters.size()) return false;
        for (std::size_t I=0;I<A.Letters.size();++I)
        {
            const auto& X=A.Letters[I]; const auto& Y=B.Letters[I];
            if (X.Id!=Y.Id || X.Plot!=Y.Plot || !(X.Mailbox==Y.Mailbox) || X.Type!=Y.Type || X.Deadline!=Y.Deadline) return false;
        }
        return true;
    }
    int Next(const mail::Day& Day,const std::vector<bool>& Done)
    { for (int Id:Day.ParOrder) if (!Done[static_cast<std::size_t>(Id)]) return Id; return -1; }
    mail::Outcome Expected(const mail::Letter& Letter,int Seconds)
    { return Letter.Type==mail::Kind::GhostPickup?mail::Outcome::PickedUp:Letter.Type==mail::Kind::Express && Seconds>Letter.Deadline?mail::Outcome::Late:mail::Outcome::OnTime; }
}
int main()
{
    const double NaN=(std::numeric_limits<double>::quiet_NaN)(),Infinity=(std::numeric_limits<double>::infinity)();
    mail::Coord Coord;
    Check(practice::SamplePosition(0,0,0,Coord) && Coord==mail::Coord{48,1,-74} &&
        practice::SamplePosition(-7200,-6200,-25,Coord) && Coord==mail::Coord{-24,1,-136} &&
        practice::SamplePosition(7200,6200,25,Coord) && Coord==mail::Coord{120,1,-12},
        "depot-relative centimetres preserve authored negative street centres and inclusive foot tolerance");
    Check(practice::SamplePosition(-4850,7350,0,Coord) && Coord==mail::Coord{0,1,0} &&
        practice::SamplePosition(-4850.01,7349.99,0,Coord) && Coord==mail::Coord{-1,1,-1} &&
        practice::SamplePosition(49.99,-50.01,0,Coord) && Coord==mail::Coord{48,1,-75},
        "nearest-cell ties use floor plus half, including negative canonical coordinates");
    const mail::Coord Sentinel{123,456,789}; Coord=Sentinel;
    const double MaxEast=(static_cast<double>((std::numeric_limits<int>::max)())-48)*100;
    const double MinEast=(static_cast<double>((std::numeric_limits<int>::min)())-48)*100;
    bool Bounds=practice::SamplePosition(MaxEast,0,0,Coord) && Coord.X==(std::numeric_limits<int>::max)() &&
        practice::SamplePosition(MinEast,0,0,Coord) && Coord.X==(std::numeric_limits<int>::min)(); Coord=Sentinel;
    Bounds=!practice::SamplePosition(MaxEast+100,0,0,Coord) && !practice::SamplePosition(MinEast-100,0,0,Coord) &&
        !practice::SamplePosition(NaN,0,0,Coord) && !practice::SamplePosition(0,Infinity,0,Coord) && !practice::SamplePosition(0,0,NaN,Coord) &&
        !practice::SamplePosition(0,0,25.01,Coord) && !practice::SamplePosition(0,0,-25.01,Coord) && Coord==Sentinel && Bounds;
    Check(Bounds,"nonfinite, wrong-height and unrepresentable positions refuse without changing output");
    int Seconds=-77;
    bool Clock=practice::Elapsed(100,100.999,0,Seconds) && Seconds==0 && practice::Elapsed(100,101,0,Seconds) && Seconds==1 &&
        practice::Elapsed(0,static_cast<double>((std::numeric_limits<int>::max)())+0.75,0,Seconds) && Seconds==(std::numeric_limits<int>::max)(); Seconds=-77;
    Clock=!practice::Elapsed(-1,0,0,Seconds) && !practice::Elapsed(100,99.9,0,Seconds) && !practice::Elapsed(100,100.9,1,Seconds) &&
        !practice::Elapsed(0,1,-1,Seconds) && !practice::Elapsed(0,Infinity,0,Seconds) && !practice::Elapsed(NaN,0,0,Seconds) &&
        !practice::Elapsed(0,static_cast<double>((std::numeric_limits<int>::max)())+1,0,Seconds) && Seconds==-77 && Clock;
    Check(Clock,"elapsed sampling floors before int bounds and preserves output on invalid or decreasing elapsed values");
    practice::Practice Empty; mail::Receipt Kept; Kept.Delivered=-1; Kept.Late=-2; Kept.Undelivered=-3; Kept.GhostReturned=true;
    Kept.Stamps=-4; Kept.Seconds=-5; Kept.ParSeconds=-6; Kept.Award=mail::Medal::Bronze; auto Receipt=Kept;
    Check(!Empty.Active() && Empty.NextLetter()==-1 && Empty.LastStation()==mail::Depot() && Empty.LastElapsed()==0 &&
        Empty.Deliver(0,0,0,0,0)==mail::Outcome::UnknownLetter && Empty.LastError()==practice::Error::Inactive &&
        !Empty.Receipt(0,0,0,0,Receipt) && Same(Receipt,Kept) && !Empty.Begin(7,NaN) && !Empty.Begin(7,-1) && !Empty.Active(),
        "inactive actions and invalid first clocks leave route/output unstarted and station at the depot");
    mail::Day Day; const bool Made=mail::MakeDay(7,Day); practice::Practice Run; mail::Day Invalid;
    const bool Begun=Made && !Run.BeginPrepared(Invalid,100) && Run.BeginPrepared(Day,100);
    practice::Practice Generated; const bool Seeded=Generated.Begin(7,100);
    Check(Begun && Seeded && Same(Run.ReadRoute().CurrentDay(),Day) && Same(Generated.ReadRoute().CurrentDay(),Day) &&
        Run.NextLetter()==Day.ParOrder.front() && Run.LastElapsed()==0 && Run.LastStation()==mail::Depot() &&
        !Run.Begin(99,500) && !Run.BeginPrepared(Run.ReadRoute().CurrentDay(),500) && Run.LastError()==practice::Error::AlreadyStarted &&
        Same(Run.ReadRoute().CurrentDay(),Day) && Run.LastElapsed()==0,
        "prepared and seeded starts reuse one authored day; repeated and aliased starts cannot replace an active route");
    if (!Begun || !Seeded) return 1;
    int Regular=0,Ghost=-1;
    for (const auto& Letter:Day.Letters) if (Letter.Type==mail::Kind::GhostPickup) Ghost=Letter.Id; else ++Regular;
    mail::Receipt First,Repeat;
    Check(Run.Receipt(0,0,0,100.9,First) && First.Delivered==0 && First.Undelivered==Regular && !First.GhostReturned && First.Award==mail::Medal::None &&
        Run.Receipt(0,0,0,100.9,Repeat) && Same(First,Repeat) && Run.Active() && Run.NextLetter()==Day.ParOrder.front() && Run.LastStation()==mail::Depot(),
        "early receipts are repeatable snapshots and do not close, finish or consume the route");
    Receipt=Kept;
    Check(!Run.Receipt(0,0,0,100.8,Receipt) && Run.LastError()==practice::Error::InvalidTime && Same(Receipt,Kept) && Run.LastElapsed()==0 &&
        !Run.Receipt(249,0,0,1000,Receipt) && Run.LastError()==practice::Error::TooFar && Same(Receipt,Kept) &&
        Run.Receipt(0,0,0,100.95,Receipt) && Receipt.Seconds==0 && Run.Receipt(0,0,0,101,Receipt) && Receipt.Seconds==1 && Run.LastStation()==mail::Depot(),
        "same-second raw clock reversal and far-future failed samples cannot advance the accepted clock");
    practice::Practice Radius; Radius.BeginPrepared(Day,0); mail::Session Raw; Raw.Start(Day); mail::Receipt RawReceipt;
    const bool Quantized=practice::SamplePosition(249,0,0,Coord) && Raw.Finish(Coord,0,RawReceipt); Receipt=Kept;
    Check(Quantized && !Radius.Receipt(249,0,0,0.5,Receipt) && Same(Receipt,Kept) && Radius.LastElapsed()==0 &&
        Radius.Receipt(200,0,25,0.5,Receipt) && !Radius.Receipt(200.0001,0,0,0.6,Receipt),
        "continuous200cm receipt radius closes the2.49-cell quantization gap and includes the exact boundary");
    const int FirstId=Day.ParOrder.front(); const auto FirstLetter=Day.Letters[static_cast<std::size_t>(FirstId)];
    practice::Practice Delivery; Delivery.BeginPrepared(Day,100);
    const bool Far=Delivery.Deliver(FirstId,East(FirstLetter.Mailbox),North(FirstLetter.Mailbox)+249,0,1000)==mail::Outcome::TooFar &&
        !Delivery.ReadRoute().IsDone(FirstId) && Delivery.LastElapsed()==0 && Delivery.LastStation()==mail::Depot();
    const bool Bad=Delivery.Deliver(-1,0,0,0,1000)==mail::Outcome::UnknownLetter &&
        Delivery.Deliver(FirstId,NaN,0,0,1000)==mail::Outcome::TooFar && Delivery.LastError()==practice::Error::InvalidPosition &&
        Delivery.Deliver(FirstId,East(FirstLetter.Mailbox),North(FirstLetter.Mailbox),25.01,1000)==mail::Outcome::TooFar &&
        Delivery.Deliver(FirstId,-7000,-7000,0,1000)==mail::Outcome::Trespass;
    const auto Accepted=Delivery.Deliver(FirstId,East(FirstLetter.Mailbox),North(FirstLetter.Mailbox)+200,-25,100.2);
    Receipt=Kept;
    Check(Far && Bad && Accepted==Expected(FirstLetter,0) && Delivery.ReadRoute().IsDone(FirstId) && Delivery.LastStation()==FirstLetter.Mailbox &&
        Delivery.LastElapsed()==0 && Delivery.LastError()==practice::Error::None && Delivery.NextLetter()!=FirstId &&
        Delivery.Deliver(FirstId,0,0,0,9999)==mail::Outcome::AlreadyDone && Delivery.LastElapsed()==0 &&
        !Delivery.Receipt(249,0,0,9999,Receipt) && Same(Receipt,Kept) && Delivery.LastStation()==FirstLetter.Mailbox &&
        Delivery.Receipt(0,0,0,100.3,Receipt) && Delivery.LastStation()==mail::Depot(),
        "delivery refusals retain state; failed receipt keeps mailbox, accepted receipt returns station to depot");
    practice::Practice Walk; Walk.BeginPrepared(Day,500); mail::Session Baseline; Baseline.Start(Day);
    std::vector<bool> Done(Day.Letters.size(),false); mail::Stop At=mail::Depot(),LastDelivered=mail::Depot(); int Cubes=0; bool Route=true;
    for (int Id:Day.ParOrder)
    {
        const auto& Letter=Day.Letters[static_cast<std::size_t>(Id)]; const auto Path=mail::Waypoints(At,Letter.Mailbox);
        Route=!Path.empty() && Path.front()==At.At() && Path.back()==Letter.Mailbox.At() && Route;
        Cubes+=mail::StreetCubes(At,Letter.Mailbox); At=Letter.Mailbox;
        if (Letter.Type==mail::Kind::GhostPickup) continue; // Keep the optional pickup outstanding for the receipt comparison.
        const double Now=500+static_cast<double>(Cubes)/5; const int Elapsed=static_cast<int>(std::floor(Now-500));
        const auto Result=Walk.Deliver(Id,East(At),North(At),0,Now); const auto Original=Baseline.Deliver(Id,At.At(),Elapsed); Done[static_cast<std::size_t>(Id)]=true; LastDelivered=At;
        Route=Result==Original && Result==Expected(Letter,Elapsed) && Walk.NextLetter()==Next(Day,Done) && Walk.LastStation()==LastDelivered && Walk.LastElapsed()==Elapsed && Route;
    }
    Cubes+=mail::StreetCubes(At,mail::Depot()); double Now=500+static_cast<double>(Cubes)/5;
    mail::Receipt Ordinary,OriginalReceipt;
    Route=Walk.Receipt(0,0,0,Now,Ordinary) && Baseline.Finish(mail::Depot().At(),static_cast<int>(std::floor(Now-500)),OriginalReceipt) && Same(Ordinary,OriginalReceipt) &&
        Ordinary.Undelivered==0 && !Ordinary.GhostReturned && Ordinary.Award==mail::Medal::Gold && Walk.Active() && Walk.LastStation()==mail::Depot() && Walk.NextLetter()==Ghost && Route;
    Check(Route,"one actualseed7 par-order street walk preserves core results, next outstanding ID and ordinary-only receipt/medal semantics");
    const int Before=Ordinary.Seconds; Now+=1;
    bool Repeatable=Walk.Receipt(0,0,0,Now,Repeat) && Repeat.Seconds==Before+1 && Repeat.Delivered==Ordinary.Delivered && Walk.Active();
    if (Ghost>=0)
    {
        const auto& Letter=Day.Letters[static_cast<std::size_t>(Ghost)]; Now+=static_cast<double>(mail::StreetCubes(mail::Depot(),Letter.Mailbox))/5;
        Repeatable=Walk.Deliver(Ghost,East(Letter.Mailbox),North(Letter.Mailbox),0,Now)==mail::Outcome::PickedUp && Walk.ReadRoute().HoldingGhost() &&
            Walk.NextLetter()==-1 && Walk.LastStation()==Letter.Mailbox && Repeatable;
        Now+=static_cast<double>(mail::StreetCubes(Letter.Mailbox,mail::Depot()))/5;
        Repeatable=Walk.Receipt(0,0,0,Now,Repeat) && Repeat.GhostReturned && Repeat.Stamps==Ordinary.Stamps+2 && Repeat.Undelivered==0 && Walk.LastStation()==mail::Depot() && Walk.Active() && Repeatable;
    }
    Check(Repeatable,"later receipts advance time without freezing/settling; an optional ghost pickup remains available afterward");
    practice::Practice Limit; Limit.BeginPrepared(Day,0); const double Maximum=(std::numeric_limits<int>::max)(); Receipt=Kept;
    Check(Limit.Receipt(0,0,0,Maximum+0.75,Receipt) && Receipt.Seconds==(std::numeric_limits<int>::max)() &&
        !Limit.Receipt(0,0,0,Maximum+1,Receipt) && Limit.LastElapsed()==(std::numeric_limits<int>::max)() &&
        !Limit.Receipt(0,0,0,Maximum+0.7,Receipt) && Limit.Receipt(0,0,0,Maximum+0.8,Receipt),
        "practice retains raw monotonicity even at the maximum floored elapsed value");
    mail::Day GhostDay,ExpressDay; int GhostSeed=-1,ExpressSeed=-1,GhostId=-1,ExpressId=-1; bool Fixtures=true;
    for (int Seed=0;Seed<8 && (GhostSeed<0 || ExpressSeed<0);++Seed)
    {
        mail::Day Fixture; if (!mail::MakeDay(Seed,Fixture)) { Fixtures=false; break; }
        for (const auto& Letter:Fixture.Letters)
        {
            if (GhostSeed<0 && Letter.Type==mail::Kind::GhostPickup) { GhostDay=Fixture; GhostSeed=Seed; GhostId=Letter.Id; }
            if (ExpressSeed<0 && Letter.Type==mail::Kind::Express) { ExpressDay=Fixture; ExpressSeed=Seed; ExpressId=Letter.Id; }
        }
    }
    bool GhostPath=Fixtures && GhostSeed>=0;
    if (GhostPath)
    {
        practice::Practice Pickup; const auto& Letter=GhostDay.Letters[static_cast<std::size_t>(GhostId)];
        mail::Receipt BeforePickup,Collected,Again; std::vector<bool> GhostDone(GhostDay.Letters.size(),false); GhostDone[static_cast<std::size_t>(GhostId)]=true;
        GhostPath=Pickup.BeginPrepared(GhostDay,1000) && Pickup.Receipt(0,0,0,1000,BeforePickup) && BeforePickup.Stamps==0 &&
            BeforePickup.Undelivered==static_cast<int>(GhostDay.Letters.size())-1 &&
            Pickup.Deliver(GhostId,East(Letter.Mailbox),North(Letter.Mailbox),0,1000.25)==mail::Outcome::PickedUp &&
            Pickup.ReadRoute().HoldingGhost() && Pickup.LastStation()==Letter.Mailbox && Pickup.NextLetter()==Next(GhostDay,GhostDone) &&
            Pickup.Receipt(0,0,0,1000.5,Collected) && Collected.GhostReturned && Collected.Stamps==BeforePickup.Stamps+2 &&
            Collected.Delivered==0 && Collected.Undelivered==BeforePickup.Undelivered && Collected.Award==mail::Medal::None && Pickup.LastStation()==mail::Depot() &&
            Pickup.Deliver(GhostId,East(Letter.Mailbox),North(Letter.Mailbox),0,9999)==mail::Outcome::AlreadyDone &&
            Pickup.Receipt(0,0,0,1000.75,Again) && Same(Collected,Again) && Again.Stamps==2 && Pickup.ReadRoute().HoldingGhost() &&
            Pickup.Active() && Pickup.LastElapsed()==0 && Pickup.LastStation()==mail::Depot();
    }
    Check(GhostPath,"bounded actual ghost fixture preserves pickup, repeated plus2 receipt facts, active route and depot navigation without settlement");
    bool ExpressPath=Fixtures && ExpressSeed>=0;
    if (ExpressPath)
    {
        const auto& Letter=ExpressDay.Letters[static_cast<std::size_t>(ExpressId)]; practice::Practice AtDeadline,AfterDeadline;
        mail::Receipt OnTime,Late;
        ExpressPath=Letter.Deadline>0 && AtDeadline.BeginPrepared(ExpressDay,2000) && AfterDeadline.BeginPrepared(ExpressDay,2000) &&
            AtDeadline.Deliver(ExpressId,East(Letter.Mailbox),North(Letter.Mailbox),0,2000+Letter.Deadline)==mail::Outcome::OnTime &&
            AfterDeadline.Deliver(ExpressId,East(Letter.Mailbox),North(Letter.Mailbox),0,2001+Letter.Deadline)==mail::Outcome::Late &&
            AtDeadline.LastElapsed()==Letter.Deadline && AfterDeadline.LastElapsed()==Letter.Deadline+1 &&
            AtDeadline.Receipt(0,0,0,2000+Letter.Deadline,OnTime) && AfterDeadline.Receipt(0,0,0,2001+Letter.Deadline,Late) &&
            OnTime.Delivered==1 && OnTime.Late==0 && OnTime.Stamps==2 && Late.Delivered==1 && Late.Late==1 && Late.Stamps==1 &&
            AtDeadline.Active() && AfterDeadline.Active() && AtDeadline.LastStation()==mail::Depot() && AfterDeadline.LastStation()==mail::Depot();
    }
    Check(ExpressPath,"distinct actual express practice attempts are on-time at deadline equality and late one elapsed second afterward");
    std::cout<<Checks<<" checks, "<<Failures<<" failed;seed7 walk;ghost fixture seed "<<GhostSeed<<";express fixture seed "<<ExpressSeed<<";no native movement/authority proof\n";
    return Failures?1:0;
}
