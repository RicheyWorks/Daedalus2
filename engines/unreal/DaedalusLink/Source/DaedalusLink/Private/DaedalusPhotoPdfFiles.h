// SPDX-License-Identifier: MIT
#pragma once

#include "CoreMinimal.h"
#include "DaedalusPhotoPdfClient.h"
#include "Templates/Function.h"

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
    /** Retains the caller's ownership/generation policy through the modal chooser and file commit. */
    bool SavePdf(const TArray<uint8>& Bytes, int32 Index, FString& Error, TFunctionRef<bool()> IsStillAllowed);
    /** Explicit save chooser for the selected prepared fax review PDF, at most 25 MiB.
     * Suggests only the generated name prepared-fax-review.pdf; the user chooses a new local target.
     * Requires a PDF header, not structural/page validation or evidence of transmission.
     * IsStillAllowed must retain the calling terminal's generation/ownership checks through the chooser and save.
     * False with an empty Error means the user dismissed the dialog. Never overwrites a file.
     */
    bool SavePreparedFaxPdf(const TArray<uint8>& Bytes, FString& Error, TFunctionRef<bool()> IsStillAllowed);
}
