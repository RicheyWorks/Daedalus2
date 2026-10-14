// SPDX-License-Identifier: MIT

#pragma once

// The realm directory seam (Sol's PR80, docs/production/REALM-DIRECTORY.md, merged 97b23eab):
//
//   GET /api/v1/realms -> { schemaVersion, chunkSize, coordinates, realms: [
//       { id, title, realm, catalog, protocol: "WORLD_V1"|"OCEAN_V1", manifestPath, chunkPathTemplate,
//         blockEditsSupported } ] }
//
// `realm` and `catalog` are the native session ids (DaedalusRealmSessionCore Realms()) or null for a world the
// server does not bind to a session realm. This header reads the DTO (DaedalusLandRegistryCore's JSON reader)
// and answers the two questions the world host asks: which server world hosts session realm X, and does every
// gated realm have a host. Pure C++17; core-test/realm_directory_test.cpp proves it.

#include "DaedalusLandRegistryCore.h"
#include "DaedalusRealmSessionCore.h"

#include <string>
#include <vector>

namespace daedalus
{
namespace directory
{

struct Row
{
    std::string Id, Title, Realm, Catalog, Protocol, ManifestPath, ChunkPathTemplate;
    bool BlockEdits = false;
    bool Bound() const { return !Realm.empty(); }
};

struct Directory
{
    int SchemaVersion = 0, ChunkSize = 0;
    std::string Coordinates;
    std::vector<Row> Rows;
    bool Ok = false;
    std::string Why;

    const Row* ForRealm(const std::string& SessionRealm) const
    {
        if (SessionRealm.empty()) return nullptr;   // unbound rows have an empty Realm; never match them
        for (const Row& R : Rows) if (R.Realm == SessionRealm) return &R;
        return nullptr;
    }
    const Row* ById(const std::string& Id) const
    {
        for (const Row& R : Rows) if (R.Id == Id) return &R;
        return nullptr;
    }
    /** The chunk URL for a bound realm at a block coordinate, from the server's own template. */
    std::string ChunkUrl(const std::string& SessionRealm, int X, int Y, int Z) const
    {
        const Row* R = ForRealm(SessionRealm);
        if (!R) return "";
        std::string T = R->ChunkPathTemplate;
        auto Sub = [&](const char* K, int V) { const size_t I = T.find(K); if (I != std::string::npos) T.replace(I, std::strlen(K), std::to_string(V)); };
        Sub("{x}", X); Sub("{y}", Y); Sub("{z}", Z);
        return T;
    }
    /** Session realms the hero can gate to that no server world hosts. PORTAL is the 8-bit realm (no host);
     *  everything else in Realms() wants a row. */
    std::vector<std::string> Unhosted() const
    {
        std::vector<std::string> Out;
        for (const session::RealmDef& D : session::Realms())
            if (D.Id != "PORTAL" && !ForRealm(D.Id)) Out.push_back(D.Id);
        return Out;
    }
};

inline Directory Read(const std::string& Json)
{
    using namespace landreg;
    Directory D;
    Value Root;
    std::string Err;
    Reader R(Json);
    if (!R.Parse(Root, Err)) { D.Why = "json: " + Err; return D; }
    if (Root.K != Value::Object) { D.Why = "not an object"; return D; }
    D.SchemaVersion = IntOf(Root.Get("schemaVersion"));
    if (D.SchemaVersion != 1) { D.Why = "schemaVersion " + std::to_string(D.SchemaVersion) + " (want 1)"; return D; }
    D.ChunkSize = IntOf(Root.Get("chunkSize"));
    D.Coordinates = StrOf(Root.Get("coordinates"));
    const Value* Rows = Root.Get("realms");
    if (!Rows || Rows->K != Value::Array) { D.Why = "no realms array"; return D; }
    for (const Value& V : Rows->A)
    {
        Row X;
        X.Id = StrOf(V.Get("id"));
        X.Title = StrOf(V.Get("title"));
        X.Realm = StrOf(V.Get("realm"));          // null -> ""
        X.Catalog = StrOf(V.Get("catalog"));
        X.Protocol = StrOf(V.Get("protocol"));
        X.ManifestPath = StrOf(V.Get("manifestPath"));
        X.ChunkPathTemplate = StrOf(V.Get("chunkPathTemplate"));
        const Value* B = V.Get("blockEditsSupported");
        X.BlockEdits = B && B->K == Value::Bool && B->B;
        if (X.Id.empty() || X.Protocol.empty()) { D.Why = "row without id/protocol"; return D; }
        if (X.Bound() && !session::Find(X.Realm)) { D.Why = "row " + X.Id + " binds unknown realm " + X.Realm; return D; }
        for (const Row& Prev : D.Rows)
        {
            if (Prev.Id == X.Id) { D.Why = "duplicate id " + X.Id; return D; }
            if (X.Bound() && Prev.Realm == X.Realm) { D.Why = "two worlds bind " + X.Realm; return D; }
        }
        D.Rows.push_back(X);
    }
    D.Ok = true;
    return D;
}

} // namespace directory
} // namespace daedalus
