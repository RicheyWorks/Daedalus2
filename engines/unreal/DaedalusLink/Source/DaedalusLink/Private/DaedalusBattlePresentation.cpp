#include "DaedalusBattlePresentation.h"
#include "Animation/AnimSequence.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/SceneComponent.h"
#include "Engine/SkeletalMesh.h"
#include <algorithm>
#include <cmath>

ADaedalusBattlePresentation::ADaedalusBattlePresentation()
{
    PrimaryActorTick.bCanEverTick=true;
    RootComponent=CreateDefaultSubobject<USceneComponent>(TEXT("StageRoot"));
}

bool ADaedalusBattlePresentation::Submit(const std::vector<daedalus::stage::Cue>& Cues)
{
    if (Cues.size()>512 || Queue.size()+Cues.size()>512) return false;
    for (const auto& Cue:Cues)
        if (!std::isfinite(Cue.At) || !std::isfinite(Cue.Dur)
            || Cue.At<0 || Cue.At>120 || Cue.Dur<0 || Cue.Dur>120
            || Cue.Text.size()>4096 || Cue.Actor < -1 || Cue.Actor>31
            || Cue.Target < -1 || Cue.Target>31
            || static_cast<int>(Cue.K)<0 || static_cast<int>(Cue.K)>static_cast<int>(daedalus::stage::Kind::Camera))
            return false;
    for (const auto& Cue:Cues) Queue.push_back({Cue,Clock+Cue.At});
    std::stable_sort(Queue.begin(),Queue.end(),[](const Pending& A,const Pending& B){return A.Due<B.Due;});
    return true;
}

void ADaedalusBattlePresentation::ClearCues() { Queue.clear(); Clock=0.0; ++Generation; }

AActor* ADaedalusBattlePresentation::Slot(int Index,bool bFoe) const
{
    const auto& Slots=bFoe?Foes:Members;
    return Slots.IsValidIndex(Index) && IsValid(Slots[Index]) ? Slots[Index].Get() : nullptr;
}

void ADaedalusBattlePresentation::Play(AActor* Actor,UAnimSequence* Animation)
{
    if (!IsValid(Actor) || !IsValid(Animation)) return;
    auto* Mesh=Actor->FindComponentByClass<USkeletalMeshComponent>();
    if (Mesh && Mesh->GetSkeletalMeshAsset()
        && Mesh->GetSkeletalMeshAsset()->GetSkeleton()==Animation->GetSkeleton())
        Mesh->PlayAnimation(Animation,false);
}

void ADaedalusBattlePresentation::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    if (bPaused || !FMath::IsFinite(DeltaSeconds) || DeltaSeconds<0) return;
    Clock+=DeltaSeconds;
    // Remove the due batch before callbacks; a callback may clear/submit cues.
    std::vector<Pending> Due;
    while (!Queue.empty() && Queue.front().Due<=Clock && Due.size()<32)
    { Due.push_back(Queue.front()); Queue.erase(Queue.begin()); }
    const uint64 DispatchGeneration=Generation;
    for (const auto& Entry:Due)
    {
        if (Generation!=DispatchGeneration || IsActorBeingDestroyed()) break;
        const auto& Cue=Entry.Cue;
        auto* Actor=Slot(Cue.Actor,Cue.ActorIsFoe);
        auto* Target=Slot(Cue.Target,Cue.TargetIsFoe);
        if (Cue.K==daedalus::stage::Kind::Swing) Play(Actor,AttackAnimation);
        if (Cue.K==daedalus::stage::Kind::Flinch) Play(Target,HurtAnimation);
        PresentCue(UTF8_TO_TCHAR(daedalus::stage::Name(Cue.K)),Actor,Target,Cue.Amount,
                   UTF8_TO_TCHAR(Cue.Text.c_str()),static_cast<float>(Cue.Dur),Cue.TargetIsFoe,Cue.Target);
    }
}
