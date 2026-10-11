// SPDX-License-Identifier: MIT

#include "DaedalusLinkModule.h"

DEFINE_LOG_CATEGORY(LogDaedalus);

void FDaedalusLinkModule::StartupModule()
{
	UE_LOG(LogDaedalus, Log, TEXT("Daedalus Link loaded: drop a Daedalus World actor into a level, or run Scripts/import_world_package.py."));
}

void FDaedalusLinkModule::ShutdownModule()
{
}

IMPLEMENT_MODULE(FDaedalusLinkModule, DaedalusLink)
