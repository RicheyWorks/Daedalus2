// SPDX-License-Identifier: MIT
#include "DaedalusPhotoPdfClient.h"

#include "DaedalusPhotoPdfCore.h"
#include "Async/Async.h"
#include "Dom/JsonObject.h"
#include "HAL/PlatformTime.h"
#include "Misc/Guid.h"
#include "Misc/ScopeLock.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"

THIRD_PARTY_INCLUDES_START
#include <curl/curl.h>
THIRD_PARTY_INCLUDES_END

namespace PhotoPdfWire
{
	constexpr int32 MaxFiles = 8;
	constexpr int32 MaxFileBytes = 8 * 1024 * 1024;
	constexpr int32 MaxBatchBytes = 24 * 1024 * 1024;
	constexpr int32 MaxJsonBytes = 32768;
	constexpr int32 MaxPdfBytes = 64 * 1024 * 1024;
	constexpr int32 MaxSessionSeconds = 900;

	enum class EOperation : uint8 { Capabilities, Session, Submit, Refresh, Cancel, Download, Revoke };

	bool Token(const FString& Value, int32 Minimum = 43, int32 Maximum = 43)
	{
		if (Value.Len() < Minimum || Value.Len() > Maximum) return false;
		for (TCHAR C : Value)
			if (!((C >= 'A' && C <= 'Z') || (C >= 'a' && C <= 'z') || (C >= '0' && C <= '9') || C == '_' || C == '-')) return false;
		return true;
	}

	bool Uuid(const FString& Value)
	{
		if (Value.Len() != 36) return false;
		for (int32 I = 0; I < Value.Len(); ++I)
		{
			const TCHAR C = Value[I];
			if (I == 8 || I == 13 || I == 18 || I == 23) { if (C != '-') return false; }
			else if (!((C >= '0' && C <= '9') || (C >= 'a' && C <= 'f'))) return false;
		}
		return true;
	}

	bool String(const TSharedPtr<FJsonObject>& Json, const TCHAR* Name, FString& Out, int32 Limit)
	{
		const TSharedPtr<FJsonValue>* Value = Json.IsValid() ? Json->Values.Find(Name) : nullptr;
		if (!Value || !Value->IsValid() || (*Value)->Type != EJson::String || !(*Value)->TryGetString(Out)
			|| Out.IsEmpty() || Out.Len() > Limit) return false;
		for (TCHAR C : Out) if (C == 0) return false;
		return true;
	}

	bool Integer(const TSharedPtr<FJsonObject>& Json, const TCHAR* Name, int32& Out, int32 Minimum, int32 Maximum)
	{
		double Number = 0;
		const TSharedPtr<FJsonValue>* Value = Json.IsValid() ? Json->Values.Find(Name) : nullptr;
		if (!Value || !Value->IsValid() || (*Value)->Type != EJson::Number || !(*Value)->TryGetNumber(Number)
			|| !FMath::IsFinite(Number) || Number < Minimum || Number > Maximum || FMath::FloorToDouble(Number) != Number) return false;
		Out = static_cast<int32>(Number);
		return true;
	}

	bool ExactInteger(const TSharedPtr<FJsonObject>& Json, const TCHAR* Name, int32 Expected)
	{
		int32 Value = 0;
		return Integer(Json, Name, Value, Expected, Expected);
	}

	TSharedPtr<FJsonObject> Parse(const TArray<uint8>& Bytes)
	{
		if (Bytes.IsEmpty() || Bytes.Num() > MaxJsonBytes) return nullptr;
		// Reject NUL and excessive nesting before the recursive engine JSON parser runs.
		int32 Depth = 0;
		bool bQuoted = false, bEscape = false;
		for (uint8 C : Bytes)
		{
			if (C == 0) return nullptr;
			if (bQuoted)
			{
				if (bEscape) bEscape = false;
				else if (C == '\\') bEscape = true;
				else if (C == '"') bQuoted = false;
			}
			else if (C == '"') bQuoted = true;
			else if (C == '{' || C == '[') { if (++Depth > 12) return nullptr; }
			else if (C == '}' || C == ']') { if (--Depth < 0) return nullptr; }
		}
		if (bQuoted || Depth != 0) return nullptr;
		const FUTF8ToTCHAR Converted(reinterpret_cast<const ANSICHAR*>(Bytes.GetData()), Bytes.Num());
		const FString Text(Converted.Length(), Converted.Get());
		TSharedPtr<FJsonObject> Json;
		return FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text), Json) ? Json : nullptr;
	}

	FString JobPath(const FString& Id) { return TEXT("/v1/jobs/") + Id; }
	FString OutputPath(const FString& Id, int32 Index) { return JobPath(Id) + TEXT("/outputs/") + FString::FromInt(Index); }

	struct FSnapshot
	{
		FString Id, State;
		int32 Total = 0, Completed = 0, Outputs = 0;
	};

	bool Snapshot(const TSharedPtr<FJsonObject>& Json, int32 ExpectedTotal, const FString& ExpectedId, FSnapshot& Out)
	{
		if (!String(Json, TEXT("id"), Out.Id, 36) || !Uuid(Out.Id)
			|| (!ExpectedId.IsEmpty() && Out.Id != ExpectedId)
			|| !String(Json, TEXT("state"), Out.State, 16)
			|| !Integer(Json, TEXT("total"), Out.Total, 1, MaxFiles) || Out.Total != ExpectedTotal
			|| !Integer(Json, TEXT("completed"), Out.Completed, 0, Out.Total)) return false;
		if (Out.State != TEXT("QUEUED") && Out.State != TEXT("RUNNING") && Out.State != TEXT("SUCCEEDED")
			&& Out.State != TEXT("FAILED") && Out.State != TEXT("CANCELED")) return false;
		const TArray<TSharedPtr<FJsonValue>>* Outputs = nullptr;
		if (!Json->TryGetArrayField(TEXT("outputs"), Outputs) || !Outputs || Outputs->Num() > MaxFiles) return false;
		if (Out.State == TEXT("SUCCEEDED"))
		{
			if (Out.Completed != Out.Total || Outputs->Num() != Out.Total) return false;
			for (int32 I = 0; I < Outputs->Num(); ++I)
			{
				const auto& Value = (*Outputs)[I];
				if (!Value.IsValid() || Value->Type != EJson::Object) return false;
				const auto Object = Value->AsObject();
				FString Name, Path;
				if (!ExactInteger(Object, TEXT("index"), I + 1)
					|| !String(Object, TEXT("name"), Name, 32) || Name != FString::Printf(TEXT("photo-%d.pdf"), I + 1)
					|| !String(Object, TEXT("downloadPath"), Path, 100) || Path != OutputPath(Out.Id, I + 1)) return false;
			}
			Out.Outputs = Outputs->Num();
		}
		else if (!Outputs->IsEmpty()) return false;
		// Error text is deliberately not propagated from a process into the terminal or logs.
		return true;
	}

	bool PdfEnvelope(const TArray<uint8>& Bytes)
	{
		// This is bounded wire/type validation, not a PDF parser or proof of page content.
		const uint8 Prefix[] = {'%', 'P', 'D', 'F', '-'};
		if (Bytes.Num() < 16 || Bytes.Num() > MaxPdfBytes || FMemory::Memcmp(Bytes.GetData(), Prefix, sizeof(Prefix)) != 0) return false;
		for (int32 I = FMath::Max(0, Bytes.Num() - 1024); I + 4 < Bytes.Num(); ++I)
			if (Bytes[I] == '%' && Bytes[I + 1] == '%' && Bytes[I + 2] == 'E' && Bytes[I + 3] == 'O' && Bytes[I + 4] == 'F') return true;
		return false;
	}

	void Append32(TArray<uint8>& Bytes, uint32 Value)
	{
		Bytes.Add(static_cast<uint8>(Value >> 24)); Bytes.Add(static_cast<uint8>(Value >> 16));
		Bytes.Add(static_cast<uint8>(Value >> 8)); Bytes.Add(static_cast<uint8>(Value));
	}

	FString DisplayName(const FString& Input, int32 Index)
	{
		// Never retain directories even if a caller accidentally supplies a full path.
		int32 Start = 0;
		for (int32 I = 0; I < Input.Len(); ++I) if (Input[I] == '/' || Input[I] == '\\') Start = I + 1;
		FString Result;
		for (int32 I = Start; I < Input.Len() && Result.Len() < 120; ++I)
			if (Input[I] >= 32 && Input[I] != 127) Result.AppendChar(Input[I]);
		return Result.IsEmpty() ? FString::Printf(TEXT("Photo %d"), Index) : Result;
	}
}

/** All mutable transport data belongs to this worker. Only atomics are read while it runs.
 * Tick reads response fields after bDone. No UObject, state callback, URL redirect, proxy,
 * returned path or curl diagnostic can escape into client/UI state.
 */
class FPhotoPdfHttpTask : public TSharedFromThis<FPhotoPdfHttpTask, ESPMode::ThreadSafe>
{
public:
	PhotoPdfWire::EOperation Operation = PhotoPdfWire::EOperation::Capabilities;
	uint64 Generation = 0;
	FString Url, Verb;
	TArray<FString> RequestHeaders;
	TSharedPtr<const TArray<uint8>, ESPMode::ThreadSafe> Body;
	TArray<uint8> Response;
	FString ContentType;
	int32 Limit = PhotoPdfWire::MaxJsonBytes;
	int32 StatusCode = 0;
	int32 TimeoutMilliseconds = 30000;
	SIZE_T HeaderBytes = 0;
	bool bTransportOk = false;
	bool bRedirect = false;
	TAtomic<bool> bCancelled{false};
	TAtomic<bool> bDone{false};

	static SIZE_T Write(char* Data, SIZE_T Size, SIZE_T Count, void* User)
	{
		auto* Task = static_cast<FPhotoPdfHttpTask*>(User);
		if (Task->bCancelled.Load() || (Count > 0 && Size > static_cast<SIZE_T>(Task->Limit) / Count)) return 0;
		const SIZE_T Bytes = Size * Count;
		if (Bytes > static_cast<SIZE_T>(Task->Limit - Task->Response.Num())) return 0;
		Task->Response.Append(reinterpret_cast<const uint8*>(Data), static_cast<int32>(Bytes));
		return Bytes;
	}

	static SIZE_T Header(char* Data, SIZE_T Size, SIZE_T Count, void* User)
	{
		auto* Task = static_cast<FPhotoPdfHttpTask*>(User);
		if (Task->bCancelled.Load() || (Count > 0 && Size > 8192 / Count)) return 0;
		const SIZE_T Bytes = Size * Count;
		if (Bytes > 8192 - Task->HeaderBytes) return 0;
		Task->HeaderBytes += Bytes;
		const FUTF8ToTCHAR Converted(Data, static_cast<int32>(Bytes));
		const FString Line(Converted.Length(), Converted.Get());
		if (Line.StartsWith(TEXT("Location:"), ESearchCase::IgnoreCase)) Task->bRedirect = true;
		if (Line.StartsWith(TEXT("Content-Type:"), ESearchCase::IgnoreCase))
		{
			FString Value = Line.Mid(13).TrimStartAndEnd().ToLower();
			int32 Semicolon = INDEX_NONE;
			if (Value.FindChar(';', Semicolon)) Value = Value.Left(Semicolon).TrimStartAndEnd();
			if (!Task->ContentType.IsEmpty() && Task->ContentType != Value) return 0;
			Task->ContentType = MoveTemp(Value);
		}
		return Bytes;
	}

	static int Progress(void* User, curl_off_t, curl_off_t, curl_off_t, curl_off_t)
	{
		return static_cast<FPhotoPdfHttpTask*>(User)->bCancelled.Load() ? 1 : 0;
	}

	void Run()
	{
		CURL* Curl = curl_easy_init();
		curl_slist* Headers = nullptr;
		if (Curl && !bCancelled.Load())
		{
			const FTCHARToUTF8 UrlUtf8(*Url), VerbUtf8(*Verb);
			bool bHeadersOk = true;
			for (const FString& Value : RequestHeaders)
			{
				curl_slist* Next = curl_slist_append(Headers, TCHAR_TO_UTF8(*Value));
				if (!Next) { bHeadersOk = false; break; }
				Headers = Next;
			}
			if (bHeadersOk)
			{
				bool bConfigured = true;
				auto Set = [Curl, &bConfigured](CURLoption Option, auto Value)
				{
					if (curl_easy_setopt(Curl, Option, Value) != CURLE_OK) bConfigured = false;
				};
				Set(CURLOPT_URL, UrlUtf8.Get());
				Set(CURLOPT_CUSTOMREQUEST, VerbUtf8.Get());
				Set(CURLOPT_HTTPHEADER, Headers);
				Set(CURLOPT_PROTOCOLS_STR, "http");
				Set(CURLOPT_PATH_AS_IS, 1L);
				Set(CURLOPT_FOLLOWLOCATION, 0L);
				Set(CURLOPT_MAXREDIRS, 0L);
				Set(CURLOPT_PROXY, "");
				Set(CURLOPT_NOPROXY, "*");
				Set(CURLOPT_NETRC, static_cast<long>(CURL_NETRC_IGNORED));
				Set(CURLOPT_VERBOSE, 0L);
				Set(CURLOPT_NOSIGNAL, 1L);
				Set(CURLOPT_CONNECTTIMEOUT_MS, 3000L);
				Set(CURLOPT_TIMEOUT_MS, static_cast<long>(TimeoutMilliseconds));
				Set(CURLOPT_WRITEFUNCTION, Write);
				Set(CURLOPT_WRITEDATA, this);
				Set(CURLOPT_HEADERFUNCTION, Header);
				Set(CURLOPT_HEADERDATA, this);
				Set(CURLOPT_NOPROGRESS, 0L);
				Set(CURLOPT_XFERINFOFUNCTION, Progress);
				Set(CURLOPT_XFERINFODATA, this);
				if (Verb != TEXT("GET"))
				{
					static const char Empty[] = "";
					const void* Data = Body.IsValid() && !Body->IsEmpty() ? Body->GetData() : static_cast<const void*>(Empty);
					Set(CURLOPT_POSTFIELDS, Data);
					Set(CURLOPT_POSTFIELDSIZE_LARGE, static_cast<curl_off_t>(Body.IsValid() ? Body->Num() : 0));
				}
				if (bConfigured)
				{
					const CURLcode Result = curl_easy_perform(Curl);
					long Code = 0;
					const CURLcode Info = curl_easy_getinfo(Curl, CURLINFO_RESPONSE_CODE, &Code);
					StatusCode = static_cast<int32>(Code);
					bTransportOk = Result == CURLE_OK && Info == CURLE_OK && !bCancelled.Load() && !bRedirect && Code >= 200 && Code <= 599;
				}
			}
		}
		if (Curl) curl_easy_cleanup(Curl);
		curl_slist_free_all(Headers);
		RequestHeaders.Reset(); Body.Reset(); Url.Reset();
		TSharedPtr<FPhotoPdfHttpTask, ESPMode::ThreadSafe> Cleanup;
		{
			FScopeLock Scope(&CleanupLock);
			bWireFinished = true;
			Cleanup = MoveTemp(FinalRevoke);
		}
		bDone.Store(true);
		// Destructor/shutdown cleanup is serialized after the active request; no client is captured.
		if (Cleanup.IsValid()) Cleanup->Run();
	}

	void RevokeAfter(const TSharedPtr<FPhotoPdfHttpTask, ESPMode::ThreadSafe>& Cleanup)
	{
		bool bStartNow = false;
		{
			FScopeLock Scope(&CleanupLock);
			if (bWireFinished) bStartNow = true;
			else FinalRevoke = Cleanup;
		}
		if (bStartNow) Async(EAsyncExecution::ThreadPool, [Cleanup]() { Cleanup->Run(); });
	}

private:
	FCriticalSection CleanupLock;
	bool bWireFinished = false;
	TSharedPtr<FPhotoPdfHttpTask, ESPMode::ThreadSafe> FinalRevoke;
};

class FDaedalusPhotoPdfClient::FImpl
{
public:
	struct FCallbackLifetime
	{
		TAtomic<uint64> Generation{1};
		TAtomic<bool> bStopped{false};
	};
	FDaedalusPhotoPdfView View;
	FString Origin, ProcessToken, SessionToken, SessionId, ActionKey;
	TSharedPtr<const TArray<uint8>, ESPMode::ThreadSafe> SelectedBody;
	TSharedPtr<FPhotoPdfHttpTask, ESPMode::ThreadSafe> Active;
	TFunction<void(TArray<uint8>&&, const FString&)> DownloadCompletion;
	TSharedRef<FCallbackLifetime, ESPMode::ThreadSafe> CallbackLifetime = MakeShared<FCallbackLifetime, ESPMode::ThreadSafe>();
	uint64 Generation = 1;
	double ExpiresAt = 0, NextPollAt = 0;
	bool bStopped = false, bAutoPoll = false, bRejected = false, bNotAdmitted = false;
	bool bCancelWanted = false, bCancelNeedsAttempt = false;
	bool bDisconnectWanted = false, bRevokeNeedsAttempt = false;
	bool bUnknownSessionCleanup = false;

	FImpl() { View.Status = TEXT("Pair with the private link from your running PhotosToPDFPC app."); }

	void Controls()
	{
		View.bBusy = Active.IsValid();
		const bool bConnected = !SessionToken.IsEmpty() && !bDisconnectWanted && !bStopped;
		View.bPaired = bConnected;
		View.bCanPair = !bStopped && !Active.IsValid() && Origin.IsEmpty();
		View.bCanDisconnect = !bStopped && !Origin.IsEmpty();
		View.bCanSelect = bConnected && !Active.IsValid() && ActionKey.IsEmpty() && View.JobId.IsEmpty();
		View.bCanSubmit = bConnected && !Active.IsValid() && SelectedBody.IsValid() && View.JobId.IsEmpty()
			&& !bCancelWanted && !bRejected;
		View.bCanRefresh = bConnected && !Active.IsValid() && !bCancelWanted
			&& (!View.JobId.IsEmpty() || (!ActionKey.IsEmpty() && View.bUncertain));
		// Cancel and Disconnect stay available while a bounded upload/download is in flight.
		View.bCanCancel = bConnected && (!ActionKey.IsEmpty() || !View.JobId.IsEmpty());
		View.bCanExport = bConnected && !Active.IsValid() && !bCancelWanted && !View.bUncertain
			&& View.JobState == TEXT("SUCCEEDED") && View.OutputCount > 0;
	}

	TSharedPtr<FPhotoPdfHttpTask, ESPMode::ThreadSafe> MakeRequest(PhotoPdfWire::EOperation Operation, const TCHAR* Verb, const FString& Path)
	{
		auto Task = MakeShared<FPhotoPdfHttpTask, ESPMode::ThreadSafe>();
		Task->Generation = Generation; Task->Operation = Operation; Task->Url = Origin + Path; Task->Verb = Verb;
		Task->RequestHeaders.Add(TEXT("Authorization: Bearer ") + ProcessToken);
		Task->RequestHeaders.Add(TEXT("Cache-Control: no-store"));
		Task->RequestHeaders.Add(TEXT("Accept: ") + FString(Operation == PhotoPdfWire::EOperation::Download ? TEXT("application/pdf") : TEXT("application/json")));
		if (!SessionToken.IsEmpty()) Task->RequestHeaders.Add(TEXT("X-Session-Token: ") + SessionToken);
		return Task;
	}

	void Start(const TSharedPtr<FPhotoPdfHttpTask, ESPMode::ThreadSafe>& Task)
	{
		check(!Active.IsValid());
		Active = Task;
		Async(EAsyncExecution::ThreadPool, [Task]() { Task->Run(); });
		Controls();
	}

	void FinishDownload(TArray<uint8>&& Bytes, const FString& Error)
	{
		if (!DownloadCompletion) return;
		auto Completion = MoveTemp(DownloadCompletion);
		const auto Lifetime = CallbackLifetime;
		const uint64 ExpectedGeneration = Generation;
		// Defer external code until state transitions finish. The independent generation fence also
		// stops already queued successful bytes reaching an exporter after cancel/close/disconnect.
		AsyncTask(ENamedThreads::GameThread,
			[Completion = MoveTemp(Completion), Bytes = MoveTemp(Bytes), Error, Lifetime, ExpectedGeneration]() mutable
			{
				if (Lifetime->bStopped.Load() || Lifetime->Generation.Load() != ExpectedGeneration)
				{
					Bytes.Reset();
					Completion({}, TEXT("The photo action changed or the terminal closed. Nothing was exported."));
				}
				else Completion(MoveTemp(Bytes), Error);
			});
	}

	void InvalidateCompletions()
	{
		++Generation;
		CallbackLifetime->Generation.Store(Generation);
	}

	void ResetAction()
	{
		ActionKey.Reset(); View.JobId.Reset(); View.JobState.Reset();
		View.Completed = 0; View.OutputCount = 0; View.bUncertain = false;
		bRejected = false; bNotAdmitted = false; bAutoPoll = false; bCancelWanted = false; bCancelNeedsAttempt = false;
	}

	void ForgetSession(const FString& Status)
	{
		InvalidateCompletions();
		Origin.Reset(); ProcessToken.Reset(); SessionToken.Reset(); SessionId.Reset();
		SelectedBody.Reset(); View.SelectedNames.Reset(); View.Total = 0;
		ResetAction(); bDisconnectWanted = false; bRevokeNeedsAttempt = false;
		bUnknownSessionCleanup = false; ExpiresAt = 0;
		View.Status = Status;
		Controls();
	}

	bool JsonResponse(const FPhotoPdfHttpTask& Task) const
	{
		return Task.bTransportOk && Task.ContentType == TEXT("application/json");
	}

	bool HasError(const FPhotoPdfHttpTask& Task, const TCHAR* Expected) const
	{
		FString Error;
		return JsonResponse(Task) && PhotoPdfWire::String(PhotoPdfWire::Parse(Task.Response), TEXT("error"), Error, 64) && Error == Expected;
	}

	bool SessionGone(const FPhotoPdfHttpTask& Task) const
	{
		return Task.StatusCode == 401 && (HasError(Task, TEXT("SESSION_REQUIRED")) || HasError(Task, TEXT("UNAUTHORIZED")));
	}

	void Submit()
	{
		if (ActionKey.IsEmpty()) ActionKey = FGuid::NewGuid().ToString(EGuidFormats::DigitsWithHyphensLower);
		bNotAdmitted = false; // A retry can be admitted even when an earlier queue rejection was confirmed.
		auto Task = MakeRequest(PhotoPdfWire::EOperation::Submit, TEXT("POST"), TEXT("/v1/jobs"));
		Task->Body = SelectedBody;
		Task->RequestHeaders.Add(TEXT("Content-Type: application/octet-stream"));
		Task->RequestHeaders.Add(TEXT("Idempotency-Key: ") + ActionKey);
		Task->RequestHeaders.Add(TEXT("Expect:"));
		View.Status = bCancelWanted ? TEXT("Recovering the same action before cancellation...") : TEXT("Submitting the selected photos to PhotosToPDFPC...");
		Start(Task);
	}

	void AdvanceIntent()
	{
		if (bStopped || Active.IsValid()) return;
		if (bDisconnectWanted && bRevokeNeedsAttempt)
		{
			bRevokeNeedsAttempt = false;
			if (!SessionToken.IsEmpty())
			{
				View.Status = TEXT("Revoking this session and its temporary jobs...");
				Start(MakeRequest(PhotoPdfWire::EOperation::Revoke, TEXT("DELETE"), TEXT("/v1/sessions")));
			}
			else
			{
				const bool Unknown = bUnknownSessionCleanup;
				ForgetSession(Unknown
					? TEXT("Disconnected locally. Session creation was unconfirmed; any temporary session expires within 15 minutes after the request ended.")
					: TEXT("Disconnected. No photo session was created."));
			}
		}
		else if (bCancelWanted && bCancelNeedsAttempt)
		{
			bCancelNeedsAttempt = false;
			if (!View.JobId.IsEmpty())
			{
				View.Status = TEXT("Canceling the job and removing its temporary outputs...");
				Start(MakeRequest(PhotoPdfWire::EOperation::Cancel, TEXT("DELETE"), PhotoPdfWire::JobPath(View.JobId)));
			}
			else if (bRejected || bNotAdmitted)
			{
				// An unaccepted body has no UUID to delete. Session revocation confirms release of every key.
				bDisconnectWanted = true; bRevokeNeedsAttempt = true; AdvanceIntent();
			}
			else if (!ActionKey.IsEmpty() && SelectedBody.IsValid()) Submit();
		}
		Controls();
	}

	void ApplySnapshot(const PhotoPdfWire::FSnapshot& Snapshot)
	{
		View.JobId = Snapshot.Id; View.JobState = Snapshot.State; View.Total = Snapshot.Total;
		View.Completed = Snapshot.Completed; View.OutputCount = Snapshot.Outputs;
		View.bUncertain = false; bRejected = false; bNotAdmitted = false;
		bAutoPoll = Snapshot.State == TEXT("QUEUED") || Snapshot.State == TEXT("RUNNING");
		NextPollAt = FPlatformTime::Seconds() + 1.0;
		if (Snapshot.State == TEXT("SUCCEEDED")) View.Status = TEXT("Conversion complete. Export each PDF, then cancel this action before selecting another batch.");
		else if (Snapshot.State == TEXT("FAILED")) View.Status = TEXT("PhotosToPDFPC could not convert this batch. Cancel the action before changing photos.");
		else if (Snapshot.State == TEXT("CANCELED")) View.Status = TEXT("The job is canceled. Confirm removal with Cancel, or disconnect.");
		else View.Status = TEXT("PhotosToPDFPC is converting the selected photos...");
	}

	void Complete(const TSharedPtr<FPhotoPdfHttpTask, ESPMode::ThreadSafe>& Task)
	{
		using namespace PhotoPdfWire;
		const bool bStale = Task->Generation != Generation;
		// A session response received during disconnect still supplies the capability needed to revoke it.
		if (Task->Operation == EOperation::Session)
		{
			const auto Json = JsonResponse(*Task) ? Parse(Task->Response) : nullptr;
			FString Id, TokenValue;
			int32 Seconds = 0;
			if (Task->StatusCode == 201 && String(Json, TEXT("sessionId"), Id, 36) && Uuid(Id)
				&& String(Json, TEXT("sessionToken"), TokenValue, 43) && Token(TokenValue)
				&& Integer(Json, TEXT("expiresInSeconds"), Seconds, 1, MaxSessionSeconds))
			{
				SessionId = MoveTemp(Id); SessionToken = MoveTemp(TokenValue);
				ExpiresAt = FPlatformTime::Seconds() + Seconds;
				bUnknownSessionCleanup = false;
				View.Status = TEXT("Connected to PhotosToPDFPC. Select PNG or JPEG photos to begin.");
			}
			else
			{
				// A lost response may have created a session. Never claim its cleanup or silently retry creation.
				bUnknownSessionCleanup = true;
				View.Status = TEXT("Session creation was not confirmed. Disconnect locally; an unknown temporary session may remain until expiry.");
			}
			AdvanceIntent(); Controls(); return;
		}
		if (bStale) { AdvanceIntent(); Controls(); return; }
		if (Task->Operation != EOperation::Capabilities && SessionGone(*Task))
		{
			ForgetSession(TEXT("The companion no longer authorizes this session. Access is revoked; temporary-file cleanup is handled by the app."));
			FinishDownload({}, TEXT("The photo session is no longer authorized."));
			return;
		}

		switch (Task->Operation)
		{
		case EOperation::Capabilities:
		{
			const auto Json = JsonResponse(*Task) && Task->StatusCode == 200 ? Parse(Task->Response) : nullptr;
			FString Protocol, Mode;
			int32 Seconds = 0;
			if (!String(Json, TEXT("protocol"), Protocol, 32) || Protocol != TEXT("photospdf.local.v1")
				|| !String(Json, TEXT("outputMode"), Mode, 32) || Mode != TEXT("one_pdf_per_photo")
				|| !ExactInteger(Json, TEXT("maxFiles"), MaxFiles) || !ExactInteger(Json, TEXT("maxFileBytes"), MaxFileBytes)
				|| !ExactInteger(Json, TEXT("maxBatchBytes"), MaxBatchBytes) || !ExactInteger(Json, TEXT("maxDimension"), 4096)
				|| !ExactInteger(Json, TEXT("maxPixelsPerPhoto"), 12000000) || !ExactInteger(Json, TEXT("maxPixelsPerBatch"), 24000000)
				|| !Integer(Json, TEXT("sessionTtlSeconds"), Seconds, 1, MaxSessionSeconds))
			{
				ForgetSession(TEXT("PhotosToPDFPC could not be verified at this link. No photo session was requested."));
				break;
			}
			bUnknownSessionCleanup = true;
			View.Status = TEXT("Opening a private PhotosToPDFPC session...");
			Start(MakeRequest(EOperation::Session, TEXT("POST"), TEXT("/v1/sessions")));
			break;
		}
		case EOperation::Submit:
		case EOperation::Refresh:
		{
			FSnapshot SnapshotValue;
			if (JsonResponse(*Task) && (Task->StatusCode == 200 || (Task->Operation == EOperation::Submit && Task->StatusCode == 202))
				&& Snapshot(Parse(Task->Response), View.Total, View.JobId, SnapshotValue))
			{
				ApplySnapshot(SnapshotValue);
				if (bCancelWanted) bCancelNeedsAttempt = true;
			}
			else
			{
				bAutoPoll = false;
				View.OutputCount = 0;
				if (Task->Operation == EOperation::Submit)
				{
					// Generic INVALID_REQUEST can arise from an IO failure after server-side acceptance.
					// Only these explicit pre-admission failures establish rejection of this body.
					const bool Rejected = (Task->StatusCode == 400 && HasError(*Task, TEXT("IDEMPOTENCY_KEY_REQUIRED")))
						|| (Task->StatusCode == 413 && HasError(*Task, TEXT("BODY_LIMIT")))
						|| (Task->StatusCode == 415 && HasError(*Task, TEXT("BINARY_BATCH_REQUIRED")))
						|| (Task->StatusCode == 422 && HasError(*Task, TEXT("INVALID_IMAGE_BATCH")));
					const bool QueueRejected = Task->StatusCode == 429 && (HasError(*Task, TEXT("QUEUE_FULL")) || HasError(*Task, TEXT("JOB_LIMIT")));
					bRejected = Rejected; bNotAdmitted = Rejected || QueueRejected; View.bUncertain = !bNotAdmitted;
					if (Rejected) View.Status = TEXT("The app rejected this batch. Cancel or disconnect before selecting different photos.");
					else if (QueueRejected) View.Status = TEXT("The app's queue is full. Retry this same batch later, cancel, or disconnect.");
					else View.Status = TEXT("Submission outcome is unknown. Retry the same frozen action, cancel to reconcile it, or disconnect. Do not start a new batch.");
					if (bCancelWanted && bNotAdmitted) bCancelNeedsAttempt = true;
				}
				else
				{
					View.bUncertain = true;
					View.Status = TEXT("Job status was not confirmed. Refresh, cancel, or disconnect; no PDF is available for export yet.");
				}
			}
			break;
		}
		case EOperation::Cancel:
		{
			const auto Json = JsonResponse(*Task) ? Parse(Task->Response) : nullptr;
			FString Id, State;
			const bool bDeleted = Task->StatusCode == 200 && String(Json, TEXT("id"), Id, 36) && Id == View.JobId
				&& String(Json, TEXT("state"), State, 16) && State == TEXT("CANCELED");
			const bool bAlreadyGone = Task->StatusCode == 404 && HasError(*Task, TEXT("NOT_FOUND"));
			if (bDeleted || bAlreadyGone)
			{
				ResetAction();
				SelectedBody.Reset(); View.SelectedNames.Reset(); View.Total = 0;
				View.Status = TEXT("Job access and its action key are removed. The app cleans temporary outputs as open handles close. Select a new batch.");
			}
			else
			{
				View.bUncertain = true; View.OutputCount = 0; bAutoPoll = false;
				View.Status = TEXT("Cancellation was not confirmed. Retry Cancel or disconnect; the action and its bytes remain frozen.");
			}
			break;
		}
		case EOperation::Download:
			if (Task->bTransportOk && Task->StatusCode == 200 && Task->ContentType == TEXT("application/pdf") && PdfEnvelope(Task->Response))
			{
				View.Status = TEXT("PDF bytes downloaded. Choose a destination to export the copy.");
				FinishDownload(MoveTemp(Task->Response), FString());
			}
			else
			{
				View.Status = TEXT("The PDF download failed validation or was interrupted. No export was reported.");
				FinishDownload({}, TEXT("The PDF download was not confirmed. Nothing was exported."));
			}
			break;
		case EOperation::Revoke:
		{
			FString State;
			if (JsonResponse(*Task) && Task->StatusCode == 200 && String(Parse(Task->Response), TEXT("state"), State, 16) && State == TEXT("DELETED"))
				ForgetSession(TEXT("Session revoked. The app removes its jobs and cleans temporary files as active handles close."));
			else
			{
				View.Status = TEXT("Session revocation was not confirmed. Retry Disconnect. Access and temporary-file cleanup may remain until the app's 15-minute session expiry.");
				View.bUncertain = true;
			}
			break;
		}
		default: break;
		}
		AdvanceIntent(); Controls();
	}
};

FDaedalusPhotoPdfClient::FDaedalusPhotoPdfClient() : Impl(MakeUnique<FImpl>()) {}
FDaedalusPhotoPdfClient::~FDaedalusPhotoPdfClient() { Shutdown(); }

FDaedalusPhotoPdfView FDaedalusPhotoPdfClient::GetView() const
{
	check(IsInGameThread());
	return Impl->View;
}

bool FDaedalusPhotoPdfClient::Pair(const FString& PairingLink)
{
	check(IsInGameThread());
	Impl->Controls();
	if (!Impl->View.bCanPair) return false;
	const FTCHARToUTF8 Link(*PairingLink, PairingLink.Len());
	if (!daedalus::photopdf::IsValidChooserLink(std::string_view(Link.Get(), Link.Length())))
	{
		Impl->View.Status = TEXT("Use the literal loopback pairing link from PhotosToPDFPC.");
		return false;
	}
	int32 Fragment = INDEX_NONE;
	if (!PairingLink.FindChar('#', Fragment)) return false;
	Impl->InvalidateCompletions();
	Impl->Origin = PairingLink.Left(Fragment - 1); // Validated grammar has exactly /#token=.
	Impl->ProcessToken = PairingLink.Mid(Fragment + 7);
	Impl->View.Status = TEXT("Verifying PhotosToPDFPC's local capabilities...");
	Impl->Start(Impl->MakeRequest(PhotoPdfWire::EOperation::Capabilities, TEXT("GET"), TEXT("/v1/capabilities")));
	return true;
}

bool FDaedalusPhotoPdfClient::SetImages(TArray<FDaedalusPhotoPdfImage>&& Images)
{
	check(IsInGameThread());
	Impl->Controls();
	if (!Impl->View.bCanSelect) return false;
	if (Images.IsEmpty() || Images.Num() > PhotoPdfWire::MaxFiles)
	{
		Impl->View.Status = TEXT("Select between one and eight PNG or JPEG photos."); return false;
	}
	int64 TotalBytes = 8;
	for (const auto& Image : Images)
	{
		TotalBytes += 5LL + Image.Bytes.Num();
		if ((Image.Type != 1 && Image.Type != 2) || Image.Bytes.IsEmpty() || Image.Bytes.Num() > PhotoPdfWire::MaxFileBytes
			|| TotalBytes > PhotoPdfWire::MaxBatchBytes)
		{
			Impl->View.Status = TEXT("Use PNG or JPEG bytes, at most 8 MiB per photo and 24 MiB including batch framing."); return false;
		}
	}
	auto Body = MakeShared<TArray<uint8>, ESPMode::ThreadSafe>();
	Body->Reserve(static_cast<int32>(TotalBytes));
	Body->Append(reinterpret_cast<const uint8*>("PTP1"), 4);
	PhotoPdfWire::Append32(*Body, static_cast<uint32>(Images.Num()));
	TArray<FString> Names;
	for (int32 I = 0; I < Images.Num(); ++I)
	{
		auto& Image = Images[I];
		Body->Add(Image.Type); PhotoPdfWire::Append32(*Body, static_cast<uint32>(Image.Bytes.Num())); Body->Append(Image.Bytes);
		Names.Add(PhotoPdfWire::DisplayName(Image.DisplayName, I + 1));
		Image.Bytes.Reset(); Image.DisplayName.Reset();
	}
	Impl->SelectedBody = Body; Impl->View.SelectedNames = MoveTemp(Names); Impl->View.Total = Images.Num();
	Impl->View.Status = TEXT("Photos selected locally. Submit to convert with the existing PhotosToPDFPC app.");
	Impl->Controls();
	return true;
}

void FDaedalusPhotoPdfClient::SubmitOrRetry()
{
	check(IsInGameThread());
	Impl->Controls();
	if (Impl->View.bCanSubmit) Impl->Submit();
}

void FDaedalusPhotoPdfClient::Refresh()
{
	check(IsInGameThread());
	Impl->Controls();
	if (!Impl->View.bCanRefresh) return;
	if (Impl->View.JobId.IsEmpty()) Impl->Submit(); // Same immutable action key and PTP1 bytes.
	else
	{
		Impl->View.Status = TEXT("Refreshing the current photo job...");
		Impl->Start(Impl->MakeRequest(PhotoPdfWire::EOperation::Refresh, TEXT("GET"), PhotoPdfWire::JobPath(Impl->View.JobId)));
	}
}

void FDaedalusPhotoPdfClient::CancelJob()
{
	check(IsInGameThread());
	if (Impl->bStopped || Impl->SessionToken.IsEmpty() || Impl->bDisconnectWanted
		|| (Impl->ActionKey.IsEmpty() && Impl->View.JobId.IsEmpty())) return;
	Impl->InvalidateCompletions(); Impl->bCancelWanted = true; Impl->bCancelNeedsAttempt = true; Impl->bAutoPoll = false;
	Impl->View.OutputCount = 0;
	if (Impl->Active.IsValid()) Impl->Active->bCancelled.Store(true);
	Impl->FinishDownload({}, TEXT("The download was canceled. Nothing was exported."));
	Impl->View.Status = TEXT("Cancellation requested. Server removal has not yet been confirmed.");
	Impl->AdvanceIntent(); Impl->Controls();
}

void FDaedalusPhotoPdfClient::Disconnect()
{
	check(IsInGameThread());
	if (Impl->bStopped || Impl->Origin.IsEmpty()) return;
	Impl->InvalidateCompletions(); Impl->bDisconnectWanted = true; Impl->bRevokeNeedsAttempt = true; Impl->bAutoPoll = false;
	Impl->View.OutputCount = 0;
	if (Impl->Active.IsValid()) Impl->Active->bCancelled.Store(true);
	Impl->FinishDownload({}, TEXT("The photo session is disconnecting. Nothing was exported."));
	Impl->View.Status = TEXT("Disconnect requested. Session revocation is still pending.");
	Impl->AdvanceIntent(); Impl->Controls();
}

void FDaedalusPhotoPdfClient::Shutdown()
{
	if (!Impl.IsValid() || Impl->bStopped) return;
	Impl->bStopped = true; Impl->InvalidateCompletions(); Impl->bAutoPoll = false;
	Impl->CallbackLifetime->bStopped.Store(true);
	Impl->FinishDownload({}, TEXT("The photo terminal closed. Nothing was exported."));
	TSharedPtr<FPhotoPdfHttpTask, ESPMode::ThreadSafe> Cleanup;
	if (!Impl->SessionToken.IsEmpty())
	{
		Cleanup = Impl->MakeRequest(PhotoPdfWire::EOperation::Revoke, TEXT("DELETE"), TEXT("/v1/sessions"));
		Cleanup->TimeoutMilliseconds = 3000;
	}
	if (Impl->Active.IsValid())
	{
		if (Cleanup.IsValid()) Impl->Active->RevokeAfter(Cleanup);
		Impl->Active->bCancelled.Store(true);
		Impl->Active.Reset();
	}
	else if (Cleanup.IsValid()) Async(EAsyncExecution::ThreadPool, [Cleanup]() { Cleanup->Run(); });
	Impl->ForgetSession(TEXT("Terminal closed. Revocation was best effort and is unconfirmed; the app expires remaining sessions within 15 minutes."));
	Impl->Controls();
}

void FDaedalusPhotoPdfClient::Tick()
{
	check(IsInGameThread());
	if (Impl->bStopped) return;
	if (Impl->Active.IsValid() && Impl->Active->bDone.Load())
	{
		auto Task = MoveTemp(Impl->Active);
		Impl->Complete(Task);
	}
	const double Now = FPlatformTime::Seconds();
	if (!Impl->SessionToken.IsEmpty() && !Impl->bDisconnectWanted && Impl->ExpiresAt > 0 && Now >= Impl->ExpiresAt)
	{
		Disconnect(); // Ask the app to revoke; never infer disk cleanup from a local clock.
	}
	if (Impl->bAutoPoll && !Impl->Active.IsValid() && !Impl->bCancelWanted && !Impl->bDisconnectWanted
		&& !Impl->View.JobId.IsEmpty() && Now >= Impl->NextPollAt) Refresh();
	Impl->Controls();
}

void FDaedalusPhotoPdfClient::Download(int32 Index, TFunction<void(TArray<uint8>&&, const FString&)> Completion)
{
	check(IsInGameThread());
	Impl->Controls();
	if (!Impl->View.bCanExport || Index < 1 || Index > Impl->View.OutputCount)
	{
		if (Completion) Completion({}, TEXT("No completed PDF is available at this index."));
		return;
	}
	Impl->DownloadCompletion = MoveTemp(Completion);
	auto Task = Impl->MakeRequest(PhotoPdfWire::EOperation::Download, TEXT("GET"), PhotoPdfWire::OutputPath(Impl->View.JobId, Index));
	Task->Limit = PhotoPdfWire::MaxPdfBytes;
	Impl->View.Status = TEXT("Downloading a PDF copy from the current photo job...");
	Impl->Start(Task);
}
