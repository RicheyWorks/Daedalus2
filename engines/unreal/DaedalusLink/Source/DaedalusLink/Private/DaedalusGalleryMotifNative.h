// SPDX-License-Identifier: MIT
#pragma once
#include "CoreMinimal.h"
#include "DaedalusGalleryMotifCore.h"

/** Private same-module adapter for local motif studies. Reuses the Studio's
 * <=512-byte reader, exact filename/document identity check and palette.
 * No directory enumeration, export, canonical Gallery API or ownership action. */
namespace DaedalusMotifNative
{
    bool ReadLocalExport(const FString& Id,daedalus::motif::Document& Out,std::string& Bytes,FString& Error);
    FLinearColor PaletteColour(int32 Index);
}
