// SPDX-License-Identifier: MIT
#pragma once

#include "CoreMinimal.h"
#include "DaedalusImageOptimizerClient.h"

/** Explicit, local user file choices only. Paths never leave this helper. */
namespace DaedalusImageOptimizerFiles
{
    bool Supported();
    /** False with an empty Error means the user dismissed the dialog. */
    bool SelectImages(TArray<FDaedalusImageOptimizerImage>& Out, FString& Error);
    /** Index is one-based; Type 1 PNG / 2 JPEG must match the signature and chosen extension.
     * At most 32 MiB; no structural decode here. The client verifies MIME, exact wire length
     * and aggregate job bytes. A successful save always creates a new file.
     */
    bool SaveImage(const TArray<uint8>& Bytes, uint8 Type, int32 Index, FString& Error);
}
