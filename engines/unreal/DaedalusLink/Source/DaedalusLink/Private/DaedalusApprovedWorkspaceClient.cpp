// SPDX-License-Identifier: MIT
#include "DaedalusApprovedWorkspaceClient.h"
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
namespace ApprovedWorkspaceWire
{
    constexpr int32 MaxJsonBytes = 128 * 1024;
    enum class EOperation : uint8 { Capabilities, Plan, Start, Action, Cancel, Revoke };
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
    bool Link(const FString& Value, bool bPhoto, FString& Origin, FString& Capability)
    {
        const FString Prefix(TEXT("http://127.0.0.1:"));
        const FString Suffix = bPhoto ? TEXT("/realm/photo-workspace/#token=") : TEXT("/realm/image-workspace/#token=");
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
    bool Flag(const TSharedPtr<FJsonObject>& Json, const TCHAR* Name, bool& Out)
    {
        const auto* Field = Json.IsValid() ? Json->Values.Find(Name) : nullptr;
        return Field && Field->IsValid() && (*Field)->Type == EJson::Boolean && (*Field)->TryGetBool(Out);
    }
    bool ExactArray(const TSharedPtr<FJsonObject>& Json, const TCHAR* Field, const TArray<FString>& Expected)
    {
        const TArray<TSharedPtr<FJsonValue>>* Values = nullptr;
        if (!Json.IsValid() || !Json->TryGetArrayField(Field, Values) || !Values || Values->Num() != Expected.Num()) return false;
        TSet<FString> Seen;
        for (const auto& Value : *Values)
        {
            FString Text;
            if (!Value.IsValid() || Value->Type != EJson::String || !Value->TryGetString(Text)
                || !Expected.Contains(Text) || Seen.Contains(Text)) return false;
            Seen.Add(Text);
        }
        return true;
    }
    bool Limit(const TSharedPtr<FJsonObject>& Json, const TCHAR* Name, int32 Expected)
    {
        int32 Value = 0; return Integer(Json, Name, Value, Expected, Expected);
    }
    bool Capabilities(const TSharedPtr<FJsonObject>& Json, bool bPhoto)
    {
        FString Product, Protocol, Mode;
        if (!String(Json, TEXT("productId"), Product, 32) || !Exact(Product, bPhoto ? TEXT("photos-to-pdf-pc") : TEXT("image-optimizer"))
            || !String(Json, TEXT("protocol"), Protocol, 40) || !Exact(Protocol, bPhoto ? TEXT("photospdf.workspace.v1") : TEXT("imageoptimizer.workspace.v1"))
            || !String(Json, bPhoto ? TEXT("outputMode") : TEXT("mode"), Mode, 32) || !Exact(Mode, TEXT("desktop_approved_plan"))) return false;
        if (bPhoto)
        {
            const TSharedPtr<FJsonObject>* Limits = nullptr;
            if (!ExactArray(Json, TEXT("capabilities"), {TEXT("workspace.read"),TEXT("workspace.start"),TEXT("workspace.cancel"),TEXT("workspace.outputs.read")})
                || !Json->TryGetObjectField(TEXT("limits"), Limits) || !Limits || !Limits->IsValid()) return false;
            return Limit(*Limits,TEXT("maxImages"),32) && Limit(*Limits,TEXT("maxFileBytes"),8388608)
                && Limit(*Limits,TEXT("maxSourceBytes"),67108864) && Limit(*Limits,TEXT("maxDimension"),4096)
                && Limit(*Limits,TEXT("maxPixelsPerImage"),12000000) && Limit(*Limits,TEXT("maxPixelsPerPlan"),48000000)
                && Limit(*Limits,TEXT("maxPdfBytes"),268435456) && Limit(*Limits,TEXT("maxOutputBytes"),268435456)
                && Limit(*Limits,TEXT("maxDepth"),0) && Limit(*Limits,TEXT("ttlSeconds"),900);
        }
        return ExactArray(Json,TEXT("capabilities"),{TEXT("image.optimize.workspace")})
            && ExactArray(Json,TEXT("permissions"),{TEXT("plan.read"),TEXT("job.start"),TEXT("job.read"),TEXT("job.cancel"),TEXT("output.read"),TEXT("grant.revoke")})
            && Limit(Json,TEXT("maxFiles"),256) && Limit(Json,TEXT("maxDepth"),16) && Limit(Json,TEXT("maxEntries"),4096)
            && Limit(Json,TEXT("maxDirectories"),512) && Limit(Json,TEXT("maxFileBytes"),8388608) && Limit(Json,TEXT("maxSourceBytes"),268435456)
            && Limit(Json,TEXT("maxDimension"),4096) && Limit(Json,TEXT("maxPixelsPerImage"),12000000) && Limit(Json,TEXT("maxPixelsPerPlan"),128000000)
            && Limit(Json,TEXT("maxOutputBytesPerImage"),33554432) && Limit(Json,TEXT("maxOutputBytesPerPlan"),268435456);
    }
    bool Terminal(const FString& State) { return Exact(State,TEXT("SUCCEEDED")) || Exact(State,TEXT("FAILED")) || Exact(State,TEXT("CANCELED")); }
    bool State(const FString& State)
    {
        return Terminal(State) || Exact(State,TEXT("APPROVED")) || Exact(State,TEXT("QUEUED"))
            || Exact(State,TEXT("RUNNING")) || Exact(State,TEXT("CANCEL_REQUESTED"));
    }
}
/** Worker owns wire data only. Client/UObjects are never captured by asynchronous work. */
class FApprovedWorkspaceHttpTask : public TSharedFromThis<FApprovedWorkspaceHttpTask, ESPMode::ThreadSafe>
{
public:
	ApprovedWorkspaceWire::EOperation Operation = ApprovedWorkspaceWire::EOperation::Capabilities;
	uint64 Generation = 0;
	double RequestedAt = FPlatformTime::Seconds();
	FString Url, Verb, ContentType, ContentDisposition, ExpectedDigest;
	TArray<FString> RequestHeaders;
	TArray<uint8> Response;
	SIZE_T HeaderBytes = 0;
	int32 Limit = ApprovedWorkspaceWire::MaxJsonBytes, StatusCode = 0, TimeoutMilliseconds = 30000;
	int32 TypeHeaders = 0, LengthHeaders = 0, DispositionHeaders = 0;
	bool bTransportOk = false, bRedirect = false, bPdfOk = false;
	TAtomic<bool> bCancelled{false}, bDone{false};
	static SIZE_T Write(char* Data, SIZE_T Size, SIZE_T Count, void* User)
	{
		auto* Task = static_cast<FApprovedWorkspaceHttpTask*>(User);
		if (Task->bCancelled.Load() || (Count > 0 && Size > static_cast<SIZE_T>(Task->Limit) / Count)) return 0;
		const SIZE_T Bytes = Size * Count;
		if (Bytes > static_cast<SIZE_T>(Task->Limit - Task->Response.Num())) return 0;
		Task->Response.Append(reinterpret_cast<const uint8*>(Data), static_cast<int32>(Bytes)); return Bytes;
	}
	static SIZE_T Header(char* Data, SIZE_T Size, SIZE_T Count, void* User)
	{
		auto* Task = static_cast<FApprovedWorkspaceHttpTask*>(User);
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
		return static_cast<FApprovedWorkspaceHttpTask*>(User)->bCancelled.Load() ? 1 : 0;
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
			if (!ApprovedWorkspaceWire::Exact(Verb, TEXT("GET")))
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
		RequestHeaders.Reset(); Url.Reset(); ExpectedDigest.Reset();
		TSharedPtr<FApprovedWorkspaceHttpTask, ESPMode::ThreadSafe> Cleanup;
		{ FScopeLock Scope(&CleanupLock); bWireFinished = true; Cleanup = MoveTemp(FinalRevoke); }
		bDone.Store(true);
		if (Cleanup.IsValid()) Cleanup->Run();
	}
	void RevokeAfter(const TSharedPtr<FApprovedWorkspaceHttpTask, ESPMode::ThreadSafe>& Cleanup)
	{
		bool bStartNow = false;
		{ FScopeLock Scope(&CleanupLock); if (bWireFinished) bStartNow = true; else FinalRevoke = Cleanup; }
		if (bStartNow) Async(EAsyncExecution::ThreadPool, [Cleanup]() { Cleanup->Run(); });
	}
private:
	FCriticalSection CleanupLock;
	bool bWireFinished = false;
	TSharedPtr<FApprovedWorkspaceHttpTask, ESPMode::ThreadSafe> FinalRevoke;
};


class FDaedalusApprovedWorkspaceClient::FImpl
{
public:
    explicit FImpl(bool InPhoto) : bPhoto(InPhoto) { View.Status = TEXT("Approve the files, settings and destination in the desktop app, then paste its workspace link."); }
    const bool bPhoto;
    FDaedalusApprovedWorkspaceView View;
    FString Origin, Token, Identity, Key, CapabilityExpiry;
    FDateTime Expiry;
    double Deadline = 0;
    uint64 Generation = 1;
    bool bStopped = false, bVerified = false, bTrustedOrigin = false, bBlocked = false, bStarted = false;
    TSharedPtr<FApprovedWorkspaceHttpTask, ESPMode::ThreadSafe> Active;
    FString Prefix() const { return bPhoto ? TEXT("/v1/") : TEXT("/v1/workspace/"); }
    bool Expired() const { return Deadline > 0 && (FPlatformTime::Seconds() >= Deadline || FDateTime::UtcNow() >= Expiry); }
    void Controls()
    {
        const bool Ready = !bStopped && bVerified && !bBlocked && !Expired() && !Token.IsEmpty();
        View.bBusy = Active.IsValid(); View.bPaired = Ready;
        View.bCanPair = !bStopped && Origin.IsEmpty() && !Active.IsValid();
        View.bCanRefresh = Ready && !Active.IsValid();
        // Retry is deliberate and retains the one key. Canceled/terminal work cannot start again.
        View.bCanStart = View.bCanRefresh && ApprovedWorkspaceWire::Exact(View.State,TEXT("APPROVED"));
        View.bCanCancel = View.bCanRefresh && !View.bCancelRequested && !ApprovedWorkspaceWire::Terminal(View.State)
            && (bPhoto || !View.ActionId.IsEmpty());
        View.bCanDisconnect = !bStopped && !Origin.IsEmpty()
            && (!Active.IsValid() || Active->Operation != ApprovedWorkspaceWire::EOperation::Revoke);
    }
    TSharedPtr<FApprovedWorkspaceHttpTask, ESPMode::ThreadSafe> Request(ApprovedWorkspaceWire::EOperation Operation, const TCHAR* Verb, const FString& Path)
    {
        auto Task = MakeShared<FApprovedWorkspaceHttpTask, ESPMode::ThreadSafe>();
        Task->Operation = Operation; Task->Generation = Generation; Task->Url = Origin + Path; Task->Verb = Verb;
        Task->RequestHeaders = {TEXT("Authorization: Bearer ") + Token, TEXT("Origin: ") + Origin, TEXT("Accept: application/json"),TEXT("Cache-Control: no-store")};
        return Task;
    }
    void Launch(const TSharedPtr<FApprovedWorkspaceHttpTask, ESPMode::ThreadSafe>& Task)
    {
        check(!Active.IsValid()); Active = Task;
        Async(EAsyncExecution::ThreadPool,[Task]() { Task->Run(); }); Controls();
    }
    void Denied(const TCHAR* Reason)
    {
        bBlocked = true; View.bUncertain = true; View.Status = Reason; Controls();
    }
    bool ReadCounts(const TSharedPtr<FJsonObject>& Json, bool bPhotoPlan)
    {
        using namespace ApprovedWorkspaceWire;
        FString StateValue;
        int32 Total = 0, Completed = 0, Failed = 0, Saved = 0, Duplicate = 0, Existing = 0, Conflicts = 0, Canceled = 0;
        bool CancelRequested = false;
        const int32 Max = bPhoto ? 32 : 256;
        if (!String(Json,TEXT("state"),StateValue,32) || !State(StateValue)
            || !Integer(Json,TEXT("total"),Total,1,Max) || Total != View.Total
            || !Integer(Json,TEXT("completed"),Completed,0,Total) || !Integer(Json,TEXT("failed"),Failed,0,Total)) return false;
        if (bPhotoPlan)
        {
            // Photo completed includes failed inputs. Commit receipts can precede the progress callback.
            if (!Integer(Json,TEXT("saved"),Saved,0,Total)) return false;
        }
        else
        {
            FString Id, Plan;
            if (!String(Json,TEXT("id"),Id,36) || !Uuid(Id) || !String(Json,TEXT("planId"),Plan,36) || !Exact(Plan,View.PlanId)
                || (!View.ActionId.IsEmpty() && !Exact(Id,View.ActionId))
                || !Integer(Json,TEXT("optimized"),Saved,0,Total) || !Integer(Json,TEXT("skippedDuplicate"),Duplicate,0,Total)
                || !Integer(Json,TEXT("skippedExisting"),Existing,0,Total) || !Integer(Json,TEXT("destinationConflicts"),Conflicts,0,Failed)
                || !Integer(Json,TEXT("canceled"),Canceled,0,Total) || !Flag(Json,TEXT("cancelRequested"),CancelRequested)
                || Completed != Saved + Duplicate + Existing) return false;
            View.ActionId = Id;
        }
        if (!bPhotoPlan && Completed + Failed + Canceled > Total) return false;
        const TArray<TSharedPtr<FJsonValue>>* Outputs = nullptr;
        if (!Json->TryGetArrayField(TEXT("outputs"),Outputs) || !Outputs || Outputs->Num() > Total) return false;
        // Output files stay in the desktop-approved destination. Never follow returned paths or URLs.
        View.State = StateValue; View.Completed = Completed; View.Failed = Failed; View.Saved = Saved;
        View.Skipped = Duplicate + Existing; View.Conflicts = Conflicts;
        View.Canceled = Canceled; View.bHasCanceledCount = !bPhotoPlan;
        View.bCancelRequested = bPhotoPlan ? Exact(StateValue,TEXT("CANCEL_REQUESTED")) : CancelRequested;
        View.bUncertain = false;
        View.Status = Terminal(View.State)
            ? TEXT("The desktop app reports this final result. Saved files remain in its approved destination; failures and skips are shown separately.")
            : TEXT("This is the approved desktop plan. Start once, refresh its actual progress, or request cancellation.");
        return true;
    }
    bool ReadPlan(const TSharedPtr<FJsonObject>& Json, double RequestedAt)
    {
        using namespace ApprovedWorkspaceWire;
        FString Id, Expires, PlanIdentity;
        int32 Total = 0;
        FDateTime PlanExpiry;
        if (!String(Json,TEXT("id"),Id,36) || !Uuid(Id) || !Integer(Json,TEXT("total"),Total,1,bPhoto ? 32 : 256)
            || !String(Json,TEXT("expiresAt"),Expires,30) || !Instant(Expires,PlanExpiry) || PlanExpiry <= FDateTime::UtcNow()
            || PlanExpiry > FDateTime::UtcNow() + FTimespan::FromMinutes(16)
            || (bPhoto && !Exact(Expires,CapabilityExpiry))) return false;
        PlanIdentity = Id + TEXT("|") + Expires + TEXT("|") + FString::FromInt(Total);
        double WireDeadline = 0;
        if (!bPhoto)
        {
            int32 RemainingMilliseconds=0;
            if (!Integer(Json,TEXT("expiresInMilliseconds"),RemainingMilliseconds,1,900000)) return false;
            // Budget the server's remaining monotonic lease from REQUEST START, never response receipt.
            WireDeadline=RequestedAt+static_cast<double>(RemainingMilliseconds)/1000.0;
            if (WireDeadline <= FPlatformTime::Seconds()) return false;
            if (Deadline > 0) Deadline=FMath::Min(Deadline,WireDeadline);
        }
        FString Action, Mode, Settings;
        if (bPhoto)
        {
            bool Approved = false;
            if (!Flag(Json,TEXT("destinationApproved"),Approved) || !Approved || !String(Json,TEXT("actionId"),Action,36) || !Uuid(Action)
                || !String(Json,TEXT("mode"),Mode,40)) return false;
            if (!Exact(Mode,TEXT("individual_image_size")) && !Exact(Mode,TEXT("merged_a4_portrait")) && !Exact(Mode,TEXT("merged_a4_landscape"))) return false;
            const TArray<TSharedPtr<FJsonValue>>* Items = nullptr;
            if (!Json->TryGetArrayField(TEXT("items"),Items) || !Items || Items->Num() != Total) return false;
            PlanIdentity += TEXT("|") + Action + TEXT("|") + Mode;
            TSet<FString> Ids; int64 BytesTotal = 0, Pixels = 0;
            for (int32 Index = 0; Index < Items->Num(); ++Index)
            {
                if (!(*Items)[Index].IsValid() || (*Items)[Index]->Type != EJson::Object) return false;
                const auto Item = (*Items)[Index]->AsObject(); FString ItemId;
                int32 At=0,Width=0,Height=0,Bytes=0;
                if (!String(Item,TEXT("id"),ItemId,36) || !Uuid(ItemId) || Ids.Contains(ItemId)
                    || !Integer(Item,TEXT("index"),At,Index+1,Index+1) || !Integer(Item,TEXT("width"),Width,1,4096)
                    || !Integer(Item,TEXT("height"),Height,1,4096) || !Integer(Item,TEXT("sourceBytes"),Bytes,1,8388608)
                    || static_cast<int64>(Width)*Height > 12000000) return false;
                Ids.Add(ItemId); BytesTotal += Bytes; Pixels += static_cast<int64>(Width)*Height;
                PlanIdentity += FString::Printf(TEXT("|%s:%d:%d:%d:%d"),*ItemId,At,Width,Height,Bytes);
            }
            if (BytesTotal > 67108864 || Pixels > 48000000) return false;
        }
        else
        {
            const TSharedPtr<FJsonObject>* Values = nullptr;
            bool Convert=false,Resize=false,Skip=false,Duplicates=false; int32 Width=0,Quality=0;
            if (!Json->TryGetObjectField(TEXT("settings"),Values) || !Values || !Values->IsValid()
                || !Flag(*Values,TEXT("convertPng"),Convert) || !Flag(*Values,TEXT("resize"),Resize)
                || !Flag(*Values,TEXT("skipOptimized"),Skip) || !Flag(*Values,TEXT("detectDuplicates"),Duplicates)
                || !Integer(*Values,TEXT("maxWidth"),Width,1,4096) || !Integer(*Values,TEXT("quality"),Quality,70,95)) return false;
            Settings = FString::Printf(TEXT("Quality %d; resize %s (max %d); PNG to JPEG %s; skip existing %s; duplicate detection %s"),
                Quality,Resize?TEXT("on"):TEXT("off"),Width,Convert?TEXT("on"):TEXT("off"),Skip?TEXT("on"):TEXT("off"),Duplicates?TEXT("on"):TEXT("off"));
            PlanIdentity += TEXT("|") + Settings;
            const auto* Field = Json->Values.Find(TEXT("actionId"));
            if (!Field || !Field->IsValid()) return false;
            if ((*Field)->Type != EJson::Null && (!String(Json,TEXT("actionId"),Action,36) || !Uuid(Action))) return false;
            if (!View.ActionId.IsEmpty() && !Exact(Action,View.ActionId)) return false;
            Mode = TEXT("Approved image destination");
        }
        if (!Identity.IsEmpty() && !Exact(Identity,PlanIdentity)) return false;
        if (Identity.IsEmpty())
        {
            Identity = PlanIdentity; View.PlanId = Id; View.Total = Total; View.ExpiresAt = Expires;
            View.Mode = Mode; View.Settings = Settings; Expiry = PlanExpiry;
            Deadline = FPlatformTime::Seconds() + FMath::Clamp((PlanExpiry-FDateTime::UtcNow()).GetTotalSeconds(),0.0,900.0);
            if (!bPhoto) Deadline=FMath::Min(Deadline,WireDeadline);
            if (bPhoto) Key = Action;
        }
        View.ActionId = Action;
        if (bPhoto) return ReadCounts(Json,true);
        if (Action.IsEmpty())
        {
            View.State = TEXT("APPROVED"); View.Status = TEXT("The destination and settings were frozen in the desktop app. Start this approved plan once.");
            // An empty plan lookup permits a deliberate retry with the same key, never a new key.
            Controls(); return true;
        }
        bStarted = true;
        Launch(Request(EOperation::Action,TEXT("GET"),Prefix()+TEXT("actions/")+Action));
        return true;
    }
    void Complete(const TSharedPtr<FApprovedWorkspaceHttpTask, ESPMode::ThreadSafe>& Task)
    {
        using namespace ApprovedWorkspaceWire;
        if (Task->Generation != Generation || bStopped) return;
        if (Task->Operation == EOperation::Revoke)
        {
            const bool Confirmed = Task->bTransportOk && Task->StatusCode == 200;
            Origin.Reset(); Token.Reset(); Identity.Reset(); Key.Reset(); CapabilityExpiry.Reset(); bVerified = false;
            bBlocked=false; bStarted=false; bTrustedOrigin=false; Deadline=0;
            View = {}; View.Status = Confirmed ? TEXT("Local access revoked. Already saved files remain in the approved destination.")
                : TEXT("Disconnected locally; revocation was not confirmed. The app's expiry remains authoritative."); Controls(); return;
        }
        if (!Task->bTransportOk || Task->StatusCode < 200 || Task->StatusCode >= 300 || !Exact(Task->ContentType,TEXT("application/json")))
        {
            View.bUncertain = true;
            View.Status = TEXT("The local request was not confirmed. Refresh to reconcile; a retry keeps the same action key.");
            if (Task->StatusCode == 401 || Task->StatusCode == 403) bBlocked = true;
            if (Task->Operation == EOperation::Capabilities) bBlocked = true;
            Controls(); return;
        }
        const auto Json = Parse(Task->Response);
        if (Task->Operation == EOperation::Capabilities)
        {
            if (!Capabilities(Json,bPhoto)) { Denied(TEXT("The app's workspace identity, permissions or limits do not match.")); return; }
            if (bPhoto)
            {
                FDateTime CapExpiry;
                if (!String(Json,TEXT("grantExpiresAt"),CapabilityExpiry,30) || !Instant(CapabilityExpiry,CapExpiry)
                    || CapExpiry <= FDateTime::UtcNow()) { Denied(TEXT("The approved workspace grant is expired or invalid.")); return; }
            }
            bTrustedOrigin = true; bVerified = true; Launch(Request(EOperation::Plan,TEXT("GET"),Prefix()+TEXT("plan"))); return;
        }
        bool Valid = false;
        if (Task->Operation == EOperation::Plan || bPhoto) Valid = ReadPlan(Json,Task->RequestedAt);
        else Valid = ReadCounts(Json,false);
        if (!Valid) { Denied(TEXT("The approved plan or job result changed or exceeded its contract. Disconnect and approve a new plan on the desktop.")); return; }
        Controls();
    }
};
FDaedalusApprovedWorkspaceClient::FDaedalusApprovedWorkspaceClient(bool bPhoto) : Impl(MakeUnique<FImpl>(bPhoto)) {}
FDaedalusApprovedWorkspaceClient::~FDaedalusApprovedWorkspaceClient() { Shutdown(); }
FDaedalusApprovedWorkspaceView FDaedalusApprovedWorkspaceClient::GetView() const { check(IsInGameThread()); return Impl->View; }
bool FDaedalusApprovedWorkspaceClient::Pair(const FString& Link)
{
    using namespace ApprovedWorkspaceWire; check(IsInGameThread()); Impl->Controls();
    if (!Impl->View.bCanPair) return false;
    FString Origin,Token;
    if (!ApprovedWorkspaceWire::Link(Link,Impl->bPhoto,Origin,Token)) { Impl->View.Status=TEXT("Use the exact workspace link from this object's desktop app."); return false; }
    Impl->Origin=Origin; Impl->Token=Token; Impl->Key=FGuid::NewGuid().ToString(EGuidFormats::DigitsWithHyphensLower);
    Impl->Launch(Impl->Request(EOperation::Capabilities,TEXT("GET"),Impl->Prefix()+TEXT("capabilities"))); return true;
}
void FDaedalusApprovedWorkspaceClient::StartOrRetry()
{
    using namespace ApprovedWorkspaceWire; check(IsInGameThread()); Impl->Controls(); if (!Impl->View.bCanStart) return;
    Impl->bStarted=true;
    const FString Path = Impl->bPhoto ? TEXT("/v1/plans/")+Impl->View.PlanId+TEXT("/start") : Impl->Prefix()+TEXT("actions");
    auto Task=Impl->Request(EOperation::Start,TEXT("POST"),Path); Task->RequestHeaders.Add(TEXT("Idempotency-Key: ")+Impl->Key); Impl->Launch(Task);
}
void FDaedalusApprovedWorkspaceClient::Refresh()
{
    using namespace ApprovedWorkspaceWire; check(IsInGameThread()); Impl->Controls();
    if (Impl->View.bCanRefresh) Impl->Launch(Impl->Request(EOperation::Plan,TEXT("GET"),Impl->Prefix()+TEXT("plan")));
}
void FDaedalusApprovedWorkspaceClient::Cancel()
{
    using namespace ApprovedWorkspaceWire; check(IsInGameThread()); Impl->Controls(); if (!Impl->View.bCanCancel) return;
    const FString Path = Impl->bPhoto ? TEXT("/v1/plans/")+Impl->View.PlanId+TEXT("/cancel") : Impl->Prefix()+TEXT("actions/")+Impl->View.ActionId;
    Impl->Launch(Impl->Request(EOperation::Cancel,Impl->bPhoto?TEXT("POST"):TEXT("DELETE"),Path));
}
void FDaedalusApprovedWorkspaceClient::Disconnect()
{
    using namespace ApprovedWorkspaceWire; check(IsInGameThread()); Impl->Controls(); if (!Impl->View.bCanDisconnect) return;
    if (!Impl->bTrustedOrigin)
    {
        ++Impl->Generation;
        if (Impl->Active.IsValid()) Impl->Active->bCancelled.Store(true);
        Impl->Active.Reset(); Impl->Origin.Reset(); Impl->Token.Reset(); Impl->Key.Reset();
        Impl->Identity.Reset(); Impl->CapabilityExpiry.Reset(); Impl->Deadline=0;
        Impl->bBlocked=false; Impl->bStarted=false; Impl->bVerified=false;
        Impl->View={}; Impl->View.Status=TEXT("Disconnected locally. No mutation was sent to an unverified app."); Impl->Controls(); return;
    }
    auto Cleanup=Impl->Request(EOperation::Revoke,TEXT("DELETE"),Impl->Prefix()+TEXT("grant")); Cleanup->TimeoutMilliseconds=3000;
    ++Impl->Generation; Cleanup->Generation=Impl->Generation;
    if (Impl->Active.IsValid()) { Impl->Active->bCancelled.Store(true); Impl->Active->RevokeAfter(Cleanup); Impl->Active=Cleanup; Impl->Controls(); }
    else Impl->Launch(Cleanup);
    Impl->bVerified=false; Impl->View.bUncertain=true; Impl->View.Status=TEXT("Disconnecting local access; saved files remain in the approved destination."); Impl->Controls();
}
void FDaedalusApprovedWorkspaceClient::Tick()
{
    check(IsInGameThread()); if (Impl->bStopped) return;
    if (Impl->Active.IsValid() && Impl->Active->bDone.Load()) { auto Task=MoveTemp(Impl->Active); Impl->Complete(Task); }
    if (Impl->Expired() && !Impl->bBlocked) { Impl->bBlocked=true; Impl->View.Status=TEXT("The workspace grant expired. Approve a new plan in the desktop app."); }
    Impl->Controls();
}
void FDaedalusApprovedWorkspaceClient::Shutdown()
{
    if (!Impl.IsValid() || Impl->bStopped) return; check(IsInGameThread());
    if (!Impl->Origin.IsEmpty() && Impl->View.bCanDisconnect) Disconnect();
    Impl->bStopped=true; ++Impl->Generation;
    // The wire task is self-owned; an already queued best-effort revoke may finish after this object is gone.
    if (Impl->Active.IsValid() && Impl->Active->Operation != ApprovedWorkspaceWire::EOperation::Revoke) Impl->Active->bCancelled.Store(true);
    Impl->Active.Reset(); Impl->Token.Reset(); Impl->Origin.Reset(); Impl->Identity.Reset(); Impl->Key.Reset(); Impl->View={};
}
