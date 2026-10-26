// SPDX-License-Identifier: MIT

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "InputCoreTypes.h"
#include "DaedalusEchoBellSessionCore.h"
#include "DaedalusEchoBellGate.generated.h"

class UBoxComponent;
class USceneComponent;
class USoundBase;
class UStaticMeshComponent;

DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FDaedalusEchoGateOpened, int32, Attempts);
DECLARE_DYNAMIC_MULTICAST_DELEGATE_ThreeParams(FDaedalusEchoGateRetry, int32, Attempt, int32, Hits, int32, FirstMiss);

/**
 * LAB03 Echo Bell labyrinth gate (contest gap G01, docs/contracts/echo-bell-v1).
 *
 * A peal of 3 + Difficulty bells rings down maze corridors; each bell's echo returns after
 * 200 + 70 x depth ms. Tap the Use key on every echo (within +/- the window) to open the gate;
 * a miss fires OnRetry and the same peal plays again after RetryDelaySeconds.
 *
 * All rules live in DaedalusEchoBellSessionCore.h / DaedalusEchoBellCore.h (engine-free, tested in
 * core-test/echo_bell). This actor only feeds the clock and taps in and plays the cues out:
 * a USoundBase per bell when given (pitched to the cue's Hz unless disabled), otherwise a
 * procedural struck-bronze tone at the cue sheet's Hz and gain; echoes at x0.5 gain, low-passed.
 */
UCLASS(Blueprintable)
class DAEDALUSLINK_API AEchoBellGate : public AActor
{
	GENERATED_BODY()

public:
	AEchoBellGate();

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|EchoBell") int64 Seed = 1;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|EchoBell", meta = (ClampMin = "0", ClampMax = "3")) int32 Difficulty = 0;
	/** Echo Crickets assist: window x1.5 and a quiet chirp on each echo. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|EchoBell") bool bCrickets = false;
	/** Corridor depth in maze cells per bell (exactly 3 + Difficulty values, 1..40). Empty = the seed picks. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|EchoBell") TArray<int32> MazeDepths;

	/** Optional sound per bell (index = bell). Empty / null entries use the procedural tone. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|EchoBell|Sound") TArray<TObjectPtr<USoundBase>> BellSounds;
	/** Retune BellSounds to each cue's Hz (pitch = Hz / SampleRootHz). Off for samples already tuned per bell. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|EchoBell|Sound") bool bPitchSamplesToCue = true;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|EchoBell|Sound") float SampleRootHz = 146.832f;
	/** Optional cricket chirp; null uses a short procedural chirp. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|EchoBell|Sound") TObjectPtr<USoundBase> CricketSound;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|EchoBell|Input") FKey UseKey = EKeys::E;
	/** Start the peal when a player pawn walks into the trigger. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|EchoBell|Input") bool bAutoStartOnOverlap = true;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|EchoBell") float RetryDelaySeconds = 2.f;
	/** How far the door sinks when the gate opens (cm). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|EchoBell") float OpenDrop = 400.f;

	UPROPERTY(BlueprintAssignable, Category = "Daedalus|EchoBell") FDaedalusEchoGateOpened OnGateOpened;
	UPROPERTY(BlueprintAssignable, Category = "Daedalus|EchoBell") FDaedalusEchoGateRetry OnRetry;

	/** Build the peal from Seed/Difficulty/bCrickets/MazeDepths and start ringing. False if invalid or already running/open. */
	UFUNCTION(BlueprintCallable, Category = "Daedalus|EchoBell") bool BeginPeal();
	/** One Use-key tap (also bound to UseKey while a player is in the trigger). */
	UFUNCTION(BlueprintCallable, Category = "Daedalus|EchoBell") void Tap();
	UFUNCTION(BlueprintPure, Category = "Daedalus|EchoBell") bool IsOpen() const;
	UFUNCTION(BlueprintPure, Category = "Daedalus|EchoBell") int32 GetAttempts() const;
	UFUNCTION(BlueprintPure, Category = "Daedalus|EchoBell") int32 GetWindowMs() const;
	/** One line for the harness: phase, attempts, taps, cues played. */
	UFUNCTION(BlueprintCallable, Category = "Daedalus|EchoBell") FString State() const;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Daedalus|EchoBell") TObjectPtr<USceneComponent> Root;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Daedalus|EchoBell") TObjectPtr<UBoxComponent> Trigger;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Daedalus|EchoBell") TObjectPtr<UStaticMeshComponent> Door;

protected:
	virtual void BeginPlay() override;
	virtual void Tick(float DeltaSeconds) override;

private:
	UFUNCTION() void OnTriggerBegin(UPrimitiveComponent* Overlapped, AActor* Other, UPrimitiveComponent* OtherComp, int32 BodyIndex, bool bFromSweep, const FHitResult& Sweep);
	UFUNCTION() void OnTriggerEnd(UPrimitiveComponent* Overlapped, AActor* Other, UPrimitiveComponent* OtherComp, int32 BodyIndex);

	void PlayCue(const daedalus::labyrinth::EchoCue& Cue);
	void OpenGate();
	void RestartAfterMiss();
	int32 NowMs() const;

	daedalus::labyrinth::EchoBellSession Session;
	std::vector<daedalus::labyrinth::EchoCue> Due;
	double PealStartSeconds = 0.0;
	bool bInputBound = false;
	FTimerHandle RetryTimer;
};