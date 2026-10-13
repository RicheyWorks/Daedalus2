// SPDX-License-Identifier: MIT

#pragma once

// ADR-065 rule 2, the shared formula: every realm is a 100 x 100 grid of cells, numbered 0..9999 in a square
// spiral out from the hub, so low numbers sit near spawn and the gates. One function gives every land its place,
// here in C++ and (Sol) in Java; core-test/land_grid_test.cpp prints the first cells so the two can be compared.
//
//   Cell(n)      -> (x, y), 0..99 each; Cell(0) = (50, 50), the hub. Then east, north, west, south: ring by ring.
//   Number(x, y) -> n, the inverse.
//   District(n)  -> 0..99, the 10x10 block of cells the land streams with (rule 5).
//   Estate(x, y, size) -> the deed number of a size x size block: its lowest cell number (rule 3).
//   Metres(n)    -> the cell's centre in realm metres, pitch 256 m (rule 8; 512 proposed), the hub at (0, 0).
//
// Pure C++17.

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <utility>
#include <vector>

namespace daedalus
{
namespace land
{

constexpr int Side = 100;          // cells per side
constexpr int Count = Side * Side; // lands per realm
constexpr int Hub = Side / 2;      // cell 0 is (50, 50)
constexpr int DistrictSide = 10;
constexpr double PitchM = 256.0;   // rule 8 (512 under discussion: a constant, not a format)

struct Cell { int X = 0, Y = 0; };

/** The square spiral: n = 0 at the hub, then rings. Ring r (r >= 1) holds 8r cells, starting east of the hub
 *  at (Hub + r, Hub - r + 1) and running north along the east side, west along the north side, south along the
 *  west side, east along the south side. Cells off the 100 x 100 grid (the spiral's corners past the edge) are
 *  skipped, so numbering stays dense. */
inline const std::vector<Cell>& Table()
{
    static const std::vector<Cell> T = [] {
        std::vector<Cell> Out;
        Out.reserve(Count);
        Out.push_back({Hub, Hub});
        for (int r = 1; static_cast<int>(Out.size()) < Count; ++r)
        {
            std::vector<Cell> Ring;
            for (int y = Hub - r + 1; y <= Hub + r; ++y) Ring.push_back({Hub + r, y});       // east side, going north (y up)
            for (int x = Hub + r - 1; x >= Hub - r; --x) Ring.push_back({x, Hub + r});       // north side, going west
            for (int y = Hub + r - 1; y >= Hub - r; --y) Ring.push_back({Hub - r, y});       // west side, going south
            for (int x = Hub - r + 1; x <= Hub + r; ++x) Ring.push_back({x, Hub - r});       // south side, going east
            for (const Cell& C : Ring)
                if (C.X >= 0 && C.X < Side && C.Y >= 0 && C.Y < Side && static_cast<int>(Out.size()) < Count) Out.push_back(C);
        }
        return Out;
    }();
    return T;
}

inline bool Valid(int N) { return N >= 0 && N < Count; }

inline Cell CellOf(int N)
{
    if (!Valid(N)) return {-1, -1};
    return Table()[static_cast<size_t>(N)];
}

inline int Number(int X, int Y)
{
    static const std::vector<int> Inv = [] {
        std::vector<int> I(static_cast<size_t>(Count), -1);
        const std::vector<Cell>& T = Table();
        for (int n = 0; n < Count; ++n) I[static_cast<size_t>(T[static_cast<size_t>(n)].Y * Side + T[static_cast<size_t>(n)].X)] = n;
        return I;
    }();
    if (X < 0 || X >= Side || Y < 0 || Y >= Side) return -1;
    return Inv[static_cast<size_t>(Y * Side + X)];
}

/** The ring a land sits on: 0 at the hub. Scarcity reads off this. */
inline int Ring(int N)
{
    const Cell C = CellOf(N);
    if (C.X < 0) return -1;
    return std::max(std::abs(C.X - Hub), std::abs(C.Y - Hub));
}

inline int District(int N)
{
    const Cell C = CellOf(N);
    if (C.X < 0) return -1;
    return (C.Y / DistrictSide) * DistrictSide + C.X / DistrictSide;
}

inline int DistrictOfCell(int X, int Y) { return (Y / DistrictSide) * DistrictSide + X / DistrictSide; }

/** An estate of Size x Size cells with its south-west corner at (X, Y): the deed number is the lowest cell number in
 *  the block, -1 when the block leaves the grid or splits a district (rule 5: estates never split a district). */
inline int Estate(int X, int Y, int Size, std::vector<int>* Cells = nullptr)
{
    if (Size < 1 || Size > 4 || X < 0 || Y < 0 || X + Size > Side || Y + Size > Side) return -1;
    const int D = DistrictOfCell(X, Y);
    int Lowest = Count;
    for (int j = 0; j < Size; ++j)
        for (int i = 0; i < Size; ++i)
        {
            if (DistrictOfCell(X + i, Y + j) != D) return -1;
            const int n = Number(X + i, Y + j);
            Lowest = std::min(Lowest, n);
            if (Cells) Cells->push_back(n);
        }
    return Lowest;
}

/** The cell's centre in realm metres, the hub cell centred on (0, 0); +X east, +Y north. */
inline std::pair<double, double> Metres(int N, double Pitch = PitchM)
{
    const Cell C = CellOf(N);
    if (C.X < 0) return {0.0, 0.0};
    return {(C.X - Hub) * Pitch, (C.Y - Hub) * Pitch};
}

/** The nearest cell to a point in realm metres (for "which land am I on"). */
inline int NumberAtMetres(double X, double Y, double Pitch = PitchM)
{
    const int CX = static_cast<int>(std::floor(X / Pitch + 0.5)) + Hub, CY = static_cast<int>(std::floor(Y / Pitch + 0.5)) + Hub;
    return Number(CX, CY);
}

} // namespace land
} // namespace daedalus
