// SPDX-License-Identifier: MIT

#pragma once

#include "Modules/ModuleManager.h"

DECLARE_LOG_CATEGORY_EXTERN(LogDaedalus, Log, All);

/** Daedalus Link (ADR-032): a live Daedalus world inside Unreal Engine 5. */
class FDaedalusLinkModule : public IModuleInterface
{
public:
	virtual void StartupModule() override;
	virtual void ShutdownModule() override;
};
