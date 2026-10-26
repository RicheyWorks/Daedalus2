// SPDX-License-Identifier: MIT
#pragma once
#include <cmath>
#include <cstdint>
#include <limits>

// Layout validation only: no painting colours, progress, knowledge or supplies.
namespace DaedalusMuralLayout
{
struct Layout
{
    std::int64_t Seed = 0;
    int Width = 0;
    int Height = 0;
    double CellSize = 40.0;
};

inline bool Valid(const Layout& layout)
{
    if (layout.Seed < 0 || layout.Seed > 999999999 || layout.Width < 1 || layout.Width > 12 ||
        layout.Height < 1 || layout.Height > 12 || !std::isfinite(layout.CellSize) || layout.CellSize <= 0)
        return false;

    const double maximum = static_cast<double>((std::numeric_limits<float>::max)());
    const double width = layout.Width * layout.CellSize;
    const double height = layout.Height * layout.CellSize;
    if (!std::isfinite(width) || !std::isfinite(height) || width + 20.0 > maximum || height + 20.0 > maximum)
        return false;

    // Native CellSize/geometry are floats: validate those operations too, including
    // conversion underflow and rounding at the representable range's upper edge.
    const float cellSize = static_cast<float>(layout.CellSize);
    if (!std::isfinite(cellSize) || cellSize <= 0.f) return false;
    const float projectedWidth = static_cast<float>(layout.Width) * cellSize;
    const float projectedHeight = static_cast<float>(layout.Height) * cellSize;
    return std::isfinite(projectedWidth) && std::isfinite(projectedHeight) &&
           std::isfinite(projectedWidth + 20.f) && std::isfinite(projectedHeight + 20.f);
}

inline bool ForFrame(std::int64_t seed, std::int64_t frameW, std::int64_t frameH,
                     double cellSize, Layout& out)
{
    if (frameW <= 0 || frameH <= 0) return false;
    // Preserve two cells per wall cube, capped at twelve. Cap before multiplying
    // so positive INT64_MAX inputs cannot overflow even transient arithmetic.
    const Layout candidate{seed, frameW >= 6 ? 12 : static_cast<int>(frameW * 2),
                           frameH >= 6 ? 12 : static_cast<int>(frameH * 2), cellSize};
    if (!Valid(candidate)) return false;
    out = candidate;
    return true;
}
}
