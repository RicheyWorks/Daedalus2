// SPDX-License-Identifier: MIT
#include "DaedalusShardsteadComponent.h"
#include "Engine/World.h"
#include "GameFramework/Actor.h"
THIRD_PARTY_INCLUDES_START
#include <openssl/sha.h>
THIRD_PARTY_INCLUDES_END
namespace {
std::string PayloadHash(const std::vector<std::uint8_t>& Bytes){
    unsigned char Digest[SHA256_DIGEST_LENGTH];
    if(Bytes.empty()||!SHA256(Bytes.data(),Bytes.size(),Digest))return {};
    static const char Hex[]="0123456789abcdef";std::string Result;Result.reserve(64);
    for(unsigned char Byte:Digest){Result.push_back(Hex[Byte>>4]);Result.push_back(Hex[Byte&15]);}
    return Result;
}
}
UDaedalusShardsteadComponent::UDaedalusShardsteadComponent(){PrimaryComponentTick.bCanEverTick=false;}
bool UDaedalusShardsteadComponent::StartCycleClockFromHost(float IntervalSeconds){
    if(!Ready||!Host()||!FMath::IsFinite(IntervalSeconds)||IntervalSeconds<=0.f)return false;
    FTimerManagerTimerParameters Parameters;
    Parameters.bLoop=true;Parameters.bMaxOncePerFrame=true;
    GetWorld()->GetTimerManager().SetTimer(CycleTimer,this,&UDaedalusShardsteadComponent::NotifyCycleDue,IntervalSeconds,Parameters);
    return true;
}
bool UDaedalusShardsteadComponent::StopCycleClockFromHost(){
    if(!Host())return false;
    ClearCycleClock();return true;
}
void UDaedalusShardsteadComponent::ClearCycleClock(){
    if(UWorld* World=GetWorld())World->GetTimerManager().ClearTimer(CycleTimer);
    CycleTimer.Invalidate();
}
void UDaedalusShardsteadComponent::EndPlay(const EEndPlayReason::Type EndPlayReason){
    ClearCycleClock();Super::EndPlay(EndPlayReason);
}
void UDaedalusShardsteadComponent::OnComponentDestroyed(bool bDestroyingHierarchy){
    ClearCycleClock();Super::OnComponentDestroyed(bDestroyingHierarchy);
}
void UDaedalusShardsteadComponent::NotifyCycleDue(){
    if(!Ready||!Host()){ClearCycleClock();return;}
    if((Durable&&Durable->HasPending())||!OnCycleDue.IsBound())return;
    const auto Cycle=ReadRules().Cycle();
    if(Cycle>=static_cast<std::uint64_t>(MAX_int64)){ClearCycleClock();return;}
    // Retry this same committed cycle on later intervals if the listener declines it.
    // Never catch up a stalled ledger by granting several cycles in one frame.
    OnCycleDue.Broadcast(static_cast<int64>(Cycle+1));
}
bool UDaedalusShardsteadComponent::Host() const {
    if(!IsInGameThread())return false;
    const AActor* Owner=GetOwner();const UWorld* World=GetWorld();
    return IsValid(Owner)&&!Owner->IsActorBeingDestroyed()&&Owner->HasAuthority()&&World&&World->IsGameWorld();
}
std::string UDaedalusShardsteadComponent::Key(const FString& Value){
    if(Value.Len()>100)return {};
    FTCHARToUTF8 Bytes(*Value,Value.Len());return std::string(Bytes.Get(),Bytes.Length());
}
bool UDaedalusShardsteadComponent::InitializeFromHost(int64 RealmSeed){
    if(!Host())return false;if(Ready)return !Durable&&BoundSeed==RealmSeed;
    Rules=daedalus::shardstead::Economy(static_cast<std::uint64_t>(RealmSeed));BoundSeed=RealmSeed;Ready=true;return true;
}
bool UDaedalusShardsteadComponent::RegisterCrewFromHost(const FString& PlayerKey){return Ready&&Host()&&!Durable&&Rules.Join(Key(PlayerKey));}
bool UDaedalusShardsteadComponent::ClaimFromHost(const FString& PlayerKey,int32 Island,bool LandPermissionVerified){
    return Ready&&Host()&&!Durable&&Island>=0&&Island<10000&&Rules.Claim(Key(PlayerKey),static_cast<std::uint32_t>(Island),LandPermissionVerified);
}
bool UDaedalusShardsteadComponent::AssignFromHost(const FString& PlayerKey,int32 Island,const FString& WorkerId,EDaedalusIslandResource Task){
    return Ready&&Host()&&!Durable&&Island>=0&&Island<10000&&Rules.Assign(Key(PlayerKey),static_cast<std::uint32_t>(Island),Key(WorkerId),static_cast<daedalus::shardstead::Resource>(Task));
}
bool UDaedalusShardsteadComponent::MineFromHost(const FString& PlayerKey,int32 Island,EDaedalusIslandResource Resource,int32 Quantity,bool DepositProximityVerified){
    return Ready&&Host()&&!Durable&&Island>=0&&Island<10000&&Rules.Mine(Key(PlayerKey),static_cast<std::uint32_t>(Island),static_cast<daedalus::shardstead::Resource>(Resource),Quantity,DepositProximityVerified);
}
bool UDaedalusShardsteadComponent::AdvanceCycleFromHost(int64 Cycle){return Ready&&Host()&&!Durable&&Cycle>0&&Rules.Produce(static_cast<std::uint64_t>(Cycle));}
const daedalus::shardstead::Economy& UDaedalusShardsteadComponent::ReadRules() const{return Durable?Durable->Read():Rules;}
bool UDaedalusShardsteadComponent::InitializeLedgerFromHost(int64 RealmSeed,const daedalus::shardstead::LedgerSnapshot* Saved){
    if(!Host()||Ready)return false;
    Durable.emplace(static_cast<std::uint64_t>(RealmSeed));
    if(Saved&&!Durable->Restore(*Saved)){Durable.reset();return false;}
    BoundSeed=RealmSeed;Ready=true;return true;
}
daedalus::shardstead::PrepareResult UDaedalusShardsteadComponent::PrepareFromHost(const FString& Request,uint64 ExpectedRevision,const daedalus::shardstead::Command& Command){
    if(!Ready||!Host()||!Durable)return daedalus::shardstead::PrepareResult::Rejected;
    return Durable->Prepare(Key(Request),ExpectedRevision,Command);
}
const daedalus::shardstead::LedgerSnapshot* UDaedalusShardsteadComponent::PendingFromHost() const{
    return Ready&&Host()&&Durable?Durable->PendingSnapshot():nullptr;
}
bool UDaedalusShardsteadComponent::ConfirmPersistedFromHost(const FString& Request,uint64 CommittedRevision){
    return Ready&&Host()&&Durable&&Durable->ConfirmPersisted(Key(Request),CommittedRevision);
}
bool UDaedalusShardsteadComponent::CancelConfirmedUncommittedFromHost(const FString& Request,uint64 ExpectedRevision){
    return Ready&&Host()&&Durable&&Durable->CancelAfterConfirmedNoCommit(Key(Request),ExpectedRevision);
}
bool UDaedalusShardsteadComponent::ExportCommittedFromHost(daedalus::shardstead::LedgerSnapshot& Out) const{
    if(!Ready||!Host()||!Durable)return false;
    Out=Durable->ExportCommitted();return true;
}
bool UDaedalusShardsteadComponent::LedgerRevisionFromHost(uint64& Out) const{
    if(!Ready||!Host()||!Durable)return false;
    Out=Durable->CurrentRevision();return true;
}
bool UDaedalusShardsteadComponent::InitializeLedgerBytesFromHost(int64 RealmSeed,const std::vector<std::uint8_t>& Bytes){
    if(!Host()||Ready)return false;
    daedalus::shardstead::LedgerSnapshot Saved;
    return daedalus::shardstead::DecodeLedgerSave(Bytes,Saved)&&InitializeLedgerFromHost(RealmSeed,&Saved);
}
bool UDaedalusShardsteadComponent::PendingBytesFromHost(std::vector<std::uint8_t>& Out) const{
    const auto* Saved=PendingFromHost();
    return Saved&&daedalus::shardstead::EncodeLedgerSave(*Saved,Out);
}
bool UDaedalusShardsteadComponent::CapturePendingRecordFromHost(const FString& Request,const std::string& Realm,
    const std::string& RecordKey,uint64 ExpectedStoreRevision,daedalus::records::WriteExpectation& OutExpected,
    std::vector<std::uint8_t>& OutBytes,uint64& OutDomainRevision) const{
    const auto* Saved=PendingFromHost();
    if(!Saved||!daedalus::records::Identity(Realm,RecordKey)||ExpectedStoreRevision>=static_cast<uint64>(MAX_int64))return false;
    const auto Entry=Saved->Applied.find(Key(Request));
    if(Entry==Saved->Applied.end()||Entry->second.Revision!=Saved->Revision)return false;
    std::vector<std::uint8_t> Bytes;if(!PendingBytesFromHost(Bytes))return false;
    auto Hash=PayloadHash(Bytes);if(!daedalus::records::Hash(Hash))return false;
    daedalus::records::WriteExpectation Expected{Realm,RecordKey,std::move(Hash),ExpectedStoreRevision};
    OutExpected=std::move(Expected);OutBytes=std::move(Bytes);OutDomainRevision=Saved->Revision;return true;
}
bool UDaedalusShardsteadComponent::ConfirmRecordReplyFromHost(const FString& Request,uint64 PreparedRevision,
    const daedalus::records::WriteExpectation& Expected,bool TransportOK,int32 HttpStatus,
    const daedalus::records::WriteReply& Reply,uint64& CommittedStoreRevision){
    const auto* Saved=PendingFromHost();
    if(!Saved||Saved->Revision!=PreparedRevision)return false;
    std::vector<std::uint8_t> Candidate;
    if(!PendingBytesFromHost(Candidate)||PayloadHash(Candidate)!=Expected.SHA256)return false;
    uint64 StoreRevision=0;
    if(!daedalus::records::ConfirmWrite(TransportOK,HttpStatus,Expected,Reply,StoreRevision))return false;
    if(!ConfirmPersistedFromHost(Request,PreparedRevision))return false;
    CommittedStoreRevision=StoreRevision;return true;
}
bool UDaedalusShardsteadComponent::ConfirmRecordReadBackFromHost(const FString& Request,uint64 PreparedRevision,
    const daedalus::records::WriteExpectation& Expected,bool TransportOK,int32 HttpStatus,
    const std::vector<std::uint8_t>& Returned,const std::string& RevisionHeader,
    const std::string& HashHeader,uint64& CommittedStoreRevision){
    const auto* Saved=PendingFromHost();if(!Saved||Saved->Revision!=PreparedRevision)return false;
    std::vector<std::uint8_t> Candidate;uint64 StoreRevision=0;
    if(!PendingBytesFromHost(Candidate)||PayloadHash(Candidate)!=Expected.SHA256||!daedalus::records::ConfirmReadBack(TransportOK,HttpStatus,Expected,Candidate,Returned,RevisionHeader,HashHeader,StoreRevision))return false;
    if(!ConfirmPersistedFromHost(Request,PreparedRevision))return false;
    CommittedStoreRevision=StoreRevision;return true;
}
FDaedalusIslandStats UDaedalusShardsteadComponent::GetCrewStats(const FString& PlayerKey) const {
    FDaedalusIslandStats Out;if(!Ready||!Host())return Out;
    const auto& View=ReadRules();
    const auto* Crew=View.Stats(Key(PlayerKey));if(!Crew)return Out;
    Out.Available=true;Out.Friendship=Crew->Friendship;Out.Infamy=Crew->Infamy;
    for(int Value:Crew->Cargo)Out.Cargo.Add(Value);
    Out.Cycle=View.Cycle()>static_cast<std::uint64_t>(MAX_int64)?MAX_int64:static_cast<int64>(View.Cycle());
    daedalus::shardstead::Stock Net{};
    if(View.ForecastNet(Key(PlayerKey),Net))for(int Quantity:Net)Out.ProjectedNet.Add(Quantity);
    return Out;
}
TArray<FDaedalusIslandClaimRow> UDaedalusShardsteadComponent::GetClaimRows(const FString& PlayerKey) const {
    TArray<FDaedalusIslandClaimRow> Out;if(!Ready||!Host())return Out;
    const auto& View=ReadRules();
    for(const auto& Row:View.Tab(Key(PlayerKey))){FDaedalusIslandClaimRow Item;
        Item.Island=static_cast<int32>(Row.Island);Item.Task=static_cast<EDaedalusIslandResource>(Row.Task);
        Item.Remaining=Row.Remaining;Item.Working=Row.Working;Item.WorkerId=UTF8_TO_TCHAR(Row.Worker.c_str());Out.Add(Item);}
    return Out;
}
