// SPDX-License-Identifier: MIT
#include "../DaedalusLink/Source/DaedalusLink/Public/DaedalusGalleryMotifCore.h"
#include <iostream>
#include <set>
#include <vector>

namespace mo=daedalus::motif;
namespace
{
    int Checks=0,Failures=0;
    void Check(bool Pass,const char* Name)
    { ++Checks; if (!Pass) { ++Failures; std::cerr<<"FAIL: "<<Name<<'\n'; } }
    // Independent centred-coordinate group action rather than production row rotations.
    std::set<int> Orbit(int Cell,int Mode)
    {
        const int X=2*(Cell%8)-7,Y=2*(Cell/8)-7;
        std::set<int> Out;
        auto Add=[&](int A,int B) { Out.insert(((B+7)/2)*8+(A+7)/2); };
        Add(X,Y);
        if (Mode==1) Add(-X,Y);
        if (Mode==2) Add(X,-Y);
        if (Mode==3) Add(-X,-Y);
        if (Mode>=4)
        {
            const int Axes[4][2]={{X,Y},{-Y,X},{-X,-Y},{Y,-X}};
            for (const auto& P:Axes) { Add(P[0],P[1]); if (Mode==5) Add(-P[0],P[1]); }
        }
        return Out;
    }
    unsigned Checksum(const std::string& Prefix)
    {
        unsigned A=0,B=0;
        for (std::size_t I=0;I<Prefix.size();++I)
        { const auto C=static_cast<unsigned char>(Prefix[I]); A+=C; B+=static_cast<unsigned>(Prefix.size()-I)*C; }
        return ((B%255u)<<8)|(A%255u);
    }
    bool Same(const mo::Document& A,const mo::Document& B)
    { return A.Id==B.Id && A.Parent==B.Parent && A.Pixels==B.Pixels; }
    std::string ReplaceOnce(std::string Text,const std::string& Before,const std::string& After)
    { const auto At=Text.find(Before); if (At==std::string::npos) return {}; Text.replace(At,Before.size(),After); return Text; }
}
int main()
{
    bool AllOrbits=true,Paints=true;
    for (int Mode=0;Mode<6;++Mode) for (int Cell=0;Cell<64;++Cell)
    {
        mo::Orbit Targets; const auto Expected=Orbit(Cell,Mode);
        const bool Valid=mo::OrbitFor(Cell,static_cast<mo::Symmetry>(Mode),Targets);
        if (!Valid || Targets.Count>8) { AllOrbits=false; Paints=false; continue; }
        const std::set<int> Actual(Targets.Cells.begin(),Targets.Cells.begin()+Targets.Count);
        AllOrbits=AllOrbits && Valid && Targets.Count<=8 && Actual==Expected && Actual.size()==Targets.Count;
        for (std::size_t I=1;I<Targets.Count;++I) AllOrbits=AllOrbits && Targets.Cells[I-1]<Targets.Cells[I];
        mo::Session Run; Run.Begin(); Run.Paint(Cell,5,static_cast<mo::Symmetry>(Mode));
        for (int I=0;I<64;++I) Paints=Paints && Run.Canvas()[I]==(Expected.count(I)?5:0);
    }
    Check(AllOrbits,"all384 individual group orbits match independent centred-coordinate transforms");
    Check(Paints,"each symmetry stroke changes exactly its orbit");
    mo::Orbit Untouched; Untouched.Cells[0]=99; Untouched.Count=1;
    Check(!mo::OrbitFor(-1,mo::Symmetry::None,Untouched) && !mo::OrbitFor(64,mo::Symmetry::None,Untouched) &&
        !mo::OrbitFor(0,static_cast<mo::Symmetry>(255),Untouched) && Untouched.Count==1 && Untouched.Cells[0]==99,
        "invalid orbit input preserves caller output");
    Check(Orbit(0,5).size()==4 && Orbit(1,5).size()==8,"D4 deduplicates diagonal orbits while retaining full off-diagonal orbit");
    mo::Session Run;
    Check(!Run.Active() && !Run.Paint(0,1,mo::Symmetry::None) && !Run.Undo() && !Run.Redo() && !Run.Clear(),
        "inactive drawing refuses edits");
    Check(Run.Begin() && mo::IsBlank(Run.Canvas()) && Run.UndoCount()==0 && Run.RedoCount()==0,"blank initial drawing");
    Check(Run.Paint(0,1,mo::Symmetry::QuarterTurn) && Run.UndoCount()==1 &&
        !Run.Paint(0,1,mo::Symmetry::QuarterTurn) && Run.UndoCount()==1,"one orbit is one edit; identical paint does not spend history");
    const auto FourCorners=Run.Canvas();
    Check(Run.Undo() && mo::IsBlank(Run.Canvas()) && Run.RedoCount()==1 && Run.Redo() &&
        Run.Canvas()==FourCorners && Run.RedoCount()==0,"Undo and Redo restore complete stroke snapshots");
    Run.Undo();
    Check(!Run.Paint(0,0,mo::Symmetry::None) && Run.RedoCount()==1 && Run.Paint(9,3,mo::Symmetry::MirrorColumns) &&
        Run.RedoCount()==0,"a no-op retains Redo while a real new stroke branches history");
    const auto Before=Run.Canvas(); const auto Count=Run.UndoCount();
    Check(!Run.Paint(0,-1,mo::Symmetry::None) && !Run.Paint(0,8,mo::Symmetry::None) &&
        !Run.Paint(0,1,static_cast<mo::Symmetry>(8)) && Run.Canvas()==Before && Run.UndoCount()==Count,
        "invalid brush input retains drawing and history");
    mo::Image Bad=Before; Bad[33]=8;
    Check(!Run.Begin(Bad) && !Run.Replace(Bad) && Run.Canvas()==Before && Run.UndoCount()==Count,
        "invalid image cannot reset or replace a drawing");
    Check(Run.Begin(Run.Canvas()) && Run.Canvas()==Before && Run.UndoCount()==0 && Run.RedoCount()==0,
        "self-aliased setup copies before clearing history");
    Check(Run.Clear() && mo::IsBlank(Run.Canvas()) && Run.Undo() && Run.Canvas()==Before,"clear remains undoable at model layer");
    Run.Begin(); std::vector<mo::Image> Past;
    for (int I=0;I<70;++I)
    { Past.push_back(Run.Canvas()); Run.Paint(0,1+I%2,mo::Symmetry::None); if (Past.size()>64) Past.erase(Past.begin()); }
    const auto End=Run.Canvas(); bool History=Run.UndoCount()==64;
    while (!Past.empty()) { History=History && Run.Undo() && Run.Canvas()==Past.back(); Past.pop_back(); }
    Check(History && Run.UndoCount()==0 && Run.RedoCount()==64 && Run.Canvas()[0]==2 && !Run.Undo(),"exact latest64 Undo boundary");
    for (int I=0;I<64;++I) History=History && Run.Redo();
    Check(History && Run.Canvas()==End && Run.RedoCount()==0 && Run.UndoCount()==64 && !Run.Redo(),"exact64 Redo boundary");
    mo::Image Pixels{}; for (int I=0;I<64;++I) Pixels[I]=static_cast<std::uint8_t>(I%8);
    const auto Pattern=mo::EncodePattern(Pixels); mo::Image Decoded{};
    Check(Pattern.size()==74 && mo::DecodePattern(Pattern,Decoded) && Decoded==Pixels &&
        std::stoul(Pattern.substr(70),nullptr,16)==Checksum(Pattern.substr(0,69)),"versioned pattern round-trip and independent weighted Fletcher calculation");
    bool Corruption=true; mo::Image Sentinel{}; Sentinel.fill(7);
    for (int I=0;I<64;++I)
    {
        auto Broken=Pattern; Broken[5+I]=static_cast<char>('0'+((Pixels[I]+1)%8)); Decoded=Sentinel;
        Corruption=Corruption && !mo::DecodePattern(Broken,Decoded) && Decoded==Sentinel;
    }
    Check(Corruption,"every single palette-digit change is refused without partial decode");
    Decoded=Sentinel;
    Check(!mo::DecodePattern(Pattern.substr(1),Decoded) && !mo::DecodePattern(Pattern+"x",Decoded) &&
        !mo::DecodePattern(ReplaceOnce(Pattern,"DGM1:","DGM2:"),Decoded) && Decoded==Sentinel && mo::EncodePattern(Bad).empty(),
        "length, version and palette guards preserve existing image");
    const std::string Id="0123456789abcdef0123456789abcdef",Parent="fedcba9876543210fedcba9876543210";
    Check(mo::ValidId(Id) && mo::CanonicalId("0123456789ABCDEF0123456789ABCDEF")==Id &&
        !mo::ValidId(std::string(32,'0')) && !mo::ValidId("../0123456789abcdef0123456789abcde") && !mo::ValidId(Id+"0"),
        "fixed nonzero hex identities normalize case and cannot contain paths");
    mo::Document Doc{Id,Parent,Pixels},Loaded;
    const auto Wire=mo::EncodeDocument(Doc);
    Check(!Wire.empty() && Wire.size()<=512 && mo::DecodeDocument(Wire,Loaded) && Same(Doc,Loaded),"bounded four-line export document round-trip");
    auto Windows=std::string("\xEF\xBB\xBF");
    for (char C:Wire) { if (C=='\n') Windows+='\r'; Windows+=C; }
    Windows.resize(Windows.size()-2);
    Check(mo::DecodeDocument(Windows,Loaded) && Same(Doc,Loaded),"UTF8 BOM, CRLF and missing final newline are deliberately accepted");
    const auto Upper=ReplaceOnce(Wire,"id:"+Id,"id:0123456789ABCDEF0123456789ABCDEF");
    Check(mo::DecodeDocument(Upper,Loaded) && Loaded.Id==Id,"parsed identities canonicalize without changing pixels");
    std::vector<std::string> Invalid={Wire+"extra:payload\n",Wire+"\n",Wire.substr(0,Wire.find("pattern:")),
        ReplaceOnce(Wire,"DGM-DOCUMENT 1","DGM-DOCUMENT 2"),ReplaceOnce(Wire,"id:"+Id,"id:"+std::string(32,'0')),
        ReplaceOnce(Wire,"parent:"+Parent,"parent:"+Id),ReplaceOnce(Wire,"parent:"+Parent,"parent:"),
        ReplaceOnce(Wire,"parent:"+Parent,"id:"+Parent),ReplaceOnce(Wire,Pattern,Pattern+"x"),std::string(513,'x')};
    auto Broken=Wire; Broken[Broken.find("pattern:")+8+5]='8'; Invalid.push_back(Broken);
    Broken=Wire; Broken[Broken.find("id:")+3]='\0'; Invalid.push_back(Broken);
    const mo::Document Old{Parent,Id,Sentinel}; bool Atomic=true;
    for (const auto& Text:Invalid) { Loaded=Old; Atomic=Atomic && !mo::DecodeDocument(Text,Loaded) && Same(Loaded,Old); }
    Check(Atomic,"malformed field/version/identity/palette/payload/byte-cap inputs retain full document");
    auto Self=Doc; Self.Parent="0123456789ABCDEF0123456789ABCDEF";
    Check(mo::EncodeDocument(Self).empty(),"case-insensitive self-parent lineage is refused");
    auto Root=Doc; Root.Parent.clear();
    Check(mo::DecodeDocument(mo::EncodeDocument(Root),Loaded) && Loaded.Parent.empty(),"root exports use explicit parent dash");
    Run.Begin(Pixels); const auto Baseline=Run.Canvas(); Run.Paint(0,7,mo::Symmetry::None);
    Check(Run.Canvas()!=Baseline && Run.Undo() && Run.Canvas()==Baseline && Run.Redo() && Run.Canvas()!=Baseline,
        "exact baseline comparison makes Undo to an export clean again");
    const auto Draft=Run.Canvas(); const auto DraftUndo=Run.UndoCount(); auto Candidate=Run; Candidate.Replace(mo::Image{});
    Check(Run.Canvas()==Draft && Run.UndoCount()==DraftUndo && Candidate.Canvas()!=Draft,
        "prepared model transaction can be discarded on IO failure without touching live draft");
    Run=Candidate;
    Check(mo::IsBlank(Run.Canvas()) && Run.Undo() && Run.Canvas()==Draft,"accepted replacement commits once and remains undoable");
    std::cout<<Checks<<" checks, "<<Failures<<" failed;384 independent symmetry orbits, codec refusals and64-step history\n";
    return Failures?1:0;
}
