#include "DaedalusBattlePresentation.h"
#include "Animation/AnimSequence.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/SceneComponent.h"
#include "Engine/SkeletalMesh.h"
#include "AssetRegistry/AssetRegistryModule.h"
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

void ADaedalusBattlePresentation::BeginPlay()
{
    Super::BeginPlay();
    RefreshCastAnimations();
}

const FDaedalusBattleCastClips* ADaedalusBattlePresentation::ClipsFor(USkeletalMesh* Mesh)
{
    if (!IsValid(Mesh)) return nullptr;
    if (const auto* Existing=CastClips.Find(Mesh)) return Existing;
    if (CastClips.Num()>=64) return nullptr;
    FDaedalusBattleCastClips Clips;
    const FString Root=TEXT("/Game/Daedalus/Art/Cast/");
    const FString Package=Mesh->GetOutermost()->GetName();
    if (Package.StartsWith(Root,ESearchCase::CaseSensitive))
    {
        const FString Relative=Package.Mid(Root.Len());
        int32 Slash=INDEX_NONE;
        if (Relative.FindChar(TEXT('/'),Slash) && Slash>0)
        {
            const FString Folder=Root+Relative.Left(Slash);
            auto& Registry=FModuleManager::LoadModuleChecked<FAssetRegistryModule>(TEXT("AssetRegistry"));
            TArray<FAssetData> Assets;
            Registry.Get().GetAssetsByPath(FName(*Folder),Assets,true);
            Assets.Sort([](const FAssetData& A,const FAssetData& B){return A.GetObjectPathString()<B.GetObjectPathString();});
            for (const FAssetData& Asset:Assets)
            {
                if (Asset.AssetClassPath!=UAnimSequence::StaticClass()->GetClassPathName()) continue;
                const FString Name=Asset.AssetName.ToString();
                const bool Attack=Name.Equals(TEXT("Attack"),ESearchCase::IgnoreCase)||Name.EndsWith(TEXT("_Attack"),ESearchCase::IgnoreCase);
                const bool Hurt=Name.Equals(TEXT("Hurt"),ESearchCase::IgnoreCase)||Name.EndsWith(TEXT("_Hurt"),ESearchCase::IgnoreCase);
                if ((!Attack||Clips.Attack) && (!Hurt||Clips.Hurt)) continue;
                auto* Clip=Cast<UAnimSequence>(Asset.GetAsset());
                if (!Clip || !Mesh->GetSkeleton() || Clip->GetSkeleton()!=Mesh->GetSkeleton()) continue;
                if (Attack) Clips.Attack=Clip;
                if (Hurt) Clips.Hurt=Clip;
            }
        }
    }
    return &CastClips.Add(Mesh,Clips);
}

void ADaedalusBattlePresentation::RefreshCastAnimations()
{
    CastClips.Empty();
    for (bool Foe:{false,true})
        for (int32 Index=0;Index<32;++Index)
            if (auto* Actor=Slot(Index,Foe))
                if (auto* Mesh=Actor->FindComponentByClass<USkeletalMeshComponent>())
                    ClipsFor(Mesh->GetSkeletalMeshAsset());
}

UAnimSequence* ADaedalusBattlePresentation::ResolveCastAnimation(AActor* Actor,bool bHurt)
{
    if (!IsValid(Actor)) return nullptr;
    auto* Mesh=Actor->FindComponentByClass<USkeletalMeshComponent>();
    if (!Mesh || !Mesh->GetSkeletalMeshAsset()) return nullptr;
    auto* Asset=Mesh->GetSkeletalMeshAsset();
    UAnimSequence* Animation=bHurt?HurtAnimation.Get():AttackAnimation.Get();
    if (!IsValid(Animation) || !Asset->GetSkeleton() || Asset->GetSkeleton()!=Animation->GetSkeleton())
    {
        const auto* Clips=ClipsFor(Asset);
        Animation=Clips?(bHurt?Clips->Hurt.Get():Clips->Attack.Get()):nullptr;
    }
    return IsValid(Animation)?Animation:nullptr;
}

void ADaedalusBattlePresentation::Play(AActor* Actor,bool bHurt)
{
    if (auto* Animation=ResolveCastAnimation(Actor,bHurt))
        Actor->FindComponentByClass<USkeletalMeshComponent>()->PlayAnimation(Animation,false);
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
        if (Cue.K==daedalus::stage::Kind::Swing) Play(Actor,false);
        if (Cue.K==daedalus::stage::Kind::Flinch) Play(Target,true);
        PresentCue(UTF8_TO_TCHAR(daedalus::stage::Name(Cue.K)),Actor,Target,Cue.Amount,
                   UTF8_TO_TCHAR(Cue.Text.c_str()),static_cast<float>(Cue.Dur),Cue.TargetIsFoe,Cue.Target);
    }
}
