// SPDX-License-Identifier: MIT
#pragma once
#include "DaedalusDesktopGameTypes.h"
#include "DaedalusLumenpathCore.h"
#include <cerrno>
#include <cstdlib>
#include <set>
#include <sstream>
#include <string>
#include <vector>

namespace daedalus { namespace desktop {
// Lumenpath Refraction (Prismheart cabinet): the ADaedalusDesktopArcade host for DaedalusLumenpathCore.h, a port of
// tools/minigames/lumenpath.py (prism-shard-dev, the rules authority). Seeding is CPython-compatible, so
// StartGame("lumenpath", seed) is the same lattice as lumenpath.start(seed, difficulty). Cabinet difficulty is the
// game difficulty (easy 5x5 / normal 6x6 / hard 7x7). Controls: Left/Right/Up/Down or stick move the cursor; J/Space
// or pad A toggles the mirror under it (empty -> / -> \ -> empty); R or pad Start restarts a finished lattice.
// Option 0 Refraction; option 1 Guide practice marks the next solution mirror.
class LumenpathGame final : public Game {
    lumenpath::Game Core;
    std::uint32_t SessionSeed=730;
    int Option=0;
    int CurR=0, CurC=0;
    int LastGained=0;
    bool WasL=false, WasR=false, WasU=false, WasD=false, WasConfirm=false;

    void Deal() {
        Core.Start(SessionSeed,CabinetDifficulty());
        CurR=Core.SourceRow; CurC=0; LastGained=0; WasL=WasR=WasU=WasD=WasConfirm=false;
    }
    static bool GoL(const Input& I) { return I.Left||I.PadLeft||I.AxisX<-0.4; }
    static bool GoR(const Input& I) { return I.Right||I.PadRight||I.AxisX>0.4; }
    static bool GoU(const Input& I) { return I.Up||I.PadUp||I.AxisY<-0.4; }
    static bool GoD(const Input& I) { return I.Down||I.PadDown||I.AxisY>0.4; }
    static bool Confirm(const Input& I) { return I.FirePressed||I.JumpPressed||I.ActionPressed||I.DashPressed; }
    void Move(int DR,int DC) { const int N=Core.Size(); if(N<=0) return; CurR=((CurR+DR)%N+N)%N; CurC=((CurC+DC)%N+N)%N; }
    static bool ParseLL(const std::string& S,long long& Out) {
        if(S.empty()) return false;
        char* End=nullptr;
        errno=0;
        const long long V=std::strtoll(S.c_str(),&End,10);
        if(End==S.c_str()||*End!='\0'||errno==ERANGE) return false;
        Out=V;
        return true;
    }
public:
    const lumenpath::Game& CoreState() const { return Core; }
    int CursorRow() const { return CurR; }
    int CursorCol() const { return CurC; }
    int LastGain() const { return LastGained; }

    void Reset(std::uint32_t Seed) override { SessionSeed=Seed; Deal(); }
    bool SetCabinetDifficulty(const std::string& Name) override {
        if(!Game::SetCabinetDifficulty(Name)) return false;
        Deal(); return true;
    }
    bool SetOption(int Value,std::uint32_t Seed) override {
        if(Value<0 || Value>1) return false;
        Option=Value; SessionSeed=Seed; Deal(); return true;
    }
    int GetOption() const override { return Option; }
    bool Toggle() {
        if(Core.Over) return false;
        int Gained=0;
        if(Core.Toggle(CurR,CurC,Gained)!=lumenpath::Game::Act::Ok) return false;
        LastGained=Gained; return true;
    }
    bool SourceKeyDown(int Key) override {
        // Up,Down,Left,Right,B,A,Enter,Space,R,other
        if(Core.Over) { if(Key==5||Key==6||Key==7||Key==8) { Deal(); return true; } return false; }
        if(Key==0) Move(-1,0); else if(Key==1) Move(1,0); else if(Key==2) Move(0,-1); else if(Key==3) Move(0,1);
        else if(Key==5||Key==6||Key==7) Toggle();
        return false;
    }
    bool SourceControllerButton(int Button) override {
        if(Button==0 && !Core.Over) { Toggle(); return true; }
        if(Button==1 && Core.Over) { Deal(); return true; }
        return false;
    }
    void Step(const Input& I) override {
        if(Core.Over) { if(Confirm(I)) Deal(); return; }
        const bool L=GoL(I),R=GoR(I),U=GoU(I),D=GoD(I),C=Confirm(I);
        if(L && !WasL) Move(0,-1); else if(R && !WasR) Move(0,1);
        else if(U && !WasU) Move(-1,0); else if(D && !WasD) Move(1,0);
        WasL=L; WasR=R; WasU=U; WasD=D;
        if(C && !WasConfirm) Toggle();
        WasConfirm=C;
    }
    std::string SaveState() const override {
        std::ostringstream O;
        O<<"lumenpath v1 d="<<CabinetDifficulty()<<" seed="<<SessionSeed<<" moves="<<Core.Moves<<" score="<<Core.Score<<" lit="<<Core.Lit
         <<" best="<<Core.Best<<" over="<<(Core.Over?1:0)<<" won="<<(Core.Won?1:0)<<" cur="<<CurR<<","<<CurC<<" grid="<<Core.GridString();
        return O.str();
    }
    bool RestoreState(const std::string& Text,std::uint32_t) override {
        if(Text.rfind("lumenpath v1 ",0)!=0) return false;
        auto Val=[&](const std::string& Key)->std::string { const std::string N=" "+Key+"="; const size_t P=Text.find(N); if(P==std::string::npos) return ""; const size_t S=P+N.size(), E=Text.find(' ',S); return Text.substr(S,E==std::string::npos?std::string::npos:E-S); };
        long long Seed=0,Moves=0,Score=0,Lit=0,Best=0,Over=0,Won=0;
        if(!ParseLL(Val("seed"),Seed)||!ParseLL(Val("moves"),Moves)||!ParseLL(Val("score"),Score)||!ParseLL(Val("lit"),Lit)
           ||!ParseLL(Val("best"),Best)||!ParseLL(Val("over"),Over)||!ParseLL(Val("won"),Won)) return false;
        const std::string Cur=Val("cur"); const size_t Comma=Cur.find(',');
        long long CR=0,CC=0; if(Comma==std::string::npos||!ParseLL(Cur.substr(0,Comma),CR)||!ParseLL(Cur.substr(Comma+1),CC)) return false;
        const std::string Diff=Val("d");
        const lumenpath::Difficulty* D=lumenpath::FindDifficulty(Diff);
        if(!D||Seed<0||Seed>0xffffffffLL||Moves<0||Moves>1000||Score<0||Score>1000000||(Over!=0&&Over!=1)||(Won!=0&&Won!=1)) return false;
        // Regenerate the lattice from the seed (crystals, stones, solution), then overlay the saved mirrors.
        lumenpath::Game Fresh; if(!Fresh.Start(static_cast<std::uint32_t>(Seed),Diff)) return false;
        const std::string GridS=Val("grid"); std::vector<std::string> Rows; std::string Row;
        for(char Ch:GridS) { if(Ch=='|') { Rows.push_back(Row); Row.clear(); } else Row.push_back(Ch); }
        Rows.push_back(Row);
        if(static_cast<int>(Rows.size())!=D->Size) return false;
        for(int R=0;R<D->Size;++R) {
            if(static_cast<int>(Rows[static_cast<size_t>(R)].size())!=D->Size) return false;
            for(int C=0;C<D->Size;++C) {
                const char Have=Rows[static_cast<size_t>(R)][static_cast<size_t>(C)], Want=Fresh.Grid[static_cast<size_t>(R)][static_cast<size_t>(C)];
                const bool Fixed=Want=='*'||Want=='#';
                if(Fixed ? Have!=Want : !(Have=='.'||Have=='/'||Have=='\\')) return false;
            }
        }
        Fresh.Grid=Rows;
        if(Fresh.CountLit()!=static_cast<int>(Lit)||Lit>Best||Best>static_cast<long long>(Fresh.Crystals.size())) return false;
        if(CR<0||CR>=D->Size||CC<0||CC>=D->Size) return false;
        Game::SetCabinetDifficulty(Diff);
        SessionSeed=static_cast<std::uint32_t>(Seed); Core=Fresh;
        Core.Moves=static_cast<int>(Moves); Core.Score=static_cast<int>(Score); Core.Lit=static_cast<int>(Lit); Core.Best=static_cast<int>(Best);
        Core.Over=Over!=0; Core.Won=Won!=0;
        CurR=static_cast<int>(CR); CurC=static_cast<int>(CC); LastGained=0; WasL=WasR=WasU=WasD=WasConfirm=false;
        return true;
    }
    std::uint32_t SeedAfterRestore(std::uint32_t) const override { return SessionSeed; }
    std::string HintLine() const {
        if(Core.Over) return Core.Won?"HINT Every crystal glows. Pad A or R lays a new lattice.":"HINT The light faded. Pad A or R lays a new lattice.";
        if(Option==1) return "HINT Practice: the blue frame marks the next solution mirror.";
        return "HINT Mirrors cycle / then \\ then empty. Bend the beam through every crystal.";
    }
    std::string ActionCue() const { return Core.Over?"CUE Retry":"CUE Toggle mirror"; }
    std::string HowToLine() const override { return "HOW Toggle shard mirrors to bend the prism beam through every crystal before your moves run out."; }
    std::string KeyHint() const override { return "KEYS Arrows move the cursor; A toggles the mirror."; }
    std::string ContrastMark() const override { return Core.Over?"MARK WAIT":"MARK ACT"; }
    void Render(Frame& F) const override {
        F.Clear(800,600,{12,14,28,255});
        F.AddText(28,20,std::string(Option==1?"LUMENPATH GUIDE  [":"LUMENPATH REFRACTION  [")+CabinetDifficulty()+"]",{222,236,255,255},26);
        F.AddText(28,56,"SCORE: "+std::to_string(Core.Score)+"   LIT: "+std::to_string(Core.Lit)+"/"+std::to_string(Core.Crystals.size())+"   MOVES: "+std::to_string(Core.Moves),White,18);
        const int N=Core.Size(); if(N<=0) return;
        const double Cell=360.0/N, Left=180, Top=110;
        const std::vector<lumenpath::Cell> Beam=lumenpath::Trace(Core.Grid,Core.SourceRow);
        const std::set<lumenpath::Cell> On(Beam.begin(),Beam.end());
        lumenpath::Cell Guide{-1,-1};
        if(Option==1 && !Core.Over) { for(const lumenpath::Mirror& M:Core.Solution) if(Core.Grid[static_cast<size_t>(M.R)][static_cast<size_t>(M.C)]!=M.M) { Guide={M.R,M.C}; break; } }
        F.AddRect(Left-8,Top-8,N*Cell+16,N*Cell+16,{26,30,54,255});
        F.AddTriangle({Left-30,Top+Core.SourceRow*Cell+Cell*0.3},{Left-30,Top+Core.SourceRow*Cell+Cell*0.7},{Left-10,Top+Core.SourceRow*Cell+Cell*0.5},{255,236,140,255});
        for(int R=0;R<N;++R) for(int C=0;C<N;++C) {
            const double X=Left+C*Cell, Y=Top+R*Cell; const char Ch=Core.Grid[static_cast<size_t>(R)][static_cast<size_t>(C)];
            const bool Lit=On.count({R,C})!=0;
            F.AddRect(X+2,Y+2,Cell-4,Cell-4,Lit?Color{70,66,40,255}:Color{18,20,40,255});
            if(Ch=='#') F.AddRect(X+6,Y+6,Cell-12,Cell-12,{90,80,84,255});
            else if(Ch=='*') F.AddCircle(X+Cell/2,Y+Cell/2,Cell*0.28,Lit?Color{255,230,120,255}:Color{110,120,170,255});
            else if(Ch=='/') F.AddLine(X+Cell*0.2,Y+Cell*0.8,X+Cell*0.8,Y+Cell*0.2,{200,230,255,255},3);
            else if(Ch=='\\') F.AddLine(X+Cell*0.2,Y+Cell*0.2,X+Cell*0.8,Y+Cell*0.8,{200,230,255,255},3);
            if(Guide.first==R && Guide.second==C) F.AddRect(X+4,Y+4,Cell-8,Cell-8,{120,225,255,255});
            if(R==CurR && C==CurC && !Core.Over) F.AddRect(X,Y,Cell,4,{255,236,180,255});
        }
        for(size_t I=1;I<Beam.size();++I) {
            const double X0=Left+Beam[I-1].second*Cell+Cell/2, Y0=Top+Beam[I-1].first*Cell+Cell/2;
            const double X1=Left+Beam[I].second*Cell+Cell/2, Y1=Top+Beam[I].first*Cell+Cell/2;
            F.AddLine(X0,Y0,X1,Y1,{255,236,140,255},2);
        }
        if(LastGained>0 && !Core.Over) F.AddText(600,120,"+"+std::to_string(LastGained),{255,236,180,255},24);
        if(Core.Over) F.AddText(560,160,Core.Won?"WON: EVERY CRYSTAL GLOWS":"LOST: THE LIGHT FADES",{255,236,180,255},18);
        F.AddText(28,548,HintLine(),{255,236,180,255},16);
        F.AddText(28,528,HowToLine(),{255,236,180,255},14);
        DrawAccess(F,300,500,KeyHint(),ContrastMark());
        F.AddText(620,548,ActionCue(),{120,225,255,255},16);
    }
    Status GetStatus() const override {
        const std::string LitS=std::to_string(Core.Lit)+"/"+std::to_string(Core.Crystals.size());
        if(Core.Over) return {Core.Score,0,true,Core.Won,(Core.Won?"Every crystal glows; ":"The light faded; ")+std::string("pad A or R lays a new lattice; lit ")+LitS};
        return {Core.Score,1,false,false,"Lit "+LitS+"; moves "+std::to_string(Core.Moves)};
    }
};
}} // daedalus::desktop
