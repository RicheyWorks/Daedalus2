// SPDX-License-Identifier: MIT
#include "DaedalusTideglassStation.h"
#include "Components/PointLightComponent.h"
#include "DaedalusHero.h"
#include "Kismet/GameplayStatics.h"
#include "Sound/SoundBase.h"

ADaedalusTideglassStation::ADaedalusTideglassStation()
{
	Workshop = CreateDefaultSubobject<UDaedalusTideglassWorkshopComponent>(TEXT("TideglassWorkshop"));
}

void ADaedalusTideglassStation::BeginPlay()
{
	Super::BeginPlay();
	Workshop->OnFeedback.AddDynamic(this, &ADaedalusTideglassStation::HandleFeedback);
	// Restore appearance from host facts without awarding or replaying the consequence.
	FDaedalusTideglassState State;
	if (Workshop->ReadState(State) && State.bConduitOpen)
	{
		Glow->SetLightColor(FLinearColor(0.1f, 0.8f, 1.f));
		Glow->SetIntensity(1200.f);
	}
}

FString ADaedalusTideglassStation::Prompt(const ADaedalusHero* Hero) const
{
	FDaedalusTideglassState State;
	if (WorkshopId.IsEmpty() || !Workshop->ReadState(State)) return TEXT("Workshop connection pending");
	if (State.bCommissionPaid) return TEXT("Harbour commission complete");
	if (!State.bValveCrafted) return TEXT("Craft the conduit pulse valve");
	if (!State.bConduitOpen) return TEXT("Install valve in the dry morning window");
	return FString::Printf(TEXT("Deliver %d clean water for the harbour commission"), Workshop->Config.WaterUnits);
}

bool ADaedalusTideglassStation::Use(ADaedalusHero* Hero)
{
	if (!Hero || Hero->GetWorld() != GetWorld() || !HasAuthority() || WorkshopId.IsEmpty() ||
		FVector::DistSquared(Hero->GetActorLocation(), GetActorLocation()) > FMath::Square(Hero->InteractReach)) return false;
	FDaedalusTideglassState State;
	const bool bRead = Workshop->ReadState(State);
	EDaedalusTideglassAction Action = EDaedalusTideglassAction::CraftValve;
	FString Suffix = TEXT("/craft");
	if (bRead && State.bValveCrafted) { Action = EDaedalusTideglassAction::InstallValve; Suffix = TEXT("/install"); }
	if (bRead && State.bConduitOpen) { Action = EDaedalusTideglassAction::SupplyWater; Suffix = TEXT("/supply"); }
	const FDaedalusTideglassResult Result = Workshop->TryAction(Action, WorkshopId + Suffix);
	return Result.Status == EDaedalusTideglassStatus::Committed || Result.Status == EDaedalusTideglassStatus::AlreadyCommitted;
}

void ADaedalusTideglassStation::HandleFeedback(const FDaedalusTideglassResult& Result)
{
	if (UDaedalusOrrery* Orrery = UDaedalusOrrery::Get(this)) Orrery->Say(Result.Message);
	if (Result.Status == EDaedalusTideglassStatus::AlreadyCommitted) return;
	const bool bCommitted = Result.Status == EDaedalusTideglassStatus::Committed;
	Glow->SetLightColor(bCommitted ? FLinearColor(0.1f, 0.8f, 1.f) : FLinearColor(1.f, 0.25f, 0.08f));
	Glow->SetIntensity(bCommitted ? 1200.f : 300.f);
	if (USoundBase* Sound = bCommitted ? CommitSound.Get() : BlockedSound.Get())
		UGameplayStatics::PlaySoundAtLocation(this, Sound, GetActorLocation());
}
