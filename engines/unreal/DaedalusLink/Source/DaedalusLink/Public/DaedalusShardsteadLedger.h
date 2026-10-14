// SPDX-License-Identifier: MIT
#pragma once
#include "DaedalusShardsteadCore.h"
#include <optional>
namespace daedalus { namespace shardstead {
enum class Operation {Join,Claim,Assign,Mine,Produce,Trade,Raid};
struct Command {
    Operation Op=Operation::Join;
    std::string Player,Other,Worker;
    std::uint32_t Island=0;Resource Product=Resource::Stone;
    int Quantity=0;std::uint64_t Cycle=0;
    Stock OfferA{},OfferB{};
    bool Permission=false,Proximity=false,BothAccepted=false,CombatWon=false,PiracyZone=false;
    bool operator==(const Command& B) const {
        return Op==B.Op&&Player==B.Player&&Other==B.Other&&Worker==B.Worker&&Island==B.Island&&Product==B.Product
            &&Quantity==B.Quantity&&Cycle==B.Cycle&&OfferA==B.OfferA&&OfferB==B.OfferB&&Permission==B.Permission
            &&Proximity==B.Proximity&&BothAccepted==B.BothAccepted&&CombatWon==B.CombatWon&&PiracyZone==B.PiracyZone;
    }
};
struct Transaction {Command Input;std::uint64_t Revision=0;};
struct LedgerSnapshot {
    unsigned Version=1;
    std::uint64_t Revision=0;
    Snapshot EconomyState;
    std::map<std::string,Transaction> Applied;
};
enum class PrepareResult {Prepared,Replay,Busy,Conflict,Rejected,CapacityReached};
/** Prepare-copy-persist-confirm. No disk/network I/O is implied by this protocol.
 * Persist PendingSnapshot in one storage CAS transaction before ConfirmPersisted.
 * Failed/unknown storage outcomes stay pending; never replay against live inventory.
 */
class Ledger {
    Economy Current;
    std::uint64_t Revision=0;
    std::map<std::string,Transaction> Applied;
    struct Pending {std::string Request;LedgerSnapshot Saved;Economy Candidate;};
    std::optional<Pending> Prepared;
    static constexpr std::size_t MaxReceipts=4096;
    static bool Bounded(const Command& C) {
        if(static_cast<unsigned>(C.Op)>static_cast<unsigned>(Operation::Raid)||!Valid(C.Product)||C.Island>=10000||C.Quantity<0||C.Quantity>25)return false;
        for(const auto* S:{&C.Player,&C.Other,&C.Worker})if(!S->empty()&&!Identity(*S))return false;
        for(const auto& Offer:{C.OfferA,C.OfferB})for(int V:Offer)if(V<0||V>1000000)return false;
        return true;
    }
    static bool Execute(Economy& E,const Command& C) {
        switch(C.Op){
            case Operation::Join:return E.Join(C.Player);
            case Operation::Claim:return E.Claim(C.Player,C.Island,C.Permission);
            case Operation::Assign:return E.Assign(C.Player,C.Island,C.Worker,C.Product);
            case Operation::Mine:return E.Mine(C.Player,C.Island,C.Product,C.Quantity,C.Proximity);
            case Operation::Produce:return E.Produce(C.Cycle);
            case Operation::Trade:return E.Trade(C.Player,C.Other,C.OfferA,C.OfferB,C.BothAccepted);
            case Operation::Raid:return E.RaidCargo(C.Player,C.Other,C.Product,C.Quantity,C.CombatWon,C.PiracyZone);
        }
        return false;
    }
public:
    explicit Ledger(std::uint64_t Seed):Current(Seed){}
    const Economy& Read() const{return Current;}
    std::uint64_t CurrentRevision() const{return Revision;}
    bool HasPending() const{return Prepared.has_value();}
    PrepareResult Prepare(const std::string& Request,std::uint64_t ExpectedRevision,const Command& C) {
        if(!Identity(Request)||!Bounded(C))return PrepareResult::Rejected;
        auto Seen=Applied.find(Request);
        // Duplicate commit remains observable after newer transactions; payload must match exactly.
        if(Seen!=Applied.end())return Seen->second.Input==C?PrepareResult::Replay:PrepareResult::Conflict;
        if(Prepared){
            if(Prepared->Request==Request&&Prepared->Saved.Applied.find(Request)->second.Input==C&&ExpectedRevision==Revision)return PrepareResult::Prepared;
            return PrepareResult::Busy;
        }
        if(ExpectedRevision!=Revision||Revision==UINT64_MAX)return PrepareResult::Conflict;
        // Never evict receipt IDs and silently accept a replay. Host checkpoints/archives explicitly.
        if(Applied.size()>=MaxReceipts)return PrepareResult::CapacityReached;
        Economy Candidate=Current;if(!Execute(Candidate,C))return PrepareResult::Rejected;
        auto Next=Applied;Next.emplace(Request,Transaction{C,Revision+1});
        LedgerSnapshot Saved{1,Revision+1,Candidate.Export(),std::move(Next)};
        Prepared.emplace(Pending{Request,std::move(Saved),std::move(Candidate)});return PrepareResult::Prepared;
    }
    const LedgerSnapshot* PendingSnapshot() const{return Prepared?&Prepared->Saved:nullptr;}
    bool ConfirmPersisted(const std::string& Request,std::uint64_t CommittedRevision) {
        if(!Prepared){auto I=Applied.find(Request);return I!=Applied.end()&&I->second.Revision==CommittedRevision;}
        if(Prepared->Request!=Request||Prepared->Saved.Revision!=CommittedRevision)return false;
        Current=std::move(Prepared->Candidate);Revision=Prepared->Saved.Revision;Applied=std::move(Prepared->Saved.Applied);Prepared.reset();return true;
    }
    // Only after authoritative storage proves no commit occurred; timeout alone is insufficient.
    bool CancelAfterConfirmedNoCommit(const std::string& Request,std::uint64_t ExpectedRevision) {
        if(!Prepared||Prepared->Request!=Request||Revision!=ExpectedRevision)return false;
        Prepared.reset();return true;
    }
    LedgerSnapshot ExportCommitted() const{return {1,Revision,Current.Export(),Applied};}
    bool Restore(const LedgerSnapshot& S) {
        if(Prepared||Revision!=0||!Applied.empty()||!Current.Export().Crews.empty()||S.Version!=1||S.Applied.size()>MaxReceipts)return false;
        if(S.Revision!=S.Applied.size())return false;
        std::set<std::uint64_t> Revisions;
        std::vector<const Transaction*> Ordered(S.Applied.size(),nullptr);
        for(const auto& Pair:S.Applied){const auto& T=Pair.second;
            if(!Identity(Pair.first)||!Bounded(T.Input)||T.Revision==0||T.Revision>S.Revision||!Revisions.insert(T.Revision).second)return false;
            Ordered[static_cast<std::size_t>(T.Revision-1)]=&T;}
        Economy Candidate(Current.Export().Seed);if(!Candidate.Restore(S.EconomyState))return false;
        // Reconstruct the retained history: a plausible but mismatched balance is not a valid restore.
        Economy Replay(Current.Export().Seed);
        for(const auto* T:Ordered)if(!T||!Execute(Replay,T->Input))return false;
        if(!SameState(Replay.Export(),S.EconomyState))return false;
        // Revisions form a complete, unique 1..N history while this bounded ledger is unarchived.
        Current=std::move(Candidate);Revision=S.Revision;Applied=S.Applied;return true;
    }
};
}}
