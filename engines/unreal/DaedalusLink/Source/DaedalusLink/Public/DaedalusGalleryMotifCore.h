// SPDX-License-Identifier: MIT
#pragma once
#include <algorithm>
#include <array>
#include <cstddef>
#include <cstdint>
#include <string>

// Local original motif studies, not Gallery server frames, player profiles or ownership.
namespace daedalus::motif
{
    inline constexpr int Side=8,CellCount=64,PaletteCount=8,SymmetryCount=6,HistoryLimit=64;
    using Image=std::array<std::uint8_t,CellCount>;
    enum class Symmetry:std::uint8_t { None,MirrorColumns,MirrorRows,HalfTurn,QuarterTurn,Dihedral };
    struct Orbit { std::array<int,8> Cells{}; std::size_t Count=0; };
    inline bool ValidImage(const Image& Pixels)
    { for (auto Colour:Pixels) if (Colour>=PaletteCount) return false; return true; }
    inline bool IsBlank(const Image& Pixels)
    { for (auto Colour:Pixels) if (Colour) return false; return true; }
    inline const char* ColourName(int Colour)
    {
        static const char* Names[]={"Paper / erase","Ink","Coral","Gold","Emerald","Azure","Violet","Teal"};
        return Colour>=0 && Colour<PaletteCount?Names[Colour]:"Unavailable";
    }
    inline const char* SymmetryName(Symmetry Mode)
    {
        static const char* Names[]={"One square","Mirror left/right","Mirror near/far","Half turn","Quarter turns","Eight-way mirror"};
        return static_cast<int>(Mode)<SymmetryCount?Names[static_cast<unsigned>(Mode)]:"Unavailable";
    }
    inline bool OrbitFor(int Cell,Symmetry Mode,Orbit& Out)
    {
        if (Cell<0 || Cell>=CellCount || static_cast<int>(Mode)>=SymmetryCount) return false;
        Orbit Candidate;
        auto Add=[&](int Row,int Column)
        {
            const int Index=Row*Side+Column;
            for (std::size_t I=0;I<Candidate.Count;++I) if (Candidate.Cells[I]==Index) return;
            Candidate.Cells[Candidate.Count++]=Index;
        };
        int Row=Cell/Side,Column=Cell%Side;
        Add(Row,Column);
        if (Mode==Symmetry::MirrorColumns) Add(Row,Side-1-Column);
        else if (Mode==Symmetry::MirrorRows) Add(Side-1-Row,Column);
        else if (Mode==Symmetry::HalfTurn) Add(Side-1-Row,Side-1-Column);
        else if (Mode==Symmetry::QuarterTurn || Mode==Symmetry::Dihedral)
            for (int Turn=0;Turn<4;++Turn)
            {
                Add(Row,Column);
                if (Mode==Symmetry::Dihedral) Add(Row,Side-1-Column);
                const int NextRow=Column; Column=Side-1-Row; Row=NextRow;
            }
        std::sort(Candidate.Cells.begin(),Candidate.Cells.begin()+Candidate.Count);
        Out=Candidate; return true;
    }

    class Session
    {
    public:
        bool Begin(const Image& Initial=Image{})
        {
            if (!ValidImage(Initial)) return false;
            const Image Prepared=Initial; // Initial may alias Canvas().
            *this=Session{}; Current=Prepared; bActive=true; return true;
        }
        bool Active() const { return bActive; }
        const Image& Canvas() const { return Current; }
        std::size_t UndoCount() const { return UndoSize; }
        std::size_t RedoCount() const { return RedoSize; }
        bool Paint(int Cell,int Colour,Symmetry Mode)
        {
            if (!bActive || Colour<0 || Colour>=PaletteCount) return false;
            Orbit Targets; if (!OrbitFor(Cell,Mode,Targets)) return false;
            Image Next=Current;
            for (std::size_t I=0;I<Targets.Count;++I) Next[Targets.Cells[I]]=static_cast<std::uint8_t>(Colour);
            return Replace(Next);
        }
        bool Replace(const Image& Pixels)
        {
            if (!bActive || !ValidImage(Pixels) || Pixels==Current) return false;
            const Image Prepared=Pixels;
            Push(UndoHistory,UndoSize,Current); Current=Prepared; RedoSize=0; return true;
        }
        bool Clear() { return Replace(Image{}); }
        bool Undo()
        {
            if (!bActive || !UndoSize) return false;
            Push(RedoHistory,RedoSize,Current); Current=UndoHistory[--UndoSize]; return true;
        }
        bool Redo()
        {
            if (!bActive || !RedoSize) return false;
            Push(UndoHistory,UndoSize,Current); Current=RedoHistory[--RedoSize]; return true;
        }
    private:
        static void Push(std::array<Image,HistoryLimit>& History,std::size_t& Count,const Image& Pixels)
        {
            if (Count==History.size())
            { for (std::size_t I=1;I<Count;++I) History[I-1]=History[I]; --Count; }
            History[Count++]=Pixels;
        }
        Image Current{};
        std::array<Image,HistoryLimit> UndoHistory{},RedoHistory{};
        std::size_t UndoSize=0,RedoSize=0;
        bool bActive=false;
    };

    namespace detail
    {
        inline int Hex(char C)
        {
            if (C>='0' && C<='9') return C-'0';
            if (C>='a' && C<='f') return C-'a'+10;
            if (C>='A' && C<='F') return C-'A'+10;
            return -1;
        }
        inline std::uint16_t Checksum(const std::string& Text)
        {
            unsigned A=0,B=0;
            for (unsigned char C:Text) { A=(A+C)%255u; B=(B+A)%255u; }
            return static_cast<std::uint16_t>((B<<8)|A);
        }
        inline bool Line(const std::string& Text,std::size_t& Position,std::string& Out)
        {
            if (Position>=Text.size()) return false;
            const auto End=Text.find('\n',Position);
            Out=Text.substr(Position,End==std::string::npos?End:End-Position);
            Position=End==std::string::npos?Text.size():End+1;
            if (!Out.empty() && Out.back()=='\r') Out.pop_back();
            return true;
        }
    }
    inline bool ValidId(const std::string& Id)
    {
        if (Id.size()!=32) return false;
        bool Nonzero=false;
        for (char C:Id) { const int Value=detail::Hex(C); if (Value<0) return false; Nonzero=Nonzero || Value!=0; }
        return Nonzero;
    }
    inline std::string CanonicalId(const std::string& Id)
    {
        if (!ValidId(Id)) return {};
        std::string Out=Id;
        for (char& C:Out) if (C>='A' && C<='F') C=static_cast<char>(C-'A'+'a');
        return Out;
    }
    /** A compact versioned pattern, not authentication. Fletcher16 detects
     * accidental edits; it grants no creator, ownership or security guarantee. */
    inline std::string EncodePattern(const Image& Pixels)
    {
        if (!ValidImage(Pixels)) return {};
        std::string Out="DGM1:";
        for (auto Colour:Pixels) Out+=static_cast<char>('0'+Colour);
        const auto Sum=detail::Checksum(Out); Out+=':';
        static const char* Digits="0123456789ABCDEF";
        for (int Shift=12;Shift>=0;Shift-=4) Out+=Digits[(Sum>>Shift)&15u];
        return Out;
    }
    inline bool DecodePattern(const std::string& Text,Image& Out)
    {
        if (Text.size()!=74 || Text.compare(0,5,"DGM1:")!=0 || Text[69]!=':') return false;
        Image Candidate{};
        for (int I=0;I<CellCount;++I)
        {
            const char C=Text[5+I]; if (C<'0' || C>'7') return false;
            Candidate[I]=static_cast<std::uint8_t>(C-'0');
        }
        unsigned Sum=0;
        for (int I=70;I<74;++I)
        { const int Value=detail::Hex(Text[I]); if (Value<0) return false; Sum=(Sum<<4)|static_cast<unsigned>(Value); }
        if (Sum!=detail::Checksum(Text.substr(0,69))) return false;
        Out=Candidate; return true;
    }
    struct Document
    {
        std::string Id,Parent;
        Image Pixels{};
    };
    inline std::string EncodeDocument(const Document& Value)
    {
        const auto Id=CanonicalId(Value.Id);
        const auto Parent=Value.Parent.empty()?std::string{}:CanonicalId(Value.Parent);
        const auto Pattern=EncodePattern(Value.Pixels);
        if (Id.empty() || (!Value.Parent.empty() && Parent.empty()) || Id==Parent || Pattern.empty()) return {};
        return "DGM-DOCUMENT 1\nid:"+Id+"\nparent:"+(Parent.empty()?"-":Parent)+"\npattern:"+Pattern+"\n";
    }
    inline bool DecodeDocument(const std::string& Text,Document& Out)
    {
        if (Text.size()>512) return false;
        std::size_t Position=0;
        if (Text.compare(0,3,"\xEF\xBB\xBF")==0) Position=3;
        std::array<std::string,4> Lines;
        for (auto& L:Lines) if (!detail::Line(Text,Position,L)) return false;
        if (Position!=Text.size() || Lines[0]!="DGM-DOCUMENT 1" || Lines[1].compare(0,3,"id:")!=0 ||
            Lines[2].compare(0,7,"parent:")!=0 || Lines[3].compare(0,8,"pattern:")!=0) return false;
        Document Candidate;
        Candidate.Id=CanonicalId(Lines[1].substr(3));
        const auto Parent=Lines[2].substr(7);
        Candidate.Parent=Parent=="-"?std::string{}:CanonicalId(Parent);
        if (Candidate.Id.empty() || (Parent!="-" && Candidate.Parent.empty()) || Candidate.Id==Candidate.Parent ||
            !DecodePattern(Lines[3].substr(8),Candidate.Pixels)) return false;
        Out=Candidate; return true;
    }
}
