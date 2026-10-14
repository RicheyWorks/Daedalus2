// SPDX-License-Identifier: MIT
#pragma once

#include "CoreMinimal.h"

/** Plain, local presentation of the desktop-selected card subset. Never persist or replicate. */
struct FDaedalusSynapseView
{
	FString Status;
	FString Prompt;
	FString Context;
	FString Answer;
	FString Kind;
	FString ReceiptSummary;
	int32 DueCount = 0;
	int32 SelectedCount = 0;
	bool bPaired = false;
	bool bBusy = false;
	bool bHasCard = false;
	bool bRevealed = false;
	bool bUncertain = false;
	bool bHasReceipt = false;
	bool bCanPair = true;
	bool bCanRefresh = false;
	bool bCanReveal = false;
	bool bCanScore = false;
	bool bCanRetry = false;
	bool bCanDisconnect = false;
};

/** Native selected-track interface to the existing Synapse StudyService.
 * All methods and Tick belong to the game thread; one bounded worker owns HTTP data only.
 * A score is sent only by explicit Score/RetrySameSave. Unknown saves retain the exact action
 * across disconnect/re-pair in this object's lifetime. Shutdown abandons that transient recovery
 * identity; revocation cannot undo a review that the desktop already committed.
 */
class DAEDALUSLINK_API FDaedalusSynapseClient
	: public TSharedFromThis<FDaedalusSynapseClient, ESPMode::ThreadSafe>
{
public:
	FDaedalusSynapseClient();
	~FDaedalusSynapseClient();
	FDaedalusSynapseView GetView() const;
	bool Pair(const FString& PairingLink);
	void Refresh();
	void Reveal();
	void Score(int32 Value);
	void RetrySameSave();
	void Disconnect();
	void Shutdown();
	void Tick();

private:
	class FImpl;
	TUniquePtr<FImpl> Impl;
};
