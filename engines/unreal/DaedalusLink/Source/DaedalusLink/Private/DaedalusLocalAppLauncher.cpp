// SPDX-License-Identifier: MIT
#include "DaedalusLocalAppLauncher.h"

#if PLATFORM_WINDOWS
#include "Windows/WindowsHWrapper.h"
#include "Windows/AllowWindowsPlatformTypes.h"
#include <shellapi.h>
#include "Windows/HideWindowsPlatformTypes.h"
#pragma comment(lib, "shell32.lib")
#endif

namespace
{
	bool LaunchApprovedCapability(const FString& CapabilityLink)
	{
#if PLATFORM_WINDOWS
		// Unreal's generic launch path can log browser arguments on failure, or always on Mac.
		// Only exact capability grammars may reach this private wrapper. No command/extra parameters.
		SHELLEXECUTEINFOW LaunchInfo{};
		LaunchInfo.cbSize = sizeof(LaunchInfo);
		LaunchInfo.fMask = SEE_MASK_FLAG_NO_UI | SEE_MASK_NOASYNC;
		LaunchInfo.lpVerb = L"open";
		LaunchInfo.lpFile = *CapabilityLink;
		LaunchInfo.nShow = SW_SHOWNORMAL;
		return ::ShellExecuteExW(&LaunchInfo) != 0;
#else
		(void)CapabilityLink;
		return false;
#endif
	}
}

namespace daedalus { namespace localapp { namespace launcher {

bool IsSupported()
{
#if PLATFORM_WINDOWS
	return true;
#else
	return false;
#endif
}

bool LaunchPhotoPdf(const FString& CapabilityLink)
{
	if (!IsSupported() || !IsInGameThread() || CapabilityLink.Len() > 160) return false;
	const FTCHARToUTF8 Narrow(*CapabilityLink, CapabilityLink.Len());
	if (!photopdf::IsValidChooserLink(std::string_view(Narrow.Get(), Narrow.Length()))) return false;
	return LaunchApprovedCapability(CapabilityLink);
}

bool LaunchCompanion(const FString& CapabilityLink, Kind ExpectedApp)
{
	if (!IsSupported() || !IsInGameThread() || CapabilityLink.Len() > static_cast<int32>(MaxLinkLength)) return false;
	const FTCHARToUTF8 Narrow(*CapabilityLink, CapabilityLink.Len());
	if (!IsValidCompanionLink(std::string_view(Narrow.Get(), Narrow.Length()), ExpectedApp)) return false;
	return LaunchApprovedCapability(CapabilityLink);
}

}}} // namespace daedalus::localapp::launcher
