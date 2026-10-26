// SPDX-License-Identifier: MIT
#pragma once

#include "CoreMinimal.h"

/** Explicitly selected local bytes. Names remain display-only, outside the app protocol. */
struct FDaedalusImageOptimizerImage
{
	uint8 Type = 0; // 1 PNG, 2 JPEG; the existing app validates actual image content.
	TArray<uint8> Bytes;
	FString DisplayName;
};

struct FDaedalusImageOptimizerSettings
{
	int32 Quality = 85; // 70..95, encoder/format-specific; no file-size saving is promised.
	bool bResize = false;
	int32 Width = 1280; // 1..4096, required even when resize is disabled.
	uint8 Format = 0; // 0 keep each source type, 1 PNG, 2 JPEG (loses transparency).
};

struct FDaedalusImageOptimizerOutput
{
	int32 Index = 0; // 1-based, generated output name; never an arbitrary URL or path.
	uint8 Type = 0;
	int32 Width = 0;
	int32 Height = 0;
	int32 Bytes = 0;
	int32 SourceBytes = 0;
};

struct FDaedalusImageOptimizerView
{
	FString Status;
	FString JobState;
	FString JobId;
	TArray<FString> SelectedNames;
	FDaedalusImageOptimizerSettings Settings;
	TArray<FDaedalusImageOptimizerOutput> Outputs;
	int32 Total = 0;
	int32 Completed = 0;
	bool bPaired = false;
	bool bBusy = false;
	bool bUncertain = false;
	bool bCanPair = true;
	bool bCanSelect = false;
	bool bCanEditSettings = false;
	bool bCanSubmit = false;
	bool bCanRefresh = false;
	bool bCanCancel = false;
	bool bCanExport = false;
	bool bCanDisconnect = false;
};

/** Native byte/job client for the running Image Optimizer's existing Thumbnailator service.
 * All operations and Tick are game-thread-only. A serial bounded worker owns HTTP data;
 * completion/export callbacks are game-thread/lifetime/generation guarded. Credentials,
 * source bytes, settings and action keys are transient and never serialized or replicated.
 */
class DAEDALUSLINK_API FDaedalusImageOptimizerClient
	: public TSharedFromThis<FDaedalusImageOptimizerClient, ESPMode::ThreadSafe>
{
public:
	FDaedalusImageOptimizerClient();
	~FDaedalusImageOptimizerClient();
	FDaedalusImageOptimizerView GetView() const;
	bool Pair(const FString& PairingLink);
	bool SetImages(TArray<FDaedalusImageOptimizerImage>&& Images);
	bool SetSettings(const FDaedalusImageOptimizerSettings& Settings);
	void SubmitOrRetry();
	void Refresh();
	void CancelJob();
	void Disconnect();
	void Shutdown();
	void Tick();
	/** 1-based output; failure returns empty bytes, Type=0 and a generic message.
	 * Success validates wire metadata/MIME/header dimensions, not full pixel/metadata correctness.
	 * The separate local export helper chooses and safely creates the destination.
	 */
	void Download(int32 Index, TFunction<void(TArray<uint8>&&, uint8, const FString&)> Completion);

private:
	class FImpl;
	TUniquePtr<FImpl> Impl;
};
