// SPDX-License-Identifier: MIT
#pragma once
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <string>
#include <vector>

namespace daedalus { namespace desktop {
struct Vec { double X = 0, Y = 0; };
struct Rect {
    double X = 0, Y = 0, W = 0, H = 0;
    bool Overlaps(const Rect& B) const { return X < B.X+B.W && X+W > B.X && Y < B.Y+B.H && Y+H > B.Y; }
    bool Contains(double Px, double Py) const { return Px >= X && Px < X+W && Py >= Y && Py < Y+H; }
};
struct Color { std::uint8_t R = 255, G = 255, B = 255, A = 255; };
inline constexpr Color White{255,255,255,255}, Black{0,0,0,255};

// One source-style 60 Hz step. Digital direction and analog axes are separate:
// latest Pong supports both keyboard and left-stick input in the same frame.
struct Input {
    bool Left = false, Right = false, Up = false, Down = false;
    bool PadLeft = false, PadRight = false, PadUp = false, PadDown = false;
    double AxisX = 0, AxisY = 0;
    bool Fire = false, Jump = false, Action = false, Dash = false;
    bool FirePressed = false, JumpPressed = false, ActionPressed = false, DashPressed = false;
};
struct Status {
    std::int64_t Score = 0;
    int Lives = 0;
    bool Over = false, Won = false;
    std::string Note;
};
enum class Shape { Rectangle, Circle, Line, Triangle, Text };
struct DrawCommand {
    Shape Kind = Shape::Rectangle;
    Vec A, B, C;
    Color Tint;
    double Size = 1;
    std::string Label;
};
struct Frame {
    static constexpr std::size_t MaxCommands = 4096;
    double Width = 800, Height = 600;
    Color Background = Black;
    std::vector<DrawCommand> Commands;
    void Clear(double W = 800, double H = 600, Color Bg = Black) {
        Width=W; Height=H; Background=Bg; Commands.clear();
    }
    void AddRect(double X,double Y,double W,double H,Color Tint) {
        if(Commands.size()<MaxCommands) Commands.push_back({Shape::Rectangle,{X,Y},{W,H},{},Tint,1,{}});
    }
    void AddCircle(double X,double Y,double Radius,Color Tint) {
        if(Commands.size()<MaxCommands) Commands.push_back({Shape::Circle,{X,Y},{},{},Tint,Radius,{}});
    }
    void AddLine(double X,double Y,double X2,double Y2,Color Tint,double Thickness=1) {
        if(Commands.size()<MaxCommands) Commands.push_back({Shape::Line,{X,Y},{X2,Y2},{},Tint,Thickness,{}});
    }
    void AddTriangle(Vec A,Vec B,Vec C,Color Tint) {
        if(Commands.size()<MaxCommands) Commands.push_back({Shape::Triangle,A,B,C,Tint,1,{}});
    }
    void AddText(double X,double Y,const std::string& Label,Color Tint=White,double FontSize=20) {
        if(Commands.size()<MaxCommands) Commands.push_back({Shape::Text,{X,Y},{},{},Tint,FontSize,Label.substr(0,256)});
    }
};
class Game {
public:
    virtual ~Game() = default;
    virtual void Reset(std::uint32_t Seed) = 0;
    virtual void Step(const Input& Controls) = 0;
    virtual void Render(Frame& Out) const = 0;
    virtual Status GetStatus() const = 0;
    // Optional source-specific facilities. Hosts use virtual dispatch, never UE-disabled RTTI.
    virtual void EnterTitle() {}
    // Ordered non-repeat keyboard events: Up,Down,Left,Right,B,A,Enter,Space,R,other.
    // True means a run transition: discard semantic edges from the old state.
    virtual bool SourceKeyDown(int) { return false; }
    // Separate controller events: 0 A, 1 Start. True consumes a source action,
    // keeping controller events out of keyboard cheat tracking.
    virtual bool SourceControllerButton(int) { return false; }
    // Logical canvas coordinates, button 0 left / 1 right / 2 middle. No fixed step.
    // True consumes one pointer action; hosts discard old held/semantic input.
    virtual bool SourcePointerButton(double,double,int) { return false; }
    virtual bool OwnPause(bool) { return false; }
    virtual bool IsCorePaused() const { return false; }
    virtual std::string SaveState() const { return {}; }
    virtual bool RestoreState(const std::string&,std::uint32_t) { return false; }
    // Games with an exact-board save retain the original restart/first-reveal seed.
    virtual std::uint32_t SeedAfterRestore(std::uint32_t Fallback) const { return Fallback; }
    virtual bool SavePending() const { return false; }
    virtual void ClearSavePending() {}
    virtual bool WantsExit() const { return false; }
    virtual bool SetOption(int,std::uint32_t) { return false; }
    virtual int GetOption() const { return -1; }
};
// Portable random stream is deliberately different from Python random. Parity
// tests inject fixed source cases; this stream makes native sessions replayable.
class Random {
    std::uint32_t State = 730;
public:
    static std::uint32_t InitialState(std::uint32_t Value) { return Value ? Value : 0x6d2b79f5u; }
    void Seed(std::uint32_t Value) { State=InitialState(Value); }
    std::uint32_t Next() { State^=State<<13; State^=State>>17; State^=State<<5; return State; }
    double Unit() { return static_cast<double>(Next()) / 4294967296.0; }
    int Int(int Low,int High) { return High<=Low ? Low : Low+static_cast<int>(Next()%static_cast<std::uint32_t>(High-Low+1)); }
    double Between(double Low,double High) { return Low+(High-Low)*Unit(); }
};
inline double Axis(double Value) { return std::isfinite(Value) ? std::max(-1.0,std::min(1.0,Value)) : 0; }
inline double Horizontal(const Input& I) { return (I.Right ? 1.0 : 0.0)-(I.Left ? 1.0 : 0.0)+(I.PadRight ? 1.0 : 0.0)-(I.PadLeft ? 1.0 : 0.0)+Axis(I.AxisX); }
inline double Vertical(const Input& I) { return (I.Down ? 1.0 : 0.0)-(I.Up ? 1.0 : 0.0)+(I.PadDown ? 1.0 : 0.0)-(I.PadUp ? 1.0 : 0.0)+Axis(I.AxisY); }
inline double Clamp(double V,double Low,double High) { return std::max(Low,std::min(High,V)); }
inline double Distance(double X,double Y,double X2,double Y2) { const double Dx=X-X2,Dy=Y-Y2; return std::sqrt(Dx*Dx+Dy*Dy); }
}} // daedalus::desktop
