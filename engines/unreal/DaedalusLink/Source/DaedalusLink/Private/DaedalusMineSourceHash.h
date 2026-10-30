// SPDX-License-Identifier: MIT
#pragma once

#include "CoreMinimal.h"
#include <openssl/sha.h>

namespace DaedalusMineSourceHash
{
// OpenSSL is already linked by DaedalusLink. The generic platform SHA256
// entry point asserts on this Windows installation; provenance still requires
// the exact complete source-byte digest and refuses invalid input.
inline bool Compute(const uint8* Data, uint32 Size, FString& OutHex)
{
    OutHex.Reset();
    if (!Data && Size != 0)
    {
        return false;
    }
    static_assert(SHA256_DIGEST_LENGTH == 32, "SHA256 digest contract");
    uint8 Digest[SHA256_DIGEST_LENGTH] = {};
    if (SHA256(Data, static_cast<size_t>(Size), Digest) == nullptr)
    {
        return false;
    }
    OutHex = BytesToHex(Digest, SHA256_DIGEST_LENGTH).ToLower();
    return true;
}
}
