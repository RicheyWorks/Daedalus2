// SPDX-License-Identifier: MIT
#pragma once
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <string>
#include <vector>

// Portable consumer policy for ai-dungeon-master /v2. No combat, maze or reward engine.
namespace DaedalusDungeon {
constexpr std::size_t MaxBodyBytes = 65536;
struct Member { std::string Name, Role; int Hp=0, MaxHp=0; bool Alive=false; };
struct Snapshot {
    std::vector<Member> Party;
    std::vector<std::string> Choices, History;
    std::string Location, QuestTitle, SceneId, SceneDescription, PlayHint;
    int Chaos=0;
    bool Combat=false, HasQuest=false, Completed=false, Failed=false;
    double Progress=0;
};
inline bool Text(const std::string& S, std::size_t Limit, bool Multiline=false) {
    if (S.size()>Limit) return false;
    for (unsigned char C:S) if (C<32 && !(Multiline && (C=='\n'||C=='\r'||C=='\t'))) return false;
    return true;
}
inline std::string Fold(std::string S) {
    for (char& C:S) if(C>='A' && C<='Z') C=char(C-'A'+'a');
    return S;
}
inline bool Valid(const Snapshot& S) {
    if(S.Party.empty() || S.Party.size()>16 || S.Choices.size()>64 || S.History.size()>30 || S.Chaos<0) return false;
    if(!Text(S.Location,256) || !Text(S.PlayHint,4096,true)) return false;
    for(const auto& M:S.Party)
        if(M.Name.empty() || !Text(M.Name,256) || !Text(M.Role,128) || M.MaxHp<=0 || M.Hp<0 || M.Hp>M.MaxHp || M.Alive!=(M.Hp>0)) return false;
    std::vector<std::string> Seen;
    for(const auto& C:S.Choices) {
        if(C.empty() || !Text(C,512) || C.find_first_not_of(' ')==std::string::npos || C.front()==' ' || C.back()==' ') return false;
        auto Key=Fold(C);
        if(std::find(Seen.begin(),Seen.end(),Key)!=Seen.end()) return false;
        Seen.push_back(Key);
    }
    for(const auto& H:S.History) if(!Text(H,4096,true)) return false;
    return !S.HasQuest || (Text(S.QuestTitle,512) && Text(S.SceneId,256) && Text(S.SceneDescription,8192,true)
        && std::isfinite(S.Progress) && S.Progress>=0 && S.Progress<=1 && !(S.Completed && S.Failed));
}
inline std::string Quote(const std::string& S) {
    std::string Out="\"";
    constexpr char Hex[]="0123456789abcdef";
    for(unsigned char C:S) {
        if(C=='\"'||C=='\\') {Out+='\\';Out+=char(C);}
        else if(C<32) {Out+="\\u00";Out+=Hex[C>>4];Out+=Hex[C&15];}
        else Out+=char(C);
    }
    return Out+'\"';
}
enum class RequestKind { None, Status, Action };
class Session {
    Snapshot Last;
    std::uint64_t Serial=0, Pending=0;
    RequestKind Kind=RequestKind::None;
    bool HasLast=false, Uncertain=false;
public:
    const Snapshot& State() const {return Last;}
    bool Ready() const {return HasLast && !Uncertain && !Pending;}
    bool Busy() const {return Pending!=0;}
    bool ActionUncertain() const {return Uncertain;}
    std::uint64_t BeginStatus() {
        if(Pending) return 0;
        Kind=RequestKind::Status;return Pending=++Serial;
    }
    std::uint64_t BeginAction(std::size_t Index, std::string& Body) {
        Body.clear();
        if(!Ready() || Index>=Last.Choices.size()) return 0;
        Body="{\"choiceLabel\":"+Quote(Last.Choices[Index])+"}";
        Kind=RequestKind::Action;return Pending=++Serial;
    }
    bool Accept(std::uint64_t Id, int Version, const std::string& Type, const Snapshot& Value) {
        if(!Pending || Id!=Pending) return false;
        if(Version!=1 || Type!="game_status" || !Valid(Value)) {Fail(Id);return false;}
        Last=Value;HasLast=true;Pending=0;Kind=RequestKind::None;
        // A later read does NOT prove an earlier timed-out action never committed.
        return true;
    }
    void Fail(std::uint64_t Id) {
        if(!Pending || Id!=Pending) return;
        if(Kind==RequestKind::Action) Uncertain=true;
        Pending=0;Kind=RequestKind::None;
    }
    // Only for a genuinely new verified backend session, not retrying an action.
    void NewSession() {++Serial;Pending=0;Kind=RequestKind::None;Last={};HasLast=false;Uncertain=false;}
};
}
