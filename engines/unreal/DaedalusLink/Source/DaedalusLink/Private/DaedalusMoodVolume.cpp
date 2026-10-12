// SPDX-License-Identifier: MIT
#include "DaedalusMoodVolume.h"
#include "Components/BoxComponent.h"
#include "GameFramework/Pawn.h"

ADaedalusMoodVolume::ADaedalusMoodVolume()
{
	Box = CreateDefaultSubobject<UBoxComponent>(TEXT("Box"));
	Box->SetBoxExtent(FVector(5000.f, 5000.f, 3000.f));
	Box->SetCollisionProfileName(TEXT("Trigger"));
	RootComponent = Box;
	Box->OnComponentBeginOverlap.AddDynamic(this, &ADaedalusMoodVolume::OnEnter);
}

void ADaedalusMoodVolume::OnEnter(UPrimitiveComponent*, AActor* Other, UPrimitiveComponent*, int32, bool, const FHitResult&)
{
	const APawn* P = Cast<APawn>(Other);
	if (!P || !P->IsPlayerControlled()) return;
	if (ADaedalusSkyDirector* D = ADaedalusSkyDirector::Find(this))
	{
		D->SetMood(Mood);
		if (bSetWeather) D->SetWeather(Weather);
	}
}
