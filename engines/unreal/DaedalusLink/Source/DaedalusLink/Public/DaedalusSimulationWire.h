// SPDX-License-Identifier: MIT
// Portable decoder for LivingWorldService.View schema 1. No engine or transport state.
#pragma once
#include <cstdint>
#include <limits>
#include <string>
#include <unordered_set>
#include <utility>
#include <vector>

namespace daedalus { namespace simulation {
struct View {
    int SchemaVersion=1;
    std::string WorldId;
    int64_t Tick=0, Revision=0;
    std::string StateHash;
    int CisternWater=0, KeeperWater=0;
    std::string NpcId, Task, Reason;
    bool QuestCompleted=false;
    std::string RememberedActor;
    bool DrySpell=false, Active=false;
    int64_t EventSequence=0;
};

namespace wire_detail {
constexpr size_t MaxResponseBytes=64*1024;
constexpr size_t MaxDepth=16;
constexpr size_t MaxFields=128;
constexpr size_t MaxArrayItems=1024;
constexpr size_t MaxUnknownStringBytes=4096;

inline bool Identity(const std::string& S) {
    if(S.empty() || S.size()>128) return false;
    for(unsigned char C:S)
        if(!((C>='A' && C<='Z') || (C>='a' && C<='z') || (C>='0' && C<='9') ||
             C=='_' || C=='.' || C==':' || C=='@' || C=='-')) return false;
    return true;
}

// All strings, including skipped extensions, must contain canonical valid UTF-8.
inline bool Utf8(const std::string& S) {
    for(size_t I=0;I<S.size();) {
        const unsigned char C=static_cast<unsigned char>(S[I++]);
        if(C<0x80) continue;
        uint32_t Point=0, Minimum=0; size_t Continuations=0;
        if(C>=0xc2 && C<=0xdf) { Point=C&0x1f; Minimum=0x80; Continuations=1; }
        else if(C>=0xe0 && C<=0xef) { Point=C&0x0f; Minimum=0x800; Continuations=2; }
        else if(C>=0xf0 && C<=0xf4) { Point=C&0x07; Minimum=0x10000; Continuations=3; }
        else return false;
        if(Continuations>S.size()-I) return false;
        for(size_t N=0;N<Continuations;++N) {
            const unsigned char Next=static_cast<unsigned char>(S[I++]);
            if((Next&0xc0)!=0x80) return false;
            Point=(Point<<6)|(Next&0x3f);
        }
        if(Point<Minimum || Point>0x10ffff || (Point>=0xd800 && Point<=0xdfff)) return false;
    }
    return true;
}
inline bool BoundedText(const std::string& S,size_t Limit) {
    return S.size()<=Limit && Utf8(S);
}
} // namespace wire_detail

inline bool ValidateView(const View& S) {
    if(S.SchemaVersion!=1 || !wire_detail::Identity(S.WorldId) || !wire_detail::Identity(S.NpcId) ||
       S.Tick<0 || S.Revision<0 || S.EventSequence<0 || S.CisternWater<0 || S.CisternWater>12 ||
       S.KeeperWater<0 || S.KeeperWater>6 || S.StateHash.size()!=64 ||
       !wire_detail::BoundedText(S.Reason,256) ||
       (!S.RememberedActor.empty() && !wire_detail::Identity(S.RememberedActor)) ||
       S.QuestCompleted!=!S.RememberedActor.empty() ||
       (S.Task!="REST" && S.Task!="WORK" && S.Task!="REQUEST_WATER")) return false;
    for(char C:S.StateHash) if(!((C>='0' && C<='9') || (C>='a' && C<='f'))) return false;
    return true;
}

namespace wire_detail {
struct Event { int64_t Sequence=0, Tick=0; };
class Parser {
public:
    explicit Parser(const std::string& Json):Source(Json) {}
    bool Read(View& Result) {
        if(Source.size()>MaxResponseBytes || !Take('{')) return false;
        std::unordered_set<std::string> Keys;
        uint32_t Seen=0;
        if(Peek('}')) return false;
        do {
            std::string Key;
            if(!String(Key,MaxUnknownStringBytes) || Keys.size()==MaxFields || !Keys.insert(Key).second || !Take(':')) return false;
            int Field=FieldIndex(Key);
            if(Field>=0) {
                Seen|=uint32_t(1)<<Field;
                if(!FieldValue(Field,Result)) return false;
            } else if(!Skip(1)) return false;
            if(Take('}')) break;
            if(!Take(',')) return false;
        } while(true);
        Space();
        if(Position!=Source.size() || Seen!=0xffff || !ValidateView(Result)) return false;
        if(Events.empty()) return Result.EventSequence==0;
        int64_t Previous=Events.front().Sequence-1;
        int64_t PreviousTick=0;
        for(const Event& E:Events) {
            if(Previous==std::numeric_limits<int64_t>::max() || E.Sequence!=Previous+1 ||
               E.Tick<PreviousTick || E.Tick>Result.Tick) return false;
            Previous=E.Sequence; PreviousTick=E.Tick;
        }
        return Previous==Result.EventSequence;
    }
private:
    const std::string& Source;
    size_t Position=0;
    std::vector<Event> Events;

    void Space() {
        while(Position<Source.size() && (Source[Position]==' ' || Source[Position]=='\t' ||
              Source[Position]=='\n' || Source[Position]=='\r')) ++Position;
    }
    bool Peek(char C) { Space(); return Position<Source.size() && Source[Position]==C; }
    bool Take(char C) {
        if(!Peek(C)) return false;
        ++Position; return true;
    }
    bool Literal(const char* Word) {
        Space(); size_t At=Position;
        for(size_t I=0;Word[I];++I) {
            if(At==Source.size() || Source[At]!=Word[I]) return false;
            ++At;
        }
        Position=At; return true;
    }
    bool Boolean(bool& Value) {
        if(Literal("true")) { Value=true; return true; }
        if(Literal("false")) { Value=false; return true; }
        return false;
    }
    static bool Digit(char C) { return C>='0' && C<='9'; }
    bool Counter(int64_t& Value) {
        Space();
        if(Position==Source.size() || !Digit(Source[Position])) return false;
        const size_t Begin=Position;
        int64_t Number=0;
        while(Position<Source.size() && Digit(Source[Position])) {
            const int N=Source[Position++]-'0';
            if(Number>(std::numeric_limits<int64_t>::max()-N)/10) return false;
            Number=Number*10+N;
        }
        if(Position-Begin>1 && Source[Begin]=='0') return false;
        if(Position<Source.size() && (Source[Position]=='.' || Source[Position]=='e' || Source[Position]=='E')) return false;
        Value=Number; return true;
    }
    bool SmallInteger(int& Value,int Maximum) {
        int64_t N=0;
        if(!Counter(N) || N>Maximum) return false;
        Value=static_cast<int>(N); return true;
    }
    bool Hex4(uint32_t& Value) {
        Value=0;
        for(int I=0;I<4;++I) {
            if(Position==Source.size()) return false;
            const char C=Source[Position++];
            if(C>='0' && C<='9') Value=(Value<<4)|static_cast<uint32_t>(C-'0');
            else if(C>='a' && C<='f') Value=(Value<<4)|static_cast<uint32_t>(C-'a'+10);
            else if(C>='A' && C<='F') Value=(Value<<4)|static_cast<uint32_t>(C-'A'+10);
            else return false;
        }
        return true;
    }
    static void AppendPoint(std::string& Out,uint32_t Point) {
        if(Point<=0x7f) Out.push_back(static_cast<char>(Point));
        else if(Point<=0x7ff) {
            Out.push_back(static_cast<char>(0xc0|(Point>>6)));
            Out.push_back(static_cast<char>(0x80|(Point&0x3f)));
        } else if(Point<=0xffff) {
            Out.push_back(static_cast<char>(0xe0|(Point>>12)));
            Out.push_back(static_cast<char>(0x80|((Point>>6)&0x3f)));
            Out.push_back(static_cast<char>(0x80|(Point&0x3f)));
        } else {
            Out.push_back(static_cast<char>(0xf0|(Point>>18)));
            Out.push_back(static_cast<char>(0x80|((Point>>12)&0x3f)));
            Out.push_back(static_cast<char>(0x80|((Point>>6)&0x3f)));
            Out.push_back(static_cast<char>(0x80|(Point&0x3f)));
        }
    }
    bool String(std::string& Value,size_t Limit) {
        if(!Take('"')) return false;
        Value.clear();
        while(Position<Source.size()) {
            const unsigned char C=static_cast<unsigned char>(Source[Position++]);
            if(C=='"') return Utf8(Value);
            if(C<0x20) return false;
            if(C!='\\') Value.push_back(static_cast<char>(C));
            else {
                if(Position==Source.size()) return false;
                switch(Source[Position++]) {
                    case '"': Value.push_back('"'); break;
                    case '\\': Value.push_back('\\'); break;
                    case '/': Value.push_back('/'); break;
                    case 'b': Value.push_back('\b'); break;
                    case 'f': Value.push_back('\f'); break;
                    case 'n': Value.push_back('\n'); break;
                    case 'r': Value.push_back('\r'); break;
                    case 't': Value.push_back('\t'); break;
                    case 'u': {
                        uint32_t Point=0;
                        if(!Hex4(Point)) return false;
                        if(Point>=0xd800 && Point<=0xdbff) {
                            if(Position+2>Source.size() || Source[Position]!='\\' || Source[Position+1]!='u') return false;
                            Position+=2; uint32_t Low=0;
                            if(!Hex4(Low) || Low<0xdc00 || Low>0xdfff) return false;
                            Point=0x10000+((Point-0xd800)<<10)+(Low-0xdc00);
                        } else if(Point>=0xdc00 && Point<=0xdfff) return false;
                        AppendPoint(Value,Point); break;
                    }
                    default: return false;
                }
            }
            if(Value.size()>Limit) return false;
        }
        return false;
    }
    // Extensions are validated and skipped with fixed limits; no unbounded DOM is created.
    bool Skip(size_t Depth) {
        if(Depth>MaxDepth) return false;
        if(Peek('"')) { std::string Ignored; return String(Ignored,MaxUnknownStringBytes); }
        if(Take('{')) {
            std::unordered_set<std::string> Keys;
            if(Take('}')) return true;
            do {
                std::string Key;
                if(!String(Key,MaxUnknownStringBytes) || Keys.size()==MaxFields || !Keys.insert(Key).second ||
                   !Take(':') || !Skip(Depth+1)) return false;
                if(Take('}')) return true;
                if(!Take(',')) return false;
            } while(true);
        }
        if(Take('[')) {
            size_t Items=0;
            if(Take(']')) return true;
            do {
                if(++Items>MaxArrayItems || !Skip(Depth+1)) return false;
                if(Take(']')) return true;
                if(!Take(',')) return false;
            } while(true);
        }
        if(Literal("true") || Literal("false") || Literal("null")) return true;
        Space();
        if(Position<Source.size() && Source[Position]=='-') ++Position;
        if(Position==Source.size() || !Digit(Source[Position])) return false;
        if(Source[Position]=='0') ++Position;
        else while(Position<Source.size() && Digit(Source[Position])) ++Position;
        if(Position<Source.size() && Source[Position]=='.') {
            ++Position;
            if(Position==Source.size() || !Digit(Source[Position])) return false;
            while(Position<Source.size() && Digit(Source[Position])) ++Position;
        }
        if(Position<Source.size() && (Source[Position]=='e' || Source[Position]=='E')) {
            ++Position;
            if(Position<Source.size() && (Source[Position]=='+' || Source[Position]=='-')) ++Position;
            if(Position==Source.size() || !Digit(Source[Position])) return false;
            while(Position<Source.size() && Digit(Source[Position])) ++Position;
        }
        return true;
    }
    static int FieldIndex(const std::string& Key) {
        static const char* Names[]={"schemaVersion","worldId","tick","revision","stateHash","cisternWater",
            "keeperWater","npcId","task","reason","questCompleted","rememberedActor","drySpell","active",
            "eventSequence","events"};
        for(int I=0;I<16;++I) if(Key==Names[I]) return I;
        return -1;
    }
    bool FieldValue(int Field,View& V) {
        switch(Field) {
            case 0: return SmallInteger(V.SchemaVersion,1);
            case 1: return String(V.WorldId,128);
            case 2: return Counter(V.Tick);
            case 3: return Counter(V.Revision);
            case 4: return String(V.StateHash,64);
            case 5: return SmallInteger(V.CisternWater,12);
            case 6: return SmallInteger(V.KeeperWater,6);
            case 7: return String(V.NpcId,128);
            case 8: return String(V.Task,32);
            case 9: return String(V.Reason,256);
            case 10: return Boolean(V.QuestCompleted);
            case 11: return String(V.RememberedActor,128);
            case 12: return Boolean(V.DrySpell);
            case 13: return Boolean(V.Active);
            case 14: return Counter(V.EventSequence);
            case 15: return ReadEvents();
            default: return false;
        }
    }
    bool ReadEvents() {
        if(!Take('[')) return false;
        if(Take(']')) return true;
        do {
            if(Events.size()==64 || !Take('{')) return false;
            Event E; uint32_t Seen=0;
            std::unordered_set<std::string> Keys;
            do {
                std::string Key;
                if(!String(Key,MaxUnknownStringBytes) || Keys.size()==MaxFields || !Keys.insert(Key).second || !Take(':')) return false;
                if(Key=="sequence") { Seen|=1; if(!Counter(E.Sequence) || E.Sequence==0) return false; }
                else if(Key=="tick") { Seen|=2; if(!Counter(E.Tick)) return false; }
                else if(Key=="kind") { Seen|=4; std::string Kind; if(!String(Kind,64) || Kind.empty()) return false; }
                else if(Key=="detail") { Seen|=8; std::string Detail; if(!String(Detail,256)) return false; }
                else if(!Skip(3)) return false;
                if(Take('}')) break;
                if(!Take(',')) return false;
            } while(true);
            if(Seen!=15) return false;
            Events.push_back(E);
            if(Take(']')) return true;
            if(!Take(',')) return false;
        } while(true);
    }
};
} // namespace wire_detail

// Failure leaves Out untouched. Counters never pass through a floating-point JSON value.
inline bool DecodeView(const std::string& Json,View& Out) {
    View Candidate;
    wire_detail::Parser Decoder(Json);
    if(!Decoder.Read(Candidate)) return false;
    Out=std::move(Candidate); return true;
}
}} // namespace daedalus::simulation
