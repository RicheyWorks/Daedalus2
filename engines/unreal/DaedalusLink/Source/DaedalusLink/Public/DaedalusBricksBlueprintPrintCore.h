// SPDX-License-Identifier: MIT
#pragma once
#include "DaedalusBricksBridgeCore.h"
#include "DaedalusBricksSkylineCore.h"
#include <cstddef>
#include <initializer_list>
#include <string>
#include <utility>

// Descriptive one-way local artifacts. This is neither a save/import format
// nor a structural-safety, authentication, ownership or reward certificate.
namespace daedalus::blueprintprint
{
    inline constexpr std::size_t MaxSvgBytes=64*1024;
    struct Identity { std::string Id,Parent; };
    inline bool ValidId(const std::string& Id)
    {
        if (Id.size()!=32) return false; bool Nonzero=false;
        for (char C:Id) { if (!((C>='0' && C<='9') || (C>='a' && C<='f'))) return false; if (C!='0') Nonzero=true; }
        return Nonzero;
    }
    namespace detail
    {
        inline bool ValidIdentity(const Identity& Value)
        { return ValidId(Value.Id) && (Value.Parent.empty() || (ValidId(Value.Parent) && Value.Parent!=Value.Id)); }
        inline std::string Xml(const std::string& Value)
        {
            std::string Out;
            for (char C:Value) switch (C)
            {
                case '&': Out+="&amp;"; break; case '<': Out+="&lt;"; break; case '>': Out+="&gt;"; break;
                case '\"': Out+="&quot;"; break; case '\'': Out+="&apos;"; break; default: Out+=C; break;
            }
            return Out;
        }
        inline const char* Flag(bool Value) { return Value?"1":"0"; }
        template<class Range> inline std::string Csv(const Range& Values)
        { std::string Out; for (auto Value:Values) { if (!Out.empty()) Out+=','; Out+=std::to_string(Value); } return Out; }
        inline std::string Digits(const skyline::Grid& Canvas)
        { std::string Out; for (auto Value:Canvas) Out+=static_cast<char>('0'+Value); return Out; }
        template<class Range> inline std::string Flags(const Range& Values)
        { std::string Out; for (bool Value:Values) Out+=Value?'1':'0'; return Out; }
        struct Svg
        {
            std::string Bytes; bool Good=true;
            void Raw(const std::string& Fragment)
            {
                if (!Good || Fragment.size()>MaxSvgBytes-Bytes.size()) { Good=false; return; }
                Bytes+=Fragment;
            }
            void Text(int X,int Y,const std::string& Value,int Size=16,const std::string& Colour="#18334b",const std::string& Anchor="start")
            { Raw("<text x=\""+std::to_string(X)+"\" y=\""+std::to_string(Y)+"\" font-size=\""+std::to_string(Size)+"\" fill=\""+Xml(Colour)+"\" text-anchor=\""+Xml(Anchor)+"\">"+Xml(Value)+"</text>\n"); }
            void Rect(int X,int Y,int W,int H,const std::string& Fill,const std::string& Stroke="#d5e2ec",int Width=1)
            { Raw("<rect x=\""+std::to_string(X)+"\" y=\""+std::to_string(Y)+"\" width=\""+std::to_string(W)+"\" height=\""+std::to_string(H)+"\" rx=\"8\" fill=\""+Xml(Fill)+"\" stroke=\""+Xml(Stroke)+"\" stroke-width=\""+std::to_string(Width)+"\"/>\n"); }
            void Circle(int X,int Y,int Radius,const std::string& Fill)
            { Raw("<circle cx=\""+std::to_string(X)+"\" cy=\""+std::to_string(Y)+"\" r=\""+std::to_string(Radius)+"\" fill=\""+Xml(Fill)+"\"/>\n"); }
            void Line(int X1,int Y1,int X2,int Y2,const std::string& Colour,int Width,const std::string& Dash="")
            { Raw("<line x1=\""+std::to_string(X1)+"\" y1=\""+std::to_string(Y1)+"\" x2=\""+std::to_string(X2)+"\" y2=\""+std::to_string(Y2)+"\" stroke=\""+Xml(Colour)+"\" stroke-width=\""+std::to_string(Width)+"\""+(Dash.empty()?"":" stroke-dasharray=\""+Xml(Dash)+"\"")+"/>\n"); }
            bool Finish(std::string& Out)
            {
                if (!Good || Bytes.empty() || Bytes.size()>MaxSvgBytes) return false;
                for (unsigned char C:Bytes) if (C>126 || (C<32 && C!='\n')) return false;
                Out=std::move(Bytes); return true;
            }
        };
        inline void Begin(Svg& Out,const std::string& Title,const std::string& Description)
        {
            Out.Raw("<svg xmlns=\"http://www.w3.org/2000/svg\" xmlns:bp=\"urn:daedalus:blueprint-print:1\" version=\"1.1\" width=\"1000\" height=\"800\" viewBox=\"0 0 1000 800\" role=\"img\" aria-labelledby=\"print-title print-desc\">\n");
            Out.Raw("<title id=\"print-title\">"+Xml(Title)+"</title>\n<desc id=\"print-desc\">"+Xml(Description)+"</desc>\n");
        }
        inline void MetaBegin(Svg& Out,const char* Kind,int Rule,const char* Name,const Identity& Value,bool Complete)
        {
            Out.Raw("<metadata><bp:print version=\"1\" kind=\""+Xml(Kind)+"\" rule=\""+std::to_string(Rule)+"\" name=\""+Xml(Name)+"\" id=\""+Xml(Value.Id)+"\" parent=\""+Xml(Value.Parent.empty()?"-none":Value.Parent)+"\" current-complete=\""+Flag(Complete)+"\">\n");
        }
        inline void Frame(Svg& Out,const char* Kind,const char* Name,bool Complete)
        {
            Out.Rect(0,0,1000,800,"#f2f7fb","#f2f7fb"); Out.Rect(30,25,940,660,"#ffffff");
            Out.Text(60,65,"BRICKS / LOCAL BLUEPRINT PRINT",14,"#3f647c"); Out.Text(60,108,std::string(Kind)+" / "+Name,29);
            Out.Text(60,143,Complete?"CURRENT SNAPSHOT: COMPLETE":"CURRENT SNAPSHOT: IN PROGRESS",16,Complete?"#126e50":"#45627a");
            Out.Rect(705,180,240,445,"#edf4f8");
        }
        inline void Footer(Svg& Out,const Identity& Value)
        {
            Out.Text(45,722,"Print ID: "+Value.Id,13); Out.Text(45,745,"Parent: "+(Value.Parent.empty()?std::string("-none"):Value.Parent),13);
            Out.Text(45,774,"Local practice artifact / not a saved game, engineering certificate or proof of ownership.",13);
            Out.Raw("</svg>\n");
        }
    }
    inline bool RenderBridgeSvg(int Rule,int Mask,const Identity& Value,std::string& Out)
    {
        brickbridge::Evaluation View;
        if (!detail::ValidIdentity(Value) || !brickbridge::Evaluate(Rule,Mask,View) || !View.WithinLength) return false;
        const auto& Plan=brickbridge::Blueprints[Rule]; detail::Svg Svg;
        detail::Begin(Svg,std::string("Bridge Blueprint / ")+Plan.Name,"Frozen local bridge practice. Numbered studded pads are joined by selected beams; dashed beams are out and crossed beams are closed. Length is a puzzle allowance, not inventory or structural safety.");
        detail::MetaBegin(Svg,"bridge",Rule,Plan.Name,Value,View.Complete);
        Svg.Raw("<bp:snapshot mask=\""+std::to_string(Mask)+"\"/>\n<bp:metrics used-length=\""+std::to_string(View.UsedLength)+"\" pads-connected=\""+std::to_string(View.PadsConnected)+"\" components=\""+std::to_string(View.Components)+"\" selected-count=\""+std::to_string(View.SelectedCount)+"\" within-length=\""+detail::Flag(View.WithinLength)+"\" linked-to-home=\""+detail::Flags(View.LinkedToHome)+"\"/>\n");
        Svg.Raw("<bp:bridge-rule columns=\""+detail::Csv(Plan.Columns)+"\" rows=\""+detail::Csv(Plan.Rows)+"\" allowed-mask=\""+std::to_string(Plan.AllowedMask)+"\" allowance=\""+std::to_string(brickbridge::LengthLimit(Rule))+"\" pads=\"9\" links=\"12\" length=\"manhattan\" goal=\"connect-all-within-allowance\">\n");
        for (int I=0;I<12;++I) Svg.Raw("<bp:link index=\""+std::to_string(I)+"\" from=\""+std::to_string(brickbridge::Links[I].From)+"\" to=\""+std::to_string(brickbridge::Links[I].To)+"\" length=\""+std::to_string(brickbridge::LinkLength(Rule,I))+"\"/>\n");
        Svg.Raw("</bp:bridge-rule></bp:print></metadata>\n"); detail::Frame(Svg,"BRIDGE",Plan.Name,View.Complete);
        const auto X=[&Plan](int Pad) { return 125+100*Plan.Columns[Pad%3]; };
        const auto Y=[&Plan](int Pad) { return 590-70*Plan.Rows[Pad/3]; };
        for (int I=0;I<12;++I)
        {
            const auto& Link=brickbridge::Links[I]; const bool Allowed=(Plan.AllowedMask&(1<<I))!=0,Selected=(Mask&(1<<I))!=0;
            const int A=X(Link.From),B=Y(Link.From),C=X(Link.To),D=Y(Link.To),MidX=(A+C)/2,MidY=(B+D)/2;
            Svg.Raw("<g data-link=\""+std::to_string(I)+"\" data-state=\""+(Allowed?(Selected?"in":"out"):"closed")+"\" data-length=\""+std::to_string(brickbridge::LinkLength(Rule,I))+"\">\n");
            Svg.Line(A,B,C,D,Allowed?(Selected?"#178360":"#8097a8"):"#9a4f50",Selected?8:2,Selected?"":"8 6");
            if (!Allowed) { Svg.Line(MidX-9,MidY-9,MidX+9,MidY+9,"#9a4f50",4); Svg.Line(MidX-9,MidY+9,MidX+9,MidY-9,"#9a4f50",4); }
            Svg.Text(MidX+(A==C?33:0),MidY+(B==D?-12:5),std::to_string(I+1)+":"+std::to_string(brickbridge::LinkLength(Rule,I)),12,"#18334b","middle");
            Svg.Raw("</g>\n");
        }
        for (int Pad=0;Pad<9;++Pad)
        {
            const int XAt=X(Pad),YAt=Y(Pad); Svg.Raw("<g data-pad=\""+std::to_string(Pad)+"\" data-linked=\""+detail::Flag(View.LinkedToHome[Pad])+"\">\n");
            Svg.Rect(XAt-24,YAt-24,48,48,View.LinkedToHome[Pad]?"#bfead9":"#d7e8f9","#34546a",2);
            for (int DX:{-13,13}) for (int DY:{-13,13}) Svg.Circle(XAt+DX,YAt+DY,4,"#ffffff");
            Svg.Text(XAt,YAt+6,std::to_string(Pad+1),18,"#18334b","middle"); Svg.Raw("</g>\n");
        }
        Svg.Text(125,646,"1 = HOME / span labels show link number:length",14);
        Svg.Text(725,216,"BEAM ALLOWANCE",16); Svg.Text(725,249,std::to_string(View.UsedLength)+" / "+std::to_string(brickbridge::LengthLimit(Rule))+" units",27);
        Svg.Text(725,290,std::to_string(View.PadsConnected)+" / 9 pads linked home",16); Svg.Text(725,319,std::to_string(View.Components)+" connected groups",16);
        Svg.Text(725,348,std::to_string(View.SelectedCount)+" selected beams",16);
        Svg.Line(727,390,774,390,"#178360",8); Svg.Text(787,396,"IN",16);
        Svg.Line(727,424,774,424,"#8097a8",2,"8 6"); Svg.Text(787,430,"OUT",16);
        Svg.Line(738,450,758,470,"#9a4f50",4); Svg.Line(738,470,758,450,"#9a4f50",4); Svg.Text(787,466,"CLOSED",16);
        Svg.Text(725,511,"Connect all nine pads.",16); Svg.Text(725,538,"Stay within the allowance.",15);
        Svg.Text(725,580,"Length is a local puzzle rule.",13); detail::Footer(Svg,Value); return Svg.Finish(Out);
    }
    inline bool RenderSkylineSvg(int Rule,const skyline::Grid& Canvas,const Identity& Value,std::string& Out)
    {
        skyline::Evaluation View;
        if (!detail::ValidIdentity(Value) || !skyline::Evaluate(Rule,Canvas,View) || !View.GivensMatch) return false;
        const auto& Plan=skyline::Blueprints[Rule]; detail::Svg Svg;
        detail::Begin(Svg,std::string("Skyline Blueprint / ")+Plan.Name,"Frozen local skyline practice. Heights one through four belong once in each row and column; taller towers hide shorter ones. F marks a fixed height, red borders mark contradictions, and zero side clues are open. Contradictions remain editable.");
        detail::MetaBegin(Svg,"skyline",Rule,Plan.Name,Value,View.Complete);
        Svg.Raw("<bp:snapshot heights=\""+detail::Digits(Canvas)+"\"/>\n<bp:metrics filled=\""+std::to_string(View.Filled)+"\" clue-matches=\""+std::to_string(View.ClueMatches)+"\" clue-count=\""+std::to_string(View.ClueCount)+"\" givens-match=\""+detail::Flag(View.GivensMatch)+"\" latin-possible=\""+detail::Flag(View.LatinPossible)+"\" conflicts=\""+detail::Flags(View.Conflicts)+"\" left=\""+detail::Csv(View.Left)+"\" right=\""+detail::Csv(View.Right)+"\" top=\""+detail::Csv(View.Top)+"\" bottom=\""+detail::Csv(View.Bottom)+"\" row-full=\""+detail::Flags(View.RowFull)+"\" column-full=\""+detail::Flags(View.ColumnFull)+"\"/>\n");
        Svg.Raw("<bp:skyline-rule side=\"4\" heights=\"1,2,3,4\" empty=\"0\" uniqueness=\"rows-and-columns\" clue=\"record-highs\" left=\""+detail::Csv(Plan.Left)+"\" right=\""+detail::Csv(Plan.Right)+"\" top=\""+detail::Csv(Plan.Top)+"\" bottom=\""+detail::Csv(Plan.Bottom)+"\" givens=\""+detail::Digits(Plan.Givens)+"\"/>\n</bp:print></metadata>\n");
        detail::Frame(Svg,"SKYLINE",Plan.Name,View.Complete);
        const char* Colours[]={"#e9f0f6","#e99886","#e8c45b","#66bea5","#b797d9"};
        for (int Cell=0;Cell<16;++Cell)
        {
            const int X=245+90*(Cell%4),Y=230+90*(Cell/4),Height=Canvas[Cell];
            Svg.Raw("<g data-cell=\""+std::to_string(Cell)+"\" data-height=\""+std::to_string(Height)+"\" data-fixed=\""+detail::Flag(Plan.Givens[Cell]!=0)+"\" data-conflict=\""+detail::Flag(View.Conflicts[Cell])+"\">\n");
            Svg.Rect(X+3,Y+3,84,84,"#ffffff",View.Conflicts[Cell]?"#bc3549":"#9fb5c6",View.Conflicts[Cell]?4:1);
            for (int Level=0;Level<Height;++Level) Svg.Rect(X+22,Y+63-10*Level,46,10,Colours[Height],"#34546a");
            Svg.Text(X+45,Y+24,Height?std::to_string(Height):"0",22,"#18334b","middle");
            if (Plan.Givens[Cell]) Svg.Text(X+74,Y+77,"F",14,"#735617","middle");
            if (View.Conflicts[Cell]) Svg.Text(X+14,Y+77,"!",17,"#bc3549","middle");
            Svg.Raw("</g>\n");
        }
        const auto ClueText=[](int Number) { return Number?std::to_string(Number):std::string("0 OPEN"); };
        for (int Line=0;Line<4;++Line)
        {
            const char* Sides[]={"left","right","top","bottom"};
            const int Clues[]={Plan.Left[Line],Plan.Right[Line],Plan.Top[Line],Plan.Bottom[Line]};
            const int X[]={210,643,290+90*Line,290+90*Line},Y[]={284+90*Line,284+90*Line,209,618};
            for (int Side=0;Side<4;++Side)
            {
                Svg.Raw("<g data-side=\""+std::string(Sides[Side])+"\" data-line=\""+std::to_string(Line)+"\" data-clue=\""+std::to_string(Clues[Side])+"\">\n");
                Svg.Text(X[Side],Y[Side],ClueText(Clues[Side]),14,"#18334b","middle"); Svg.Raw("</g>\n");
            }
        }
        Svg.Text(245,650,"Rows run down / columns run right / 0 = empty",14);
        Svg.Text(725,216,"HEIGHTS 1 / 2 / 3 / 4",16); Svg.Text(725,252,std::to_string(View.Filled)+" / 16 filled",26);
        Svg.Text(725,292,std::to_string(View.ClueMatches)+" / "+std::to_string(View.ClueCount)+" full-line clues",16);
        Svg.Text(725,329,View.LatinPossible?"No repeated heights":"Repeated heights marked !",15,View.LatinPossible?"#126e50":"#bc3549");
        Svg.Text(725,376,"F = fixed by the blueprint",14); Svg.Text(725,408,"0 side clue = open",14);
        Svg.Text(725,450,"Use 1-4 once in each",15); Svg.Text(725,476,"row and column.",15);
        Svg.Text(725,516,"Taller towers hide shorter",14); Svg.Text(725,540,"ones from that side.",14);
        Svg.Text(725,580,"Any matching skyline works.",14); detail::Footer(Svg,Value); return Svg.Finish(Out);
    }
}
