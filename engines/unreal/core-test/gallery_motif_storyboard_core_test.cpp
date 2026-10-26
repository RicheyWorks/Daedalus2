// SPDX-License-Identifier: MIT
#include "../DaedalusLink/Source/DaedalusLink/Public/DaedalusGalleryMotifStoryboardCore.h"
#include <algorithm>
#include <array>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>

namespace sheet=daedalus::storyboard;
namespace motif=daedalus::motif;
namespace flip=daedalus::flipbook;
namespace
{
    int Checks=0,Failures=0;
    void Check(bool Passed,const char* Name)
    { ++Checks; if (!Passed) { ++Failures; std::cerr<<"FAIL: "<<Name<<'\n'; } }
    std::string IdFor(int Value)
    { const char* Hex="0123456789abcdef"; std::string Out(32,'0'); Out[30]=Hex[(Value>>4)&15]; Out[31]=Hex[Value&15]; return Out; }
    std::array<motif::Document,4> Documents()
    {
        std::array<motif::Document,4> Out;
        for (int Frame=0;Frame<4;++Frame)
        {
            Out[Frame].Id=IdFor(10+Frame);
            for (int Row=0;Row<8;++Row) for (int Column=0;Column<8;++Column)
                Out[Frame].Pixels[Row*8+Column]=static_cast<std::uint8_t>((Frame*3+Row+2*Column)%8);
        }
        Out[0].Parent=IdFor(255); Out[2].Parent=Out[3].Id; Out[3].Parent=Out[0].Id; return Out;
    }
    bool Same(const flip::Player& Book,const std::array<motif::Document,4>& Docs)
    {
        for (int I=0;I<Book.Count();++I)
        { const auto* Frame=Book.Frame(I); if (!Frame || Frame->Id!=Docs[I].Id || Frame->Parent!=Docs[I].Parent || Frame->Pixels!=Docs[I].Pixels) return false; }
        return true;
    }
    bool Ascii(const std::string& Svg)
    { return !Svg.empty() && Svg.size()<=sheet::MaxSvgBytes && std::all_of(Svg.begin(),Svg.end(),[](unsigned char C){return (C>=32 && C<=126) || C=='\n';}); }
    std::string Digits(const motif::Image& Pixels)
    { std::string Out; for (auto Pixel:Pixels) Out+=static_cast<char>('0'+Pixel); return Out; }
    std::string Json(const std::string& Value)
    {
        const char* Hex="0123456789abcdef"; std::string Out="\"";
        for (unsigned char C:Value)
        {
            if (C=='\"' || C=='\\') { Out+='\\'; Out+=static_cast<char>(C); }
            else if (C<32) { Out+="\\u00"; Out+=Hex[C>>4]; Out+=Hex[C&15]; }
            else Out+=static_cast<char>(C);
        }
        return Out+'\"';
    }
    bool Write(const std::filesystem::path& Path,const std::string& Value)
    {
        if (std::filesystem::exists(Path)) return false;
        std::ofstream File(Path,std::ios::binary|std::ios::out); if (!File) return false;
        File.write(Value.data(),static_cast<std::streamsize>(Value.size())); File.close(); return !File.fail();
    }
    struct Case { flip::Player Book; sheet::Palette Colours; sheet::Identity Identity; std::string Svg; };
}
int main(int Argc,char** Argv)
{
    if (Argc!=2 || !std::filesystem::is_directory(std::filesystem::path(Argv[1]))) { std::cerr<<"Pass the fresh runner check directory.\n"; return 2; }
    const std::filesystem::path Directory(Argv[1]);
    for (const char* Name:{"two_frames.svg","four_frames_reverse.svg","cases.json"}) if (std::filesystem::exists(Directory/Name))
    { std::cerr<<"Refusing to replace existing artifact.\n"; return 2; }
    const sheet::Palette Colours{{"#F2f7Fb","#101820","#Ea6a4A","#F0c43C","#168A6d","#2B71d8","#9A54c4","#23a7A9"}};
    const auto Docs=Documents(); const sheet::Identity Identity{IdFor(40),""}; const std::string Sentinel("kept\0output",11); std::string Out=Sentinel;
    flip::Player Empty;
    Check(sheet::MaxSvgBytes==65536 && !sheet::RenderSvg(Empty,Colours,Identity,Out) && Out==Sentinel,"inactive books refuse atomically at the64KiB artifact boundary");
    std::array<flip::Player,3> Books; for (int Count=2;Count<=4;++Count) Books[Count-2].Capture(Docs,Count);
    bool Ids=true; std::vector<sheet::Identity> Invalid={{"",""},{std::string(32,'0'),""},{std::string(32,'A'),""},{std::string(31,'a'),""},
        {IdFor(40),IdFor(40)},{IdFor(40),std::string(32,'A')},{IdFor(40),std::string(32,'0')}};
    auto Nul=IdFor(40); Nul[3]='\0'; Invalid.push_back({Nul,""}); auto Injection=IdFor(40); Injection[3]='\"'; Invalid.push_back({Injection,""});
    for (const auto& Bad:Invalid) { Out=Sentinel; Ids=!sheet::RenderSvg(Books[0],Colours,Bad,Out) && Out==Sentinel && Ids; }
    Check(Ids,"invalid/noncanonical artifact identity and parent injections preserve exact binary output");
    std::vector<std::string> BadColours={"","123456","#12345","#12345678","#gg0000","url(x)","#12\"456","#12<456"};
    auto NulColour=std::string("#123456"); NulColour[4]='\0'; BadColours.push_back(NulColour); auto HighColour=std::string("#123456"); HighColour[4]=static_cast<char>(0xe9); BadColours.push_back(HighColour);
    bool Palettes=true;
    for (int Slot=0;Slot<8;++Slot) for (const auto& Bad:BadColours)
    { auto Palette=Colours; Palette[Slot]=Bad; Out=Sentinel; Palettes=!sheet::RenderSvg(Books[2],Palette,Identity,Out) && Out==Sentinel && Palettes; }
    Check(Palettes,"every palette slot rejects wrong-width/nonhex/alpha/URL/quote/NUL/high-byte content atomically");
    std::vector<Case> Cases;
    for (int Count=2;Count<=4;++Count)
    {
        Case Value{Books[Count-2],Colours,{IdFor(38+Count),Count==2?std::string{}:IdFor(200)},""}; std::string Again;
        const bool Rendered=sheet::RenderSvg(Value.Book,Value.Colours,Value.Identity,Value.Svg);
        const bool Repeated=sheet::RenderSvg(Value.Book,Value.Colours,Value.Identity,Again);
        Check(Rendered && Repeated && Value.Svg==Again && Ascii(Value.Svg) && Same(Value.Book,Docs),
            Count==2?"two-frame sheet is deterministic bounded ASCII with unchanged original documents":Count==3?"three-frame sheet is deterministic bounded ASCII with unchanged original documents":"four-frame sheet is deterministic bounded ASCII with all256 pixel samples available");
        Cases.push_back(Value);
    }
    flip::Player Moving=Books[2]; Moving.Step(-1); Moving.Reverse(); Moving.CycleSpeed(); Moving.TogglePlay(); Moving.Advance(0.125);
    Case Playing{Moving,Colours,{IdFor(43),IdFor(200)},""};
    const bool RenderedPlaying=sheet::RenderSvg(Moving,Colours,Playing.Identity,Playing.Svg);
    Check(RenderedPlaying && Moving.Index()==3 && Moving.Fps()==4 && Moving.Direction()==-1 && Moving.Playing() && Same(Moving,Docs) &&
        Moving.Advance(0.125) && Moving.Index()==2,"rendering a playing reversed capture records state without consuming its half-frame phase");
    std::string PausedSameIdentity;
    Check(sheet::RenderSvg(Books[2],Colours,Playing.Identity,PausedSameIdentity) && PausedSameIdentity!=Playing.Svg,
        "current/speed/direction/playing capture metadata change the static artifact without replacing frame documents");
    Cases.push_back(Playing);
    auto OtherColours=Colours; OtherColours[7]="#aBcDeF"; std::string OriginalPalette,OtherPalette;
    Check(sheet::RenderSvg(Books[1],Colours,Identity,OriginalPalette) && sheet::RenderSvg(Books[1],OtherColours,Identity,OtherPalette) &&
        OriginalPalette!=OtherPalette && Same(Books[1],Docs),"host palette changes produce distinct sheets while mixed-case strings and source indices stay intact");
    Cases.push_back({Books[1],OtherColours,{IdFor(44),IdFor(200)},""});
    auto IdenticalDocs=Docs; for (auto& Frame:IdenticalDocs) Frame.Pixels=Docs[0].Pixels; flip::Player Identical; Identical.Capture(IdenticalDocs,3);
    sheet::Palette DuplicateColours; DuplicateColours.fill("#Aa00Ff");
    Check(sheet::RenderSvg(Identical,DuplicateColours,Identity,Out) && Ascii(Out) && Same(Identical,IdenticalDocs),
        "equal images under distinct DGM IDs and repeated host palette colours remain valid separate cards");
    Cases.push_back({Identical,DuplicateColours,{IdFor(45),IdFor(200)},""});
    const sheet::Identity SharedText{Docs[0].Id,Docs[1].Id};
    Check(sheet::RenderSvg(Books[0],Colours,SharedText,Out) && Same(Books[0],Docs),
        "artifact IDs may share text with DGM IDs because their metadata roles are separate without a new lineage policy");
    Cases.push_back({Books[0],Colours,SharedText,""});
    flip::Player Live=Playing.Book; const flip::Player Captured=Live; std::string CapturedBefore,CapturedAfter,LiveAfter;
    const bool Before=sheet::RenderSvg(Captured,Colours,Identity,CapturedBefore); Live.Step(1);
    Check(Before && sheet::RenderSvg(Captured,Colours,Identity,CapturedAfter) && CapturedBefore==CapturedAfter &&
        sheet::RenderSvg(Live,Colours,Identity,LiveAfter) && LiveAfter!=CapturedAfter,"a by-value captured book prints unchanged after the live source controls advance");
    std::string WithoutParent,WithParent;
    Check(sheet::RenderSvg(Books[1],Colours,{IdFor(90),""},WithoutParent) && sheet::RenderSvg(Books[1],Colours,{IdFor(90),IdFor(91)},WithParent) &&
        WithoutParent!=WithParent && Same(Books[1],Docs),"artifact parent changes never rewrite per-frame DGM lineage or pixel data");
    Cases.push_back({Books[1],Colours,{IdFor(90),IdFor(91)},""});
    bool All=true; std::size_t Maximum=0;
    for (auto& Value:Cases)
    { const bool Rendered=sheet::RenderSvg(Value.Book,Value.Colours,Value.Identity,Value.Svg); All=Rendered && Ascii(Value.Svg) && All; Maximum=std::max(Maximum,Value.Svg.size()); }
    std::string Report="{\"Schema\":1,\"MaxSvgBytes\":"+std::to_string(sheet::MaxSvgBytes)+",\"MaximumObserved\":"+std::to_string(Maximum)+",\"Examples\":{\"two_frames.svg\":"+Json(Cases[0].Identity.Id)+",\"four_frames_reverse.svg\":"+Json(Playing.Identity.Id)+"},\"Cases\":[";
    for (std::size_t I=0;I<Cases.size();++I)
    {
        const auto& Value=Cases[I]; if (I) Report+=',';
        Report+="{\"Id\":"+Json(Value.Identity.Id)+",\"Parent\":"+Json(Value.Identity.Parent)+",\"Count\":"+std::to_string(Value.Book.Count())+",\"Index\":"+std::to_string(Value.Book.Index())+
            ",\"Fps\":"+std::to_string(Value.Book.Fps())+",\"Direction\":"+std::to_string(Value.Book.Direction())+",\"Playing\":"+(Value.Book.Playing()?"true":"false")+",\"Palette\":[";
        for (int Colour=0;Colour<8;++Colour) { if (Colour) Report+=','; Report+=Json(Value.Colours[Colour]); }
        Report+="],\"Frames\":[";
        for (int Frame=0;Frame<Value.Book.Count();++Frame)
        { const auto& Document=*Value.Book.Frame(Frame); if (Frame) Report+=','; Report+="{\"Id\":"+Json(Document.Id)+",\"Parent\":"+Json(Document.Parent)+",\"Pixels\":"+Json(Digits(Document.Pixels))+"}"; }
        Report+="],\"Svg\":"+Json(Value.Svg)+"}";
    }
    Report+="]}\n";
    Check(Failures==0 && All && Cases.size()==8 && Write(Directory/"two_frames.svg",Cases[0].Svg) && Write(Directory/"four_frames_reverse.svg",Playing.Svg) &&
        Write(Directory/"cases.json",Report),"eight static capture fixtures and two example sheets are written only to fresh artifact paths");
    std::cout<<Checks<<" checks, "<<Failures<<" failed;8 static sheets;maximum "<<Maximum<<" bytes;independent XML verifier follows;visuals untested\n";
    return Failures?1:0;
}
