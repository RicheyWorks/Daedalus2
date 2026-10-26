// SPDX-License-Identifier: MIT
#pragma once

#include "CoreMinimal.h"
#include "DaedalusOrrery.h"
#include "DaedalusLocalAppCore.h"
#include "DaedalusLocalAppMachine.generated.h"

UENUM(BlueprintType)
enum class EDaedalusLocalAppKind : uint8
{
	ImageOptimizer = 0,
	Synapse = 1
};

/** Describes the native interface only, never completed image work or a completed study review. */
UENUM(BlueprintType)
enum class EDaedalusLocalAppState : uint8
{
	Unpaired,
	Paired,
	CompanionOpened
};

/** Another interface to an existing local app. The browser/app owns image selection, optimization
 * or the explicitly selected Synapse track/review. This actor reads no files, notes or job documents.
 * Windows-only launch pilot; final art/placement and runtime pairing UI belong to Claude/Blender.
 */
UCLASS(Blueprintable)
class DAEDALUSLINK_API ADaedalusLocalAppMachine : public ADaedalusUsable
{
	GENERATED_BODY()

public:
	ADaedalusLocalAppMachine();
	virtual FString Prompt(const ADaedalusHero* Hero) const override;
	virtual bool Use(ADaedalusHero* Hero) override;

	UFUNCTION(BlueprintGetter, Category = "Daedalus|Practical Apps")
	EDaedalusLocalAppKind GetApplication() const { return Application; }

	/** Actual preset changes discard pairing immediately, including changes away and back. */
	UFUNCTION(BlueprintSetter, Category = "Daedalus|Practical Apps")
	void SetApplication(EDaedalusLocalAppKind NextApplication);

	/** Pair at runtime with the same app's exact typed link. Invalid input clears previous pairing. */
	UFUNCTION(BlueprintCallable, Category = "Daedalus|Practical Apps")
	bool PairLocalApp(const FString& CapabilityLink);

	/** Forget pairing only. Job cancellation/deletion or a chosen study review remains in the app. */
	UFUNCTION(BlueprintCallable, Category = "Daedalus|Practical Apps")
	void ClearRuntimePairing();

	UFUNCTION(BlueprintPure, Category = "Daedalus|Practical Apps")
	EDaedalusLocalAppState GetCompanionState() const;

protected:
	virtual void EndPlay(const EEndPlayReason::Type Reason) override;
#if WITH_EDITOR
	virtual void PreEditChange(FProperty* PropertyAboutToChange) override;
	virtual void PostEditChangeProperty(FPropertyChangedEvent& PropertyChangedEvent) override;
	virtual void PostEditUndo() override;
#endif

private:
	bool CanUseLocally(const ADaedalusHero* Hero) const;
	daedalus::localapp::Kind ExpectedApp() const;

	// Saved preset only. C++ callers use the setter; Blueprint writes are routed through it.
	UPROPERTY(EditAnywhere, BlueprintGetter = GetApplication, BlueprintSetter = SetApplication,
		Category = "Daedalus|Practical Apps", meta = (AllowPrivateAccess = "true"))
	EDaedalusLocalAppKind Application = EDaedalusLocalAppKind::ImageOptimizer;

	UPROPERTY(Transient, DuplicateTransient, TextExportTransient, NonTransactional)
	FString RuntimeCapabilityLink;

	UPROPERTY(Transient, DuplicateTransient, TextExportTransient, NonTransactional)
	EDaedalusLocalAppKind PairedApplication = EDaedalusLocalAppKind::ImageOptimizer;

	UPROPERTY(Transient, DuplicateTransient, TextExportTransient, NonTransactional)
	EDaedalusLocalAppState CompanionState = EDaedalusLocalAppState::Unpaired;

#if WITH_EDITOR
	EDaedalusLocalAppKind ApplicationBeforeEdit = EDaedalusLocalAppKind::ImageOptimizer;
	bool bEditingApplication = false;
#endif

	// Pair/unpair never resets the shared two-second attempt policy.
	daedalus::photopdf::LaunchGate LaunchGate;
};
