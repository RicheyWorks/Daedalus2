// SPDX-License-Identifier: MIT
#pragma once

#include "DaedalusRealmCore.h"
#include <algorithm>
#include <array>
#include <cmath>
#include <string>
#include <utility>
#include <vector>

/**
 * Optional, engine-free Portal input translation. It emits only the existing realm::Button edges;
 * it does not install mappings, discover a controller, persist settings, or change game authority.
 * NintendoLabels is a presentation choice, not proof that an unknown device uses these key names.
 * Original design choices: separate layout/labels, complete validated remaps, stick hysteresis,
 * combined held-source tracking and context-correct prompts. Source-only, currently UNVALIDATED.
 */
namespace daedalus::portal_controls {

using Button = realm::Button;
inline constexpr const char* Version = "portal-controls/v1";
inline constexpr std::size_t MaxBindings = 64;
inline constexpr std::array<Button, 7> Buttons = {
    Button::Up, Button::Down, Button::Left, Button::Right, Button::A, Button::B, Button::Start
};

enum class Family { Keyboard, Pad, Observed };
enum class Labels { Position, NintendoLabels, XboxLabels };
enum class Layout { ExistingBottomConfirm, EastConfirm };
// Derived from public TopBox(), never from Realm::Busy (which combines several different states).
enum class Context {
    Disabled, Title, Field, CommandGrid, List, Message, Status,
    BattleIntro, BattleCommand, BattleTarget, BattlePlayback, BattleEnding
};

struct Binding {
    std::string Key;       // Existing FKey name, or an explicitly observed host key; no guessed USB numbers.
    Button Intent = Button::A;
    Family Source = Family::Observed;
    std::string Label;     // Optional display name for a remapped/observed key.
};

struct Stick {
    std::string XKey = "Gamepad_LeftX", YKey = "Gamepad_LeftY";
    bool SwapAxes = false, InvertX = false, InvertY = false;
    double PressThreshold = 0.55, ReleaseThreshold = 0.40, SwitchBias = 0.10;
};

struct Profile {
    std::string Name = "Portal Legacy";
    Labels PromptLabels = Labels::Position;
    std::vector<Binding> Bindings;
    Stick Movement;

    /** Preserve the current keyboard controls. EastConfirm swaps pad confirm/back by physical position. */
    static Profile Preset(Layout L = Layout::ExistingBottomConfirm, Labels Style = Labels::Position)
    {
        Profile P;
        P.Name = L == Layout::EastConfirm ? "Portal East Confirm" : "Portal Legacy";
        P.PromptLabels = Style;
        P.Bindings = {
            {"Up", Button::Up, Family::Keyboard, "Up"}, {"W", Button::Up, Family::Keyboard, "W"},
            {"Down", Button::Down, Family::Keyboard, "Down"}, {"S", Button::Down, Family::Keyboard, "S"},
            {"Left", Button::Left, Family::Keyboard, "Left"}, {"A", Button::Left, Family::Keyboard, "A"},
            {"Right", Button::Right, Family::Keyboard, "Right"}, {"D", Button::Right, Family::Keyboard, "D"},
            {"Enter", Button::A, Family::Keyboard, "Enter"}, {"SpaceBar", Button::A, Family::Keyboard, "Space"},
            {"Z", Button::A, Family::Keyboard, "Z"}, {"E", Button::A, Family::Keyboard, "E"},
            {"BackSpace", Button::B, Family::Keyboard, "Backspace"}, {"X", Button::B, Family::Keyboard, "X"},
            {"Q", Button::B, Family::Keyboard, "Q"}, {"Tab", Button::Start, Family::Keyboard, "Tab"},
            {"Gamepad_DPad_Up", Button::Up, Family::Pad, "D-pad up"},
            {"Gamepad_DPad_Down", Button::Down, Family::Pad, "D-pad down"},
            {"Gamepad_DPad_Left", Button::Left, Family::Pad, "D-pad left"},
            {"Gamepad_DPad_Right", Button::Right, Family::Pad, "D-pad right"},
            {"Gamepad_FaceButton_Bottom", L == Layout::EastConfirm ? Button::B : Button::A, Family::Pad, ""},
            {"Gamepad_FaceButton_Right", L == Layout::EastConfirm ? Button::A : Button::B, Family::Pad, ""},
            {"Gamepad_Special_Right", Button::Start, Family::Pad, "Menu"}
        };
        return P;
    }

    const Binding* Find(const std::string& Key) const
    {
        auto It = std::find_if(Bindings.begin(), Bindings.end(), [&](const Binding& B) { return B.Key == Key; });
        return It == Bindings.end() ? nullptr : &*It;
    }

    /** Validate a complete replacement before changing any held input. No settings file is written. */
    bool Validate(std::string& Error) const
    {
        Error.clear();
        if (Name.empty() || Name.size() > 48 || Bindings.empty() || Bindings.size() > MaxBindings)
            { Error = "Profile needs a name and one to sixty-four bindings"; return false; }
        for (std::size_t I = 0; I < Bindings.size(); ++I)
        {
            const Binding& B = Bindings[I];
            if (B.Key.empty() || B.Key.size() > 96 || B.Label.size() > 48
                || std::find(Buttons.begin(), Buttons.end(), B.Intent) == Buttons.end())
                { Error = "Invalid key, label or Portal button"; return false; }
            if (B.Source != Family::Keyboard && B.Source != Family::Pad && B.Source != Family::Observed)
                { Error = "Invalid binding family"; return false; }
            for (std::size_t J = 0; J < I; ++J)
                if (Bindings[J].Key == B.Key) { Error = "Each physical key must have only one intent"; return false; }
        }
        for (Button B : Buttons)
            if (std::none_of(Bindings.begin(), Bindings.end(), [&](const Binding& K) { return K.Intent == B; }))
                { Error = "A complete profile must retain movement, confirm, back and menu"; return false; }
        if (PromptLabels != Labels::Position && PromptLabels != Labels::NintendoLabels && PromptLabels != Labels::XboxLabels)
            { Error = "Invalid prompt label style"; return false; }
        const Stick& S = Movement;
        const bool Enabled = !S.XKey.empty() || !S.YKey.empty();
        if (Enabled && (S.XKey.empty() || S.YKey.empty() || S.XKey == S.YKey
            || S.XKey.size() > 96 || S.YKey.size() > 96 || Find(S.XKey) || Find(S.YKey)))
            { Error = "Movement axes must be two distinct unmapped physical keys"; return false; }
        if (!std::isfinite(S.PressThreshold) || !std::isfinite(S.ReleaseThreshold) || !std::isfinite(S.SwitchBias)
            || S.PressThreshold < 0.1 || S.PressThreshold > 1.0 || S.ReleaseThreshold < 0.0
            || S.ReleaseThreshold >= S.PressThreshold || S.SwitchBias < 0.0 || S.SwitchBias > 1.0)
            { Error = "Invalid stick thresholds"; return false; }
        return true;
    }

    /** Replace or append one mapping; validate atomically and keep the old profile on refusal. */
    bool Remap(const std::string& Key, Button Intent, Family Source, const std::string& Display, std::string& Error)
    {
        Profile Candidate = *this;
        auto It = std::find_if(Candidate.Bindings.begin(), Candidate.Bindings.end(),
                               [&](const Binding& B) { return B.Key == Key; });
        Binding B{Key, Intent, Source, Display};
        if (It == Candidate.Bindings.end()) Candidate.Bindings.push_back(std::move(B));
        else *It = std::move(B);
        if (!Candidate.Validate(Error)) return false;
        *this = std::move(Candidate);
        return true;
    }

    bool Unbind(const std::string& Key, std::string& Error)
    {
        Profile Candidate = *this;
        Candidate.Bindings.erase(std::remove_if(Candidate.Bindings.begin(), Candidate.Bindings.end(),
                                                [&](const Binding& B) { return B.Key == Key; }), Candidate.Bindings.end());
        if (!Candidate.Validate(Error)) return false;
        *this = std::move(Candidate);
        return true;
    }

    std::string Display(const Binding& B) const
    {
        if (!B.Label.empty()) return B.Label;
        if (B.Key == "Gamepad_FaceButton_Bottom")
            return PromptLabels == Labels::NintendoLabels ? "B (south)" : PromptLabels == Labels::XboxLabels ? "A (south)" : "South";
        if (B.Key == "Gamepad_FaceButton_Right")
            return PromptLabels == Labels::NintendoLabels ? "A (east)" : PromptLabels == Labels::XboxLabels ? "B (east)" : "East";
        if (B.Key == "Gamepad_FaceButton_Top")
            return PromptLabels == Labels::NintendoLabels ? "X (north)" : PromptLabels == Labels::XboxLabels ? "Y (north)" : "North";
        if (B.Key == "Gamepad_FaceButton_Left")
            return PromptLabels == Labels::NintendoLabels ? "Y (west)" : PromptLabels == Labels::XboxLabels ? "X (west)" : "West";
        return B.Key;
    }
};

struct Prompt {
    Button Intent = Button::A;
    std::string Key, Glyph, Action;
    bool Visible = false;
};

/** Existing public UI inspection includes message boxes that take precedence over the battle phase. */
inline Context ContextOf(const realm::Realm& Game)
{
    if (!Game.IsLoaded()) return Context::Disabled;
    const std::string Box = Game.TopBox();
    if (Box == "TITLE") return Context::Title;
    if (Box == "MESSAGE") return Context::Message;
    if (Box == "STATUS") return Context::Status;
    if (Box == "MENU") return Context::CommandGrid;
    if (Box == "ITEMS" || Box == "MEMBERS" || Box == "SPELLS" || Box == "EQUIP"
        || Box == "SHOP" || Box == "BUY" || Box == "SELL" || Box == "YESNO") return Context::List;
    if (Game.CurrentMode() == realm::Mode::Battle)
    {
        if (Box == "INTRO") return Context::BattleIntro;
        if (Box == "COMMAND") return Context::BattleCommand;
        if (Box == "TARGET") return Context::BattleTarget;
        if (Box == "PLAY") return Context::BattlePlayback;
        if (Box == "ENDING") return Context::BattleEnding;
    }
    else if (Box == "NONE") return Context::Field;
    return Context::Disabled;
}

/** Labels follow the actual remap, while actions follow the established Realm::Press behavior. */
inline Prompt DescribePrompt(const Profile& P, Button B, Context C, Family Preferred = Family::Pad)
{
    Prompt Out;
    Out.Intent = B;
    if (C == Context::Disabled) return Out;
    const Binding* Chosen = nullptr;
    for (const Binding& K : P.Bindings)
        if (K.Intent == B && (!Chosen || K.Source == Preferred))
        { Chosen = &K; if (K.Source == Preferred) break; }
    if (!Chosen) return Out;
    Out.Key = Chosen->Key;
    Out.Glyph = P.Display(*Chosen);
    if (B == Button::Start)
    {
        if (C == Context::Title) Out.Action = "Continue";
        else if (C == Context::Field) Out.Action = "Commands";
    }
    else if (B == Button::A || B == Button::B)
    {
        if (C == Context::Title || C == Context::BattleIntro) Out.Action = "Continue";
        else if (C == Context::Field) Out.Action = B == Button::A ? "Interact" : "Commands";
        else if (C == Context::Message) Out.Action = "Continue";
        else if (C == Context::Status) Out.Action = "Close";
        else if (C == Context::BattlePlayback) Out.Action = "Advance faster";
        else if (C == Context::BattleEnding) Out.Action = "Continue when ready";
        else if (C == Context::BattleCommand) Out.Action = B == Button::A ? "Confirm" : "Undo choice";
        else if (C == Context::BattleTarget) Out.Action = B == Button::A ? "Confirm target" : "Back to commands";
        else if (C == Context::CommandGrid || C == Context::List) Out.Action = B == Button::A ? "Select" : "Back";
    }
    else if (C == Context::Field || C == Context::CommandGrid || C == Context::BattleTarget
        || ((C == Context::List || C == Context::BattleCommand) && (B == Button::Up || B == Button::Down)))
    {
        const char* Direction = B == Button::Up ? "up" : B == Button::Down ? "down" : B == Button::Left ? "left" : "right";
        Out.Action = std::string(C == Context::Field ? "Move " : "Choose ") + Direction;
    }
    Out.Visible = !Out.Action.empty();
    return Out;
}

struct Edge { Button Intent = Button::A; bool Pressed = false; };
struct Dispatch { bool Consumed = false; std::vector<Edge> Edges; };

/**
 * Per-focus-session held-source translator, independent of device enumeration or Unreal input setup.
 * The host forwards returned edges exactly once, then lets the existing core own movement timing.
 */
class Translator {
public:
    Translator() : Current(Profile::Preset()) { }
    const Profile& GetProfile() const { return Current; }

    /** On successful replacement, dispatch all returned releases before processing any new events. */
    bool Replace(Profile P, std::vector<Edge>& Releases, std::string& Error)
    {
        Releases.clear();
        if (!P.Validate(Error)) return false;
        Releases = ReleaseAll();
        Current = std::move(P);
        return true;
    }

    Dispatch KeyDown(const std::string& Key, bool IsRepeat = false)
    {
        const Binding* B = Current.Find(Key);
        if (!B) return {};
        Dispatch Out{true, {}};
        if (IsRepeat || std::any_of(Held.begin(), Held.end(), [&](const Binding& K) { return K.Key == Key; })) return Out;
        const bool Already = Active(B->Intent);
        Held.push_back(*B);
        if (!Already) Out.Edges.push_back({B->Intent, true});
        return Out;
    }

    Dispatch KeyUp(const std::string& Key)
    {
        auto It = std::find_if(Held.begin(), Held.end(), [&](const Binding& B) { return B.Key == Key; });
        Dispatch Out{It != Held.end() || Current.Find(Key) != nullptr, {}};
        if (It == Held.end()) return Out;
        const Button B = It->Intent;
        Held.erase(It);
        if (!Active(B)) Out.Edges.push_back({B, false});
        return Out;
    }

    Dispatch Axis(const std::string& Key, double Value)
    {
        const Stick& S = Current.Movement;
        if ((S.XKey.empty() && S.YKey.empty()) || (Key != S.XKey && Key != S.YKey)) return {};
        Dispatch Out{true, {}};
        if (!std::isfinite(Value))
        {
            X = Y = 0.0;
            ChangeStick(-1, Out.Edges);
            return Out;
        }
        Value = std::clamp(Value, -1.0, 1.0);
        if (Key == S.XKey) X = Value; else Y = Value;
        double DX = S.SwapAxes ? Y : X, DY = S.SwapAxes ? X : Y;
        if (S.InvertX) DX = -DX;
        if (S.InvertY) DY = -DY;
        const double AX = std::abs(DX), AY = std::abs(DY);
        if (std::max(AX, AY) <= S.ReleaseThreshold) ChangeStick(-1, Out.Edges);
        else
        {
            const int Candidate = AX > AY ? (DX > 0.0 ? 3 : 2) : (DY > 0.0 ? 0 : 1);
            const double Own = Direction == 0 ? DY : Direction == 1 ? -DY : Direction == 2 ? -DX : DX;
            if (Direction >= 0 && Own > S.ReleaseThreshold
                && (Candidate == Direction || std::max(AX, AY) < S.PressThreshold
                    || std::max(AX, AY) <= Own + S.SwitchBias)) return Out;
            ChangeStick(std::max(AX, AY) >= S.PressThreshold ? Candidate : -1, Out.Edges);
        }
        return Out;
    }

    /** Focus loss, disconnect, portal exit or accepted remap: prevent a held direction leaking onward. */
    std::vector<Edge> ReleaseAll()
    {
        std::vector<Edge> Out;
        for (Button B : Buttons) if (Active(B)) Out.push_back({B, false});
        Held.clear();
        Direction = -1;
        X = Y = 0.0;
        return Out;
    }

    /** Optional host convenience; this calls only the established core button API, never game-specific commands. */
    static void Forward(realm::Realm& Game, const std::vector<Edge>& Edges)
    {
        for (const Edge& E : Edges) { if (E.Pressed) Game.Press(E.Intent); else Game.Release(E.Intent); }
    }

private:
    Profile Current;
    std::vector<Binding> Held;
    double X = 0.0, Y = 0.0;
    int Direction = -1;

    static Button DirectionButton(int D)
    {
        static constexpr std::array<Button, 4> Directions = {Button::Up, Button::Down, Button::Left, Button::Right};
        return Directions[static_cast<std::size_t>(D)];
    }

    bool Active(Button B) const
    {
        return (Direction >= 0 && DirectionButton(Direction) == B)
            || std::any_of(Held.begin(), Held.end(), [&](const Binding& K) { return K.Intent == B; });
    }

    void ChangeStick(int Next, std::vector<Edge>& Edges)
    {
        if (Next == Direction) return;
        const int Old = Direction;
        Direction = -1;
        if (Old >= 0 && !Active(DirectionButton(Old))) Edges.push_back({DirectionButton(Old), false});
        const bool Already = Next >= 0 && Active(DirectionButton(Next));
        Direction = Next;
        if (Next >= 0 && !Already) Edges.push_back({DirectionButton(Next), true});
    }
};

} // namespace daedalus::portal_controls
