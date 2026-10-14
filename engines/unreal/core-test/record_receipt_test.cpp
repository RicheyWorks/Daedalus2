#include "DaedalusRecordReceiptCore.h"
#include <iostream>
using namespace daedalus::records;
int main(){
    const std::string Digest(64,'a');
    WriteExpectation E{"WORLD-ZERO","ledger",Digest,9007199254740992ULL};
    WriteReply R{"UPDATED",E.Realm,E.Key,"9007199254740993",Digest,Digest};
    std::uint64_t Out=7;
    if(!ConfirmWrite(true,200,E,R,Out)||Out!=9007199254740993ULL)return 1;
    R.Result="REPLAY";if(!ConfirmWrite(true,200,E,R,Out))return 2;
    if(ConfirmWrite(true,409,E,R,Out)||ConfirmWrite(false,200,E,R,Out))return 3;
    for(const auto& Text:{"09007199254740993","9007199254740992","9007199254740994","9223372036854775808","+1","1 ",""}){
        R.RevisionHeader=Text;Out=7;if(ConfirmWrite(true,200,E,R,Out)||Out!=7)return 4;
    }
    R.RevisionHeader="9007199254740993";R.BodySHA256=std::string(64,'b');
    if(ConfirmWrite(true,200,E,R,Out))return 5;
    R.BodySHA256=Digest;R.Key="another-ledger";if(ConfirmWrite(true,200,E,R,Out))return 6;
    std::cout<<"PASS exact 64-bit revision, replay, conflict/unknown, hash and identity receipt checks\n";
    return 0;
}
