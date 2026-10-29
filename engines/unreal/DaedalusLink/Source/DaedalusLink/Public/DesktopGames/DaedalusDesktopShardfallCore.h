// SPDX-License-Identifier: MIT
#pragma once
#include "DaedalusDesktopGameTypes.h"
#include "DaedalusShardfallCore.h"
#include <cerrno>
#include <cstdlib>
#include <sstream>
#include <string>
#include <vector>

namespace daedalus { namespace desktop {
// Shardfall Gamble (Prismheart cabinet): the ADaedalusDesktopArcade host for DaedalusShardfallCore.h, a port of
// tools/minigames/shardfall.py (prism-shard-dev, the rules authority). CPython-compatible seeding and shuffle, so
// StartGame("shardfall", seed) deals the same seam as shardfall.start(seed, difficulty). Pad A / J / Space draws a
// shard; pad B / K or pad X / Shift banks the pot. R or pad Start restarts a finished seam. Option 0 Gamble;
// option 1 Guide practice shows whether demo_action would draw or bank.
class ShardfallGame final : public Game {
    shardfall::Game Core;
    std::uint32_t SessionSeed=730;
    int Option=0;
    std::string LastResult;
    int LastValue=0;
    bool WasDraw=false, WasBank=false;

    void Deal() { Core.Start(SessionSeed,CabinetDifficulty()); LastResult.clear(); LastValue=0; }
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
    const shardfall::Game& CoreState() const { return Core; }
    const std::string& LastResultText() const { return LastResult; }

    void Reset(std::uint32_t Seed) override { SessionSeed=Seed; Deal(); }
    bool SetCabinetDifficulty(const std::string& Name) override { if(!Game::SetCabinetDifficulty(Name)) return false; Deal(); return true; }
    bool SetOption(int Value,std::uint32_t Seed) override { if(Value<0 || Value>1) return false; Option=Value; SessionSeed=Seed; Deal(); return true; }
    int GetOption() const override { return Option; }
    bool DrawShard() {
        if(Core.Over) return false;
        shardfall::Game::Draw D; int V=0;
        if(Core.DrawShard(D,V)!=shardfall::Game::Act::Ok) return false;
        LastResult=D==shardfall::Game::Draw::Collapse?"collapse":D==shardfall::Game::Draw::Cracked?"cracked":"+"+std::to_string(V); LastValue=V; return true;
    }
    bool BankPot() {
        if(Core.Over) return false;
        int B=0; if(Core.Bank(B)!=shardfall::Game::Act::Ok) return false;
        LastResult="banked "+std::to_string(B); LastValue=B; return true;
    }
    bool SourceKeyDown(int Key) override {
        if(Core.Over) { if(Key==5||Key==6||Key==7||Key==8) { Deal(); return true; } return false; }
        if(Key==5||Key==6||Key==7) DrawShard(); else if(Key==4) BankPot();
        return false;
    }
    bool SourceControllerButton(int Button) override {
        if(Button==0 && !Core.Over) { DrawShard(); return true; }
        if(Button==1 && Core.Over) { Deal(); return true; }
        return false;
    }
    void Step(const Input& I) override {
        const bool Dr=I.FirePressed, Bk=I.JumpPressed||I.ActionPressed||I.DashPressed;
        if(Core.Over) { if((Dr && !WasDraw)||(Bk && !WasBank)) Deal(); }
        else if(Dr && !WasDraw) DrawShard(); else if(Bk && !WasBank) BankPot();
        WasDraw=Dr; WasBank=Bk;
    }
    std::string SaveState() const override {
        std::ostringstream O;
        O<<"shardfall v1 d="<<CabinetDifficulty()<<" seed="<<SessionSeed<<" drawn="<<Core.Rng.Drawn()<<" round="<<Core.Round<<" pot="<<Core.Pot<<" cracks="<<Core.Cracks
         <<" score="<<Core.Score<<" over="<<(Core.Over?1:0)<<" won="<<(Core.Won?1:0)<<" bag="<<Core.BagString()<<" history="<<Core.HistoryString();
        return O.str();
    }
    bool RestoreState(const std::string& Text,std::uint32_t) override {
        if(Text.rfind("shardfall v1 ",0)!=0) return false;
        auto Val=[&](const std::string& Key)->std::string { const std::string N=" "+Key+"="; const size_t P=Text.find(N); if(P==std::string::npos) return ""; const size_t S=P+N.size(), E=Text.find(' ',S); return Text.substr(S,E==std::string::npos?std::string::npos:E-S); };
        auto Ints=[&](const std::string& S,std::vector<int>& Out,int Lo,int Hi) { Out.clear(); if(S=="-"||S.empty()) return S=="-"; std::string Tok; for(char Ch:S+",") { if(Ch==',') { long long V=0; if(!ParseLL(Tok,V)||V<Lo||V>Hi) return false; Out.push_back(static_cast<int>(V)); Tok.clear(); } else Tok.push_back(Ch); } return true; };
        long long Seed=0,Drawn=0,Round=0,Pot=0,Cracks=0,Score=0,Over=0,Won=0;
        if(!ParseLL(Val("seed"),Seed)||!ParseLL(Val("drawn"),Drawn)||!ParseLL(Val("round"),Round)||!ParseLL(Val("pot"),Pot)||!ParseLL(Val("cracks"),Cracks)
           ||!ParseLL(Val("score"),Score)||!ParseLL(Val("over"),Over)||!ParseLL(Val("won"),Won)) return false;
        const std::string Diff=Val("d"); const shardfall::Difficulty* D=shardfall::FindDifficulty(Diff);
        if(!D||Seed<0||Seed>0xffffffffLL||Drawn<1||Drawn>200000||Round<1||Round>D->Rounds||Pot<0||Pot>35||Cracks<0||Cracks>=shardfall::BustAt||Score<0||Score>400||(Over!=0&&Over!=1)||(Won!=0&&Won!=1)) return false;
        std::vector<int> Bag,Hist;
        if(!Ints(Val("bag"),Bag,0,5)||!Ints(Val("history"),Hist,0,35)) return false;
        if(static_cast<int>(Bag.size())>shardfall::ValueCount+D->Cracked||static_cast<int>(Hist.size())!=Round-1-(Over?0:0)+(Over?0:0)) {}
        if(static_cast<int>(Hist.size())!=(Over?Round:Round-1)) return false;
        int Cracked=0; for(int V:Bag) if(V==0) ++Cracked; if(Cracked+Cracks>D->Cracked) return false;
        Game::SetCabinetDifficulty(Diff);
        SessionSeed=static_cast<std::uint32_t>(Seed);
        Core.Diff=D; Core.Round=static_cast<int>(Round); Core.Pot=static_cast<int>(Pot); Core.Cracks=static_cast<int>(Cracks); Core.Score=static_cast<int>(Score); Core.Over=Over!=0; Core.Won=Won!=0; Core.Bag=Bag; Core.History=Hist;
        Core.Rng.Seed(std::string(shardfall::GameId())+":"+std::to_string(SessionSeed)+":"+Diff); Core.Rng.Discard(static_cast<std::uint64_t>(Drawn));
        LastResult.clear(); LastValue=0;
        return true;
    }
    std::uint32_t SeedAfterRestore(std::uint32_t) const override { return SessionSeed; }
    std::string HintLine() const {
        if(Core.Over) return Core.Won?"HINT The seam's light is yours. Pad A or R opens a new seam.":"HINT The seam closed. Pad A or R opens a new seam.";
        if(Option==1) return std::string("HINT Practice: the Wardens would ")+(Core.DemoBank()?"BANK now.":"DRAW again.");
        if(Core.Cracks>0) return "HINT One crack already. The next cracked shard collapses the seam.";
        return "HINT Draw to grow the pot; bank before the second crack.";
    }
    std::string ActionCue() const { if(Core.Over) return "CUE Retry"; if(Core.Bag.empty()) return "CUE Bank"; return Core.Cracks>0?"CUE Draw or bank":"CUE Draw"; }
    std::string HowToLine() const override { return "HOW Draw shards to grow the pot or bank it; a second cracked shard collapses the seam and loses the pot; reach the target by the last round."; }
    std::string KeyHint() const override { return "KEYS A draws a shard; B or X banks the pot."; }
    std::string ContrastMark() const override { return Core.Over?"MARK WAIT":"MARK ACT"; }
    void Render(Frame& F) const override {
        F.Clear(800,600,{22,14,14,255});
        F.AddText(28,20,std::string(Option==1?"SHARDFALL GUIDE  [":"SHARDFALL GAMBLE  [")+CabinetDifficulty()+"]",{255,232,210,255},26);
        F.AddText(28,56,"ROUND "+std::to_string(Core.Round)+"/"+std::to_string(Core.Diff?Core.Diff->Rounds:0)+"   SCORE: "+std::to_string(Core.Score)+"/"+std::to_string(Core.Diff?Core.Diff->Target:0),White,18);
        F.AddRect(60,120,300,180,{44,28,28,255});
        F.AddText(80,132,"POT",{255,232,210,255},16);
        F.AddText(80,160,std::to_string(Core.Pot),{255,236,180,255},54);
        F.AddText(80,240,"CRACKS "+std::to_string(Core.Cracks)+"/"+std::to_string(shardfall::BustAt),Core.Cracks?Color{255,150,120,255}:White,16);
        F.AddRect(400,120,340,180,{36,26,36,255});
        F.AddText(420,132,"SEAM: "+std::to_string(Core.Bag.size())+" shards, "+std::to_string(Core.CrackedLeft())+" cracked",{255,232,210,255},16);
        for(size_t I=0;I<Core.Bag.size();++I) F.AddRect(420+static_cast<double>(I%8)*38,160+static_cast<double>(I/8)*38,30,30,{90,72,90,255});
        if(!LastResult.empty() && !Core.Over) F.AddText(420,250,"LAST: "+LastResult,{255,236,180,255},20);
        if(Option==1 && !Core.Over) F.AddRect(400,304,340,6,Core.DemoBank()?Color{120,225,255,255}:Color{255,236,180,255});
        F.AddText(60,330,"BANKED: "+Core.HistoryString(),White,16);
        if(Core.Over) F.AddText(60,380,Core.Won?"WON: THE SEAM'S LIGHT IS YOURS":"LOST: THE SEAM CLOSES",{255,236,180,255},22);
        F.AddText(28,548,HintLine(),{255,236,180,255},16);
        F.AddText(28,528,HowToLine(),{255,236,180,255},14);
        DrawAccess(F,300,500,KeyHint(),ContrastMark());
        F.AddText(620,548,ActionCue(),{120,225,255,255},16);
    }
    Status GetStatus() const override {
        if(Core.Over) return {Core.Score,0,true,Core.Won,(Core.Won?"The seam's light is yours; ":"The seam closed; ")+std::string("pad A or R opens a new seam; rounds ")+std::to_string(Core.Round)};
        return {Core.Score,1,false,false,"Round "+std::to_string(Core.Round)+"; pot "+std::to_string(Core.Pot)+"; cracks "+std::to_string(Core.Cracks)};
    }
};
}} // daedalus::desktop
