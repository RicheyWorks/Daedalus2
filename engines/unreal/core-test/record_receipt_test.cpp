#include "DaedalusRecordReceiptCore.h"
#include <iostream>
using namespace daedalus::records;
int main(){
    const std::string Digest(64,'a');
    if(!Identity("WORLD-ZERO","Crew_1:ledger.v1")||!Identity(std::string(40,'A'),std::string(100,'a')))return 19;
    for(const auto& Realm:{"world-zero","1WORLD","WORLD/OTHER","", "WORLD ZERO"})if(Identity(Realm,"ledger"))return 20;
    for(const auto& Key:{"/ledger",".ledger","ledger?query","ledger/path","", "ledger\n"})if(Identity("WORLD-ZERO",Key))return 21;
    if(Identity(std::string(41,'A'),"ledger")||Identity("WORLD-ZERO",std::string(101,'a')))return 22;
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
    const std::string Json="{\"result\":\"UPDATED\",\"realm\":\"WORLD-ZERO\",\"key\":\"ledger\",\"revision\":9007199254740993,\"sha256\":\""+Digest+"\"}";
    if(!ParseWriteReply(Json,"9007199254740993",Digest,R)||!ConfirmWrite(true,200,E,R,Out))return 7;
    auto Duplicate=Json;Duplicate.insert(1,"\"key\":\"other\",");if(ParseWriteReply(Duplicate,"9007199254740993",Digest,R))return 8;
    if(ParseWriteReply(Json+"x","9007199254740993",Digest,R)||ParseWriteReply(Json,"9007199254740994",Digest,R))return 9;
    auto Fraction=Json;auto At=Fraction.find("9007199254740993");Fraction.replace(At,16,"9007199254740993.0");
    if(ParseWriteReply(Fraction,"9007199254740993",Digest,R))return 10;
    const std::vector<std::uint8_t> Candidate{1,2,3};
    if(!ConfirmReadBack(true,200,E,Candidate,Candidate,"9007199254740993",Digest,Out))return 11;
    Out=7;
    if(ConfirmReadBack(true,200,E,Candidate,{1,2,4},"9007199254740993",Digest,Out)||Out!=7)return 12;
    if(ConfirmReadBack(false,200,E,Candidate,Candidate,"9007199254740993",Digest,Out)||Out!=7)return 13;
    if(ConfirmReadBack(true,200,E,Candidate,Candidate,"9007199254740994",Digest,Out)||Out!=7)return 14;
    std::string HeaderRevision,HeaderHash;
    std::vector<std::string> Headers{"HTTP/1.1 100 Continue","","HTTP/1.1 200 OK","X-Record-Revision: 9007199254740993","X-Payload-SHA256: "+Digest,""};
    if(!ParseRecordHeaders(Headers,HeaderRevision,HeaderHash)||HeaderRevision!="9007199254740993"||HeaderHash!=Digest)return 15;
    Headers.push_back("x-record-revision: 9007199254740993");
    if(ParseRecordHeaders(Headers,HeaderRevision,HeaderHash))return 16;
    Headers.pop_back();Headers.push_back("x-payload-sha256: "+Digest);
    if(ParseRecordHeaders(Headers,HeaderRevision,HeaderHash))return 17;
    Headers={"HTTP/1.1 200 OK","X-Record-Revision: 1","X-Payload-SHA256: "+Digest,"HTTP/1.1 200 OK"};
    if(ParseRecordHeaders(Headers,HeaderRevision,HeaderHash))return 18;
    std::cout<<"PASS exact 64-bit revision, replay, conflict/unknown, hash and identity receipt checks\n";
    return 0;
}
