// SPDX-License-Identifier: MIT

#include "DaedalusTactics.h"

#include "DaedalusTacticsCore.h"
#include "DaedalusTarget.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/Pawn.h"
#include "HAL/IConsoleManager.h"
#include "Kismet/GameplayStatics.h"

static TAutoConsoleVariable<int32> CVarTactics(TEXT("daedalus.Tactics"), 1,
	TEXT("1 = the local squad director gives packs orders once a second (ADR-060); 0 = off (foes fight alone)."));

namespace
{
	constexpr int32 MaxOutbox = 512;
	daedalus::tactics::Vec V(const FVector& P) { return daedalus::tactics::Vec{P.X, P.Y, P.Z}; }
	FVector F(const daedalus::tactics::Vec& P) { return FVector(P.X, P.Y, P.Z); }
}

bool UDaedalusTactics::DoesSupportWorldType(const EWorldType::Type WorldType) const
{
	return WorldType == EWorldType::Game || WorldType == EWorldType::PIE;
}

UDaedalusTactics* UDaedalusTactics::GetTactics(const UObject* WorldContext)
{
	const UWorld* W = WorldContext ? WorldContext->GetWorld() : nullptr;
	return W ? W->GetSubsystem<UDaedalusTactics>() : nullptr;
}

TArray<ADaedalusTarget*> UDaedalusTactics::Members(const FString& Squad) const
{
	TArray<ADaedalusTarget*> Out;
	if (UWorld* W = GetWorld())
		for (TActorIterator<ADaedalusTarget> It(W); It; ++It)
			if (It->IsAlive() && It->Squad == Squad) Out.Add(*It);
	return Out;
}

FString UDaedalusTactics::Squads() const
{
	TSet<FString> S;
	if (UWorld* W = GetWorld())
		for (TActorIterator<ADaedalusTarget> It(W); It; ++It)
			if (It->IsAlive() && !It->Squad.IsEmpty()) S.Add(It->Squad);
	TArray<FString> A = S.Array();
	A.Sort();
	return FString::Join(A, TEXT(","));
}

FString UDaedalusTactics::ApplyOrders(const FString& Spec)
{
	return Apply(Spec, false);
}

FString UDaedalusTactics::Apply(const FString& Spec, bool bLocal)
{
	const daedalus::tactics::ParseResult R = daedalus::tactics::Parse(TCHAR_TO_UTF8(*Spec));
	if (!R.Ok)
	{
		++Refused;
		LastError = UTF8_TO_TCHAR(R.Error.c_str());
		return TEXT("refused: ") + LastError;
	}
	const FString Squad = UTF8_TO_TCHAR(R.Out.Squad.c_str());
	TArray<ADaedalusTarget*> M = Members(Squad);
	int32 Done = 0, Unknown = 0;
	for (const daedalus::tactics::Order& O : R.Out.Orders)
	{
		const FString Id = UTF8_TO_TCHAR(O.Unit.c_str());
		ADaedalusTarget** Who = M.FindByPredicate([&](const ADaedalusTarget* T) { return T->TacticalId() == Id; });
		if (!Who) { ++Unknown; continue; }
		FString Why = UTF8_TO_TCHAR(O.Why.c_str());
		if (O.Way != daedalus::tactics::Side::None) Why += FString::Printf(TEXT(" (%s)"), UTF8_TO_TCHAR(daedalus::tactics::SideName(O.Way)));
		(*Who)->SetOrder(UTF8_TO_TCHAR(daedalus::tactics::VerbName(O.Do)), F(O.At), Why, OrderSeconds);
		++Done;
	}
	++Applied;
	if (!bLocal)
		if (const UWorld* W = GetWorld()) ExternalUntil.Add(Squad, W->GetTimeSeconds() + ExternalHold);   // Java has it now
	return FString::Printf(TEXT("applied=%d unknown=%d squad=%s"), Done, Unknown, *Squad);
}

FString UDaedalusTactics::DecideNow(const FString& Squad)
{
	const APawn* Player = UGameplayStatics::GetPlayerPawn(this, 0);
	TArray<ADaedalusTarget*> M = Members(Squad);
	if (!Player || M.Num() == 0) return FString();
	std::vector<daedalus::tactics::Unit> Units;
	for (const ADaedalusTarget* T : M)
		Units.push_back({TCHAR_TO_UTF8(*T->TacticalId()), V(T->GetActorLocation()), T->Health, T->MaxHealth, T->bSeesPlayer});
	const daedalus::tactics::Spec S = daedalus::tactics::Decide(TCHAR_TO_UTF8(*Squad), TickNo, Units, V(Player->GetActorLocation()));
	const FString Text = UTF8_TO_TCHAR(daedalus::tactics::Write(S).c_str());
	++Decided;
	Apply(Text, true);
	return Text;
}

void UDaedalusTactics::Note(const FString& Kind, const FString& Unit, const FVector& At, float Value)
{
	if (Outbox.Num() >= MaxOutbox)
	{
		Outbox.RemoveAt(0);   // oldest first: Java is not reading, so keep the latest
		++Dropped;
	}
	Outbox.Add({Kind, Unit, At, Value});
}

FString UDaedalusTactics::TakeEvents()
{
	std::vector<daedalus::tactics::Event> E;
	for (const FNote& N : Outbox)
	{
		daedalus::tactics::Event Ev;
		Ev.Kind = N.Kind == TEXT("HIT") ? daedalus::tactics::EventKind::Hit : N.Kind == TEXT("DOWN") ? daedalus::tactics::EventKind::Down
			: N.Kind == TEXT("PLAYER") ? daedalus::tactics::EventKind::Player : daedalus::tactics::EventKind::Seen;
		Ev.Unit = TCHAR_TO_UTF8(*N.Unit);
		Ev.At = V(N.At);
		Ev.Value = N.Value;
		E.push_back(Ev);
	}
	Outbox.Reset();
	return UTF8_TO_TCHAR(daedalus::tactics::WriteEvents(TickNo, E).c_str());
}

void UDaedalusTactics::Tick(float DeltaTime)
{
	Next -= DeltaTime;
	if (Next > 0.f) return;
	Next = 1.f;
	++TickNo;
	const UWorld* W = GetWorld();
	const APawn* Player = UGameplayStatics::GetPlayerPawn(this, 0);
	if (!W || !Player) return;
	Note(TEXT("PLAYER"), TEXT("player"), Player->GetActorLocation(), 0.f);
	TSet<FString> Seen;
	for (TActorIterator<ADaedalusTarget> It(W); It; ++It)
	{
		if (!It->IsAlive() || It->Squad.IsEmpty()) continue;
		Seen.Add(It->Squad);
		if (It->bSeesPlayer) Note(TEXT("SEEN"), It->TacticalId(), It->GetActorLocation(), 1.f);
	}
	if (CVarTactics.GetValueOnGameThread() == 0) return;
	const double Now = W->GetTimeSeconds();
	for (const FString& Squad : Seen)
	{
		const double* Until = ExternalUntil.Find(Squad);
		if (Until && *Until > Now) continue;   // Java has this squad
		DecideNow(Squad);
	}
}

FString UDaedalusTactics::Stats() const
{
	return FString::Printf(TEXT("squads=%s decided=%d applied=%d refused=%d outbox=%d dropped=%d last_error=%s"), *Squads(), Decided,
		Applied, Refused, Outbox.Num(), Dropped, *LastError);
}
