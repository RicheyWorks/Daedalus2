// SPDX-License-Identifier: MIT
#pragma once

#include "CoreMinimal.h"
#include "UObject/Interface.h"
#include "DaedalusTideglassHost.generated.h"

/** Owned by the inventory/save host, not a second player inventory in the workshop. */
USTRUCT(BlueprintType)
struct FDaedalusTideglassState
{
	GENERATED_BODY()
	UPROPERTY(EditAnywhere, BlueprintReadWrite, SaveGame) int32 Version = 1;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, SaveGame) int64 Revision = 0;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, SaveGame) TMap<FString, int32> Items;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, SaveGame) bool bValveCrafted = false;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, SaveGame) bool bConduitOpen = false;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, SaveGame) bool bCommissionPaid = false;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, SaveGame) TMap<FString, FString> Receipts;
};

UENUM(BlueprintType)
enum class EDaedalusTideglassHostCommit : uint8
{
	Rejected, Committed, Uncertain
};

UINTERFACE(BlueprintType)
class DAEDALUSLINK_API UDaedalusTideglassHost : public UInterface
{
	GENERATED_BODY()
};

/** Implement on the existing authoritative inventory/save owner. Defaults refuse all work.
 * TryCommit must compare the entire expected snapshot and durably write items, revision,
 * consequence facts and operation receipt together before returning Committed. Rejected
 * guarantees no write; a lost/ambiguous save must return Uncertain. The host must serialize
 * all workshop instances and durably block further commits while any save is unresolved,
 * including after component recreation. SaveGame annotations
 * are a serialization contract, not a disk writer. Never infer finite water from a sip/tag. */
class DAEDALUSLINK_API IDaedalusTideglassHost
{
	GENERATED_BODY()
public:
	UFUNCTION(BlueprintNativeEvent, BlueprintCallable, Category = "Daedalus|Tideglass")
	bool ReadTideglassState(FDaedalusTideglassState& State) const;
	virtual bool ReadTideglassState_Implementation(FDaedalusTideglassState& State) const { return false; }

	UFUNCTION(BlueprintNativeEvent, BlueprintCallable, Category = "Daedalus|Tideglass")
	EDaedalusTideglassHostCommit TryCommitTideglassState(const FDaedalusTideglassState& Expected,
		const FDaedalusTideglassState& Proposed, const FString& OperationId);
	virtual EDaedalusTideglassHostCommit TryCommitTideglassState_Implementation(
		const FDaedalusTideglassState& Expected, const FDaedalusTideglassState& Proposed,
		const FString& OperationId) { return EDaedalusTideglassHostCommit::Rejected; }

	/** Shared host gate, including durable uncertainty holds; missing implementation refuses commits. */
	UFUNCTION(BlueprintNativeEvent, BlueprintCallable, Category = "Daedalus|Tideglass")
	bool CanCommitTideglassState() const;
	virtual bool CanCommitTideglassState_Implementation() const { return false; }

	/** A non-Orrery binding may expose its existing filter capability through this hook. */
	UFUNCTION(BlueprintNativeEvent, BlueprintCallable, Category = "Daedalus|Tideglass")
	bool HasCleanWaterForTideglass() const;
	virtual bool HasCleanWaterForTideglass_Implementation() const { return false; }

	/** Reconciliation evidence must come from committed durable storage, never an unsaved RAM copy.
	 * Confirm the exact receipt signature and revision on the same inventory/save host. */
	UFUNCTION(BlueprintNativeEvent, BlueprintCallable, Category = "Daedalus|Tideglass")
	bool ConfirmDurableTideglassReceipt(const FString& OperationId, const FString& Signature, int64 MinimumRevision) const;
	virtual bool ConfirmDurableTideglassReceipt_Implementation(const FString& OperationId,
		const FString& Signature, int64 MinimumRevision) const { return false; }
};
