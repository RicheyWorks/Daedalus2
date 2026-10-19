// SPDX-License-Identifier: MIT
#pragma once

#include "CoreMinimal.h"

/** A transient view of one desktop-approved job. No backend credentials or pairing token. */
struct FDaedalusFaxPreparationView
{
	FString Status;
	FString JobState;
	FString FaxId;
	FString Recipient;
	FString DocumentSha256;
	FString ExpiresAt;
	FString GrantExpiresAt;
	int32 PageCount = 0;
	int64 ByteCount = 0;
	bool bPaired = false;
	bool bBusy = false;
	bool bUncertain = false;
	bool bHasJob = false;
	bool bCanPair = true;
	bool bCanRefresh = false;
	bool bCanCancel = false;
	bool bCanExport = false;
	bool bCanDisconnect = false;
};

/** Read/cancel one existing prepared fax through its explicitly granted local companion.
 * All operations and Tick are game-thread-only. Requests are serial and bounded; completion
 * callbacks are lifetime/generation guarded on the game thread. No upload, preparation,
 * confirmation, transmission, backend login or owner-wide job list exists in this client.
 * Links, metadata and PDF bytes stay transient: never serialized, logged or replicated.
 */
class DAEDALUSLINK_API FDaedalusFaxPreparationClient
	: public TSharedFromThis<FDaedalusFaxPreparationClient, ESPMode::ThreadSafe>
{
public:
	FDaedalusFaxPreparationClient();
	~FDaedalusFaxPreparationClient();
	FDaedalusFaxPreparationView GetView() const;
	bool Pair(const FString& PairingLink);
	void Refresh();
	void CancelPreparation();
	/** Revoke only the local grant; this does not cancel the upstream job or delete uploads. */
	void Disconnect();
	void Shutdown();
	void Tick();
	/** Explicit PDF copy. Failure returns empty bytes and a generic error. Successful bytes
	 * pass MIME/length/SHA256/header/EOF checks and a fresh same-job status check. The desktop
	 * owns PDFBox page/structure validation; this client does not decode or sanitize a PDF.
	 */
	void Download(TFunction<void(TArray<uint8>&&, const FString&)> Completion);

private:
	class FImpl;
	TUniquePtr<FImpl> Impl;
};
