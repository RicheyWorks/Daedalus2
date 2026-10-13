// SPDX-License-Identifier: MIT
#include "DaedalusPhotoPdfMachine.h"

#include "Components/StaticMeshComponent.h"
#include "DaedalusHero.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "HAL/PlatformTime.h"
#include "UObject/ConstructorHelpers.h"

#if PLATFORM_WINDOWS
#include "Windows/WindowsHWrapper.h"
#include "Windows/AllowWindowsPlatformTypes.h"
#include <shellapi.h>
#include "Windows/HideWindowsPlatformTypes.h"
#pragma comment(lib, "shell32.lib")
#endif

namespace
{
	bool SupportsPrivateChooserLaunch()
	{
#if PLATFORM_WINDOWS
		return true;
#else
		return false;
#endif
	}

	bool LaunchPrivateChooser(const FString& CapabilityLink)
	{
#if PLATFORM_WINDOWS
		// UE's generic LaunchURL path can log the complete browser command on failure (Mac always
		// logs the URL). This Windows pilot calls the OS directly so our token never enters UE logs.
		// Safe only AFTER the exact loopback URL grammar was checked. No command or extra parameters.
		SHELLEXECUTEINFOW LaunchInfo{};
		LaunchInfo.cbSize = sizeof(LaunchInfo);
		LaunchInfo.fMask = SEE_MASK_FLAG_NO_UI | SEE_MASK_NOASYNC;
		LaunchInfo.lpVerb = L"open";
		LaunchInfo.lpFile = *CapabilityLink;
		LaunchInfo.nShow = SW_SHOWNORMAL;
		return ::ShellExecuteExW(&LaunchInfo) != 0;
#else
		// Fail closed until the platform has a vetted launcher that does not log capabilities.
		(void)CapabilityLink;
		return false;
#endif
	}
}

ADaedalusPhotoPdfMachine::ADaedalusPhotoPdfMachine()
{
	bReplicates = false;
	Tags.Add(TEXT("DaedalusPracticalApp"));
	Tags.Add(TEXT("PhotoPdfMachine"));
	// An engine-shipped placeholder only; no art assets or live levels are modified by this slice.
	static ConstructorHelpers::FObjectFinder<UStaticMesh> Cube(TEXT("/Engine/BasicShapes/Cube.Cube"));
	if (Cube.Succeeded())
	{
		Body->SetStaticMesh(Cube.Object);
		Body->SetRelativeScale3D(FVector(0.75f, 0.55f, 0.3f));
	}
}

FString ADaedalusPhotoPdfMachine::Prompt(const ADaedalusHero* Hero) const
{
	if (!CanUseLocally(Hero)) return TEXT("PhotosToPDFPC is for your local player");
	return RuntimeCapabilityLink.IsEmpty() ? TEXT("Pair your local PhotosToPDFPC app") : TEXT("Open PhotosToPDFPC photo chooser");
}

bool ADaedalusPhotoPdfMachine::PairLocalApp(const FString& CapabilityLink)
{
	ClearRuntimePairing();
	const UWorld* World = GetWorld();
	if (!SupportsPrivateChooserLaunch() || !IsInGameThread() || !World || !World->IsGameWorld()
		|| World->GetNetMode() == NM_DedicatedServer || IsActorBeingDestroyed())
		return false;
	// Bound before conversion. Preserve the length so an embedded NUL is rejected, not silently truncated.
	if (CapabilityLink.Len() > 160) return false;
	const FTCHARToUTF8 Narrow(*CapabilityLink, CapabilityLink.Len());
	if (!daedalus::photopdf::IsValidChooserLink(std::string_view(Narrow.Get(), Narrow.Length()))) return false;
	RuntimeCapabilityLink = CapabilityLink;
	ChooserState = EDaedalusPhotoPdfState::Paired;
	return true;
}

void ADaedalusPhotoPdfMachine::ClearRuntimePairing()
{
	RuntimeCapabilityLink.Empty();
	ChooserState = EDaedalusPhotoPdfState::Unpaired;
}

bool ADaedalusPhotoPdfMachine::CanUseLocally(const ADaedalusHero* Hero) const
{
	const UWorld* World = GetWorld();
	if (!SupportsPrivateChooserLaunch() || !IsInGameThread() || !World || !IsValid(Hero) || IsActorBeingDestroyed()) return false;
	const APlayerController* Player = Cast<APlayerController>(Hero->GetController());
	const bool LocalPlayer = Hero->IsLocallyControlled() && Player && Player->IsLocalPlayerController();
	// Hero::Interact already chooses a nearby Usable. Recheck for direct native Use callers as well.
	const float Reach = Hero->InteractReach;
	const double DistanceSquared = FVector::DistSquared(GetActorLocation(), Hero->GetActorLocation());
	const bool InReach = FMath::IsFinite(Reach) && Reach > 0.f && FMath::IsFinite(DistanceSquared)
		&& DistanceSquared <= FMath::Square(FMath::Min(Reach, 1000.f));
	return daedalus::photopdf::CanUseChooser(World->IsGameWorld(), World->GetNetMode() == NM_DedicatedServer,
		LocalPlayer, Hero->GetWorld() == World, InReach);
}

bool ADaedalusPhotoPdfMachine::Use(ADaedalusHero* Hero)
{
	if (!CanUseLocally(Hero) || RuntimeCapabilityLink.IsEmpty()) return false;
	// Revalidate at the actual side-effect boundary, and never pass other launch parameters.
	const FTCHARToUTF8 Narrow(*RuntimeCapabilityLink, RuntimeCapabilityLink.Len());
	if (!daedalus::photopdf::IsValidChooserLink(std::string_view(Narrow.Get(), Narrow.Length())))
	{
		ClearRuntimePairing();
		return false;
	}
	if (!LaunchGate.TryBegin(FPlatformTime::Seconds())) return false;
	if (!LaunchPrivateChooser(RuntimeCapabilityLink)) return false;
	ChooserState = EDaedalusPhotoPdfState::ChooserLaunched;
	return true;
}

void ADaedalusPhotoPdfMachine::EndPlay(const EEndPlayReason::Type Reason)
{
	ClearRuntimePairing();
	Super::EndPlay(Reason);
}
