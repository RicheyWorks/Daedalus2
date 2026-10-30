// SPDX-License-Identifier: MIT
#pragma once
#include <cstdint>

// Local selection only. The existing painting owns colours, knowledge and supplies.
namespace DaedalusMuralTools
{
class Focus
{
public:
    bool Configure(std::int64_t seed, int width, int height)
    {
        if (seed < 0 || seed > 999999999 || width < 1 || width > 12 || height < 1 || height > 12)
        {
            Configured = false;
            Seed = 0;
            Columns = Rows = Cell = 0;
            return false;
        }
        if (!Configured || Seed != seed || Columns != width || Rows != height) Cell = 0;
        Seed = seed;
        Columns = width;
        Rows = height;
        Configured = true;
        return true;
    }

    bool Valid() const { return Configured; }
    bool SetCell(int x, int y)
    {
        if (!Configured || x < 0 || x >= Columns || y < 0 || y >= Rows) return false;
        Cell = y * Columns + x;
        return true;
    }
    bool Move(std::int64_t delta)
    {
        if (!Configured) return false;
        const int total = Columns * Rows;
        // Reduce the full signed delta before adding; never negate INT64_MIN.
        Cell = (Cell + static_cast<int>(delta % total) + total) % total;
        return true;
    }
    bool SelectPigment(int index)
    {
        if (index < 0 || index >= 6) return false;
        Pigment = index;
        return true;
    }
    bool CyclePigment(std::int64_t delta)
    {
        Pigment = (Pigment + static_cast<int>(delta % 6) + 6) % 6;
        return true;
    }

    int X() const { return Configured ? Cell % Columns : 0; }
    int Y() const { return Configured ? Cell / Columns : 0; }
    int Width() const { return Columns; }
    int Height() const { return Rows; }
    int PigmentIndex() const { return Pigment; }

private:
    std::int64_t Seed = 0;
    int Columns = 0;
    int Rows = 0;
    int Cell = 0;
    int Pigment = 0;
    bool Configured = false;
};
}
