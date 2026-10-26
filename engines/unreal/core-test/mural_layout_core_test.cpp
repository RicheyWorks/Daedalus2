#include "../DaedalusLink/Source/DaedalusLink/Public/DaedalusMuralLayoutCore.h"
#include <cmath>
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
bool Same(const DaedalusMuralLayout::Layout& a, const DaedalusMuralLayout::Layout& b)
{
    return a.Seed == b.Seed && a.Width == b.Width && a.Height == b.Height && a.CellSize == b.CellSize;
}
}

int main()
{
    using namespace DaedalusMuralLayout;
    const auto maximumSeed = (std::numeric_limits<std::int64_t>::max)();
    const auto minimumSeed = (std::numeric_limits<std::int64_t>::min)();
    const double infinity = std::numeric_limits<double>::infinity();
    const double nan = std::numeric_limits<double>::quiet_NaN();
    const double maximumFloat = static_cast<double>((std::numeric_limits<float>::max)());
    const double minimumFloat = static_cast<double>(std::numeric_limits<float>::denorm_min());

    Check(!Valid(Layout{}) && Layout{}.CellSize == 40.0, "default layout has no accepted dimensions");
    Check(Valid(Layout{0, 1, 1, 40.0}), "minimum seed and cell dimensions");
    Check(Valid(Layout{999999999, 12, 12, 40.0}), "maximum seed and cell dimensions");
    Check(!Valid(Layout{-1, 1, 1, 40.0}) && !Valid(Layout{1000000000, 1, 1, 40.0}), "seed boundaries");
    Check(!Valid(Layout{minimumSeed, 1, 1, 40.0}) && !Valid(Layout{maximumSeed, 1, 1, 40.0}), "extreme seeds");
    Check(!Valid(Layout{0, 0, 1, 40.0}) && !Valid(Layout{0, 13, 1, 40.0}), "width boundaries");
    Check(!Valid(Layout{0, 1, 0, 40.0}) && !Valid(Layout{0, 1, 13, 40.0}), "height boundaries");
    Check(!Valid(Layout{0, (std::numeric_limits<int>::min)(), 1, 40.0}) &&
          !Valid(Layout{0, 1, (std::numeric_limits<int>::max)(), 40.0}), "extreme dimensions refuse before products");
    Check(!Valid(Layout{0, 2, 2, 0.0}) && !Valid(Layout{0, 2, 2, -0.0}) &&
          !Valid(Layout{0, 2, 2, -1.0}), "zero and negative cell sizes");
    Check(!Valid(Layout{0, 2, 2, nan}), "NaN cell size");
    Check(!Valid(Layout{0, 2, 2, infinity}) && !Valid(Layout{0, 2, 2, -infinity}), "infinite cell sizes");
    Check(Valid(Layout{0, 12, 12, minimumFloat}), "smallest positive float has no arbitrary tuning minimum");
    Check(!Valid(Layout{0, 1, 1, std::numeric_limits<double>::denorm_min()}),
          "positive double that becomes zero in native float property refuses");
    Check(Valid(Layout{0, 1, 1, maximumFloat}), "largest finite single-cell native span");
    Check(!Valid(Layout{0, 1, 1, std::nextafter(maximumFloat, infinity)}), "above-float-range cell size refuses");
    Check(Valid(Layout{0, 12, 12, maximumFloat / 24.0}), "large finite projected geometry without policy ceiling");
    Check(!Valid(Layout{0, 12, 1, maximumFloat / 2.0}), "projected width overflow refuses");
    Check(!Valid(Layout{0, 1, 12, maximumFloat / 2.0}), "projected height overflow refuses");
    Check(!Valid(Layout{0, 12, 12, (std::numeric_limits<double>::max)()}), "double product overflow refuses before conversion");

    Layout out{77, 8, 6, 19.5};
    Check(ForFrame(0, 1, 1, 40.0, out) && Same(out, Layout{0, 2, 2, 40.0}), "one wall cube becomes two cells per side");
    Check(ForFrame(123456, 3, 2, 12.5, out) && Same(out, Layout{123456, 6, 4, 12.5}), "frame conversion preserves seed and cell size");
    Check(ForFrame(9, 5, 6, 40.0, out) && out.Width == 10 && out.Height == 12, "conversion at the cap boundary");
    Check(ForFrame(9, 7, 3, 40.0, out) && out.Width == 12 && out.Height == 6, "existing width-seven cap is preserved");
    Check(ForFrame(999999999, maximumSeed, maximumSeed, 40.0, out) &&
          Same(out, Layout{999999999, 12, 12, 40.0}), "INT64_MAX frame sides cap before multiplication");
    Check(ForFrame(9, maximumSeed, 1, 40.0, out) && out.Width == 12 && out.Height == 2,
          "independent frame-axis caps");

    struct Request { std::int64_t Seed; std::int64_t Width; std::int64_t Height; double Size; };
    const Request invalidFrames[] = {{-1, 1, 1, 40.0}, {1000000000, 1, 1, 40.0},
                                      {0, 0, 1, 40.0}, {0, 1, 0, 40.0}, {0, -1, 2, 40.0},
                                      {0, minimumSeed, 2, 40.0}, {0, 2, minimumSeed, 40.0},
                                      {0, 2, 2, 0.0}, {0, 2, 2, -2.0}, {0, 2, 2, nan},
                                      {0, 2, 2, infinity}, {0, 2, 2, maximumFloat}};
    const Layout previous{77, 8, 6, 19.5};
    bool allAtomic = true;
    for (const auto& request : invalidFrames)
    {
        out = previous;
        const bool rejected = !ForFrame(request.Seed, request.Width, request.Height, request.Size, out);
        allAtomic = allAtomic && rejected && Same(out, previous);
    }
    Check(allAtomic, "rejected requested layout leaves caller's prior Layout value unchanged");
    out = previous;
    Check(!ForFrame(0, maximumSeed, minimumSeed, 40.0, out) && Same(out, previous),
          "mixed extreme frame sides reject without mutation");
    Check(ForFrame(1, 6, 6, minimumFloat, out) && Valid(out) && out.CellSize == minimumFloat,
          "minimum representable cell size survives frame conversion");
    out = previous;
    Check(!ForFrame(1, 1, 1, std::numeric_limits<double>::denorm_min(), out) && Same(out, previous),
          "frame conversion refuses native cell-size underflow atomically");
    Check(ForFrame(42, 2, 2, 0.25, out) && Same(out, Layout{42, 4, 4, 0.25}),
          "valid request recovers after failed conversion without minimum scale policy");

    std::cout << (Failures ? "MURAL_LAYOUT_CORE_FAIL " : "MURAL_LAYOUT_CORE_PASS ")
              << ChecksTotal - Failures << '/' << ChecksTotal << " checks\n";
    return Failures ? 1 : 0;
}
