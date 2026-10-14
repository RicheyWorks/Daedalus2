#include "DaedalusShardsteadSaveCore.h"
#include <iostream>
#include <fstream>
#include <iterator>
using namespace daedalus::shardstead;
int main(int Argc,char** Argv){
    Ledger L(730);Command C;C.Player="crew";
    if(L.Prepare("join",0,C)!=PrepareResult::Prepared||!L.ConfirmPersisted("join",1))return 1;
    C.Op=Operation::Claim;C.Island=17;C.Permission=true;
    if(L.Prepare("claim",1,C)!=PrepareResult::Prepared||!L.ConfirmPersisted("claim",2))return 2;
    C.Op=Operation::Assign;C.Worker="worker";C.Product=Resource::Iron;
    if(L.Prepare("assign",2,C)!=PrepareResult::Prepared||!L.ConfirmPersisted("assign",3))return 3;
    C.Op=Operation::Produce;C.Cycle=1;
    if(L.Prepare("produce",3,C)!=PrepareResult::Prepared||!L.ConfirmPersisted("produce",4))return 4;
    const auto Saved=L.ExportCommitted();std::vector<std::uint8_t> Bytes;
    if(!EncodeLedgerSave(Saved,Bytes))return 5;
    LedgerSnapshot Decoded;if(!DecodeLedgerSave(Bytes,Decoded)||Decoded.Revision!=4||!SameState(Saved.EconomyState,Decoded.EconomyState))return 6;
    Ledger Restored(730);if(!Restored.Restore(Decoded)||Restored.Prepare("produce",0,C)!=PrepareResult::Replay)return 7;
    for(std::size_t N=0;N<Bytes.size();++N){
        std::vector<std::uint8_t> Cut(Bytes.begin(),Bytes.begin()+static_cast<std::ptrdiff_t>(N));
        if(DecodeLedgerSave(Cut,Decoded)||Decoded.Revision!=4)return 8;
    }
    auto Extra=Bytes;Extra.push_back(0);if(DecodeLedgerSave(Extra,Decoded))return 9;
    auto Bad=Bytes;Bad[0]^=1;if(DecodeLedgerSave(Bad,Decoded))return 10;
    auto Forged=Saved;Forged.EconomyState.Crews.at("crew").Cargo[2]++;
    auto Before=Bytes;if(EncodeLedgerSave(Forged,Bytes)||Bytes!=Before)return 11;
    if(Argc==3){
        if(std::string(Argv[1])=="--write"){
            std::ofstream File(Argv[2],std::ios::binary);File.write(reinterpret_cast<const char*>(Bytes.data()),static_cast<std::streamsize>(Bytes.size()));
            if(!File)return 12;
        }else if(std::string(Argv[1])=="--read"){
            std::ifstream File(Argv[2],std::ios::binary);if(!File)return 13;
            std::vector<std::uint8_t> Returned((std::istreambuf_iterator<char>(File)),std::istreambuf_iterator<char>());
            if(Returned!=Bytes||!DecodeLedgerSave(Returned,Decoded)||!SameState(Saved.EconomyState,Decoded.EconomyState))return 14;
        }else return 15;
    }else if(Argc!=1)return 16;
    std::cout<<"PASS ledger roundtrip, idempotent restored receipt, every truncation, trailing bytes and forged balances\n";
    return 0;
}
