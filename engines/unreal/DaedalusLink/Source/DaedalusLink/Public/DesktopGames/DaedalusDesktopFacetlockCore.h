// SPDX-License-Identifier: MIT
#pragma once
#include "DaedalusDesktopGameTypes.h"
#include "DaedalusFacetlockCore.h"
#include <cerrno>
#include <cstdlib>
#include <cstring>
#include <sstream>
#include <string>
#include <vector>

namespace daedalus { namespace desktop {
// Facetlock Lattice (Prismheart cabinet): the ADaedalusDesktopArcade host for DaedalusFacetlockCore.h, a port of
// tools/minigames/facetlock.py (prism-shard-dev, the rules authority). CPython-compatible seeding, so
// StartGame("facetlock", seed) is the same scramble as facetlock.start(seed, difficulty). A cursor sits on one cell;
// pad A / J slides that row right, pad B / K slides it left, pad X / Space slides that column down, pad Y / Shift
// slides it up (Fire, Jump, Action, Dash edges). Arrows or stick move the cursor. R or pad Start restarts a finished
// lock. Option 0 Lattice; option 1 Guide practice marks the row or column the solution would slide next.
class FacetlockGame final : public Game {
    facetlock::Game Core;
    std::uint32_t SessionSeed=730;
    int Option=0;
    int CurR=0, CurC=0;
    int LastGained=0;
    bool WasL=false, WasR=false, WasU=false, WasD=false;

    void Deal() { Core.Start(SessionSeed,CabinetDifficulty()); CurR=CurC=0; LastGained=0; WasL=WasR=WasU=WasD=false; }
    static bool GoL(const Input& I) { return I.Left||I.PadLeft||I.AxisX<-0.4; }
    static bool GoR(const Input& I) { return I.Right||I.PadRight||I.AxisX>0.4; }
    static bool GoU(const Input& I) { return I.Up||I.PadUp||I.AxisY<-0.4; }
    static bool GoD(const Input& I) { return I.Down||I.PadDown||I.AxisY>0.4; }
    void MoveCursor(int DR,int DC) { const int N=Core.Size(); if(N<=0) return; CurR=((CurR+DR)%N+N)%N; CurC=((CurC+DC)%N+N)%N; }
    static bool ParseLL(const std::string& S,long long& Out) {
        if(S.empty()) return false;
        char* End=nullptr;
        errno=0;
        const long long V=std::strtoll(S.c_str(),&End,10);
        if(End==S.c_str()||*End!='\0'||errno==ERANGE) return false;
        Out=V;
        return true;
    }
    static Color MarkColor(char M) {
        switch(M) { case 'E': return {255,132,64,255}; case 'T': return {72,160,255,255}; case 'V': return {96,214,112,255}; case 'G': return {228,228,160,255}; case 'U': return {170,110,230,255}; default: return {60,56,70,255}; }
    }
public:
    const facetlock::Game& CoreState() const { return Core; }
    int CursorRow() const { return CurR; }
    int CursorCol() const { return CurC; }
    int LastGain() const { return LastGained; }

    void Reset(std::uint32_t Seed) override { SessionSeed=Seed; Deal(); }
    bool SetCabinetDifficulty(const std::string& Name) override { if(!Game::SetCabinetDifficulty(Name)) return false; Deal(); return true; }
    bool SetOption(int Value,std::uint32_t Seed) override { if(Value<0 || Value>1) return false; Option=Value; SessionSeed=Seed; Deal(); return true; }
    int GetOption() const override { return Option; }
    /** Slide the cursor's row (Row=true) or column by Dir. False when nothing happened. */
    bool Slide(bool Row,int Dir) {
        if(Core.Over) return false;
        int Gained=0;
        if(Core.Apply({Row,Row?CurR:CurC,Dir},Gained)!=facetlock::Game::Act::Ok) return false;
        LastGained=Gained; return true;
    }
    bool SourceKeyDown(int Key) override {
        // Up,Down,Left,Right,B,A,Enter,Space,R,other
        if(Core.Over) { if(Key==5||Key==6||Key==7||Key==8) { Deal(); return true; } return false; }
        if(Key==0) MoveCursor(-1,0); else if(Key==1) MoveCursor(1,0); else if(Key==2) MoveCursor(0,-1); else if(Key==3) MoveCursor(0,1);
        else if(Key==5||Key==6) Slide(true,1); else if(Key==4) Slide(true,-1); else if(Key==7) Slide(false,1);
        return false;
    }
    bool SourceControllerButton(int Button) override {
        if(Button==0 && !Core.Over) { Slide(true,1); return true; }
        if(Button==1 && Core.Over) { Deal(); return true; }
        return false;
    }
    void Step(const Input& I) override {
        if(Core.Over) { if(I.FirePressed||I.JumpPressed||I.ActionPressed||I.DashPressed) Deal(); return; }
        const bool L=GoL(I),R=GoR(I),U=GoU(I),D=GoD(I);
        if(L && !WasL) MoveCursor(0,-1); else if(R && !WasR) MoveCursor(0,1);
        else if(U && !WasU) MoveCursor(-1,0); else if(D && !WasD) MoveCursor(1,0);
        WasL=L; WasR=R; WasU=U; WasD=D;
        if(I.FirePressed) Slide(true,1); else if(I.JumpPressed) Slide(true,-1); else if(I.ActionPressed) Slide(false,1); else if(I.DashPressed) Slide(false,-1);
    }
    std::string SaveState() const override {
        std::ostringstream O;
        O<<"facetlock v1 d="<<CabinetDifficulty()<<" seed="<<SessionSeed<<" moves="<<Core.Moves<<" score="<<Core.Score<<" over="<<(Core.Over?1:0)<<" won="<<(Core.Won?1:0)
         <<" cur="<<CurR<<","<<CurC<<" board="<<Core.BoardString()<<" solution="<<Core.SolutionString();
        return O.str();
    }
    bool RestoreState(const std::string& Text,std::uint32_t) override {
        if(Text.rfind("facetlock v1 ",0)!=0) return false;
        auto Val=[&](const std::string& Key)->std::string { const std::string N=" "+Key+"="; const size_t P=Text.find(N); if(P==std::string::npos) return ""; const size_t S=P+N.size(), E=Text.find(' ',S); return Text.substr(S,E==std::string::npos?std::string::npos:E-S); };
        auto Split=[](const std::string& S,char Sep) { std::vector<std::string> Out; std::string Tok; for(char Ch:S) { if(Ch==Sep) { Out.push_back(Tok); Tok.clear(); } else Tok.push_back(Ch); } if(!S.empty()) Out.push_back(Tok); return Out; };
        long long Seed=0,Moves=0,Score=0,Over=0,Won=0,CR=0,CC=0;
        if(!ParseLL(Val("seed"),Seed)||!ParseLL(Val("moves"),Moves)||!ParseLL(Val("score"),Score)||!ParseLL(Val("over"),Over)||!ParseLL(Val("won"),Won)) return false;
        const std::string Cur=Val("cur"); const size_t Comma=Cur.find(','); if(Comma==std::string::npos||!ParseLL(Cur.substr(0,Comma),CR)||!ParseLL(Cur.substr(Comma+1),CC)) return false;
        const std::string Diff=Val("d"); const facetlock::Difficulty* D=facetlock::FindDifficulty(Diff);
        if(!D||Seed<0||Seed>0xffffffffLL||Moves<0||Moves>D->Scramble+D->Spare||Score<0||Score>1000||(Over!=0&&Over!=1)||(Won!=0&&Won!=1)||CR<0||CR>=D->Size||CC<0||CC>=D->Size) return false;
        facetlock::Game Fresh; if(!Fresh.Start(static_cast<std::uint32_t>(Seed),Diff)) return false;
        const std::vector<std::string> Rows=Split(Val("board"),'|'); if(static_cast<int>(Rows.size())!=D->Size) return false;
        int Counts[5]={0,0,0,0,0};
        for(const std::string& Row:Rows) { if(static_cast<int>(Row.size())!=D->Size) return false; for(char Ch:Row) { const char* P=std::strchr(facetlock::Marks(),Ch); if(!P||P-facetlock::Marks()>=D->Size) return false; ++Counts[P-facetlock::Marks()]; } }
        for(int M=0;M<D->Size;++M) if(Counts[M]!=D->Size) return false;   // every hue keeps exactly one row's worth of facets
        std::vector<facetlock::Move> Sol; const std::string SolS=Val("solution");
        if(!SolS.empty()) for(const std::string& Part:Split(SolS,';')) {
            const std::vector<std::string> F=Split(Part,','); long long I=0,Dd=0;
            if(F.size()!=3||(F[0]!="r"&&F[0]!="c")||!ParseLL(F[1],I)||!ParseLL(F[2],Dd)||I<0||I>=D->Size||(Dd!=1&&Dd!=-1)) return false;
            Sol.push_back({F[0]=="r",static_cast<int>(I),static_cast<int>(Dd)});
        }
        if(Sol.size()>64) return false;
        Game::SetCabinetDifficulty(Diff);
        SessionSeed=static_cast<std::uint32_t>(Seed); Core=Fresh; Core.Board=Rows; Core.Solution=Sol; Core.Moves=static_cast<int>(Moves); Core.Score=static_cast<int>(Score); Core.Over=Over!=0; Core.Won=Won!=0;
        CurR=static_cast<int>(CR); CurC=static_cast<int>(CC); LastGained=0; WasL=WasR=WasU=WasD=false;
        return true;
    }
    std::uint32_t SeedAfterRestore(std::uint32_t) const override { return SessionSeed; }
    std::string HintLine() const {
        if(Core.Over) return Core.Won?"HINT The vault lock opened. Pad A or R scrambles a new lattice.":"HINT The lock sealed. Pad A or R scrambles a new lattice.";
        if(Option==1) return "HINT Practice: the blue bar marks the next slide of the solution.";
        return "HINT Rows and columns wrap. Make every row one hue.";
    }
    std::string ActionCue() const { return Core.Over?"CUE Retry":"CUE Slide"; }
    std::string HowToLine() const override { return "HOW Slide lattice rows and columns, which wrap, until each row shows a single hue inside the move budget."; }
    std::string KeyHint() const override { return "KEYS Arrows move the cursor; A/B slide the row, X/Y the column."; }
    std::string ContrastMark() const override { return Core.Over?"MARK WAIT":"MARK ACT"; }
    void Render(Frame& F) const override {
        F.Clear(800,600,{16,10,24,255});
        F.AddText(28,20,std::string(Option==1?"FACETLOCK GUIDE  [":"FACETLOCK LATTICE  [")+CabinetDifficulty()+"]",{255,236,220,255},26);
        F.AddText(28,56,"SCORE: "+std::to_string(Core.Score)+"   MOVES: "+std::to_string(Core.Moves),White,18);
        const int N=Core.Size(); if(N<=0) return;
        const double Cell=340.0/N, Left=200, Top=120;
        const facetlock::Move Guide=(Option==1 && !Core.Over)?Core.DemoAction():facetlock::Move{true,-1,0};
        F.AddRect(Left-10,Top-10,N*Cell+20,N*Cell+20,{34,24,46,255});
        for(int R=0;R<N;++R) for(int C=0;C<N;++C) {
            const double X=Left+C*Cell, Y=Top+R*Cell; const char M=Core.Board[static_cast<size_t>(R)][static_cast<size_t>(C)];
            F.AddRect(X+3,Y+3,Cell-6,Cell-6,MarkColor(M));
            if(R==CurR && C==CurC && !Core.Over) F.AddRect(X,Y,Cell,5,{255,236,180,255});
        }
        if(Guide.Index>=0) {
            if(Guide.Row) F.AddRect(Left-10,Top+Guide.Index*Cell+Cell-4,N*Cell+20,4,{120,225,255,255});
            else F.AddRect(Left+Guide.Index*Cell+Cell-4,Top-10,4,N*Cell+20,{120,225,255,255});
        }
        F.AddText(580,120,"TARGET",{255,236,220,255},16);
        for(int R=0;R<N;++R) F.AddRect(580,150+R*22,120,16,MarkColor(facetlock::Marks()[R]));
        if(LastGained>0 && !Core.Over) F.AddText(580,320,"+"+std::to_string(LastGained),{255,236,180,255},24);
        if(Core.Over) F.AddText(560,360,Core.Won?"WON: THE VAULT LOCK OPENS":"LOST: THE LOCK SEALS",{255,236,180,255},18);
        F.AddText(28,548,HintLine(),{255,236,180,255},16);
        F.AddText(28,528,HowToLine(),{255,236,180,255},14);
        DrawAccess(F,300,500,KeyHint(),ContrastMark());
        F.AddText(620,548,ActionCue(),{120,225,255,255},16);
    }
    Status GetStatus() const override {
        if(Core.Over) return {Core.Score,0,true,Core.Won,(Core.Won?"The vault lock opened; ":"The lock sealed; ")+std::string("pad A or R scrambles a new lattice; moves left ")+std::to_string(Core.Moves)};
        return {Core.Score,1,false,false,"Moves "+std::to_string(Core.Moves)+"; solution "+std::to_string(Core.Solution.size())+" slides"};
    }
};
}} // daedalus::desktop
