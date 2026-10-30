// SPDX-License-Identifier: MIT
// The land registry seam: Sol's district DTO (REALM-LAND-API.md) read without exceptions and reconciled with the
// editor's plots.
//   g++ -std=c++17 -O2 -Wall -Wextra -I ../DaedalusLink/Source/DaedalusLink/Public land_registry_test.cpp -o landreg_test && ./landreg_test

#include "DaedalusLandGrid.h"
#include "DaedalusLandRegistryCore.h"

#include <iostream>

using namespace daedalus::landreg;

static int Ok = 0, Total = 0;
static void Check(const std::string& Name, bool Cond, const std::string& Why = "")
{
    ++Total;
    Ok += Cond;
    std::cout << (Cond ? "PASS " : "FAIL ") << Name << (Cond || Why.empty() ? "" : "  " + Why) << "\n";
}

static const char* SAMPLE = R"({
  "schemaVersion": 1, "realm": "WORLD-ZERO", "revision": 2, "district": 55, "gridSide": 100, "pitchMetres": 256.0,
  "coordinates": "east-north-realm-metres", "reservedCells": [0, 1, 2, 3, 4, 5, 6, 7, 8],
  "lands": [
    {"landNumber": 9,  "cellX": 56, "cellY": 52, "size": 4, "seed": "-9223372036854775808", "originEastMetres": 1536.0,  "originNorthMetres": 512.0},
    {"landNumber": 10, "cellX": 52, "cellY": 50, "size": 4, "seed": "42", "originEastMetres": 512.0, "originNorthMetres": 0.0},
    {"landNumber": 60, "cellX": 54, "cellY": 51, "size": 1, "seed": "7", "originEastMetres": 1024.0, "originNorthMetres": 256.0},
    {"landNumber": 64, "cellX": 55, "cellY": 55, "size": 1, "seed": "8", "originEastMetres": 1280.0, "originNorthMetres": 1280.0}
  ]
})";

int main()
{
    District D = ReadDistrict(SAMPLE);
    Check("the sample district reads", D.Ok, D.Why);
    Check("header fields", D.Realm == "WORLD-ZERO" && D.Revision == 2 && D.Number == 55 && D.GridSide == 100 && D.PitchM == 256.0 && D.Coordinates == "east-north-realm-metres");
    Check("nine reserved hub cells", D.Reserved.size() == 9 && D.Reserved[8] == 8);
    Check("four lands, numbers and cells", D.Lands.size() == 4 && D.Lands[0].Number == 9 && D.Lands[0].CellX == 56 && D.Lands[0].CellY == 52 && D.Lands[0].Size == 4);
    Check("an int64 seed survives as its decimal text", D.Lands[0].Seed == "-9223372036854775808" && D.Lands[1].Seed == "42");
    Check("origin metres read as numbers", D.Lands[3].EastM == 1280.0 && D.Lands[3].NorthM == 1280.0);

    Check("schema 2 is refused", !ReadDistrict("{\"schemaVersion\": 2, \"realm\": \"X\", \"district\": 1, \"lands\": []}").Ok);
    Check("a missing lands array is refused", !ReadDistrict("{\"schemaVersion\": 1, \"realm\": \"X\", \"district\": 1}").Ok);
    Check("broken json is refused with a reason, not a throw", !ReadDistrict("{\"schemaVersion\": 1, ").Ok && ReadDistrict("{\"schemaVersion\": 1, ").Why.rfind("json:", 0) == 0);
    Check("a land of size 5 is refused", !ReadDistrict("{\"schemaVersion\": 1, \"realm\": \"X\", \"district\": 1, \"lands\": [{\"landNumber\": 1, \"cellX\": 1, \"cellY\": 1, \"size\": 5}]}").Ok);
    Check("an empty district is fine", ReadDistrict("{\"schemaVersion\": 1, \"realm\": \"X\", \"district\": 0, \"lands\": []}").Ok);
    Check("escapes in strings", ReadDistrict("{\"schemaVersion\": 1, \"realm\": \"A\\\"B\", \"district\": 1, \"lands\": []}").Realm == "A\"B");

    // The editor's plots: 9 and 10 agree, 60 was moved by the server, 64 is only on the server, 70 only in the
    // editor, 99 sits on a reserved cell (number 0 = the hub) and is also only in the editor.
    std::vector<Plot> Plots = {{9, 56, 52, 4}, {10, 52, 50, 4}, {60, 54, 50, 1}, {70, 56, 56, 1}, {99, 50, 50, 1}, {5000, 10, 10, 1}};
    Report R = Reconcile(D, Plots, [](int X, int Y) { return daedalus::land::Number(X, Y); });
    Check("two agree", R.Agree.size() == 2 && R.Agree[0] == 9 && R.Agree[1] == 10);
    Check("60 moved: the editor must follow the server's cell", R.Moved.size() == 1 && R.Moved[0].first == 60 && R.Moved[0].second.CellY == 51);
    Check("64 is only on the server", R.OnlyServer.size() == 1 && R.OnlyServer[0].Number == 64);
    Check("70 and 99 are only in the editor; the plot in district 11 is not this district's business", R.OnlyEditor.size() == 2 && R.OnlyEditor[0] == 70 && R.OnlyEditor[1] == 99);
    Check("99 stands on a reserved cell", R.ReservedButPlotted.size() == 1 && R.ReservedButPlotted[0] == 99);
    Check("describe", R.Describe() == "rev=2 agree=2 moved=1 only_server=1 only_editor=2 reserved_plotted=1", R.Describe());
    Check("district membership: 55 is x 50..59, y 50..59", InDistrict(55, 50, 50) && InDistrict(55, 59, 59) && !InDistrict(55, 60, 50) && !InDistrict(55, 50, 49));

    std::cout << Ok << "/" << Total << "\n";
    return Ok == Total ? 0 : 1;
}
