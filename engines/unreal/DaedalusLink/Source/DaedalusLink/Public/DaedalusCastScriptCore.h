// SPDX-License-Identifier: MIT

#pragma once

// DCS 1, the cast script: what a realm's NPCs say (REALM-CASTS.md), as branching conversations the dialogue box
// plays (DaedalusDialogueCore.h). One file per realm, Content/Casts/<realm>.dcs; one script per character.
//
//   DCS 1
//   cast GALLERY-CITY
//   who Curator Vell                              a character; what follows is their script until the next 'who'
//   voice 7 1.05                                  optional: pitch 0..11 and rate; default from the name
//   step start                                    a step: the script runs from 'start'
//   say Welcome to the Gallery, painter.          a line (the box pages it)
//   ask Will you look into it? | Of course=yes | Not now=later     a question: choices with the step each leads to
//   step yes
//   say Thank you. Start with the Echo Choir.
//   set heartstone                                remember a flag on this character (saved by the host)
//   end                                           the conversation closes here
//   step later
//   say Come back when you are ready.
//   end
//   if heartstone -> done                         at a step's start: a flag already set jumps elsewhere
//
// A conversation remembers where it is per character (Step) and the flags it set; a second talk starts at 'start'
// again unless an 'if' sends it on. Pure C++17; core-test/cast_script_test.cpp proves it.

#include <algorithm>
#include <cctype>
#include <map>
#include <set>
#include <string>
#include <vector>

namespace daedalus
{
namespace cast
{

struct Choice { std::string Label, Goto; };

struct Node
{
    enum class Kind { Say, Ask, Set, Goto, End, If } K = Kind::Say;
    std::string Text;                // Say/Ask text, Set flag, Goto step, If flag
    std::vector<Choice> Choices;     // Ask
    std::string Target;              // If: the step to jump to
};

struct Step { std::string Id; std::vector<Node> Nodes; };

struct Script
{
    std::string Who;
    int Pitch = -1; double Rate = 1.0;   // -1: from the name
    std::vector<Step> Steps;
    const Step* Find(const std::string& Id) const { for (const Step& S : Steps) if (S.Id == Id) return &S; return nullptr; }
};

struct Cast
{
    std::string Realm;
    std::vector<Script> Scripts;
    const Script* Find(const std::string& Who) const
    {
        for (const Script& S : Scripts) if (Upper(S.Who) == Upper(Who)) return &S;
        return nullptr;
    }
    static std::string Upper(std::string S) { for (char& C : S) C = static_cast<char>(std::toupper(static_cast<unsigned char>(C))); return S; }
    static std::string Trim(std::string S)
    {
        while (!S.empty() && std::isspace(static_cast<unsigned char>(S.back()))) S.pop_back();
        size_t I = 0;
        while (I < S.size() && std::isspace(static_cast<unsigned char>(S[I]))) ++I;
        return S.substr(I);
    }
    static std::vector<std::string> Split(const std::string& S, char Sep)
    {
        std::vector<std::string> Out;
        std::string Cur;
        for (char C : S) { if (C == Sep) { Out.push_back(Trim(Cur)); Cur.clear(); } else Cur += C; }
        Out.push_back(Trim(Cur));
        return Out;
    }
    static bool IsId(const std::string& S)
    {
        if (S.empty() || S.size() > 32) return false;
        for (char C : S) if (!(std::isalnum(static_cast<unsigned char>(C)) || C == '_' || C == '-')) return false;
        return true;
    }

    /** Parse. False with Error "line N: why"; nothing kept on failure. Every goto/if/choice target must exist. */
    bool Parse(const std::string& Text, std::string& Error)
    {
        Cast Out;
        std::vector<std::string> Lines;
        {
            std::string Cur;
            for (char C : Text) { if (C == '\n') { Lines.push_back(Cur); Cur.clear(); } else if (C != '\r') Cur += C; }
            if (!Cur.empty()) Lines.push_back(Cur);
        }
        auto Fail = [&](size_t I, const std::string& Why) { Error = "line " + std::to_string(I + 1) + ": " + Why; return false; };
        if (Lines.empty() || Trim(Lines[0]) != "DCS 1") return Fail(0, "expected 'DCS 1'");
        Script* Cur = nullptr;
        Step* St = nullptr;
        std::vector<std::pair<size_t, std::string>> Refs;   // (line, step id) to check
        for (size_t I = 1; I < Lines.size(); ++I)
        {
            const std::string L = Trim(Lines[I]);
            if (L.empty() || L[0] == '#') continue;
            const size_t Sp = L.find(' ');
            const std::string K = L.substr(0, Sp), Rest = Sp == std::string::npos ? "" : Trim(L.substr(Sp + 1));
            if (K == "cast") { if (Rest.empty()) return Fail(I, "cast needs a name"); Out.Realm = Rest; continue; }
            if (K == "who")
            {
                if (Rest.empty()) return Fail(I, "who needs a name");
                if (Out.Find(Rest)) return Fail(I, "a second script for " + Rest);
                Out.Scripts.push_back(Script());
                Cur = &Out.Scripts.back();
                Cur->Who = Rest;
                St = nullptr;
                continue;
            }
            if (!Cur) return Fail(I, "'" + K + "' before any 'who'");
            if (K == "voice")
            {
                const std::vector<std::string> F = Split(Rest, ' ');
                if (F.empty() || F[0].empty()) return Fail(I, "voice needs a pitch");
                Cur->Pitch = std::atoi(F[0].c_str());
                if (Cur->Pitch < 0 || Cur->Pitch > 11) return Fail(I, "pitch is 0..11");
                if (F.size() > 1 && !F[1].empty()) Cur->Rate = std::atof(F[1].c_str());
                if (Cur->Rate < 0.5 || Cur->Rate > 2.0) return Fail(I, "rate is 0.5..2");
                continue;
            }
            if (K == "step")
            {
                if (!IsId(Rest)) return Fail(I, "bad step id");
                if (Cur->Find(Rest)) return Fail(I, "step " + Rest + " twice in " + Cur->Who);
                Cur->Steps.push_back(Step());
                St = &Cur->Steps.back();
                St->Id = Rest;
                continue;
            }
            if (!St) return Fail(I, "'" + K + "' before any 'step'");
            Node N;
            if (K == "say") { if (Rest.empty()) return Fail(I, "say needs words"); N.K = Node::Kind::Say; N.Text = Rest; }
            else if (K == "ask")
            {
                const std::vector<std::string> P = Split(Rest, '|');
                if (P.size() < 2 || P[0].empty()) return Fail(I, "ask needs words and at least one choice");
                N.K = Node::Kind::Ask; N.Text = P[0];
                for (size_t k = 1; k < P.size(); ++k)
                {
                    const size_t Eq = P[k].find('=');
                    if (Eq == std::string::npos) return Fail(I, "choice '" + P[k] + "' needs =step");
                    Choice C; C.Label = Trim(P[k].substr(0, Eq)); C.Goto = Trim(P[k].substr(Eq + 1));
                    if (C.Label.empty() || !IsId(C.Goto)) return Fail(I, "bad choice '" + P[k] + "'");
                    Refs.push_back({I, C.Goto});
                    N.Choices.push_back(C);
                }
                if (N.Choices.size() > 4) return Fail(I, "at most four choices");
            }
            else if (K == "set") { if (!IsId(Rest)) return Fail(I, "set needs a flag"); N.K = Node::Kind::Set; N.Text = Rest; }
            else if (K == "goto") { if (!IsId(Rest)) return Fail(I, "goto needs a step"); N.K = Node::Kind::Goto; N.Text = Rest; Refs.push_back({I, Rest}); }
            else if (K == "end") { N.K = Node::Kind::End; }
            else if (K == "if")
            {
                const size_t Arrow = Rest.find("->");
                if (Arrow == std::string::npos) return Fail(I, "if needs 'flag -> step'");
                N.K = Node::Kind::If; N.Text = Trim(Rest.substr(0, Arrow)); N.Target = Trim(Rest.substr(Arrow + 2));
                if (!IsId(N.Text) || !IsId(N.Target)) return Fail(I, "bad if");
                Refs.push_back({I, N.Target});
            }
            else return Fail(I, "unknown '" + K + "'");
            St->Nodes.push_back(N);
        }
        if (Out.Realm.empty()) return Fail(Lines.size(), "no cast line");
        for (const Script& S : Out.Scripts)
        {
            if (!S.Find("start")) { Error = S.Who + " has no 'start' step"; return false; }
            for (const Step& T : S.Steps)
            {
                if (T.Nodes.empty()) { Error = S.Who + ": step " + T.Id + " is empty"; return false; }
                for (const Node& N : T.Nodes)
                {
                    if (N.K == Node::Kind::Goto && !S.Find(N.Text)) { Error = S.Who + ": goto " + N.Text + " goes nowhere"; return false; }
                    if (N.K == Node::Kind::If && !S.Find(N.Target)) { Error = S.Who + ": if -> " + N.Target + " goes nowhere"; return false; }
                    for (const Choice& C : N.Choices) if (!S.Find(C.Goto)) { Error = S.Who + ": choice '" + C.Label + "' goes nowhere"; return false; }
                }
            }
        }
        *this = std::move(Out);
        return true;
    }
};

/** What the host does next: speak a line (with choices when asking), or the talk is over. */
struct Beat
{
    bool Over = false;
    std::string Text;
    std::vector<std::string> Choices;
};

/** A conversation with one character: holds the step, the node, and the flags. Save() / Restore() are one line. */
class Conversation
{
public:
    void Bind(const Script* S) { Sc = S; StepId = "start"; Node = 0; }
    const Script* Bound() const { return Sc; }
    const std::set<std::string>& Flags() const { return Set; }
    bool Has(const std::string& Flag) const { return Set.count(Flag) > 0; }

    /** Start (or continue) talking: the next beat. */
    Beat Talk()
    {
        if (!Sc) return Over();
        if (Node == 0) ApplyIfs();   // at a step's start: an 'if' may send us elsewhere
        return Advance();
    }

    /** The player picked a choice of the last Ask. */
    Beat Picked(int Index)
    {
        if (!Sc || LastAsk.empty()) return Over();
        const std::vector<Choice>& C = LastAsk;
        if (Index < 0 || Index >= static_cast<int>(C.size())) return Over();
        const std::string To = C[static_cast<size_t>(Index)].Goto;
        LastAsk.clear();
        Jump(To);
        return Talk();
    }

    std::string Save() const
    {
        std::string S = StepId + ":" + std::to_string(Node);
        for (const std::string& F : Set) S += " " + F;
        return S;
    }
    void Restore(const std::string& Text)
    {
        Set.clear();
        std::string Tok;
        bool First = true;
        for (size_t i = 0; i <= Text.size(); ++i)
        {
            if (i == Text.size() || Text[i] == ' ')
            {
                if (!Tok.empty())
                {
                    if (First) { const size_t C = Tok.find(':'); StepId = Tok.substr(0, C); Node = C == std::string::npos ? 0 : std::atoi(Tok.c_str() + C + 1); First = false; }
                    else Set.insert(Tok);
                }
                Tok.clear();
            }
            else Tok += Text[i];
        }
        if (!Sc || !Sc->Find(StepId)) { StepId = "start"; Node = 0; }
    }
    std::string Where() const { return StepId + ":" + std::to_string(Node); }

private:
    Beat Over() { Beat B; B.Over = true; StepId = "start"; Node = 0; LastAsk.clear(); return B; }
    void Jump(const std::string& To) { StepId = To; Node = 0; ApplyIfs(); }
    void ApplyIfs()
    {
        for (int Guard = 0; Guard < 16; ++Guard)
        {
            const Step* S = Sc->Find(StepId);
            if (!S || S->Nodes.empty() || S->Nodes[0].K != Node::Kind::If || !Has(S->Nodes[0].Text)) return;
            StepId = S->Nodes[0].Target;
            Node = 0;
        }
    }
    Beat Advance()
    {
        for (int Guard = 0; Guard < 64; ++Guard)
        {
            const Step* S = Sc->Find(StepId);
            if (!S) return Over();
            if (Node >= static_cast<int>(S->Nodes.size())) return Over();   // a step that runs out ends the talk
            const daedalus::cast::Node& N = S->Nodes[static_cast<size_t>(Node)];
            ++Node;
            switch (N.K)
            {
            case daedalus::cast::Node::Kind::Say: { Beat B; B.Text = N.Text; return B; }
            case daedalus::cast::Node::Kind::Ask: { Beat B; B.Text = N.Text; for (const Choice& C : N.Choices) B.Choices.push_back(C.Label); LastAsk = N.Choices; return B; }
            case daedalus::cast::Node::Kind::Set: Set.insert(N.Text); break;
            case daedalus::cast::Node::Kind::Goto: Jump(N.Text); break;
            case daedalus::cast::Node::Kind::If: if (Has(N.Text)) Jump(N.Target); break;
            case daedalus::cast::Node::Kind::End: return Over();
            }
        }
        return Over();
    }

    const Script* Sc = nullptr;
    std::string StepId = "start";
    int Node = 0;
    std::set<std::string> Set;
    std::vector<Choice> LastAsk;
};

} // namespace cast
} // namespace daedalus
