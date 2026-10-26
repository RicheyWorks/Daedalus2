// SPDX-License-Identifier: MIT
#pragma once

#include "CoreMinimal.h"
#include "UObject/Object.h"
#include "WebJSFunction.h"
#include "DaedalusFaxWorkbenchFiles.generated.h"

class ADaedalusFaxWorkbenchTerminal;

/** Fixed local SaveAs only. Never binds Synapse selectors or invokes a server operation. */
UCLASS(Transient)
class DAEDALUSLINK_API UDaedalusFaxWorkbenchBridge final : public UObject
{
    GENERATED_BODY()
public:
    void Initialize(ADaedalusFaxWorkbenchTerminal* InOwner, uint64 InGeneration);
    void MarkPaired(double PairStartedSeconds);
    void Invalidate();

    UFUNCTION()
    void SavePng(const FString& Base64Bytes, const FString& GrantExpiresAt, int32 RemainingLeaseMillis, FWebJSResponse Response);
    UFUNCTION()
    void SaveText(const FString& Base64Bytes, const FString& GrantExpiresAt, int32 RemainingLeaseMillis, FWebJSResponse Response);

private:
    bool Allowed() const;
    bool AdmitLease(const FString& Expiry, int32 RemainingMillis, double EntrySeconds);
    bool BeginAction();
    void Save(bool bPng, const FString& Base64Bytes, const FString& Expiry, int32 RemainingMillis,
        double EntrySeconds, FWebJSResponse Response);
    TWeakObjectPtr<ADaedalusFaxWorkbenchTerminal> Owner;
    uint64 Generation = 0;
    uint64 ActionDocumentGeneration = 0;
    int32 ActionCount = 0;
    double LastActionSeconds = -100.0;
    double PairDeadline = -1.0;
    double GrantDeadline = -1.0;
    FString PinnedExpiry;
    FDateTime GrantUtc;
    bool bBusy = false;
    bool bBlocked = false;
};
