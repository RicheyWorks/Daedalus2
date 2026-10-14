// SPDX-License-Identifier: MIT
#include "DaedalusBullSeaEventComponent.h"
#include "DaedalusUnicornRewardComponent.h"
#include "Engine/TriggerVolume.h"
#include "Engine/World.h"
#include "GameFramework/Actor.h"

UDaedalusBullSeaEventComponent::UDaedalusBullSeaEventComponent() { PrimaryComponentTick.bCanEverTick = false; }
bool UDaedalusBullSeaEventComponent::Authority() const
{
    return GetOwner() && GetOwner()->HasAuthority() && GetWorld() && GetWorld()->IsGameWorld();
}
void UDaedalusBullSeaEventComponent::BeginPlay()
{
    Super::BeginPlay();
    if (Authority()) GetOwner()->OnActorBeginOverlap.AddDynamic(this, &UDaedalusBullSeaEventComponent::OnOwnerOverlap);
}
bool UDaedalusBullSeaEventComponent::BindHostBull(const FString& StableBullId, UDaedalusUnicornRewardComponent* CreditedPlayer, bool BurningVerified)
{
    if (!Authority() || !BullId.IsEmpty() || StableBullId.IsEmpty() || StableBullId.Len() > 100 ||
        !IsValid(CreditedPlayer) || CreditedPlayer->GetWorld() != GetWorld() ||
        !CreditedPlayer->GetOwner() || !CreditedPlayer->GetOwner()->HasAuthority()) return false;
    BullId = StableBullId;
    Reward = CreditedPlayer;
    bBurningVerified = BurningVerified;
    CreditedPlayer->OnRecordStatus.AddDynamic(this, &UDaedalusBullSeaEventComponent::OnPlayerRecordStatus);
    return true;
}
void UDaedalusBullSeaEventComponent::OnOwnerOverlap(AActor* OwnerActor, AActor* OtherActor)
{
    if (!Authority() || OwnerActor != GetOwner() || !bBurningVerified || bArrivalRecorded) return;
    ATriggerVolume* Sea = Cast<ATriggerVolume>(OtherActor);
    if (!Sea || !Sea->ActorHasTag(TEXT("DaedalusSeaArrival"))) return;
    PendingSea = Sea;
    RetryPendingArrival();
}
bool UDaedalusBullSeaEventComponent::RetryPendingArrival()
{
    ATriggerVolume* Sea = PendingSea.Get();
    UDaedalusUnicornRewardComponent* Player = Reward.Get();
    if (!Authority() || bArrivalRecorded || !bBurningVerified || BullId.IsEmpty() || !Sea || !Player ||
        Sea->GetWorld() != GetWorld() || !Sea->ActorHasTag(TEXT("DaedalusSeaArrival")) ||
        !Sea->EncompassesPoint(GetOwner()->GetActorLocation())) return false;
    bArrivalRecorded = Player->RecordBullAtSea(BullId, true, true);
    return bArrivalRecorded;
}
void UDaedalusBullSeaEventComponent::OnPlayerRecordStatus(bool Ready, bool, int64)
{
    if (Ready && PendingSea.IsValid() && !bArrivalRecorded) RetryPendingArrival();
}
