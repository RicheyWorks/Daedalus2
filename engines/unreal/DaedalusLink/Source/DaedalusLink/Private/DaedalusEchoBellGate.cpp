// SPDX-License-Identifier: MIT

#include "DaedalusEchoBellGate.h"

#include "Components/AudioComponent.h"
#include "Components/BoxComponent.h"
#include "Components/InputComponent.h"
#include "Components/SceneComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/GameplayStatics.h"
#include "Sound/SoundBase.h"
#include "Sound/SoundWaveProcedural.h"
#include "TimerManager.h"
#include "UObject/ConstructorHelpers.h"

using daedalus::labyrinth::EchoCue;
using daedalus::labyrinth::EchoCueKind;
using daedalus::labyrinth::EchoCueRules;
using daedalus::labyrinth::EchoPhase;

namespace
{
	constexpr int32 ToneRate = 22050;

	USoundWaveProcedural* NewMonoWave(UObject* Outer, const TArray<int16>& Pcm)
	{
		USoundWaveProcedural* Wave = NewObject<USoundWaveProcedural>(Outer);
		Wave->SetSampleRate(ToneRate);
		Wave->NumChannels = 1;
		Wave->Duration = static_cast<float>(Pcm.Num()) / ToneRate;
		Wave->SoundGroup = SOUNDGROUP_Default;
		Wave->bLooping = false;
		Wave->QueueAudio(reinterpret_cast<const uint8*>(Pcm.GetData()), Pcm.Num() * sizeof(int16));
		return Wave;
	}

	/** Soft struck bronze at Hz: fundamental plus a quickly fading 2.76x partial kept under ~2 kHz; echoes drop it. */
	USoundWaveProcedural* MakeBellTone(UObject* Outer, double Hz, bool bEcho)
	{
		const int32 N = FMath::RoundToInt(ToneRate * EchoCueRules::kBellDecaySeconds);
		const double Partial = Hz * 2.76;
		const bool bPartial = !bEcho && Partial < 2000.0;
		TArray<int16> Pcm;
		Pcm.SetNumUninitialized(N);
		for (int32 i = 0; i < N; ++i)
		{
			const double T = static_cast<double>(i) / ToneRate;
			const double Attack = FMath::Min(1.0, T / 0.004);
			double S = FMath::Sin(2.0 * PI * Hz * T) * FMath::Exp(-3.0 * T);
			if (bPartial) S += 0.35 * FMath::Sin(2.0 * PI * Partial * T) * FMath::Exp(-7.0 * T);
			Pcm[i] = static_cast<int16>(FMath::Clamp(S * Attack * 0.7, -1.0, 1.0) * 32767.0);
		}
		return NewMonoWave(Outer, Pcm);
	}

	/** Three 25 ms chirps at 4.2 kHz: the Echo Crickets tick. */
	USoundWaveProcedural* MakeChirp(UObject* Outer)
	{
		const int32 N = ToneRate / 5;
		TArray<int16> Pcm;
		Pcm.SetNumZeroed(N);
		for (int32 i = 0; i < N; ++i)
		{
			const double T = static_cast<double>(i) / ToneRate;
			const double Phase = FMath::Fmod(T, 0.06);
			if (Phase < 0.025) Pcm[i] = static_cast<int16>(FMath::Sin(2.0 * PI * 4200.0 * T) * FMath::Sin(PI * Phase / 0.025) * 0.5 * 32767.0);
		}
		return NewMonoWave(Outer, Pcm);
	}
}

AEchoBellGate::AEchoBellGate()
{
	PrimaryActorTick.bCanEverTick = true;

	Root = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
	RootComponent = Root;

	Trigger = CreateDefaultSubobject<UBoxComponent>(TEXT("Trigger"));
	Trigger->SetupAttachment(Root);
	Trigger->SetBoxExtent(FVector(300.f, 300.f, 150.f));
	Trigger->SetCollisionProfileName(TEXT("Trigger"));

	Door = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Door"));
	Door->SetupAttachment(Root);
	Door->SetRelativeScale3D(FVector(0.2f, 3.f, 3.f));
	Door->SetRelativeLocation(FVector(0.f, 0.f, 150.f));
	static ConstructorHelpers::FObjectFinder<UStaticMesh> Cube(TEXT("/Engine/BasicShapes/Cube.Cube"));
	if (Cube.Succeeded()) Door->SetStaticMesh(Cube.Object);
}

void AEchoBellGate::BeginPlay()
{
	Super::BeginPlay();
	Trigger->OnComponentBeginOverlap.AddDynamic(this, &AEchoBellGate::OnTriggerBegin);
	Trigger->OnComponentEndOverlap.AddDynamic(this, &AEchoBellGate::OnTriggerEnd);
}

int32 AEchoBellGate::NowMs() const
{
	const UWorld* World = GetWorld();
	return World ? FMath::FloorToInt((World->GetTimeSeconds() - PealStartSeconds) * 1000.0) : 0;
}

bool AEchoBellGate::BeginPeal()
{
	if (Session.Phase() == EchoPhase::Listening || Session.Phase() == EchoPhase::Opened) return false;
	daedalus::labyrinth::EchoGateConfig Config;
	Config.Seed = Seed;
	Config.Difficulty = Difficulty;
	Config.Crickets = bCrickets;
	Config.Depths.assign(MazeDepths.GetData(), MazeDepths.GetData() + MazeDepths.Num());
	std::string Why;
	if (!Session.Start(Config, &Why))
	{
		UE_LOG(LogTemp, Warning, TEXT("EchoBellGate %s: invalid peal (%s)"), *GetName(), UTF8_TO_TCHAR(Why.c_str()));
		return false;
	}
	GetWorldTimerManager().ClearTimer(RetryTimer);
	PealStartSeconds = GetWorld()->GetTimeSeconds();
	return true;
}

void AEchoBellGate::Tap()
{
	Session.Tap(NowMs());
}

void AEchoBellGate::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	if (Session.Phase() != EchoPhase::Listening) return;
	const int32 Now = NowMs();
	Session.Advance(Now, Due);
	for (const EchoCue& Cue : Due) PlayCue(Cue);
	if (!Session.JudgeDue(Now)) return;
	const daedalus::labyrinth::EchoVerdict& Verdict = Session.Finish();
	if (Verdict.Open)
	{
		OpenGate();
		return;
	}
	OnRetry.Broadcast(Session.Attempts(), Verdict.Hits, Verdict.FirstMiss);
	GetWorldTimerManager().SetTimer(RetryTimer, this, &AEchoBellGate::RestartAfterMiss, FMath::Max(0.01f, RetryDelaySeconds), false);
}

void AEchoBellGate::RestartAfterMiss()
{
	if (Session.Retry()) PealStartSeconds = GetWorld()->GetTimeSeconds();
}

void AEchoBellGate::PlayCue(const EchoCue& Cue)
{
	USoundBase* Sound = nullptr;
	float Pitch = 1.f;
	if (Cue.Kind == EchoCueKind::Cricket)
	{
		Sound = CricketSound ? CricketSound.Get() : MakeChirp(this);
	}
	else if (BellSounds.IsValidIndex(Cue.BellIndex) && BellSounds[Cue.BellIndex])
	{
		Sound = BellSounds[Cue.BellIndex];
		if (bPitchSamplesToCue && SampleRootHz > 0.f) Pitch = FMath::Clamp(static_cast<float>(Cue.Hz / SampleRootHz), 0.25f, 4.f);
	}
	else
	{
		Sound = MakeBellTone(this, Cue.Hz, Cue.Kind == EchoCueKind::Echo);
	}
	UAudioComponent* Audio = UGameplayStatics::SpawnSoundAtLocation(this, Sound, GetActorLocation(), FRotator::ZeroRotator, static_cast<float>(Cue.Gain), Pitch);
	if (Audio && Cue.LowPassHz > 0.0)
	{
		Audio->SetLowPassFilterEnabled(true);
		Audio->SetLowPassFilterFrequency(static_cast<float>(Cue.LowPassHz));
	}
}

void AEchoBellGate::OpenGate()
{
	Door->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Door->SetRelativeLocation(Door->GetRelativeLocation() - FVector(0.f, 0.f, OpenDrop));
	OnGateOpened.Broadcast(Session.Attempts());
}

void AEchoBellGate::OnTriggerBegin(UPrimitiveComponent*, AActor* Other, UPrimitiveComponent*, int32, bool, const FHitResult&)
{
	APawn* Pawn = Cast<APawn>(Other);
	APlayerController* PC = Pawn ? Cast<APlayerController>(Pawn->GetController()) : nullptr;
	if (!PC) return;
	EnableInput(PC);
	if (!bInputBound && InputComponent)
	{
		InputComponent->BindKey(UseKey, IE_Pressed, this, &AEchoBellGate::Tap);
		bInputBound = true;
	}
	if (bAutoStartOnOverlap) BeginPeal();
}

void AEchoBellGate::OnTriggerEnd(UPrimitiveComponent*, AActor* Other, UPrimitiveComponent*, int32)
{
	APawn* Pawn = Cast<APawn>(Other);
	if (APlayerController* PC = Pawn ? Cast<APlayerController>(Pawn->GetController()) : nullptr) DisableInput(PC);
}

bool AEchoBellGate::IsOpen() const { return Session.Phase() == EchoPhase::Opened; }
int32 AEchoBellGate::GetAttempts() const { return Session.Attempts(); }
int32 AEchoBellGate::GetWindowMs() const { return Session.WindowMs(); }

FString AEchoBellGate::State() const
{
	return FString::Printf(TEXT("phase=%s attempts=%d taps=%d cues=%d/%d window=%d"),
		UTF8_TO_TCHAR(daedalus::labyrinth::EchoPhaseName(Session.Phase())), Session.Attempts(),
		static_cast<int32>(Session.GetTaps().size()), static_cast<int32>(Session.CuesPlayed()),
		static_cast<int32>(Session.GetCues().size()), Session.WindowMs());
}