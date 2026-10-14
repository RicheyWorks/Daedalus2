// SPDX-License-Identifier: MIT
#pragma once

#include "CoreMinimal.h"
#include "DaedalusPhotoPdfClient.h"

/** Explicit, local user file choices only. Paths never leave this helper. */
namespace DaedalusPhotoPdfFiles
{
    bool Supported();
    /** False with an empty Error means the user dismissed the dialog. */
    bool SelectImages(TArray<FDaedalusPhotoPdfImage>& Out, FString& Error);
    /** Index is one-based. At most 64 MiB and a PDF header are required (not parsed here).
     * A successful save always creates a new file.
     */
    bool SavePdf(const TArray<uint8>& Bytes, int32 Index, FString& Error);
}
