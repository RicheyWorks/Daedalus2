// SPDX-License-Identifier: MIT
#pragma once
#include "CoreMinimal.h"
#include <cstddef>
#include <string>

/** Same-module, one-way local SVG artifacts. Only these fixed kinds select
 * folders/names; callers cannot supply paths, extensions or byte limits.
 * Fresh files, including failed/partial files, are never overwritten/deleted. */
namespace DaedalusLocalSvgFiles
{
    enum class Kind { Blueprint, Storyboard };
    inline constexpr std::size_t MaxBytes=65536;
    /** Empty unless kind is known and ID is 32 lower-hex digits, not all zero. */
    FString Filename(Kind Type,const FString& Id);
    /** Success requires full write, flush, close and exact bounded readback.
     * No lineage/source mutation; a failed call may have kept a fresh file. */
    bool WriteNewVerified(Kind Type,const FString& Id,const std::string& Bytes,FString& Error);
}
