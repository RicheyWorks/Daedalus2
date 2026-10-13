// SPDX-License-Identifier: MIT
#include "../DaedalusLink/Source/DaedalusLink/Public/DaedalusDungeonCore.h"
#include <iostream>
#include <limits>
#include <cstdlib>
using namespace DaedalusDungeon;
int Checks=0;
void Check(bool Value,const char* What) {++Checks;if(!Value){std::cerr<<"FAIL "<<What<<"\n";std::exit(1);}}
Snapshot Fixture() {
    Snapshot S;S.Party.push_back({"Surveyor","Warrior",80,100,true});
    S.Choices={"Inspect the archive", "Take the \"marked\" passage"};
    S.History={"The wheel turns.\nA passage opens."};
    S.HasQuest=true;S.QuestTitle="The Broken Survey";S.SceneId="archive";S.Progress=.5;
    return S;
}
int main() {
    Session P;std::string Body;auto S=Fixture();
    Check(Valid(S),"valid fixture");Check(!P.BeginAction(0,Body),"action before status refused");
    auto A=P.BeginStatus();Check(A!=0,"poll starts");Check(!P.BeginStatus(),"single flight");
    Check(!P.Accept(A+1,1,"game_status",S),"stale response refused");Check(P.Busy(),"stale response leaves flight intact");
    Check(P.Accept(A,1,"game_status",S),"status accepted");Check(P.Ready(),"status enables choices");
    Check(!P.Accept(A,1,"game_status",S),"duplicate response refused");
    Check(!P.BeginAction(2,Body),"unoffered index refused");
    auto B=P.BeginAction(1,Body);Check(B>A,"action token advances");
    Check(Body=="{\"choiceLabel\":\"Take the \\\"marked\\\" passage\"}","JSON quote escaping");
    Check(!P.BeginAction(0,Body),"double click refused");
    Check(P.Accept(B,1,"game_status",S),"action snapshot accepted");
    auto C=P.BeginAction(0,Body);P.Fail(C);Check(P.ActionUncertain(),"timeout makes outcome uncertain");
    Check(P.State().QuestTitle==S.QuestTitle,"last valid state retained");
    Check(!P.BeginAction(0,Body),"uncertain action not retried");
    auto D=P.BeginStatus();Check(D>C,"read allowed after uncertainty");
    Check(P.Accept(D,1,"game_status",S),"read response accepted");Check(!P.Ready(),"read cannot clear uncertain mutation");
    P.NewSession();Check(!P.ActionUncertain() && !P.Ready(),"new identity clears old display");
    auto E=P.BeginStatus();Check(!P.Accept(C,1,"game_status",S),"old session callback fenced");
    Check(!P.Accept(E,2,"game_status",S),"version refused");Check(!P.Busy(),"bad version completes request");
    E=P.BeginStatus();Check(!P.Accept(E,1,"narrative_update",S),"narration cannot mutate status");
    auto Invalid=[&](auto Edit,const char* Label){auto X=S;Edit(X);Check(!Valid(X),Label);};
    Invalid([](auto& X){X.Party.clear();},"empty party");
    Invalid([](auto& X){X.Party.resize(17,X.Party[0]);},"party bound");
    Invalid([](auto& X){X.Party[0].Hp=101;},"health exceeds max");
    Invalid([](auto& X){X.Party[0].Hp=-1;},"negative health");
    Invalid([](auto& X){X.Party[0].Alive=false;},"inconsistent alive");
    Invalid([](auto& X){X.Choices.resize(65,"x");},"choice bound");
    Invalid([](auto& X){X.Choices.push_back("INSPECT THE ARCHIVE");},"case insensitive ambiguity");
    Invalid([](auto& X){X.Choices[0]="   ";},"blank choice");
    Invalid([](auto& X){X.Choices[0]=" x";},"server trim ambiguity");
    Invalid([](auto& X){X.Choices[0]=std::string("x\0y",3);},"embedded null");
    Invalid([](auto& X){X.Choices[0]=std::string(513,'x');},"label bound");
    Invalid([](auto& X){X.History.resize(31);},"history bound");
    Invalid([](auto& X){X.Progress=std::numeric_limits<double>::quiet_NaN();},"NaN progress");
    Invalid([](auto& X){X.Progress=1.1;},"progress is fraction");
    Invalid([](auto& X){X.Completed=X.Failed=true;},"contradictory quest state");
    Invalid([](auto& X){X.SceneDescription=std::string(8193,'x');},"scene text bound");
    Invalid([](auto& X){X.Chaos=-1;},"negative chaos");
    auto X=S;X.HasQuest=false;X.Choices.clear();Check(Valid(X),"no quest or choices valid");
    E=P.BeginStatus();Check(P.Accept(E,1,"game_status",S),"recover read failure");
    E=P.BeginAction(0,Body);X=S;X.Party.clear();Check(!P.Accept(E,1,"game_status",X),"malformed action response");
    Check(P.ActionUncertain() && P.State().Party.size()==1,"malformed action preserves display and blocks retry");
    Check(Quote("a\\b\nc") == "\"a\\\\b\\u000ac\"","JSON controls escaped");
    std::cout<<Checks<<" dungeon core checks passed\n";
}
