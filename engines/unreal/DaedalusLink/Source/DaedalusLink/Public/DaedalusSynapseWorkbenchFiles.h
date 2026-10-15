// SPDX-License-Identifier: MIT
#pragma once

#include "CoreMinimal.h"
#include "Templates/Function.h"
#include "UObject/Object.h"
#include "WebJSFunction.h"
#include "DaedalusSynapseWorkbenchFiles.generated.h"

class ADaedalusSynapseWorkbenchTerminal;

namespace DaedalusSynapseWorkbenchFiles
{
    enum class ESelection : uint8 { Image, MemoryJson };
    struct FSelectedBytes { TArray<uint8> Bytes; FString Mime; };
    bool Supported();
    bool Select(ESelection Kind, FSelectedBytes& Out, FString& Error, TFunctionRef<bool()> IsStillAllowed);
    bool SaveMemoryJson(const TArray<uint8>& Bytes, FString& Error, TFunctionRef<bool()> IsStillAllowed);
}

/** Native C++ exports only. These functions do not widen the Synapse JS binding. */
namespace DaedalusWorkbenchExports
{
    bool SaveFaxQrPng(const TArray<uint8>& Bytes, FString& Error, TFunctionRef<bool()> IsStillAllowed);
    bool SaveFaxPlainText(const TArray<uint8>& Bytes, FString& Error, TFunctionRef<bool()> IsStillAllowed);
}

/** The sole JS binding: selected bytes in, generated JSON bytes out; never paths, URLs or commands. */
UCLASS(Transient)
class DAEDALUSLINK_API UDaedalusSynapseWorkbenchBridge final : public UObject
{
    GENERATED_BODY()
public:
    void Initialize(ADaedalusSynapseWorkbenchTerminal* InOwner, uint64 InGeneration);
    void Invalidate();

    UFUNCTION()
    void PickImage(FWebJSResponse Response);
    UFUNCTION()
    void PickImport(FWebJSResponse Response);
    UFUNCTION()
    void SaveJson(const FString& Base64Bytes, FWebJSResponse Response);

private:
    void Pick(DaedalusSynapseWorkbenchFiles::ESelection Kind, FWebJSResponse Response);
    bool Allowed() const;
    bool BeginAction();
    TWeakObjectPtr<ADaedalusSynapseWorkbenchTerminal> Owner;
    uint64 Generation = 0;
    int32 ActionCount = 0;
    double LastActionSeconds = -100.0;
    bool bBusy = false;
};
