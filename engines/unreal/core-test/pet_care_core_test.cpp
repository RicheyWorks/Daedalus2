// SPDX-License-Identifier: MIT
// Parity against fixtures produced by executing the pinned original Python source.
#include "DaedalusPetCareCore.h"
#include <fstream>
#include <iostream>
#include <sstream>
#include <stdexcept>
using namespace daedalus::petcare;

namespace {
int Total=0, Passed=0;
void Check(bool OK,const std::string& Name) {
    ++Total; if(OK) ++Passed; else std::cerr<<"FAIL "<<Name<<'\n';
}
bool SameObjects(const std::vector<Object>& A,const std::vector<Object>& B) {
    if(A.size()!=B.size()) return false;
    for(std::size_t I=0; I<A.size(); ++I)
        if(A[I].Id!=B[I].Id || !std::isfinite(A[I].X) || !std::isfinite(B[I].X) || std::abs(A[I].X-B[I].X)>1e-10) return false;
    return true;
}
bool Same(const State& A,const State& B) {
    return A.Hunger==B.Hunger && A.Mood==B.Mood && A.Energy==B.Energy && A.Hygiene==B.Hygiene &&
        A.Health==B.Health && A.Bond==B.Bond && A.Sick==B.Sick && A.Hidden==B.Hidden &&
        A.Anim==B.Anim && A.LastTick==B.LastTick && SameObjects(A.Mess,B.Mess) && SameObjects(A.Gifts,B.Gifts);
}
bool SameChase(const Chase& A,const Chase& B) { return A.Taken==B.Taken && A.Cmd==B.Cmd && A.Mark==B.Mark; }
State ReadState(std::istream& In) {
    State S; int Sick=0, Hidden=0, Anim=0, N=0;
    In>>S.Hunger>>S.Mood>>S.Energy>>S.Hygiene>>S.Health>>S.Bond>>Sick>>Hidden>>Anim>>S.LastTick;
    S.Sick=Sick!=0; S.Hidden=Hidden!=0; S.Anim=static_cast<Pose>(Anim);
    In>>N;
    if(N<0 || N>100) throw std::runtime_error("bad fixture object count");
    for(int I=0; I<N; ++I) { Object O; In>>O.Id>>O.X; S.Mess.push_back(O); }
    In>>N;
    if(N<0 || N>100) throw std::runtime_error("bad fixture object count");
    for(int I=0; I<N; ++I) { Object O; In>>O.Id>>O.X; S.Gifts.push_back(O); }
    return S;
}
Chase ReadChase(std::istream& In) {
    Chase C; int Taken=0; In>>Taken>>C.Cmd>>C.Mark;
    C.Taken=Taken!=0; if(C.Mark=="-") C.Mark.clear(); return C;
}
void CheckCare(const CareResult& Got,const State& Expected,int PoseId,int CommandId,const std::string& Name) {
    Check(Got.Failure==CareError::None && Same(Got.Value,Expected) &&
        static_cast<int>(Got.Anim)==PoseId && static_cast<int>(Got.Cmd)==CommandId,Name);
}
void RunRow(std::istringstream& In,const std::string& Kind,const std::string& Name) {
    if(Kind=="A" || Kind=="M") {
        std::int64_t Id=0; In>>Id; const State Before=ReadState(In), Expected=ReadState(In);
        int PoseId=0, CommandId=0; In>>PoseId>>CommandId;
        const auto Got=Kind=="A" ? Apply(Before,static_cast<Action>(Id)) : PickMess(Before,Id);
        CheckCare(Got,Expected,PoseId,CommandId,Name);
    } else if(Kind=="D") {
        double Dt=0; std::int64_t Now=0; int Rest=0, N=0; In>>Dt>>Now>>Rest>>N;
        if(N<0 || N>100) throw std::runtime_error("bad fixture RNG count");
        std::vector<double> Tape;
        for(int I=0; I<N; ++I) { double V=0; In>>V; Tape.push_back(V); }
        const State Before=ReadState(In), Expected=ReadState(In);
        std::size_t Used=0, ExpectedUsed=0; In>>ExpectedUsed;
        const auto Got=Decay(Before,Dt,Now,Rest!=0,[&](){return Tape.at(Used++);});
        Check(Got.Failure==CareError::None && Same(Got.Value,Expected) && Used==ExpectedUsed,Name);
    } else if(Kind=="S") {
        int N=0; double Dt=0; In>>N>>Dt; const State Before=ReadState(In), Expected=ReadState(In);
        if(N<0 || N>200000) throw std::runtime_error("bad fixture sequence count");
        State S=Before;
        for(int I=0; I<N; ++I) {
            const auto Got=Decay(S,Dt,1700,false,[](){return 0.9;});
            if(Got.Failure!=CareError::None) throw std::runtime_error("sequence rejected");
            S=Got.Value;
        }
        Check(Same(S,Expected),Name);
    } else if(Kind=="V") {
        const State S=ReadState(In); std::string Expected; In>>Expected;
        Check(Vitals(S)==Expected,Name);
    } else if(Kind=="C") {
        double N=0; int Expected=0, Got=0; In>>N>>Expected; Check(TryClamp(N,Got) && Got==Expected,Name);
    } else if(Kind=="R") {
        int Hour=0, Expected=0; In>>Hour>>Expected; Check(RuiRestingHour(Hour)==(Expected!=0),Name);
    } else if(Kind=="H") {
        const Chase Before=ReadChase(In); int OnCare=0, V=0, Act=0; In>>OnCare>>V>>Act;
        const Chase Expected=ReadChase(In); int ApplyN=0, PersistN=0, PlayN=0, EatN=0;
        In>>ApplyN>>PersistN>>PlayN>>EatN;
        const Hop Got=PlayHop(Before,static_cast<Via>(V),OnCare!=0);
        Check(static_cast<int>(Got.Act)==Act && SameChase(Got.Next,Expected) && Got.ApplyPlay==ApplyN &&
            Got.PersistPlay==PersistN && Got.IssuePlay==PlayN && Got.IssueEat==EatN,Name);
    } else if(Kind=="Q") {
        int OnCare=0,N=0; In>>OnCare>>N;
        if(N<0 || N>100) throw std::runtime_error("bad fixture chase count");
        std::vector<Via> Vias; std::vector<HopAct> Acts;
        for(int I=0; I<N; ++I) { int V=0; In>>V; Vias.push_back(static_cast<Via>(V)); }
        for(int I=0; I<N; ++I) { int A=0; In>>A; Acts.push_back(static_cast<HopAct>(A)); }
        const Chase Expected=ReadChase(In); int ApplyN=0,PersistN=0,PlayN=0,EatN=0;
        In>>ApplyN>>PersistN>>PlayN>>EatN;
        const auto Got=PlayChase(Vias,{false,"seek","lure"},OnCare!=0);
        Check(Got.Acts==Acts && SameChase(Got.Next,Expected) && Got.ApplyPlay==ApplyN &&
            Got.PersistPlay==PersistN && Got.IssuePlay==PlayN && Got.IssueEat==EatN,Name);
    } else throw std::runtime_error("unknown fixture case: "+Kind);
    if(!In) throw std::runtime_error("incomplete fixture case: "+Name);
    std::string Extra;
    if(In>>Extra) throw std::runtime_error("trailing fixture data: "+Name);
}
void Parity(const char* Path) {
    std::ifstream File(Path);
    if(!File) throw std::runtime_error(std::string("cannot open fixture: ")+Path);
    std::string Line;
    if(!std::getline(File,Line) || (Line!="PETCARE 1" && Line!="PETCARE 1\r"))
        throw std::runtime_error("unsupported fixture header");
    int Cases=0, LineNumber=1; bool End=false;
    while(std::getline(File,Line)) {
        ++LineNumber;
        if(Line.empty() || Line[0]=='#') continue;
        std::istringstream In(Line); std::string Kind; In>>Kind;
        if(Kind=="END") {
            int Expected=0; In>>Expected;
            if(!In || Expected!=Cases || Cases==0) throw std::runtime_error("fixture case count mismatch");
            End=true; break;
        }
        RunRow(In,Kind,"Python oracle line "+std::to_string(LineNumber)+" "+Kind); ++Cases;
    }
    if(!End) throw std::runtime_error("fixture missing END marker");
    std::cout<<"Python oracle cases: "<<Cases<<'\n';
}
void BoundaryGuards() {
    State S;
    int Value=37;
    Check(!TryClamp(std::numeric_limits<double>::quiet_NaN(),Value) && Value==37,
        "nonfinite clamp refuses without undefined conversion");
    Check(!SameObjects({{1,std::numeric_limits<double>::quiet_NaN()}},{{1,0}}),
        "object parity comparison rejects NaN");
    const auto Infinite=Decay(S,std::numeric_limits<double>::infinity(),1700,false,[](){return 0.9;});
    Check(Infinite.Failure==CareError::InvalidInput && Same(Infinite.Value,S),"nonfinite elapsed refuses atomically");
    const auto Bad=Decay(S,120000,1700,false,[](){return std::numeric_limits<double>::quiet_NaN();});
    Check(Bad.Failure==CareError::InvalidRandom && Same(Bad.Value,S),"nonfinite RNG refuses atomically");
    const auto BadRange=Decay(S,120000,1700,false,[](){return 1.0;});
    Check(BadRange.Failure==CareError::InvalidRandom && Same(BadRange.Value,S),"out-of-range RNG refuses atomically");
    const auto Late=Decay(S,120000,std::numeric_limits<std::int64_t>::max(),false,[](){return 0.9;});
    Check(Late.Failure==CareError::InvalidInput && Same(Late.Value,S),"object ID overflow refused");
    const auto BadAction=Apply(S,static_cast<Action>(99));
    Check(BadAction.Failure==CareError::InvalidInput && Same(BadAction.Value,S),"invalid action refuses atomically");
    S.Hunger=-1; const auto Invalid=Apply(S,Action::Feed);
    Check(Invalid.Failure==CareError::InvalidState && Same(Invalid.Value,S),"invalid vitals refuses atomically");
    State Before; Before.Hidden=true; Before.Sick=true;
    Check(std::string(Vitals(Before,true))=="Hidden","hidden vitals precedence survives blue/unwell");
}
}
int main(int Argc,char** Argv) {
    try { Parity(Argc>1 ? Argv[1] : "pet_care_parity.txt"); BoundaryGuards(); }
    catch(const std::exception& E) { std::cerr<<"FAIL "<<E.what()<<'\n'; return 1; }
    std::cout<<"Pet care: "<<Passed<<"/"<<Total<<" checks passed\n";
    return Passed==Total ? 0 : 1;
}
