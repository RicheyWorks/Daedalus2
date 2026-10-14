// SPDX-License-Identifier: MIT
#include "DaedalusShardsteadComponent.h"
#include "Engine/World.h"
#include "GameFramework/Actor.h"
UDaedalusShardsteadComponent::UDaedalusShardsteadComponent(){PrimaryComponentTick.bCanEverTick=false;}
bool UDaedalusShardsteadComponent::Host() const {
    const AActor* Owner=GetOwner();const UWorld* World=GetWorld();
    return IsValid(Owner)&&!Owner->IsActorBeingDestroyed()&&Owner->HasAuthority()&&World&&World->IsGameWorld();
}
std::string UDaedalusShardsteadComponent::Key(const FString& Value){
    if(Value.Len()>100)return {};
    FTCHARToUTF8 Bytes(*Value,Value.Len());return std::string(Bytes.Get(),Bytes.Length());
}
bool UDaedalusShardsteadComponent::InitializeFromHost(int64 RealmSeed){
    if(!Host())return false;if(Ready)return BoundSeed==RealmSeed;
    Rules=daedalus::shardstead::Economy(static_cast<std::uint64_t>(RealmSeed));BoundSeed=RealmSeed;Ready=true;return true;
}
bool UDaedalusShardsteadComponent::RegisterCrewFromHost(const FString& PlayerKey){return Ready&&Host()&&Rules.Join(Key(PlayerKey));}
bool UDaedalusShardsteadComponent::ClaimFromHost(const FString& PlayerKey,int32 Island,bool LandPermissionVerified){
    return Ready&&Host()&&Island>=0&&Island<10000&&Rules.Claim(Key(PlayerKey),static_cast<std::uint32_t>(Island),LandPermissionVerified);
}
bool UDaedalusShardsteadComponent::AssignFromHost(const FString& PlayerKey,int32 Island,const FString& WorkerId,EDaedalusIslandResource Task){
    return Ready&&Host()&&Island>=0&&Island<10000&&Rules.Assign(Key(PlayerKey),static_cast<std::uint32_t>(Island),Key(WorkerId),static_cast<daedalus::shardstead::Resource>(Task));
}
bool UDaedalusShardsteadComponent::MineFromHost(const FString& PlayerKey,int32 Island,EDaedalusIslandResource Resource,int32 Quantity,bool DepositProximityVerified){
    return Ready&&Host()&&Island>=0&&Island<10000&&Rules.Mine(Key(PlayerKey),static_cast<std::uint32_t>(Island),static_cast<daedalus::shardstead::Resource>(Resource),Quantity,DepositProximityVerified);
}
bool UDaedalusShardsteadComponent::AdvanceCycleFromHost(int64 Cycle){return Ready&&Host()&&Cycle>0&&Rules.Produce(static_cast<std::uint64_t>(Cycle));}
FDaedalusIslandStats UDaedalusShardsteadComponent::GetCrewStats(const FString& PlayerKey) const {
    FDaedalusIslandStats Out;if(!Ready||!Host())return Out;
    const auto* Crew=Rules.Stats(Key(PlayerKey));if(!Crew)return Out;
    Out.Available=true;Out.Friendship=Crew->Friendship;Out.Infamy=Crew->Infamy;
    for(int Value:Crew->Cargo)Out.Cargo.Add(Value);
    Out.Cycle=Rules.Cycle()>static_cast<std::uint64_t>(MAX_int64)?MAX_int64:static_cast<int64>(Rules.Cycle());
    auto Forecast=Rules;
    if(Rules.Cycle()!=UINT64_MAX&&Forecast.Produce(Rules.Cycle()+1)){
        const auto* Next=Forecast.Stats(Key(PlayerKey));
        for(unsigned K=0;K<daedalus::shardstead::Slot(daedalus::shardstead::Resource::Count);++K)Out.ProjectedNet.Add(Next->Cargo[K]-Crew->Cargo[K]);
    }
    return Out;
}
TArray<FDaedalusIslandClaimRow> UDaedalusShardsteadComponent::GetClaimRows(const FString& PlayerKey) const {
    TArray<FDaedalusIslandClaimRow> Out;if(!Ready||!Host())return Out;
    for(const auto& Row:Rules.Tab(Key(PlayerKey))){FDaedalusIslandClaimRow Item;
        Item.Island=static_cast<int32>(Row.Island);Item.Task=static_cast<EDaedalusIslandResource>(Row.Task);
        Item.Remaining=Row.Remaining;Item.Working=Row.Working;Item.WorkerId=UTF8_TO_TCHAR(Row.Worker.c_str());Out.Add(Item);}
    return Out;
}
