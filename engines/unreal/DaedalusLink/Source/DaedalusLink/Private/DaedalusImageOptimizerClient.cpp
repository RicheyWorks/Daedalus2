// SPDX-License-Identifier: MIT
#include "DaedalusImageOptimizerClient.h"

#include "DaedalusLocalAppCore.h"
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

namespace ImageOptimizerWire
{
	constexpr int32 MaxFiles = 8;
	constexpr int32 MaxFileBytes = 8 * 1024 * 1024;
	constexpr int32 MaxBatchBytes = 24 * 1024 * 1024;
	constexpr int32 MaxJsonBytes = 32768;
	constexpr int32 MaxOutputBytes = 32 * 1024 * 1024; // Whole job, not per output.
	constexpr int32 FixedHeaderBytes = 15;
	enum class EOperation : uint8 { Capabilities, Session, Submit, Refresh, Cancel, Download, Revoke };

	bool Exact(const FString& Left, const FString& Right)
	{
		return Left.Len() == Right.Len() && (Left.IsEmpty()
			|| FMemory::Memcmp(*Left, *Right, static_cast<SIZE_T>(Left.Len()) * sizeof(TCHAR)) == 0);
	}
	bool String(const TSharedPtr<FJsonObject>& Json, const TCHAR* Name, FString& Out, int32 Maximum)
	{
		const auto* Value = Json.IsValid() ? Json->Values.Find(Name) : nullptr;
		if (!Value || !Value->IsValid() || (*Value)->Type != EJson::String || !(*Value)->TryGetString(Out)
			|| Out.IsEmpty() || Out.Len() > Maximum) return false;
		for (TCHAR C : Out) if (C == 0) return false;
		return true;
	}
	bool Integer(const TSharedPtr<FJsonObject>& Json, const TCHAR* Name, int32& Out, int32 Minimum, int32 Maximum)
	{
		double Number = 0;
		const auto* Value = Json.IsValid() ? Json->Values.Find(Name) : nullptr;
		if (!Value || !Value->IsValid() || (*Value)->Type != EJson::Number || !(*Value)->TryGetNumber(Number)
			|| !FMath::IsFinite(Number) || Number < Minimum || Number > Maximum || FMath::FloorToDouble(Number) != Number) return false;
		Out = static_cast<int32>(Number); return true;
	}
	bool ExactInteger(const TSharedPtr<FJsonObject>& Json, const TCHAR* Name, int32 Expected)
	{
		int32 Value = 0; return Integer(Json, Name, Value, Expected, Expected);
	}
	bool Token(const FString& Value)
	{
		if (Value.Len() != 43) return false;
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
	bool Settings(const FDaedalusImageOptimizerSettings& Value)
	{
		return Value.Quality >= 70 && Value.Quality <= 95 && Value.Width >= 1 && Value.Width <= 4096 && Value.Format <= 2;
	}
	bool Dimensions(int32 Width, int32 Height)
	{
		return Width >= 1 && Height >= 1 && Width <= 4096 && Height <= 4096 && static_cast<int64>(Width) * Height <= 12000000;
	}
	bool Terminal(const FString& State)
	{
		return Exact(State, TEXT("SUCCEEDED")) || Exact(State, TEXT("FAILED")) || Exact(State, TEXT("CANCELED"));
	}
	TSharedPtr<FJsonObject> Parse(const TArray<uint8>& Bytes)
	{
		if (Bytes.IsEmpty() || Bytes.Num() > MaxJsonBytes) return nullptr;
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
		TSharedPtr<FJsonObject> Result;
		return FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(FString(Converted.Length(), Converted.Get())), Result) ? Result : nullptr;
	}
	FString JobPath(const FString& Id) { return TEXT("/v1/jobs/") + Id; }
	FString OutputPath(const FString& Id, int32 Index) { return JobPath(Id) + TEXT("/outputs/") + FString::FromInt(Index); }
	FString Name(int32 Index, uint8 Type) { return FString::Printf(TEXT("image-%d.%s"), Index, Type == 1 ? TEXT("png") : TEXT("jpg")); }
	FString Mime(uint8 Type) { return Type == 1 ? TEXT("image/png") : TEXT("image/jpeg"); }
	FString DisplayName(const FString& Input, int32 Index)
	{
		int32 Start = 0;
		for (int32 I = 0; I < Input.Len(); ++I) if (Input[I] == '/' || Input[I] == '\\') Start = I + 1;
		FString Out;
		for (int32 I = Start; I < Input.Len() && Out.Len() < 120; ++I) if (Input[I] >= 32 && Input[I] != 127) Out.AppendChar(Input[I]);
		return Out.IsEmpty() ? FString::Printf(TEXT("Image %d"), Index) : Out;
	}
	void Append32(TArray<uint8>& Bytes, uint32 Value)
	{
		Bytes.Add(static_cast<uint8>(Value >> 24)); Bytes.Add(static_cast<uint8>(Value >> 16));
		Bytes.Add(static_cast<uint8>(Value >> 8)); Bytes.Add(static_cast<uint8>(Value));
	}
	uint32 Read32(const uint8* Bytes)
	{
		return (static_cast<uint32>(Bytes[0]) << 24) | (static_cast<uint32>(Bytes[1]) << 16)
			| (static_cast<uint32>(Bytes[2]) << 8) | Bytes[3];
	}
	int32 Read16(const uint8* Bytes) { return (static_cast<int32>(Bytes[0]) << 8) | Bytes[1]; }

	bool EncodedHeader(const TArray<uint8>& Bytes, const FDaedalusImageOptimizerOutput& Output)
	{
		// Bounded signature/container/header checks only. The existing service owns full decode,
		// normalized pixels, metadata removal and no-enlargement behavior. No native encoder here.
		if (Bytes.Num() != Output.Bytes || Bytes.IsEmpty() || Bytes.Num() > MaxOutputBytes) return false;
		if (Output.Type == 1)
		{
			const uint8 Signature[] = {137, 80, 78, 71, 13, 10, 26, 10};
			if (Bytes.Num() < 45 || FMemory::Memcmp(Bytes.GetData(), Signature, 8) != 0
				|| Read32(Bytes.GetData() + 8) != 13 || FMemory::Memcmp(Bytes.GetData() + 12, "IHDR", 4) != 0
				|| Read32(Bytes.GetData() + Bytes.Num() - 12) != 0 || FMemory::Memcmp(Bytes.GetData() + Bytes.Num() - 8, "IEND", 4) != 0) return false;
			return Read32(Bytes.GetData() + 16) == static_cast<uint32>(Output.Width)
				&& Read32(Bytes.GetData() + 20) == static_cast<uint32>(Output.Height);
		}
		if (Output.Type != 2 || Bytes.Num() < 12 || Bytes[0] != 0xff || Bytes[1] != 0xd8
			|| Bytes[Bytes.Num() - 2] != 0xff || Bytes.Last() != 0xd9) return false;
		int32 At = 2;
		while (At < Bytes.Num() - 2)
		{
			if (Bytes[At++] != 0xff) return false;
			while (At < Bytes.Num() && Bytes[At] == 0xff) ++At;
			if (At >= Bytes.Num()) return false;
			const uint8 Marker = Bytes[At++];
			if (Marker == 0 || Marker == 0xd8 || Marker == 0xd9 || Marker == 0xda) return false;
			if (Marker == 0x01 || (Marker >= 0xd0 && Marker <= 0xd7)) continue;
			if (At > Bytes.Num() - 2) return false;
			const int32 Length = Read16(Bytes.GetData() + At);
			if (Length < 2 || Length > Bytes.Num() - At) return false;
			const bool bFrame = (Marker >= 0xc0 && Marker <= 0xcf && Marker != 0xc4 && Marker != 0xc8 && Marker != 0xcc);
			if (bFrame)
			{
				return Length >= 8 && Read16(Bytes.GetData() + At + 3) == Output.Height && Read16(Bytes.GetData() + At + 5) == Output.Width;
			}
			At += Length;
		}
		return false;
	}

	bool Capabilities(const TSharedPtr<FJsonObject>& Json)
	{
		FString Product, Protocol, Mode;
		int32 Seconds = 0;
		const TArray<TSharedPtr<FJsonValue>>* Capabilities = nullptr;
		if (!String(Json, TEXT("productId"), Product, 32) || !Exact(Product, TEXT("image-optimizer"))
			|| !String(Json, TEXT("protocol"), Protocol, 32) || !Exact(Protocol, TEXT("imageoptimizer.local.v1"))
			|| !String(Json, TEXT("outputMode"), Mode, 32) || !Exact(Mode, TEXT("one_image_per_input"))
			|| !Json->TryGetArrayField(TEXT("capabilities"), Capabilities) || !Capabilities || Capabilities->Num() != 1) return false;
		FString Capability;
		const auto& Value = (*Capabilities)[0];
		if (!Value.IsValid() || Value->Type != EJson::String || !Value->TryGetString(Capability) || !Exact(Capability, TEXT("image.optimize"))) return false;
		return ExactInteger(Json, TEXT("maxFiles"), MaxFiles) && ExactInteger(Json, TEXT("maxFileBytes"), MaxFileBytes)
			&& ExactInteger(Json, TEXT("maxBatchBytes"), MaxBatchBytes) && ExactInteger(Json, TEXT("maxDimension"), 4096)
			&& ExactInteger(Json, TEXT("maxPixelsPerImage"), 12000000) && ExactInteger(Json, TEXT("maxPixelsPerBatch"), 24000000)
			&& ExactInteger(Json, TEXT("maxOutputBytesPerJob"), MaxOutputBytes) && ExactInteger(Json, TEXT("qualityMin"), 70)
			&& ExactInteger(Json, TEXT("qualityMax"), 95) && Integer(Json, TEXT("sessionTtlSeconds"), Seconds, 1, 900);
	}
	struct FSnapshot
	{
		FString Id, State;
		int32 Total = 0, Completed = 0;
		TArray<FDaedalusImageOptimizerOutput> Outputs;
	};
	bool Snapshot(const TSharedPtr<FJsonObject>& Json, const FString& ExpectedId, const TArray<uint8>& SourceTypes,
		const TArray<int32>& SourceSizes, const FDaedalusImageOptimizerSettings& Settings, FSnapshot& Out)
	{
		if (SourceTypes.IsEmpty() || SourceTypes.Num() != SourceSizes.Num()
			|| !String(Json, TEXT("id"), Out.Id, 36) || !Uuid(Out.Id) || (!ExpectedId.IsEmpty() && !Exact(Out.Id, ExpectedId))
			|| !String(Json, TEXT("state"), Out.State, 16)
			|| !Integer(Json, TEXT("total"), Out.Total, 1, MaxFiles) || Out.Total != SourceTypes.Num()
			|| !Integer(Json, TEXT("completed"), Out.Completed, 0, Out.Total)) return false;
		if (!Exact(Out.State, TEXT("QUEUED")) && !Exact(Out.State, TEXT("RUNNING")) && !Terminal(Out.State)) return false;
		const TArray<TSharedPtr<FJsonValue>>* Outputs = nullptr;
		if (!Json->TryGetArrayField(TEXT("outputs"), Outputs) || !Outputs || Outputs->Num() > MaxFiles) return false;
		if (!Exact(Out.State, TEXT("SUCCEEDED"))) return Outputs->IsEmpty();
		if (Out.Completed != Out.Total || Outputs->Num() != Out.Total) return false;
		int64 Bytes = 0, Pixels = 0;
		for (int32 I = 0; I < Out.Total; ++I)
		{
			const auto& Value = (*Outputs)[I];
			if (!Value.IsValid() || Value->Type != EJson::Object) return false;
			const auto Object = Value->AsObject();
			FDaedalusImageOptimizerOutput Output;
			Output.Type = Settings.Format == 0 ? SourceTypes[I] : Settings.Format;
			FString OutputName, Path;
			if ((Output.Type != 1 && Output.Type != 2) || !Integer(Object, TEXT("index"), Output.Index, I + 1, I + 1)
				|| !String(Object, TEXT("name"), OutputName, 32) || !Exact(OutputName, Name(I + 1, Output.Type))
				|| !String(Object, TEXT("downloadPath"), Path, 100) || !Exact(Path, OutputPath(Out.Id, I + 1))
				|| !Integer(Object, TEXT("width"), Output.Width, 1, 4096) || !Integer(Object, TEXT("height"), Output.Height, 1, 4096)
				|| !Dimensions(Output.Width, Output.Height) || (Settings.bResize && Output.Width > Settings.Width)
				|| !Integer(Object, TEXT("bytes"), Output.Bytes, 1, MaxOutputBytes)
				|| !Integer(Object, TEXT("sourceBytes"), Output.SourceBytes, 1, MaxFileBytes) || Output.SourceBytes != SourceSizes[I]) return false;
			Bytes += Output.Bytes; Pixels += static_cast<int64>(Output.Width) * Output.Height;
			if (Bytes > MaxOutputBytes || Pixels > 24000000) return false;
			Out.Outputs.Add(Output);
		}
		return true;
	}
}

/** Each worker owns its request and response. No UObject/client is captured by asynchronous work. */
class FImageOptimizerHttpTask : public TSharedFromThis<FImageOptimizerHttpTask, ESPMode::ThreadSafe>
{
public:
	ImageOptimizerWire::EOperation Operation = ImageOptimizerWire::EOperation::Capabilities;
	uint64 Generation = 0;
	FString Url, Verb, ContentType, ContentDisposition;
	TArray<FString> RequestHeaders;
	TSharedPtr<const TArray<uint8>, ESPMode::ThreadSafe> Body;
	TArray<uint8> Response;
	SIZE_T HeaderBytes = 0;
	int32 Limit = ImageOptimizerWire::MaxJsonBytes, StatusCode = 0, TimeoutMilliseconds = 30000;
	bool bTransportOk = false, bRedirect = false;
	TAtomic<bool> bCancelled{false}, bDone{false};
	static SIZE_T Write(char* Data, SIZE_T Size, SIZE_T Count, void* User)
	{
		auto* Task = static_cast<FImageOptimizerHttpTask*>(User);
		if (Task->bCancelled.Load() || (Count > 0 && Size > static_cast<SIZE_T>(Task->Limit) / Count)) return 0;
		const SIZE_T Bytes = Size * Count;
		if (Bytes > static_cast<SIZE_T>(Task->Limit - Task->Response.Num())) return 0;
		Task->Response.Append(reinterpret_cast<const uint8*>(Data), static_cast<int32>(Bytes)); return Bytes;
	}
	static SIZE_T Header(char* Data, SIZE_T Size, SIZE_T Count, void* User)
	{
		auto* Task = static_cast<FImageOptimizerHttpTask*>(User);
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
			if (!Task->ContentType.IsEmpty() && !ImageOptimizerWire::Exact(Task->ContentType, Type)) return 0;
			Task->ContentType = MoveTemp(Type);
		}
		if (Line.StartsWith(TEXT("Content-Disposition:"), ESearchCase::IgnoreCase))
		{
			const FString Value = Line.Mid(20).TrimStartAndEnd();
			if (!Task->ContentDisposition.IsEmpty() && !ImageOptimizerWire::Exact(Task->ContentDisposition, Value)) return 0;
			Task->ContentDisposition = Value;
		}
		return Bytes;
	}
	static int Progress(void* User, curl_off_t, curl_off_t, curl_off_t, curl_off_t)
	{
		return static_cast<FImageOptimizerHttpTask*>(User)->bCancelled.Load() ? 1 : 0;
	}
	void Run()
	{
		CURL* Curl = curl_easy_init();
		curl_slist* Headers = nullptr;
		if (Curl && !bCancelled.Load() && (!Body.IsValid() || Body->Num() <= ImageOptimizerWire::MaxBatchBytes))
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
			Set(CURLOPT_VERBOSE, 0L); Set(CURLOPT_NOSIGNAL, 1L); Set(CURLOPT_CONNECTTIMEOUT_MS, 3000L);
			Set(CURLOPT_TIMEOUT_MS, static_cast<long>(TimeoutMilliseconds));
			Set(CURLOPT_WRITEFUNCTION, Write); Set(CURLOPT_WRITEDATA, this); Set(CURLOPT_HEADERFUNCTION, Header); Set(CURLOPT_HEADERDATA, this);
			Set(CURLOPT_NOPROGRESS, 0L); Set(CURLOPT_XFERINFOFUNCTION, Progress); Set(CURLOPT_XFERINFODATA, this);
			if (!ImageOptimizerWire::Exact(Verb, TEXT("GET")))
			{
				static const char Empty[] = "";
				const void* Data = Body.IsValid() && !Body->IsEmpty() ? Body->GetData() : static_cast<const void*>(Empty);
				Set(CURLOPT_POSTFIELDS, Data); Set(CURLOPT_POSTFIELDSIZE_LARGE, static_cast<curl_off_t>(Body.IsValid() ? Body->Num() : 0));
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
		RequestHeaders.Reset(); Body.Reset(); Url.Reset();
		TSharedPtr<FImageOptimizerHttpTask, ESPMode::ThreadSafe> Cleanup;
		{
			FScopeLock Scope(&CleanupLock); bWireFinished = true; Cleanup = MoveTemp(FinalRevoke);
		}
		bDone.Store(true);
		if (Cleanup.IsValid()) Cleanup->Run();
	}
	void RevokeAfter(const TSharedPtr<FImageOptimizerHttpTask, ESPMode::ThreadSafe>& Cleanup)
	{
		bool bStartNow = false;
		{
			FScopeLock Scope(&CleanupLock); if (bWireFinished) bStartNow = true; else FinalRevoke = Cleanup;
		}
		if (bStartNow) Async(EAsyncExecution::ThreadPool, [Cleanup]() { Cleanup->Run(); });
	}
private:
	FCriticalSection CleanupLock;
	bool bWireFinished = false;
	TSharedPtr<FImageOptimizerHttpTask, ESPMode::ThreadSafe> FinalRevoke;
};

class FDaedalusImageOptimizerClient::FImpl
{
public:
	struct FCallbackLifetime { TAtomic<uint64> Generation{1}; TAtomic<bool> bStopped{false}; };
	FDaedalusImageOptimizerView View;
	FString Origin, ProcessToken, SessionToken, ActionKey;
	TArray<FDaedalusImageOptimizerImage> SelectedImages;
	TArray<uint8> SourceTypes;
	TArray<int32> SourceSizes;
	FDaedalusImageOptimizerSettings FrozenSettings;
	TSharedPtr<const TArray<uint8>, ESPMode::ThreadSafe> FrozenBody;
	TSharedPtr<FImageOptimizerHttpTask, ESPMode::ThreadSafe> Active;
	TFunction<void(TArray<uint8>&&, uint8, const FString&)> DownloadCompletion;
	FDaedalusImageOptimizerOutput DownloadOutput;
	TSharedRef<FCallbackLifetime, ESPMode::ThreadSafe> CallbackLifetime = MakeShared<FCallbackLifetime, ESPMode::ThreadSafe>();
	uint64 Generation = 1;
	double ExpiresAt = 0, NextPollAt = 0;
	bool bStopped = false, bAutoPoll = false, bRejected = false, bNotAdmitted = false;
	bool bCancelWanted = false, bCancelNeedsAttempt = false, bDisconnectWanted = false, bRevokeNeedsAttempt = false;
	bool bUnknownSession = false;

	FImpl() { View.Status = TEXT("Pair with your running Image Optimizer app's private Realm workbench link."); }
	void Controls()
	{
		const bool bConnected = !bStopped && !SessionToken.IsEmpty() && !bDisconnectWanted;
		const bool bIdle = !Active.IsValid();
		View.bBusy = !bIdle; View.bPaired = bConnected;
		View.bCanPair = !bStopped && bIdle && Origin.IsEmpty();
		View.bCanDisconnect = !bStopped && !Origin.IsEmpty();
		View.bCanSelect = bConnected && bIdle && ActionKey.IsEmpty() && View.JobId.IsEmpty() && !bCancelWanted;
		View.bCanEditSettings = View.bCanSelect;
		View.bCanSubmit = bConnected && bIdle && !bCancelWanted && !bRejected
			&& (!SelectedImages.IsEmpty() || FrozenBody.IsValid()) && (View.JobId.IsEmpty() || ImageOptimizerWire::Terminal(View.JobState));
		View.bCanRefresh = bConnected && bIdle && !bCancelWanted && (!View.JobId.IsEmpty() || (!ActionKey.IsEmpty() && View.bUncertain));
		View.bCanCancel = bConnected && (!ActionKey.IsEmpty() || !View.JobId.IsEmpty());
		View.bCanExport = bConnected && bIdle && !bCancelWanted && !View.bUncertain
			&& ImageOptimizerWire::Exact(View.JobState, TEXT("SUCCEEDED")) && !View.Outputs.IsEmpty();
	}
	void Invalidate()
	{
		++Generation; CallbackLifetime->Generation.Store(Generation);
	}
	void FinishDownload(TArray<uint8>&& Bytes, uint8 Type, const FString& Error)
	{
		if (!DownloadCompletion) return;
		auto Completion = MoveTemp(DownloadCompletion);
		const auto Lifetime = CallbackLifetime;
		const uint64 ExpectedGeneration = Generation;
		AsyncTask(ENamedThreads::GameThread,
			[Completion = MoveTemp(Completion), Bytes = MoveTemp(Bytes), Type, Error, Lifetime, ExpectedGeneration]() mutable
			{
				if (Lifetime->bStopped.Load() || Lifetime->Generation.Load() != ExpectedGeneration)
				{
					Bytes.Reset(); Completion({}, 0, TEXT("The image action changed or the terminal closed. Nothing was exported."));
				}
				else Completion(MoveTemp(Bytes), Type, Error);
			});
	}
	void ResetAction()
	{
		ActionKey.Reset(); FrozenBody.Reset(); SelectedImages.Reset(); SourceTypes.Reset(); SourceSizes.Reset();
		FrozenSettings = FDaedalusImageOptimizerSettings();
		View.SelectedNames.Reset(); View.JobState.Reset(); View.JobId.Reset(); View.Outputs.Reset(); View.Total = 0; View.Completed = 0;
		View.bUncertain = false; bAutoPoll = false; bRejected = false; bNotAdmitted = false; bCancelWanted = false; bCancelNeedsAttempt = false;
	}
	void ForgetSession(const FString& Status)
	{
		Invalidate(); ResetAction(); Origin.Reset(); ProcessToken.Reset(); SessionToken.Reset(); ExpiresAt = 0;
		bDisconnectWanted = false; bRevokeNeedsAttempt = false; bUnknownSession = false;
		View.Status = Status; Controls();
	}
	TSharedPtr<FImageOptimizerHttpTask, ESPMode::ThreadSafe> MakeRequest(ImageOptimizerWire::EOperation Operation, const TCHAR* Verb, const FString& Path)
	{
		auto Task = MakeShared<FImageOptimizerHttpTask, ESPMode::ThreadSafe>();
		Task->Operation = Operation; Task->Generation = Generation; Task->Verb = Verb; Task->Url = Origin + Path;
		Task->RequestHeaders.Add(TEXT("Authorization: Bearer ") + ProcessToken);
		Task->RequestHeaders.Add(TEXT("Origin: ") + Origin); Task->RequestHeaders.Add(TEXT("Cache-Control: no-store"));
		Task->RequestHeaders.Add(TEXT("Accept: ") + (Operation == ImageOptimizerWire::EOperation::Download ? ImageOptimizerWire::Mime(DownloadOutput.Type) : FString(TEXT("application/json"))));
		if (!SessionToken.IsEmpty()) Task->RequestHeaders.Add(TEXT("X-Session-Token: ") + SessionToken);
		return Task;
	}
	void Start(const TSharedPtr<FImageOptimizerHttpTask, ESPMode::ThreadSafe>& Task)
	{
		check(!Active.IsValid()); Active = Task;
		Async(EAsyncExecution::ThreadPool, [Task]() { Task->Run(); }); Controls();
	}
	TSharedPtr<FJsonObject> Json(const FImageOptimizerHttpTask& Task) const
	{
		return Task.bTransportOk && ImageOptimizerWire::Exact(Task.ContentType, TEXT("application/json")) ? ImageOptimizerWire::Parse(Task.Response) : nullptr;
	}
	bool Error(const FImageOptimizerHttpTask& Task, const TCHAR* Expected) const
	{
		FString Value; return ImageOptimizerWire::String(Json(Task), TEXT("error"), Value, 64) && ImageOptimizerWire::Exact(Value, Expected);
	}
	bool Freeze()
	{
		using namespace ImageOptimizerWire;
		if (FrozenBody.IsValid()) return true;
		if (SelectedImages.IsEmpty() || SelectedImages.Num() > MaxFiles || !Settings(View.Settings)) return false;
		int64 Length = FixedHeaderBytes;
		for (const auto& Image : SelectedImages) Length += 5LL + Image.Bytes.Num();
		if (Length > MaxBatchBytes) return false;
		auto Body = MakeShared<TArray<uint8>, ESPMode::ThreadSafe>();
		Body->Reserve(static_cast<int32>(Length)); Body->Append(reinterpret_cast<const uint8*>("IOP1"), 4);
		Append32(*Body, static_cast<uint32>(SelectedImages.Num())); Body->Add(static_cast<uint8>(View.Settings.Quality));
		Body->Add(View.Settings.bResize ? 1 : 0); Append32(*Body, static_cast<uint32>(View.Settings.Width)); Body->Add(View.Settings.Format);
		for (const auto& Image : SelectedImages)
		{
			Body->Add(Image.Type); Append32(*Body, static_cast<uint32>(Image.Bytes.Num())); Body->Append(Image.Bytes);
		}
		FrozenBody = Body; FrozenSettings = View.Settings; SelectedImages.Reset();
		return true;
	}
	void Submit()
	{
		if (!Freeze()) { View.Status = TEXT("The image batch or settings exceed the native request bounds. Nothing was submitted."); return; }
		if (ActionKey.IsEmpty()) ActionKey = FGuid::NewGuid().ToString(EGuidFormats::DigitsWithHyphensLower);
		bNotAdmitted = false;
		auto Task = MakeRequest(ImageOptimizerWire::EOperation::Submit, TEXT("POST"), TEXT("/v1/jobs"));
		Task->Body = FrozenBody; Task->RequestHeaders.Add(TEXT("Content-Type: application/octet-stream"));
		Task->RequestHeaders.Add(TEXT("Idempotency-Key: ") + ActionKey); Task->RequestHeaders.Add(TEXT("Expect:"));
		View.Status = bCancelWanted ? TEXT("Recovering the same frozen action before cancellation...") : TEXT("Submitting selected images and settings to Image Optimizer...");
		Start(Task);
	}
	void StartRefresh()
	{
		View.Status = TEXT("Refreshing the same Image Optimizer job...");
		Start(MakeRequest(ImageOptimizerWire::EOperation::Refresh, TEXT("GET"), ImageOptimizerWire::JobPath(View.JobId)));
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
				Start(MakeRequest(ImageOptimizerWire::EOperation::Revoke, TEXT("DELETE"), TEXT("/v1/sessions")));
			}
			else
			{
				const bool Unknown = bUnknownSession;
				ForgetSession(Unknown ? TEXT("Disconnected locally. Session creation was unconfirmed; temporary session cleanup is unconfirmed until app expiry/shutdown.")
					: TEXT("Disconnected. No private image session was created."));
			}
		}
		else if (bCancelWanted && bCancelNeedsAttempt)
		{
			bCancelNeedsAttempt = false;
			if (!View.JobId.IsEmpty())
			{
				View.Status = TEXT("Canceling the job. The app retains an idempotency tombstone until session expiry...");
				Start(MakeRequest(ImageOptimizerWire::EOperation::Cancel, TEXT("DELETE"), ImageOptimizerWire::JobPath(View.JobId)));
			}
			else if (bRejected || bNotAdmitted)
			{
				// Do not start new image work merely to cancel a body known not to have been admitted.
				bDisconnectWanted = true; bRevokeNeedsAttempt = true; AdvanceIntent();
			}
			else if (!ActionKey.IsEmpty() && FrozenBody.IsValid()) Submit();
		}
		Controls();
	}
	bool ReadSession(const TSharedPtr<FJsonObject>& Value)
	{
		FString Id, Token;
		int32 Seconds = 0;
		if (!ImageOptimizerWire::String(Value, TEXT("sessionId"), Id, 36) || !ImageOptimizerWire::Uuid(Id)
			|| !ImageOptimizerWire::String(Value, TEXT("sessionToken"), Token, 43) || !ImageOptimizerWire::Token(Token)
			|| !ImageOptimizerWire::Integer(Value, TEXT("expiresInSeconds"), Seconds, 1, 900)) return false;
		SessionToken = MoveTemp(Token); ExpiresAt = FPlatformTime::Seconds() + Seconds; bUnknownSession = false; return true;
	}
	void ApplySnapshot(ImageOptimizerWire::FSnapshot&& Snapshot)
	{
		View.JobId = MoveTemp(Snapshot.Id); View.JobState = MoveTemp(Snapshot.State);
		View.Total = Snapshot.Total; View.Completed = Snapshot.Completed; View.Outputs = MoveTemp(Snapshot.Outputs);
		View.bUncertain = false; bRejected = false; bNotAdmitted = false;
		bAutoPoll = !ImageOptimizerWire::Terminal(View.JobState); NextPollAt = FPlatformTime::Seconds() + 1.0;
		if (ImageOptimizerWire::Exact(View.JobState, TEXT("SUCCEEDED")))
			View.Status = TEXT("Images are ready. Review actual sizes/dimensions and export copies. Unchanged Optimize refreshes this job; Cancel before changing images/settings.");
		else if (ImageOptimizerWire::Exact(View.JobState, TEXT("FAILED")))
			View.Status = TEXT("Image Optimizer could not finish this batch. Cancel before selecting a new batch or changing settings.");
		else if (ImageOptimizerWire::Exact(View.JobState, TEXT("CANCELED")))
			View.Status = TEXT("This action is canceled and cannot restart. Confirm Cancel to retire it locally, then select new work with a fresh action key.");
		else View.Status = TEXT("Image Optimizer is processing the selected images...");
	}
	void Complete(const TSharedPtr<FImageOptimizerHttpTask, ESPMode::ThreadSafe>& Task)
	{
		using namespace ImageOptimizerWire;
		const auto Value = Json(*Task);
		if (Task->Generation != Generation)
		{
			if (Task->Operation == EOperation::Session && bDisconnectWanted && Task->StatusCode == 201) ReadSession(Value);
			AdvanceIntent(); Controls(); return;
		}
		if (Task->bTransportOk && Task->StatusCode == 401)
		{
			ForgetSession(TEXT("The app no longer authorizes this session. Local data is cleared; temporary-file cleanup is handled by app expiry/shutdown."));
			FinishDownload({}, 0, TEXT("The image session is no longer authorized.")); return;
		}
		switch (Task->Operation)
		{
		case EOperation::Capabilities:
			if (Task->StatusCode == 200 && Capabilities(Value))
			{
				bUnknownSession = true; View.Status = TEXT("Opening a private Image Optimizer session...");
				Start(MakeRequest(EOperation::Session, TEXT("POST"), TEXT("/v1/sessions"))); // Empty body, not JSON.
			}
			else ForgetSession(TEXT("Image Optimizer capabilities were not verified. No session was requested."));
			break;
		case EOperation::Session:
			if (Task->StatusCode == 201 && ReadSession(Value)) View.Status = TEXT("Connected. Choose PNG/JPEG images and bounded settings. JPEG loses transparency; output size can grow.");
			else { bUnknownSession = true; View.Status = TEXT("Session creation was not confirmed. Disconnect before re-pairing; temporary session cleanup may remain until expiry."); }
			break;
		case EOperation::Submit:
		case EOperation::Refresh:
		{
			FSnapshot SnapshotValue;
			if ((Task->StatusCode == 200 || (Task->Operation == EOperation::Submit && Task->StatusCode == 202))
				&& Snapshot(Value, View.JobId, SourceTypes, SourceSizes, FrozenSettings, SnapshotValue))
			{
				ApplySnapshot(MoveTemp(SnapshotValue)); if (bCancelWanted) bCancelNeedsAttempt = true;
			}
			else
			{
				bAutoPoll = false; View.Outputs.Reset();
				if (Task->Operation == EOperation::Submit)
				{
					const bool Rejected = (Task->StatusCode == 400 && Error(*Task, TEXT("IDEMPOTENCY_KEY_REQUIRED")))
						|| (Task->StatusCode == 413 && Error(*Task, TEXT("BODY_LIMIT"))) || (Task->StatusCode == 415 && Error(*Task, TEXT("BINARY_BATCH_REQUIRED")))
						|| (Task->StatusCode == 422 && Error(*Task, TEXT("INVALID_IMAGE_BATCH")));
					const bool QueueRejected = Task->StatusCode == 429 && (Error(*Task, TEXT("QUEUE_FULL")) || Error(*Task, TEXT("JOB_LIMIT")));
					bRejected = Rejected; bNotAdmitted = Rejected || QueueRejected; View.bUncertain = !bNotAdmitted;
					if (Rejected) View.Status = TEXT("The app rejected this frozen batch/settings. Cancel or disconnect before changing it.");
					else if (QueueRejected) View.Status = TEXT("The app's queue/action capacity is full. Retry this same action later, cancel, or disconnect for a fresh session.");
					else View.Status = TEXT("Submission outcome is unknown. Retry only these frozen bytes/settings and action key, cancel to reconcile, or disconnect.");
					// Generic INVALID_REQUEST may follow an IO exception after admission: retain uncertainty.
					if (bCancelWanted && bNotAdmitted) bCancelNeedsAttempt = true;
				}
				else { View.bUncertain = true; View.Status = TEXT("The job snapshot was not confirmed. Refresh, Cancel or Disconnect; no output is available for export."); }
			}
			break;
		}
		case EOperation::Cancel:
		{
			FString Id, State;
			const bool Confirmed = Task->StatusCode == 200 && String(Value, TEXT("id"), Id, 36) && Exact(Id, View.JobId)
				&& String(Value, TEXT("state"), State, 16) && Exact(State, TEXT("CANCELED"));
			const bool Gone = Task->StatusCode == 404 && Error(*Task, TEXT("NOT_FOUND"));
			if (Confirmed || Gone)
			{
				ResetAction();
				View.Status = Confirmed ? TEXT("Action canceled. The app retains its tombstone/key until session expiry and cleans outputs after open handles close. New work uses a fresh key.")
					: TEXT("The owned job is no longer available. Its local action is retired; choose new work. This is not a physical-file deletion receipt.");
			}
			else { View.bUncertain = true; View.Outputs.Reset(); View.Status = TEXT("Cancellation was not confirmed. Retry Cancel or Disconnect; bytes, settings and action key remain frozen."); }
			break;
		}
		case EOperation::Download:
		{
			const FString Disposition = TEXT("attachment; filename=\"") + Name(DownloadOutput.Index, DownloadOutput.Type) + TEXT("\"");
			if (Task->bTransportOk && Task->StatusCode == 200 && Exact(Task->ContentType, Mime(DownloadOutput.Type))
				&& Exact(Task->ContentDisposition, Disposition) && EncodedHeader(Task->Response, DownloadOutput))
			{
				View.Status = TEXT("Image bytes downloaded with matching metadata/MIME/header dimensions. Choose a new destination to export the copy.");
				FinishDownload(MoveTemp(Task->Response), DownloadOutput.Type, FString());
			}
			else { View.Status = TEXT("Image download failed bounded wire/header checks or was interrupted. No export was reported."); FinishDownload({}, 0, TEXT("The image download was not confirmed. Nothing was exported.")); }
			break;
		}
		case EOperation::Revoke:
		{
			FString State;
			if (Task->StatusCode == 200 && String(Value, TEXT("state"), State, 16) && Exact(State, TEXT("DELETED")))
				ForgetSession(TEXT("The app confirmed session revocation. Jobs/keys are removed and temporary outputs clean up as active handles close."));
			else { View.bUncertain = true; View.Status = TEXT("Session revocation was not confirmed. Retry Disconnect; remaining access/temporary files expire under the app's fixed session policy."); }
			break;
		}
		default: break;
		}
		AdvanceIntent(); Controls();
	}
};

FDaedalusImageOptimizerClient::FDaedalusImageOptimizerClient() : Impl(MakeUnique<FImpl>()) {}
FDaedalusImageOptimizerClient::~FDaedalusImageOptimizerClient() { Shutdown(); }
FDaedalusImageOptimizerView FDaedalusImageOptimizerClient::GetView() const { check(IsInGameThread()); return Impl->View; }

bool FDaedalusImageOptimizerClient::Pair(const FString& PairingLink)
{
	check(IsInGameThread()); Impl->Controls();
	if (!Impl->View.bCanPair) return false;
	const FTCHARToUTF8 Link(*PairingLink, PairingLink.Len());
	if (!daedalus::localapp::IsValidCompanionLink(std::string_view(Link.Get(), Link.Length()), daedalus::localapp::Kind::ImageOptimizer))
	{
		Impl->View.Status = TEXT("Use the literal typed loopback pairing link supplied by Image Optimizer."); return false;
	}
	Impl->Invalidate();
	const FString Path(TEXT("/realm/image-optimizer/"));
	const int32 PathAt = PairingLink.Find(Path, ESearchCase::CaseSensitive);
	Impl->Origin = PairingLink.Left(PathAt); Impl->ProcessToken = PairingLink.Mid(PathAt + Path.Len() + 7);
	Impl->View.Status = TEXT("Verifying Image Optimizer's local capabilities...");
	Impl->Start(Impl->MakeRequest(ImageOptimizerWire::EOperation::Capabilities, TEXT("GET"), TEXT("/v1/capabilities"))); return true;
}

bool FDaedalusImageOptimizerClient::SetImages(TArray<FDaedalusImageOptimizerImage>&& Images)
{
	check(IsInGameThread()); Impl->Controls();
	if (!Impl->View.bCanSelect) return false;
	if (Images.IsEmpty() || Images.Num() > ImageOptimizerWire::MaxFiles)
	{
		Impl->View.Status = TEXT("Choose one to eight PNG or JPEG images."); return false;
	}
	int64 Length = ImageOptimizerWire::FixedHeaderBytes;
	for (const auto& Image : Images)
	{
		Length += 5LL + Image.Bytes.Num();
		if ((Image.Type != 1 && Image.Type != 2) || Image.Bytes.IsEmpty() || Image.Bytes.Num() > ImageOptimizerWire::MaxFileBytes || Length > ImageOptimizerWire::MaxBatchBytes)
		{
			Impl->View.Status = TEXT("Use PNG/JPEG images at most 8 MiB each and 24 MiB including the 15-byte header and image framing."); return false;
		}
	}
	Impl->View.SelectedNames.Reset(); Impl->SourceTypes.Reset(); Impl->SourceSizes.Reset();
	for (int32 I = 0; I < Images.Num(); ++I)
	{
		Impl->View.SelectedNames.Add(ImageOptimizerWire::DisplayName(Images[I].DisplayName, I + 1));
		Impl->SourceTypes.Add(Images[I].Type); Impl->SourceSizes.Add(Images[I].Bytes.Num()); Images[I].DisplayName.Reset();
	}
	Impl->View.Total = Images.Num(); Impl->SelectedImages = MoveTemp(Images);
	Impl->View.Status = TEXT("Images selected locally. Set quality, resize and output format, then submit to the existing app.");
	Impl->Controls(); return true;
}

bool FDaedalusImageOptimizerClient::SetSettings(const FDaedalusImageOptimizerSettings& Settings)
{
	check(IsInGameThread()); Impl->Controls();
	if (!Impl->View.bCanEditSettings) return false;
	if (!ImageOptimizerWire::Settings(Settings)) { Impl->View.Status = TEXT("Use integer quality 70–95, width 1–4096, and keep/PNG/JPEG format."); return false; }
	Impl->View.Settings = Settings;
	Impl->View.Status = TEXT("Settings updated for the next action. JPEG loses transparency and encoded outputs can be larger than their sources.");
	Impl->Controls(); return true;
}

void FDaedalusImageOptimizerClient::SubmitOrRetry()
{
	check(IsInGameThread()); Impl->Controls();
	if (!Impl->View.bCanSubmit) return;
	if (!Impl->View.JobId.IsEmpty()) Impl->StartRefresh(); // A repeated completed action never starts replacement work.
	else Impl->Submit();
}
void FDaedalusImageOptimizerClient::Refresh()
{
	check(IsInGameThread()); Impl->Controls();
	if (!Impl->View.bCanRefresh) return;
	if (Impl->View.JobId.IsEmpty()) Impl->Submit(); else Impl->StartRefresh();
}
void FDaedalusImageOptimizerClient::CancelJob()
{
	check(IsInGameThread());
	if (Impl->bStopped || Impl->SessionToken.IsEmpty() || Impl->bDisconnectWanted || (Impl->ActionKey.IsEmpty() && Impl->View.JobId.IsEmpty())) return;
	Impl->Invalidate(); Impl->bCancelWanted = true; Impl->bCancelNeedsAttempt = true; Impl->bAutoPoll = false; Impl->View.Outputs.Reset();
	if (Impl->Active.IsValid()) Impl->Active->bCancelled.Store(true);
	Impl->FinishDownload({}, 0, TEXT("The image download was canceled. Nothing was exported."));
	Impl->View.Status = TEXT("Cancellation requested. Server cancellation is not yet confirmed."); Impl->AdvanceIntent(); Impl->Controls();
}
void FDaedalusImageOptimizerClient::Disconnect()
{
	check(IsInGameThread());
	if (Impl->bStopped || Impl->Origin.IsEmpty()) return;
	Impl->Invalidate(); Impl->bDisconnectWanted = true; Impl->bRevokeNeedsAttempt = true; Impl->bAutoPoll = false; Impl->View.Outputs.Reset();
	if (Impl->Active.IsValid()) Impl->Active->bCancelled.Store(true);
	Impl->FinishDownload({}, 0, TEXT("The image session is disconnecting. Nothing was exported."));
	Impl->View.Status = TEXT("Disconnect requested. Session revocation is still pending."); Impl->AdvanceIntent(); Impl->Controls();
}
void FDaedalusImageOptimizerClient::Shutdown()
{
	if (!Impl.IsValid() || Impl->bStopped) return;
	Impl->bStopped = true; Impl->Invalidate(); Impl->CallbackLifetime->bStopped.Store(true);
	Impl->FinishDownload({}, 0, TEXT("The image terminal closed. Nothing was exported."));
	TSharedPtr<FImageOptimizerHttpTask, ESPMode::ThreadSafe> Cleanup;
	if (!Impl->SessionToken.IsEmpty())
	{
		Cleanup = Impl->MakeRequest(ImageOptimizerWire::EOperation::Revoke, TEXT("DELETE"), TEXT("/v1/sessions")); Cleanup->TimeoutMilliseconds = 3000;
	}
	if (Impl->Active.IsValid())
	{
		if (Cleanup.IsValid()) Impl->Active->RevokeAfter(Cleanup);
		Impl->Active->bCancelled.Store(true); Impl->Active.Reset();
	}
	else if (Cleanup.IsValid()) Async(EAsyncExecution::ThreadPool, [Cleanup]() { Cleanup->Run(); });
	Impl->ForgetSession(TEXT("Terminal closed. Session revocation was best effort and remains unconfirmed; the app controls expiry and deferred file cleanup."));
	Impl->Controls();
}
void FDaedalusImageOptimizerClient::Tick()
{
	check(IsInGameThread());
	if (Impl->bStopped) return;
	if (Impl->Active.IsValid() && Impl->Active->bDone.Load()) { auto Task = MoveTemp(Impl->Active); Impl->Complete(Task); }
	const double Now = FPlatformTime::Seconds();
	if (!Impl->SessionToken.IsEmpty() && !Impl->bDisconnectWanted && Impl->ExpiresAt > 0 && Now >= Impl->ExpiresAt) Disconnect();
	if (Impl->bAutoPoll && !Impl->Active.IsValid() && !Impl->bCancelWanted && !Impl->bDisconnectWanted && !Impl->View.JobId.IsEmpty() && Now >= Impl->NextPollAt) Refresh();
	Impl->Controls();
}
void FDaedalusImageOptimizerClient::Download(int32 Index, TFunction<void(TArray<uint8>&&, uint8, const FString&)> Completion)
{
	check(IsInGameThread()); Impl->Controls();
	if (!Impl->View.bCanExport || Index < 1 || Index > Impl->View.Outputs.Num())
	{
		if (Completion) Completion({}, 0, TEXT("No completed image output is available at this index.")); return;
	}
	Impl->DownloadOutput = Impl->View.Outputs[Index - 1]; Impl->DownloadCompletion = MoveTemp(Completion);
	auto Task = Impl->MakeRequest(ImageOptimizerWire::EOperation::Download, TEXT("GET"), ImageOptimizerWire::OutputPath(Impl->View.JobId, Index));
	Task->Limit = Impl->DownloadOutput.Bytes;
	Impl->View.Status = TEXT("Downloading the selected image copy from this owned job..."); Impl->Start(Task);
}
