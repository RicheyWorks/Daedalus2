// SPDX-License-Identifier: MIT
#pragma once
#include "DaedalusDesktopGameTypes.h"
#include "DaedalusPrismcairnCore.h"
#include <cerrno>
#include <cstdlib>
#include <sstream>
#include <string>
#include <vector>

namespace daedalus { namespace desktop {
// Prismcairn Duel (Prismheart cabinet): the ADaedalusDesktopArcade host for DaedalusPrismcairnCore.h, a port of
// tools/minigames/prismcairn.py (prism-shard-dev, the rules authority). CPython-compatible seeding, so
// StartGame("prismcairn", seed) is the same duel as prismcairn.start(seed, difficulty). Left/Right or stick pick a
// cairn; pad A / J takes 1, pad B / K takes 2, pad X / Space takes 3, pad Y / Shift takes 4 (Fire, Jump, Action, Dash
// edges; capped at the difficulty's limit and the cairn). R or pad Start restarts a finished duel.
// Option 0 Duel; option 1 Guide practice marks the cairn and count best_move would take.
class PrismcairnGame final : public Game {
    prismcairn::Game Core;
    std::uint32_t SessionSeed=730;
    int Option=0;
    int Cursor=0;
    int LastWardenCairn=-1, LastWardenTake=-1;
    prismcairn::Game::Outcome LastOut=prismcairn::Game::Outcome::WardenTakes;
    bool WasPrev=false, WasNext=false;

    void Deal() { Core.Start(SessionSeed,CabinetDifficulty()); Cursor=0; LastWardenCairn=LastWardenTake=-1; WasPrev=WasNext=false; }
    static bool GoPrev(const Input& I) { return I.Left||I.Up||I.PadLeft||I.PadUp||I.AxisX<-0.4||I.AxisY<-0.4; }
    static bool GoNext(const Input& I) { return I.Right||I.Down||I.PadRight||I.PadDown||I.AxisX>0.4||I.AxisY>0.4; }
    void Move(int Dir) { const int N=static_cast<int>(Core.Cairns.size()); if(N<=0) return; Cursor=((Cursor+Dir)%N+N)%N; }
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
    const prismcairn::Game& CoreState() const { return Core; }
    int CursorCairn() const { return Cursor; }
    int LastWardenCairnIndex() const { return LastWardenCairn; }
    int LastWardenTakeCount() const { return LastWardenTake; }

    void Reset(std::uint32_t Seed) override { SessionSeed=Seed; Deal(); }
    bool SetCabinetDifficulty(const std::string& Name) override { if(!Game::SetCabinetDifficulty(Name)) return false; Deal(); return true; }
    bool SetOption(int Value,std::uint32_t Seed) override { if(Value<0 || Value>1) return false; Option=Value; SessionSeed=Seed; Deal(); return true; }
    int GetOption() const override { return Option; }
    /** Take `Count` shards from the cursor cairn (capped to the limit and the cairn). False when nothing happened. */
    bool Take(int Count) {
        if(Core.Over || Core.Cairns.empty()) return false;
        const int H=Core.Cairns[static_cast<size_t>(Cursor)]; if(H<=0) return false;
        const int T=std::min(Count,std::min(Core.Diff->TakeMax,H)); if(T<1) return false;
        const prismcairn::Game::Act R=Core.Take(Cursor,T,LastOut,LastWardenCairn,LastWardenTake);
        if(R!=prismcairn::Game::Act::Ok) return false;
        if(!Core.Over && Core.Cairns[static_cast<size_t>(Cursor)]==0) Move(1);
        return true;
    }
    bool SourceKeyDown(int Key) override {
        if(Core.Over) { if(Key==5||Key==6||Key==7||Key==8) { Deal(); return true; } return false; }
        if(Key==0||Key==2) Move(-1); else if(Key==1||Key==3) Move(1);
        else if(Key==5||Key==6) Take(1); else if(Key==4) Take(2); else if(Key==7) Take(3);
        return false;
    }
    bool SourceControllerButton(int Button) override {
        if(Button==0 && !Core.Over) { Take(1); return true; }
        if(Button==1 && Core.Over) { Deal(); return true; }
        return false;
    }
    void Step(const Input& I) override {
        if(Core.Over) { if(I.FirePressed||I.JumpPressed||I.ActionPressed||I.DashPressed) Deal(); return; }
        const bool P=GoPrev(I), N=GoNext(I);
        if(P && !WasPrev) Move(-1); else if(N && !WasNext) Move(1);
        WasPrev=P; WasNext=N;
        if(I.FirePressed) Take(1); else if(I.JumpPressed) Take(2); else if(I.ActionPressed) Take(3); else if(I.DashPressed) Take(4);
    }
    std::string SaveState() const override {
        std::ostringstream O;
        O<<"prismcairn v1 d="<<CabinetDifficulty()<<" seed="<<SessionSeed<<" drawn="<<Core.Rng.Drawn()<<" round="<<Core.Round<<" wins="<<Core.Wins<<" losses="<<Core.Losses
         <<" score="<<Core.Score<<" over="<<(Core.Over?1:0)<<" won="<<(Core.Won?1:0)<<" cursor="<<Cursor<<" cairns="<<Core.CairnsString();
        return O.str();
    }
    bool RestoreState(const std::string& Text,std::uint32_t) override {
        if(Text.rfind("prismcairn v1 ",0)!=0) return false;
        auto Val=[&](const std::string& Key)->std::string { const std::string N=" "+Key+"="; const size_t P=Text.find(N); if(P==std::string::npos) return ""; const size_t S=P+N.size(), E=Text.find(' ',S); return Text.substr(S,E==std::string::npos?std::string::npos:E-S); };
        long long Seed=0,Drawn=0,Round=0,Wins=0,Losses=0,Score=0,Over=0,Won=0,Cur=0;
        if(!ParseLL(Val("seed"),Seed)||!ParseLL(Val("drawn"),Drawn)||!ParseLL(Val("round"),Round)||!ParseLL(Val("wins"),Wins)||!ParseLL(Val("losses"),Losses)
           ||!ParseLL(Val("score"),Score)||!ParseLL(Val("over"),Over)||!ParseLL(Val("won"),Won)||!ParseLL(Val("cursor"),Cur)) return false;
        const std::string Diff=Val("d"); const prismcairn::Difficulty* D=prismcairn::FindDifficulty(Diff);
        if(!D||Seed<0||Seed>0xffffffffLL||Drawn<1||Drawn>200000||Round<1||Round>D->Rounds||Wins<0||Losses<0||Wins+Losses>=Round||Score<0||Score>1000||(Over!=0&&Over!=1)||(Won!=0&&Won!=1)||Cur<0||Cur>=D->Cairns) return false;
        std::vector<int> C; std::string Tok; const std::string CS=Val("cairns")+",";
        for(char Ch:CS) { if(Ch==',') { long long V=0; if(!ParseLL(Tok,V)||V<0||V>D->MaxHeight) return false; C.push_back(static_cast<int>(V)); Tok.clear(); } else Tok.push_back(Ch); }
        if(static_cast<int>(C.size())!=D->Cairns) return false;
        Game::SetCabinetDifficulty(Diff);
        SessionSeed=static_cast<std::uint32_t>(Seed);
        Core.Diff=D; Core.Round=static_cast<int>(Round); Core.Wins=static_cast<int>(Wins); Core.Losses=static_cast<int>(Losses); Core.Score=static_cast<int>(Score);
        Core.Over=Over!=0; Core.Won=Won!=0; Core.Cairns=C; Core.Log.clear();
        Core.Rng.Seed(std::string(prismcairn::GameId())+":"+std::to_string(SessionSeed)+":"+Diff); Core.Rng.Discard(static_cast<std::uint64_t>(Drawn));
        Cursor=static_cast<int>(Cur); LastWardenCairn=LastWardenTake=-1; WasPrev=WasNext=false;
        return true;
    }
    std::uint32_t SeedAfterRestore(std::uint32_t) const override { return SessionSeed; }
    std::string HintLine() const {
        if(Core.Over) return Core.Won?"HINT The Warden yields. Pad A or R raises new cairns.":"HINT The Warden keeps the cairns. Pad A or R raises new ones.";
        if(Option==1) return "HINT Practice: the blue mark shows the winning take.";
        return "HINT Lift the last shard. Leave the Warden a balanced field.";
    }
    std::string ActionCue() const { if(Core.Over) return "CUE Retry"; if(LastWardenTake>0) return "CUE Warden took "+std::to_string(LastWardenTake); return "CUE Take shards"; }
    std::string HowToLine() const override { return "HOW Take one or more shards, up to the limit, from one cairn each turn; lift the last shard to win the round, best of three."; }
    std::string KeyHint() const override { return "KEYS Left or Right picks a cairn; A/B/X/Y take 1/2/3/4."; }
    std::string ContrastMark() const override { return Core.Over?"MARK WAIT":"MARK ACT"; }
    void Render(Frame& F) const override {
        F.Clear(800,600,{18,16,22,255});
        F.AddText(28,20,std::string(Option==1?"PRISMCAIRN GUIDE  [":"PRISMCAIRN DUEL  [")+CabinetDifficulty()+"]",{236,226,255,255},26);
        F.AddText(28,56,"ROUND "+std::to_string(Core.Round)+"/"+std::to_string(Core.Diff?Core.Diff->Rounds:0)+"   WINS: "+std::to_string(Core.Wins)+"   LOSSES: "+std::to_string(Core.Losses)+"   SCORE: "+std::to_string(Core.Score)+"   TAKE 1-"+std::to_string(Core.Diff?Core.Diff->TakeMax:0),White,18);
        const int N=static_cast<int>(Core.Cairns.size()); if(N<=0) return;
        const std::pair<int,int> Guide=(Option==1 && !Core.Over)?Core.DemoAction():std::pair<int,int>{-1,0};
        const double Floor=430, Left=120, Gap=560.0/N;
        for(int I=0;I<N;++I) {
            const double X=Left+I*Gap; const int H=Core.Cairns[static_cast<size_t>(I)];
            for(int S=0;S<H;++S) F.AddRect(X-22+(S%2?3:0),Floor-(S+1)*22,44,18,{150,130,190,255});
            if(I==Cursor && !Core.Over) F.AddRect(X-28,Floor+6,56,5,{255,236,180,255});
            if(Guide.first==I) { F.AddRect(X-28,Floor+14,56,4,{120,225,255,255}); F.AddText(X-10,Floor+20,"-"+std::to_string(Guide.second),{120,225,255,255},14); }
            if(I==LastWardenCairn && !Core.Over) F.AddText(X-30,Floor-H*22-30,"-"+std::to_string(LastWardenTake),{255,150,120,255},16);
            F.AddText(X-6,Floor+36,std::to_string(H),White,14);
        }
        if(Core.Over) F.AddText(240,470,Core.Won?"WON: THE WARDEN YIELDS":"LOST: THE WARDEN KEEPS THE CAIRNS",{255,236,180,255},22);
        F.AddText(28,548,HintLine(),{255,236,180,255},16);
        F.AddText(28,528,HowToLine(),{255,236,180,255},14);
        DrawAccess(F,300,500,KeyHint(),ContrastMark());
        F.AddText(600,548,ActionCue(),{120,225,255,255},16);
    }
    Status GetStatus() const override {
        const std::string Rec=std::to_string(Core.Wins)+"-"+std::to_string(Core.Losses);
        if(Core.Over) return {Core.Score,0,true,Core.Won,(Core.Won?"The Warden yields; ":"The Warden keeps the cairns; ")+std::string("pad A or R raises new cairns; rounds ")+Rec};
        return {Core.Score,1,false,false,"Round "+std::to_string(Core.Round)+"; rounds "+Rec};
    }
};
}} // daedalus::desktop
