// SPDX-License-Identifier: MIT
#include "DaedalusLocalAppMachine.h"

#include "Components/StaticMeshComponent.h"
#include "DaedalusHero.h"
#include "DaedalusLocalAppLauncher.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "HAL/PlatformTime.h"
#include "UObject/ConstructorHelpers.h"
#if WITH_EDITOR
#include "UObject/UnrealType.h"
#endif

ADaedalusLocalAppMachine::ADaedalusLocalAppMachine()
{
	bReplicates = false;
	Tags.Add(TEXT("DaedalusPracticalApp"));
	Tags.Add(TEXT("LocalAppMachine"));
	static ConstructorHelpers::FObjectFinder<UStaticMesh> Cube(TEXT("/Engine/BasicShapes/Cube.Cube"));
	if (Cube.Succeeded())
	{
		Body->SetStaticMesh(Cube.Object);
		Body->SetRelativeScale3D(FVector(0.65f, 0.5f, 0.35f));
	}
}

daedalus::localapp::Kind ADaedalusLocalAppMachine::ExpectedApp() const
{
	return static_cast<daedalus::localapp::Kind>(Application);
}

void ADaedalusLocalAppMachine::SetApplication(EDaedalusLocalAppKind NextApplication)
{
	if (!IsInGameThread()) return;
	daedalus::localapp::Kind Selected = ExpectedApp();
	if (daedalus::localapp::ChangeApplication(Selected, static_cast<daedalus::localapp::Kind>(NextApplication),
		[this]() { ClearRuntimePairing(); })) Application = NextApplication;
}

#if WITH_EDITOR
void ADaedalusLocalAppMachine::PreEditChange(FProperty* PropertyAboutToChange)
{
	bEditingApplication = PropertyAboutToChange && PropertyAboutToChange->GetFName()
		== GET_MEMBER_NAME_CHECKED(ADaedalusLocalAppMachine, Application);
	if (bEditingApplication) ApplicationBeforeEdit = Application;
	Super::PreEditChange(PropertyAboutToChange);
}

void ADaedalusLocalAppMachine::PostEditChangeProperty(FPropertyChangedEvent& PropertyChangedEvent)
{
	if (PropertyChangedEvent.GetPropertyName() == GET_MEMBER_NAME_CHECKED(ADaedalusLocalAppMachine, Application))
	{
		if (bEditingApplication)
		{
			const EDaedalusLocalAppKind EditedApplication = Application;
			Application = ApplicationBeforeEdit;
			SetApplication(EditedApplication);
		}
		else ClearRuntimePairing(); // fail closed for edits that did not provide a pre-edit notification
	}
	bEditingApplication = false;
	Super::PostEditChangeProperty(PropertyChangedEvent);
}

void ADaedalusLocalAppMachine::PostEditUndo()
{
	Super::PostEditUndo();
	// Undo may restore a preset, never its process capability. Runtime fields are NonTransactional.
	ClearRuntimePairing();
}
#endif

EDaedalusLocalAppState ADaedalusLocalAppMachine::GetCompanionState() const
{
	return RuntimeCapabilityLink.IsEmpty() || Application != PairedApplication
		? EDaedalusLocalAppState::Unpaired : CompanionState;
}

FString ADaedalusLocalAppMachine::Prompt(const ADaedalusHero* Hero) const
{
	if (!CanUseLocally(Hero)) return TEXT("Local app companions are for your local player");
	if (daedalus::localapp::CompanionPath(ExpectedApp()).empty()) return TEXT("Select a supported local app");
	const FString Name = UTF8_TO_TCHAR(daedalus::localapp::AppName(ExpectedApp()));
	return GetCompanionState() == EDaedalusLocalAppState::Unpaired ? TEXT("Pair your local ") + Name : TEXT("Open ") + Name + TEXT(" companion");
}

bool ADaedalusLocalAppMachine::PairLocalApp(const FString& CapabilityLink)
{
	if (!IsInGameThread()) return false;
	ClearRuntimePairing();
	const UWorld* World = GetWorld();
	if (!daedalus::localapp::launcher::IsSupported() || !World || !World->IsGameWorld()
		|| World->GetNetMode() == NM_DedicatedServer || IsActorBeingDestroyed()) return false;
	if (CapabilityLink.Len() > static_cast<int32>(daedalus::localapp::MaxLinkLength)) return false;
	const FTCHARToUTF8 Narrow(*CapabilityLink, CapabilityLink.Len());
	if (!daedalus::localapp::IsValidCompanionLink(std::string_view(Narrow.Get(), Narrow.Length()), ExpectedApp())) return false;
	RuntimeCapabilityLink = CapabilityLink;
	PairedApplication = Application;
	CompanionState = EDaedalusLocalAppState::Paired;
	return true;
}

void ADaedalusLocalAppMachine::ClearRuntimePairing()
{
	if (!IsInGameThread()) return;
	RuntimeCapabilityLink.Empty();
	CompanionState = EDaedalusLocalAppState::Unpaired;
}

bool ADaedalusLocalAppMachine::CanUseLocally(const ADaedalusHero* Hero) const
{
	const UWorld* World = GetWorld();
	if (!daedalus::localapp::launcher::IsSupported() || !IsInGameThread() || !World || !IsValid(Hero) || IsActorBeingDestroyed()) return false;
	const APlayerController* Player = Cast<APlayerController>(Hero->GetController());
	const bool LocalPlayer = Hero->IsLocallyControlled() && Player && Player->IsLocalPlayerController();
	const float Reach = Hero->InteractReach;
	const double DistanceSquared = FVector::DistSquared(GetActorLocation(), Hero->GetActorLocation());
	const bool InReach = FMath::IsFinite(Reach) && Reach > 0.f && FMath::IsFinite(DistanceSquared)
		&& DistanceSquared <= FMath::Square(FMath::Min(Reach, 1000.f));
	return daedalus::photopdf::CanUseChooser(World->IsGameWorld(), World->GetNetMode() == NM_DedicatedServer,
		LocalPlayer, Hero->GetWorld() == World, InReach);
}

bool ADaedalusLocalAppMachine::Use(ADaedalusHero* Hero)
{
	if (!CanUseLocally(Hero) || RuntimeCapabilityLink.IsEmpty()) return false;
	const FTCHARToUTF8 Narrow(*RuntimeCapabilityLink, RuntimeCapabilityLink.Len());
	// Application can change through Blueprint/Details after pairing. It is checked again at Use,
	// and the guarded launcher repeats validation at the OS side-effect boundary.
	if (Application != PairedApplication || !daedalus::localapp::IsValidCompanionLink(
		std::string_view(Narrow.Get(), Narrow.Length()), ExpectedApp()))
	{
		ClearRuntimePairing();
		return false;
	}
	if (!LaunchGate.TryBegin(FPlatformTime::Seconds())) return false;
	if (!daedalus::localapp::launcher::LaunchCompanion(RuntimeCapabilityLink, ExpectedApp())) return false;
	CompanionState = EDaedalusLocalAppState::CompanionOpened;
	return true;
}

void ADaedalusLocalAppMachine::EndPlay(const EEndPlayReason::Type Reason)
{
	ClearRuntimePairing();
	Super::EndPlay(Reason);
}
