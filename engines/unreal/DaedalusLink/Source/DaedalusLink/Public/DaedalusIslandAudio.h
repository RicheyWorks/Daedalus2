// SPDX-License-Identifier: MIT
#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "TimerManager.h"
#include "DaedalusIslandAudio.generated.h"

class UAudioComponent;
class USoundBase;
class USoundWaveProcedural;
struct FDaedalusPreparedAudio;
struct FDaedalusAudioTransport;

/** Inputs to Astra's existing /api/v1/audio/design; no world decisions are made here. */
USTRUCT(BlueprintType)
struct FDaedalusAudioDesignInput
{
	GENERATED_BODY()
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Daedalus|Audio") FString Biome = TEXT("FOREST");
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Daedalus|Audio") double Hour = 12.0;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Daedalus|Audio") double Rain = 0.0;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Daedalus|Audio") double Wind = 0.0;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Daedalus|Audio") double WaterNear = 0.0;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Daedalus|Audio") FString Species = TEXT("CANID");
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Daedalus|Audio") FString GenomeHex = TEXT("00");
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Daedalus|Audio") FString MusicCue = TEXT("FIELD");
};

/** One replicated property keeps the accepted spec, seed and local revision together. */
USTRUCT()
struct FDaedalusAcceptedAudio
{
	GENERATED_BODY()
	UPROPERTY() FString Text;
	UPROPERTY() uint64 Seed = 0;
	UPROPERTY() uint32 Revision = 0;
};

/** Optional server-owned audio endpoint on an existing replicated scene actor.
 * Java supplies AUD 1 decisions; Unreal caches the call and owns immediate playback.
 * Ambient bindings must be looping assets with a Density float parameter where applicable.
 * Missing assets are silent and reported. This does not create scene bindings or music tracks.
 */
UCLASS(ClassGroup=(Daedalus), meta=(BlueprintSpawnableComponent))
class DAEDALUSLINK_API UDaedalusIslandAudio : public UActorComponent
{
	GENERATED_BODY()
public:
	UDaedalusIslandAudio();
	/** Local scene bindings for the contract's layer IDs; never loaded from Java paths. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Daedalus|Audio")
	TMap<FName, TObjectPtr<USoundBase>> AmbientBindings;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Daedalus|Audio", meta=(ClampMin="0", ClampMax="1"))
	float CallVolume = 0.7f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Daedalus|Audio") bool bSpatialize = true;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Transient, Category="Daedalus|Audio") FString Status;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Transient, Category="Daedalus|Audio") FString MissingLayers;

	/** Server bootstrap only: existing host JWT stays private, transient and unreplicated. */
	void ConfigureDesignService(const FString& ServerBaseUrl, const FString& ExistingHostBearer);
	/** Explicit refresh; no polling, synchronous waits, retries, or frame-critical round trips. */
	UFUNCTION(BlueprintCallable, Category="Daedalus|Audio") bool RefreshDesign(const FDaedalusAudioDesignInput& Input);
	/** Server-side fixture/transport seam. Validation and synthesis still happen asynchronously. */
	UFUNCTION(BlueprintCallable, Category="Daedalus|Audio") bool AcceptDesignText(const FString& Aud1, const FString& GenomeHex);
	/** Server-approved cosmetic call, using the prepared PCM; at most one call voice. */
	UFUNCTION(BlueprintCallable, Category="Daedalus|Audio") bool PlayCreatureCall();
	UFUNCTION(BlueprintCallable, Category="Daedalus|Audio") void StopAudio();
	virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const override;
	virtual void EndPlay(const EEndPlayReason::Type Reason) override;

private:
	UPROPERTY(ReplicatedUsing=OnRep_Accepted) FDaedalusAcceptedAudio Accepted;
	UPROPERTY(Transient) TMap<FName, TObjectPtr<UAudioComponent>> AmbientVoices;
	UPROPERTY(Transient) TObjectPtr<UAudioComponent> CallVoice;
	UPROPERTY(Transient) TObjectPtr<USoundWaveProcedural> CallWave;
	UFUNCTION() void OnRep_Accepted();
	UFUNCTION(NetMulticast, Unreliable) void MulticastCall(uint32 Revision);
	void StartPreparation(FString Text, uint64 Seed, uint32 Revision, bool bPublish);
	void ApplyPrepared(TSharedPtr<FDaedalusPreparedAudio, ESPMode::ThreadSafe> Value);
	void StopLocal();
	void RouteMusicCue(const FString& Cue);
	void SendMusicCue(const FString& Cue);
	bool IsServer() const;
	TSharedPtr<FDaedalusPreparedAudio, ESPMode::ThreadSafe> Prepared;
	TSharedPtr<FDaedalusAudioTransport> Transport;
	FTimerHandle CallStopTimer;
	uint64 WorkGeneration = 0;
	bool bPreparing = false;
	bool bReplicaPending = false;
	bool bEnded = false;
};
