// SPDX-License-Identifier: MIT
#include "../DaedalusLink/Source/DaedalusLink/Public/DaedalusBricksBlueprintPrintCore.h"
#include <algorithm>
#include <array>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>

namespace print=daedalus::blueprintprint;
namespace
{
    int Checks=0,Failures=0;
    void Check(bool Passed,const char* Name)
    { ++Checks; if (!Passed) { ++Failures; std::cerr<<"FAIL: "<<Name<<'\n'; } }
    std::string IdFor(int Number)
    { const char* Hex="0123456789abcdef"; std::string Out(32,'0'); Out[30]=Hex[(Number>>4)&15]; Out[31]=Hex[Number&15]; return Out; }
    std::string Digits(const daedalus::skyline::Grid& Canvas)
    { std::string Out; for (auto Height:Canvas) Out+=static_cast<char>('0'+Height); return Out; }
    std::string Json(const std::string& Text)
    {
        const char* Hex="0123456789abcdef"; std::string Out="\"";
        for (unsigned char C:Text)
        {
            if (C=='\"' || C=='\\') { Out+='\\'; Out+=static_cast<char>(C); }
            else if (C<32) { Out+="\\u00"; Out+=Hex[C>>4]; Out+=Hex[C&15]; }
            else Out+=static_cast<char>(C);
        }
        return Out+'\"';
    }
    struct Case
    {
        std::string Kind; int Rule=0,Mask=0; daedalus::skyline::Grid Grid{};
        print::Identity Identity; std::string Svg;
    };
    bool Different(const std::array<std::uint8_t,4>& A,const std::array<std::uint8_t,4>& B)
    { for (int I=0;I<4;++I) if (A[I]==B[I]) return false; return true; }
    std::array<std::vector<daedalus::skyline::Grid>,3> Alternatives()
    {
        std::vector<std::array<std::uint8_t,4>> Rows; std::array<std::uint8_t,4> Row{{1,2,3,4}};
        do { Rows.push_back(Row); } while (std::next_permutation(Row.begin(),Row.end()));
        std::array<std::vector<daedalus::skyline::Grid>,3> Out;
        for (const auto& A:Rows) for (const auto& B:Rows) if (Different(A,B))
            for (const auto& C:Rows) if (Different(A,C) && Different(B,C))
                for (const auto& D:Rows) if (Different(A,D) && Different(B,D) && Different(C,D))
                {
                    daedalus::skyline::Grid Canvas{};
                    for (int I=0;I<4;++I) { Canvas[I]=A[I]; Canvas[4+I]=B[I]; Canvas[8+I]=C[I]; Canvas[12+I]=D[I]; }
                    for (int Rule=0;Rule<3;++Rule)
                    { daedalus::skyline::Evaluation View; if (daedalus::skyline::Evaluate(Rule,Canvas,View) && View.Complete) Out[Rule].push_back(Canvas); }
                }
        return Out;
    }
    bool Write(const std::filesystem::path& Path,const std::string& Bytes)
    {
        if (std::filesystem::exists(Path)) return false;
        std::ofstream File(Path,std::ios::binary|std::ios::out); if (!File) return false;
        File.write(Bytes.data(),static_cast<std::streamsize>(Bytes.size())); File.close(); return !File.fail();
    }
}
int main(int Argc,char** Argv)
{
    if (Argc!=2 || !std::filesystem::is_directory(std::filesystem::path(Argv[1])))
    { std::cerr<<"Pass the fresh runner check directory.\n"; return 2; }
    const std::filesystem::path Directory(Argv[1]);
    for (const char* Name:{"bridge.svg","skyline.svg","cases.json"}) if (std::filesystem::exists(Directory/Name))
    { std::cerr<<"Refusing to replace existing artifact.\n"; return 2; }
    const print::Identity Good{IdFor(1),""}; std::string Out;
    Check(print::MaxSvgBytes==65536 && print::ValidId(IdFor(1)) && print::ValidId("0123456789abcdef0123456789abcdef"),"strict artifact identity accepts nonzero lowercase hexadecimal IDs");
    std::vector<std::string> BadIds={"",std::string(31,'a'),std::string(33,'a'),std::string(32,'0'),std::string(32,'A'),std::string(32,'g')};
    auto Slash=std::string(32,'a'); Slash[0]='/'; BadIds.push_back(Slash); auto Nul=IdFor(1); Nul[5]='\0'; BadIds.push_back(Nul);
    bool Ids=true; for (const auto& Id:BadIds) Ids=!print::ValidId(Id) && Ids;
    Check(Ids,"uppercase, zero, path, NUL and wrong-width IDs are refused");
    const std::string Sentinel("kept\0output",11); bool Atomic=true;
    for (const auto& Id:BadIds)
    {
        Out=Sentinel; Atomic=!print::RenderBridgeSvg(0,0,{Id,""},Out) && Out==Sentinel && Atomic;
        Atomic=!print::RenderSkylineSvg(2,{}, {Id,""},Out) && Out==Sentinel && Atomic;
    }
    for (const auto& Parent:std::vector<std::string>{IdFor(1),std::string(32,'0'),std::string(32,'A'),"not-an-id"})
    {
        Out=Sentinel; Atomic=!print::RenderBridgeSvg(0,0,{IdFor(1),Parent},Out) && Out==Sentinel && Atomic;
        Atomic=!print::RenderSkylineSvg(2,{}, {IdFor(1),Parent},Out) && Out==Sentinel && Atomic;
    }
    Check(Atomic,"identity/lineage refusals preserve exact binary output for both renderers");
    Out=Sentinel;
    Check(!print::RenderBridgeSvg(-1,0,Good,Out) && !print::RenderBridgeSvg(3,0,Good,Out) && !print::RenderBridgeSvg(0,-1,Good,Out) &&
        !print::RenderBridgeSvg(0,4096,Good,Out) && !print::RenderBridgeSvg(1,1<<2,Good,Out) && !print::RenderBridgeSvg(2,1<<8,Good,Out) &&
        !print::RenderBridgeSvg(0,4095,Good,Out) && Out==Sentinel,"invalid, closed and over-allowance bridge snapshots refuse atomically");
    auto BadHeight=daedalus::skyline::Blueprints[0].Givens; BadHeight[1]=5;
    auto WrongGiven=daedalus::skyline::Blueprints[0].Givens; WrongGiven[0]=2;
    auto MissingGiven=daedalus::skyline::Blueprints[0].Givens; MissingGiven[15]=0;
    Check(!print::RenderSkylineSvg(-1,{},Good,Out) && !print::RenderSkylineSvg(3,{},Good,Out) && !print::RenderSkylineSvg(0,BadHeight,Good,Out) &&
        !print::RenderSkylineSvg(0,WrongGiven,Good,Out) && !print::RenderSkylineSvg(0,MissingGiven,Good,Out) && Out==Sentinel,
        "invalid heights/rules and missing or wrong skyline givens refuse atomically");
    std::vector<Case> Cases;
    const auto AddBridge=[&](int Rule,int Mask)
    { Case Value; Value.Kind="bridge"; Value.Rule=Rule; Value.Mask=Mask; Cases.push_back(Value); };
    const auto AddSkyline=[&](int Rule,const daedalus::skyline::Grid& Canvas)
    { Case Value; Value.Kind="skyline"; Value.Rule=Rule; Value.Grid=Canvas; Cases.push_back(Value); };
    AddBridge(0,0); AddBridge(0,1010); AddBridge(0,1011); AddBridge(0,(1<<0)|(1<<2)|(1<<6)|(1<<7));
    AddBridge(1,0); AddBridge(1,1011); AddBridge(2,0); AddBridge(2,766);
    for (int Rule=0;Rule<3;++Rule) AddSkyline(Rule,daedalus::skyline::Blueprints[Rule].Givens);
    daedalus::skyline::Grid Contradiction{}; Contradiction[0]=2; Contradiction[1]=2; Contradiction[2]=1; Contradiction[3]=4; AddSkyline(2,Contradiction);
    const auto Solutions=Alternatives(); bool All=true;
    for (int Rule=0;Rule<3;++Rule) for (const auto& Canvas:Solutions[Rule]) AddSkyline(Rule,Canvas);
    Check(Solutions[0].size()==1 && Solutions[1].size()==2 && Solutions[2].size()==3,"all six valid skyline alternatives are included for independent XML validation");
    daedalus::skyline::Session Skyline; Skyline.Begin();
    for (int I=0;I<16;++I) if (!daedalus::skyline::Blueprints[0].Givens[I]) Skyline.SetHeight(I,Solutions[0].front()[I]);
    const bool Ever=Skyline.EverCompleted(0); Skyline.Undo(); AddSkyline(0,Skyline.Canvas());
    daedalus::skyline::Evaluation Current;
    Check(Ever && Skyline.View(Current) && !Current.Complete,"after-completion undo fixture has ever-study information but an incomplete current snapshot");
    std::size_t Maximum=0; std::string ExampleBridge,ExampleSkyline,BridgeId,SkylineId;
    for (std::size_t I=0;I<Cases.size();++I)
    {
        auto& Value=Cases[I]; Value.Identity={IdFor(static_cast<int>(I)+1),I?IdFor(250):""}; std::string Repeat;
        const bool Accepted=Value.Kind=="bridge"?print::RenderBridgeSvg(Value.Rule,Value.Mask,Value.Identity,Value.Svg):print::RenderSkylineSvg(Value.Rule,Value.Grid,Value.Identity,Value.Svg);
        const bool Again=Value.Kind=="bridge"?print::RenderBridgeSvg(Value.Rule,Value.Mask,Value.Identity,Repeat):print::RenderSkylineSvg(Value.Rule,Value.Grid,Value.Identity,Repeat);
        const bool Ascii=std::all_of(Value.Svg.begin(),Value.Svg.end(),[](unsigned char C) { return (C>=32 && C<=126) || C=='\n'; });
        All=Accepted && Again && Value.Svg==Repeat && !Value.Svg.empty() && Value.Svg.size()<=print::MaxSvgBytes && Ascii && All;
        Maximum=std::max(Maximum,Value.Svg.size());
        if (Value.Kind=="bridge" && Value.Rule==0 && Value.Mask==1010) { ExampleBridge=Value.Svg; BridgeId=Value.Identity.Id; }
        if (Value.Kind=="skyline" && Value.Rule==2 && Value.Grid==Contradiction) { ExampleSkyline=Value.Svg; SkylineId=Value.Identity.Id; }
    }
    Check(All && Cases.size()==19,"nineteen accepted current snapshots are deterministic nonempty ASCII within64KiB");
    std::string Partial,Complete;
    Check(print::RenderBridgeSvg(0,1010,Good,Partial) && print::RenderBridgeSvg(0,1011,Good,Complete) && Partial!=Complete,
        "different bridge snapshots change the artifact with identical identity");
    Check(print::RenderSkylineSvg(2,{},Good,Partial) && print::RenderSkylineSvg(2,Contradiction,Good,Complete) && Partial!=Complete,
        "editable skyline contradictions produce a distinct artifact with identical identity");
    Check(print::RenderBridgeSvg(0,0,{IdFor(3),IdFor(2)},Out) && Out!=Cases.front().Svg,"valid parent lineage is descriptive and changes the artifact");
    std::string Report="{\"Schema\":1,\"MaxSvgBytes\":"+std::to_string(print::MaxSvgBytes)+",\"MaximumObserved\":"+std::to_string(Maximum)+",\"Examples\":{\"bridge.svg\":"+Json(BridgeId)+",\"skyline.svg\":"+Json(SkylineId)+"},\"Cases\":[";
    for (std::size_t I=0;I<Cases.size();++I)
    {
        const auto& Value=Cases[I]; if (I) Report+=',';
        Report+="{\"Kind\":"+Json(Value.Kind)+",\"Rule\":"+std::to_string(Value.Rule)+",\"Mask\":"+std::to_string(Value.Mask)+",\"Heights\":"+Json(Digits(Value.Grid))+
            ",\"Id\":"+Json(Value.Identity.Id)+",\"Parent\":"+Json(Value.Identity.Parent)+",\"Svg\":"+Json(Value.Svg)+"}";
    }
    Report+="]}\n";
    Check(Failures==0 && !ExampleBridge.empty() && !ExampleSkyline.empty() && Write(Directory/"bridge.svg",ExampleBridge) &&
        Write(Directory/"skyline.svg",ExampleSkyline) && Write(Directory/"cases.json",Report),"fresh example SVGs and bounded JSON evidence are written without replacing existing files");
    std::cout<<Checks<<" checks, "<<Failures<<" failed;19 SVG snapshots;maximum "<<Maximum<<" bytes. Independent XML verifier follows.\n";
    return Failures?1:0;
}
