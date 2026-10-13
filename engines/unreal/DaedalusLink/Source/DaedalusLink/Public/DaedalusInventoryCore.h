// SPDX-License-Identifier: MIT

#pragma once

// The tabbed inventory (hub 28570/28573/28574, 2026-10-13): one interaction pattern for every realm, in the spirit of
// ARC Raiders' tabs; each realm brings its own catalog (tabs, items, equipment slots, actions) and its own theme
// (colours, type, panel). Browsing never changes a quantity: the model reads the bag and emits Intents the host runs.
//
// Pure C++17, no Unreal, so engines/unreal/core-test/inventory_core_test.cpp proves the behaviour headlessly and the
// Slate widget (SDaedalusInventory) only draws. The Java server reads the same DIC files for the realm's item rules.
//
// The catalog, "DIC 1" (Daedalus Inventory Catalog):
//   DIC 1
//   realm GALLERY-CITY                      the realm this catalog belongs to
//   theme gallery                           which theme the widget wears (DaedalusInventoryCore.h: Themes())
//   tab ALL                                 tabs in order; ALL is special: every item
//   tab WEAPONS
//   slot HAND                               equipment slots this realm has (EQUIP needs one that fits)
//   item PAINT_SPRAY WEAPONS HAND EQUIP,DROP Paint Spray     id, tab, slot or -, actions (comma list), name
//   detail PAINT_SPRAY A can of neon. Tags the wall you aim at.
// Items the bag doesn't hold are not shown; the bag is "id count" pairs the host supplies.

#include <algorithm>
#include <cctype>
#include <cstdint>
#include <cstdlib>
#include <map>
#include <string>
#include <vector>

namespace daedalus
{
namespace inv
{

struct ItemDef
{
    std::string Id, Name, Tab, Slot, Detail;
    std::vector<std::string> Actions;   // in display order, e.g. EQUIP, USE, DROP, SPLIT, INSPECT
    bool Has(const std::string& A) const { return std::find(Actions.begin(), Actions.end(), A) != Actions.end(); }
};

struct Catalog
{
    std::string Realm, Theme = "default";
    std::vector<std::string> Tabs;     // display order
    std::vector<std::string> Slots;    // equipment slots
    std::vector<ItemDef> Items;        // catalog order = display order inside a tab

    const ItemDef* Find(const std::string& Id) const
    {
        for (const ItemDef& I : Items) if (I.Id == Id) return &I;
        return nullptr;
    }
    bool HasSlot(const std::string& S) const { return std::find(Slots.begin(), Slots.end(), S) != Slots.end(); }
    bool HasTab(const std::string& T) const { return std::find(Tabs.begin(), Tabs.end(), T) != Tabs.end(); }

    static std::vector<std::string> Split(const std::string& S, char Sep)
    {
        std::vector<std::string> Out;
        std::string Cur;
        for (char C : S) { if (C == Sep) { if (!Cur.empty()) Out.push_back(Cur); Cur.clear(); } else Cur += C; }
        if (!Cur.empty()) Out.push_back(Cur);
        return Out;
    }

    static bool IsId(const std::string& S)
    {
        if (S.empty() || S.size() > 48) return false;
        for (char C : S) if (!(std::isalnum(static_cast<unsigned char>(C)) || C == '_' || C == '-')) return false;
        return true;
    }

    /** Parse the text. False with Error "line N: why"; nothing kept on failure. */
    bool Parse(const std::string& Text, std::string& Error)
    {
        Catalog Out;
        std::vector<std::string> Lines;
        {
            std::string Cur;
            for (char C : Text) { if (C == '\n') { Lines.push_back(Cur); Cur.clear(); } else if (C != '\r') Cur += C; }
            if (!Cur.empty()) Lines.push_back(Cur);
        }
        auto Fail = [&](size_t I, const std::string& Why) { Error = "line " + std::to_string(I + 1) + ": " + Why; return false; };
        if (Lines.empty() || Lines[0] != "DIC 1") return Fail(0, "expected 'DIC 1'");
        for (size_t I = 1; I < Lines.size(); ++I)
        {
            const std::string& L = Lines[I];
            if (L.empty() || L[0] == '#') continue;
            std::vector<std::string> F = Split(L, ' ');
            auto Rest = [&](size_t From) {
                std::string R;
                for (size_t k = From; k < F.size(); ++k) { if (!R.empty()) R += ' '; R += F[k]; }
                return R;
            };
            if (F[0] == "realm") { if (F.size() < 2) return Fail(I, "realm needs a name"); Out.Realm = Rest(1); }
            else if (F[0] == "theme") { if (F.size() != 2) return Fail(I, "theme needs one name"); Out.Theme = F[1]; }
            else if (F[0] == "tab")
            {
                if (F.size() != 2 || !IsId(F[1])) return Fail(I, "expected 'tab <NAME>'");
                if (Out.HasTab(F[1])) return Fail(I, "duplicate tab " + F[1]);
                if (Out.Tabs.size() >= 12) return Fail(I, "too many tabs (12)");
                Out.Tabs.push_back(F[1]);
            }
            else if (F[0] == "slot")
            {
                if (F.size() != 2 || !IsId(F[1])) return Fail(I, "expected 'slot <NAME>'");
                if (Out.HasSlot(F[1])) return Fail(I, "duplicate slot " + F[1]);
                Out.Slots.push_back(F[1]);
            }
            else if (F[0] == "item")
            {
                if (F.size() < 6) return Fail(I, "expected 'item <id> <tab> <slot|-> <actions> <name...>'");
                ItemDef D;
                D.Id = F[1];
                if (!IsId(D.Id)) return Fail(I, "bad item id " + D.Id);
                if (Out.Find(D.Id)) return Fail(I, "duplicate item " + D.Id);
                D.Tab = F[2];
                if (!Out.HasTab(D.Tab) || D.Tab == "ALL") return Fail(I, "item " + D.Id + " names no tab of this realm: " + D.Tab);
                D.Slot = F[3] == "-" ? "" : F[3];
                if (!D.Slot.empty() && !Out.HasSlot(D.Slot)) return Fail(I, "item " + D.Id + " names no slot of this realm: " + D.Slot);
                D.Actions = Split(F[4], ',');
                for (const std::string& A : D.Actions)
                {
                    if (!IsId(A)) return Fail(I, "bad action " + A);
                    if (A == "EQUIP" && D.Slot.empty()) return Fail(I, "item " + D.Id + " can EQUIP but has no slot");
                }
                D.Name = Rest(5);
                Out.Items.push_back(D);
            }
            else if (F[0] == "detail")
            {
                if (F.size() < 3) return Fail(I, "expected 'detail <id> <text...>'");
                ItemDef* D = const_cast<ItemDef*>(Out.Find(F[1]));
                if (!D) return Fail(I, "detail for unknown item " + F[1]);
                D->Detail = Rest(2);
            }
            else return Fail(I, "unknown record " + F[0]);
        }
        if (Out.Realm.empty()) return Fail(Lines.size(), "no realm line");
        if (Out.Tabs.empty()) return Fail(Lines.size(), "no tabs");
        *this = std::move(Out);
        return true;
    }
};

/** What the host runs when the player confirms an action. The model never changes a count itself. */
struct Intent
{
    std::string Action, ItemId, Slot;
    int Count = 0;
};

/** The look a realm gives the shared widget. The widget reads these; the behaviour never does. */
struct Theme
{
    std::string Name, Font = "MODERN";       // PIXEL (the 8-bit realm's kit) or MODERN
    uint32_t Panel = 0x14161A, Ink = 0xE8E2D2, Text = 0xF4F1EA, Dim = 0x8A8F99, Hot = 0xF2B134, Focus = 0x62D0FF;
    int Corner = 6;                           // px, 0 = square (the retro kit)
    int Cols = 6;                             // item grid columns
    std::string Decor;                        // what the realm hangs around the panel: a word for the widget
};

inline const std::map<std::string, Theme>& Themes()
{
    static const std::map<std::string, Theme> T = [] {
        std::map<std::string, Theme> M;
        Theme D; D.Name = "default"; M["default"] = D;
        Theme G; G.Name = "gallery"; G.Panel = 0x0E0F13; G.Ink = 0xFF4FD8; G.Hot = 0x3DF7C0; G.Focus = 0xFFFFFF; G.Corner = 2; G.Decor = "neon"; M["gallery"] = G;
        Theme P; P.Name = "parcels"; P.Panel = 0x2A1F14; P.Ink = 0xD9B27C; P.Hot = 0xF2C14E; P.Focus = 0xFFF1C8; P.Corner = 10; P.Decor = "kraft"; M["parcels"] = P;
        Theme B; B.Name = "bricks"; B.Panel = 0xB3261E; B.Ink = 0xF9D71C; B.Text = 0xFFFFFF; B.Dim = 0xF3B5B0; B.Hot = 0x2C7BE5; B.Focus = 0xFFFFFF; B.Corner = 4; B.Cols = 8; B.Decor = "studs"; M["bricks"] = B;
        Theme L; L.Name = "labyrinth"; L.Panel = 0x101418; L.Ink = 0x6AA0FF; L.Hot = 0xFF6A6A; L.Focus = 0xC8E0FF; L.Corner = 0; L.Decor = "stone"; M["labyrinth"] = L;
        Theme R; R.Name = "retro"; R.Font = "PIXEL"; R.Panel = 0x000000; R.Ink = 0xF8A070; R.Text = 0xFCFCFC; R.Dim = 0x7C7C7C; R.Hot = 0xF8D878; R.Focus = 0xFCFCFC; R.Corner = 0; R.Cols = 1; R.Decor = "rule"; M["retro"] = R;
        Theme Z; Z.Name = "zero"; Z.Panel = 0x0B1F14; Z.Ink = 0x7CFF9A; Z.Hot = 0xFFE066; Z.Focus = 0xFFFFFF; Z.Corner = 8; Z.Decor = "vines"; M["zero"] = Z;
        return M;
    }();
    return T;
}

inline const Theme& ThemeNamed(const std::string& Name)
{
    const auto& T = Themes();
    auto It = T.find(Name);
    return It == T.end() ? T.at("default") : It->second;
}

/** One row of what the player sees in the current tab. */
struct Entry
{
    const ItemDef* Def = nullptr;
    int Count = 0;
    bool Equipped = false;
};

/**
 * The shared interaction. Open it on a catalog with the bag's counts and what is equipped; drive it with the same
 * buttons in every realm:
 *   PrevTab / NextTab      LB / RB, Q / E: wrap around; each tab remembers its own cursor
 *   Up/Down/Left/Right     the grid, Theme.Cols wide; wraps inside the tab
 *   Confirm                opens the item's actions, or picks the highlighted action
 *   Back                   closes the actions, then the inventory
 * Nothing here changes a count: Confirm on an action returns an Intent for the host.
 */
class Tabs
{
public:
    void Open(const Catalog& C, const std::map<std::string, int>& Bag, const std::map<std::string, std::string>& Equipped, int Cols = 6)
    {
        Cat = &C;
        Counts = Bag;
        Worn = Equipped;
        GridCols = std::max(1, Cols);
        Cursors.assign(C.Tabs.size(), 0);
        Tab = 0;
        ActionsOpen = false;
        ActionCursor = 0;
        IsOpen = true;
        Rebuild();
    }

    void Close() { IsOpen = false; ActionsOpen = false; }
    bool Opened() const { return IsOpen; }

    /** The host's bag changed (an Intent ran): keep the tab and cursor, refresh the rows. */
    void Refresh(const std::map<std::string, int>& Bag, const std::map<std::string, std::string>& Equipped)
    {
        Counts = Bag;
        Worn = Equipped;
        Rebuild();
    }

    // ---- navigation
    void NextTab() { if (!Cat) return; Tab = (Tab + 1) % static_cast<int>(Cat->Tabs.size()); ActionsOpen = false; Rebuild(); }
    void PrevTab() { if (!Cat) return; Tab = (Tab + static_cast<int>(Cat->Tabs.size()) - 1) % static_cast<int>(Cat->Tabs.size()); ActionsOpen = false; Rebuild(); }
    void SelectTab(int T) { if (!Cat || T < 0 || T >= static_cast<int>(Cat->Tabs.size())) return; Tab = T; ActionsOpen = false; Rebuild(); }

    void Up()    { if (ActionsOpen) { MoveAction(-1); return; } MoveCursor(-GridCols); }
    void Down()  { if (ActionsOpen) { MoveAction(+1); return; } MoveCursor(+GridCols); }
    void Left()  { if (ActionsOpen) return; MoveCursor(-1); }
    void Right() { if (ActionsOpen) return; MoveCursor(+1); }

    /** Confirm: open the actions of the highlighted item, or pick the highlighted action (returns true with Out). */
    bool Confirm(Intent& Out)
    {
        Out = Intent();
        const Entry* E = Selected();
        if (!E) return false;
        if (!ActionsOpen)
        {
            if (E->Def->Actions.empty()) return false;
            ActionsOpen = true;
            ActionCursor = 0;
            return false;
        }
        const std::string& A = E->Def->Actions[static_cast<size_t>(ActionCursor)];
        Out.Action = A == "EQUIP" && E->Equipped ? "UNEQUIP" : A;
        Out.ItemId = E->Def->Id;
        Out.Slot = E->Def->Slot;
        Out.Count = A == "DROP" || A == "SPLIT" ? std::max(1, E->Count / (A == "SPLIT" ? 2 : 1)) : 1;
        ActionsOpen = false;
        return true;
    }

    /** Back: close the actions first; then the inventory. Returns true when the inventory closed. */
    bool Back()
    {
        if (ActionsOpen) { ActionsOpen = false; return false; }
        Close();
        return true;
    }

    // ---- what to draw
    const Catalog* Current() const { return Cat; }
    int TabIndex() const { return Tab; }
    std::string TabName() const { return Cat ? Cat->Tabs[static_cast<size_t>(Tab)] : ""; }
    const std::vector<Entry>& Rows() const { return Visible; }
    int Cursor() const { return Cat ? Cursors[static_cast<size_t>(Tab)] : 0; }
    int Cols() const { return GridCols; }
    const Entry* Selected() const
    {
        if (!Cat || Visible.empty()) return nullptr;
        const int C = Cursor();
        return C >= 0 && C < static_cast<int>(Visible.size()) ? &Visible[static_cast<size_t>(C)] : nullptr;
    }
    bool ActionsShown() const { return ActionsOpen; }
    int ActionIndex() const { return ActionCursor; }
    /** The action labels for the selected item, EQUIP shown as UNEQUIP when it is worn. */
    std::vector<std::string> ActionLabels() const
    {
        std::vector<std::string> L;
        if (const Entry* E = Selected())
            for (const std::string& A : E->Def->Actions) L.push_back(A == "EQUIP" && E->Equipped ? "UNEQUIP" : A);
        return L;
    }
    const Theme& Look() const { return ThemeNamed(Cat ? Cat->Theme : "default"); }
    /** Count per tab, for the tab strip's badges. */
    int CountIn(int T) const
    {
        if (!Cat || T < 0 || T >= static_cast<int>(Cat->Tabs.size())) return 0;
        int N = 0;
        const std::string& Name = Cat->Tabs[static_cast<size_t>(T)];
        for (const ItemDef& D : Cat->Items)
        {
            auto It = Counts.find(D.Id);
            if (It != Counts.end() && It->second > 0 && (Name == "ALL" || D.Tab == Name)) ++N;
        }
        return N;
    }

    /** One line for the harness: realm, tab, cursor, selection, actions. */
    std::string Describe() const
    {
        if (!Cat || !IsOpen) return "open=0";
        std::string S = "open=1 realm=" + Cat->Realm + " theme=" + Cat->Theme + " tab=" + TabName() + "(" + std::to_string(Tab + 1) + "/" + std::to_string(Cat->Tabs.size()) + ")";
        S += " rows=" + std::to_string(Visible.size()) + " cursor=" + std::to_string(Cursor());
        if (const Entry* E = Selected()) S += " item=" + E->Def->Id + " x" + std::to_string(E->Count) + (E->Equipped ? " worn" : "");
        if (ActionsOpen) S += " actions=" + std::to_string(ActionCursor);
        return S;
    }

private:
    void Rebuild()
    {
        Visible.clear();
        if (!Cat) return;
        const std::string& Name = Cat->Tabs[static_cast<size_t>(Tab)];
        for (const ItemDef& D : Cat->Items)
        {
            auto It = Counts.find(D.Id);
            if (It == Counts.end() || It->second <= 0) continue;
            if (Name != "ALL" && D.Tab != Name) continue;
            Entry E;
            E.Def = &D;
            E.Count = It->second;
            auto W = Worn.find(D.Slot);
            E.Equipped = !D.Slot.empty() && W != Worn.end() && W->second == D.Id;
            Visible.push_back(E);
        }
        int& C = Cursors[static_cast<size_t>(Tab)];
        if (Visible.empty()) C = 0;
        else C = std::max(0, std::min(C, static_cast<int>(Visible.size()) - 1));
    }

    void MoveCursor(int Delta)
    {
        if (!Cat || Visible.empty()) return;
        const int N = static_cast<int>(Visible.size());
        int& C = Cursors[static_cast<size_t>(Tab)];
        if (Delta == -1 || Delta == +1) { C = (C + Delta + N) % N; return; }   // a row wraps end to end
        const int Next = C + Delta;                                            // a column: stay on the grid
        if (Next >= 0 && Next < N) C = Next;
        else if (Delta > 0 && C / GridCols < (N - 1) / GridCols) C = N - 1;    // a short last row: land on its end
    }

    void MoveAction(int Delta)
    {
        const Entry* E = Selected();
        if (!E || E->Def->Actions.empty()) return;
        const int N = static_cast<int>(E->Def->Actions.size());
        ActionCursor = (ActionCursor + Delta + N) % N;
    }

    const Catalog* Cat = nullptr;
    std::map<std::string, int> Counts;
    std::map<std::string, std::string> Worn;   // slot -> item id
    std::vector<int> Cursors;
    std::vector<Entry> Visible;
    int Tab = 0, GridCols = 6, ActionCursor = 0;
    bool ActionsOpen = false, IsOpen = false;
};

} // namespace inv
} // namespace daedalus
