// SPDX-License-Identifier: MIT

#include "DaedalusTactics.h"

#include "DaedalusTacticsCore.h"
#include "DaedalusTarget.h"
#include "DaedalusHero.h"
#include "Misc/Guid.h"
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

void UDaedalusTactics::Initialize(FSubsystemCollectionBase& Collection)
{
	Super::Initialize(Collection);
	Session = FGuid::NewGuid().ToString(EGuidFormats::Digits).Left(12).ToLower();   // a token: [0-9a-f]{12}
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
	if (!bLocal)
	{
		// Stale fencing (Astra's integration requirement): Java's ticks only move forward for a squad. A repeat is
		// ignored; an older spec is refused whole.
		const int64* Last = LastExternalTick.Find(Squad);
		const daedalus::tactics::Fence F = daedalus::tactics::Check(Last ? *Last : 0, Last != nullptr, R.Out.Tick);
		if (F == daedalus::tactics::Fence::Repeat) return FString::Printf(TEXT("repeat: tick %lld"), R.Out.Tick);
		if (F == daedalus::tactics::Fence::Stale)
		{
			++Refused;
			LastError = FString::Printf(TEXT("stale tick %lld <= %lld for %s"), R.Out.Tick, *Last, *Squad);
			return TEXT("refused: ") + LastError;
		}
		LastExternalTick.Add(Squad, R.Out.Tick);
	}
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
	const ADaedalusHero* Hero = Cast<ADaedalusHero>(Player);
	Note(TEXT("PLAYER"), TEXT("player"), Player->GetActorLocation(), Hero ? Hero->Health : -1.f);   // -1 = health unknown
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

void UDaedalusTactics::NoteDown(const FString& Squad, const FString& Unit, const FString& Kind, float MaxHealth, const FVector& At)
{
	if (Squad.IsEmpty()) return;
	TArray<FDowned>& D = Downed.FindOrAdd(Squad);
	if (D.Num() < static_cast<int32>(daedalus::tactics::MaxOrders) && !D.ContainsByPredicate([&](const FDowned& X) { return X.Unit == Unit; }))
		D.Add({Unit, Kind, MaxHealth, At});
}

FString UDaedalusTactics::TakeRoster(const FString& Squad)
{
	std::vector<daedalus::tactics::RosterUnit> Units;
	TArray<ADaedalusTarget*> M = Members(Squad);
	// std::vector, not TArray: RosterUnit holds std::string, which TArray's bitwise relocation must not move.
	for (const ADaedalusTarget* T : M)
		Units.push_back({TCHAR_TO_UTF8(*T->TacticalId()), TCHAR_TO_UTF8(*T->Kind), FMath::Clamp(T->Health, 0.f, T->MaxHealth), T->MaxHealth,
			V(T->GetActorLocation()), T->bSeesPlayer});
	// The fallen stay on the roster at health 0: casualties are what raise the director's caution.
	if (const TArray<FDowned>* D = Downed.Find(Squad))
		for (const FDowned& X : *D)
		{
			const std::string Id = TCHAR_TO_UTF8(*X.Unit);
			if (std::none_of(Units.begin(), Units.end(), [&](const daedalus::tactics::RosterUnit& U) { return U.Unit == Id; }))
				Units.push_back({Id, TCHAR_TO_UTF8(*X.Kind), 0.0, X.MaxHealth, V(X.At), false});
		}
	std::sort(Units.begin(), Units.end(), [](const daedalus::tactics::RosterUnit& A, const daedalus::tactics::RosterUnit& B) { return A.Unit < B.Unit; });
	if (Units.size() > daedalus::tactics::MaxOrders) Units.resize(daedalus::tactics::MaxOrders);
	return UTF8_TO_TCHAR(daedalus::tactics::WriteRoster(TCHAR_TO_UTF8(*Session), TCHAR_TO_UTF8(*Squad), TickNo, Units).c_str());
}

FString UDaedalusTactics::Stats() const
{
	return FString::Printf(TEXT("session=%s squads=%s decided=%d applied=%d refused=%d outbox=%d dropped=%d last_error=%s"), *Session, *Squads(), Decided,
		Applied, Refused, Outbox.Num(), Dropped, *LastError);
}
