#include "StartupUcsAttributionObserver.h"

#if WITH_EDITOR && DO_BLUEPRINT_GUARD
#include "Engine/Level.h"
#include "Engine/World.h"
#include "GameFramework/Actor.h"
#include "HAL/PlatformTime.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "ProfilingDebugging/CpuProfilerTrace.h"
#include "UObject/Class.h"

namespace
{
// These are short callback-boundary events, NOT a trace scope spanning UCS.
// BlueprintTime's intervening scope makes spanning the two delegates unsafe.
class FLocalCpuBoundary
{
public:
    explicit FLocalCpuBoundary(const FString& Name)
    {
#if CPUPROFILERTRACE_ENABLED
        bStarted = TRACE_CPUPROFILER_EVENT_MANUAL_IS_ENABLED();
        if (bStarted)
        {
            FCpuProfilerTrace::OutputBeginDynamicEvent(*Name, __FILE__, __LINE__);
        }
#endif
    }
    ~FLocalCpuBoundary()
    {
#if CPUPROFILERTRACE_ENABLED
        if (bStarted)
        {
            FCpuProfilerTrace::OutputEndEvent();
        }
#endif
    }
    bool Started() const { return bStarted; }
    FLocalCpuBoundary(const FLocalCpuBoundary&) = delete;
    FLocalCpuBoundary& operator=(const FLocalCpuBoundary&) = delete;
private:
    bool bStarted = false;
};

struct FCallbackFlag
{
    explicit FCallbackFlag(bool& InFlag) : Flag(InFlag) { Flag = true; }
    ~FCallbackFlag() { Flag = false; }
    bool& Flag;
};

bool BoundedIdentity(const FString& Value)
{
    return !Value.IsEmpty() && Value.Len() <= 1024 && !Value.Contains(TEXT("\r")) && !Value.Contains(TEXT("\n"));
}

FString Csv(const FString& Value)
{
    return TEXT("\"") + Value.Replace(TEXT("\""), TEXT("\"\"")) + TEXT("\"");
}

void Emit(const TCHAR* Event, uint32 Id, int32 Depth, double Start, const FString& End,
          const FString& DurationMs, bool bMarker, const FString& Marker, const FString& World,
          const FString& Actor, const FString& Class, const FString& Level)
{
    UE_LOG(LogTemp, Display, TEXT("UCS_ATTR_V1,%s,%u,%d,%.9f,%s,%s,%d,%s,%s,%s,%s,%s"),
           Event, Id, Depth, Start, *End, *DurationMs, bMarker ? 1 : 0,
           *Csv(Marker), *Csv(World), *Csv(Actor), *Csv(Class), *Csv(Level));
}
}

FStartupUcsAttributionObserver::FStartupUcsAttributionObserver()
    : AttachedSeconds(FPlatformTime::Seconds())
{
    Active.Reserve(MaxObservations);
}

FStartupUcsAttributionObserver* FStartupUcsAttributionObserver::RegisterIfRequested()
{
    if (!IsInGameThread() || !FCommandLine::IsInitialized() ||
        !FParse::Param(FCommandLine::Get(), TEXT("DaedalusTraceUCS")))
    {
        return nullptr;
    }
    // Manual process-local one-shot guard; no global static auto-registration.
    static bool bEverRegistered = false;
    if (bEverRegistered)
    {
        return nullptr;
    }
    FStartupUcsAttributionObserver* Observer = new FStartupUcsAttributionObserver();
    Observer->EnterHandle = FBlueprintContextTracker::OnEnterScriptContext.AddRaw(Observer, &FStartupUcsAttributionObserver::Enter);
    Observer->ExitHandle = FBlueprintContextTracker::OnExitScriptContext.AddRaw(Observer, &FStartupUcsAttributionObserver::Exit);
    bEverRegistered = true;
    UE_LOG(LogTemp, Display, TEXT("UCS_ATTR_STATE_V1,ATTACHED,attached_seconds=%.9f,max=64,admission_seconds=240,boundary_markers_only=1"), Observer->AttachedSeconds);
    return Observer;
}

void FStartupUcsAttributionObserver::HoldPairing()
{
    if (!bPairingHeld)
    {
        bPairingHeld = true;
        UE_LOG(LogTemp, Warning, TEXT("UCS_ATTR_STATE_V1,HELD_PAIRING,retain_observer_and_module=1"));
    }
}

void FStartupUcsAttributionObserver::Enter(const FBlueprintContextTracker& Tracker, const UObject* Object, const UFunction* Function)
{
    if (!IsInGameThread() || bInCallback || bPairingHeld || Started >= MaxObservations ||
        FPlatformTime::Seconds() - AttachedSeconds >= AdmissionSeconds)
    {
        return;
    }
    FCallbackFlag Callback(bInCallback);
    if (Function == nullptr || Function->GetFName() != UcsName)
    {
        return;
    }
    const AActor* Actor = Cast<AActor>(Object);
    if (Actor == nullptr || !Actor->IsRunningUserConstructionScript())
    {
        return;
    }
    const UWorld* World = Actor->GetWorld();
    const ULevel* Level = Actor->GetLevel();
    if (World == nullptr || Level == nullptr || World->GetPathName() != TargetWorld)
    {
        return;
    }
    const int32 Depth = Tracker.GetScriptEntryTag(); // Entry already incremented.
    if (Depth <= 0 || (!Active.IsEmpty() &&
        (Active.Last().Tracker != &Tracker || Active.Last().Depth >= Depth)))
    {
        HoldPairing();
        return;
    }
    FActiveContext Frame;
    Frame.ActorPath = Actor->GetPathName();
    Frame.ClassPath = Actor->GetClass()->GetPathName();
    Frame.LevelPath = Level->GetPathName();
    if (!BoundedIdentity(Frame.ActorPath) || !BoundedIdentity(Frame.ClassPath) || !BoundedIdentity(Frame.LevelPath))
    {
        return; // No truncated identity is accepted as a named actor observation.
    }
    Frame.Id = ++Started;
    Frame.Depth = Depth;
    Frame.Tracker = &Tracker;
    Frame.StartSeconds = FPlatformTime::Seconds();
    if (Frame.StartSeconds - AttachedSeconds >= AdmissionSeconds)
    {
        --Started;
        return;
    }
    Active.Add(MoveTemp(Frame));
    const FActiveContext& Current = Active.Last();
    const FString Marker = FString::Printf(TEXT("Daedalus.UCS.Enter.%03u"), Current.Id);
    FLocalCpuBoundary Boundary(Marker);
    Emit(TEXT("BEGIN"), Current.Id, Depth, Current.StartSeconds, TEXT(""), TEXT(""), Boundary.Started(),
         Marker, TargetWorld, Current.ActorPath, Current.ClassPath, Current.LevelPath);
}

void FStartupUcsAttributionObserver::Exit(const FBlueprintContextTracker& Tracker)
{
    if (!IsInGameThread() || bInCallback || Active.IsEmpty() || bPairingHeld)
    {
        return;
    }
    FCallbackFlag Callback(bInCallback);
    const int32 Depth = Tracker.GetScriptEntryTag(); // Exit broadcasts BEFORE decrement.
    const FActiveContext& Current = Active.Last();
    if (Current.Tracker != &Tracker || Depth < Current.Depth)
    {
        HoldPairing();
        return;
    }
    if (Depth != Current.Depth)
    {
        return; // A nested, unobserved script context; it cannot close this UCS.
    }
    const double End = FPlatformTime::Seconds();
    const FString Marker = FString::Printf(TEXT("Daedalus.UCS.Exit.%03u"), Current.Id);
    {
        FLocalCpuBoundary Boundary(Marker);
        Emit(TEXT("END"), Current.Id, Depth, Current.StartSeconds, FString::Printf(TEXT("%.9f"), End),
             FString::Printf(TEXT("%.6f"), (End - Current.StartSeconds) * 1000.0), Boundary.Started(),
             Marker, TargetWorld, Current.ActorPath, Current.ClassPath, Current.LevelPath);
    }
    Active.Pop(EAllowShrinking::No); // Contains strings and tracker identity only; no UObject retained.
}

bool FStartupUcsAttributionObserver::TryDetachAndDestroy(FStartupUcsAttributionObserver*& Observer)
{
    if (Observer == nullptr)
    {
        return true;
    }
    if (!IsInGameThread() || Observer->bInCallback || !Observer->Active.IsEmpty() || Observer->bPairingHeld)
    {
        if (IsInGameThread() && !Observer->bUnsafeDetachReported)
        {
            Observer->bUnsafeDetachReported = true;
            UE_LOG(LogTemp, Warning, TEXT("UCS_ATTR_STATE_V1,DETACH_REFUSED,retain_observer_and_module=1"));
        }
        return false;
    }
    FBlueprintContextTracker::OnEnterScriptContext.Remove(Observer->EnterHandle);
    FBlueprintContextTracker::OnExitScriptContext.Remove(Observer->ExitHandle);
    UE_LOG(LogTemp, Display, TEXT("UCS_ATTR_STATE_V1,DETACHED,observations=%u"), Observer->Started);
    delete Observer;
    Observer = nullptr;
    return true;
}
#endif
