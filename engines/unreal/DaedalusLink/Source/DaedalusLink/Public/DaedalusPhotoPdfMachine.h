// SPDX-License-Identifier: MIT
#pragma once

#include "CoreMinimal.h"
#include "DaedalusOrrery.h"
#include "DaedalusPhotoPdfCore.h"
#include "DaedalusPhotoPdfMachine.generated.h"

/** Native interface state only. A browser launch never means a PDF was converted or downloaded. */
UENUM(BlueprintType)
enum class EDaedalusPhotoPdfState : uint8
{
	Unpaired,
	Paired,
	ChooserLaunched
};

/** A physical interface to the SAME local PhotosToPDFPC application, through Hero::Interact/Use.
 * The browser owns image selection, job status/cancellation and downloads. This actor handles no files,
 * uploads or server jobs. This pilot launches on Windows only; other platforms fail closed.
 * Claude/Blender can supply the final mesh and placement using the inherited Body.
 */
UCLASS(Blueprintable)
class DAEDALUSLINK_API ADaedalusPhotoPdfMachine : public ADaedalusUsable
{
	GENERATED_BODY()

public:
	ADaedalusPhotoPdfMachine();
	virtual FString Prompt(const ADaedalusHero* Hero) const override;
	virtual bool Use(ADaedalusHero* Hero) override;

	/** Pair only in a running game world, with the complete link copied from the user's local app.
	 * No default/editor/level property or RPC contains this capability. Invalid input clears any old pairing.
	 */
	UFUNCTION(BlueprintCallable, Category = "Daedalus|Practical Apps|Photo PDF")
	bool PairLocalApp(const FString& CapabilityLink);

	/** Forget the local capability. The browser/app's job cancellation remains in the app. */
	UFUNCTION(BlueprintCallable, Category = "Daedalus|Practical Apps|Photo PDF")
	void ClearRuntimePairing();

	UFUNCTION(BlueprintPure, Category = "Daedalus|Practical Apps|Photo PDF")
	EDaedalusPhotoPdfState GetChooserState() const { return ChooserState; }

protected:
	virtual void EndPlay(const EEndPlayReason::Type Reason) override;

private:
	bool CanUseLocally(const ADaedalusHero* Hero) const;

	// No editor exposure, getter, Config/SaveGame/replication, or text export. Copies/PIE duplicates start unpaired.
	UPROPERTY(Transient, DuplicateTransient, TextExportTransient)
	FString RuntimeCapabilityLink;

	UPROPERTY(Transient, DuplicateTransient, TextExportTransient)
	EDaedalusPhotoPdfState ChooserState = EDaedalusPhotoPdfState::Unpaired;

	daedalus::photopdf::LaunchGate LaunchGate;
};
