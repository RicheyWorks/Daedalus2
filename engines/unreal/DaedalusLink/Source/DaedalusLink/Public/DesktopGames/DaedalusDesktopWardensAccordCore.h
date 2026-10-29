// SPDX-License-Identifier: MIT
#pragma once
#include "DaedalusDesktopGameTypes.h"
#include "DaedalusWardensAccordCore.h"
#include <cerrno>
#include <cstdlib>
#include <sstream>
#include <string>
#include <vector>

namespace daedalus { namespace desktop {
// Wardens' Accord (Prismheart cabinet): the ADaedalusDesktopArcade host for DaedalusWardensAccordCore.h, a port of
// tools/minigames/wardens_accord.py (prism-shard-dev, the rules authority). CPython-compatible seeding, so
// StartGame("wardens_accord", seed) is the same altar as wardens_accord.start(seed, difficulty). One cursor runs over
// the three altar shards (0..2) and then the spirits (3..): Left/Up previous, Right/Down next, J/Space or pad A takes
// the shard or summons the spirit under the cursor; R or pad Start restarts a finished altar. Option 0 Accord;
// option 1 Guide practice marks what demo_action would do.
class WardensAccordGame final : public Game {
    wardens::Game Core;
    std::uint32_t SessionSeed=730;
    int Option=0;
    int Cursor=0;
    int LastGained=0;
    bool WasPrev=false, WasNext=false, WasConfirm=false;

    int Slots() const { return 3+static_cast<int>(Core.Spirits.size()); }
    void Deal() { Core.Start(SessionSeed,CabinetDifficulty()); Cursor=0; LastGained=0; WasPrev=WasNext=WasConfirm=false; }
    static bool GoPrev(const Input& I) { return I.Left||I.Up||I.PadLeft||I.PadUp||I.AxisX<-0.4||I.AxisY<-0.4; }
    static bool GoNext(const Input& I) { return I.Right||I.Down||I.PadRight||I.PadDown||I.AxisX>0.4||I.AxisY>0.4; }
    static bool Confirm(const Input& I) { return I.FirePressed||I.JumpPressed||I.ActionPressed||I.DashPressed; }
    void Move(int Dir) { const int N=Slots(); Cursor=((Cursor+Dir)%N+N)%N; }
    static bool ParseLL(const std::string& S,long long& Out) {
        if(S.empty()) return false;
        char* End=nullptr;
        errno=0;
        const long long V=std::strtoll(S.c_str(),&End,10);
        if(End==S.c_str()||*End!='\0'||errno==ERANGE) return false;
        Out=V;
        return true;
    }
    static Color HueColor(int H) {
        switch(H) { case 0: return {255,132,64,255}; case 1: return {72,160,255,255}; case 2: return {96,214,112,255}; case 3: return {228,228,160,255}; case 4: return {170,110,230,255}; default: return {60,56,70,255}; }
    }
public:
    const wardens::Game& CoreState() const { return Core; }
    int CursorSlot() const { return Cursor; }
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
    /** Take the altar shard or summon the spirit under the cursor. False when nothing happened. */
    bool Act() {
        if(Core.Over) return false;
        int Gained=0;
        const wardens::Game::Act R=Cursor<3 ? Core.Take(Cursor,Gained) : Core.Summon(Cursor-3,Gained);
        if(R!=wardens::Game::Act::Ok) return false;
        LastGained=Gained; return true;
    }
    bool SourceKeyDown(int Key) override {
        if(Core.Over) { if(Key==5||Key==6||Key==7||Key==8) { Deal(); return true; } return false; }
        if(Key==0||Key==2) Move(-1); else if(Key==1||Key==3) Move(1); else if(Key==5||Key==6||Key==7) Act();
        return false;
    }
    bool SourceControllerButton(int Button) override {
        if(Button==0 && !Core.Over) { Act(); return true; }
        if(Button==1 && Core.Over) { Deal(); return true; }
        return false;
    }
    void Step(const Input& I) override {
        if(Core.Over) { if(Confirm(I)) Deal(); return; }
        const bool P=GoPrev(I), N=GoNext(I), C=Confirm(I);
        if(P && !WasPrev) Move(-1); else if(N && !WasNext) Move(1);
        WasPrev=P; WasNext=N;
        if(C && !WasConfirm) Act();
        WasConfirm=C;
    }
    std::string SaveState() const override {
        std::ostringstream O;
        O<<"wardens_accord v1 d="<<CabinetDifficulty()<<" seed="<<SessionSeed<<" drawn="<<Core.Rng.Drawn()<<" rounds="<<Core.Rounds<<" score="<<Core.Score
         <<" over="<<(Core.Over?1:0)<<" won="<<(Core.Won?1:0)<<" cursor="<<Cursor<<" pouch="<<Core.PouchString()<<" offer=";
        for(size_t I=0;I<Core.Offer.size();++I) O<<(I?",":"")<<Core.Offer[I];
        O<<" summoned="; for(size_t I=0;I<Core.Summoned.size();++I) O<<(I?",":"")<<Core.Summoned[I];
        O<<" spirits=";
        for(size_t I=0;I<Core.Spirits.size();++I) { if(I) O<<';'; O<<Core.Spirits[I].Name<<':'; for(size_t J=0;J<Core.Spirits[I].Cost.size();++J) { if(J) O<<'+'; O<<Core.Spirits[I].Cost[J].first<<'='<<Core.Spirits[I].Cost[J].second; } O<<':'<<Core.Spirits[I].Value; }
        return O.str();
    }
    bool RestoreState(const std::string& Text,std::uint32_t) override {
        if(Text.rfind("wardens_accord v1 ",0)!=0) return false;
        auto Val=[&](const std::string& Key)->std::string { const std::string N=" "+Key+"="; const size_t P=Text.find(N); if(P==std::string::npos) return ""; const size_t S=P+N.size(), E=Text.find(' ',S); return Text.substr(S,E==std::string::npos?std::string::npos:E-S); };
        auto Split=[](const std::string& S,char Sep) { std::vector<std::string> Out; std::string Tok; for(char Ch:S) { if(Ch==Sep) { Out.push_back(Tok); Tok.clear(); } else Tok.push_back(Ch); } if(!Tok.empty()||!S.empty()) Out.push_back(Tok); return Out; };
        long long Seed=0,Drawn=0,Rounds=0,Score=0,Over=0,Won=0,Cur=0;
        if(!ParseLL(Val("seed"),Seed)||!ParseLL(Val("drawn"),Drawn)||!ParseLL(Val("rounds"),Rounds)||!ParseLL(Val("score"),Score)
           ||!ParseLL(Val("over"),Over)||!ParseLL(Val("won"),Won)||!ParseLL(Val("cursor"),Cur)) return false;
        const std::string Diff=Val("d");
        const wardens::Difficulty* D=wardens::FindDifficulty(Diff);
        if(!D||Seed<0||Seed>0xffffffffLL||Drawn<1||Drawn>200000||Rounds<0||Rounds>D->Rounds||Score<0||Score>100000||(Over!=0&&Over!=1)||(Won!=0&&Won!=1)) return false;
        wardens::Game Fresh; Fresh.Diff=D; Fresh.Rounds=static_cast<int>(Rounds); Fresh.Score=static_cast<int>(Score); Fresh.Over=Over!=0; Fresh.Won=Won!=0;
        const std::vector<std::string> PouchV=Split(Val("pouch"),','); if(static_cast<int>(PouchV.size())!=D->Hues) return false;
        for(int H=0;H<D->Hues;++H) { long long V=0; if(!ParseLL(PouchV[static_cast<size_t>(H)],V)||V<0||V>100) return false; Fresh.Pouch[H]=static_cast<int>(V); }
        const std::vector<std::string> OfferV=Split(Val("offer"),','); if(OfferV.size()!=3) return false;
        for(const std::string& S:OfferV) { long long V=0; if(!ParseLL(S,V)||V<0||V>=D->Hues) return false; Fresh.Offer.push_back(static_cast<int>(V)); }
        const std::string SummS=Val("summoned");
        if(!SummS.empty()) for(const std::string& S:Split(SummS,',')) { long long V=0; if(!ParseLL(S,V)||V<0||V>=wardens::NameCount) return false; Fresh.Summoned.push_back(static_cast<int>(V)); }
        const std::vector<std::string> SpV=Split(Val("spirits"),';'); if(static_cast<int>(SpV.size())!=D->Spirits) return false;
        for(const std::string& SpS:SpV) {
            const std::vector<std::string> Parts=Split(SpS,':'); if(Parts.size()!=3) return false;
            wardens::Spirit S; long long Name=0,Value=0;
            if(!ParseLL(Parts[0],Name)||Name<0||Name>=wardens::NameCount||!ParseLL(Parts[2],Value)||Value<10||Value>25) return false;
            S.Name=static_cast<int>(Name); S.Value=static_cast<int>(Value);
            int Total=0;
            for(const std::string& C:Split(Parts[1],'+')) {
                const size_t Eq=C.find('='); long long H=0,Nn=0; if(Eq==std::string::npos||!ParseLL(C.substr(0,Eq),H)||!ParseLL(C.substr(Eq+1),Nn)||H<0||H>=D->Hues||Nn<0||Nn>4) return false;
                S.Cost.push_back({static_cast<int>(H),static_cast<int>(Nn)}); Total+=static_cast<int>(Nn);
            }
            if(S.Cost.empty()||S.Cost.size()>2||Total<2||Total>4||S.Value!=Total*5+(S.Cost.size()==2?5:0)) return false;
            Fresh.Spirits.push_back(S);
        }
        if(Cur<0||Cur>=3+static_cast<long long>(Fresh.Spirits.size())) return false;
        Game::SetCabinetDifficulty(Diff);
        SessionSeed=static_cast<std::uint32_t>(Seed);
        Fresh.Rng.Seed(std::string(wardens::GameId())+":"+std::to_string(SessionSeed)+":"+Diff); Fresh.Rng.Discard(static_cast<std::uint64_t>(Drawn));
        Core=Fresh; Cursor=static_cast<int>(Cur); LastGained=0; WasPrev=WasNext=WasConfirm=false;
        return true;
    }
    std::uint32_t SeedAfterRestore(std::uint32_t) const override { return SessionSeed; }
    std::string HintLine() const {
        if(Core.Over) return Core.Won?"HINT The Wardens answered. Pad A or R lights the altar again.":"HINT The altar went dark. Pad A or R lights it again.";
        if(Option==1) return "HINT Practice: the blue mark shows the Wardens' counsel.";
        return "HINT Take a shard each round; spend matching shards to summon.";
    }
    std::string ActionCue() const { if(Core.Over) return "CUE Retry"; return Cursor<3?"CUE Take shard":(Core.Affordable(Cursor-3)?"CUE Summon":"CUE Need shards"); }
    std::string HowToLine() const override { return "HOW Take one of three altar shards each round, then spend matching shards to summon spirits before the rounds end."; }
    std::string KeyHint() const override { return "KEYS Left or Right picks a shard or spirit; A takes or summons."; }
    std::string ContrastMark() const override { return Core.Over?"MARK WAIT":"MARK ACT"; }
    void Render(Frame& F) const override {
        F.Clear(800,600,{20,12,26,255});
        F.AddText(28,20,std::string(Option==1?"WARDENS' GUIDE  [":"WARDENS' ACCORD  [")+CabinetDifficulty()+"]",{255,228,236,255},26);
        F.AddText(28,56,"SCORE: "+std::to_string(Core.Score)+"/"+std::to_string(Core.Diff?Core.Diff->Target:0)+"   ROUNDS: "+std::to_string(Core.Rounds),White,18);
        const std::pair<bool,int> Guide=(Option==1 && !Core.Over)?Core.DemoAction():std::pair<bool,int>{false,-1};
        const int GuideSlot=Guide.second<0?-1:(Guide.first?3+Guide.second:Guide.second);
        F.AddText(28,100,"ALTAR",{255,228,236,255},16);
        for(int I=0;I<3 && I<static_cast<int>(Core.Offer.size());++I) {
            const double X=60+I*90, Y=160;
            if(Cursor==I && !Core.Over) F.AddCircle(X,Y,36,{255,236,180,255});
            if(GuideSlot==I) F.AddCircle(X,Y,33,{120,225,255,255});
            F.AddCircle(X,Y,28,HueColor(Core.Offer[static_cast<size_t>(I)]));
            F.AddText(X-26,Y+36,wardens::HueName(Core.Offer[static_cast<size_t>(I)]),White,12);
        }
        F.AddText(28,230,"POUCH",{255,228,236,255},16);
        for(int H=0;H<Core.Hues();++H) { const double X=60+H*60; F.AddCircle(X,270,14,HueColor(H)); F.AddText(X-6,290,std::to_string(Core.Pouch[H]),White,14); }
        F.AddText(400,100,"SPIRITS",{255,228,236,255},16);
        for(int I=0;I<static_cast<int>(Core.Spirits.size());++I) {
            const wardens::Spirit& S=Core.Spirits[static_cast<size_t>(I)]; const double Y=130+I*70;
            const bool Ok=Core.Affordable(I);
            F.AddRect(400,Y,360,60,Ok?Color{44,36,60,255}:Color{30,24,40,255});
            if(Cursor==3+I && !Core.Over) F.AddRect(400,Y,360,4,{255,236,180,255});
            if(GuideSlot==3+I) F.AddRect(400,Y+56,360,4,{120,225,255,255});
            F.AddText(410,Y+6,wardens::SpiritName(S.Name),Ok?Color{255,236,180,255}:White,16);
            double CX=410; for(const auto& P:S.Cost) { for(int K=0;K<P.second;++K) { F.AddCircle(CX+8,Y+42,7,HueColor(P.first)); CX+=18; } CX+=8; }
            F.AddText(700,Y+20,"+"+std::to_string(S.Value),{120,225,255,255},18);
        }
        if(LastGained>0 && !Core.Over) F.AddText(300,160,"+"+std::to_string(LastGained),{255,236,180,255},24);
        if(Core.Over) F.AddText(60,330,Core.Won?"WON: THE WARDENS ANSWER":"LOST: THE ALTAR GOES DARK",{255,236,180,255},22);
        F.AddText(28,548,HintLine(),{255,236,180,255},16);
        F.AddText(28,528,HowToLine(),{255,236,180,255},14);
        DrawAccess(F,300,500,KeyHint(),ContrastMark());
        F.AddText(620,548,ActionCue(),{120,225,255,255},16);
    }
    Status GetStatus() const override {
        const std::string Sum=std::to_string(Core.Summoned.size());
        if(Core.Over) return {Core.Score,0,true,Core.Won,(Core.Won?"The Wardens answered; ":"The altar went dark; ")+std::string("pad A or R lights it again; summoned ")+Sum};
        return {Core.Score,1,false,false,"Rounds "+std::to_string(Core.Rounds)+"; summoned "+Sum};
    }
};
}} // daedalus::desktop
