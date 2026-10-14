// SPDX-License-Identifier: MIT
// Headless proof of the tabbed inventory (hub 28570/28573/28574): one interaction, many realms.
//   g++ -std=c++17 -O2 -Wall -Wextra -I ../DaedalusLink/Source/DaedalusLink/Public inventory_core_test.cpp -o inv_test
//   ./inv_test ../DaedalusLink/Content/Inventory
// Prints n/m last; exits nonzero on a failure.

#include "DaedalusInventoryCore.h"

#include <fstream>
#include <set>
#include <iostream>
#include <sstream>

using namespace daedalus::inv;

static int Ok = 0, Total = 0;
static void Check(const std::string& Name, bool Cond, const std::string& Why = "")
{
    ++Total;
    Ok += Cond;
    std::cout << (Cond ? "PASS " : "FAIL ") << Name << (Cond || Why.empty() ? "" : "  " + Why) << "\n";
}

static std::string ReadAll(const std::string& Path)
{
    std::ifstream In(Path);
    std::stringstream S;
    S << In.rdbuf();
    return S.str();
}

int main(int argc, char** argv)
{
    const std::string Dir = argc > 1 ? argv[1] : "../DaedalusLink/Content/Inventory";
    const char* Files[] = {"world-zero", "gallery-city", "parcels", "bricks", "labyrinth", "ocean"};
    std::map<std::string, Catalog> Cats;
    for (const char* F : Files)
    {
        std::string Err;
        Catalog C;
        const bool Loaded = C.Parse(ReadAll(Dir + "/" + F + ".dic"), Err);
        Check(std::string("catalog loads: ") + F, Loaded, Err);
        if (Loaded) Cats[F] = C;
    }
    Check("six realms, six catalogs", Cats.size() == 6);
    {
        std::set<std::string> Themes, Realms;
        for (const auto& P : Cats) { Themes.insert(P.second.Theme); Realms.insert(P.second.Realm); }
        Check("each realm wears its own theme", Themes.size() == 6 && Realms.size() == 6);
        bool Known = true;
        for (const auto& P : Cats) Known &= Themes.count(P.second.Theme) && daedalus::inv::Themes().count(P.second.Theme);
        Check("and every theme named exists", Known);
        bool Distinct = true;
        for (const auto& A : Cats) for (const auto& B : Cats) if (A.first < B.first)
        {
            int Shared = 0;
            for (const ItemDef& I : A.second.Items) if (B.second.Find(I.Id)) ++Shared;
            Distinct &= Shared == 0;
        }
        Check("the item sets differ realm to realm (no shared inventory implied)", Distinct);
        bool AllFirst = true, Detailed = true;
        for (const auto& P : Cats)
        {
            AllFirst &= P.second.Tabs[0] == "ALL";
            for (const ItemDef& I : P.second.Items) Detailed &= !I.Detail.empty() && !I.Name.empty();
        }
        Check("every catalog opens on ALL and every item has a name and a detail line", AllFirst && Detailed);
    }

    // ---- refusals name the line
    {
        Catalog Bad;
        std::string E;
        Check("a catalog without its magic is refused", !Bad.Parse("hello\n", E) && E.rfind("line 1", 0) == 0, E);
        Check("an item in no tab is refused", !Bad.Parse("DIC 1\nrealm X\ntab ALL\nitem A NOPE - USE A\n", E) && E.find("line 4") == 0, E);
        Check("EQUIP without a slot is refused", !Bad.Parse("DIC 1\nrealm X\ntab ALL\ntab T\nitem A T - EQUIP A\n", E) && E.find("no slot") != std::string::npos, E);
        Check("a detail for nothing is refused", !Bad.Parse("DIC 1\nrealm X\ntab ALL\ntab T\ndetail Z words\n", E) && E.find("unknown item") != std::string::npos, E);
        Check("an item filed under ALL is refused", !Bad.Parse("DIC 1\nrealm X\ntab ALL\nitem A ALL - USE A\n", E), E);
    }

    // ---- the same controls in two realms
    const Catalog& Gallery = Cats["gallery-city"];
    const Catalog& Bricks = Cats["bricks"];
    std::map<std::string, int> GBag = {{"PAINT_SPRAY", 1}, {"WIDE_BRUSH", 1}, {"PIGMENT_RED", 12}, {"PIGMENT_BLUE", 3}, {"PAINTER_COAT", 1}, {"MURAL_PIECE", 4}, {"HEARTSTONE", 1}};
    std::map<std::string, std::string> GWorn = {{"HAND", "PAINT_SPRAY"}, {"COAT", "PAINTER_COAT"}};
    std::map<std::string, int> BBag = {{"STUD_HAMMER", 1}, {"BRICK_RED", 240}, {"BRICK_BLUE", 31}, {"BRICK_YELLOW", 8}, {"PLATE_GREEN", 2}, {"PLAN_BRIDGE", 1}, {"BRICK_PLATE", 1}, {"GLUE_POT", 1}};
    std::map<std::string, std::string> BWorn = {{"HAND", "STUD_HAMMER"}};

    Tabs G, B;
    G.Open(Gallery, GBag, GWorn, G.Look().Cols);
    B.Open(Bricks, BBag, BWorn, B.Look().Cols);
    Check("both open on ALL with everything held", G.TabName() == "ALL" && G.Rows().size() == 7 && B.TabName() == "ALL" && B.Rows().size() == 8, G.Describe() + " | " + B.Describe());
    Check("the themes differ but the grid is the same idea", G.Look().Name == "gallery" && B.Look().Name == "bricks" && G.Look().Ink != B.Look().Ink && G.Look().Cols != B.Look().Cols);
    Check("an item the bag lacks is not shown", [&] { for (const Entry& E : G.Rows()) if (E.Def->Id == "VARNISH_GUN") return false; return true; }());

    // RB in both: the next tab, with its own rows
    G.NextTab(); B.NextTab();
    Check("RB moves to the realm's own second tab", G.TabName() == "SPRAYS" && G.Rows().size() == 2 && B.TabName() == "BRICKS" && B.Rows().size() == 3, G.Describe() + " | " + B.Describe());
    Check("tab badges count what each tab holds", G.CountIn(0) == 7 && G.CountIn(1) == 2 && G.CountIn(5) == 1 && B.CountIn(1) == 3 && B.CountIn(2) == 1);
    // the cursor is kept per tab
    G.Right();
    Check("right moves the cursor in the row", G.Cursor() == 1 && G.Selected()->Def->Id == "WIDE_BRUSH");
    G.NextTab(); G.PrevTab();
    Check("a tab remembers its cursor", G.TabName() == "SPRAYS" && G.Cursor() == 1);
    G.PrevTab();
    Check("and the ALL tab kept its own", G.TabName() == "ALL" && G.Cursor() == 0);
    // wrap around the strip
    for (size_t k = 0; k < Gallery.Tabs.size(); ++k) G.NextTab();
    Check("RB wraps the strip", G.TabName() == "ALL");
    G.PrevTab();
    Check("LB wraps the other way", G.TabName() == "QUEST" && G.Rows().size() == 1);

    // the grid: 8 cols in Bricks' ALL tab (8 rows fit one line); 6 cols in Gallery (7 rows = 2 lines)
    G.SelectTab(0);
    for (int k = 0; k < 6; ++k) G.Right();
    Check("a row wraps end to end", G.Cursor() == 6, std::to_string(G.Cursor()));
    G.SelectTab(0); G.Right(); G.Down();
    Check("down lands on the short last row's end", G.Cursor() == 6, std::to_string(G.Cursor()));
    G.Up();
    Check("up comes back a row", G.Cursor() == 0, std::to_string(G.Cursor()));
    G.Down(); G.Down();
    Check("down past the end stays put", G.Cursor() == 6);

    // worn gear shows as worn and offers UNEQUIP; browsing changed nothing
    G.SelectTab(0); G.Up();   // the cursor was parked on the last row: ALL remembers it
    Check("the worn spray is marked", G.Selected()->Def->Id == "PAINT_SPRAY" && G.Selected()->Equipped);
    Intent I;
    Check("confirm opens the actions, no intent yet", !G.Confirm(I) && G.ActionsShown() && G.ActionLabels()[0] == "UNEQUIP");
    G.Down();
    Check("down walks the actions", G.ActionIndex() == 1 && G.ActionLabels()[1] == "INSPECT");
    G.Up();
    Check("confirm on UNEQUIP hands the host an intent", G.Confirm(I) && I.Action == "UNEQUIP" && I.ItemId == "PAINT_SPRAY" && I.Slot == "HAND" && !G.ActionsShown(), I.Action);
    Check("browsing changed no quantity", GBag["PAINT_SPRAY"] == 1 && GBag["PIGMENT_RED"] == 12 && G.Rows().size() == 7);
    // the host ran the intent: refresh keeps the place
    GWorn.erase("HAND");
    G.Refresh(GBag, GWorn);
    Check("after the host acts, refresh keeps tab and cursor and shows it unworn", G.TabName() == "ALL" && G.Cursor() == 0 && !G.Selected()->Equipped && G.ActionLabels()[0] == "EQUIP");

    // DROP and SPLIT carry counts
    B.SelectTab(1);   // BRICKS: red 240, blue 31, yellow 8
    B.Confirm(I); B.Down(); B.Down();   // PLACE, DROP, SPLIT
    Check("SPLIT asks for half the stack", B.Confirm(I) && I.Action == "SPLIT" && I.ItemId == "BRICK_RED" && I.Count == 120, I.Action + " " + std::to_string(I.Count));
    B.Confirm(I); B.Down();
    Check("DROP offers the stack", B.Confirm(I) && I.Action == "DROP" && I.Count == 240);
    Check("the stack is still 240 until the host says so", BBag["BRICK_RED"] == 240);

    // Back: actions first, then the panel
    B.Confirm(I);
    Check("back closes the actions, not the panel", !B.Back() && B.Opened() && !B.ActionsShown());
    Check("back again closes the panel", B.Back() && !B.Opened() && B.Describe() == "open=0");

    // an empty tab
    std::map<std::string, int> Nothing;
    Tabs E;
    E.Open(Cats["labyrinth"], Nothing, {}, 6);
    Check("an empty bag opens to no rows and no selection", E.Rows().empty() && E.Selected() == nullptr && !E.Confirm(I));
    E.Right(); E.Down(); E.NextTab();
    Check("moving through nothing is harmless", E.Cursor() == 0 && E.TabName() == "WAYFINDING");

    // a harness line
    std::map<std::string, int> SeaBag{{"TIDE_COMPASS", 1}, {"HULL_PATCH", 3}};
    Tabs Sea;
    Sea.Open(Cats["ocean"], SeaBag, {}, 6);
    Check("Ocean uses the common tabs with its own definitions", Sea.Rows().size() == 2 && Sea.TabName() == "ALL"
        && Sea.Selected() && Sea.Selected()->Def->Id == "TIDE_COMPASS");
    Check("Ocean exposes inspect without unfinished effects", !Sea.Confirm(I) && Sea.ActionLabels().size() == 1
        && Sea.ActionLabels()[0] == "INSPECT");
    Check("Ocean confirm emits inspect for the host", Sea.Confirm(I) && I.Action == "INSPECT" && I.ItemId == "TIDE_COMPASS");
    Check("Ocean browsing preserves host-owned quantities", SeaBag["TIDE_COMPASS"] == 1 && SeaBag["HULL_PATCH"] == 3);

    Check("describe names realm, theme, tab, item", G.Describe().find("realm=GALLERY-CITY theme=gallery tab=ALL(1/6)") != std::string::npos && G.Describe().find("item=PAINT_SPRAY x1") != std::string::npos, G.Describe());

    std::cout << Ok << "/" << Total << "\n";
    return Ok == Total ? 0 : 1;
}
