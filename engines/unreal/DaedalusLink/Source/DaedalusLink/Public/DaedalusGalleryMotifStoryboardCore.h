// SPDX-License-Identifier: MIT
#pragma once
#include "DaedalusGalleryMotifFlipbookCore.h"
#include <array>
#include <cstddef>
#include <string>
#include <utility>

// Static descriptive contact sheet, not an animation/save/import/profile.
// Artifact identity and DGM frame lineage have separate metadata roles.
namespace daedalus::storyboard
{
    inline constexpr std::size_t MaxSvgBytes=64*1024;
    struct Identity { std::string Id,Parent; };
    using Palette=std::array<std::string,8>;
    namespace detail
    {
        inline bool Id(const std::string& Value)
        {
            if (Value.size()!=32) return false; bool Nonzero=false;
            for (char C:Value) { if (!((C>='0' && C<='9') || (C>='a' && C<='f'))) return false; if (C!='0') Nonzero=true; }
            return Nonzero;
        }
        inline bool Colour(const std::string& Value)
        {
            if (Value.size()!=7 || Value[0]!='#') return false;
            for (std::size_t I=1;I<7;++I) if (!((Value[I]>='0' && Value[I]<='9') || (Value[I]>='a' && Value[I]<='f') || (Value[I]>='A' && Value[I]<='F'))) return false;
            return true;
        }
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
        inline std::string Digits(const motif::Image& Pixels)
        { std::string Out; for (auto Pixel:Pixels) Out+=static_cast<char>('0'+Pixel); return Out; }
        inline std::string ParentText(const std::string& Value) { return Value.empty()?std::string("-none"):Value; }
        struct Svg
        {
            std::string Bytes; bool Good=true;
            void Raw(const std::string& Fragment)
            { if (!Good || Fragment.size()>MaxSvgBytes-Bytes.size()) { Good=false; return; } Bytes+=Fragment; }
            void Text(int X,int Y,const std::string& Value,int Size=16,const std::string& Ink="#20384d",const std::string& Anchor="start")
            { Raw("<text x=\""+std::to_string(X)+"\" y=\""+std::to_string(Y)+"\" font-size=\""+std::to_string(Size)+"\" fill=\""+Xml(Ink)+"\" text-anchor=\""+Xml(Anchor)+"\">"+Xml(Value)+"</text>\n"); }
            void Rect(int X,int Y,int Width,int Height,const std::string& Fill,const std::string& Stroke="none",int StrokeWidth=0)
            { Raw("<rect x=\""+std::to_string(X)+"\" y=\""+std::to_string(Y)+"\" width=\""+std::to_string(Width)+"\" height=\""+std::to_string(Height)+"\" fill=\""+Xml(Fill)+"\" stroke=\""+Xml(Stroke)+"\" stroke-width=\""+std::to_string(StrokeWidth)+"\"/>\n"); }
            bool Finish(std::string& Out)
            {
                if (!Good || Bytes.empty() || Bytes.size()>MaxSvgBytes) return false;
                for (unsigned char C:Bytes) if (C>126 || (C<32 && C!='\n')) return false;
                Out=std::move(Bytes); return true;
            }
        };
    }
    inline bool RenderSvg(const flipbook::Player& Book,const Palette& Colours,const Identity& Artifact,std::string& Out)
    {
        if (!detail::Id(Artifact.Id) || (!Artifact.Parent.empty() && (!detail::Id(Artifact.Parent) || Artifact.Parent==Artifact.Id)) ||
            !Book.Active() || Book.Count()<2 || Book.Count()>4 || Book.Index()<0 || Book.Index()>=Book.Count() ||
            (Book.Fps()!=2 && Book.Fps()!=4) || (Book.Direction()!=1 && Book.Direction()!=-1)) return false;
        for (const auto& Value:Colours) if (!detail::Colour(Value)) return false;
        for (int I=0;I<Book.Count();++I)
        {
            const auto* Frame=Book.Frame(I);
            if (!Frame || Frame->Id.empty() || motif::CanonicalId(Frame->Id)!=Frame->Id ||
                (!Frame->Parent.empty() && motif::CanonicalId(Frame->Parent)!=Frame->Parent) || motif::EncodeDocument(*Frame).empty()) return false;
            for (int Previous=0;Previous<I;++Previous) if (Book.Frame(Previous)->Id==Frame->Id) return false;
        }
        const int Height=Book.Count()==2?900:1410; detail::Svg Svg;
        Svg.Raw("<svg xmlns=\"http://www.w3.org/2000/svg\" xmlns:sb=\"urn:daedalus:motif-storyboard:1\" version=\"1.1\" width=\"1200\" height=\""+std::to_string(Height)+"\" viewBox=\"0 0 1200 "+std::to_string(Height)+"\" role=\"img\" aria-labelledby=\"sheet-title sheet-desc\">\n");
        Svg.Raw("<title id=\"sheet-title\">Local Motif Storyboard</title>\n<desc id=\"sheet-desc\">Static original-order contact sheet of frozen local motif documents. Current-frame border and playback labels describe the moment of capture, not a resumable animation. Each square uses the supplied sRGB palette.</desc>\n");
        Svg.Raw("<metadata><sb:storyboard version=\"1\" artifact-id=\""+detail::Xml(Artifact.Id)+"\" artifact-parent=\""+detail::Xml(detail::ParentText(Artifact.Parent))+"\" frame-count=\""+std::to_string(Book.Count())+"\">\n");
        Svg.Raw("<sb:playback current-index=\""+std::to_string(Book.Index())+"\" fps=\""+std::to_string(Book.Fps())+"\" direction=\""+std::to_string(Book.Direction())+"\" playing=\""+detail::Flag(Book.Playing())+"\" state-label=\"at capture\"/>\n<sb:palette version=\"1\" space=\"srgb\" encoding=\"#RRGGBB\">\n");
        for (int I=0;I<8;++I) Svg.Raw("<sb:colour index=\""+std::to_string(I)+"\" value=\""+detail::Xml(Colours[I])+"\"/>\n");
        Svg.Raw("</sb:palette><sb:frames>\n");
        for (int I=0;I<Book.Count();++I)
        {
            const auto& Frame=*Book.Frame(I);
            Svg.Raw("<sb:frame index=\""+std::to_string(I)+"\" order=\""+std::to_string(I+1)+"\" dgm-id=\""+detail::Xml(Frame.Id)+"\" dgm-parent=\""+detail::Xml(detail::ParentText(Frame.Parent))+"\" palette-indices=\""+detail::Digits(Frame.Pixels)+"\"/>\n");
        }
        Svg.Raw("</sb:frames></sb:storyboard></metadata>\n");
        Svg.Rect(0,0,1200,Height,"#f3f6fb"); Svg.Text(40,53,"GALLERY / LOCAL MOTIF STORYBOARD",15,"#4d6680");
        Svg.Text(40,96,"A small story, one sketch at a time",32);
        Svg.Text(40,132,"At capture: frame "+std::to_string(Book.Index()+1)+" of "+std::to_string(Book.Count())+" / "+std::to_string(Book.Fps())+" fps / "+
            (Book.Direction()==1?"forward":"reverse")+" / "+(Book.Playing()?"playing":"paused"),18);
        Svg.Text(40,160,"Read left to right, then down. Frame order stays original even when playback is reversed.",15,"#4d6680");
        for (int I=0;I<Book.Count();++I)
        {
            const auto& Frame=*Book.Frame(I); const int X=40+580*(I%2),Y=180+510*(I/2),PixelX=X+150,PixelY=Y+55; const bool Current=I==Book.Index();
            Svg.Raw("<g data-frame=\""+std::to_string(I)+"\" data-order=\""+std::to_string(I+1)+"\" data-current=\""+detail::Flag(Current)+"\">\n");
            Svg.Rect(X,Y,540,470,"#ffffff",Current?"#7a4bb5":"#c4d3df",Current?4:1);
            Svg.Text(X+22,Y+32,"FRAME "+std::to_string(I+1)+(Current?" / CURRENT AT CAPTURE":""),18,Current?"#66339f":"#20384d");
            Svg.Rect(PixelX-2,PixelY-2,244,244,"#20384d"); Svg.Raw("<g data-pixels=\"1\">\n");
            for (int Cell=0;Cell<64;++Cell)
            {
                const int Index=Frame.Pixels[Cell];
                Svg.Raw("<rect data-cell=\""+std::to_string(Cell)+"\" data-index=\""+std::to_string(Index)+"\" x=\""+std::to_string(PixelX+30*(Cell%8))+"\" y=\""+std::to_string(PixelY+30*(Cell/8))+"\" width=\"30\" height=\"30\" fill=\""+detail::Xml(Colours[Index])+"\"/>\n");
            }
            Svg.Raw("</g>\n"); Svg.Text(X+22,Y+324,"R1 C1 is top left / 8 x 8 original palette indices",14,"#4d6680");
            Svg.Text(X+22,Y+356,"DGM ID: "+Frame.Id,14); Svg.Text(X+22,Y+382,"DGM parent: "+detail::ParentText(Frame.Parent),14);
            Svg.Text(X+22,Y+429,"A frozen document, not a new exported sketch.",14,"#4d6680"); Svg.Raw("</g>\n");
        }
        Svg.Text(40,Height-200,"HOST PALETTE / sRGB AT CAPTURE / indices 0-7",16);
        for (int I=0;I<8;++I)
        {
            const int X=40+140*I; Svg.Raw("<g data-palette=\""+std::to_string(I)+"\">\n");
            Svg.Rect(X,Height-175,28,28,Colours[I],"#20384d",1); Svg.Text(X+38,Height-155,std::to_string(I)+" "+Colours[I],13); Svg.Raw("</g>\n");
        }
        Svg.Text(40,Height-94,"Artifact ID: "+Artifact.Id,14); Svg.Text(40,Height-68,"Artifact parent: "+detail::ParentText(Artifact.Parent),14);
        Svg.Text(40,Height-29,"Static local artifact / playback labels are at capture / not a saved flipbook or profile.",15);
        Svg.Raw("</svg>\n"); return Svg.Finish(Out);
    }
}
