// SPDX-License-Identifier: MIT
#pragma once

#include "CoreMinimal.h"
#include "DaedalusLocalAppCore.h"

// Internal OS side-effect boundary. Every entry point validates its exact known grammar; there is
// no generic launch-any-URL function. Do not log links/errors or pass them to UE's URL helpers.
namespace daedalus { namespace localapp { namespace launcher {

bool IsSupported();
bool LaunchPhotoPdf(const FString& CapabilityLink);
bool LaunchCompanion(const FString& CapabilityLink, Kind ExpectedApp);

}}} // namespace daedalus::localapp::launcher
