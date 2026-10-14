// SPDX-License-Identifier: MIT
#pragma once
#include "DaedalusShardsteadLedger.h"
#include "DaedalusRefugeSaveCore.h"
namespace daedalus { namespace shardstead {
// DRSH 1: little-endian bounded ledger payload, stored opaquely by RealmRecordStore.
// Reuse the existing record byte reader/writer; persistence/checksum stays in the store.
namespace ledger_save_detail {
using Writer=refuge::save_detail::Writer;
using Reader=refuge::save_detail::Reader;
inline void WriteStock(Writer& W,const Stock& S){for(int V:S)W.U32(static_cast<std::uint32_t>(V));}
inline int Amount(Reader& R,unsigned Limit=1000000){
    auto V=R.U32();if(V>Limit){R.Good=false;return 0;}return static_cast<int>(V);
}
inline Stock ReadStock(Reader& R){Stock S{};for(auto& V:S)V=Amount(R);return S;}
inline void WriteCommand(Writer& W,const Command& C){
    W.Byte(static_cast<std::uint8_t>(C.Op));W.Text(C.Player);W.Text(C.Other);W.Text(C.Worker);
    W.U32(C.Island);W.Byte(static_cast<std::uint8_t>(C.Product));W.U32(static_cast<std::uint32_t>(C.Quantity));W.U64(C.Cycle);
    WriteStock(W,C.OfferA);WriteStock(W,C.OfferB);
    for(bool V:{C.Permission,C.Proximity,C.BothAccepted,C.CombatWon,C.PiracyZone})W.Byte(V?1:0);
}
inline Command ReadCommand(Reader& R){
    Command C;C.Op=static_cast<Operation>(R.Byte());C.Player=R.Text();C.Other=R.Text();C.Worker=R.Text();
    C.Island=R.U32();C.Product=static_cast<Resource>(R.Byte());C.Quantity=Amount(R,25);C.Cycle=R.U64();
    C.OfferA=ReadStock(R);C.OfferB=ReadStock(R);
    C.Permission=R.Bool();C.Proximity=R.Bool();C.BothAccepted=R.Bool();C.CombatWon=R.Bool();C.PiracyZone=R.Bool();return C;
}
}
inline bool EncodeLedgerSave(const LedgerSnapshot& S,std::vector<std::uint8_t>& Out){
    Ledger Check(S.EconomyState.Seed);if(!Check.Restore(S))return false;
    using namespace ledger_save_detail;
    Writer W;W.U32(0x48535244);W.U32(1);W.U32(S.Version);W.U64(S.Revision);
    const auto& E=S.EconomyState;W.U32(E.Version);W.U64(E.Seed);W.U64(E.Cycle);
    W.U32(static_cast<std::uint32_t>(E.Crews.size()));
    for(const auto& Pair:E.Crews){W.Text(Pair.first);WriteStock(W,Pair.second.Cargo);W.U32(Pair.second.Friendship);W.U32(Pair.second.Infamy);}
    W.U32(static_cast<std::uint32_t>(E.Plots.size()));
    for(const auto& Pair:E.Plots){const auto& P=Pair.second;W.U32(Pair.first);W.Text(P.Owner);W.Text(P.Worker);W.Byte(static_cast<std::uint8_t>(P.Task));WriteStock(W,P.Remaining);W.Byte(P.Assigned?1:0);}
    W.U32(static_cast<std::uint32_t>(S.Applied.size()));
    for(const auto& Pair:S.Applied){W.Text(Pair.first);W.U64(Pair.second.Revision);WriteCommand(W,Pair.second.Input);}
    if(W.Bytes.size()>8*1024*1024)return false;
    Out=std::move(W.Bytes);return true;
}
inline bool DecodeLedgerSave(const std::vector<std::uint8_t>& Bytes,LedgerSnapshot& Out){
    if(Bytes.size()>8*1024*1024)return false;
    using namespace ledger_save_detail;
    Reader R{Bytes};if(R.U32()!=0x48535244||R.U32()!=1)return false;
    LedgerSnapshot S;S.Version=R.U32();S.Revision=R.U64();auto& E=S.EconomyState;
    E.Version=R.U32();E.Seed=R.U64();E.Cycle=R.U64();
    auto Count=R.U32();if(Count>256)return false;
    for(unsigned I=0;I<Count;++I){auto Id=R.Text();Crew C;C.Cargo=ReadStock(R);C.Friendship=Amount(R,100);C.Infamy=Amount(R,100);if(!E.Crews.emplace(Id,C).second)return false;}
    Count=R.U32();if(Count>10000)return false;
    for(unsigned I=0;I<Count;++I){auto Id=R.U32();Plot P;P.Owner=R.Text();P.Worker=R.Text();P.Task=static_cast<Resource>(R.Byte());P.Remaining=ReadStock(R);P.Assigned=R.Bool();if(!E.Plots.emplace(Id,std::move(P)).second)return false;}
    Count=R.U32();if(Count>4096)return false;
    for(unsigned I=0;I<Count;++I){auto Id=R.Text();Transaction T;T.Revision=R.U64();T.Input=ReadCommand(R);if(!S.Applied.emplace(Id,std::move(T)).second)return false;}
    if(!R.Good||R.At!=Bytes.size())return false;
    Ledger Check(E.Seed);if(!Check.Restore(S))return false;
    Out=std::move(S);return true;
}
}}
