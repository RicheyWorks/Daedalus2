// SPDX-License-Identifier: MIT
#pragma once
#include "DaedalusRefugeRunCore.h"
#include "DaedalusRefugeCore.h"
#include <utility>
namespace daedalus { namespace refuge {
struct SaveRecord {RunSnapshot Run;ShelterSnapshot Household;};
// Versioned, bounded little-endian payload for RealmRecordStore. No native pointers or floating amounts.
namespace save_detail {
struct Writer {
    std::vector<std::uint8_t> Bytes;
    void Byte(std::uint8_t V){Bytes.push_back(V);}
    void U32(std::uint32_t V){for(unsigned I=0;I<4;++I)Byte(static_cast<std::uint8_t>(V>>(8*I)));}
    void U64(std::uint64_t V){for(unsigned I=0;I<8;++I)Byte(static_cast<std::uint8_t>(V>>(8*I)));}
    void Text(const std::string& S){U32(static_cast<std::uint32_t>(S.size()));Bytes.insert(Bytes.end(),S.begin(),S.end());}
};
struct Reader {
    const std::vector<std::uint8_t>& Bytes;std::size_t At=0;bool Good=true;
    std::uint8_t Byte(){if(At>=Bytes.size()){Good=false;return 0;}return Bytes[At++];}
    std::uint32_t U32(){std::uint32_t V=0;for(unsigned I=0;I<4;++I)V|=static_cast<std::uint32_t>(Byte())<<(8*I);return V;}
    std::uint64_t U64(){std::uint64_t V=0;for(unsigned I=0;I<8;++I)V|=static_cast<std::uint64_t>(Byte())<<(8*I);return V;}
    bool Bool(){auto V=Byte();if(V>1)Good=false;return V==1;}
    int Amount(){auto V=U32();if(V>100000)Good=false;return V<=100000?static_cast<int>(V):0;}
    std::string Text(){auto N=U32();if(N>100||N>Bytes.size()-At){Good=false;return {};}
        std::string S(Bytes.begin()+static_cast<std::ptrdiff_t>(At),Bytes.begin()+static_cast<std::ptrdiff_t>(At+N));At+=N;return S;}
};
}
inline bool ValidateSave(const SaveRecord& S){
    Run Check(S.Run.RunId,S.Run.Player,S.Run.Seed,S.Run.Policy);
    Shelter Home;
    if(!Check.Restore(S.Run)||!Home.Restore(S.Household)||S.Household.Day>S.Run.Day)return false;
    if(S.Run.State==RunState::Lost&&!Home.Finished())return false;
    return true;
}
inline bool EncodeSave(const SaveRecord& S,std::vector<std::uint8_t>& Out){
    if(!ValidateSave(S))return false;
    save_detail::Writer W;W.U32(0x48465244);W.U32(1); // DRFH, format 1
    W.U32(S.Run.Version);W.Text(S.Run.RunId);W.Text(S.Run.Player);W.U64(S.Run.Seed);W.U32(S.Run.Day);
    W.U32(S.Run.Policy.DailyChanceBasisPoints);W.Byte(S.Run.Policy.AutomaticRescue?1:0);W.Byte(S.Run.RankedLongest?1:0);
    W.Byte(static_cast<std::uint8_t>(S.Run.State));W.Text(S.Run.RescueVoyage);W.U32(S.Run.LivesSaved);
    const auto& H=S.Household;W.U32(H.Version);W.U32(H.Day);W.U32(static_cast<std::uint32_t>(H.Integrity));
    for(int V:{H.Stock.Food,H.Stock.Water,H.Stock.Medicine,H.Stock.RepairParts})W.U32(static_cast<std::uint32_t>(V));
    for(const auto& R:H.Residents){for(int V:{R.Health,R.Hunger,R.Thirst,R.Morale})W.U32(static_cast<std::uint32_t>(V));W.Byte(R.Alive?1:0);}
    Out=std::move(W.Bytes);return true;
}
inline bool DecodeSave(const std::vector<std::uint8_t>& Bytes,SaveRecord& Out){
    if(Bytes.size()>4096)return false;
    save_detail::Reader R{Bytes};if(R.U32()!=0x48465244||R.U32()!=1)return false;
    SaveRecord S;S.Run.Version=R.U32();S.Run.RunId=R.Text();S.Run.Player=R.Text();S.Run.Seed=R.U64();S.Run.Day=R.U32();
    S.Run.Policy.DailyChanceBasisPoints=R.U32();S.Run.Policy.AutomaticRescue=R.Bool();S.Run.RankedLongest=R.Bool();
    S.Run.State=static_cast<RunState>(R.Byte());S.Run.RescueVoyage=R.Text();S.Run.LivesSaved=R.U32();
    auto& H=S.Household;H.Version=R.U32();H.Day=R.U32();H.Integrity=R.Amount();
    H.Stock.Food=R.Amount();H.Stock.Water=R.Amount();H.Stock.Medicine=R.Amount();H.Stock.RepairParts=R.Amount();
    for(auto& Member:H.Residents){Member.Health=R.Amount();Member.Hunger=R.Amount();Member.Thirst=R.Amount();Member.Morale=R.Amount();Member.Alive=R.Bool();}
    if(!R.Good||R.At!=Bytes.size()||!ValidateSave(S))return false;
    Out=std::move(S);return true;
}
}}
