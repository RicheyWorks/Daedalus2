// SPDX-License-Identifier: MIT
#include "DaedalusSynapseClient.h"

#include "DaedalusLocalAppCore.h"
#include "Async/Async.h"
#include "Dom/JsonObject.h"
#include "HAL/PlatformTime.h"
#include "Misc/DateTime.h"
#include "Misc/Guid.h"
#include "Misc/ScopeLock.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"

THIRD_PARTY_INCLUDES_START
#include <curl/curl.h>
THIRD_PARTY_INCLUDES_END

namespace SynapseWire
{
	constexpr int32 MaxResponseBytes = 512 * 1024; // Includes worst-case escaped 32 KiB card strings.
	constexpr int32 MaxRequestBytes = 4096;
	constexpr int32 MaxTextBytes = 32768;
	constexpr int32 MaxCards = 100;
	enum class EOperation : uint8 { Capabilities, Session, Due, Reveal, Review, Revoke };

	bool Exact(const FString& Left, const FString& Right)
	{
		// FString's convenience equality can ignore case, and null-terminated comparisons can
		// stop inside an imported ID. Rust String identities require every code unit to match.
		return Left.Len() == Right.Len() && (Left.IsEmpty()
			|| FMemory::Memcmp(*Left, *Right, static_cast<SIZE_T>(Left.Len()) * sizeof(TCHAR)) == 0);
	}

	bool Utf8(const TArray<uint8>& Bytes)
	{
		// Do not normalize malformed UTF-8 into a different opaque identifier or receipt.
		for (int32 I = 0; I < Bytes.Num();)
		{
			const uint8 Lead = Bytes[I++];
			if (Lead < 0x80) { if (Lead == 0) return false; continue; }
			int32 Count = 0;
			uint32 Codepoint = 0, Minimum = 0;
			if (Lead >= 0xc2 && Lead <= 0xdf) { Count = 1; Codepoint = Lead & 0x1f; Minimum = 0x80; }
			else if (Lead >= 0xe0 && Lead <= 0xef) { Count = 2; Codepoint = Lead & 0x0f; Minimum = 0x800; }
			else if (Lead >= 0xf0 && Lead <= 0xf4) { Count = 3; Codepoint = Lead & 0x07; Minimum = 0x10000; }
			else return false;
			if (Count > Bytes.Num() - I) return false;
			while (Count-- > 0)
			{
				const uint8 Next = Bytes[I++];
				if ((Next & 0xc0) != 0x80) return false;
				Codepoint = (Codepoint << 6) | (Next & 0x3f);
			}
			if (Codepoint < Minimum || Codepoint > 0x10ffff || (Codepoint >= 0xd800 && Codepoint <= 0xdfff)) return false;
		}
		return true;
	}

	bool Text(const FString& Value, int32 MaximumBytes, bool bAllowEmpty = true)
	{
		if ((!bAllowEmpty && Value.IsEmpty()) || Value.Len() > MaximumBytes) return false;
		// JSON Unicode escapes must not introduce unpaired surrogates either.
		for (int32 I = 0; I < Value.Len(); ++I)
		{
			const uint32 C = static_cast<uint32>(Value[I]);
			if (sizeof(TCHAR) == 2 && C >= 0xd800 && C <= 0xdbff)
			{
				if (++I >= Value.Len()) return false;
				const uint32 Low = static_cast<uint32>(Value[I]);
				if (Low < 0xdc00 || Low > 0xdfff) return false;
			}
			else if ((C >= 0xd800 && C <= 0xdfff) || C > 0x10ffff) return false;
		}
		const FTCHARToUTF8 Converted(*Value, Value.Len());
		return Converted.Length() <= MaximumBytes;
	}

	bool String(const TSharedPtr<FJsonObject>& Json, const TCHAR* Name, FString& Out, int32 MaximumBytes, bool bAllowEmpty = true)
	{
		const auto* Value = Json.IsValid() ? Json->Values.Find(Name) : nullptr;
		return Value && Value->IsValid() && (*Value)->Type == EJson::String && (*Value)->TryGetString(Out)
			&& Text(Out, MaximumBytes, bAllowEmpty);
	}

	bool Integer(const TSharedPtr<FJsonObject>& Json, const TCHAR* Name, uint64& Out, uint64 Minimum, uint64 Maximum)
	{
		double Number = 0;
		const auto* Value = Json.IsValid() ? Json->Values.Find(Name) : nullptr;
		if (!Value || !Value->IsValid() || (*Value)->Type != EJson::Number || !(*Value)->TryGetNumber(Number)
			|| !FMath::IsFinite(Number) || Number < static_cast<double>(Minimum) || Number > static_cast<double>(Maximum)
			|| FMath::FloorToDouble(Number) != Number) return false;
		Out = static_cast<uint64>(Number);
		return true;
	}

	bool True(const TSharedPtr<FJsonObject>& Json, const TCHAR* Name)
	{
		bool Value = false;
		const auto* Field = Json.IsValid() ? Json->Values.Find(Name) : nullptr;
		return Field && Field->IsValid() && (*Field)->Type == EJson::Boolean && (*Field)->TryGetBool(Value) && Value;
	}

	bool Token(const FString& Value)
	{
		if (Value.Len() != 43) return false;
		for (TCHAR C : Value)
			if (!((C >= 'A' && C <= 'Z') || (C >= 'a' && C <= 'z') || (C >= '0' && C <= '9') || C == '_' || C == '-')) return false;
		return true;
	}

	bool Revision(const FString& Value)
	{
		if (Value.Len() != 64) return false;
		for (TCHAR C : Value) if (!((C >= '0' && C <= '9') || (C >= 'a' && C <= 'f'))) return false;
		return true;
	}

	bool Kind(const FString& Value) { return Exact(Value, TEXT("basic")) || Exact(Value, TEXT("cloze")) || Exact(Value, TEXT("code")); }

	TSharedPtr<FJsonObject> Parse(const TArray<uint8>& Bytes)
	{
		if (Bytes.IsEmpty() || Bytes.Num() > MaxResponseBytes || !Utf8(Bytes)) return nullptr;
		int32 Depth = 0;
		bool bQuoted = false, bEscape = false;
		for (uint8 C : Bytes)
		{
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
		TSharedPtr<FJsonObject> Json;
		return FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(FString(Converted.Length(), Converted.Get())), Json) ? Json : nullptr;
	}

	TSharedPtr<const TArray<uint8>, ESPMode::ThreadSafe> Body(const TSharedRef<FJsonObject>& Json)
	{
		FString Serialized;
		if (!FJsonSerializer::Serialize(Json, TJsonWriterFactory<>::Create(&Serialized))) return nullptr;
		const FTCHARToUTF8 Converted(*Serialized, Serialized.Len());
		if (Converted.Length() > MaxRequestBytes) return nullptr;
		auto Bytes = MakeShared<TArray<uint8>, ESPMode::ThreadSafe>();
		Bytes->Append(reinterpret_cast<const uint8*>(Converted.Get()), Converted.Length());
		return Bytes;
	}

	TSharedPtr<const TArray<uint8>, ESPMode::ThreadSafe> CardBody(const FString& Id, const FString& CardRevision)
	{
		auto Json = MakeShared<FJsonObject>();
		Json->SetStringField(TEXT("card_id"), Id); Json->SetStringField(TEXT("revision"), CardRevision);
		return Body(Json);
	}

	bool Capabilities(const TSharedPtr<FJsonObject>& Json)
	{
		FString Product;
		uint64 Version = 0;
		const TArray<TSharedPtr<FJsonValue>>* Actions = nullptr;
		if (!String(Json, TEXT("productId"), Product, 16, false) || !Exact(Product, TEXT("synapse"))
			|| !Integer(Json, TEXT("version"), Version, 1, 1) || !True(Json, TEXT("localOnly"))
			|| !Json->TryGetArrayField(TEXT("actions"), Actions) || !Actions || Actions->Num() != 4) return false;
		uint8 Seen = 0;
		for (const auto& Value : *Actions)
		{
			FString Action;
			if (!Value.IsValid() || Value->Type != EJson::String || !Value->TryGetString(Action)) return false;
			const uint8 Bit = Exact(Action, TEXT("due")) ? 1 : Exact(Action, TEXT("reveal")) ? 2 : Exact(Action, TEXT("review")) ? 4 : Exact(Action, TEXT("revoke")) ? 8 : 0;
			if (Bit == 0 || (Seen & Bit) != 0) return false;
			Seen |= Bit;
		}
		return Seen == 15;
	}

	bool Timestamp(const FString& Value)
	{
		if (Value.Len() < 20 || Value.Len() > 64) return false;
		for (TCHAR C : Value)
			if (!((C >= '0' && C <= '9') || C == '-' || C == '+' || C == ':' || C == '.' || C == 'T' || C == 'Z')) return false;
		FDateTime Date;
		return FDateTime::ParseIso8601(*Value, Date);
	}
}

/** Additive transport, matching the existing private photo client's bounded libcurl pattern.
 * No worker captures this client or a UObject. Response state is consumed only after bDone.
 */
class FSynapseHttpTask : public TSharedFromThis<FSynapseHttpTask, ESPMode::ThreadSafe>
{
public:
	SynapseWire::EOperation Operation = SynapseWire::EOperation::Capabilities;
	uint64 Generation = 0;
	FString Url, Verb, ContentType;
	TArray<FString> RequestHeaders;
	TSharedPtr<const TArray<uint8>, ESPMode::ThreadSafe> RequestBody;
	TArray<uint8> Response;
	SIZE_T HeaderBytes = 0;
	int32 StatusCode = 0, TimeoutMilliseconds = 30000;
	bool bTransportOk = false, bRedirect = false;
	TAtomic<bool> bCancelled{false}, bDone{false};

	static SIZE_T Write(char* Data, SIZE_T Size, SIZE_T Count, void* User)
	{
		auto* Task = static_cast<FSynapseHttpTask*>(User);
		if (Task->bCancelled.Load() || (Count > 0 && Size > SynapseWire::MaxResponseBytes / Count)) return 0;
		const SIZE_T Bytes = Size * Count;
		if (Bytes > static_cast<SIZE_T>(SynapseWire::MaxResponseBytes - Task->Response.Num())) return 0;
		Task->Response.Append(reinterpret_cast<const uint8*>(Data), static_cast<int32>(Bytes));
		return Bytes;
	}
	static SIZE_T Header(char* Data, SIZE_T Size, SIZE_T Count, void* User)
	{
		auto* Task = static_cast<FSynapseHttpTask*>(User);
		if (Task->bCancelled.Load() || (Count > 0 && Size > 8192 / Count)) return 0;
		const SIZE_T Bytes = Size * Count;
		if (Bytes > 8192 - Task->HeaderBytes) return 0;
		Task->HeaderBytes += Bytes;
		const FUTF8ToTCHAR Converted(Data, static_cast<int32>(Bytes));
		const FString Line(Converted.Length(), Converted.Get());
		if (Line.StartsWith(TEXT("Location:"), ESearchCase::IgnoreCase)) Task->bRedirect = true;
		if (Line.StartsWith(TEXT("Content-Type:"), ESearchCase::IgnoreCase))
		{
			FString Type = Line.Mid(13).TrimStartAndEnd().ToLower();
			int32 Semicolon = INDEX_NONE;
			if (Type.FindChar(';', Semicolon)) Type = Type.Left(Semicolon).TrimStartAndEnd();
			if (!Task->ContentType.IsEmpty() && !SynapseWire::Exact(Task->ContentType, Type)) return 0;
			Task->ContentType = MoveTemp(Type);
		}
		return Bytes;
	}
	static int Progress(void* User, curl_off_t, curl_off_t, curl_off_t, curl_off_t)
	{
		return static_cast<FSynapseHttpTask*>(User)->bCancelled.Load() ? 1 : 0;
	}

	void Run()
	{
		CURL* Curl = curl_easy_init();
		curl_slist* Headers = nullptr;
		if (Curl && !bCancelled.Load() && (!RequestBody.IsValid() || RequestBody->Num() <= SynapseWire::MaxRequestBytes))
		{
			const FTCHARToUTF8 UrlUtf8(*Url), VerbUtf8(*Verb);
			bool bConfigured = true;
			for (const auto& HeaderValue : RequestHeaders)
			{
				curl_slist* Next = curl_slist_append(Headers, TCHAR_TO_UTF8(*HeaderValue));
				if (!Next) { bConfigured = false; break; }
				Headers = Next;
			}
			auto Set = [Curl, &bConfigured](CURLoption Option, auto Value)
				{ if (curl_easy_setopt(Curl, Option, Value) != CURLE_OK) bConfigured = false; };
			Set(CURLOPT_URL, UrlUtf8.Get()); Set(CURLOPT_CUSTOMREQUEST, VerbUtf8.Get()); Set(CURLOPT_HTTPHEADER, Headers);
			Set(CURLOPT_PROTOCOLS_STR, "http"); Set(CURLOPT_PATH_AS_IS, 1L); Set(CURLOPT_FOLLOWLOCATION, 0L); Set(CURLOPT_MAXREDIRS, 0L);
			Set(CURLOPT_PROXY, ""); Set(CURLOPT_NOPROXY, "*"); Set(CURLOPT_NETRC, static_cast<long>(CURL_NETRC_IGNORED));
			Set(CURLOPT_VERBOSE, 0L); Set(CURLOPT_NOSIGNAL, 1L); Set(CURLOPT_CONNECTTIMEOUT_MS, 3000L);
			Set(CURLOPT_TIMEOUT_MS, static_cast<long>(TimeoutMilliseconds));
			Set(CURLOPT_WRITEFUNCTION, Write); Set(CURLOPT_WRITEDATA, this); Set(CURLOPT_HEADERFUNCTION, Header); Set(CURLOPT_HEADERDATA, this);
			Set(CURLOPT_NOPROGRESS, 0L); Set(CURLOPT_XFERINFOFUNCTION, Progress); Set(CURLOPT_XFERINFODATA, this);
			if (!SynapseWire::Exact(Verb, TEXT("GET")))
			{
				static const char Empty[] = "";
				const void* Data = RequestBody.IsValid() && !RequestBody->IsEmpty() ? RequestBody->GetData() : static_cast<const void*>(Empty);
				Set(CURLOPT_POSTFIELDS, Data);
				Set(CURLOPT_POSTFIELDSIZE_LARGE, static_cast<curl_off_t>(RequestBody.IsValid() ? RequestBody->Num() : 0));
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
		if (Curl) curl_easy_cleanup(Curl);
		curl_slist_free_all(Headers);
		RequestHeaders.Reset(); RequestBody.Reset(); Url.Reset();
		TSharedPtr<FSynapseHttpTask, ESPMode::ThreadSafe> Cleanup;
		{
			FScopeLock Scope(&CleanupLock); bWireFinished = true; Cleanup = MoveTemp(FinalRevoke);
		}
		bDone.Store(true);
		if (Cleanup.IsValid()) Cleanup->Run();
	}
	void RevokeAfter(const TSharedPtr<FSynapseHttpTask, ESPMode::ThreadSafe>& Cleanup)
	{
		bool bStartNow = false;
		{
			FScopeLock Scope(&CleanupLock);
			if (bWireFinished) bStartNow = true; else FinalRevoke = Cleanup;
		}
		if (bStartNow) Async(EAsyncExecution::ThreadPool, [Cleanup]() { Cleanup->Run(); });
	}
private:
	FCriticalSection CleanupLock;
	bool bWireFinished = false;
	TSharedPtr<FSynapseHttpTask, ESPMode::ThreadSafe> FinalRevoke;
};

class FDaedalusSynapseClient::FImpl
{
public:
	FDaedalusSynapseView View;
	FString Origin, PairToken, Session, CardId, CardRevision;
	FString PendingCardId, PendingRevision, PendingActionId, PendingKind;
	int32 PendingScore = 0;
	TSharedPtr<const TArray<uint8>, ESPMode::ThreadSafe> PendingBody;
	TSharedPtr<FSynapseHttpTask, ESPMode::ThreadSafe> Active;
	uint64 Generation = 1;
	double ExpiresAt = 0;
	bool bStopped = false, bPendingNeedsReveal = false;
	bool bDisconnectWanted = false, bRevokeNeedsAttempt = false, bRevokeUnconfirmed = false;
	bool bUnknownSession = false, bPriorRevokeUnconfirmed = false;

	FImpl() { View.Status = TEXT("In Synapse, enable a selected study track and paste its private study-desk link."); }
	bool HasPending() const { return PendingBody.IsValid(); }
	void Controls()
	{
		const bool bConnected = !bStopped && !Session.IsEmpty() && !bDisconnectWanted;
		const bool bIdle = !Active.IsValid();
		View.bBusy = !bIdle; View.bPaired = bConnected;
		View.bCanPair = !bStopped && bIdle && (Origin.IsEmpty() || bRevokeUnconfirmed || bUnknownSession);
		View.bCanDisconnect = !bStopped && !Origin.IsEmpty();
		View.bCanRefresh = bConnected && bIdle && !HasPending();
		View.bCanReveal = bConnected && bIdle && View.bHasCard && !View.bRevealed && (!HasPending() || bPendingNeedsReveal);
		View.bCanScore = bConnected && bIdle && View.bHasCard && View.bRevealed && !HasPending();
		View.bCanRetry = bConnected && bIdle && HasPending() && !bPendingNeedsReveal;
		View.bUncertain = HasPending();
	}
	void ClearCard()
	{
		CardId.Reset(); CardRevision.Reset();
		View.Prompt.Reset(); View.Context.Reset(); View.Answer.Reset(); View.Kind.Reset();
		View.bHasCard = false; View.bRevealed = false;
	}
	void ClearReceipt() { View.bHasReceipt = false; View.ReceiptSummary.Reset(); }
	void ClearVisible()
	{
		ClearCard(); ClearReceipt(); View.DueCount = 0; View.SelectedCount = 0;
	}
	void ForgetGrant(const FString& Status)
	{
		++Generation; Origin.Reset(); PairToken.Reset(); Session.Reset(); ExpiresAt = 0;
		bDisconnectWanted = false; bRevokeNeedsAttempt = false; bRevokeUnconfirmed = false; bUnknownSession = false;
		bPendingNeedsReveal = false;
		ClearVisible(); View.Status = Status; Controls(); // Pending identity/body intentionally survive.
	}
	TSharedPtr<FSynapseHttpTask, ESPMode::ThreadSafe> MakeRequest(SynapseWire::EOperation Operation, const TCHAR* Verb, const TCHAR* Path)
	{
		auto Task = MakeShared<FSynapseHttpTask, ESPMode::ThreadSafe>();
		Task->Operation = Operation; Task->Generation = Generation; Task->Verb = Verb; Task->Url = Origin + Path;
		Task->RequestHeaders.Add(TEXT("Authorization: Bearer ") + PairToken);
		Task->RequestHeaders.Add(TEXT("Accept: application/json")); Task->RequestHeaders.Add(TEXT("Cache-Control: no-store"));
		if (!Session.IsEmpty()) Task->RequestHeaders.Add(TEXT("X-Desk-Session: ") + Session);
		if (!SynapseWire::Exact(Task->Verb, TEXT("GET")))
		{
			Task->RequestHeaders.Add(TEXT("Origin: ") + Origin);
			Task->RequestHeaders.Add(TEXT("Content-Type: application/json")); Task->RequestHeaders.Add(TEXT("Expect:"));
			Task->RequestBody = SynapseWire::Body(MakeShared<FJsonObject>());
		}
		return Task;
	}
	void Start(const TSharedPtr<FSynapseHttpTask, ESPMode::ThreadSafe>& Task)
	{
		check(!Active.IsValid());
		Active = Task;
		Async(EAsyncExecution::ThreadPool, [Task]() { Task->Run(); });
		Controls();
	}
	TSharedPtr<FJsonObject> Json(const FSynapseHttpTask& Task) const
	{
		return Task.bTransportOk && SynapseWire::Exact(Task.ContentType, TEXT("application/json")) ? SynapseWire::Parse(Task.Response) : nullptr;
	}
	bool Error(const FSynapseHttpTask& Task, const TCHAR* Name) const
	{
		FString Code;
		return SynapseWire::String(Json(Task), TEXT("error"), Code, 64, false) && SynapseWire::Exact(Code, Name);
	}
	void StartDue()
	{
		ClearCard(); ClearReceipt();
		View.Status = TEXT("Reading one due card from the desktop-selected track...");
		Start(MakeRequest(SynapseWire::EOperation::Due, TEXT("GET"), TEXT("/v1/due")));
	}
	void StartReview()
	{
		auto Task = MakeRequest(SynapseWire::EOperation::Review, TEXT("POST"), TEXT("/v1/review"));
		Task->RequestBody = PendingBody;
		View.Status = TEXT("Checking or saving the exact review action. Saved status is not yet confirmed...");
		Start(Task);
	}
	void AdvanceDisconnect()
	{
		if (bStopped || Active.IsValid() || !bDisconnectWanted || !bRevokeNeedsAttempt) return;
		bRevokeNeedsAttempt = false;
		if (Session.IsEmpty())
		{
			const bool bClaimUnknown = bUnknownSession;
			bPriorRevokeUnconfirmed |= bClaimUnknown;
			ForgetGrant(HasPending()
				? TEXT("Disconnected locally. The review outcome remains unknown; pair a fresh selected track and retry the same save. Revocation cannot undo a saved review.")
				: bClaimUnknown ? TEXT("Disconnected locally. An unconfirmed session claim requires a fresh link from Synapse; remote revocation is unconfirmed.")
				: TEXT("Disconnected. No private desk session was claimed."));
		}
		else
		{
			View.Status = TEXT("Revoking this desk grant. Existing saved reviews cannot be undone by disconnecting...");
			Start(MakeRequest(SynapseWire::EOperation::Revoke, TEXT("POST"), TEXT("/v1/revoke")));
		}
	}
	bool ApplyDue(const TSharedPtr<FJsonObject>& Value)
	{
		uint64 Count = 0;
		if (!SynapseWire::Integer(Value, TEXT("due_count"), Count, 0, static_cast<uint64>(View.SelectedCount))) return false;
		const auto* Card = Value->Values.Find(TEXT("card"));
		if (!Card || !Card->IsValid()) return false;
		if ((*Card)->Type == EJson::Null)
		{
			if (Count != 0) return false;
			ClearCard(); View.DueCount = 0;
			View.Status = TEXT("No selected cards are due. Refresh later using the existing Synapse schedule.");
			return true;
		}
		if (Count == 0 || (*Card)->Type != EJson::Object) return false;
		const auto Object = (*Card)->AsObject();
		FString Id, Prompt, Revision, Kind, Context;
		if (!SynapseWire::String(Object, TEXT("id"), Id, 64) // Imported IDs are opaque, not UUIDs.
			|| !SynapseWire::String(Object, TEXT("prompt"), Prompt, SynapseWire::MaxTextBytes)
			|| !SynapseWire::String(Object, TEXT("revision"), Revision, 64, false) || !SynapseWire::Revision(Revision)
			|| !SynapseWire::String(Object, TEXT("kind"), Kind, 8, false) || !SynapseWire::Kind(Kind)) return false;
		const auto* ContextValue = Object->Values.Find(TEXT("context"));
		if (!ContextValue || !ContextValue->IsValid()) return false;
		if (SynapseWire::Exact(Kind, TEXT("cloze")))
		{
			if (!SynapseWire::String(Object, TEXT("context"), Context, SynapseWire::MaxTextBytes)) return false;
		}
		else if ((*ContextValue)->Type != EJson::Null) return false;
		CardId = MoveTemp(Id); CardRevision = MoveTemp(Revision);
		View.Prompt = MoveTemp(Prompt); View.Context = MoveTemp(Context); View.Kind = MoveTemp(Kind);
		View.Answer.Reset(); View.bHasCard = true; View.bRevealed = false; View.DueCount = static_cast<int32>(Count);
		View.Status = TEXT("Recall your answer, then explicitly reveal it. Scores save only when you choose one.");
		return true;
	}
	bool ApplyReveal(const TSharedPtr<FJsonObject>& Value)
	{
		const auto* Card = Value.IsValid() ? Value->Values.Find(TEXT("card")) : nullptr;
		if (!Card || !Card->IsValid() || (*Card)->Type != EJson::Object) return false;
		const auto Object = (*Card)->AsObject();
		FString Type, Answer, Language;
		if (!SynapseWire::String(Object, TEXT("type"), Type, 8, false) || !SynapseWire::Kind(Type)
			|| !SynapseWire::Exact(Type, HasPending() ? PendingKind : View.Kind)) return false;
		if (SynapseWire::Exact(Type, TEXT("basic")))
		{
			if (!SynapseWire::String(Object, TEXT("answer"), Answer, SynapseWire::MaxTextBytes)) return false;
		}
		else if (SynapseWire::Exact(Type, TEXT("cloze")))
		{
			if (!SynapseWire::String(Object, TEXT("text"), Answer, SynapseWire::MaxTextBytes)) return false;
		}
		else
		{
			if (!SynapseWire::String(Object, TEXT("language"), Language, SynapseWire::MaxTextBytes)
				|| !SynapseWire::String(Object, TEXT("code"), Answer, SynapseWire::MaxTextBytes)) return false;
			const FTCHARToUTF8 LanguageBytes(*Language, Language.Len()), CodeBytes(*Answer, Answer.Len());
			if (LanguageBytes.Length() + CodeBytes.Length() > SynapseWire::MaxTextBytes) return false;
			View.Context = MoveTemp(Language); // Plain language label; never used to execute or fetch code.
		}
		View.Answer = MoveTemp(Answer); View.Kind = MoveTemp(Type); View.bHasCard = true; View.bRevealed = true;
		bPendingNeedsReveal = false;
		View.Status = HasPending()
			? TEXT("The original revision was explicitly revealed. Retry the same retained score/action; other scores remain locked.")
			: TEXT("Answer revealed as plain text. Choose an explicit score from 0 to 5 to save this review.");
		return true;
	}
	bool ApplyReceipt(const TSharedPtr<FJsonObject>& Value)
	{
		FString Action, Id, ReviewedAt, NextReview;
		uint64 Score = 0, Interval = 0;
		if (!HasPending() || !SynapseWire::String(Value, TEXT("action_id"), Action, 36, false) || !SynapseWire::Exact(Action, PendingActionId)
			|| !SynapseWire::String(Value, TEXT("card_id"), Id, 64) || !SynapseWire::Exact(Id, PendingCardId)
			|| !SynapseWire::Integer(Value, TEXT("score"), Score, 0, 5) || Score != static_cast<uint64>(PendingScore)
			|| !SynapseWire::True(Value, TEXT("persisted"))
			|| !SynapseWire::String(Value, TEXT("reviewed_at"), ReviewedAt, 64, false) || !SynapseWire::Timestamp(ReviewedAt)
			|| !SynapseWire::String(Value, TEXT("next_review"), NextReview, 64, false) || !SynapseWire::Timestamp(NextReview)
			|| !SynapseWire::Integer(Value, TEXT("interval_days"), Interval, 0, 4294967295ULL)) return false;
		// The protocol returns no revision field. The existing StudyService validates the frozen
		// action's revision before returning this matching action/card/score receipt.
		const FString Summary = FString::Printf(TEXT("Saved score %d. Next review: %s. Interval: %llu days."), PendingScore, *NextReview, static_cast<unsigned long long>(Interval));
		PendingBody.Reset(); PendingCardId.Reset(); PendingRevision.Reset(); PendingActionId.Reset(); PendingKind.Reset();
		bPendingNeedsReveal = false; PendingScore = 0;
		ClearCard(); View.bHasReceipt = true; View.ReceiptSummary = Summary;
		View.Status = TEXT("Synapse confirmed the review and receipt persisted together. Refresh for the next card and current due count.");
		return true;
	}
	void Complete(const TSharedPtr<FSynapseHttpTask, ESPMode::ThreadSafe>& Task)
	{
		using namespace SynapseWire;
		const auto Value = Json(*Task);
		if (Task->Generation != Generation)
		{
			// A complete session claim racing an explicit disconnect can still provide the capability
			// for revocation. It never restores visible cards, pairing controls or a stale save receipt.
			if (Task->Operation == EOperation::Session && bDisconnectWanted && Task->StatusCode == 200)
			{
				FString TokenValue;
				uint64 Count = 0, Seconds = 0;
				if (String(Value, TEXT("session"), TokenValue, 43, false) && Token(TokenValue)
					&& Integer(Value, TEXT("selected_count"), Count, 1, MaxCards) && Integer(Value, TEXT("expires_in_seconds"), Seconds, 0, 900))
				{
					Session = MoveTemp(TokenValue); bUnknownSession = false;
					ExpiresAt = FPlatformTime::Seconds() + static_cast<double>(Seconds);
				}
			}
			AdvanceDisconnect(); Controls(); return;
		}
		if (Task->bTransportOk && Task->StatusCode == 401)
		{
			ForgetGrant(HasPending()
				? TEXT("The desk no longer authorizes this session. Save outcome remains unknown. Pair a fresh selected track, then explicitly retry the same save before navigating.")
				: TEXT("The desk no longer authorizes this session. Enable a fresh selected track in Synapse and pair again."));
			return;
		}
		switch (Task->Operation)
		{
		case EOperation::Capabilities:
			if (Task->StatusCode == 200 && Capabilities(Value))
			{
				bUnknownSession = true;
				View.Status = TEXT("Claiming one private Synapse session...");
				Start(MakeRequest(EOperation::Session, TEXT("POST"), TEXT("/v1/session")));
			}
			else ForgetGrant(TEXT("Synapse capabilities were not verified. No session claim was requested; use a fresh link from the desktop app."));
			break;
		case EOperation::Session:
		{
			FString TokenValue;
			uint64 Count = 0, Seconds = 0;
			if (Task->StatusCode == 200 && String(Value, TEXT("session"), TokenValue, 43, false) && Token(TokenValue)
				&& Integer(Value, TEXT("selected_count"), Count, 1, MaxCards) && Integer(Value, TEXT("expires_in_seconds"), Seconds, 0, 900))
			{
				Session = MoveTemp(TokenValue); bUnknownSession = false; View.SelectedCount = static_cast<int32>(Count);
				ExpiresAt = FPlatformTime::Seconds() + static_cast<double>(Seconds);
				if (Seconds == 0) { bDisconnectWanted = true; bRevokeNeedsAttempt = true; }
				else if (HasPending()) View.Status = TEXT("Paired. A prior save is still unresolved. Explicitly retry the same save before reading a new card; no review is sent automatically.");
				else StartDue();
			}
			else
			{
				bUnknownSession = true;
				View.Status = TEXT("The single session claim was not confirmed or the link was already used. Obtain a fresh link from Synapse; no automatic claim retry is made.");
			}
			break;
		}
		case EOperation::Due:
			if (Task->StatusCode != 200 || !ApplyDue(Value))
			{
				ClearCard(); View.DueCount = 0;
				View.Status = TEXT("The due-card response was not confirmed. Refresh or reconnect; no answer or review was accepted.");
			}
			break;
		case EOperation::Reveal:
			if (Task->StatusCode != 200 || !ApplyReveal(Value))
			{
				View.Answer.Reset(); View.bRevealed = false;
				if (HasPending())
				{
					bPendingNeedsReveal = true;
					View.Status = TEXT("The original revision's reveal was not confirmed. The same save stays frozen; retry explicit Reveal or reconnect. No new score/action is permitted.");
				}
				else
				{
					ClearCard(); View.Status = TEXT("The card changed or its answer was not confirmed. Refresh before revealing or scoring.");
				}
			}
			break;
		case EOperation::Review:
			if (Task->StatusCode == 200 && ApplyReceipt(Value)) break;
			if (Task->StatusCode == 409 && Error(*Task, TEXT("reveal_required")))
			{
				bPendingNeedsReveal = true; View.bHasCard = true; View.bRevealed = false; View.Kind = PendingKind;
				View.Prompt = TEXT("Recover the retained review for the original selected card."); View.Context.Reset(); View.Answer.Reset();
				View.Status = TEXT("No matching saved receipt was returned. Explicitly reveal the original revision, then retry the same retained score/action. Navigation and other scores remain locked.");
			}
			else if (Task->StatusCode == 404 && Error(*Task, TEXT("card_unavailable")))
				View.Status = TEXT("The selected track does not expose the retained card. Save outcome remains unknown. Disconnect, select its original track in Synapse and pair fresh to retry the same save.");
			else if (Task->StatusCode == 409 && Error(*Task, TEXT("invalid_or_stale_action")))
				View.Status = TEXT("Synapse rejected the original action as stale or conflicting. No save receipt was confirmed. The action stays frozen; check Synapse or reconnect. Closing abandons recovery, not a saved review.");
			else View.Status = TEXT("Save was not confirmed. Retry the exact retained action to check or save once. Navigation and other scores remain locked; disconnect cannot undo an existing save.");
			break;
		case EOperation::Revoke:
			if (Task->StatusCode == 200 && True(Value, TEXT("revoked")))
				ForgetGrant(HasPending()
					? TEXT("Desk grant revoked. The retained review may already be saved. Pair fresh and retry the same save to resolve it; revocation does not undo reviews.")
					: TEXT("Synapse confirmed this desk grant was revoked. Existing saved reviews remain in the desktop app."));
			else
			{
				bRevokeUnconfirmed = true;
				View.Status = TEXT("Revocation was not confirmed. Retry Disconnect or pair a fresh link while retaining the unresolved save. Connection refusal is not a revoke receipt; Synapse controls expiry.");
			}
			break;
		default: break;
		}
		AdvanceDisconnect(); Controls();
	}
};

FDaedalusSynapseClient::FDaedalusSynapseClient() : Impl(MakeUnique<FImpl>()) {}
FDaedalusSynapseClient::~FDaedalusSynapseClient() { Shutdown(); }

FDaedalusSynapseView FDaedalusSynapseClient::GetView() const
{
	check(IsInGameThread());
	auto View = Impl->View;
	if (Impl->bPriorRevokeUnconfirmed)
		View.Status += TEXT(" A previous grant's revocation remains unconfirmed; the desktop controls its expiry.");
	return View;
}

bool FDaedalusSynapseClient::Pair(const FString& PairingLink)
{
	check(IsInGameThread()); Impl->Controls();
	if (!Impl->View.bCanPair) return false;
	const FTCHARToUTF8 Link(*PairingLink, PairingLink.Len());
	if (!daedalus::localapp::IsValidCompanionLink(std::string_view(Link.Get(), Link.Length()), daedalus::localapp::Kind::Synapse))
	{
		Impl->View.Status = TEXT("Use the literal typed loopback study-desk link supplied by Synapse."); return false;
	}
	if (!Impl->Origin.IsEmpty()) Impl->bPriorRevokeUnconfirmed = true;
	Impl->ForgetGrant(TEXT("Verifying the fresh Synapse study-desk capabilities..."));
	const FString Path(TEXT("/realm/synapse/"));
	const int32 PathAt = PairingLink.Find(Path, ESearchCase::CaseSensitive);
	Impl->Origin = PairingLink.Left(PathAt); Impl->PairToken = PairingLink.Mid(PathAt + Path.Len() + 7);
	Impl->Start(Impl->MakeRequest(SynapseWire::EOperation::Capabilities, TEXT("GET"), TEXT("/v1/capabilities")));
	return true;
}

void FDaedalusSynapseClient::Refresh()
{
	check(IsInGameThread()); Impl->Controls();
	if (Impl->View.bCanRefresh) Impl->StartDue();
}

void FDaedalusSynapseClient::Reveal()
{
	check(IsInGameThread()); Impl->Controls();
	if (!Impl->View.bCanReveal) return;
	const FString& Id = Impl->HasPending() ? Impl->PendingCardId : Impl->CardId;
	const FString& Revision = Impl->HasPending() ? Impl->PendingRevision : Impl->CardRevision;
	auto Body = SynapseWire::CardBody(Id, Revision);
	if (!Body.IsValid()) { Impl->View.Status = TEXT("The card action exceeded the native request boundary. Nothing was submitted."); return; }
	auto Task = Impl->MakeRequest(SynapseWire::EOperation::Reveal, TEXT("POST"), TEXT("/v1/reveal"));
	Task->RequestBody = MoveTemp(Body);
	Impl->View.Status = TEXT("Requesting an explicit reveal of this exact card revision...");
	Impl->Start(Task);
}

void FDaedalusSynapseClient::Score(int32 Value)
{
	check(IsInGameThread()); Impl->Controls();
	if (!Impl->View.bCanScore || Value < 0 || Value > 5) return;
	const FString ActionId = FGuid::NewGuid().ToString(EGuidFormats::DigitsWithHyphensLower);
	auto Json = MakeShared<FJsonObject>();
	Json->SetStringField(TEXT("card_id"), Impl->CardId); Json->SetStringField(TEXT("revision"), Impl->CardRevision);
	Json->SetNumberField(TEXT("score"), Value); Json->SetStringField(TEXT("action_id"), ActionId);
	auto Body = SynapseWire::Body(Json);
	if (!Body.IsValid()) { Impl->View.Status = TEXT("The review exceeded the native request boundary. Nothing was submitted."); return; }
	Impl->ClearReceipt();
	Impl->PendingCardId = Impl->CardId; Impl->PendingRevision = Impl->CardRevision;
	Impl->PendingActionId = ActionId; Impl->PendingScore = Value; Impl->PendingKind = Impl->View.Kind;
	Impl->PendingBody = MoveTemp(Body); Impl->bPendingNeedsReveal = false;
	Impl->StartReview();
}

void FDaedalusSynapseClient::RetrySameSave()
{
	check(IsInGameThread()); Impl->Controls();
	if (Impl->View.bCanRetry) Impl->StartReview();
}

void FDaedalusSynapseClient::Disconnect()
{
	check(IsInGameThread());
	if (Impl->bStopped || Impl->Origin.IsEmpty()) return;
	++Impl->Generation; Impl->bDisconnectWanted = true; Impl->bRevokeNeedsAttempt = true;
	Impl->bPendingNeedsReveal = false; Impl->ClearVisible();
	if (Impl->Active.IsValid()) Impl->Active->bCancelled.Store(true);
	Impl->View.Status = TEXT("Disconnect requested. Revocation is pending; any retained save outcome remains unknown and saved reviews are not undone.");
	Impl->AdvanceDisconnect(); Impl->Controls();
}

void FDaedalusSynapseClient::Shutdown()
{
	if (!Impl.IsValid() || Impl->bStopped) return;
	Impl->bStopped = true; ++Impl->Generation;
	TSharedPtr<FSynapseHttpTask, ESPMode::ThreadSafe> Cleanup;
	if (!Impl->Session.IsEmpty())
	{
		Cleanup = Impl->MakeRequest(SynapseWire::EOperation::Revoke, TEXT("POST"), TEXT("/v1/revoke"));
		Cleanup->TimeoutMilliseconds = 3000;
	}
	if (Impl->Active.IsValid())
	{
		if (Cleanup.IsValid()) Impl->Active->RevokeAfter(Cleanup);
		Impl->Active->bCancelled.Store(true); Impl->Active.Reset();
	}
	else if (Cleanup.IsValid()) Async(EAsyncExecution::ThreadPool, [Cleanup]() { Cleanup->Run(); });
	const bool bAbandoningSave = Impl->HasPending();
	Impl->PendingBody.Reset(); Impl->PendingCardId.Reset(); Impl->PendingRevision.Reset(); Impl->PendingActionId.Reset(); Impl->PendingKind.Reset(); Impl->PendingScore = 0;
	Impl->ForgetGrant(bAbandoningSave
		? TEXT("Terminal closed. Transient save recovery was abandoned; the review may already be saved. Revocation is best effort and does not undo a review.")
		: TEXT("Terminal closed. Revocation is best effort and unconfirmed; the desktop controls grant expiry. Existing saved reviews remain."));
	Impl->Controls();
}

void FDaedalusSynapseClient::Tick()
{
	check(IsInGameThread());
	if (Impl->bStopped) return;
	if (Impl->Active.IsValid() && Impl->Active->bDone.Load())
	{
		auto Task = MoveTemp(Impl->Active); Impl->Complete(Task);
	}
	if (!Impl->Session.IsEmpty() && !Impl->bDisconnectWanted && Impl->ExpiresAt > 0 && FPlatformTime::Seconds() >= Impl->ExpiresAt)
		Disconnect(); // Server authority/revoke response decides availability; clock is not a save receipt.
	Impl->Controls();
}
