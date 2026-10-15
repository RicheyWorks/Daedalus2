// SPDX-License-Identifier: MIT
#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "UObject/ScriptInterface.h"
#include "DaedalusTideglassHost.h"
#include "DaedalusTideglassWorkshopComponent.generated.h"

UENUM(BlueprintType)
enum class EDaedalusTideglassAction : uint8 { CraftValve, InstallValve, SupplyWater };

UENUM(BlueprintType)
enum class EDaedalusTideglassStatus : uint8
{
	Committed, AlreadyCommitted, Invalid, Insufficient, WrongWindow, UnsafeWeather,
	WaterUnavailable, PrerequisiteMissing, AlreadyComplete, Stale, Overflow, ReceiptLimit,
	Unbound, ReadFailed, NoClock, NoAuthority, HostRejected, CommitUncertain
};

USTRUCT(BlueprintType)
struct FDaedalusTideglassConfig
{
	GENERATED_BODY()
	FDaedalusTideglassConfig() { ValveInputs.Add(TEXT("copper_ingot"), 2); ValveInputs.Add(TEXT("charcoal"), 1); }
	/** Host maps these configured IDs to its existing item registry. Defaults are a fixture recipe. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite) TMap<FString, int32> ValveInputs;
	UPROPERTY(EditAnywhere, BlueprintReadWrite) FString ValveItem = TEXT("poot_pulse_valve");
	UPROPERTY(EditAnywhere, BlueprintReadWrite) FString WaterItem = TEXT("water");
	UPROPERTY(EditAnywhere, BlueprintReadWrite) FString RewardItem = TEXT("poot_harbor_credit");
	UPROPERTY(EditAnywhere, BlueprintReadWrite) int32 WaterUnits = 2;
	UPROPERTY(EditAnywhere, BlueprintReadWrite) int32 RewardUnits = 1;
	UPROPERTY(EditAnywhere, BlueprintReadWrite) double InstallStartHour = 6;
	UPROPERTY(EditAnywhere, BlueprintReadWrite) double InstallEndHour = 10;
};

USTRUCT(BlueprintType)
struct FDaedalusTideglassResult
{
	GENERATED_BODY()
	UPROPERTY(BlueprintReadOnly) EDaedalusTideglassStatus Status = EDaedalusTideglassStatus::Invalid;
	UPROPERTY(BlueprintReadOnly) EDaedalusTideglassAction Action = EDaedalusTideglassAction::CraftValve;
	UPROPERTY(BlueprintReadOnly) FString OperationId;
	UPROPERTY(BlueprintReadOnly) FString Message;
	UPROPERTY(BlueprintReadOnly) FString Cue;
	UPROPERTY(BlueprintReadOnly) TMap<FString, int32> Missing;
	UPROPERTY(BlueprintReadOnly) int64 Revision = -1;
};

DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FDaedalusTideglassFeedback, const FDaedalusTideglassResult&, Result);
DECLARE_DYNAMIC_MULTICAST_DELEGATE_TwoParams(FDaedalusTideglassConsequence, EDaedalusTideglassAction, Action,
	const FDaedalusTideglassState&, State);

/** Transaction/feedback adapter only: samples the shared clock, never owns a ledger or save file. */
UCLASS(ClassGroup = Daedalus, meta = (BlueprintSpawnableComponent))
class DAEDALUSLINK_API UDaedalusTideglassWorkshopComponent : public UActorComponent
{
	GENERATED_BODY()
public:
	UDaedalusTideglassWorkshopComponent();
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|Tideglass")
	TScriptInterface<IDaedalusTideglassHost> InventoryHost;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|Tideglass") FDaedalusTideglassConfig Config;
	/** Read Claude's existing filter flag, or use the explicitly bound host capability. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|Tideglass") bool bUseOrreryFilter = true;
	UPROPERTY(BlueprintAssignable, Category = "Daedalus|Tideglass") FDaedalusTideglassFeedback OnFeedback;
	/** Bind local conduit visuals/ecology effects here; fires only after a verified new commit. */
	UPROPERTY(BlueprintAssignable, Category = "Daedalus|Tideglass") FDaedalusTideglassConsequence OnConsequence;

	UFUNCTION(BlueprintCallable, Category = "Daedalus|Tideglass")
	FDaedalusTideglassResult TryAction(EDaedalusTideglassAction Action, const FString& OperationId);
	UFUNCTION(BlueprintCallable, Category = "Daedalus|Tideglass")
	bool ReadState(FDaedalusTideglassState& State) const;

private:
	FDaedalusTideglassResult Finish(FDaedalusTideglassResult Result);
	/** An uncertain host outcome blocks this adapter until the owner reconciles the durable receipt. */
	bool bNeedsReconciliation = false;
	FString UncertainOperation;
	FDaedalusTideglassState UncertainProposed;
	TWeakObjectPtr<UObject> UncertainHost;
public:
	/** Owner-supplied durable receipt evidence; this does not submit or replay a transaction. */
	UFUNCTION(BlueprintCallable, Category = "Daedalus|Tideglass")
	bool ReconcileCommittedOperation(const FString& OperationId);
};
