// SPDX-License-Identifier: MIT
#include "DaedalusMailRouteSession.h"
#include "DaedalusMailRouteBoard.h"
#include "GameFramework/Actor.h"
#include <limits>

namespace DaedalusMailLocal
{
    bool Identity(const FString& Value)
    {
        if (Value.IsEmpty() || Value.Len()>128 || Value.TrimStartAndEnd()!=Value) return false;
        for (TCHAR C:Value) if (C<32 || C==127) return false;
        return true;
    }
    bool WithinReach(const FIntVector& A,const FIntVector& B)
    {
        const double X=static_cast<double>(A.X)-B.X, Z=static_cast<double>(A.Z)-B.Z;
        return X*X+Z*Z<=daedalus::parcels::Reach*daedalus::parcels::Reach;
    }
    FString OutcomeText(daedalus::parcels::Outcome Value)
    {
        using daedalus::parcels::Outcome;
        switch (Value)
        {
        case Outcome::OnTime: return TEXT("Delivered on time.");
        case Outcome::Late: return TEXT("Delivered late. Other letters can still be delivered.");
        case Outcome::PickedUp: return TEXT("Ghost letter collected. Carry it back to the helipad.");
        case Outcome::UnknownLetter: return TEXT("That letter is not in this route.");
        case Outcome::AlreadyDone: return TEXT("This letter is already done.");
        case Outcome::TooFar: return TEXT("Move within two cubes of the mailbox on the street.");
        case Outcome::Trespass: return TEXT("Deliver from the street, outside every plot.");
        case Outcome::NotHolding: return TEXT("There is no Ghost letter to return.");
        }
        return TEXT("This letter is unavailable.");
    }
    FString MedalText(daedalus::parcels::Medal Value)
    {
        using daedalus::parcels::Medal;
        switch (Value)
        {
        case Medal::Gold: return TEXT("Gold");
        case Medal::Silver: return TEXT("Silver");
        case Medal::Bronze: return TEXT("Bronze");
        case Medal::None: return TEXT("None");
        }
        return TEXT("None");
    }
}

UDaedalusMailRouteSession::UDaedalusMailRouteSession()
{
    PrimaryComponentTick.bCanEverTick=false;
}

bool UDaedalusMailRouteSession::CanHost() const
{
    const AActor* Actor=GetOwner();
    return IsInGameThread() && !bEnding && HasBegunPlay() && IsValid(Actor) && Actor->HasActorBegunPlay() && !Actor->IsActorBeingDestroyed() &&
        Actor->HasAuthority() && GetWorld()!=nullptr;
}

bool UDaedalusMailRouteSession::HasHostBinding() const
{
    const UObject* Adapter=Host.Get();
    if (!CanHost() || !bConfigured || !IsValid(Adapter) || Adapter->GetWorld()!=GetWorld() ||
        !CourierActor.IsValid() || CourierActor.Get()!=GetOwner() || !OnActionRequested.IsBound()) return false;
    if (const auto* Actor=Cast<AActor>(Adapter))
        if (Actor->IsActorBeingDestroyed() || !Actor->HasActorBegunPlay()) return false;
    if (const auto* Component=Cast<UActorComponent>(Adapter))
        if (!Component->HasBegunPlay() || !IsValid(Component->GetOwner()) || Component->GetOwner()->IsActorBeingDestroyed()) return false;
    return true;
}

bool UDaedalusMailRouteSession::IsCourier(const AActor* Courier) const
{
    return HasHostBinding() && IsValid(Courier) && !Courier->IsActorBeingDestroyed() &&
        Courier==CourierActor.Get() && Courier->GetWorld()==GetWorld();
}

bool UDaedalusMailRouteSession::ConfigureHost(UObject* HostAdapter,const FString& CourierIdentity,
    const FString& SessionIdentity,const FString& DistrictIdentity,int64 DaySeed)
{
    if (!CanHost() || !IsValid(HostAdapter) || HostAdapter->GetWorld()!=GetWorld() ||
        !DaedalusMailLocal::Identity(CourierIdentity) || !DaedalusMailLocal::Identity(SessionIdentity) ||
        !DaedalusMailLocal::Identity(DistrictIdentity)) return false;
    if (Route.Active() && (CourierIdentity!=CourierKey || SessionIdentity!=SessionKey ||
        DistrictIdentity!=DistrictKey || DaySeed!=Seed)) return false;
    ++BindingRevision;
    ForgetPending();
    Host=HostAdapter; CourierActor=GetOwner();
    CourierKey=CourierIdentity; SessionKey=SessionIdentity; DistrictKey=DistrictIdentity; Seed=DaySeed;
    bConfigured=true;
    Notice=TEXT("Host binding supplied. The host must validate each action.");
    Changed();
    return true;
}

void UDaedalusMailRouteSession::ClearHostBinding()
{
    if (!CanHost()) return;
    ++BindingRevision;
    ForgetPending(); Host.Reset(); bConfigured=false;
    Notice=TEXT("Host disconnected. Route progress is retained in memory.");
    Changed();
}

void UDaedalusMailRouteSession::ForgetPending()
{
    PendingTicket=0; PendingStation.Reset(); PendingLetter=-1; PendingPlot=-1;
}

void UDaedalusMailRouteSession::CancelStationRequest(ADaedalusMailRouteBoard* Station)
{
    if (!CanHost() || PendingTicket==0 || PendingStation.Get()!=Station) return;
    ForgetPending();
    Notice=TEXT("The station changed or closed. Route progress is unchanged.");
    Changed();
}

bool UDaedalusMailRouteSession::CancelPendingRequest()
{
    if (!CanHost() || PendingTicket==0) return false;
    ForgetPending();
    Notice=TEXT("Mail check canceled. Use the station again to retry.");
    Changed();
    return true;
}

void UDaedalusMailRouteSession::Changed() { if (!bEnding) OnChanged.Broadcast(this); }

int32 UDaedalusMailRouteSession::LetterForPlot(int32 Plot) const
{
    if (Route.Active())
        for (const auto& Letter:Route.CurrentDay().Letters) if (Letter.Plot==Plot) return Letter.Id;
    return -1;
}

bool UDaedalusMailRouteSession::RequestAction(AActor* Courier,ADaedalusMailRouteBoard* Station)
{
    if (!IsCourier(Courier) || !IsValid(Station) || !Station->IsStationActive() ||
        Station->GetWorld()!=GetWorld() || Station->GetRouteSession()!=this) return false;
    if (PendingTicket!=0) return CancelPendingRequest();
    FIntVector StationCube;
    if (!Station->ExpectedStationCube(StationCube)) return false;
    const int32 Plot=Station->GetPlotNumber();
    EDaedalusMailRouteAction Action=EDaedalusMailRouteAction::Start;
    const int32 LetterId=LetterForPlot(Plot);
    if (Plot==-1) Action=Route.Active()?EDaedalusMailRouteAction::Receipt:EDaedalusMailRouteAction::Start;
    else
    {
        if (!Route.Active() || LetterId<0) return false;
        if (Route.IsDone(LetterId)) { Notice=TEXT("This letter is already done."); Changed(); return false; }
        Action=EDaedalusMailRouteAction::Deliver;
    }
    // Never recycle a ticket, including across rebind/cancel/clear.
    if (NextTicket==(std::numeric_limits<int64>::max)()) return false;
    PendingTicket=++NextTicket;
    PendingStation=Station; PendingAction=Action; PendingLetter=LetterId; PendingPlot=Plot;
    PendingRevision=BindingRevision;
    Notice=TEXT("Waiting for the host check. Use again to cancel.");
    const int64 Ticket=PendingTicket;
    // The adapter may complete synchronously. Do not overwrite its result afterward.
    OnActionRequested.Broadcast(this,Ticket,Station,Action,LetterId);
    Changed();
    return true;
}

bool UDaedalusMailRouteSession::MatchingTicket(UObject* HostAdapter,int64 Ticket) const
{
    return HasHostBinding() && IsValid(HostAdapter) && HostAdapter==Host.Get() && Ticket>0 &&
        Ticket==PendingTicket && PendingRevision==BindingRevision;
}

bool UDaedalusMailRouteSession::RejectHostAction(UObject* HostAdapter,int64 Ticket)
{
    if (!MatchingTicket(HostAdapter,Ticket)) return false;
    ForgetPending();
    Notice=TEXT("The host could not validate this action. Route progress is unchanged.");
    Changed();
    return true;
}

bool UDaedalusMailRouteSession::CompleteHostAction(UObject* HostAdapter,int64 Ticket,
    const FDaedalusMailRouteObservation& Observation)
{
    if (!MatchingTicket(HostAdapter,Ticket) || Observation.CourierIdentity!=CourierKey ||
        Observation.SessionIdentity!=SessionKey || Observation.DistrictIdentity!=DistrictKey ||
        Observation.DaySeed!=Seed) return false;
    auto* Station=PendingStation.Get();
    FIntVector ExpectedCube;
    const EDaedalusMailRouteAction Action=PendingAction;
    const int32 LetterId=PendingLetter;
    const bool StationMatches=IsValid(Station) && Station->IsStationActive() &&
        Station->GetWorld()==GetWorld() && Station->GetRouteSession()==this && Station->GetPlotNumber()==PendingPlot &&
        Station->ExpectedStationCube(ExpectedCube) && ExpectedCube==Observation.StationCube;
    // Consume before core changes or callbacks, including a refused host sample.
    ForgetPending();
    if (!StationMatches || Observation.ElapsedSeconds<0 || Observation.ElapsedSeconds<LastElapsed)
    {
        Notice=TEXT("The host sample did not match this station or round. Progress is unchanged.");
        Changed(); return false;
    }
    const daedalus::parcels::Coord Position{Observation.CourierCube.X,Observation.CourierCube.Y,Observation.CourierCube.Z};
    if (Action==EDaedalusMailRouteAction::Start)
    {
        if (Route.Active() || !DaedalusMailLocal::WithinReach(Observation.CourierCube,ExpectedCube))
        { Notice=TEXT("Start at the helipad, within two cubes of the board."); Changed(); return false; }
        daedalus::parcels::Day Day;
        if (!daedalus::parcels::MakeDay(Seed,Day) || !Route.Start(Day))
        { Notice=TEXT("The route could not be prepared. Try again."); Changed(); return false; }
        Receipt={};
        Notice=TEXT("Satchel ready. Follow the numbered street tour and return to the helipad.");
    }
    else if (Action==EDaedalusMailRouteAction::Deliver)
    {
        if (!Route.Active() || LetterForPlot(Station->GetPlotNumber())!=LetterId) return false;
        const auto Result=Route.Deliver(LetterId,Position,Observation.ElapsedSeconds);
        Notice=DaedalusMailLocal::OutcomeText(Result);
        if (Result==daedalus::parcels::Outcome::OnTime || Result==daedalus::parcels::Outcome::Late ||
            Result==daedalus::parcels::Outcome::PickedUp) Receipt={};
    }
    else
    {
        daedalus::parcels::Receipt Sample;
        if (!Route.Active() || !Route.Finish(Position,Observation.ElapsedSeconds,Sample))
        { Notice=TEXT("Return within two cubes of the helipad to view the receipt."); Changed(); return false; }
        Receipt.bAvailable=true; Receipt.bPendingSettlement=true;
        Receipt.Delivered=Sample.Delivered; Receipt.Late=Sample.Late; Receipt.Undelivered=Sample.Undelivered;
        Receipt.bGhostReturned=Sample.GhostReturned; Receipt.Stamps=Sample.Stamps;
        Receipt.Seconds=Sample.Seconds; Receipt.ParSeconds=Sample.ParSeconds;
        Receipt.Medal=DaedalusMailLocal::MedalText(Sample.Award);
        Notice=TEXT("Receipt pending settlement. No rewards issued; the round remains open.");
    }
    LastElapsed=Observation.ElapsedSeconds;
    Changed();
    return true;
}

FString UDaedalusMailRouteSession::StationPrompt(const AActor* Courier,int32 Plot) const
{
    if (!IsCourier(Courier)) return TEXT("Mail route unavailable");
    if (PendingTicket!=0) return TEXT("Cancel pending mail check");
    if (Plot==-1) return Route.Active()?TEXT("View pending route receipt"):TEXT("Request mail route");
    daedalus::parcels::Stop Stop;
    if (!daedalus::parcels::Mailbox(Plot,Stop)) return TEXT("Mailbox unavailable");
    if (!Route.Active()) return TEXT("Start the route at the helipad");
    const int32 Id=LetterForPlot(Plot);
    if (Id<0) return TEXT("No letter for this mailbox");
    if (Route.IsDone(Id)) return TEXT("Letter already done");
    return Route.CurrentDay().Letters[static_cast<size_t>(Id)].Type==daedalus::parcels::Kind::GhostPickup?
        TEXT("Request Ghost letter pickup"):TEXT("Request letter delivery");
}

FString UDaedalusMailRouteSession::RouteStatus() const
{
    if (!HasHostBinding()) return TEXT("Mail route inactive\nHost identity, scene and clock bindings required.");
    FString Text=TEXT("Mail route / host-fed prototype\n");
    if (Route.Active())
    {
        int32 Done=0;
        for (const auto& Letter:Route.CurrentDay().Letters) if (Route.IsDone(Letter.Id)) ++Done;
        Text+=FString::Printf(TEXT("Stops %d/%d  /  Par %ds\nHost sample: %ds elapsed\n"),Done,
            static_cast<int32>(Route.CurrentDay().Letters.size()),Route.CurrentDay().ParSeconds,FMath::Max(0,LastElapsed));
        if (Route.HoldingGhost()) Text+=TEXT("Ghost letter in satchel: return to helipad.\n");
    }
    Text+=Notice;
    return Text;
}

FString UDaedalusMailRouteSession::StationText(int32 Plot) const
{
    if (!HasHostBinding()) return RouteStatus();
    FString Text=Plot==-1?TEXT("Postmaster's delivery board\n"):FString::Printf(TEXT("Mailbox / Plot %d\n"),Plot);
    Text+=RouteStatus();
    if (!Route.Active()) return Text;
    const auto& Day=Route.CurrentDay();
    if (Plot==-1)
    {
        Text+=TEXT("\nStreet tour: H");
        for (int32 Id:Day.ParOrder) Text+=FString::Printf(TEXT(" > %d"),Id+1);
        Text+=TEXT(" > H\n");
        for (const auto& Letter:Day.Letters)
        {
            const TCHAR* Kind=Letter.Type==daedalus::parcels::Kind::GhostPickup?TEXT("Ghost pickup"):
                (Letter.Type==daedalus::parcels::Kind::Express?TEXT("Express"):TEXT("Letter"));
            Text+=FString::Printf(TEXT("%d: Plot %d / %s%s"),Letter.Id+1,Letter.Plot,Kind,Route.IsDone(Letter.Id)?TEXT(" / done"):TEXT(""));
            if (Letter.Type==daedalus::parcels::Kind::Express) Text+=FString::Printf(TEXT(" / due %ds"),Letter.Deadline);
            Text+=TEXT("\n");
        }
        if (Receipt.bAvailable)
            Text+=FString::Printf(TEXT("Receipt at %ds: %d delivered, %d late, %d left\nGhost returned: %s / %d stamps / %s\nPENDING SETTLEMENT / no rewards issued"),
                Receipt.Seconds,Receipt.Delivered,Receipt.Late,Receipt.Undelivered,Receipt.bGhostReturned?TEXT("yes"):TEXT("no"),Receipt.Stamps,*Receipt.Medal);
    }
    else
    {
        const int32 Id=LetterForPlot(Plot);
        if (Id<0) Text+=TEXT("\nNo letter for this mailbox today.");
        else
        {
            const auto& Letter=Day.Letters[static_cast<size_t>(Id)];
            Text+=FString::Printf(TEXT("\nTour stop %d / %s"),Id+1,Letter.Type==daedalus::parcels::Kind::GhostPickup?TEXT("Ghost pickup"):TEXT("Delivery"));
            if (Letter.Type==daedalus::parcels::Kind::Express) Text+=FString::Printf(TEXT(" / Express due %ds"),Letter.Deadline);
            if (Route.IsDone(Id)) Text+=TEXT("\n")+DaedalusMailLocal::OutcomeText(Route.Result(Id));
        }
    }
    return Text;
}

void UDaedalusMailRouteSession::BeginPlay()
{
    bEnding=false;
    Super::BeginPlay();
}

void UDaedalusMailRouteSession::EndPlay(const EEndPlayReason::Type Reason)
{
    bEnding=true; ++BindingRevision; bConfigured=false; Host.Reset(); CourierActor.Reset(); ForgetPending();
    Super::EndPlay(Reason);
}
