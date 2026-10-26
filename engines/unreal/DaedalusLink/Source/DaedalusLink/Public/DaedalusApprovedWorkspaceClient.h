// SPDX-License-Identifier: MIT
#pragma once
#include "CoreMinimal.h"

/** Snapshot of the original app's explicitly approved, immutable local plan. */
struct FDaedalusApprovedWorkspaceView
{
    FString Status, PlanId, ActionId, State, Mode, Settings, ExpiresAt;
    int32 Total = 0, Completed = 0, Saved = 0, Failed = 0, Skipped = 0, Conflicts = 0, Canceled = 0;
    bool bHasCanceledCount = false, bCancelRequested = false;
    bool bPaired = false, bBusy = false, bUncertain = false;
    bool bCanPair = true, bCanStart = false, bCanRefresh = false, bCanCancel = false, bCanDisconnect = false;
};

/** Game-thread-only monitor/controller. Conversion, paths and output commits remain in the desktop app.
 * One bounded direct-loopback worker owns only wire data. It never captures this client or a UObject.
 */
class DAEDALUSLINK_API FDaedalusApprovedWorkspaceClient
{
public:
    explicit FDaedalusApprovedWorkspaceClient(bool bPhoto);
    ~FDaedalusApprovedWorkspaceClient();
    FDaedalusApprovedWorkspaceView GetView() const;
    bool Pair(const FString& Link);
    void StartOrRetry();
    void Refresh();
    void Cancel();
    void Disconnect();
    void Tick();
    void Shutdown();
private:
    class FImpl;
    TUniquePtr<FImpl> Impl;
};
