// SPDX-License-Identifier: MIT

#include "DaedalusEcology.h"
#include "DaedalusEcologyCore.h"
#include "Engine/World.h"
#include "Engine/Engine.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"

namespace eco = daedalus::ecology;

struct UDaedalusEcology::FImpl { eco::Field F; };

static FString EcoPath(const FString& Path, const TCHAR* Default)
{
	return Path.IsEmpty() ? FPaths::Combine(FPaths::ProjectSavedDir(), TEXT("Daedalus"), Default) : Path;
}

UDaedalusEcology::~UDaedalusEcology() { delete Field; Field = nullptr; }

bool UDaedalusEcology::LoadSnapshot(const FString& Path)
{
	const FString File = EcoPath(Path, TEXT("ecology.dbe"));
	FString Text;
	if (!FFileHelper::LoadFileToString(Text, *File)) { Error = TEXT("cannot read ") + File; return false; }
	return LoadSnapshotText(Text);
}

bool UDaedalusEcology::LoadSnapshotText(const FString& Spec)
{
	FImpl* Next = new FImpl();
	const eco::Result R = eco::ReadSnapshot(std::string(TCHAR_TO_UTF8(*Spec)), Next->F);
	if (!R.Ok) { Error = UTF8_TO_TCHAR(R.Error.c_str()); delete Next; return false; }
	delete Field; Field = Next; Error.Reset();
	return true;
}

float UDaedalusEcology::CoverAt(const FVector& Where) const
{
	return Field ? (float)Field->F.CoverAt(Where.X, Where.Y) : 0.f;
}

float UDaedalusEcology::ConcealmentAt(const FVector& Where) const
{
	return Field ? (float)Field->F.ConcealmentAt(Where.X, Where.Y) : 0.f;
}

bool UDaedalusEcology::BurningAt(const FVector& Where) const
{
	return Field && Field->F.BurningAt(Where.X, Where.Y);
}

bool UDaedalusEcology::QueueEvent(EDaedalusEcologyEvent Kind, const FVector& Where, float RadiusCm)
{
	if (Queue.Num() >= eco::MaxEvents || !(RadiusCm > 0.f) || RadiusCm > 100000.f) { return false; }
	Queue.Add({Kind, Where, RadiusCm});
	return true;
}

bool UDaedalusEcology::FlushEvents(const FString& Path)
{
	std::vector<eco::Event> Events;
	Events.reserve(Queue.Num());
	for (const FQueued& Q : Queue)
	{
		const eco::EventKind K = Q.Kind == EDaedalusEcologyEvent::Ignite ? eco::EventKind::IGNITE
			: Q.Kind == EDaedalusEcologyEvent::Blast ? eco::EventKind::BLAST : eco::EventKind::DOUSE;
		Events.push_back({K, Q.Where.X, Q.Where.Y, Q.Where.Z, (double)Q.RadiusCm});
	}
	std::string Out;
	const eco::Result R = eco::WriteEvents(Events, Out);
	if (!R.Ok) { Error = UTF8_TO_TCHAR(R.Error.c_str()); return false; }
	const FString File = EcoPath(Path, TEXT("ecology_events.dbe"));
	if (!FFileHelper::SaveStringToFile(FString(UTF8_TO_TCHAR(Out.c_str())), *File)) { Error = TEXT("cannot write ") + File; return false; }
	Queue.Reset(); Error.Reset();
	return true;
}

FString UDaedalusEcology::Stats() const
{
	return Field ? FString::Printf(TEXT("field=%dx%d tick=%lld queued=%d"), Field->F.W, Field->F.H, Field->F.Tick, Queue.Num())
		: FString::Printf(TEXT("field=none queued=%d"), Queue.Num());
}

UDaedalusEcology* UDaedalusEcology::GetEcology(const UObject* WorldContext)
{
	const UWorld* World = GEngine ? GEngine->GetWorldFromContextObject(WorldContext, EGetWorldErrorMode::ReturnNull) : nullptr;
	return World ? World->GetSubsystem<UDaedalusEcology>() : nullptr;
}
