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
    if (Authority())
    {
        GetOwner()->OnActorBeginOverlap.AddDynamic(this, &UDaedalusBullSeaEventComponent::OnOwnerOverlap);
        GetOwner()->OnActorEndOverlap.AddDynamic(this, &UDaedalusBullSeaEventComponent::OnOwnerExit);
    }
}
bool UDaedalusBullSeaEventComponent::BindHostBull(const FString& StableBullId, UDaedalusUnicornRewardComponent* CreditedPlayer, bool BurningVerified)
{
    if (!Authority() || !BullId.IsEmpty() || StableBullId.IsEmpty() || StableBullId.Len() > 100 ||
        !IsValid(CreditedPlayer) || CreditedPlayer->GetWorld() != GetWorld() ||
        !CreditedPlayer->GetOwner() || !CreditedPlayer->GetOwner()->HasAuthority()) return false;
    const FTCHARToUTF8 Encoded(*StableBullId);
    if (!DaedalusUnicornReward::Gate::ValidEntityIdentity(std::string(Encoded.Get(), Encoded.Length()))) return false;
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
    if (!bArrivalRecorded && PendingSea.IsValid())
        GetWorld()->GetTimerManager().SetTimer(ArrivalRetryTimer, this, &UDaedalusBullSeaEventComponent::OnArrivalRetry, 0.25f, true);
}
bool UDaedalusBullSeaEventComponent::RetryPendingArrival()
{
    ATriggerVolume* Sea = PendingSea.Get();
    UDaedalusUnicornRewardComponent* Player = Reward.Get();
    if (!Authority() || bRecordingArrival || bArrivalRecorded || !bBurningVerified || BullId.IsEmpty() || !Sea || !Player ||
        Sea->GetWorld() != GetWorld() || !Sea->ActorHasTag(TEXT("DaedalusSeaArrival")) ||
        !Sea->EncompassesPoint(GetOwner()->GetActorLocation())) return false;
    TGuardValue<bool> Guard(bRecordingArrival, true);
    bArrivalRecorded = Player->HasRecordedBull(BullId) || Player->RecordBullAtSea(BullId, true, true);
    if (bArrivalRecorded) ClearPendingArrival();
    return bArrivalRecorded;
}
bool UDaedalusBullSeaEventComponent::SetBurningFromHost(bool BurningVerified)
{
    if (!Authority()) return false;
    bBurningVerified = BurningVerified;
    if (!BurningVerified) ClearPendingArrival();
    return true;
}
void UDaedalusBullSeaEventComponent::OnOwnerExit(AActor* OwnerActor, AActor* OtherActor)
{
    if (OwnerActor == GetOwner() && OtherActor == PendingSea.Get()) ClearPendingArrival();
}
void UDaedalusBullSeaEventComponent::OnArrivalRetry()
{
    ATriggerVolume* Sea = PendingSea.Get();
    if (!Authority() || !Sea || !Reward.IsValid() || !GetOwner()->IsOverlappingActor(Sea))
    {
        ClearPendingArrival();
        return;
    }
    RetryPendingArrival();
}
void UDaedalusBullSeaEventComponent::ClearPendingArrival()
{
    if (GetWorld()) GetWorld()->GetTimerManager().ClearTimer(ArrivalRetryTimer);
    PendingSea.Reset();
}
void UDaedalusBullSeaEventComponent::EndPlay(const EEndPlayReason::Type Reason)
{
    ClearPendingArrival();
    if (GetOwner())
    {
        GetOwner()->OnActorBeginOverlap.RemoveDynamic(this, &UDaedalusBullSeaEventComponent::OnOwnerOverlap);
        GetOwner()->OnActorEndOverlap.RemoveDynamic(this, &UDaedalusBullSeaEventComponent::OnOwnerExit);
    }
    if (auto* Player = Reward.Get()) Player->OnRecordStatus.RemoveDynamic(this, &UDaedalusBullSeaEventComponent::OnPlayerRecordStatus);
    Super::EndPlay(Reason);
}
void UDaedalusBullSeaEventComponent::OnPlayerRecordStatus(bool Ready, bool, int64)
{
    if (Ready && PendingSea.IsValid() && !bArrivalRecorded) RetryPendingArrival();
}
