// SPDX-License-Identifier: MIT
#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
THIRD_PARTY_INCLUDES_START
#include "DaedalusShardsteadSaveCore.h"
#include "DaedalusRecordReceiptCore.h"
THIRD_PARTY_INCLUDES_END
#include "DaedalusShardsteadComponent.generated.h"

UENUM(BlueprintType)
enum class EDaedalusIslandResource : uint8 { Food, Energy, Iron, Copper, Crystal, Stone };

USTRUCT(BlueprintType)
struct DAEDALUSLINK_API FDaedalusIslandStats {
    GENERATED_BODY()
    UPROPERTY(BlueprintReadOnly,Category="Daedalus|Shardstead") bool Available=false;
    UPROPERTY(BlueprintReadOnly,Category="Daedalus|Shardstead") TArray<int32> Cargo;
    UPROPERTY(BlueprintReadOnly,Category="Daedalus|Shardstead") TArray<int32> ProjectedNet;
    UPROPERTY(BlueprintReadOnly,Category="Daedalus|Shardstead") int64 Cycle=0;
    UPROPERTY(BlueprintReadOnly,Category="Daedalus|Shardstead") int32 Friendship=0;
    UPROPERTY(BlueprintReadOnly,Category="Daedalus|Shardstead") int32 Infamy=0;
};
USTRUCT(BlueprintType)
struct DAEDALUSLINK_API FDaedalusIslandClaimRow {
    GENERATED_BODY()
    UPROPERTY(BlueprintReadOnly,Category="Daedalus|Shardstead") int32 Island=0;
    UPROPERTY(BlueprintReadOnly,Category="Daedalus|Shardstead") EDaedalusIslandResource Task=EDaedalusIslandResource::Stone;
    UPROPERTY(BlueprintReadOnly,Category="Daedalus|Shardstead") int32 Remaining=0;
    UPROPERTY(BlueprintReadOnly,Category="Daedalus|Shardstead") bool Working=false;
    UPROPERTY(BlueprintReadOnly,Category="Daedalus|Shardstead") FString WorkerId;
};
/** One host-side realm manager. No tick or client RPC; durable ledger must wrap mutations before public use. */
UCLASS(ClassGroup=(Daedalus),meta=(BlueprintSpawnableComponent))
class DAEDALUSLINK_API UDaedalusShardsteadComponent : public UActorComponent {
    GENERATED_BODY()
public:
    UDaedalusShardsteadComponent();
    UFUNCTION(BlueprintCallable,BlueprintAuthorityOnly,Category="Daedalus|Shardstead") bool InitializeFromHost(int64 RealmSeed);
    UFUNCTION(BlueprintCallable,BlueprintAuthorityOnly,Category="Daedalus|Shardstead") bool RegisterCrewFromHost(const FString& PlayerKey);
    UFUNCTION(BlueprintCallable,BlueprintAuthorityOnly,Category="Daedalus|Shardstead") bool ClaimFromHost(const FString& PlayerKey,int32 Island,bool LandPermissionVerified);
    UFUNCTION(BlueprintCallable,BlueprintAuthorityOnly,Category="Daedalus|Shardstead") bool AssignFromHost(const FString& PlayerKey,int32 Island,const FString& WorkerId,EDaedalusIslandResource Task);
    UFUNCTION(BlueprintCallable,BlueprintAuthorityOnly,Category="Daedalus|Shardstead") bool MineFromHost(const FString& PlayerKey,int32 Island,EDaedalusIslandResource Resource,int32 Quantity,bool DepositProximityVerified);
    UFUNCTION(BlueprintCallable,BlueprintAuthorityOnly,Category="Daedalus|Shardstead") bool AdvanceCycleFromHost(int64 Cycle);
    UFUNCTION(BlueprintPure,Category="Daedalus|Shardstead") FDaedalusIslandStats GetCrewStats(const FString& PlayerKey) const;
    UFUNCTION(BlueprintPure,Category="Daedalus|Shardstead") TArray<FDaedalusIslandClaimRow> GetClaimRows(const FString& PlayerKey) const;
    // Trusted native storage adapter only; these are deliberately not client RPCs.
    bool InitializeLedgerFromHost(int64 RealmSeed,const daedalus::shardstead::LedgerSnapshot* Saved=nullptr);
    daedalus::shardstead::PrepareResult PrepareFromHost(const FString& Request,uint64 ExpectedRevision,const daedalus::shardstead::Command& Command);
    const daedalus::shardstead::LedgerSnapshot* PendingFromHost() const;
    bool ConfirmPersistedFromHost(const FString& Request,uint64 CommittedRevision);
    bool CancelConfirmedUncommittedFromHost(const FString& Request,uint64 ExpectedRevision);
    bool ExportCommittedFromHost(daedalus::shardstead::LedgerSnapshot& Out) const;
    bool LedgerRevisionFromHost(uint64& Out) const;
    bool InitializeLedgerBytesFromHost(int64 RealmSeed,const std::vector<std::uint8_t>& Bytes);
    bool PendingBytesFromHost(std::vector<std::uint8_t>& Out) const;
    // Expected context must be captured from the actual outgoing encoded candidate.
    bool ConfirmRecordReplyFromHost(const FString& Request,uint64 PreparedRevision,
        const daedalus::records::WriteExpectation& Expected,bool TransportOK,int32 HttpStatus,
        const daedalus::records::WriteReply& Reply,uint64& CommittedStoreRevision);
    bool ConfirmRecordReadBackFromHost(const FString& Request,uint64 PreparedRevision,
        const daedalus::records::WriteExpectation& Expected,bool TransportOK,int32 HttpStatus,
        const std::vector<std::uint8_t>& Returned,const std::string& RevisionHeader,
        const std::string& HashHeader,uint64& CommittedStoreRevision);
private:
    bool Ready=false;
    int64 BoundSeed=0;
    daedalus::shardstead::Economy Rules{0};
    std::optional<daedalus::shardstead::Ledger> Durable;
    const daedalus::shardstead::Economy& ReadRules() const;
    bool Host() const;
    static std::string Key(const FString& Value);
};
