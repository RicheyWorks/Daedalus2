// SPDX-License-Identifier: MIT
#include "DaedalusFaxWorkbenchFiles.h"
#include "DaedalusFaxWorkbenchTerminal.h"
#include "DaedalusSynapseWorkbenchFiles.h"
#include "HAL/PlatformTime.h"
#include "Misc/Base64.h"
#include "UObject/StrongObjectPtr.h"

namespace
{
    bool Instant(const FString& Value, FDateTime& Out)
    {
        // Same strict Java Instant UTC grammar as the existing preparation client.
        if (Value.Len() < 20 || Value.Len() > 30 || Value[4] != '-' || Value[7] != '-' || Value[10] != 'T'
            || Value[13] != ':' || Value[16] != ':' || Value[Value.Len() - 1] != 'Z') return false;
        for (int32 I = 0; I < 19; ++I)
            if (I != 4 && I != 7 && I != 10 && I != 13 && I != 16 && (Value[I] < '0' || Value[I] > '9')) return false;
        if (Value.Len() != 20)
        {
            if (Value.Len() < 22 || Value[19] != '.') return false;
            for (int32 I = 20; I < Value.Len() - 1; ++I) if (Value[I] < '0' || Value[I] > '9') return false;
        }
        // Floor sub-millisecond precision; never round grant expiry later.
        const FString Bounded = Value.Len() > 24 ? Value.Left(23) + TEXT("Z") : Value;
        return FDateTime::ParseIso8601(*Bounded, Out);
    }
}

void UDaedalusFaxWorkbenchBridge::Initialize(ADaedalusFaxWorkbenchTerminal* InOwner, uint64 InGeneration)
{
    Owner = InOwner; Generation = InGeneration; ActionCount = 0; bBusy = false; bBlocked = false;
    LastActionSeconds = -100.0; PairDeadline = -1.0; GrantDeadline = -1.0; PinnedExpiry.Reset();
}
void UDaedalusFaxWorkbenchBridge::MarkPaired(double PairStartedSeconds)
{
    if (IsInGameThread() && PairDeadline < 0 && FMath::IsFinite(PairStartedSeconds)) PairDeadline = PairStartedSeconds + 900.0;
}
void UDaedalusFaxWorkbenchBridge::Invalidate() { Owner.Reset(); ++Generation; bBlocked = true; GrantDeadline = 0; }
bool UDaedalusFaxWorkbenchBridge::Allowed() const
{
    const auto* Terminal = Owner.Get();
    const double Now = FPlatformTime::Seconds();
    return IsInGameThread() && !bBlocked && Terminal && Terminal->AllowsNativeFileAction(Generation)
        && PairDeadline > Now && (PinnedExpiry.IsEmpty() || (GrantDeadline > Now && FDateTime::UtcNow() < GrantUtc))
        && (!bBusy || Terminal->GetDocumentGeneration() == ActionDocumentGeneration);
}
bool UDaedalusFaxWorkbenchBridge::AdmitLease(const FString& Expiry, int32 RemainingMillis, double EntrySeconds)
{
    FDateTime Parsed;
    if (RemainingMillis < 1 || RemainingMillis > 900000 || !FMath::IsFinite(EntrySeconds) || !Instant(Expiry, Parsed)) return false;
    if (!PinnedExpiry.IsEmpty() && !PinnedExpiry.Equals(Expiry, ESearchCase::CaseSensitive)) { bBlocked = true; return false; }
    const double UtcRemaining = (Parsed - FDateTime::UtcNow()).GetTotalSeconds();
    if (!FMath::IsFinite(UtcRemaining) || UtcRemaining <= 0 || PairDeadline <= EntrySeconds) return false;
    const double Candidate = FMath::Min(PairDeadline, FMath::Min(EntrySeconds + RemainingMillis / 1000.0,
        EntrySeconds + FMath::Min(UtcRemaining, 900.0)));
    GrantDeadline = PinnedExpiry.IsEmpty() ? Candidate : FMath::Min(GrantDeadline, Candidate);
    PinnedExpiry = Expiry; GrantUtc = Parsed;
    return Allowed();
}
bool UDaedalusFaxWorkbenchBridge::BeginAction()
{
    const double Now = FPlatformTime::Seconds();
    if (!Allowed() || bBusy || ActionCount >= 64 || Now - LastActionSeconds < 0.5) return false;
    ActionDocumentGeneration = Owner->GetDocumentGeneration();
    bBusy = true; ++ActionCount; LastActionSeconds = Now;
    return true;
}
void UDaedalusFaxWorkbenchBridge::SavePng(const FString& Base64Bytes, const FString& GrantExpiresAt,
    int32 RemainingLeaseMillis, FWebJSResponse Response)
{
    const double EntrySeconds = FPlatformTime::Seconds();
    Save(true, Base64Bytes, GrantExpiresAt, RemainingLeaseMillis, EntrySeconds, Response);
}
void UDaedalusFaxWorkbenchBridge::SaveText(const FString& Base64Bytes, const FString& GrantExpiresAt,
    int32 RemainingLeaseMillis, FWebJSResponse Response)
{
    const double EntrySeconds = FPlatformTime::Seconds();
    Save(false, Base64Bytes, GrantExpiresAt, RemainingLeaseMillis, EntrySeconds, Response);
}
void UDaedalusFaxWorkbenchBridge::Save(bool bPng, const FString& Base64Bytes, const FString& Expiry,
    int32 RemainingMillis, double EntrySeconds, FWebJSResponse Response)
{
    if (!Allowed()) { Response.Failure(TEXT("Local export access ended.")); return; }
    const int32 MaxBytes = bPng ? 262144 : 393216;
    const int32 MaxBase64 = ((MaxBytes + 2) / 3) * 4;
    if (Base64Bytes.Len() > MaxBase64 || (bPng && Base64Bytes.IsEmpty()) || !AdmitLease(Expiry, RemainingMillis, EntrySeconds))
    { Response.Failure(TEXT("The local export or grant exceeded its limits.")); return; }
    if (!BeginAction()) { Response.Failure(TEXT("File action unavailable; wait or reopen the workbench.")); return; }
    TArray<uint8> Bytes;
    if ((!Base64Bytes.IsEmpty() && !FBase64::Decode(Base64Bytes, Bytes)) || Bytes.Num() > MaxBytes
        || !FBase64::Encode(Bytes).Equals(Base64Bytes, ESearchCase::CaseSensitive))
    { bBusy = false; Response.Failure(TEXT("The bounded file transfer was invalid.")); return; }
    const TStrongObjectPtr<UDaedalusFaxWorkbenchBridge> KeepAlive(this);
    const TWeakObjectPtr<UDaedalusFaxWorkbenchBridge> WeakThis(this);
    const uint64 Expected = Generation, ExpectedDocument = ActionDocumentGeneration;
    const auto AllowedNow = [WeakThis, Expected, ExpectedDocument]
    {
        const auto* Bridge = WeakThis.Get();
        const auto* Terminal = Bridge ? Bridge->Owner.Get() : nullptr;
        return Bridge && Bridge->Generation == Expected && Bridge->Allowed()
            && Terminal && Terminal->GetDocumentGeneration() == ExpectedDocument;
    };
    FString Error;
    const bool Saved = bPng ? DaedalusWorkbenchExports::SaveFaxQrPng(Bytes, Error, AllowedNow)
        : DaedalusWorkbenchExports::SaveFaxPlainText(Bytes, Error, AllowedNow);
    auto* Self = WeakThis.Get();
    if (!Self) return;
    Self->bBusy = false;
    if (!AllowedNow()) { Response.Failure(TEXT("Local export access ended. Any already committed copy remains.")); return; }
    if (!Error.IsEmpty()) Response.Failure(Error);
    else Response.Success(Saved ? TEXT("{\"canceled\":false}") : TEXT("{\"canceled\":true}"));
}
