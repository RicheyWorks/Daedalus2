#include "../DaedalusLink/Source/DaedalusLink/Public/DaedalusMuralToolCore.h"
#include <cstdint>
#include <iostream>
#include <limits>

namespace
{
int ChecksTotal = 0;
int Failures = 0;
void Check(bool value, const char* label)
{
    ++ChecksTotal;
    if (!value) { ++Failures; std::cerr << "FAIL " << label << '\n'; }
}
}

int main()
{
    using DaedalusMuralTools::Focus;
    const auto maximum = std::numeric_limits<std::int64_t>::max();
    const auto minimum = std::numeric_limits<std::int64_t>::min();
    Focus focus;
    Check(!focus.Valid() && focus.Width() == 0 && focus.Height() == 0 &&
          focus.X() == 0 && focus.Y() == 0 && focus.PigmentIndex() == 0, "default detached focus");
    Check(!focus.SetCell(0, 0) && !focus.Move(1) && !focus.Move(minimum), "detached focus cannot select a cell");
    Check(focus.SelectPigment(5) && focus.PigmentIndex() == 5, "pigment choice is independent of grid attachment");
    Check(!focus.SelectPigment(-1) && !focus.SelectPigment(6) && focus.PigmentIndex() == 5,
          "invalid pigment selection is unchanged");
    Check(focus.CyclePigment(1) && focus.PigmentIndex() == 0, "pigment wraps while detached");
    Check(focus.Configure(0, 1, 1) && focus.Valid() && focus.Width() == 1 && focus.Height() == 1,
          "minimum seed and singleton dimensions");
    Check(focus.Move(maximum) && focus.Move(minimum) && focus.X() == 0 && focus.Y() == 0,
          "extreme movement on singleton grid");
    Check(focus.Configure(999999999, 12, 12) && focus.Width() == 12 && focus.Height() == 12 &&
          focus.X() == 0 && focus.Y() == 0, "maximum seed and dimensions");
    Check(focus.SetCell(11, 11) && focus.X() == 11 && focus.Y() == 11, "last valid cell");
    Check(focus.Move(1) && focus.X() == 0 && focus.Y() == 0, "last cell wraps to first");
    Check(focus.Move(-1) && focus.X() == 11 && focus.Y() == 11, "first cell wraps backward to last");
    Check(focus.Move(maximum) && focus.X() == 6 && focus.Y() == 6,
          "INT64_MAX movement from nonzero cell reduces before addition");
    focus.SetCell(11, 11);
    Check(focus.Move(minimum) && focus.X() == 3 && focus.Y() == 5,
          "INT64_MIN movement does not negate or overflow");
    Check(focus.Move(0) && focus.X() == 3 && focus.Y() == 5, "zero movement preserves focus");
    focus.SelectPigment(2);
    Check(focus.Configure(999999999, 12, 12) && focus.X() == 3 && focus.Y() == 5 && focus.PigmentIndex() == 2,
          "same identity preserves cell and pigment");
    Check(focus.Configure(123, 12, 12) && focus.X() == 0 && focus.Y() == 0 && focus.PigmentIndex() == 2,
          "changed seed resets only the cell");
    focus.SetCell(5, 5);
    Check(focus.Configure(123, 6, 12) && focus.X() == 0 && focus.Y() == 0 &&
          focus.Width() == 6 && focus.Height() == 12 && focus.PigmentIndex() == 2,
          "changed width resets only the cell");
    focus.SetCell(2, 3);
    Check(focus.Configure(123, 6, 6) && focus.X() == 0 && focus.Y() == 0 && focus.PigmentIndex() == 2,
          "changed height resets only the cell");
    focus.SetCell(2, 3);
    Check(!focus.SetCell(-1, 0) && !focus.SetCell(0, -1) && !focus.SetCell(6, 0) && !focus.SetCell(0, 6) &&
          focus.X() == 2 && focus.Y() == 3, "out-of-range coordinates leave selection unchanged");
    Check(!focus.SelectPigment(std::numeric_limits<int>::min()) &&
          !focus.SelectPigment(std::numeric_limits<int>::max()) && focus.PigmentIndex() == 2,
          "extreme pigment indices refuse unchanged");
    focus.SelectPigment(0);
    Check(focus.CyclePigment(maximum) && focus.PigmentIndex() == 1, "maximum signed pigment cycle");
    focus.SelectPigment(0);
    Check(focus.CyclePigment(minimum) && focus.PigmentIndex() == 4, "minimum signed pigment cycle");
    focus.SelectPigment(0);
    Check(focus.CyclePigment(-1) && focus.PigmentIndex() == 5 &&
          focus.CyclePigment(6) && focus.CyclePigment(-12) && focus.PigmentIndex() == 5,
          "negative pigment wrap and whole cycles");
    Check(focus.CyclePigment(0) && focus.SelectPigment(5) && focus.PigmentIndex() == 5 &&
          focus.X() == 2 && focus.Y() == 3, "pigment choices do not move the cell");
    focus.Configure(7, 4, 3);
    focus.SetCell(3, 1);
    Check(focus.Move(5) && focus.X() == 0 && focus.Y() == 0, "movement follows row-major order");
    Check(focus.Move(-1) && focus.X() == 3 && focus.Y() == 2, "rectangular grid backward wrap");
    Check(focus.Move(12) && focus.Move(-24) && focus.X() == 3 && focus.Y() == 2,
          "whole grid cycles preserve cell");
    focus.SetCell(0, 0);
    Check(focus.Move(maximum) && focus.X() == 3 && focus.Y() == 1, "maximum move on rectangular grid");
    focus.SetCell(0, 0);
    Check(focus.Move(minimum) && focus.X() == 0 && focus.Y() == 1, "minimum move on rectangular grid");

    struct BadConfig { std::int64_t Seed; int Width; int Height; };
    const BadConfig bad[] = {{-1, 2, 2}, {1000000000, 2, 2}, {minimum, 2, 2}, {maximum, 2, 2},
                             {0, 0, 2}, {0, 13, 2}, {0, 2, 0}, {0, 2, 13},
                             {0, std::numeric_limits<int>::min(), 2}, {0, 2, std::numeric_limits<int>::max()}};
    bool allInvalidClear = true;
    for (const auto& config : bad)
    {
        focus.Configure(7, 4, 3);
        focus.SetCell(2, 2);
        focus.SelectPigment(4);
        const bool rejected = !focus.Configure(config.Seed, config.Width, config.Height);
        allInvalidClear = allInvalidClear && rejected && !focus.Valid() &&
                          focus.Width() == 0 && focus.Height() == 0 && focus.X() == 0 && focus.Y() == 0 &&
                          focus.PigmentIndex() == 4 && !focus.Move(1) && !focus.SetCell(0, 0);
    }
    Check(allInvalidClear, "invalid configurations clear cell/grid and preserve pigment preference");
    Check(focus.Configure(0, 1, 1) && focus.Valid() && focus.X() == 0 && focus.Y() == 0 &&
          focus.PigmentIndex() == 4, "valid configuration recovers from invalidation");

    std::cout << (Failures ? "MURAL_TOOL_CORE_FAIL " : "MURAL_TOOL_CORE_PASS ")
              << ChecksTotal - Failures << '/' << ChecksTotal << " checks\n";
    return Failures ? 1 : 0;
}
