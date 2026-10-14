// SPDX-License-Identifier: MIT

#pragma once

// The land registry seam (BASE-LAYER.md row 11, Sol's PR85 docs/production/REALM-LAND-API.md):
//
//   GET /api/v1/realms/{REALM}/lands?district=0..99  ->
//   { schemaVersion, realm, revision, district, gridSide, pitchMetres, coordinates, reservedCells[], lands[
//       { landNumber, cellX, cellY, size, seed (int64 as a decimal string), originEastMetres, originNorthMetres } ] }
//
// This header reads that DTO (a small JSON reader, no exceptions: UE game targets compile with /EHsc off) and
// reconciles it with what the editor laid down (daedalus_plots: a plot per free cell, labelled by deed number):
// which plots agree, which the server has moved, which only one side knows. Pure C++17 so core-test proves it;
// ADaedalusWorldActor and daedalus_land_sync.py are the two consumers. The registry is a placement ledger, not
// ownership (Sol 29151): nothing here implies a mint.

#include <cstdlib>
#include <cstring>
#include <map>
#include <string>
#include <vector>

namespace daedalus
{
namespace landreg
{

struct Land
{
    int Number = -1, CellX = -1, CellY = -1, Size = 1;
    std::string Seed;                 // decimal int64, kept as text
    double EastM = 0.0, NorthM = 0.0; // origin of the south-west cell's centre, realm metres from the hub cell
};

struct District
{
    int SchemaVersion = 0, Revision = 0, Number = -1, GridSide = 100;
    double PitchM = 256.0;
    std::string Realm, Coordinates;
    std::vector<int> Reserved;
    std::vector<Land> Lands;
    bool Ok = false;
    std::string Why;
};

// ---- a minimal JSON reader: objects, arrays, strings, numbers, true/false/null -------------------------------

struct Value
{
    enum Kind { Null, Bool, Number, String, Array, Object } K = Null;
    bool B = false;
    double N = 0.0;
    std::string S;                         // String: the text; Number: the original digits (int64 seeds survive)
    std::vector<Value> A;
    std::vector<std::pair<std::string, Value>> O;
    const Value* Get(const char* Key) const
    {
        for (const auto& KV : O) if (KV.first == Key) return &KV.second;
        return nullptr;
    }
};

class Reader
{
public:
    explicit Reader(const std::string& Text) : T(Text) {}
    bool Parse(Value& Out, std::string& Err)
    {
        I = 0;
        if (!ParseValue(Out, 0)) { Err = Error.empty() ? "bad json" : Error; return false; }
        Skip();
        if (I != T.size()) { Err = "trailing text at " + std::to_string(I); return false; }
        return true;
    }

private:
    const std::string& T;
    size_t I = 0;
    std::string Error;

    void Skip() { while (I < T.size() && (T[I] == ' ' || T[I] == '\n' || T[I] == '\r' || T[I] == '\t')) ++I; }
    bool Fail(const char* M) { if (Error.empty()) Error = std::string(M) + " at " + std::to_string(I); return false; }
    bool ParseValue(Value& V, int Depth)
    {
        if (Depth > 64) return Fail("too deep");
        Skip();
        if (I >= T.size()) return Fail("unexpected end");
        const char C = T[I];
        if (C == '{')
        {
            V.K = Value::Object; ++I;
            Skip();
            if (I < T.size() && T[I] == '}') { ++I; return true; }
            for (;;)
            {
                Skip();
                std::string Key;
                if (!ParseString(Key)) return false;
                Skip();
                if (I >= T.size() || T[I] != ':') return Fail("expected ':'");
                ++I;
                Value Child;
                if (!ParseValue(Child, Depth + 1)) return false;
                V.O.emplace_back(Key, Child);
                Skip();
                if (I < T.size() && T[I] == ',') { ++I; continue; }
                if (I < T.size() && T[I] == '}') { ++I; return true; }
                return Fail("expected ',' or '}'");
            }
        }
        if (C == '[')
        {
            V.K = Value::Array; ++I;
            Skip();
            if (I < T.size() && T[I] == ']') { ++I; return true; }
            for (;;)
            {
                Value Child;
                if (!ParseValue(Child, Depth + 1)) return false;
                V.A.push_back(Child);
                Skip();
                if (I < T.size() && T[I] == ',') { ++I; continue; }
                if (I < T.size() && T[I] == ']') { ++I; return true; }
                return Fail("expected ',' or ']'");
            }
        }
        if (C == '"') { V.K = Value::String; return ParseString(V.S); }
        if (T.compare(I, 4, "true") == 0) { V.K = Value::Bool; V.B = true; I += 4; return true; }
        if (T.compare(I, 5, "false") == 0) { V.K = Value::Bool; V.B = false; I += 5; return true; }
        if (T.compare(I, 4, "null") == 0) { V.K = Value::Null; I += 4; return true; }
        const size_t S = I;
        while (I < T.size() && (std::strchr("+-0123456789.eE", T[I]) != nullptr)) ++I;
        if (I == S) return Fail("unexpected character");
        V.K = Value::Number;
        V.S = T.substr(S, I - S);
        V.N = std::strtod(V.S.c_str(), nullptr);
        return true;
    }
    bool ParseString(std::string& Out)
    {
        if (I >= T.size() || T[I] != '"') return Fail("expected string");
        ++I;
        Out.clear();
        while (I < T.size())
        {
            const char C = T[I++];
            if (C == '"') return true;
            if (C == '\\')
            {
                if (I >= T.size()) return Fail("bad escape");
                const char E = T[I++];
                switch (E)
                {
                case 'n': Out += '\n'; break;
                case 't': Out += '\t'; break;
                case 'r': Out += '\r'; break;
                case 'b': Out += '\b'; break;
                case 'f': Out += '\f'; break;
                case 'u': if (I + 4 > T.size()) return Fail("bad \\u"); Out += '?'; I += 4; break;   // enough for ids
                default: Out += E; break;
                }
            }
            else Out += C;
        }
        return Fail("unterminated string");
    }
};

inline int IntOf(const Value* V, int Def = 0) { return V && V->K == Value::Number ? static_cast<int>(V->N) : Def; }
inline double NumOf(const Value* V, double Def = 0.0) { return V && V->K == Value::Number ? V->N : Def; }
inline std::string StrOf(const Value* V) { return V ? (V->K == Value::String || V->K == Value::Number ? V->S : "") : ""; }

/** Read one district response. Refuses (Ok=false, Why) anything that is not schema 1 with a lands array. */
inline District ReadDistrict(const std::string& Json)
{
    District D;
    Value Root;
    std::string Err;
    Reader R(Json);
    if (!R.Parse(Root, Err)) { D.Why = "json: " + Err; return D; }
    if (Root.K != Value::Object) { D.Why = "not an object"; return D; }
    D.SchemaVersion = IntOf(Root.Get("schemaVersion"));
    if (D.SchemaVersion != 1) { D.Why = "schemaVersion " + std::to_string(D.SchemaVersion) + " (want 1)"; return D; }
    D.Realm = StrOf(Root.Get("realm"));
    D.Revision = IntOf(Root.Get("revision"));
    D.Number = IntOf(Root.Get("district"), -1);
    D.GridSide = IntOf(Root.Get("gridSide"), 100);
    D.PitchM = NumOf(Root.Get("pitchMetres"), 256.0);
    D.Coordinates = StrOf(Root.Get("coordinates"));
    if (D.Realm.empty() || D.Number < 0 || D.Number > 99) { D.Why = "realm/district missing"; return D; }
    if (const Value* Res = Root.Get("reservedCells"))
        for (const Value& C : Res->A) D.Reserved.push_back(IntOf(&C, -1));
    const Value* Lands = Root.Get("lands");
    if (!Lands || Lands->K != Value::Array) { D.Why = "no lands array"; return D; }
    for (const Value& L : Lands->A)
    {
        Land X;
        X.Number = IntOf(L.Get("landNumber"), -1);
        X.CellX = IntOf(L.Get("cellX"), -1);
        X.CellY = IntOf(L.Get("cellY"), -1);
        X.Size = IntOf(L.Get("size"), 1);
        X.Seed = StrOf(L.Get("seed"));
        X.EastM = NumOf(L.Get("originEastMetres"));
        X.NorthM = NumOf(L.Get("originNorthMetres"));
        if (X.Number < 0 || X.CellX < 0 || X.CellY < 0 || X.Size < 1 || X.Size > 4) { D.Why = "bad land row"; return D; }
        D.Lands.push_back(X);
    }
    D.Ok = true;
    return D;
}

// ---- reconciliation with the editor's plots ----------------------------------------------------------------

/** What the editor has: one entry per plot/estate, by deed number. */
struct Plot
{
    int Number = -1, CellX = -1, CellY = -1, Size = 1;
};

struct Report
{
    int Revision = 0;
    std::vector<int> Agree;                       // same cell and size on both sides
    std::vector<std::pair<int, Land>> Moved;      // the server's current cell/size differs: the editor follows
    std::vector<Land> OnlyServer;                 // the server lists a land the editor has no plot for
    std::vector<int> OnlyEditor;                  // the editor has a plot the server does not list (this district)
    std::vector<int> ReservedButPlotted;          // the editor put a plot on a cell the server reserves
    std::string Describe() const
    {
        return "rev=" + std::to_string(Revision) + " agree=" + std::to_string(Agree.size()) + " moved=" + std::to_string(Moved.size())
             + " only_server=" + std::to_string(OnlyServer.size()) + " only_editor=" + std::to_string(OnlyEditor.size())
             + " reserved_plotted=" + std::to_string(ReservedButPlotted.size());
    }
};

/** Cells in the district: district d covers x in [10*(d%10), +10), y in [10*(d/10), +10). */
inline bool InDistrict(int District, int X, int Y)
{
    return X / 10 == District % 10 && Y / 10 == District / 10;
}

/** CellNumber(x, y) is the realm's spiral number for a cell (DaedalusLandGrid::Number); passed in so this header
 *  does not depend on the grid header. */
template <typename NumberFn>
inline Report Reconcile(const District& D, const std::vector<Plot>& Plots, NumberFn CellNumber)
{
    Report R;
    R.Revision = D.Revision;
    std::map<int, const Land*> Server;
    for (const Land& L : D.Lands) Server[L.Number] = &L;
    std::map<int, const Plot*> Editor;
    for (const Plot& P : Plots)
        if (InDistrict(D.Number, P.CellX, P.CellY)) Editor[P.Number] = &P;
    std::map<int, bool> ReservedSet;
    for (int C : D.Reserved) ReservedSet[C] = true;
    for (const auto& KV : Server)
    {
        auto It = Editor.find(KV.first);
        if (It == Editor.end()) { R.OnlyServer.push_back(*KV.second); continue; }
        const Plot& P = *It->second;
        if (P.CellX == KV.second->CellX && P.CellY == KV.second->CellY && P.Size == KV.second->Size) R.Agree.push_back(KV.first);
        else R.Moved.emplace_back(KV.first, *KV.second);
    }
    for (const auto& KV : Editor)
    {
        if (!Server.count(KV.first)) R.OnlyEditor.push_back(KV.first);
        if (ReservedSet.count(CellNumber(KV.second->CellX, KV.second->CellY))) R.ReservedButPlotted.push_back(KV.first);
    }
    return R;
}

} // namespace landreg
} // namespace daedalus
