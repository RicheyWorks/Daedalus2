// SPDX-License-Identifier: MIT
#include "DaedalusMoodVolume.h"
#include "Camera/PlayerCameraManager.h"
#include "Components/BoxComponent.h"
#include "GameFramework/Pawn.h"
#include "Kismet/GameplayStatics.h"

ADaedalusMoodVolume::ADaedalusMoodVolume()
{
	PrimaryActorTick.bCanEverTick = true;
	PrimaryActorTick.TickInterval = 0.5f;  // a view check twice a second is plenty
	Box = CreateDefaultSubobject<UBoxComponent>(TEXT("Box"));
	Box->SetBoxExtent(FVector(5000.f, 5000.f, 3000.f));
	Box->SetCollisionProfileName(TEXT("Trigger"));
	RootComponent = Box;
	Box->OnComponentBeginOverlap.AddDynamic(this, &ADaedalusMoodVolume::OnEnter);
	Box->OnComponentEndOverlap.AddDynamic(this, &ADaedalusMoodVolume::OnExit);
}

bool ADaedalusMoodVolume::IsPointInside(const FVector& P) const
{
	const FVector L = GetActorTransform().InverseTransformPosition(P);  // handles actor scale + rotation
	const FVector E = Box->GetUnscaledBoxExtent();
	return FMath::Abs(L.X) <= E.X && FMath::Abs(L.Y) <= E.Y && FMath::Abs(L.Z) <= E.Z;
}

void ADaedalusMoodVolume::BeginPlay()
{
	Super::BeginPlay();
	if (bForceOnBeginPlay) ApplyNow(true);
}

void ADaedalusMoodVolume::ApplyNow(bool bInstant)
{
	ADaedalusSkyDirector* D = ADaedalusSkyDirector::Find(this);
	if (!D) return;
	if (!bApplied) { PrevMood = D->Mood; PrevWeather = D->Weather; bPrevClock = D->bClockRunning; PrevAuto = D->AutoWeatherHours; }
	bApplied = true;
	if (bHoldWhileInside) { D->bClockRunning = false; D->AutoWeatherHours = 0.f; }
	if (SetHour >= 0.f) D->SetTimeOfDay(SetHour);
	D->SetMood(Mood, bInstant);
	if (bSetWeather) D->SetWeather(Weather, bInstant);
}

void ADaedalusMoodVolume::Restore()
{
	if (!bApplied || bForceOnBeginPlay) return;
	bApplied = false;
	if (!bRestoreOnExit) return;
	if (ADaedalusSkyDirector* D = ADaedalusSkyDirector::Find(this))
	{
		D->bClockRunning = bPrevClock; D->AutoWeatherHours = PrevAuto;
		D->SetMood(PrevMood); if (bSetWeather) D->SetWeather(PrevWeather);
	}
}

void ADaedalusMoodVolume::Tick(float Dt)
{
	Super::Tick(Dt);
	if (!bTriggerOnView) return;
	const APlayerCameraManager* Cam = UGameplayStatics::GetPlayerCameraManager(this, 0);
	if (!Cam) return;
	const bool bIn = IsPointInside(Cam->GetCameraLocation());
	if (bIn && !bApplied) ApplyNow(false);
	else if (!bIn && bApplied) Restore();
}

void ADaedalusMoodVolume::OnEnter(UPrimitiveComponent*, AActor* Other, UPrimitiveComponent*, int32, bool, const FHitResult&)
{
	const APawn* P = Cast<APawn>(Other);
	if (P && P->IsPlayerControlled() && !bApplied) ApplyNow(false);
}

void ADaedalusMoodVolume::OnExit(UPrimitiveComponent*, AActor* Other, UPrimitiveComponent*, int32)
{
	const APawn* P = Cast<APawn>(Other);
	if (P && P->IsPlayerControlled() && !bTriggerOnView) Restore();
}
