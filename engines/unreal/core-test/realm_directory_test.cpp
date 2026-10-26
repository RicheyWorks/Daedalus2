// SPDX-License-Identifier: MIT
// The realm directory seam: Sol's /api/v1/realms DTO read and checked against the session's realm table.
//   g++ -std=c++17 -O2 -Wall -Wextra -I ../DaedalusLink/Source/DaedalusLink/Public realm_directory_test.cpp -o dir_test && ./dir_test

#include "DaedalusRealmDirectoryCore.h"

#include <iostream>

using namespace daedalus::directory;

static int Ok = 0, Total = 0;
static void Check(const std::string& Name, bool Cond, const std::string& Why = "")
{
    ++Total;
    Ok += Cond;
    std::cout << (Cond ? "PASS " : "FAIL ") << Name << (Cond || Why.empty() ? "" : "  " + Why) << "\n";
}

static const char* FULL = R"({"schemaVersion": 1, "chunkSize": 16, "coordinates": "xyz-y-up-metres", "realms": [
  {"id": "world-zero", "title": "World Zero", "realm": "WORLD-ZERO", "catalog": "world-zero", "protocol": "WORLD_V1", "manifestPath": "/api/v1/world/world-zero", "chunkPathTemplate": "/api/v1/world/world-zero/chunk/blocks?x={x}&y={y}&z={z}", "blockEditsSupported": true},
  {"id": "gallery", "title": "Gallery City", "realm": "GALLERY-CITY", "catalog": "gallery-city", "protocol": "WORLD_V1", "manifestPath": "/api/v1/world/gallery", "chunkPathTemplate": "/api/v1/world/gallery/chunk/blocks?x={x}&y={y}&z={z}", "blockEditsSupported": true},
  {"id": "parcels", "title": "Parcels", "realm": "PARCELS", "catalog": "parcels", "protocol": "WORLD_V1", "manifestPath": "/api/v1/world/parcels", "chunkPathTemplate": "/api/v1/world/parcels/chunk/blocks?x={x}&y={y}&z={z}", "blockEditsSupported": true},
  {"id": "bricks", "title": "Bricks", "realm": "BRICKS", "catalog": "bricks", "protocol": "WORLD_V1", "manifestPath": "/api/v1/world/bricks", "chunkPathTemplate": "/api/v1/world/bricks/chunk/blocks?x={x}&y={y}&z={z}", "blockEditsSupported": true},
  {"id": "labyrinth", "title": "Labyrinth", "realm": "LABYRINTH", "catalog": "labyrinth", "protocol": "WORLD_V1", "manifestPath": "/api/v1/world/labyrinth", "chunkPathTemplate": "/api/v1/world/labyrinth/chunk/blocks?x={x}&y={y}&z={z}", "blockEditsSupported": true},
  {"id": "custom-sky", "title": "Someone's world", "realm": null, "catalog": null, "protocol": "WORLD_V1", "manifestPath": "/api/v1/world/custom-sky", "chunkPathTemplate": "/api/v1/world/custom-sky/chunk/blocks?x={x}&y={y}&z={z}", "blockEditsSupported": true},
  {"id": "ocean-sea", "title": "Ocean", "realm": "OCEAN", "catalog": "ocean", "protocol": "OCEAN_V1", "manifestPath": "/api/v1/ocean/v1", "chunkPathTemplate": "/api/v1/ocean/v1/chunk?x={x}&y={y}&z={z}", "blockEditsSupported": false}
]})";

int main()
{
    Directory D = Read(FULL);
    Check("the full directory reads", D.Ok, D.Why);
    Check("header", D.SchemaVersion == 1 && D.ChunkSize == 16 && D.Coordinates == "xyz-y-up-metres" && D.Rows.size() == 7);
    Check("a bound row carries the session realm and catalog", D.ForRealm("GALLERY-CITY") && D.ForRealm("GALLERY-CITY")->Id == "gallery" && D.ForRealm("GALLERY-CITY")->Catalog == "gallery-city");
    Check("a null realm reads as unbound, and is still listed by id", D.ById("custom-sky") && !D.ById("custom-sky")->Bound() && !D.ForRealm(""));
    Check("the chunk url comes from the server's template", D.ChunkUrl("PARCELS", 3, -1, 7) == "/api/v1/world/parcels/chunk/blocks?x=3&y=-1&z=7");
    Check("no url for an unhosted realm", D.ChunkUrl("PORTAL", 0, 0, 0).empty());
    Check("ocean row: OCEAN_V1, no block edits", D.ForRealm("OCEAN") && D.ForRealm("OCEAN")->Protocol == "OCEAN_V1" && !D.ForRealm("OCEAN")->BlockEdits);
    Check("every gated realm and the Ocean have a host; PORTAL needs none", D.Unhosted().empty());

    Directory Two = Read(R"({"schemaVersion": 1, "realms": [{"id": "world-zero", "realm": "WORLD-ZERO", "protocol": "WORLD_V1"}]})");
    Check("a directory with only World Zero names the five unhosted realms", Two.Ok && Two.Unhosted().size() == 5 && Two.Unhosted()[0] == "GALLERY-CITY" && Two.Unhosted()[4] == "OCEAN");
    Check("schema 2 refused", !Read(R"({"schemaVersion": 2, "realms": []})").Ok);
    Check("a row binding an unknown realm is refused", !Read(R"({"schemaVersion": 1, "realms": [{"id": "x", "realm": "MOON", "protocol": "WORLD_V1"}]})").Ok);
    Check("two worlds binding one realm are refused (the server would 503 too)", !Read(R"({"schemaVersion": 1, "realms": [{"id": "a", "realm": "PARCELS", "protocol": "WORLD_V1"}, {"id": "b", "realm": "PARCELS", "protocol": "WORLD_V1"}]})").Ok);
    Check("a duplicate id is refused", !Read(R"({"schemaVersion": 1, "realms": [{"id": "a", "protocol": "WORLD_V1"}, {"id": "a", "protocol": "WORLD_V1"}]})").Ok);
    Check("broken json refused with a reason", Read("{\"schemaVersion\": 1, ").Why.rfind("json:", 0) == 0);

    std::cout << Ok << "/" << Total << "\n";
    return Ok == Total ? 0 : 1;
}
