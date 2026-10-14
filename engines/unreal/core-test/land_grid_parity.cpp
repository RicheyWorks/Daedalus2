// SPDX-License-Identifier: MIT
// Canonical ASCII/LF rows for the Java LandGrid parity regression. No Unreal editor required.
#include "DaedalusLandGrid.h"
#include <iostream>

int main()
{
    using namespace daedalus::land;
    for (int n = 0; n < Count; ++n)
    {
        const Cell c = CellOf(n);
        const auto m = Metres(n);
        std::cout << n << ',' << c.X << ',' << c.Y << ',' << Number(c.X, c.Y) << ','
                  << Ring(n) << ',' << District(n) << ',' << static_cast<int>(m.first) << ','
                  << static_cast<int>(m.second) << '\n';
    }
    for (int y = 0; y < Side; ++y)
        for (int x = 0; x < Side; ++x)
            for (int size = 1; size <= 4; ++size)
                std::cout << x << ',' << y << ',' << size << ',' << Estate(x, y, size) << '\n';
}
