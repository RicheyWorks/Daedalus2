// SPDX-License-Identifier: MIT
#pragma once

#include "CoreMinimal.h"

/** Explicitly selected local bytes. Names are display-only and never enter the wire protocol. */
struct FDaedalusPhotoPdfImage
{
	uint8 Type = 0; // 1 = PNG, 2 = JPEG. The existing Java backend validates actual image content.
	TArray<uint8> Bytes;
	FString DisplayName;
};

/** Game-thread snapshot. Opening/pairing is not evidence that conversion or export succeeded. */
struct FDaedalusPhotoPdfView
{
	FString Status;
	FString JobState;
	FString JobId;
	TArray<FString> SelectedNames;
	int32 Total = 0;
	int32 Completed = 0;
	int32 OutputCount = 0;
	bool bPaired = false;
	bool bBusy = false;
	bool bUncertain = false;
	bool bCanPair = true;
	bool bCanSelect = false;
	bool bCanSubmit = false;
	bool bCanRefresh = false;
	bool bCanCancel = false;
	bool bCanExport = false;
	bool bCanDisconnect = false;
};

/** Native terminal for the running PhotosToPDFPC app, not a second PDF converter.
 * Construct/operate/Tick on the game thread. One bounded HTTP request runs on a pool worker;
 * no worker touches the client or a UObject. Tick consumes completions on the game thread.
 * Pairing capabilities, selected bytes and action keys are transient process memory only.
 */
class DAEDALUSLINK_API FDaedalusPhotoPdfClient
	: public TSharedFromThis<FDaedalusPhotoPdfClient, ESPMode::ThreadSafe>
{
public:
	FDaedalusPhotoPdfClient();
	~FDaedalusPhotoPdfClient();
	FDaedalusPhotoPdfView GetView() const;
	bool Pair(const FString& PairingLink);
	bool SetImages(TArray<FDaedalusPhotoPdfImage>&& Images);
	void SubmitOrRetry();
	void Refresh();
	void CancelJob();
	void Disconnect();
	void Shutdown();
	void Tick();
	/** 1-based output index. Completion runs on the game thread; failure has empty bytes.
	 * The caller chooses a local export destination. No paths or returned URLs are accepted here.
	 */
	void Download(int32 Index, TFunction<void(TArray<uint8>&&, const FString&)> Completion);

private:
	class FImpl;
	TUniquePtr<FImpl> Impl;
};
