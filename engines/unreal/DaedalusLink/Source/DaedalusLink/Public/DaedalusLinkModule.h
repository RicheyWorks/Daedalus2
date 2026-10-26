// SPDX-License-Identifier: MIT

#pragma once

#include "Modules/ModuleManager.h"

DECLARE_LOG_CATEGORY_EXTERN(LogDaedalus, Log, All);

#if WITH_EDITOR
class FStartupUcsAttributionObserver;
#endif

/** Daedalus Link (ADR-032): a live Daedalus world inside Unreal Engine 5. */
class FDaedalusLinkModule : public IModuleInterface
{
public:
	virtual void StartupModule() override;
	virtual void ShutdownModule() override;
	virtual bool SupportsDynamicReloading() override;
	virtual bool SupportsAutomaticShutdown() override;

private:
#if WITH_EDITOR
	void DetachStartupUcsObserver();
	FStartupUcsAttributionObserver* StartupUcsObserver = nullptr;
	FDelegateHandle StartupUcsPreExitHandle;
#endif
};
