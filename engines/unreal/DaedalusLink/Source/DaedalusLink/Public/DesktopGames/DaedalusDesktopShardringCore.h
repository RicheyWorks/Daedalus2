// SPDX-License-Identifier: MIT
#pragma once
#include "DaedalusDesktopGameTypes.h"
#include "DaedalusShardringCore.h"
#include <memory>
#include <sstream>
#include <string>
#include <vector>

namespace daedalus { namespace desktop {
// Shardring Resonance (Prismheart cabinet): the ADaedalusDesktopArcade host for the pure core in
// DaedalusShardringCore.h, which is a port of tools/minigames/prism_shard.py (the rules authority).
// Draws come from the portable Random stream (deliberately not Python's PRNG; see GameTypes) unless a
// test injects an Oracle, which is how parity with the Python fixtures is proven. Cabinet difficulty is
// the game's difficulty (easy 12 facets / normal 10 / hard 8). Controls follow the DaedalusPad map in
// tools/minigames/web/shardring/index.html: Left/Up previous facet, Right/Down next, confirm sets the shard.
class ShardringGame final : public Game {
    // Own xorshift copy of desktop::Random so the stream state can be saved and restored.
    struct Stream : shardring::Oracle {
        std::uint32_t State=730; int Hues=4;
        void Seed(std::uint32_t Value) { State=Random::InitialState(Value); }
        std::uint32_t Next() { State^=State<<13; State^=State>>17; State^=State<<5; return State; }
        shardring::Hue Draw() override { return static_cast<shardring::Hue>(Next()%static_cast<std::uint32_t>(Hues)); }
        int SpiritPick(const std::vector<int>& Filled) override { return Filled[Next()%static_cast<std::uint32_t>(Filled.size())]; }
    };
    Stream Rng;
    shardring::Oracle* External=nullptr;
    shardring::Game Core;
    std::uint32_t SessionSeed=730;
    int Option=0;
    int Cursor=0;
    int LastGained=0;
    bool WasPrev=false, WasNext=false, WasConfirm=false;
    bool SaveRequested=false;

    shardring::Oracle& Source() { return External ? *External : Rng; }
    void Deal() {
        const shardring::Difficulty* D=shardring::FindDifficulty(CabinetDifficulty());
        Rng.Hues=D?D->Hues:4;
        Rng.Seed(SessionSeed^static_cast<std::uint32_t>((D?D->Facets:10)*0x9e3779b1u));
        Core.Start(D?D->Name:"normal",Source());
        Cursor=0; LastGained=0; WasPrev=WasNext=WasConfirm=false;
    }
    static bool GoPrev(const Input& I) { return I.Left||I.Up||I.PadLeft||I.PadUp||I.AxisX<-0.4||I.AxisY<-0.4; }
    static bool GoNext(const Input& I) { return I.Right||I.Down||I.PadRight||I.PadDown||I.AxisX>0.4||I.AxisY>0.4; }
    static bool Confirm(const Input& I) { return I.FirePressed||I.JumpPressed||I.ActionPressed||I.DashPressed; }
    void MoveCursor(int Dir) {
        const int N=Core.Facets(); if(N<=0) return;
        for(int K=1;K<=N;++K) { const int C=((Cursor+Dir*K)%N+N)%N; if(Core.Ring[static_cast<std::size_t>(C)]==shardring::Hue::None) { Cursor=C; return; } }
    }
    void Settle() { if(Core.Facets() && Core.Ring[static_cast<std::size_t>(Cursor)]!=shardring::Hue::None) MoveCursor(1); }
    static Color HueColor(shardring::Hue H) {
        switch(H) {
            case shardring::Hue::Ember: return {255,132,64,255};
            case shardring::Hue::Tide: return {72,160,255,255};
            case shardring::Hue::Verdant: return {96,214,112,255};
            case shardring::Hue::Gale: return {228,228,160,255};
            case shardring::Hue::Umbra: return {170,110,230,255};
            default: return {60,56,70,255};
        }
    }
public:
    // Tests only: route every draw/spirit pick through a fixture oracle instead of the portable stream.
    void UseOracle(shardring::Oracle* O) { External=O; }
    const shardring::Game& CoreState() const { return Core; }
    int CursorFacet() const { return Cursor; }
    int LastGain() const { return LastGained; }

    void Reset(std::uint32_t Seed) override { SessionSeed=Seed?Seed:1; Deal(); }
    bool SetCabinetDifficulty(const std::string& Name) override {
        if(!Game::SetCabinetDifficulty(Name)) return false;
        Deal(); return true;
    }
    // Option 0: Resonance (standard). Option 1: Guide practice, which marks the facet greedy_move would pick.
    bool SetOption(int Value,std::uint32_t Seed) override {
        if(Value<0 || Value>1) return false;
        Option=Value; SessionSeed=Seed?Seed:1; Deal(); return true;
    }
    int GetOption() const override { return Option; }
    bool SourceKeyDown(int Key) override {
        // Up,Down,Left,Right,B,A,Enter,Space,R,other
        if(Core.Over) { if(Key==5||Key==6||Key==7||Key==8) { Deal(); return true; } return false; }
        if(Key==0||Key==2) { MoveCursor(-1); return false; }
        if(Key==1||Key==3) { MoveCursor(1); return false; }
        if(Key==5||Key==6||Key==7) { Place(); return false; }
        return false;
    }
    bool SourceControllerButton(int Button) override {
        if(Button==0 && !Core.Over) { Place(); return true; }
        if(Button==1 && Core.Over) { Deal(); return true; }   // pad menu restarts only after the sphere settles
        return false;
    }
    bool Place() {
        if(Core.Over) return false;
        int Gained=0;
        const shardring::Game::Place R=Core.SetShard(Cursor,Source(),Gained);
        if(R!=shardring::Game::Place::Ok) return false;
        LastGained=Gained; Settle(); return true;
    }
    void Step(const Input& I) override {
        if(Core.Over) { if(Confirm(I)) Deal(); return; }
        const bool P=GoPrev(I), N=GoNext(I), C=Confirm(I);
        if(P && !WasPrev) MoveCursor(-1);
        else if(N && !WasNext) MoveCursor(1);
        WasPrev=P; WasNext=N;
        if(C && !WasConfirm) Place();
        WasConfirm=C;
    }
    std::string SaveState() const override {
        std::ostringstream O;
        O<<"shardring v1 d="<<CabinetDifficulty()<<" seed="<<SessionSeed<<" rng="<<Rng.State<<" pouch="<<Core.Pouch
         <<" score="<<Core.Score<<" chain="<<Core.Chain<<" cur="<<static_cast<int>(Core.Current)<<" next="<<static_cast<int>(Core.Next)
         <<" cursor="<<Cursor<<" over="<<(Core.Over?1:0)<<" won="<<(Core.Won?1:0)<<" ring=";
        for(shardring::Hue H:Core.Ring) O<<static_cast<int>(H)<<",";
        O<<" res="; for(int R:Core.Resonance) O<<R<<",";
        O<<" spirits="; for(shardring::Hue H:Core.Spirits) O<<static_cast<int>(H)<<",";
        return O.str();
    }
    bool RestoreState(const std::string& Text,std::uint32_t) override {
        std::istringstream In(Text); std::string Tag,Ver; In>>Tag>>Ver;
        if(Tag!="shardring"||Ver!="v1") return false;
        std::string Diff; std::uint32_t Seed=0,State=0; int Pouch=0,Chain=0,Cur=-1,Nxt=-1,Cur2=0,Over=0,Won=0; std::int64_t Score=0;
        std::string RingS,ResS,SpS;
        auto Val=[&](const std::string& Key)->std::string { const std::string N=" "+Key+"="; const size_t P=Text.find(N); if(P==std::string::npos) return ""; const size_t S=P+N.size(), E=Text.find(' ',S); return Text.substr(S,E==std::string::npos?std::string::npos:E-S); };
        try {
            Diff=Val("d"); Seed=static_cast<std::uint32_t>(std::stoul(Val("seed"))); State=static_cast<std::uint32_t>(std::stoul(Val("rng")));
            Pouch=std::stoi(Val("pouch")); Score=std::stoll(Val("score")); Chain=std::stoi(Val("chain")); Cur=std::stoi(Val("cur")); Nxt=std::stoi(Val("next"));
            Cur2=std::stoi(Val("cursor")); Over=std::stoi(Val("over")); Won=std::stoi(Val("won")); RingS=Val("ring"); ResS=Val("res"); SpS=Val("spirits");
        } catch(...) { return false; }
        const shardring::Difficulty* D=shardring::FindDifficulty(Diff);
        if(!D||State==0) return false;
        auto Ints=[](const std::string& S) { std::vector<int> Out; std::string Tok; for(char Ch:S) { if(Ch==',') { if(!Tok.empty()) Out.push_back(std::stoi(Tok)); Tok.clear(); } else Tok.push_back(Ch); } return Out; };
        std::vector<int> RingV,ResV,SpV;
        try { RingV=Ints(RingS); ResV=Ints(ResS); SpV=Ints(SpS); } catch(...) { return false; }
        if(static_cast<int>(RingV.size())!=D->Facets||ResV.size()!=static_cast<std::size_t>(shardring::HueCount)) return false;
        for(int V:RingV) if(V<-1||V>=D->Hues) return false;
        for(int V:SpV) if(V<0||V>=D->Hues) return false;
        if(Cur<0||Cur>=D->Hues||Nxt<0||Nxt>=D->Hues||Pouch<0||Pouch>D->Shards||Chain<0||Cur2<0||Cur2>=D->Facets) return false;
        Game::SetCabinetDifficulty(Diff);
        SessionSeed=Seed?Seed:1; Rng.State=State; Rng.Hues=D->Hues;
        Core.Diff=D; Core.Ring.clear(); for(int V:RingV) Core.Ring.push_back(static_cast<shardring::Hue>(V));
        Core.Pouch=Pouch; Core.Score=static_cast<int>(Score); Core.Chain=Chain;
        for(int I=0;I<shardring::HueCount;++I) Core.Resonance[I]=ResV[static_cast<std::size_t>(I)];
        Core.Spirits.clear(); for(int V:SpV) Core.Spirits.push_back(static_cast<shardring::Hue>(V));
        Core.Current=static_cast<shardring::Hue>(Cur); Core.Next=static_cast<shardring::Hue>(Nxt); Core.Over=Over!=0; Core.Won=Won!=0;
        Cursor=Cur2; LastGained=0; WasPrev=WasNext=WasConfirm=false; Settle();
        return true;
    }
    std::uint32_t SeedAfterRestore(std::uint32_t) const override { return SessionSeed; }
    bool SavePending() const override { return SaveRequested; }
    void ClearSavePending() override { SaveRequested=false; }
    std::string HintLine() const {
        if(Core.Over) return Core.Won?"HINT The sphere is whole. Pad A or R sets a new ring.":"HINT The sphere shattered. Pad A or R sets a new ring.";
        if(Core.Chain>0) return "HINT Chain "+std::to_string(Core.Chain)+": keep resonating for bigger clears.";
        if(Option==1) return "HINT Practice: the blue ring marks a strong facet.";
        return "HINT Three of one hue in a row resonate and clear.";
    }
    std::string ActionCue() const { return Core.Over?"CUE Retry":"CUE Set shard"; }
    std::string HowToLine() const override { return "HOW Set each shard in an empty facet; three of one hue in a row resonate."; }
    std::string KeyHint() const override { return "KEYS Left or Right picks a facet; A sets the shard."; }
    std::string ContrastMark() const override { return Core.Over?"MARK WAIT":"MARK ACT"; }
    void Render(Frame& F) const override {
        F.Clear(800,600,{14,12,26,255});
        F.AddText(28,20,std::string(Option==1?"SHARDRING GUIDE  [":"SHARDRING RESONANCE  [")+CabinetDifficulty()+"]",{236,222,255,255},26);
        F.AddText(28,56,"SCORE: "+std::to_string(Core.Score)+"   CHAIN: "+std::to_string(Core.Chain)+"   POUCH: "+std::to_string(Core.Pouch),White,18);
        const double CX=330, CY=300, R=165, Facet=26;
        F.AddCircle(CX,CY,R+Facet+10,{30,26,52,255});
        F.AddCircle(CX,CY,R-Facet-10,{14,12,26,255});
        const int N=Core.Facets(); const int Guide=Option==1?Core.GreedyMove():-1;
        for(int I=0;I<N;++I) {
            const double A=-1.5707963267948966+6.283185307179586*I/static_cast<double>(N);
            const double X=CX+R*std::cos(A), Y=CY+R*std::sin(A);
            const shardring::Hue H=Core.Ring[static_cast<std::size_t>(I)];
            if(I==Cursor && !Core.Over) F.AddCircle(X,Y,Facet+6,{255,236,180,255});
            if(Option==1 && !Core.Over && I==Guide) F.AddCircle(X,Y,Facet+3,{120,225,255,255});
            F.AddCircle(X,Y,Facet,HueColor(H));
            F.AddText(X-6,Y-9,std::to_string(I),H==shardring::Hue::None?Color{150,150,170,255}:Black,14);
        }
        F.AddRect(560,110,200,150,{22,20,40,255});
        F.AddText(572,118,"SHARD",{236,222,255,255},16);
        F.AddCircle(620,190,30,HueColor(Core.Current));
        F.AddText(586,230,shardring::HueName(Core.Current),White,14);
        F.AddText(680,118,"NEXT",{180,170,210,255},14);
        F.AddCircle(710,190,18,HueColor(Core.Next));
        F.AddText(690,230,shardring::HueName(Core.Next),{180,170,210,255},12);
        F.AddText(572,280,"SPIRITS",{236,222,255,255},16);
        for(std::size_t I=0;I<Core.Spirits.size() && I<8;++I) F.AddText(572,302+static_cast<double>(I)*18,shardring::SpiritName(Core.Spirits[I]),HueColor(Core.Spirits[I]),13);
        if(LastGained>0 && !Core.Over) F.AddText(CX-40,CY-10,"+"+std::to_string(LastGained),{255,236,180,255},24);
        if(Core.Over) F.AddText(CX-120,CY-14,Core.Won?"WON: THE SPHERE IS WHOLE":"LOST: THE SPHERE SHATTERED",{255,236,180,255},22);
        F.AddText(28,548,HintLine(),{255,236,180,255},16);
        F.AddText(28,528,HowToLine(),{255,236,180,255},14);
        DrawAccess(F,300,500,KeyHint(),ContrastMark());
        F.AddText(620,548,ActionCue(),{120,225,255,255},16);
    }
    Status GetStatus() const override {
        const std::string Sp=std::to_string(Core.Spirits.size());
        if(Core.Over) return {Core.Score,0,true,Core.Won,(Core.Won?"The sphere is whole; ":"The sphere shattered; ")+std::string("pad A or R sets a new ring; spirits ")+Sp};
        return {Core.Score,1,false,false,"Pouch "+std::to_string(Core.Pouch)+"; chain "+std::to_string(Core.Chain)+"; spirits "+Sp};
    }
};
}} // daedalus::desktop
