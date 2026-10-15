// SPDX-License-Identifier: MIT
#include "DaedalusSimulationWire.h"
#include <cstdio>
#include <fstream>
#include <iterator>
#include <limits>
#include <string>
#include <vector>
using namespace daedalus::simulation;
namespace {
int Passed=0, Total=0;
void Check(const char* Name,bool OK) {
    ++Total; Passed+=OK?1:0; std::printf("%s %s\n",OK?"PASS":"FAIL",Name);
}
// Genuine Jackson-serialized View records from unmodified PR29 sources at
// 2ca96368fff13a4722ed266741972dd13c138250, using a memory repository and controlled
// clock (seed 0, world-zero): initial, advance to tick 6, then supply 3 as alice.
// These fixtures exercise the real Java DTO shape; this native test starts no backend
// or Unreal runtime and makes no claim about a deployed endpoint or playable behavior.
#ifndef SIMULATION_FIXTURE_DIR
#define SIMULATION_FIXTURE_DIR "fixtures/simulation-v1"
#endif
std::string Fixture(const char* Name) {
    std::ifstream Input(std::string(SIMULATION_FIXTURE_DIR)+"/"+Name,std::ios::binary);
    std::string Json((std::istreambuf_iterator<char>(Input)),std::istreambuf_iterator<char>());
    while(!Json.empty() && (Json.back()==' ' || Json.back()=='\r' || Json.back()=='\n' || Json.back()=='\t')) Json.pop_back();
    return Json;
}
const std::string Initial=Fixture("initial.json");
const std::string RequestWater=Fixture("request-water.json");
const std::string Work=Fixture("work.json");
std::string Replace(std::string Json,const std::string& Before,const std::string& After) {
    const size_t At=Json.find(Before);
    if(At==std::string::npos) return "invalid test fixture replacement";
    Json.replace(At,Before.size(),After); return Json;
}
std::string Extend(const std::string& Value) {
    std::string Json=Initial; Json.pop_back(); Json+=",\"extension\":"+Value+"}"; return Json;
}
std::string EventJson(int64_t Sequence,int64_t Tick=0) {
    return "{\"sequence\":"+std::to_string(Sequence)+",\"tick\":"+std::to_string(Tick)+
           ",\"kind\":\"NPC_STATE_CHANGED\",\"detail\":\"REQUEST_WATER\"}";
}
std::string WithEvents(const std::string& Events,int64_t Cursor,int64_t Tick=0) {
    return Replace(Replace(Replace(Initial,"\"events\":[]","\"events\":"+Events),
            "\"eventSequence\":0","\"eventSequence\":"+std::to_string(Cursor)),
            "\"tick\":0","\"tick\":"+std::to_string(Tick));
}
bool Same(const View& A,const View& B) {
    return A.SchemaVersion==B.SchemaVersion && A.WorldId==B.WorldId && A.Tick==B.Tick &&
        A.Revision==B.Revision && A.StateHash==B.StateHash && A.CisternWater==B.CisternWater &&
        A.KeeperWater==B.KeeperWater && A.NpcId==B.NpcId && A.Task==B.Task && A.Reason==B.Reason &&
        A.QuestCompleted==B.QuestCompleted && A.RememberedActor==B.RememberedActor &&
        A.DrySpell==B.DrySpell && A.Active==B.Active && A.EventSequence==B.EventSequence;
}
bool Rejected(const std::string& Json) {
    View Out;
    if(!DecodeView(Initial,Out)) return false;
    Out.Tick=42; Out.Revision=99; Out.Reason="retained";
    const View Before=Out;
    return !DecodeView(Json,Out) && Same(Before,Out);
}
bool Accepted(const std::string& Json) { View V; return DecodeView(Json,V) && ValidateView(V); }
}
int main() {
    if(Initial.empty() || RequestWater.empty() || Work.empty()) {
        std::printf("FAIL Java fixture files missing from %s\n",SIMULATION_FIXTURE_DIR); return 1;
    }
    View V;
    Check("published initial View fixture",DecodeView(Initial,V) && V.SchemaVersion==1 &&
          V.WorldId=="world-zero" && V.NpcId=="npc-zero" && V.CisternWater==3 && V.KeeperWater==0 &&
          V.Task=="REST" && V.Reason=="Night schedule" && V.Active && !V.QuestCompleted && V.EventSequence==0);
    Check("Java REQUEST_WATER fixture",DecodeView(RequestWater,V) && V.Tick==6 && V.Revision==1 &&
          V.Task=="REQUEST_WATER" && V.CisternWater==4 && V.KeeperWater==0 && V.EventSequence==2);
    Check("Java supplied WORK and durable memory fixture",DecodeView(Work,V) && V.Tick==6 && V.Revision==2 &&
          V.Task=="WORK" && V.CisternWater==1 && V.KeeperWater==3 && V.EventSequence==5 &&
          V.QuestCompleted && V.RememberedActor=="alice");
    Check("surrounding JSON whitespace",Accepted(" \t\r\n"+Initial+"\n\t "));
    for(const char* Task:{"REST","WORK","REQUEST_WATER"})
        Check(Task,Accepted(Replace(Initial,"\"task\":\"REST\"","\"task\":\""+std::string(Task)+"\"")));
    Check("completed memory pair",Accepted(Replace(Replace(Initial,"\"questCompleted\":false",
          "\"questCompleted\":true"),"\"rememberedActor\":\"\"","\"rememberedActor\":\"alice\"")));
    Check("task refuses unsupported decision",Rejected(Replace(Initial,"\"REST\"","\"ATTACK\"")));
    Check("schema rejects old and future versions",Rejected(Replace(Initial,"\"schemaVersion\":1",
          "\"schemaVersion\":0")) && Rejected(Replace(Initial,"\"schemaVersion\":1","\"schemaVersion\":2")));
    Check("completion requires memory",Rejected(Replace(Initial,"\"questCompleted\":false","\"questCompleted\":true")));
    Check("memory requires completion",Rejected(Replace(Initial,"\"rememberedActor\":\"\"","\"rememberedActor\":\"alice\"")));

    const std::vector<std::string> Counters={"tick","revision","eventSequence"};
    for(const std::string& Name:Counters) {
        const std::string Field="\""+Name+"\":0";
        bool Bad=true;
        for(const char* Number:{"-1","-0","9223372036854775808","18446744073709551615","01","0.0","1e0","+1","\"1\"","null","true"})
            Bad=Bad && Rejected(Replace(Initial,Field,"\""+Name+"\":"+Number));
        Check((Name+" rejects invalid signed-counter encoding atomically").c_str(),Bad);
    }
    const int64_t Precise=9007199254740993LL, Max=std::numeric_limits<int64_t>::max();
    std::string PreciseJson=WithEvents("["+EventJson(Precise,Precise)+"]",Precise,Precise);
    PreciseJson=Replace(PreciseJson,"\"revision\":0","\"revision\":"+std::to_string(Precise));
    Check("all counters preserve integer precision above 2^53",DecodeView(PreciseJson,V) &&
          V.Tick==Precise && V.Revision==Precise && V.EventSequence==Precise);
    std::string MaxJson=WithEvents("["+EventJson(Max,Max)+"]",Max,Max);
    MaxJson=Replace(MaxJson,"\"revision\":0","\"revision\":"+std::to_string(Max));
    Check("signed int64 maximum accepted without overflow",DecodeView(MaxJson,V) && V.Tick==Max &&
          V.Revision==Max && V.EventSequence==Max);

    Check("communal resource upper bounds accepted",Accepted(Replace(Replace(Initial,"\"cisternWater\":3",
          "\"cisternWater\":12"),"\"keeperWater\":0","\"keeperWater\":6")));
    Check("communal resources reject out of range or fractions",Rejected(Replace(Initial,"\"cisternWater\":3",
          "\"cisternWater\":13")) && Rejected(Replace(Initial,"\"keeperWater\":0","\"keeperWater\":7")) &&
          Rejected(Replace(Initial,"\"cisternWater\":3","\"cisternWater\":-1")) &&
          Rejected(Replace(Initial,"\"keeperWater\":0","\"keeperWater\":1.5")));
    Check("world and NPC identity bounds accepted",Accepted(Replace(Replace(Initial,"world-zero",std::string(128,'w')),
          "npc-zero",std::string(128,'n'))));
    Check("world and NPC invalid identities rejected",Rejected(Replace(Initial,"world-zero",std::string(129,'w'))) &&
          Rejected(Replace(Initial,"npc-zero",std::string(129,'n'))) && Rejected(Replace(Initial,"world-zero","world/zero")) &&
          Rejected(Replace(Initial,"npc-zero","")));
    Check("remembered actor identity bounded",Rejected(Replace(Replace(Initial,"\"questCompleted\":false",
          "\"questCompleted\":true"),"\"rememberedActor\":\"\"","\"rememberedActor\":\""+std::string(129,'a')+"\"")));
    Check("opaque SHA-256 hash strict lowercase and length",Rejected(Replace(Initial,V.StateHash,"short")) &&
          Rejected(Replace(Initial,"5aabbf8731","5Aabbf8731")) && Rejected(Replace(Initial,"5aabbf8731","gaabbf8731")));
    Check("reason bound accepts 256 bytes and rejects 257",Accepted(Replace(Initial,"Night schedule",std::string(256,'r'))) &&
          Rejected(Replace(Initial,"Night schedule",std::string(257,'r'))));

    const std::string Escaped=R"(quote:\" slash:\/ backslash:\\ tab:\t newline:\n carriage:\r backspace:\b formfeed:\f \u0061\u00e9\uD83D\uDE80)";
    const std::string Expected="quote:\" slash:/ backslash:\\ tab:\t newline:\n carriage:\r backspace:\b formfeed:\f a\xc3\xa9\xf0\x9f\x9a\x80";
    Check("JSON escapes and Unicode surrogate pair decoded",DecodeView(Replace(Initial,"Night schedule",Escaped),V) && V.Reason==Expected);
    const std::string Unicode="caf\xc3\xa9 \xe6\xb0\xb4 \xf0\x9f\x9a\x80";
    Check("valid raw UTF-8 preserved",DecodeView(Replace(Initial,"Night schedule",Unicode),V) && V.Reason==Unicode);
    bool BadUnicode=true;
    for(const std::string& Text:std::vector<std::string>{R"(\q)",R"(\u12x4)",R"(\uD800)",R"(\uDC00)",
        R"(\uD800\u0041)",R"(\uD800x)",std::string("\xc0\xaf",2),std::string("\xed\xa0\x80",3),
        std::string("\xf4\x90\x80\x80",4),std::string("\xe2\x82",2),std::string("\x80",1),std::string("\n",1)})
        BadUnicode=BadUnicode && Rejected(Replace(Initial,"Night schedule",Text));
    Check("bad escapes, unpaired surrogates, controls and invalid UTF-8 rejected",BadUnicode);
    Check("invalid UTF-8 in unknown extension rejected",Rejected(Extend("\""+std::string("\xc0\xaf",2)+"\"")));
    Check("escaped recognized key decoded",Accepted(Replace(Initial,"\"tick\"",R"("ti\u0063k")")));

    Check("duplicate recognized field rejected",Rejected(Replace(Initial,"\"tick\":0","\"tick\":0,\"tick\":0")));
    Check("duplicate equivalent escaped key rejected",Rejected(Replace(Initial,"\"tick\":0",R"("tick":0,"ti\u0063k":0)")));
    Check("duplicate additive field rejected",Rejected(Extend("0,\"extension\":1")));
    Check("duplicate nested field rejected",Rejected(Extend(R"({"name":1,"name":2})")));
    Check("additive object, array and number fields accepted",Accepted(Extend(R"({"array":[null,true,false,"x",{"n":-1.25e+3}],"large":99999999999999999999999999999999999999999})")));
    bool MalformedExtensions=true;
    for(const char* Extension:{"NaN","Infinity","+1","01","-01","1.","1e","1e+",".","truefalse","nullx","[1,]","{\"a\":1,}"})
        MalformedExtensions=MalformedExtensions && Rejected(Extend(Extension));
    Check("unknown fields obey strict JSON grammar",MalformedExtensions);

    const std::vector<std::string> Fields={"\"schemaVersion\":1,","\"worldId\":\"world-zero\",","\"tick\":0,",
        "\"revision\":0,","\"stateHash\":\"5aabbf8731d0421c22c6a67c347e38de5a41184625a9052ee51b14eb6dce3f8f\",",
        "\"cisternWater\":3,","\"keeperWater\":0,","\"npcId\":\"npc-zero\",","\"task\":\"REST\",",
        "\"reason\":\"Night schedule\",","\"questCompleted\":false,","\"rememberedActor\":\"\",",
        "\"drySpell\":false,","\"active\":true,","\"eventSequence\":0,",",\"events\":[]"};
    bool Required=true;
    for(const std::string& Field:Fields) Required=Required && Rejected(Replace(Initial,Field,""));
    Check("every v1 View field is required",Required);
    bool BadTypes=true;
    for(const std::string& Field:Fields) {
        std::string Clean=Field;
        if(Clean.front()==',') Clean.erase(0,1);
        if(Clean.back()==',') Clean.pop_back();
        BadTypes=BadTypes && Rejected(Replace(Initial,Clean,Clean.substr(0,Clean.find(':')+1)+"null"));
    }
    Check("all recognized fields reject null",BadTypes);
    Check("booleans reject quoted and numeric values",Rejected(Replace(Initial,"\"active\":true","\"active\":1")) &&
          Rejected(Replace(Initial,"\"drySpell\":false","\"drySpell\":\"false\"")));
    Check("nonobject, trailing data and trailing comma rejected",Rejected("[]") && Rejected("null") && Rejected(Initial+"x") &&
          Rejected(Initial+Initial) && Rejected(Replace(Initial,"\"events\":[]}","\"events\":[],}")));
    bool Truncations=true;
    for(size_t I=0;I<Initial.size();++I) Truncations=Truncations && Rejected(Initial.substr(0,I));
    Check("every truncation rejected without replacing last view",Truncations);

    Check("ordered event suffix accepted",Accepted(WithEvents("["+EventJson(100,6)+","+EventJson(101,7)+"]",101,7)));
    Check("event sequence mismatch, empty cursor and tick ahead rejected",Rejected(WithEvents("[]",1)) &&
          Rejected(WithEvents("["+EventJson(1)+"]",2)) && Rejected(WithEvents("["+EventJson(1,1)+"]",1)));
    Check("event gaps and backwards ticks rejected",Rejected(WithEvents("["+EventJson(1)+","+EventJson(3)+"]",3)) &&
          Rejected(WithEvents("["+EventJson(1,2)+","+EventJson(2,1)+"]",2,2)));
    Check("event malformed counter, missing field and duplicate rejected",Rejected(WithEvents("["+EventJson(0)+"]",0)) &&
          Rejected(WithEvents("[{\"sequence\":1,\"tick\":0,\"kind\":\"NPC_STATE_CHANGED\"}]",1)) &&
          Rejected(WithEvents("["+Replace(EventJson(1),"\"tick\":0","\"tick\":0,\"tick\":0")+"]",1)));
    Check("event details bounded and types checked",Rejected(WithEvents("["+Replace(EventJson(1),"REQUEST_WATER",std::string(257,'d'))+"]",1)) &&
          Rejected(WithEvents("["+Replace(EventJson(1),"\"kind\":\"NPC_STATE_CHANGED\"","\"kind\":null")+"]",1)));
    Check("additive event details and future kind safely skipped",Accepted(WithEvents("["+Replace(EventJson(1),
          "\"kind\":\"NPC_STATE_CHANGED\"","\"kind\":\"FUTURE_DIAGNOSTIC\",\"extra\":{\"v\":[1,2]}")+"]",1)));
    std::string Events="[";
    for(int I=1;I<=64;++I) { if(I>1) Events+=","; Events+=EventJson(I); }
    Check("64 recent events accepted",Accepted(WithEvents(Events+"]",64)));
    Check("65 recent events refused",Rejected(WithEvents(Events+","+EventJson(65)+"]",65)));

    std::string Nested="null";
    for(int I=0;I<15;++I) Nested="["+Nested+"]";
    Check("bounded extension nesting accepted",Accepted(Extend(Nested)));
    Check("excess extension nesting rejected",Rejected(Extend("["+Nested+"]")));
    std::string Members="{";
    for(int I=0;I<128;++I) { if(I) Members+=","; Members+="\"k"+std::to_string(I)+"\":null"; }
    Check("bounded extension object members accepted",Accepted(Extend(Members+"}")));
    Check("excess extension object members rejected",Rejected(Extend(Members+",\"extra\":null}")));
    std::string Items="[";
    for(int I=0;I<1024;++I) { if(I) Items+=","; Items+="null"; }
    Check("bounded extension array accepted",Accepted(Extend(Items+"]")));
    Check("excess extension array rejected",Rejected(Extend(Items+",null]")));
    Check("extension strings bounded",Accepted(Extend("\""+std::string(4096,'s')+"\"")) &&
          Rejected(Extend("\""+std::string(4097,'s')+"\"")));
    const std::string AtLimit=Initial+std::string(64*1024-Initial.size(),' ');
    Check("64 KiB response accepted",Accepted(AtLimit));
    Check("response over 64 KiB rejected",Rejected(AtLimit+" "));

    DecodeView(Initial,V);
    V.Tick=-1; Check("native validator rejects negative counter",!ValidateView(V));
    DecodeView(Initial,V); V.Task="ATTACK"; Check("native validator rejects unsupported task",!ValidateView(V));
    DecodeView(Initial,V); V.Reason=std::string("\xed\xa0\x80",3);
    Check("native validator rejects malformed UTF-8",!ValidateView(V));
    std::printf("%d/%d\n",Passed,Total); return Passed==Total?0:1;
}
