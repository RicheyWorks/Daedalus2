// SPDX-License-Identifier: MIT

#include "DaedalusLinkModule.h"

#if WITH_EDITOR
#include "StartupUcsAttributionObserver.h"
#include "Misc/CoreDelegates.h"
#endif

DEFINE_LOG_CATEGORY(LogDaedalus);

void FDaedalusLinkModule::StartupModule()
{
#if WITH_EDITOR && DO_BLUEPRINT_GUARD
	StartupUcsObserver = FStartupUcsAttributionObserver::RegisterIfRequested();
	if (StartupUcsObserver)
	{
		StartupUcsPreExitHandle = FCoreDelegates::OnPreExit.AddRaw(this, &FDaedalusLinkModule::DetachStartupUcsObserver);
	}
#endif
	UE_LOG(LogDaedalus, Log, TEXT("Daedalus Link loaded: drop a Daedalus World actor into a level, or run Scripts/import_world_package.py."));
}

void FDaedalusLinkModule::ShutdownModule()
{
#if WITH_EDITOR
	DetachStartupUcsObserver();
	if (StartupUcsObserver == nullptr)
	{
		FCoreDelegates::OnPreExit.Remove(StartupUcsPreExitHandle);
		StartupUcsPreExitHandle.Reset();
	}
#endif
}

bool FDaedalusLinkModule::SupportsDynamicReloading()
{
#if WITH_EDITOR
	// The opt-in script delegates require resident code. No hot/Live Coding unload.
	return false;
#else
	return IModuleInterface::SupportsDynamicReloading();
#endif
}

bool FDaedalusLinkModule::SupportsAutomaticShutdown()
{
#if WITH_EDITOR
	// OnPreExit attempts quiescent detach. A held observer AND module remain
	// resident through process exit; void ShutdownModule is not an unload veto.
	return false;
#else
	return IModuleInterface::SupportsAutomaticShutdown();
#endif
}

#if WITH_EDITOR
void FDaedalusLinkModule::DetachStartupUcsObserver()
{
#if DO_BLUEPRINT_GUARD
	if (StartupUcsObserver && !FStartupUcsAttributionObserver::TryDetachAndDestroy(StartupUcsObserver))
	{
		UE_LOG(LogDaedalus, Warning, TEXT("Startup UCS observer detach held; observer and module remain resident until process exit."));
	}
#endif
}
#endif

IMPLEMENT_MODULE(FDaedalusLinkModule, DaedalusLink)
