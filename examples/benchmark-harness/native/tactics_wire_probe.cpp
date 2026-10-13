// SPDX-License-Identifier: MIT
// Developer compatibility probe: feed Java DTO 1 on stdin; use the existing Unreal-free parser/writer.
#include "DaedalusTacticsCore.h"
#include <iostream>
#include <iterator>
#include <string>

int main()
{
    const std::string text{std::istreambuf_iterator<char>(std::cin), std::istreambuf_iterator<char>()};
    const auto parsed = daedalus::tactics::Parse(text);
    if (!parsed.Ok) {
        std::cerr << parsed.Error << '\n';
        return 1;
    }
    std::cout << daedalus::tactics::Write(parsed.Out);
    return 0;
}
