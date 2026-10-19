// SPDX-License-Identifier: MIT
#include "DaedalusFaxPreparationClient.h"

#include "Async/Async.h"
#include "Dom/JsonObject.h"
#include "HAL/PlatformTime.h"
#include "Misc/DateTime.h"
#include "Misc/ScopeLock.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"

THIRD_PARTY_INCLUDES_START
#include <curl/curl.h>
#include <openssl/sha.h>
THIRD_PARTY_INCLUDES_END

namespace FaxPreparationWire
{
	constexpr int32 MaxJsonBytes = 8192;
	constexpr int32 MaxPdfBytes = 25 * 1024 * 1024;
	constexpr int32 MaxPages = 100;
	enum class EOperation : uint8 { Capabilities, Job, BeforeDownload, Document, AfterDownload, Cancel, Revoke };

	bool Exact(const FString& Left, const FString& Right)
	{
		return Left.Len() == Right.Len() && (Left.IsEmpty()
			|| FMemory::Memcmp(*Left, *Right, static_cast<SIZE_T>(Left.Len()) * sizeof(TCHAR)) == 0);
	}
	bool String(const TSharedPtr<FJsonObject>& Json, const TCHAR* Name, FString& Out, int32 Maximum)
	{
		const auto* Field = Json.IsValid() ? Json->Values.Find(Name) : nullptr;
		if (!Field || !Field->IsValid() || (*Field)->Type != EJson::String || !(*Field)->TryGetString(Out)
			|| Out.IsEmpty() || Out.Len() > Maximum) return false;
		for (TCHAR C : Out) if (C == 0) return false;
		return true;
	}
	bool Integer(const TSharedPtr<FJsonObject>& Json, const TCHAR* Name, int32& Out, int32 Minimum, int32 Maximum)
	{
		double Number = 0;
		const auto* Field = Json.IsValid() ? Json->Values.Find(Name) : nullptr;
		if (!Field || !Field->IsValid() || (*Field)->Type != EJson::Number || !(*Field)->TryGetNumber(Number)
			|| !FMath::IsFinite(Number) || Number < Minimum || Number > Maximum || FMath::FloorToDouble(Number) != Number) return false;
		Out = static_cast<int32>(Number); return true;
	}
	bool Utf8(const TArray<uint8>& Bytes)
	{
		for (int32 I = 0; I < Bytes.Num();)
		{
			const uint8 Lead = Bytes[I++];
			if (Lead < 0x80) { if (Lead == 0) return false; continue; }
			int32 Count = 0; uint32 Codepoint = 0, Minimum = 0;
			if (Lead >= 0xc2 && Lead <= 0xdf) { Count = 1; Codepoint = Lead & 0x1f; Minimum = 0x80; }
			else if (Lead >= 0xe0 && Lead <= 0xef) { Count = 2; Codepoint = Lead & 0x0f; Minimum = 0x800; }
			else if (Lead >= 0xf0 && Lead <= 0xf4) { Count = 3; Codepoint = Lead & 0x07; Minimum = 0x10000; }
			else return false;
			if (Count > Bytes.Num() - I) return false;
			while (Count-- > 0)
			{
				const uint8 Next = Bytes[I++]; if ((Next & 0xc0) != 0x80) return false;
				Codepoint = (Codepoint << 6) | (Next & 0x3f);
			}
			if (Codepoint < Minimum || Codepoint > 0x10ffff || (Codepoint >= 0xd800 && Codepoint <= 0xdfff)) return false;
		}
		return true;
	}
	TSharedPtr<FJsonObject> Parse(const TArray<uint8>& Bytes)
	{
		if (Bytes.IsEmpty() || Bytes.Num() > MaxJsonBytes || !Utf8(Bytes)) return nullptr;
		int32 Depth = 0; bool bQuoted = false, bEscape = false;
		for (uint8 C : Bytes)
		{
			if (bQuoted)
			{
				if (bEscape) bEscape = false;
				else if (C == '\\') bEscape = true;
				else if (C == '"') bQuoted = false;
			}
			else if (C == '"') bQuoted = true;
			else if (C == '{' || C == '[') { if (++Depth > 8) return nullptr; }
			else if (C == '}' || C == ']') { if (--Depth < 0) return nullptr; }
		}
		if (bQuoted || Depth != 0) return nullptr;
		const FUTF8ToTCHAR Converted(reinterpret_cast<const ANSICHAR*>(Bytes.GetData()), Bytes.Num());
		TSharedPtr<FJsonObject> Json;
		return FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(FString(Converted.Length(), Converted.Get())), Json) ? Json : nullptr;
	}
	bool Token(const FString& Value)
	{
		if (Value.Len() != 43) return false;
		for (TCHAR C : Value)
			if (!((C >= 'A' && C <= 'Z') || (C >= 'a' && C <= 'z') || (C >= '0' && C <= '9') || C == '_' || C == '-')) return false;
		return true;
	}
	bool Link(const FString& Value, FString& Origin, FString& Capability)
	{
		const FString Prefix(TEXT("http://127.0.0.1:")), Suffix(TEXT("/realm/fax-preparation/#token="));
		if (Value.Len() > 256 || !Value.StartsWith(Prefix, ESearchCase::CaseSensitive)) return false;
		const int32 At = Value.Find(Suffix, ESearchCase::CaseSensitive);
		if (At <= Prefix.Len() || At > Prefix.Len() + 5) return false;
		const FString Port = Value.Mid(Prefix.Len(), At - Prefix.Len());
		if (Port[0] == '0') return false;
		int32 Number = 0;
		for (TCHAR C : Port) { if (C < '0' || C > '9') return false; Number = Number * 10 + C - '0'; }
		if (Number < 1 || Number > 65535) return false;
		Capability = Value.Mid(At + Suffix.Len());
		if (!Token(Capability)) { Capability.Reset(); return false; }
		Origin = Value.Left(At); return true;
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
	bool Digest(const FString& Value)
	{
		if (Value.Len() != 64) return false;
		for (TCHAR C : Value) if (!((C >= '0' && C <= '9') || (C >= 'a' && C <= 'f'))) return false;
		return true;
	}
	bool Recipient(const FString& Value)
	{
		if (Value.Len() < 9 || Value.Len() > 16 || Value[0] != '+' || Value[1] < '1' || Value[1] > '9') return false;
		for (int32 I = 2; I < Value.Len(); ++I) if (Value[I] < '0' || Value[I] > '9') return false;
		return true;
	}
	bool Instant(const FString& Value, FDateTime& Out)
	{
		// Java Instant.toString UTC grammar, up to nanoseconds. Reject loose parser alternatives.
		if (Value.Len() < 20 || Value.Len() > 30 || Value[4] != '-' || Value[7] != '-' || Value[10] != 'T'
			|| Value[13] != ':' || Value[16] != ':' || Value[Value.Len() - 1] != 'Z') return false;
		for (int32 I = 0; I < 19; ++I)
			if (I != 4 && I != 7 && I != 10 && I != 13 && I != 16 && (Value[I] < '0' || Value[I] > '9')) return false;
		if (Value.Len() != 20)
		{
			if (Value.Len() < 22 || Value[19] != '.') return false;
			for (int32 I = 20; I < Value.Len() - 1; ++I) if (Value[I] < '0' || Value[I] > '9') return false;
		}
		// Floor sub-millisecond precision so client expiry cannot be rounded later than the grant.
		const FString Bounded = Value.Len() > 24 ? Value.Left(23) + TEXT("Z") : Value;
		return FDateTime::ParseIso8601(*Bounded, Out);
	}
	bool State(const FString& Value)
	{
		const TCHAR* States[] = { TEXT("PREPARED"), TEXT("TRANSPORT_DISABLED"), TEXT("SUBMITTING"), TEXT("SUBMISSION_UNCERTAIN"),
			TEXT("PROVIDER_QUEUED"), TEXT("SENDING"), TEXT("DELIVERY_EVIDENCE_PENDING"), TEXT("NEEDS_REVIEW"),
			TEXT("DELIVERED"), TEXT("FAILED"), TEXT("CANCELED"), TEXT("EXPIRED") };
		for (const TCHAR* Allowed : States) if (Exact(Value, Allowed)) return true;
		return false;
	}
	bool Preparable(const FString& Value) { return Exact(Value, TEXT("PREPARED")) || Exact(Value, TEXT("TRANSPORT_DISABLED")); }
	struct FSnapshot
	{
		FString Id, Recipient, Digest, Expiry, State;
		FDateTime ExpiresAt;
		int32 Pages = 0, Bytes = 0;
		bool Same(const FSnapshot& Other) const
		{
			return Exact(Id, Other.Id) && Exact(Recipient, Other.Recipient) && Exact(Digest, Other.Digest)
				&& Exact(Expiry, Other.Expiry) && Pages == Other.Pages && Bytes == Other.Bytes;
		}
		bool Readable() const { return !Exact(State, TEXT("CANCELED")) && !Exact(State, TEXT("EXPIRED")) && FDateTime::UtcNow() < ExpiresAt; }
	};
	bool Snapshot(const TSharedPtr<FJsonObject>& Json, FSnapshot& Out)
	{
		return String(Json, TEXT("faxId"), Out.Id, 36) && Uuid(Out.Id)
			&& String(Json, TEXT("recipient"), Out.Recipient, 16) && Recipient(Out.Recipient)
			&& String(Json, TEXT("documentSha256"), Out.Digest, 64) && Digest(Out.Digest)
			&& Integer(Json, TEXT("pageCount"), Out.Pages, 1, MaxPages) && Integer(Json, TEXT("byteCount"), Out.Bytes, 1, MaxPdfBytes)
			&& String(Json, TEXT("expiresAt"), Out.Expiry, 30) && Instant(Out.Expiry, Out.ExpiresAt)
			&& String(Json, TEXT("state"), Out.State, 32) && State(Out.State);
	}
	bool Capabilities(const TSharedPtr<FJsonObject>& Json, FString& Expiry, FDateTime& ExpiresAt)
	{
		FString Product, Protocol, Mode;
		const TArray<TSharedPtr<FJsonValue>>* Values = nullptr;
		if (!String(Json, TEXT("productId"), Product, 32) || !Exact(Product, TEXT("fax-trident"))
			|| !String(Json, TEXT("protocol"), Protocol, 32) || !Exact(Protocol, TEXT("faxprep.local.v1"))
			|| !String(Json, TEXT("outputMode"), Mode, 32) || !Exact(Mode, TEXT("selected_prepared_pdf"))
			|| !String(Json, TEXT("grantExpiresAt"), Expiry, 30) || !Instant(Expiry, ExpiresAt)
			|| !Json->TryGetArrayField(TEXT("capabilities"), Values) || !Values || Values->Num() != 2) return false;
		bool Read = false, Cancel = false;
		for (const auto& Value : *Values)
		{
			FString Capability;
			if (!Value.IsValid() || Value->Type != EJson::String || !Value->TryGetString(Capability)) return false;
			if (Exact(Capability, TEXT("fax.prepared.read")) && !Read) Read = true;
			else if (Exact(Capability, TEXT("fax.prepared.cancel")) && !Cancel) Cancel = true;
			else return false;
		}
		const TSharedPtr<FJsonObject>* Limits = nullptr;
		int32 Pdf = 0, Pages = 0, Ttl = 0;
		return Read && Cancel && Json->TryGetObjectField(TEXT("limits"), Limits) && Limits && Limits->IsValid()
			&& Integer(*Limits, TEXT("maxPdfBytes"), Pdf, MaxPdfBytes, MaxPdfBytes)
			&& Integer(*Limits, TEXT("maxPages"), Pages, MaxPages, MaxPages)
			&& Integer(*Limits, TEXT("grantTtlSeconds"), Ttl, 900, 900);
	}
	bool Pdf(const TArray<uint8>& Bytes, int32 ExpectedBytes, const FString& ExpectedDigest)
	{
		// Structural envelope only; companion PDFBox owns actual unencrypted page/dimension checks.
		if (Bytes.Num() != ExpectedBytes || Bytes.Num() < 16 || Bytes.Num() > MaxPdfBytes
			|| FMemory::Memcmp(Bytes.GetData(), "%PDF-", 5) != 0 || Bytes[5] < '0' || Bytes[5] > '9'
			|| Bytes[6] != '.' || Bytes[7] < '0' || Bytes[7] > '9' || (Bytes[8] != '\r' && Bytes[8] != '\n' && Bytes[8] != ' ')) return false;
		int32 End = Bytes.Num();
		while (End > 0 && (Bytes[End - 1] == 0 || Bytes[End - 1] == 9 || Bytes[End - 1] == 10
			|| Bytes[End - 1] == 12 || Bytes[End - 1] == 13 || Bytes[End - 1] == 32)) --End;
		if (End < 5 || FMemory::Memcmp(Bytes.GetData() + End - 5, "%%EOF", 5) != 0) return false;
		uint8 Hash[SHA256_DIGEST_LENGTH];
		if (::SHA256(Bytes.GetData(), static_cast<size_t>(Bytes.Num()), Hash) == nullptr) return false;
		const TCHAR Hex[] = TEXT("0123456789abcdef");
		FString Actual; Actual.Reserve(64);
		for (uint8 C : Hash) { Actual.AppendChar(Hex[C >> 4]); Actual.AppendChar(Hex[C & 15]); }
		return Exact(Actual, ExpectedDigest);
	}
}

/** Worker owns wire data only. Client/UObjects are never captured by asynchronous work. */
class FFaxPreparationHttpTask : public TSharedFromThis<FFaxPreparationHttpTask, ESPMode::ThreadSafe>
{
public:
	FaxPreparationWire::EOperation Operation = FaxPreparationWire::EOperation::Capabilities;
	uint64 Generation = 0;
	FString Url, Verb, ContentType, ContentDisposition, ExpectedDigest;
	TArray<FString> RequestHeaders;
	TArray<uint8> Response;
	SIZE_T HeaderBytes = 0;
	int32 Limit = FaxPreparationWire::MaxJsonBytes, StatusCode = 0, TimeoutMilliseconds = 30000;
	int32 TypeHeaders = 0, LengthHeaders = 0, DispositionHeaders = 0;
	bool bTransportOk = false, bRedirect = false, bPdfOk = false;
	TAtomic<bool> bCancelled{false}, bDone{false};
	static SIZE_T Write(char* Data, SIZE_T Size, SIZE_T Count, void* User)
	{
		auto* Task = static_cast<FFaxPreparationHttpTask*>(User);
		if (Task->bCancelled.Load() || (Count > 0 && Size > static_cast<SIZE_T>(Task->Limit) / Count)) return 0;
		const SIZE_T Bytes = Size * Count;
		if (Bytes > static_cast<SIZE_T>(Task->Limit - Task->Response.Num())) return 0;
		Task->Response.Append(reinterpret_cast<const uint8*>(Data), static_cast<int32>(Bytes)); return Bytes;
	}
	static SIZE_T Header(char* Data, SIZE_T Size, SIZE_T Count, void* User)
	{
		auto* Task = static_cast<FFaxPreparationHttpTask*>(User);
		if (Task->bCancelled.Load() || (Count > 0 && Size > 8192 / Count)) return 0;
		const SIZE_T Bytes = Size * Count;
		if (Bytes > 8192 - Task->HeaderBytes) return 0;
		Task->HeaderBytes += Bytes;
		for (SIZE_T I = 0; I < Bytes; ++I)
			if ((static_cast<uint8>(Data[I]) < 32 && Data[I] != '\r' && Data[I] != '\n' && Data[I] != '\t') || static_cast<uint8>(Data[I]) > 126) return 0;
		const FUTF8ToTCHAR Converted(Data, static_cast<int32>(Bytes));
		const FString Line(Converted.Length(), Converted.Get());
		if (Line.StartsWith(TEXT("Location:"), ESearchCase::IgnoreCase)) Task->bRedirect = true;
		if (Line.StartsWith(TEXT("Content-Type:"), ESearchCase::IgnoreCase))
		{
			if (++Task->TypeHeaders != 1) return 0;
			FString Type = Line.Mid(13).TrimStartAndEnd().ToLower();
			int32 Semicolon = INDEX_NONE;
			if (Type.FindChar(';', Semicolon)) Type = Type.Left(Semicolon).TrimStartAndEnd();
			Task->ContentType = MoveTemp(Type);
		}
		if (Line.StartsWith(TEXT("Content-Length:"), ESearchCase::IgnoreCase))
		{
			if (++Task->LengthHeaders != 1) return 0;
			const FString Value = Line.Mid(15).TrimStartAndEnd();
			if (Value.IsEmpty() || Value.Len() > 10) return 0;
			int64 Length = 0;
			for (TCHAR C : Value) { if (C < '0' || C > '9') return 0; Length = Length * 10 + C - '0'; }
			if (Length > Task->Limit) return 0;
		}
		if (Line.StartsWith(TEXT("Content-Disposition:"), ESearchCase::IgnoreCase))
		{
			if (++Task->DispositionHeaders != 1) return 0;
			Task->ContentDisposition = Line.Mid(20).TrimStartAndEnd();
		}
		return Bytes;
	}
	static int Progress(void* User, curl_off_t, curl_off_t, curl_off_t, curl_off_t)
	{
		return static_cast<FFaxPreparationHttpTask*>(User)->bCancelled.Load() ? 1 : 0;
	}
	void Run()
	{
		CURL* Curl = curl_easy_init(); curl_slist* Headers = nullptr;
		if (Curl && !bCancelled.Load())
		{
			const FTCHARToUTF8 UrlUtf8(*Url), VerbUtf8(*Verb);
			bool bConfigured = true;
			for (const auto& HeaderValue : RequestHeaders)
			{
				curl_slist* Next = curl_slist_append(Headers, TCHAR_TO_UTF8(*HeaderValue));
				if (!Next) { bConfigured = false; break; } Headers = Next;
			}
			auto Set = [Curl, &bConfigured](CURLoption Option, auto Value)
				{ if (curl_easy_setopt(Curl, Option, Value) != CURLE_OK) bConfigured = false; };
			Set(CURLOPT_URL, UrlUtf8.Get()); Set(CURLOPT_CUSTOMREQUEST, VerbUtf8.Get()); Set(CURLOPT_HTTPHEADER, Headers);
			Set(CURLOPT_PROTOCOLS_STR, "http"); Set(CURLOPT_PATH_AS_IS, 1L); Set(CURLOPT_FOLLOWLOCATION, 0L); Set(CURLOPT_MAXREDIRS, 0L);
			Set(CURLOPT_PROXY, ""); Set(CURLOPT_NOPROXY, "*"); Set(CURLOPT_NETRC, static_cast<long>(CURL_NETRC_IGNORED));
			Set(CURLOPT_IPRESOLVE, static_cast<long>(CURL_IPRESOLVE_V4)); Set(CURLOPT_VERBOSE, 0L); Set(CURLOPT_NOSIGNAL, 1L);
			Set(CURLOPT_CONNECTTIMEOUT_MS, 3000L); Set(CURLOPT_TIMEOUT_MS, static_cast<long>(TimeoutMilliseconds));
			Set(CURLOPT_WRITEFUNCTION, Write); Set(CURLOPT_WRITEDATA, this); Set(CURLOPT_HEADERFUNCTION, Header); Set(CURLOPT_HEADERDATA, this);
			Set(CURLOPT_NOPROGRESS, 0L); Set(CURLOPT_XFERINFOFUNCTION, Progress); Set(CURLOPT_XFERINFODATA, this);
			if (!FaxPreparationWire::Exact(Verb, TEXT("GET")))
			{
				static const char Empty[] = "";
				Set(CURLOPT_POSTFIELDS, Empty); Set(CURLOPT_POSTFIELDSIZE_LARGE, static_cast<curl_off_t>(0));
			}
			if (bConfigured)
			{
				const CURLcode Result = curl_easy_perform(Curl);
				long Code = 0; const CURLcode Info = curl_easy_getinfo(Curl, CURLINFO_RESPONSE_CODE, &Code);
				StatusCode = static_cast<int32>(Code);
				bTransportOk = Result == CURLE_OK && Info == CURLE_OK && !bCancelled.Load() && !bRedirect && Code >= 200 && Code <= 599;
			}
		}
		if (Curl) curl_easy_cleanup(Curl);
		curl_slist_free_all(Headers);
		if (Operation == FaxPreparationWire::EOperation::Document && bTransportOk && StatusCode == 200
			&& FaxPreparationWire::Exact(ContentType, TEXT("application/pdf"))
			&& FaxPreparationWire::Exact(ContentDisposition, TEXT("attachment; filename=prepared-fax-review.pdf")))
			bPdfOk = FaxPreparationWire::Pdf(Response, Limit, ExpectedDigest) && !bCancelled.Load();
		RequestHeaders.Reset(); Url.Reset(); ExpectedDigest.Reset();
		TSharedPtr<FFaxPreparationHttpTask, ESPMode::ThreadSafe> Cleanup;
		{ FScopeLock Scope(&CleanupLock); bWireFinished = true; Cleanup = MoveTemp(FinalRevoke); }
		bDone.Store(true);
		if (Cleanup.IsValid()) Cleanup->Run();
	}
	void RevokeAfter(const TSharedPtr<FFaxPreparationHttpTask, ESPMode::ThreadSafe>& Cleanup)
	{
		bool bStartNow = false;
		{ FScopeLock Scope(&CleanupLock); if (bWireFinished) bStartNow = true; else FinalRevoke = Cleanup; }
		if (bStartNow) Async(EAsyncExecution::ThreadPool, [Cleanup]() { Cleanup->Run(); });
	}
private:
	FCriticalSection CleanupLock;
	bool bWireFinished = false;
	TSharedPtr<FFaxPreparationHttpTask, ESPMode::ThreadSafe> FinalRevoke;
};

class FDaedalusFaxPreparationClient::FImpl
{
public:
	struct FCallbackLifetime { TAtomic<uint64> Generation{1}; TAtomic<bool> bStopped{false}; };
	FDaedalusFaxPreparationView View;
	FaxPreparationWire::FSnapshot Bound;
	FString Origin, Capability;
	FDateTime GrantExpiresAt;
	double GrantDeadline = 0;
	uint64 Generation = 1;
	bool bStopped = false, bVerified = false, bBlocked = false, bDisconnectWanted = false, bRevokeNeedsAttempt = false;
	TSharedPtr<FFaxPreparationHttpTask, ESPMode::ThreadSafe> Active;
	TArray<uint8> PendingDownload;
	TFunction<void(TArray<uint8>&&, const FString&)> DownloadCompletion;
	TSharedRef<FCallbackLifetime, ESPMode::ThreadSafe> CallbackLifetime = MakeShared<FCallbackLifetime, ESPMode::ThreadSafe>();

	FImpl() { View.Status = TEXT("Pair with the private local link for one desktop-approved prepared fax. This terminal cannot send a fax."); }
	bool Expired() const
	{
		return GrantDeadline > 0 && (FPlatformTime::Seconds() >= GrantDeadline || FDateTime::UtcNow() >= GrantExpiresAt);
	}
	void Controls()
	{
		const bool Connected = !bStopped && bVerified && !bBlocked && !bDisconnectWanted && !Expired() && !Capability.IsEmpty();
		View.bBusy = Active.IsValid(); View.bPaired = Connected;
		View.bCanPair = !bStopped && !Active.IsValid() && Origin.IsEmpty();
		View.bCanRefresh = Connected && !Active.IsValid();
		View.bCanCancel = Connected && !Active.IsValid() && View.bHasJob
			&& (FaxPreparationWire::Preparable(Bound.State) || FaxPreparationWire::Exact(Bound.State, TEXT("CANCELED")));
		View.bCanExport = Connected && !Active.IsValid() && View.bHasJob && !View.bUncertain && Bound.Readable();
		View.bCanDisconnect = !bStopped && !Origin.IsEmpty();
	}
	void Invalidate() { ++Generation; CallbackLifetime->Generation.Store(Generation); }
	void QueueCompletion(TFunction<void(TArray<uint8>&&, const FString&)> Completion, TArray<uint8>&& Bytes, const FString& Error)
	{
		if (!Completion) return;
		const auto Lifetime = CallbackLifetime; const uint64 ExpectedGeneration = Generation;
		const double ExpectedDeadline = GrantDeadline;
		const FDateTime ExpectedGrantExpiry = GrantExpiresAt, ExpectedJobExpiry = Bound.ExpiresAt;
		AsyncTask(ENamedThreads::GameThread, [Completion = MoveTemp(Completion), Bytes = MoveTemp(Bytes), Error, Lifetime,
			ExpectedGeneration, ExpectedDeadline, ExpectedGrantExpiry, ExpectedJobExpiry]() mutable
		{
			const bool Expired = !Bytes.IsEmpty() && (ExpectedDeadline <= 0 || FPlatformTime::Seconds() >= ExpectedDeadline
				|| FDateTime::UtcNow() >= ExpectedGrantExpiry || FDateTime::UtcNow() >= ExpectedJobExpiry);
			if (Lifetime->bStopped.Load() || Lifetime->Generation.Load() != ExpectedGeneration || Expired)
			{
				Bytes.Reset(); Completion({}, TEXT("The fax action changed or the terminal closed. Nothing was exported."));
			}
			else Completion(MoveTemp(Bytes), Error);
		});
	}
	void FinishDownload(TArray<uint8>&& Bytes, const FString& Error)
	{
		PendingDownload.Reset(); QueueCompletion(MoveTemp(DownloadCompletion), MoveTemp(Bytes), Error);
	}
	void ClearJob()
	{
		Bound = FaxPreparationWire::FSnapshot(); View.bHasJob = false;
		View.FaxId.Reset(); View.Recipient.Reset(); View.DocumentSha256.Reset(); View.ExpiresAt.Reset();
		View.JobState.Reset(); View.PageCount = 0; View.ByteCount = 0; PendingDownload.Reset();
	}
	void Forget(const FString& Status)
	{
		Invalidate(); ClearJob(); Origin.Reset(); Capability.Reset(); View.GrantExpiresAt.Reset(); GrantDeadline = 0;
		bVerified = false; bBlocked = false; bDisconnectWanted = false; bRevokeNeedsAttempt = false;
		View.bUncertain = false; View.Status = Status; Controls();
	}
	TSharedPtr<FFaxPreparationHttpTask, ESPMode::ThreadSafe> MakeRequest(FaxPreparationWire::EOperation Operation, const TCHAR* Verb, const TCHAR* Path)
	{
		auto Task = MakeShared<FFaxPreparationHttpTask, ESPMode::ThreadSafe>();
		Task->Operation = Operation; Task->Generation = Generation; Task->Verb = Verb; Task->Url = Origin + Path;
		Task->RequestHeaders.Add(TEXT("Authorization: Bearer ") + Capability);
		Task->RequestHeaders.Add(TEXT("Origin: ") + Origin); Task->RequestHeaders.Add(TEXT("Cache-Control: no-store"));
		Task->RequestHeaders.Add(TEXT("Accept: ") + (Operation == FaxPreparationWire::EOperation::Document ? FString(TEXT("application/pdf")) : FString(TEXT("application/json"))));
		return Task;
	}
	void Start(const TSharedPtr<FFaxPreparationHttpTask, ESPMode::ThreadSafe>& Task)
	{
		check(!Active.IsValid()); Active = Task;
		Async(EAsyncExecution::ThreadPool, [Task]() { Task->Run(); }); Controls();
	}
	void AdvanceDisconnect()
	{
		if (bStopped || Active.IsValid() || !bDisconnectWanted || !bRevokeNeedsAttempt) return;
		bRevokeNeedsAttempt = false;
		View.Status = TEXT("Revoking this local grant. This request affects local access only...");
		Start(MakeRequest(FaxPreparationWire::EOperation::Revoke, TEXT("DELETE"), TEXT("/v1/grant")));
	}
	TSharedPtr<FJsonObject> Json(const FFaxPreparationHttpTask& Task) const
	{
		return Task.bTransportOk && FaxPreparationWire::Exact(Task.ContentType, TEXT("application/json")) ? FaxPreparationWire::Parse(Task.Response) : nullptr;
	}
	bool ApplySnapshot(const TSharedPtr<FJsonObject>& Json)
	{
		FaxPreparationWire::FSnapshot Next;
		if (!FaxPreparationWire::Snapshot(Json, Next) || (View.bHasJob && !Bound.Same(Next))) return false;
		Bound = MoveTemp(Next); View.bHasJob = true; View.bUncertain = false;
		View.FaxId = Bound.Id; View.Recipient = Bound.Recipient; View.DocumentSha256 = Bound.Digest;
		View.ExpiresAt = Bound.Expiry; View.JobState = Bound.State; View.PageCount = Bound.Pages; View.ByteCount = Bound.Bytes;
		if (FaxPreparationWire::Exact(Bound.State, TEXT("CANCELED")))
			View.Status = TEXT("The selected job is CANCELED. This does not delete its source upload or copies already exported.");
		else if (FaxPreparationWire::Preparable(Bound.State))
			View.Status = TEXT("Review this exact prepared job. This terminal can export a PDF copy or request cancellation; it cannot confirm or send.");
		else View.Status = TEXT("Selected job state refreshed from Fax Trident. This terminal cannot confirm, send or recall a fax.");
		return true;
	}
	void Complete(const TSharedPtr<FFaxPreparationHttpTask, ESPMode::ThreadSafe>& Task)
	{
		using namespace FaxPreparationWire;
		if (Task->Generation != Generation) { AdvanceDisconnect(); Controls(); return; }
		const auto Value = Json(*Task);
		if (Task->Operation == EOperation::Revoke)
		{
			FString State;
			if (Task->StatusCode == 200 && String(Value, TEXT("localAccess"), State, 16) && Exact(State, TEXT("REVOKED")))
				Forget(TEXT("Local grant revocation confirmed. Revocation does not cancel upstream work, delete source uploads or remove exported copies."));
			else { View.bUncertain = true; View.Status = TEXT("Local revocation is unconfirmed. Disconnect retries it; Close forgets the link and leaves expiry to the desktop. Local revocation does not cancel upstream work."); }
			Controls(); return;
		}
		if (Expired())
		{
			FinishDownload({}, TEXT("The local grant expired. Nothing was exported."));
			Forget(TEXT("The local grant expired. Local expiry does not cancel upstream work, delete source uploads or remove exported copies.")); return;
		}
		if (Task->StatusCode == 401 || Task->StatusCode == 403)
		{
			Invalidate(); bBlocked = true; ClearJob();
			FinishDownload({}, TEXT("Local fax access is unavailable. Nothing was exported."));
			View.Status = TEXT("Local access is unavailable. Disconnect to request revocation, or Close and obtain a fresh desktop link. Access loss does not confirm upstream cancellation or deletion.");
			Controls(); return;
		}
		if (Task->Operation == EOperation::Capabilities)
		{
			FString Expiry; FDateTime Expires;
			if (Task->StatusCode != 200 || !Capabilities(Value, Expiry, Expires))
			{
				bBlocked = true; View.Status = TEXT("The typed link did not return the required fax preparation protocol. Disconnect or Close before pairing again.");
			}
			else
			{
				const double Remaining = (Expires - FDateTime::UtcNow()).GetTotalSeconds();
				if (Remaining <= 0 || Remaining > 901) { bBlocked = true; View.Status = TEXT("The local grant is expired or its expiry could not be validated."); }
				else
				{
					GrantExpiresAt = Expires; GrantDeadline = FPlatformTime::Seconds() + FMath::Min(Remaining, 900.0);
					View.GrantExpiresAt = Expiry; bVerified = true;
					View.Status = TEXT("Reading the one desktop-approved fax job...");
					Start(MakeRequest(EOperation::Job, TEXT("GET"), TEXT("/v1/job")));
				}
			}
		}
		else if (Task->Operation == EOperation::Document)
		{
			if (Task->bPdfOk && Task->StatusCode == 200 && View.bHasJob && Bound.Readable())
			{
				PendingDownload = MoveTemp(Task->Response);
				View.Status = TEXT("Rechecking the same job after PDF download...");
				Start(MakeRequest(EOperation::AfterDownload, TEXT("GET"), TEXT("/v1/job")));
			}
			else
			{
				View.bUncertain = true; View.Status = TEXT("The PDF copy failed its bounded wire checks. Refresh the same selected job before another export.");
				FinishDownload({}, TEXT("The selected PDF could not be verified. Nothing was exported."));
			}
		}
		else
		{
			if (Task->StatusCode != 200 || !ApplySnapshot(Value))
			{
				View.bUncertain = true;
				View.Status = Task->Operation == EOperation::Cancel
					? TEXT("Cancellation is unconfirmed. Refresh the same job or explicitly retry cancellation. No replacement job will be created.")
					: TEXT("The same selected job could not be verified. Refresh before exporting; a changed job is never accepted.");
				FinishDownload({}, TEXT("The selected job could not be verified. Nothing was exported."));
			}
			else if (Task->Operation == EOperation::Cancel)
			{
				if (!Exact(Bound.State, TEXT("CANCELED")))
				{ View.bUncertain = true; View.Status = TEXT("Cancellation was not confirmed. Refresh the selected job; attempted transmission cannot be recalled here."); }
			}
			else if (Task->Operation == EOperation::BeforeDownload)
			{
				if (!Bound.Readable()) FinishDownload({}, TEXT("The selected job no longer permits a PDF copy. Nothing was exported."));
				else
				{
					auto Document = MakeRequest(EOperation::Document, TEXT("GET"), TEXT("/v1/document"));
					Document->Limit = Bound.Bytes; Document->ExpectedDigest = Bound.Digest;
					View.Status = TEXT("Downloading the exact selected PDF from the local companion..."); Start(Document);
				}
			}
			else if (Task->Operation == EOperation::AfterDownload)
			{
				if (!Bound.Readable() || PendingDownload.Num() != Bound.Bytes)
					FinishDownload({}, TEXT("The selected job no longer permits this PDF copy. Nothing was exported."));
				else
				{
					View.Status = TEXT("The exact PDF copy is verified. Exported copies remain user files after local revocation or server cancellation.");
					auto Bytes = MoveTemp(PendingDownload); FinishDownload(MoveTemp(Bytes), FString());
				}
			}
		}
		Controls();
	}
};

FDaedalusFaxPreparationClient::FDaedalusFaxPreparationClient() : Impl(MakeUnique<FImpl>()) {}
FDaedalusFaxPreparationClient::~FDaedalusFaxPreparationClient() { Shutdown(); }
FDaedalusFaxPreparationView FDaedalusFaxPreparationClient::GetView() const { check(IsInGameThread()); return Impl->View; }

bool FDaedalusFaxPreparationClient::Pair(const FString& PairingLink)
{
	check(IsInGameThread()); Impl->Controls();
	if (!Impl->View.bCanPair) return false;
	FString Origin, Capability;
	if (!FaxPreparationWire::Link(PairingLink, Origin, Capability))
	{
		Impl->View.Status = TEXT("Use the exact typed http://127.0.0.1:<port>/realm/fax-preparation/#token= link from Fax Trident."); return false;
	}
	Impl->Invalidate(); Impl->Origin = MoveTemp(Origin); Impl->Capability = MoveTemp(Capability);
	Impl->View.Status = TEXT("Verifying the selected fax grant and its bounded capabilities...");
	Impl->Start(Impl->MakeRequest(FaxPreparationWire::EOperation::Capabilities, TEXT("GET"), TEXT("/v1/capabilities"))); return true;
}
void FDaedalusFaxPreparationClient::Refresh()
{
	check(IsInGameThread()); Impl->Controls();
	if (!Impl->View.bCanRefresh) return;
	Impl->Invalidate(); Impl->View.Status = TEXT("Refreshing the same desktop-approved fax job...");
	Impl->Start(Impl->MakeRequest(FaxPreparationWire::EOperation::Job, TEXT("GET"), TEXT("/v1/job")));
}
void FDaedalusFaxPreparationClient::CancelPreparation()
{
	check(IsInGameThread()); Impl->Controls();
	if (!Impl->View.bCanCancel) return;
	Impl->Invalidate();
	if (FaxPreparationWire::Exact(Impl->Bound.State, TEXT("CANCELED")))
	{
		Impl->View.Status = TEXT("The selected job is already CANCELED. No new cancellation request was sent."); return;
	}
	Impl->View.bUncertain = true; Impl->View.Status = TEXT("Cancellation requested for this same job; server cancellation is not yet confirmed...");
	Impl->Start(Impl->MakeRequest(FaxPreparationWire::EOperation::Cancel, TEXT("POST"), TEXT("/v1/cancel")));
}
void FDaedalusFaxPreparationClient::Disconnect()
{
	check(IsInGameThread());
	if (Impl->bStopped || Impl->Origin.IsEmpty()) return;
	Impl->Invalidate(); Impl->bDisconnectWanted = true; Impl->bRevokeNeedsAttempt = true; Impl->ClearJob();
	if (Impl->Active.IsValid()) Impl->Active->bCancelled.Store(true);
	Impl->FinishDownload({}, TEXT("Local fax access is disconnecting. Nothing was exported."));
	Impl->View.Status = TEXT("Local disconnection requested. Grant revocation remains unconfirmed. Local disconnection does not cancel upstream work.");
	Impl->AdvanceDisconnect(); Impl->Controls();
}
void FDaedalusFaxPreparationClient::Shutdown()
{
	if (!Impl.IsValid() || Impl->bStopped) return;
	Impl->bStopped = true; Impl->Invalidate(); Impl->CallbackLifetime->bStopped.Store(true);
	Impl->FinishDownload({}, TEXT("The fax terminal closed. Nothing was exported."));
	TSharedPtr<FFaxPreparationHttpTask, ESPMode::ThreadSafe> Cleanup;
	if (!Impl->Origin.IsEmpty() && !Impl->Capability.IsEmpty() && !Impl->Expired())
	{
		Cleanup = Impl->MakeRequest(FaxPreparationWire::EOperation::Revoke, TEXT("DELETE"), TEXT("/v1/grant")); Cleanup->TimeoutMilliseconds = 3000;
	}
	if (Impl->Active.IsValid())
	{
		if (Cleanup.IsValid()) Impl->Active->RevokeAfter(Cleanup);
		Impl->Active->bCancelled.Store(true); Impl->Active.Reset();
	}
	else if (Cleanup.IsValid()) Async(EAsyncExecution::ThreadPool, [Cleanup]() { Cleanup->Run(); });
	Impl->Forget(TEXT("Terminal closed. Local revocation was best effort and is unconfirmed; the desktop controls grant expiry. Closing does not cancel upstream work or delete source uploads."));
}
void FDaedalusFaxPreparationClient::Tick()
{
	check(IsInGameThread());
	if (Impl->bStopped) return;
	if (Impl->Expired())
	{
		Impl->Invalidate(); if (Impl->Active.IsValid()) Impl->Active->bCancelled.Store(true);
		Impl->FinishDownload({}, TEXT("The local grant expired. Nothing was exported."));
		// Retain the serial worker until it finishes, but forget all local authority now.
		Impl->Forget(TEXT("The local grant expired. Local expiry does not cancel upstream work, delete source uploads or remove exported copies."));
	}
	if (Impl->Active.IsValid() && Impl->Active->bDone.Load())
	{
		auto Task = MoveTemp(Impl->Active); Impl->Complete(Task);
	}
	Impl->Controls();
}
void FDaedalusFaxPreparationClient::Download(TFunction<void(TArray<uint8>&&, const FString&)> Completion)
{
	check(IsInGameThread()); Impl->Controls();
	if (!Impl->View.bCanExport)
	{
		Impl->QueueCompletion(MoveTemp(Completion), {}, TEXT("No verified PDF copy is available for this selected job.")); return;
	}
	Impl->Invalidate(); Impl->DownloadCompletion = MoveTemp(Completion);
	Impl->View.Status = TEXT("Rechecking this selected job before downloading a PDF copy...");
	Impl->Start(Impl->MakeRequest(FaxPreparationWire::EOperation::BeforeDownload, TEXT("GET"), TEXT("/v1/job")));
}
