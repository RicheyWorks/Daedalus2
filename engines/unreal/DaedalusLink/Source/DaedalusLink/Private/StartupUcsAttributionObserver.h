#pragma once

#include "CoreMinimal.h"
#include "UObject/Script.h"

#if WITH_EDITOR && DO_BLUEPRINT_GUARD
/** Opt-in proposal only. Manually owned by a non-dynamically-unloading editor module. */
class FStartupUcsAttributionObserver final
{
public:
    // No registration or allocation unless the explicit per-process flag is present.
    static FStartupUcsAttributionObserver* RegisterIfRequested();

    // GT only. False means retain the observer AND module; never delete/unload it.
    static bool TryDetachAndDestroy(FStartupUcsAttributionObserver*& Observer);

private:
    FStartupUcsAttributionObserver();
    ~FStartupUcsAttributionObserver() = default;
    FStartupUcsAttributionObserver(const FStartupUcsAttributionObserver&) = delete;
    FStartupUcsAttributionObserver& operator=(const FStartupUcsAttributionObserver&) = delete;
    void Enter(const FBlueprintContextTracker& Tracker, const UObject* Object, const UFunction* Function);
    void Exit(const FBlueprintContextTracker& Tracker);
    void HoldPairing();

    struct FActiveContext
    {
        uint32 Id = 0;
        int32 Depth = 0;
        const FBlueprintContextTracker* Tracker = nullptr; // Not a UObject; GT singleton identity only.
        double StartSeconds = 0.0;
        FString ActorPath;
        FString ClassPath;
        FString LevelPath;
    };

    static constexpr uint32 MaxObservations = 64;
    static constexpr double AdmissionSeconds = 240.0;
    const FString TargetWorld = TEXT("/Game/Daedalus/DaedalusWorld.DaedalusWorld");
    const FName UcsName = FName(TEXT("UserConstructionScript"));
    FDelegateHandle EnterHandle;
    FDelegateHandle ExitHandle;
    TArray<FActiveContext> Active;
    double AttachedSeconds = 0.0;
    uint32 Started = 0;
    bool bInCallback = false;
    bool bPairingHeld = false;
    bool bUnsafeDetachReported = false;
};
#endif
