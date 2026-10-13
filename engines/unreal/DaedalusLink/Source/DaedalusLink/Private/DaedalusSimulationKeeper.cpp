// SPDX-License-Identifier: MIT
#include "DaedalusSimulationKeeper.h"

#include "Components/PrimitiveComponent.h"
#include "Engine/World.h"
#include "GameFramework/Actor.h"
#include "GenericPlatform/GenericPlatformHttp.h"
#include "HAL/PlatformTime.h"
#include "HttpModule.h"
#include "Interfaces/IHttpRequest.h"
#include "Interfaces/IHttpResponse.h"
#include "Net/UnrealNetwork.h"

namespace {
// HTTP's stream callback runs on its worker. Only completion reads these bytes, after HTTP has finished writing.
class FKeeperResponse final : public FArchive {
public:
    static constexpr int64 Limit = 65536;
    std::string Bytes;
    virtual void Serialize(void* Data, int64 Num) override {
        if (IsError()) return;
        if (Num < 0 || Num > Limit - static_cast<int64>(Bytes.size())) { SetError(); return; }
        if (Num > 0) Bytes.append(static_cast<const char*>(Data), static_cast<size_t>(Num));
    }
};
}

UDaedalusSimulationKeeper::UDaedalusSimulationKeeper() {
    PrimaryComponentTick.bCanEverTick = true;
    SetIsReplicatedByDefault(true);
}

bool UDaedalusSimulationKeeper::CanRun() const {
    return IsInGameThread() && IsValid(GetOwner()) && GetOwner()->HasAuthority()
        && GetWorld() && GetWorld()->IsGameWorld() && GetWorld()->GetNetMode() != NM_Client;
}

bool UDaedalusSimulationKeeper::Start(const FString& ServerUrl, const FString& WorldId, const FString& Authorization) {
    if (!CanRun() || !daedalus::simulation::wire_detail::Identity(TCHAR_TO_UTF8(*BoundNpcId))
        || !daedalus::simulation::wire_detail::Identity(TCHAR_TO_UTF8(*WorldId))
        || !(ServerUrl.StartsWith(TEXT("http://")) || ServerUrl.StartsWith(TEXT("https://")))) return false;
    Stop();
    FString Base = ServerUrl;
    Base.RemoveFromEnd(TEXT("/"));
    Url = Base + TEXT("/api/v1/world/") + FGenericPlatformHttp::UrlEncode(WorldId) + TEXT("/simulation/v1");
    Auth = Authorization;
    Session = Mailbox.Begin(TCHAR_TO_UTF8(*WorldId), TCHAR_TO_UTF8(*BoundNpcId));
    bRunning = Session != 0;
    NextPoll = 0;
    View = FDaedalusKeeperView();
    return bRunning;
}

void UDaedalusSimulationKeeper::Stop() {
    if (!IsInGameThread()) return;
    bRunning = false;
    Session = 0; // Fence cancellation completions before touching the request.
    if (Request.IsValid()) { Request->OnProcessRequestComplete().Unbind(); Request->CancelRequest(); Request.Reset(); }
    Auth.Empty(); Url.Empty(); View.bFresh = false;
}

void UDaedalusSimulationKeeper::EndPlay(const EEndPlayReason::Type Reason) {
    Stop();
    Super::EndPlay(Reason);
}

void UDaedalusSimulationKeeper::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& Out) const {
    Super::GetLifetimeReplicatedProps(Out);
    DOREPLIFETIME(UDaedalusSimulationKeeper, View);
}

void UDaedalusSimulationKeeper::Poll() {
    if (!CanRun() || !bRunning || Request.IsValid() || Mailbox.NeedsReconcile()) return;
    Request = FHttpModule::Get().CreateRequest();
    Request->SetURL(Url);
    Request->SetVerb(TEXT("GET"));
    Request->SetHeader(TEXT("Accept"), TEXT("application/json"));
    if (!Auth.IsEmpty()) Request->SetHeader(TEXT("Authorization"), Auth);
    Request->SetTimeout(3.f);
    Request->SetDelegateThreadPolicy(EHttpRequestDelegateThreadPolicy::CompleteOnGameThread);
    TSharedRef<FKeeperResponse> Body = MakeShared<FKeeperResponse>();
    if (!Request->SetResponseBodyReceiveStream(Body)) { Request.Reset(); return; }
    const uint64 ExpectedSession = Session;
    TWeakObjectPtr<UDaedalusSimulationKeeper> Self(this);
    Request->OnProcessRequestComplete().BindLambda([Self, ExpectedSession, Body](FHttpRequestPtr Done, FHttpResponsePtr Response, bool bConnected) {
        if (!Self.IsValid() || !Self->CanRun() || !Self->bRunning || Self->Session != ExpectedSession || Self->Request != Done) return;
        Self->Request.Reset();
        if (!bConnected || !Response.IsValid() || Response->GetResponseCode() != 200 || Body->IsError()) return;
        // Raw UTF-8 bytes keep Java long counters exact; FJsonValue's double conversion would lose precision.
        daedalus::simulation::View Parsed;
        if (daedalus::simulation::DecodeView(Body->Bytes, Parsed)) {
            Self->Mailbox.TryPush(ExpectedSession, MoveTemp(Parsed), FPlatformTime::Seconds());
        }
    });
    if (!Request->ProcessRequest()) Request.Reset();
}

void UDaedalusSimulationKeeper::TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction) {
    Super::TickComponent(DeltaTime, TickType, ThisTickFunction);
    if (!CanRun() || !bRunning) return;
    const double Now = FPlatformTime::Seconds();
    Mailbox.Pump(Now);
    View.bFresh = Mailbox.Fresh(Now);
    const auto* State = Mailbox.Current();
    if (State && (View.Task.IsEmpty() || View.Revision != State->Revision)) {
        View.Task = UTF8_TO_TCHAR(State->Task.c_str()); View.Reason = UTF8_TO_TCHAR(State->Reason.c_str());
        View.RememberedActor = UTF8_TO_TCHAR(State->RememberedActor.c_str());
        View.Tick = State->Tick; View.Revision = State->Revision;
        View.CisternWater = State->CisternWater; View.KeeperWater = State->KeeperWater;
        View.bQuestCompleted = State->QuestCompleted; View.bDrySpell = State->DrySpell;
    }
    if (Now >= NextPoll) { NextPoll = Now + 1.0; Poll(); }
    if (View.bFresh && bMoveKeeper) MoveKeeper(DeltaTime);
}

void UDaedalusSimulationKeeper::MoveKeeper(float DeltaTime) {
    AActor* Owner = GetOwner();
    if (GetWorld()->GetNetMode() != NM_Standalone && (!Owner->GetIsReplicated() || !Owner->IsReplicatingMovement())) return;
    AActor* Marker = View.Task == TEXT("REST") ? RestMarker.Get() : View.Task == TEXT("WORK") ? WorkMarker.Get() : WaterMarker.Get();
    UPrimitiveComponent* Root = Cast<UPrimitiveComponent>(Owner->GetRootComponent());
    if (!IsValid(Marker) || !Root || !Root->IsQueryCollisionEnabled() || Root->IsSimulatingPhysics()
        || Root->Mobility != EComponentMobility::Movable) return;
    const FVector At = Owner->GetActorLocation(), Goal = Marker->GetActorLocation();
    const auto Delta = daedalus::simulation::Step({At.X, At.Y, At.Z}, {Goal.X, Goal.Y, Goal.Z}, 180.0, DeltaTime);
    if (Delta.X == 0.0 && Delta.Y == 0.0) return;
    const FVector Next = At + FVector(Delta.X, Delta.Y, 0.0);
    FCollisionQueryParams Query(SCENE_QUERY_STAT(DaedalusSimulationKeeper), false, Owner);
    FHitResult Ground;
    if (!GetWorld()->LineTraceSingleByObjectType(Ground, Next + FVector(0, 0, 100), Next - FVector(0, 0, 300),
        FCollisionObjectQueryParams(ECC_WorldStatic), Query) || Ground.ImpactNormal.Z < 0.85f) return;
    // Preserve the actor's collision clearance rather than snapping its centre to the ground.
    FHitResult CurrentGround;
    if (!GetWorld()->LineTraceSingleByObjectType(CurrentGround, At + FVector(0, 0, 100), At - FVector(0, 0, 300),
        FCollisionObjectQueryParams(ECC_WorldStatic), Query)) return;
    const double Rise = Ground.ImpactPoint.Z - CurrentGround.ImpactPoint.Z;
    if (Rise > 40.0 || Rise < -60.0) return;
    FHitResult Sweep;
    Owner->SetActorLocation(Next + FVector(0, 0, Rise), true, &Sweep);
}
