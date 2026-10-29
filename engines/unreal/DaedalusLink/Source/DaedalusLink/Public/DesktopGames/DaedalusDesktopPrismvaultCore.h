// SPDX-License-Identifier: MIT
#pragma once
#include "DaedalusDesktopGameTypes.h"
#include "DaedalusPrismvaultCore.h"
#include <cerrno>
#include <cstdlib>
#include <sstream>
#include <string>
#include <vector>

namespace daedalus { namespace desktop {
// Prismvault Weigh (Prismheart cabinet): the ADaedalusDesktopArcade host for DaedalusPrismvaultCore.h, a port of
// tools/minigames/prismvault.py (prism-shard-dev, the rules authority). CPython-compatible seeding, so
// StartGame("prismvault", seed) hides the same hollow shard as prismvault.start(seed, difficulty). Left/Right or
// stick pick a shard; pad A / J cycles it none -> left pan -> right pan -> none; pad X / Space weighs the pans
// (equal, non-empty); pad Y / Shift names the cursor shard; pad B / K clears both pans. R or pad Start restarts a
// finished vault. Option 0 Weigh; option 1 Guide practice loads the pans demo_action would use.
class PrismvaultGame final : public Game {
    prismvault::Game Core;
    std::uint32_t SessionSeed=730;
    int Option=0;
    int Cursor=0;
    std::vector<int> Pan;    // per shard: 0 none, 1 left, 2 right
    char LastResult='?';
    int LastGained=0;
    bool WasPrev=false, WasNext=false;

    void Deal() { Core.Start(SessionSeed,CabinetDifficulty()); Cursor=0; Pan.assign(static_cast<size_t>(Core.Shards()),0); LastResult='?'; LastGained=0; WasPrev=WasNext=false; }
    static bool GoPrev(const Input& I) { return I.Left||I.Up||I.PadLeft||I.PadUp||I.AxisX<-0.4||I.AxisY<-0.4; }
    static bool GoNext(const Input& I) { return I.Right||I.Down||I.PadRight||I.PadDown||I.AxisX>0.4||I.AxisY>0.4; }
    void Move(int Dir) { const int N=Core.Shards(); if(N<=0) return; Cursor=((Cursor+Dir)%N+N)%N; }
    static bool ParseLL(const std::string& S,long long& Out) {
        if(S.empty()) return false;
        char* End=nullptr;
        errno=0;
        const long long V=std::strtoll(S.c_str(),&End,10);
        if(End==S.c_str()||*End!='\0'||errno==ERANGE) return false;
        Out=V;
        return true;
    }
    std::vector<int> PanList(int Which) const { std::vector<int> V; for(int I=0;I<static_cast<int>(Pan.size());++I) if(Pan[static_cast<size_t>(I)]==Which) V.push_back(I); return V; }
public:
    const prismvault::Game& CoreState() const { return Core; }
    int CursorShard() const { return Cursor; }
    int PanOf(int Shard) const { return Shard>=0 && Shard<static_cast<int>(Pan.size()) ? Pan[static_cast<size_t>(Shard)] : 0; }
    char LastWeighResult() const { return LastResult; }
    int LastGain() const { return LastGained; }

    void Reset(std::uint32_t Seed) override { SessionSeed=Seed; Deal(); }
    bool SetCabinetDifficulty(const std::string& Name) override { if(!Game::SetCabinetDifficulty(Name)) return false; Deal(); return true; }
    bool SetOption(int Value,std::uint32_t Seed) override { if(Value<0 || Value>1) return false; Option=Value; SessionSeed=Seed; Deal(); return true; }
    int GetOption() const override { return Option; }
    void CyclePan() { if(Core.Over) return; int& P=Pan[static_cast<size_t>(Cursor)]; P=(P+1)%3; }
    void ClearPans() { for(int& P:Pan) P=0; }
    bool WeighPans() {
        if(Core.Over) return false;
        char R='?';
        if(Core.Weigh(PanList(1),PanList(2),R)!=prismvault::Game::Act::Ok) return false;
        LastResult=R; ClearPans(); return true;
    }
    bool NameCursor() {
        if(Core.Over) return false;
        int Gained=0;
        if(Core.Name(Cursor,Gained)!=prismvault::Game::Act::Ok) return false;
        LastGained=Gained; return true;
    }
    bool SourceKeyDown(int Key) override {
        if(Core.Over) { if(Key==5||Key==6||Key==7||Key==8) { Deal(); return true; } return false; }
        if(Key==0||Key==2) Move(-1); else if(Key==1||Key==3) Move(1);
        else if(Key==5||Key==6) CyclePan(); else if(Key==4) ClearPans(); else if(Key==7) WeighPans();
        return false;
    }
    bool SourceControllerButton(int Button) override {
        if(Button==0 && !Core.Over) { CyclePan(); return true; }
        if(Button==1 && Core.Over) { Deal(); return true; }
        return false;
    }
    void Step(const Input& I) override {
        if(Core.Over) { if(I.FirePressed||I.JumpPressed||I.ActionPressed||I.DashPressed) Deal(); return; }
        const bool P=GoPrev(I), N=GoNext(I);
        if(P && !WasPrev) Move(-1); else if(N && !WasNext) Move(1);
        WasPrev=P; WasNext=N;
        if(I.FirePressed) CyclePan(); else if(I.JumpPressed) ClearPans(); else if(I.ActionPressed) WeighPans(); else if(I.DashPressed) NameCursor();
    }
    std::string SaveState() const override {
        std::ostringstream O;
        O<<"prismvault v1 d="<<CabinetDifficulty()<<" seed="<<SessionSeed<<" weighings="<<Core.Weighings<<" score="<<Core.Score<<" over="<<(Core.Over?1:0)<<" won="<<(Core.Won?1:0)
         <<" cursor="<<Cursor<<" candidates="<<(Core.Candidates.empty()?"-":Core.CandidatesString())<<" log=";
        for(size_t I=0;I<Core.Log.size();++I) { if(I) O<<';'; O<<prismvault::Game::ListString(Core.Log[I].Left)<<':'<<prismvault::Game::ListString(Core.Log[I].Right)<<':'<<Core.Log[I].Result; }
        return O.str();
    }
    bool RestoreState(const std::string& Text,std::uint32_t) override {
        if(Text.rfind("prismvault v1 ",0)!=0) return false;
        auto Val=[&](const std::string& Key)->std::string { const std::string N=" "+Key+"="; const size_t P=Text.find(N); if(P==std::string::npos) return ""; const size_t S=P+N.size(), E=Text.find(' ',S); return Text.substr(S,E==std::string::npos?std::string::npos:E-S); };
        auto Split=[](const std::string& S,char Sep) { std::vector<std::string> Out; std::string Tok; for(char Ch:S) { if(Ch==Sep) { Out.push_back(Tok); Tok.clear(); } else Tok.push_back(Ch); } if(!S.empty()) Out.push_back(Tok); return Out; };
        long long Seed=0,W=0,Score=0,Over=0,Won=0,Cur=0;
        if(!ParseLL(Val("seed"),Seed)||!ParseLL(Val("weighings"),W)||!ParseLL(Val("score"),Score)||!ParseLL(Val("over"),Over)||!ParseLL(Val("won"),Won)||!ParseLL(Val("cursor"),Cur)) return false;
        const std::string Diff=Val("d"); const prismvault::Difficulty* D=prismvault::FindDifficulty(Diff);
        if(!D||Seed<0||Seed>0xffffffffLL||W<0||W>D->Weighings||Score<0||Score>1000||(Over!=0&&Over!=1)||(Won!=0&&Won!=1)||Cur<0||Cur>=D->Shards) return false;
        // Regenerate the hollow shard from the seed, then replay the saved log so candidates are derived, not trusted.
        prismvault::Game Fresh; if(!Fresh.Start(static_cast<std::uint32_t>(Seed),Diff)) return false;
        const std::string LogS=Val("log");
        if(!LogS.empty()) for(const std::string& Row:Split(LogS,';')) {
            const std::vector<std::string> P=Split(Row,':'); if(P.size()!=3||P[2].size()!=1) return false;
            std::vector<int> L,R;
            for(const std::string& X:Split(P[0],',')) { long long V=0; if(!ParseLL(X,V)) return false; L.push_back(static_cast<int>(V)); }
            for(const std::string& X:Split(P[1],',')) { long long V=0; if(!ParseLL(X,V)) return false; R.push_back(static_cast<int>(V)); }
            char Res='?'; if(Fresh.Weigh(L,R,Res)!=prismvault::Game::Act::Ok||Res!=P[2][0]) return false;
        }
        if(Fresh.Weighings!=static_cast<int>(W)) return false;
        const std::string CandS=Val("candidates"); if((CandS=="-"?std::string():CandS)!=Fresh.CandidatesString()) return false;
        Fresh.Score=static_cast<int>(Score); Fresh.Over=Over!=0; Fresh.Won=Won!=0;
        Game::SetCabinetDifficulty(Diff);
        SessionSeed=static_cast<std::uint32_t>(Seed); Core=Fresh; Cursor=static_cast<int>(Cur); Pan.assign(static_cast<size_t>(Core.Shards()),0); LastResult='?'; LastGained=0; WasPrev=WasNext=false;
        return true;
    }
    std::uint32_t SeedAfterRestore(std::uint32_t) const override { return SessionSeed; }
    std::string HintLine() const {
        if(Core.Over) return Core.Won?"HINT You found the hollow shard. Pad A or R seals a new vault.":"HINT Wrong shard. Pad A or R seals a new vault.";
        if(Option==1) return "HINT Practice: the blue pans show a balanced split.";
        return "HINT Split the suspects in three; the lighter pan holds the hollow one.";
    }
    std::string ActionCue() const { if(Core.Over) return "CUE Retry"; if(Core.Candidates.size()==1) return "CUE Name it"; if(Core.Weighings==0) return "CUE Name a shard"; return "CUE Load the pans"; }
    std::string HowToLine() const override { return "HOW Weigh equal groups of shards on the balance to find the hollow one, then name it before the weighings run out."; }
    std::string KeyHint() const override { return "KEYS Left or Right picks a shard; A pans it, X weighs, Y names."; }
    std::string ContrastMark() const override { return Core.Over?"MARK WAIT":"MARK ACT"; }
    void Render(Frame& F) const override {
        F.Clear(800,600,{14,16,24,255});
        F.AddText(28,20,std::string(Option==1?"PRISMVAULT GUIDE  [":"PRISMVAULT WEIGH  [")+CabinetDifficulty()+"]",{226,236,255,255},26);
        F.AddText(28,56,"SCORE: "+std::to_string(Core.Score)+"   WEIGHINGS LEFT: "+std::to_string(Core.Weighings)+"   SUSPECTS: "+std::to_string(Core.Candidates.size()),White,18);
        const int N=Core.Shards(); if(N<=0) return;
        std::vector<int> GuideL,GuideR;
        if(Option==1 && !Core.Over) { const prismvault::Game::Demo Dm=Core.DemoAction(); if(!Dm.IsName) { GuideL=Dm.Left; GuideR=Dm.Right; } else GuideL.push_back(Dm.Shard); }
        const int Cols=N<=12?N:9; const double Cell=N<=12?48:40, Left=60, Top=110;
        for(int I=0;I<N;++I) {
            const double X=Left+(I%Cols)*Cell, Y=Top+(I/Cols)*Cell;
            bool Suspect=false; for(int C:Core.Candidates) if(C==I) Suspect=true;
            const int P=Pan[static_cast<size_t>(I)];
            F.AddCircle(X+Cell/2,Y+Cell/2,Cell*0.36,P==1?Color{255,180,90,255}:P==2?Color{90,180,255,255}:Suspect?Color{200,200,220,255}:Color{50,50,64,255});
            bool GL=false,GR=false; for(int G:GuideL) if(G==I) GL=true; for(int G:GuideR) if(G==I) GR=true;
            if(GL||GR) F.AddCircle(X+Cell/2,Y+Cell/2,Cell*0.44,{120,225,255,255});
            if(I==Cursor && !Core.Over) F.AddRect(X+4,Y+Cell-6,Cell-8,4,{255,236,180,255});
            F.AddText(X+Cell/2-6,Y+Cell/2-8,std::to_string(I),Black,12);
        }
        F.AddText(520,120,"LOG",{226,236,255,255},16);
        for(size_t I=0;I<Core.Log.size() && I<3;++I) F.AddText(520,146+static_cast<double>(I)*22,prismvault::Game::ListString(Core.Log[I].Left)+" "+std::string(1,Core.Log[I].Result)+" "+prismvault::Game::ListString(Core.Log[I].Right),White,14);
        if(LastResult!='?' && !Core.Over) F.AddText(520,240,std::string("BALANCE: ")+(LastResult=='<'?"left is lighter":LastResult=='>'?"right is lighter":"balanced"),{255,236,180,255},16);
        if(LastGained>0 && !Core.Over) F.AddText(520,270,"+"+std::to_string(LastGained),{255,236,180,255},24);
        if(Core.Over) F.AddText(60,400,Core.Won?"WON: SHARD "+std::to_string(Core.Hollow)+" WAS HOLLOW":"LOST: SHARD "+std::to_string(Core.Hollow)+" WAS THE HOLLOW ONE",{255,236,180,255},22);
        F.AddText(28,548,HintLine(),{255,236,180,255},16);
        F.AddText(28,528,HowToLine(),{255,236,180,255},14);
        DrawAccess(F,300,500,KeyHint(),ContrastMark());
        F.AddText(600,548,ActionCue(),{120,225,255,255},16);
    }
    Status GetStatus() const override {
        if(Core.Over) return {Core.Score,0,true,Core.Won,(Core.Won?"The hollow shard was found; ":"Wrong shard; ")+std::string("pad A or R seals a new vault; weighings left ")+std::to_string(Core.Weighings)};
        return {Core.Score,1,false,false,"Weighings "+std::to_string(Core.Weighings)+"; suspects "+std::to_string(Core.Candidates.size())};
    }
};
}} // daedalus::desktop
