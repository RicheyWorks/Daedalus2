// SPDX-License-Identifier: MIT
#include "DaedalusIslandAudio.h"

#include "DaedalusAudioCore.h"
#include "Async/Async.h"
#include "Components/AudioComponent.h"
#include "Dom/JsonObject.h"
#include "Engine/World.h"
#include "GameFramework/Actor.h"
#include "HAL/IConsoleManager.h"
#include "HttpModule.h"
#include "Interfaces/IHttpRequest.h"
#include "Interfaces/IHttpResponse.h"
#include "Net/UnrealNetwork.h"
#include "Serialization/Archive.h"
#include "Serialization/JsonSerializer.h"
#include "Sound/SoundBase.h"
#include "Sound/SoundAttenuation.h"
#include "Sound/SoundWaveProcedural.h"
#include "TimerManager.h"

namespace DA = daedalus::audio;

struct FDaedalusPreparedAudio
{
	DA::Design Design;
	std::vector<int16_t> Pcm;
	uint32 Revision = 0;
};

struct FDaedalusAudioTransport
{
	FString Url;
	FString Bearer;
	TSharedPtr<IHttpRequest, ESPMode::ThreadSafe> Request;
	DA::RequestFence Requests;
	TSharedPtr<IHttpRequest, ESPMode::ThreadSafe> MusicRequest;
	DA::CueRoutePolicy Music;
};

namespace
{
	// HTTP writes from its worker thread. Completion runs after the stream has finished.
	// Returning an archive error terminates reception without retaining an oversized body.
	class FBoundedAudBody final : public FArchive
	{
	public:
		FBoundedAudBody() { SetIsSaving(true); }
		void Serialize(void* Data, int64 Length) override
		{
			if (Length < 0 || !Received.Append(static_cast<const char*>(Data), static_cast<size_t>(Length)))
			{
				SetError();
				return;
			}
		}
		DA::BoundedBody Received;
	};

	bool IsOneOf(const FString& Value, std::initializer_list<const TCHAR*> Values)
	{
		for (const TCHAR* Candidate : Values) if (Value.Equals(Candidate, ESearchCase::CaseSensitive)) return true;
		return false;
	}

	bool InRange(double Value, double Min, double Max)
	{
		return FMath::IsFinite(Value) && Value >= Min && Value <= Max;
	}

	bool SeedForGenome(const FString& Genome, uint64& Seed, std::string& Error)
	{
		if (Genome.Len() < 2 || Genome.Len() > 128 || Genome.Len() % 2 != 0) return false;
		const FTCHARToUTF8 Utf8(*Genome, Genome.Len());
		return DA::GenomeSeed(std::string_view(Utf8.Get(), static_cast<size_t>(Utf8.Length())), Seed, Error);
	}
}

UDaedalusIslandAudio::UDaedalusIslandAudio()
{
	PrimaryComponentTick.bCanEverTick = false;
	SetIsReplicatedByDefault(true);
	Transport = MakeShared<FDaedalusAudioTransport>();
}

bool UDaedalusIslandAudio::IsServer() const
{
	return !bEnded && IsInGameThread() && GetWorld() && GetWorld()->GetNetMode() != NM_Client && GetOwner() && GetOwner()->HasAuthority();
}

void UDaedalusIslandAudio::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
	Super::GetLifetimeReplicatedProps(OutLifetimeProps);
	DOREPLIFETIME(UDaedalusIslandAudio, Accepted);
}

void UDaedalusIslandAudio::ConfigureDesignService(const FString& ServerBaseUrl, const FString& ExistingHostBearer)
{
	if (!IsServer()) return;
	++WorkGeneration;
	bReplicaPending = false;
	Transport->Requests.Invalidate();
	if (Transport->Request) Transport->Request->CancelRequest();
	Transport->Request.Reset();
	Transport->Url = ServerBaseUrl;
	Transport->Url.RemoveFromEnd(TEXT("/"));
	Transport->Url += TEXT("/api/v1/audio/design");
	Transport->Bearer = ExistingHostBearer;
}

bool UDaedalusIslandAudio::RefreshDesign(const FDaedalusAudioDesignInput& Input)
{
	if (!IsServer() || bPreparing || Transport->Requests.Busy()) return false;
	uint64 Seed = 0;
	std::string Error;
	if (!SeedForGenome(Input.GenomeHex, Seed, Error) ||
		!IsOneOf(Input.Biome, {TEXT("FOREST"), TEXT("GRASSLAND"), TEXT("WETLAND"), TEXT("COAST"), TEXT("DESERT"), TEXT("ALPINE"), TEXT("CAVE")}) ||
		!IsOneOf(Input.Species, {TEXT("SONGBIRD"), TEXT("GOAT"), TEXT("BOVINE"), TEXT("SWINE"), TEXT("FOWL"), TEXT("AMPHIBIAN"), TEXT("CANID")}) ||
		!IsOneOf(Input.MusicCue, {TEXT("FIELD"), TEXT("TOWN"), TEXT("CASTLE"), TEXT("CAVE"), TEXT("BATTLE"), TEXT("BOSS"), TEXT("VICTORY"), TEXT("DEFEAT"), TEXT("INN")}) ||
		!InRange(Input.Hour, 0, 24) || !InRange(Input.Rain, 0, 1) || !InRange(Input.Wind, 0, 1) || !InRange(Input.WaterNear, 0, 1))
	{
		Status = TEXT("invalid design input");
		return false;
	}
	if (Transport->Bearer.IsEmpty() || !(Transport->Url.StartsWith(TEXT("https://")) || Transport->Url.StartsWith(TEXT("http://"))))
	{
		Status = TEXT("design service not configured");
		return false;
	}
	TSharedRef<FJsonObject> Json = MakeShared<FJsonObject>();
	Json->SetStringField(TEXT("biome"), Input.Biome);
	Json->SetNumberField(TEXT("hour"), Input.Hour);
	Json->SetNumberField(TEXT("rain"), Input.Rain);
	Json->SetNumberField(TEXT("wind"), Input.Wind);
	Json->SetNumberField(TEXT("waterNear"), Input.WaterNear);
	Json->SetStringField(TEXT("species"), Input.Species);
	Json->SetStringField(TEXT("genome"), Input.GenomeHex);
	Json->SetStringField(TEXT("musicCue"), Input.MusicCue);
	FString Body;
	FJsonSerializer::Serialize(Json, TJsonWriterFactory<>::Create(&Body));
	uint64 Generation = 0;
	if (!Transport->Requests.Begin(Generation)) { Status = TEXT("request generation exhausted"); return false; }
	TSharedRef<FBoundedAudBody, ESPMode::ThreadSafe> Received = MakeShared<FBoundedAudBody, ESPMode::ThreadSafe>();
	TSharedRef<IHttpRequest, ESPMode::ThreadSafe> Request = FHttpModule::Get().CreateRequest();
	Transport->Request = Request;
	Request->SetURL(Transport->Url);
	Request->SetVerb(TEXT("POST"));
	Request->SetHeader(TEXT("Authorization"), TEXT("Bearer ") + Transport->Bearer);
	Request->SetHeader(TEXT("Content-Type"), TEXT("application/json"));
	Request->SetHeader(TEXT("Accept"), TEXT("text/plain"));
	Request->SetTimeout(5.0f);
	Request->SetDelegateThreadPolicy(EHttpRequestDelegateThreadPolicy::CompleteOnGameThread);
	if (!Request->SetResponseBodyReceiveStreamDelegateV2(FHttpRequestStreamDelegateV2::CreateLambda([Received](void* Data, int64& Length)
	{
		Received->Serialize(Data, Length);
		if (Received->IsError()) Length = 0;
	})))
	{
		Transport->Requests.Complete(Generation);
		Transport->Request.Reset();
		Status = TEXT("bounded response stream unavailable");
		return false;
	}
	const TWeakObjectPtr<UDaedalusIslandAudio> Weak(this);
	Request->OnProcessRequestComplete().BindLambda([Weak, Received, Generation, Seed](FHttpRequestPtr, FHttpResponsePtr Response, bool bOk)
	{
		UDaedalusIslandAudio* Self = Weak.Get();
		if (!Self || Self->bEnded || !Self->Transport->Requests.Complete(Generation)) return;
		Self->Transport->Request.Reset();
		if (!bOk || !Response || Received->IsError() || Response->GetResponseCode() != 200 ||
			!Response->GetContentType().StartsWith(TEXT("text/plain"), ESearchCase::IgnoreCase))
		{
			Self->Status = FString::Printf(TEXT("design refused/unavailable (HTTP %d); retaining accepted mix"), Response ? Response->GetResponseCode() : 0);
			return;
		}
		// AUD1 is ASCII. Reject embedded NUL/non-ASCII before FString conversion, without truncation.
		for (unsigned char Byte : Received->Received.Body()) if (Byte == 0 || Byte > 127)
		{
			Self->Status = TEXT("invalid AUD1 encoding; retaining accepted mix");
			return;
		}
		Self->StartPreparation(UTF8_TO_TCHAR(Received->Received.Body().c_str()), Seed, 0, true);
	});
	Status = TEXT("design request pending");
	if (!Request->ProcessRequest())
	{
		Transport->Requests.Complete(Generation);
		Transport->Request.Reset();
		Status = TEXT("design request could not start");
		return false;
	}
	return true;
}

bool UDaedalusIslandAudio::AcceptDesignText(const FString& Aud1, const FString& GenomeHex)
{
	if (!IsServer() || bPreparing || Transport->Requests.Busy() || Aud1.Len() > 4096) return false;
	uint64 Seed = 0;
	std::string Error;
	if (!SeedForGenome(GenomeHex, Seed, Error))
	{
		Status = TEXT("invalid genome");
		return false;
	}
	StartPreparation(Aud1, Seed, 0, true);
	return true;
}

void UDaedalusIslandAudio::StartPreparation(FString Text, uint64 Seed, uint32 Revision, bool bPublish)
{
	if (bEnded || Text.Len() > 4096) return;
	if (bPreparing)
	{
		// Replication retains just the latest bounded Accepted property, never a work queue.
		if (!bPublish) bReplicaPending = true;
		return;
	}
	bPreparing = true;
	const uint64 Generation = ++WorkGeneration;
	const TWeakObjectPtr<UDaedalusIslandAudio> Weak(this);
	Status = TEXT("preparing audio");
	Async(EAsyncExecution::ThreadPool, [Weak, Text = MoveTemp(Text), Seed, Revision, bPublish, Generation]()
	{
		TSharedPtr<FDaedalusPreparedAudio, ESPMode::ThreadSafe> Value = MakeShared<FDaedalusPreparedAudio, ESPMode::ThreadSafe>();
		std::string Error;
		const FTCHARToUTF8 Utf8(*Text, Text.Len());
		const bool bOk = DA::DecodeAud1(std::string_view(Utf8.Get(), static_cast<size_t>(Utf8.Length())), Value->Design, Error) &&
			DA::RenderCall(Value->Design.Call, Seed, Value->Pcm, Error);
		AsyncTask(ENamedThreads::GameThread, [Weak, Text, Seed, Revision, bPublish, Generation, Value, Error, bOk]()
		{
			UDaedalusIslandAudio* Self = Weak.Get();
			if (!Self || Self->bEnded) return;
			Self->bPreparing = false;
			if (Generation == Self->WorkGeneration && (bPublish ? Self->IsServer() : Revision == Self->Accepted.Revision))
			{
				if (bOk)
				{
					if (bPublish)
					{
						Self->Accepted.Text = Text;
						Self->Accepted.Seed = Seed;
						++Self->Accepted.Revision;
						Self->GetOwner()->ForceNetUpdate();
					}
					Value->Revision = Self->Accepted.Revision;
					Self->ApplyPrepared(Value);
				}
				else Self->Status = TEXT("invalid AUD1; retaining accepted mix: ") + FString(UTF8_TO_TCHAR(Error.c_str()));
			}
			if (Self->bReplicaPending)
			{
				Self->bReplicaPending = false;
				if (!Self->Accepted.Text.IsEmpty()) Self->StartPreparation(Self->Accepted.Text, Self->Accepted.Seed, Self->Accepted.Revision, false);
			}
		});
	});
}

void UDaedalusIslandAudio::OnRep_Accepted()
{
	if (bEnded) return;
	if (Accepted.Text.IsEmpty())
	{
		++WorkGeneration;
		bReplicaPending = false;
		StopLocal();
		return;
	}
	if (Accepted.Text.Len() > 4096 || (Prepared && Prepared->Revision == Accepted.Revision)) return;
	StartPreparation(Accepted.Text, Accepted.Seed, Accepted.Revision, false);
}

void UDaedalusIslandAudio::ApplyPrepared(TSharedPtr<FDaedalusPreparedAudio, ESPMode::ThreadSafe> Value)
{
	Prepared = MoveTemp(Value);
	MissingLayers.Reset();
	Status = TEXT("audio prepared");
	if (IsServer()) RouteMusicCue(UTF8_TO_TCHAR(Prepared->Design.MusicCue.c_str()));
	if (!GetWorld() || GetWorld()->GetNetMode() == NM_DedicatedServer) return;
	TSet<FName> Active;
	for (const DA::Layer& Layer : Prepared->Design.Layers)
	{
		const FString Name(UTF8_TO_TCHAR(Layer.Id.c_str()));
		// Unknown remote IDs must not grow Unreal's permanent global name table.
		const FName Id(*Name, FNAME_Find);
		const TObjectPtr<USoundBase>* Binding = AmbientBindings.Find(Id);
		if (Id.IsNone() || !Binding || !*Binding)
		{
			if (!MissingLayers.IsEmpty()) MissingLayers += TEXT(",");
			MissingLayers += Name;
			if (TObjectPtr<UAudioComponent>* Existing = AmbientVoices.Find(Id)) (*Existing)->Stop();
			continue;
		}
		Active.Add(Id);
		TObjectPtr<UAudioComponent>& Voice = AmbientVoices.FindOrAdd(Id);
		if (!Voice)
		{
			Voice = NewObject<UAudioComponent>(GetOwner());
			Voice->bAutoActivate = false;
			Voice->bAllowSpatialization = bSpatialize;
			Voice->SetupAttachment(GetOwner()->GetRootComponent());
			Voice->RegisterComponent();
		}
		if (Voice->Sound != *Binding) { Voice->Stop(); Voice->SetSound(*Binding); }
		Voice->SetVolumeMultiplier(static_cast<float>(Layer.Gain));
		Voice->SetLowPassFilterEnabled(true);
		Voice->SetLowPassFilterFrequency(static_cast<float>(Layer.LowpassHz));
		Voice->SetFloatParameter(TEXT("Density"), static_cast<float>(Layer.Density));
		if (!Voice->IsPlaying() && Layer.Gain > 0) Voice->Play();
	}
	for (auto It = AmbientVoices.CreateIterator(); It; ++It)
	{
		if (!Active.Contains(It.Key())) { It.Value()->DestroyComponent(); It.RemoveCurrent(); }
	}
	if (!MissingLayers.IsEmpty()) Status += TEXT("; missing ambience: ") + MissingLayers;
}

void UDaedalusIslandAudio::RouteMusicCue(const FString& Cue)
{
	const IConsoleVariable* Setting = IConsoleManager::Get().FindConsoleVariable(TEXT("daedalus.Jukebox"));
	if (!Setting || Setting->GetString().IsEmpty()) { Status += TEXT("; jukebox unconfigured"); return; }
	std::string ToSend;
	if (Transport->Music.Offer(TCHAR_TO_UTF8(*Cue), ToSend)) SendMusicCue(UTF8_TO_TCHAR(ToSend.c_str()));
}

void UDaedalusIslandAudio::SendMusicCue(const FString& Cue)
{
	// ADR052's established cue route. Content fetching/playback remains the touring service's job.
	const IConsoleVariable* Setting = IConsoleManager::Get().FindConsoleVariable(TEXT("daedalus.Jukebox"));
	const FString Url = Setting ? Setting->GetString() : FString();
	if (Url.IsEmpty()) { Transport->Music.Reset(); Status += TEXT("; jukebox unconfigured"); return; }
	TSharedRef<IHttpRequest, ESPMode::ThreadSafe> Request = FHttpModule::Get().CreateRequest();
	Transport->MusicRequest = Request;
	Request->SetURL(Url);
	Request->SetVerb(TEXT("POST"));
	Request->SetHeader(TEXT("Content-Type"), TEXT("application/json"));
	Request->SetContentAsString(FString::Printf(TEXT("{\"cue\":\"%s\",\"changed\":true,\"sfx\":[]}"), *Cue));
	Request->SetTimeout(5.0f);
	Request->SetDelegateThreadPolicy(EHttpRequestDelegateThreadPolicy::CompleteOnGameThread);
	const TWeakObjectPtr<UDaedalusIslandAudio> Weak(this);
	// The cue acknowledgement is bounded too; we never download touring tracks here.
	TSharedRef<FBoundedAudBody, ESPMode::ThreadSafe> Received = MakeShared<FBoundedAudBody, ESPMode::ThreadSafe>();
	if (!Request->SetResponseBodyReceiveStreamDelegateV2(FHttpRequestStreamDelegateV2::CreateLambda([Received](void* Data, int64& Length)
	{
		Received->Serialize(Data, Length);
		if (Received->IsError()) Length = 0;
	})))
	{
		Transport->MusicRequest.Reset();
		Transport->Music.Reset();
		Status += TEXT("; bounded jukebox stream unavailable");
		return;
	}
	Request->OnProcessRequestComplete().BindLambda([Weak, Received](FHttpRequestPtr Completed, FHttpResponsePtr Response, bool bOk)
	{
		UDaedalusIslandAudio* Self = Weak.Get();
		if (!Self || Self->bEnded || Self->Transport->MusicRequest != Completed) return;
		Self->Transport->MusicRequest.Reset();
		const bool bAccepted = bOk && Response && !Received->IsError() && Response->GetResponseCode() >= 200 && Response->GetResponseCode() < 300;
		if (!bAccepted)
		{
			Self->Status += TEXT("; jukebox cue refused/unavailable");
		}
		std::string Next;
		if (Self->Transport->Music.Complete(bAccepted, Next)) Self->SendMusicCue(UTF8_TO_TCHAR(Next.c_str()));
	});
	if (!Request->ProcessRequest() && Transport->MusicRequest == Request)
	{
		Transport->MusicRequest.Reset();
		Transport->Music.Reset();
		Status += TEXT("; jukebox request could not start");
	}
}

bool UDaedalusIslandAudio::PlayCreatureCall()
{
	if (!IsServer() || !Prepared || Prepared->Revision != Accepted.Revision) return false;
	MulticastCall(Accepted.Revision);
	return true;
}

void UDaedalusIslandAudio::MulticastCall_Implementation(uint32 Revision)
{
	if (bEnded || !GetWorld() || GetWorld()->GetNetMode() == NM_DedicatedServer || !Prepared || Prepared->Revision != Revision) return;
	if (!CallVoice)
	{
		CallVoice = NewObject<UAudioComponent>(GetOwner());
		CallVoice->bAutoActivate = false;
		CallVoice->bAllowSpatialization = bSpatialize;
		CallVoice->bOverrideAttenuation = true;
		CallVoice->AttenuationOverrides.bAttenuate = bSpatialize;
		CallVoice->AttenuationOverrides.bSpatialize = bSpatialize;
		CallVoice->AttenuationOverrides.AttenuationShape = EAttenuationShape::Sphere;
		CallVoice->AttenuationOverrides.AttenuationShapeExtents = FVector(200.f, 0.f, 0.f);
		CallVoice->AttenuationOverrides.FalloffDistance = 3000.f;
		CallVoice->SetupAttachment(GetOwner()->GetRootComponent());
		CallVoice->RegisterComponent();
	}
	CallVoice->Stop();
	if (!CallWave) CallWave = NewObject<USoundWaveProcedural>(this);
	CallWave->ResetAudio();
	CallWave->SetSampleRate(DA::SampleRate);
	CallWave->NumChannels = 1;
	CallWave->Duration = static_cast<float>(Prepared->Pcm.size()) / DA::SampleRate;
	CallWave->bLooping = false;
	CallWave->QueueAudio(reinterpret_cast<const uint8*>(Prepared->Pcm.data()), static_cast<int32>(Prepared->Pcm.size() * sizeof(int16_t)));
	CallVoice->SetSound(CallWave);
	CallVoice->SetVolumeMultiplier(FMath::Clamp(CallVolume, 0.f, 1.f));
	CallVoice->Play();
	// Procedural waves pad underruns. Explicitly stop the single voice when this bounded call ends.
	GetWorld()->GetTimerManager().SetTimer(CallStopTimer, FTimerDelegate::CreateWeakLambda(this, [this]()
	{
		if (CallVoice) CallVoice->Stop();
	}), CallWave->Duration + 0.1f, false);
}

void UDaedalusIslandAudio::StopLocal()
{
	if (GetWorld()) GetWorld()->GetTimerManager().ClearTimer(CallStopTimer);
	if (CallVoice) CallVoice->Stop();
	CallWave = nullptr;
	for (auto& Voice : AmbientVoices) if (Voice.Value) Voice.Value->DestroyComponent();
	AmbientVoices.Reset();
	Prepared.Reset();
	MissingLayers.Reset();
	Status = TEXT("audio stopped");
}

void UDaedalusIslandAudio::StopAudio()
{
	if (!IsServer()) return;
	++WorkGeneration;
	Transport->Requests.Invalidate();
	bReplicaPending = false;
	if (Transport->Request) Transport->Request->CancelRequest();
	Transport->Request.Reset();
	TSharedPtr<IHttpRequest, ESPMode::ThreadSafe> MusicRequest = MoveTemp(Transport->MusicRequest);
	Transport->Music.Reset();
	if (MusicRequest) MusicRequest->CancelRequest();
	Accepted.Text.Reset();
	++Accepted.Revision;
	GetOwner()->ForceNetUpdate();
	StopLocal();
}

void UDaedalusIslandAudio::EndPlay(const EEndPlayReason::Type Reason)
{
	bEnded = true;
	++WorkGeneration;
	Transport->Requests.Invalidate();
	if (Transport->Request) Transport->Request->CancelRequest();
	Transport->Request.Reset();
	if (Transport->MusicRequest) Transport->MusicRequest->CancelRequest();
	Transport->MusicRequest.Reset();
	Transport->Bearer.Reset();
	StopLocal();
	Super::EndPlay(Reason);
}
