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
    // Independent union-find over original right/down equal-colour neighbours.
    // Only the CLICKED component is selected; its cells' group images are then
    // unioned. Symmetry copies are never additional component-search seeds.
    std::set<int> FillSelection(const mo::Image& Source,int Cell,int Mode)
    {
        std::array<int,64> Parents{}; for (int I=0;I<64;++I) Parents[I]=I;
        auto Root=[&](int At) { while (Parents[At]!=At) At=Parents[At]; return At; };
        for (int At=0;At<64;++At)
        {
            if (At%8<7 && Source[At]==Source[At+1]) Parents[Root(At+1)]=Root(At);
            if (At/8<7 && Source[At]==Source[At+8]) Parents[Root(At+8)]=Root(At);
        }
        const int Component=Root(Cell); std::set<int> Out;
        for (int At=0;At<64;++At) if (Root(At)==Component)
        { const auto Copies=Orbit(At,Mode); Out.insert(Copies.begin(),Copies.end()); }
        return Out;
    }
    mo::Image Transformed(const mo::Image& Source,int Kind)
    {
        mo::Image Out{};
        for (int At=0;At<64;++At)
        {
            const int X=2*(At%8)-7,Y=2*(At/8)-7;
            const int NextX=Kind==0?-Y:Kind==1?-X:X,NextY=Kind==0?X:Kind==2?-Y:Y;
            Out[((NextY+7)/2)*8+(NextX+7)/2]=Source[At];
        }
        return Out;
    }
    std::array<int,8> Histogram(const mo::Image& Pixels)
    { std::array<int,8> Counts{}; for (auto Colour:Pixels) ++Counts[Colour]; return Counts; }
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
    Check(!Run.Active() && !Run.Paint(0,1,mo::Symmetry::None) && !Run.Fill(0,1,mo::Symmetry::None) &&
        !Run.Transform(mo::CanvasTransform::Clockwise) && !Run.Undo() && !Run.Redo() && !Run.Clear(),
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

    mo::Image Uniform{},Checker{},Bands{},Bridge{}; Bridge.fill(7);
    for (int At=0;At<64;++At)
    {
        Checker[At]=static_cast<std::uint8_t>((At/8+At%8)%2);
        Bands[At]=static_cast<std::uint8_t>(((At/8)/2+(At%8)/3)%4);
    }
    Bridge[0]=Bridge[8]=Bridge[7]=Bridge[15]=Bridge[23]=1;
    const std::array<mo::Image,4> Sources{{Uniform,Checker,Bands,Bridge}};
    bool Selections=true,Fills=true;
    for (const auto& Source:Sources) for (int Mode=0;Mode<6;++Mode) for (int Cell=0;Cell<64;++Cell)
    {
        const auto Expected=FillSelection(Source,Cell,Mode); mo::Selection Actual;
        const auto Symmetry=static_cast<mo::Symmetry>(Mode);
        Selections=Selections && mo::FillTargetsFor(Source,Cell,Symmetry,Actual) && Actual.Count==Expected.size();
        const int Colour=(Cell+Mode)%8; auto ExpectedImage=Source;
        for (int At=0;At<64;++At)
        { Selections=Selections && Actual.Cells[At]==(Expected.count(At)!=0); if (Expected.count(At)) ExpectedImage[At]=static_cast<std::uint8_t>(Colour); }
        mo::Session Fill; Fill.Begin(Source); const bool Changed=ExpectedImage!=Source;
        const bool Accepted=Fill.Fill(Cell,Colour,Symmetry);
        Fills=Fills && Accepted==Changed && Fill.Canvas()==ExpectedImage && Fill.UndoCount()==(Changed?1u:0u) && Fill.RedoCount()==0;
    }
    Check(Selections,"1536 fill selections match immutable-source union-find plus centred-coordinate group oracle");
    Check(Fills,"all intentional-image fills paint exactly the selected union in at most one history edit");
    mo::Selection Selected;
    const auto BridgeBefore=Bridge;
    Check(mo::FillTargetsFor(Bridge,0,mo::Symmetry::MirrorColumns,Selected) && Selected.Count==4 &&
        Selected.Cells[0] && Selected.Cells[8] && Selected.Cells[7] && Selected.Cells[15] && !Selected.Cells[23] && !Selected.Cells[16] && Bridge==BridgeBefore,
        "copied cells cannot grow the original region into a disconnected same-colour island");
    mo::Image Edges{}; Edges.fill(7); Edges[7]=Edges[8]=1; Edges[18]=Edges[27]=2;
    Check(mo::FillTargetsFor(Edges,7,mo::Symmetry::None,Selected) && Selected.Count==1 && Selected.Cells[7] && !Selected.Cells[8] &&
        mo::FillTargetsFor(Edges,18,mo::Symmetry::None,Selected) && Selected.Count==1 && Selected.Cells[18] && !Selected.Cells[27],
        "region connectivity excludes row wrap and diagonal-only neighbours");
    Run.Begin(Bridge);
    Check(Run.Fill(0,2,mo::Symmetry::MirrorColumns) && Run.UndoCount()==1 && Run.Canvas()[23]==1 && Run.Canvas()[16]==7 &&
        Run.Undo() && Run.Canvas()==Bridge && Run.RedoCount()==1 && Run.Redo() && Run.Canvas()[0]==2,
        "symmetric fill is one undoable stroke without copied-island leakage");
    mo::Image SameInk{}; SameInk[0]=1; Run.Begin(SameInk);
    Check(Run.Fill(0,1,mo::Symmetry::MirrorColumns) && Run.Canvas()[7]==1 && Run.UndoCount()==1,
        "same-colour source fill still paints different symmetry copies");
    mo::Selection SentinelSelection; SentinelSelection.Cells[13]=true; SentinelSelection.Count=1; Selected=SentinelSelection;
    auto BadFill=Bridge; BadFill[63]=8;
    Check(!mo::FillTargetsFor(BadFill,0,mo::Symmetry::None,Selected) && !mo::FillTargetsFor(Bridge,-1,mo::Symmetry::None,Selected) &&
        !mo::FillTargetsFor(Bridge,64,mo::Symmetry::None,Selected) && !mo::FillTargetsFor(Bridge,0,static_cast<mo::Symmetry>(255),Selected) &&
        Selected.Count==SentinelSelection.Count && Selected.Cells==SentinelSelection.Cells,
        "invalid fill preview retains all caller selection fields");
    mo::Image Markers{}; Markers[0]=1; Markers[10]=2; Markers[28]=3;
    mo::Image Clockwise{}; Clockwise[7]=1; Clockwise[22]=2; Clockwise[36]=3; Run.Begin(Markers);
    Check(Run.Transform(mo::CanvasTransform::Clockwise) && Run.Canvas()==Clockwise && Run.UndoCount()==1 &&
        Run.Undo() && Run.Canvas()==Markers && Run.Redo() && Run.Canvas()==Clockwise,
        "clockwise markers land at exact expected cells as one undoable edit");
    bool Permutations=true;
    for (int Kind=0;Kind<3;++Kind)
    {
        std::set<int> Destinations;
        for (int Cell=0;Cell<64;++Cell)
        {
            mo::Image Dot{}; Dot[Cell]=1; const auto Expected=Transformed(Dot,Kind); mo::Session Move; Move.Begin(Dot);
            Permutations=Permutations && Move.Transform(static_cast<mo::CanvasTransform>(Kind)) && Move.Canvas()==Expected && Histogram(Move.Canvas())==Histogram(Dot);
            for (int At=0;At<64;++At) if (Move.Canvas()[At]) Destinations.insert(At);
        }
        Permutations=Permutations && Destinations.size()==64;
        mo::Session Move; Move.Begin(Markers); Move.Transform(static_cast<mo::CanvasTransform>(Kind));
        Permutations=Permutations && Move.Canvas()==Transformed(Markers,Kind) && Histogram(Move.Canvas())==Histogram(Markers);
    }
    Check(Permutations,"all192 single-pixel transforms are bijective centred-coordinate permutations preserving palette histogram");
    Run.Begin(Markers); bool Inverses=true;
    for (int Turn=0;Turn<4;++Turn) Inverses=Run.Transform(mo::CanvasTransform::Clockwise) && Inverses;
    Inverses=Inverses && Run.Canvas()==Markers && Run.UndoCount()==4;
    for (int Kind=1;Kind<3;++Kind)
    { Run.Begin(Markers); Inverses=Run.Transform(static_cast<mo::CanvasTransform>(Kind)) && Run.Transform(static_cast<mo::CanvasTransform>(Kind)) && Run.Canvas()==Markers && Inverses; }
    Check(Inverses,"four clockwise turns and each mirror twice return the exact drawing");
    Run.Begin(); Run.Paint(0,1,mo::Symmetry::None); Run.Undo();
    Check(!Run.Fill(0,0,mo::Symmetry::Dihedral) && !Run.Transform(mo::CanvasTransform::Clockwise) &&
        !Run.Transform(mo::CanvasTransform::MirrorColumns) && !Run.Transform(mo::CanvasTransform::MirrorRows) &&
        mo::IsBlank(Run.Canvas()) && Run.UndoCount()==0 && Run.RedoCount()==1,
        "uniform fill and transform no-ops preserve Redo");
    const auto Guarded=Run.Canvas(); const auto GuardUndo=Run.UndoCount(),GuardRedo=Run.RedoCount();
    Check(!Run.Fill(-1,1,mo::Symmetry::None) && !Run.Fill(64,1,mo::Symmetry::None) && !Run.Fill(0,-1,mo::Symmetry::None) &&
        !Run.Fill(0,8,mo::Symmetry::None) && !Run.Fill(0,1,static_cast<mo::Symmetry>(255)) && !Run.Transform(static_cast<mo::CanvasTransform>(255)) &&
        Run.Canvas()==Guarded && Run.UndoCount()==GuardUndo && Run.RedoCount()==GuardRedo && Run.Redo() && Run.Canvas()[0]==1,
        "invalid fill and transform retain canvas and both history branches");
    Run.Undo();
    Check(Run.Fill(0,3,mo::Symmetry::None) && Run.RedoCount()==0 && Run.UndoCount()==1 && Run.Undo() && mo::IsBlank(Run.Canvas()),
        "a real fill branches Redo and can restore the previous complete image");

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
    std::cout<<Checks<<" checks, "<<Failures<<" failed;384 symmetry orbits,1536 fill selections,192 transform permutations, codec refusals and64-step history\n";
    return Failures?1:0;
}
