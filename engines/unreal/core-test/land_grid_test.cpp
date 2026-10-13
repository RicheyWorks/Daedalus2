// SPDX-License-Identifier: MIT
// ADR-065 rule 2: the shared spiral. Prints the first cells (for the Java side to match) and proves the grid.
//   g++ -std=c++17 -O2 -Wall -Wextra -I ../DaedalusLink/Source/DaedalusLink/Public land_grid_test.cpp -o land_test && ./land_test

#include "DaedalusLandGrid.h"

#include <iostream>
#include <set>

using namespace daedalus::land;

static int Ok = 0, Total = 0;
static void Check(const std::string& Name, bool Cond, const std::string& Why = "")
{
    ++Total;
    Ok += Cond;
    std::cout << (Cond ? "PASS " : "FAIL ") << Name << (Cond || Why.empty() ? "" : "  " + Why) << "\n";
}

int main()
{
    std::cout << "first cells:";
    for (int n = 0; n < 12; ++n) std::cout << " " << n << "=(" << CellOf(n).X << "," << CellOf(n).Y << ")";
    std::cout << "\n";
    Check("cell 0 is the hub", CellOf(0).X == 50 && CellOf(0).Y == 50);
    Check("cell 1 is east of it, then the ring runs north", CellOf(1).X == 51 && CellOf(1).Y == 50 && CellOf(2).X == 51 && CellOf(2).Y == 51);
    Check("ring 1 is eight cells, ring 2 starts at 9", Ring(8) == 1 && Ring(9) == 2 && CellOf(9).X == 52 && CellOf(9).Y == 49);
    {
        std::set<std::pair<int, int>> Seen;
        bool InGrid = true, Inverse = true;
        for (int n = 0; n < Count; ++n)
        {
            const Cell C = CellOf(n);
            InGrid &= C.X >= 0 && C.X < Side && C.Y >= 0 && C.Y < Side;
            Seen.insert({C.X, C.Y});
            Inverse &= Number(C.X, C.Y) == n;
        }
        Check("10,000 numbers, 10,000 distinct cells, all on the grid", Seen.size() == static_cast<size_t>(Count) && InGrid);
        Check("Number(Cell(n)) == n for every land", Inverse);
    }
    Check("off-grid asks are refused", Number(-1, 0) == -1 && Number(100, 5) == -1 && CellOf(10000).X == -1 && CellOf(-1).X == -1);
    Check("the hub is in district 55", District(0) == 55 && District(1) == 55);
    Check("a corner land is in a corner district", District(Number(0, 0)) == 0 && District(Number(99, 99)) == 99);
    Check("low numbers ring the hub (scarce like a city centre)", Ring(24) == 2 && Ring(25) == 3 && Ring(9999) >= 49);
    {
        std::vector<int> Cells;
        const int E = Estate(50, 50, 2, &Cells);
        Check("a 2x2 estate at the hub is deed 0 with four cells", E == 0 && Cells.size() == 4);
        Check("an estate that would split a district is refused", Estate(49, 49, 2) == -1 && Estate(48, 48, 2) >= 0);
        Check("an estate off the grid is refused", Estate(98, 98, 4) == -1 && Estate(96, 96, 4) >= 0);
        Check("estate sizes are 1..4", Estate(10, 10, 5) == -1 && Estate(10, 10, 1) == Number(10, 10));
    }
    {
        const auto M = Metres(1);
        Check("cell 1 sits one pitch east of the hub", M.first == 256.0 && M.second == 0.0);
        Check("and the point there maps back to land 1", NumberAtMetres(256.0, 0.0) == 1 && NumberAtMetres(300.0, -100.0) == 1 && NumberAtMetres(0.0, 0.0) == 0);
        const auto Far = Metres(9999);
        Check("the far corner is about 12.8 km out", std::abs(Far.first) > 12000.0 || std::abs(Far.second) > 12000.0);
        Check("a bigger pitch scales the place, not the number", Metres(1, 512.0).first == 512.0 && NumberAtMetres(512.0, 0.0, 512.0) == 1);
    }
    std::cout << Ok << "/" << Total << "\n";
    return Ok == Total ? 0 : 1;
}
