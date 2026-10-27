// SPDX-License-Identifier: MIT
// G13 GAL01 living paintings, C++17 port of com.daedalus.world.gallery (Pigment, PigmentPalette, ColourKnowledge,
// LivingPainting) for ADaedalusLivingPainting. Header-only, no engine types, no exceptions (Unreal game targets build
// without them): where Java throws, this returns BadCell / false / an invalid mural. The mural RNG is a bit-exact
// port of java.util.SplittableRandom(seed).nextInt(bound), so every client paints the same mural as the server.
// core-test/living_painting_core_test.cpp --write emits living_painting_parity.txt; LivingPaintingParityTest
// rebuilds the same lines from the Java classes.
#pragma once

#include <cstdint>
#include <string>
#include <vector>

namespace daedalus::gallery {

enum class Pigment : int { Red, Yellow, Blue, Orange, Green, Violet };
constexpr int kPigments = 6;
inline const char* PigmentName(Pigment P)
{
    static const char* k[] = {"RED", "YELLOW", "BLUE", "ORANGE", "GREEN", "VIOLET"};
    return k[static_cast<int>(P)];
}
inline bool IsPrimary(Pigment P) { return P == Pigment::Red || P == Pigment::Yellow || P == Pigment::Blue; }
// Secondary pigments: the two primaries they are mixed from (false for primaries).
inline bool Components(Pigment P, Pigment& A, Pigment& B)
{
    switch (P)
    {
        case Pigment::Orange: A = Pigment::Red; B = Pigment::Yellow; return true;
        case Pigment::Green: A = Pigment::Yellow; B = Pigment::Blue; return true;
        case Pigment::Violet: A = Pigment::Red; B = Pigment::Blue; return true;
        default: return false;
    }
}
// Gallery City chemistry: ingredient -> pigment, or -1.
inline int FromIngredient(const std::string& I)
{
    if (I == "beet" || I == "cherry") { return 0; }
    if (I == "dawnleaf") { return 1; }
    if (I == "cobalt") { return 2; }
    if (I == "orange") { return 3; }
    if (I == "copper") { return 4; }
    return -1;
}

// java.util.SplittableRandom, the parts LivingPainting uses (constructor(seed), nextInt(bound)).
class SplitRandom
{
public:
    explicit SplitRandom(int64_t InSeed) : State(static_cast<uint64_t>(InSeed)) {}
    int32_t NextInt(int32_t Bound)
    {
        int32_t R = Mix32(NextSeed());
        const int32_t M = Bound - 1;
        if ((Bound & M) == 0) { return R & M; }
        for (int32_t U = static_cast<int32_t>(static_cast<uint32_t>(R) >> 1);; U = static_cast<int32_t>(static_cast<uint32_t>(Mix32(NextSeed())) >> 1))
        {
            R = U % Bound;
            // Java: u + m - r < 0 in wrapping int arithmetic
            if (static_cast<int32_t>(static_cast<uint32_t>(U) + static_cast<uint32_t>(M) - static_cast<uint32_t>(R)) >= 0) { return R; }
        }
    }

private:
    uint64_t NextSeed() { return State += 0x9e3779b97f4a7c15ULL; }
    static int32_t Mix32(uint64_t Z)
    {
        Z = (Z ^ (Z >> 33)) * 0x62a9d9ed799705f5ULL;
        return static_cast<int32_t>(static_cast<uint32_t>(((Z ^ (Z >> 28)) * 0xcb24d0a5c88c35b3ULL) >> 32));
    }
    uint64_t State;
};

enum class Ability : int { EmberLantern, CanalTint, Sunwash, TrellisVine, DuskReading, PrismSight };
constexpr int kAbilities = 6;
inline const char* AbilityName(Ability A)
{
    static const char* k[] = {"EMBER_LANTERN", "CANAL_TINT", "SUNWASH", "TRELLIS_VINE", "DUSK_READING", "PRISM_SIGHT"};
    return k[static_cast<int>(A)];
}

class Knowledge
{
public:
    static constexpr int kKnowAt = 3;
    void Learn(Pigment P) { ++Strokes[static_cast<int>(P)]; }
    int StrokesOf(Pigment P) const { return Strokes[static_cast<int>(P)]; }
    bool Knows(Pigment P) const { return StrokesOf(P) >= kKnowAt; }
    bool CanMix(Pigment Secondary) const
    {
        Pigment A, B;
        return Components(Secondary, A, B) && Knows(A) && Knows(B);
    }
    bool Has(Ability A) const
    {
        switch (A)
        {
            case Ability::EmberLantern: return Knows(Pigment::Red);
            case Ability::CanalTint: return Knows(Pigment::Blue);
            case Ability::Sunwash: return Knows(Pigment::Yellow);
            case Ability::TrellisVine: return Knows(Pigment::Green);
            case Ability::DuskReading: return Knows(Pigment::Violet);
            case Ability::PrismSight: return Knows(Pigment::Red) && Knows(Pigment::Yellow) && Knows(Pigment::Blue);
        }
        return false;
    }

private:
    int Strokes[kPigments] = {};
};

enum class PaletteResult { Ok, UnknownIngredient, NotKnown, MissingPrimary, Full };
inline const char* PaletteResultName(PaletteResult R)
{
    static const char* k[] = {"OK", "UNKNOWN_INGREDIENT", "NOT_KNOWN", "MISSING_PRIMARY", "FULL"};
    return k[static_cast<int>(R)];
}

class Palette
{
public:
    static constexpr int kMaxUnits = 999;
    PaletteResult Grind(const std::string& Ingredient)
    {
        const int P = FromIngredient(Ingredient);
        if (P < 0) { return PaletteResult::UnknownIngredient; }
        if (Units[P] >= kMaxUnits) { return PaletteResult::Full; }
        ++Units[P];
        return PaletteResult::Ok;
    }
    PaletteResult Mix(Pigment Secondary, const Knowledge& K)
    {
        Pigment A, B;
        if (IsPrimary(Secondary) || !K.CanMix(Secondary) || !Components(Secondary, A, B)) { return PaletteResult::NotKnown; }
        if (Count(A) == 0 || Count(B) == 0) { return PaletteResult::MissingPrimary; }
        if (Count(Secondary) >= kMaxUnits) { return PaletteResult::Full; }
        --Units[static_cast<int>(A)];
        --Units[static_cast<int>(B)];
        ++Units[static_cast<int>(Secondary)];
        return PaletteResult::Ok;
    }
    bool Spend(Pigment P)
    {
        if (Units[static_cast<int>(P)] == 0) { return false; }
        --Units[static_cast<int>(P)];
        return true;
    }
    int Count(Pigment P) const { return Units[static_cast<int>(P)]; }
    void Add(Pigment P, int N) { Units[static_cast<int>(P)] = N < 0 ? 0 : (N > kMaxUnits ? kMaxUnits : N); }

private:
    int Units[kPigments] = {};
};

enum class State { Drained, Restoring, Living };
enum class Cell { Grey, Smudged, Restored };
enum class Result { Restored, Smudged, NeedsWash, AlreadyRestored, NoPigment, Washed, NothingToWash, BadCell };
inline const char* StateName(State S) { static const char* k[] = {"DRAINED", "RESTORING", "LIVING"}; return k[static_cast<int>(S)]; }
inline const char* ResultName(Result R)
{
    static const char* k[] = {"RESTORED", "SMUDGED", "NEEDS_WASH", "ALREADY_RESTORED", "NO_PIGMENT", "WASHED", "NOTHING_TO_WASH", "BAD_CELL"};
    return k[static_cast<int>(R)];
}

constexpr int kMaxSide = 12;
constexpr int64_t kMaxSeed = 1000000000;
inline const char* Subject(int64_t Seed)
{
    static const char* k[] = {"Mob_Gallery_PaperCrane", "Mob_Gallery_PrismFinch", "Mob_Gallery_CrayonGecko",
                              "Mob_Gallery_Inkpup", "Mob_Gallery_LampMoth", "Mob_Gallery_BrushtailSquirrel"};
    return Seed < 0 ? "" : k[Seed % 6];
}

class Painting
{
public:
    // Java throws for seed outside 0..999999999 or a side outside 1..12; here the mural is !Valid() with no cells.
    Painting(int64_t InSeed, int InWidth, int InHeight) : Seed(InSeed), Width(InWidth), Height(InHeight)
    {
        if (InSeed < 0 || InSeed >= kMaxSeed || InWidth < 1 || InWidth > kMaxSide || InHeight < 1 || InHeight > kMaxSide)
        {
            Width = Height = 0;
            return;
        }
        SplitRandom Rng(InSeed);
        const int PaletteSize = 2 + Rng.NextInt(3);
        Pigment Pal[kPigments] = {Pigment::Red, Pigment::Yellow, Pigment::Blue, Pigment::Orange, Pigment::Green, Pigment::Violet};
        for (int I = kPigments - 1; I > 0; --I)
        {
            const int J = Rng.NextInt(I + 1);
            const Pigment T = Pal[I]; Pal[I] = Pal[J]; Pal[J] = T;
        }
        Target.resize(static_cast<size_t>(Width * Height));
        Cells.assign(Target.size(), Cell::Grey);
        for (Pigment& T : Target) { T = Pal[Rng.NextInt(PaletteSize)]; }
    }
    // GalleryOps.Frame: 2x2 cells per wall cube, capped at 12.
    static Painting ForFrame(int64_t FrameSeed, int FrameW, int FrameH)
    {
        return Painting(FrameSeed, FrameW * 2 < kMaxSide ? FrameW * 2 : kMaxSide, FrameH * 2 < kMaxSide ? FrameH * 2 : kMaxSide);
    }

    bool Valid() const { return !Cells.empty(); }
    Result Paint(int X, int Y, Pigment P, Palette& Pal, Knowledge& K)
    {
        const int I = Index(X, Y);
        if (I < 0) { return Result::BadCell; }
        if (Cells[I] == Cell::Restored) { return Result::AlreadyRestored; }
        if (Cells[I] == Cell::Smudged) { return Result::NeedsWash; }
        if (!Pal.Spend(P)) { return Result::NoPigment; }
        if (P != Target[I]) { Cells[I] = Cell::Smudged; ++Smudges; return Result::Smudged; }
        Cells[I] = Cell::Restored;
        ++RestoredN;
        K.Learn(P);
        return Result::Restored;
    }
    Result Wash(int X, int Y)
    {
        const int I = Index(X, Y);
        if (I < 0) { return Result::BadCell; }
        if (Cells[I] != Cell::Smudged) { return Result::NothingToWash; }
        Cells[I] = Cell::Grey;
        return Result::Washed;
    }
    // PRISM_SIGHT only; false (Out untouched) otherwise, so a host cannot leak the answer.
    bool Reveal(int X, int Y, const Knowledge& K, Pigment& Out) const
    {
        const int I = Index(X, Y);
        if (I < 0 || !K.Has(Ability::PrismSight)) { return false; }
        Out = Target[I];
        return true;
    }
    State GetState() const
    {
        if (Valid() && RestoredN == static_cast<int>(Cells.size())) { return State::Living; }
        return RestoredN == 0 ? State::Drained : State::Restoring;
    }
    int ProgressPm() const { return Valid() ? RestoredN * 1000 / static_cast<int>(Cells.size()) : 0; }
    Cell CellAt(int X, int Y) const { const int I = Index(X, Y); return I < 0 ? Cell::Grey : Cells[I]; }
    int RestoredCells() const { return RestoredN; }
    int SmudgeCount() const { return Smudges; }
    int CellCount() const { return static_cast<int>(Cells.size()); }
    int GetWidth() const { return Width; }
    int GetHeight() const { return Height; }
    int64_t GetSeed() const { return Seed; }
    // Bit i set when pigment i appears in the mural.
    int ColourMask() const { int M = 0; for (Pigment P : Target) { M |= 1 << static_cast<int>(P); } return M; }

private:
    int Index(int X, int Y) const { return (X < 0 || X >= Width || Y < 0 || Y >= Height) ? -1 : Y * Width + X; }
    int64_t Seed;
    int Width, Height;
    std::vector<Pigment> Target;
    std::vector<Cell> Cells;
    int Smudges = 0;
    int RestoredN = 0;
};

}  // namespace daedalus::gallery