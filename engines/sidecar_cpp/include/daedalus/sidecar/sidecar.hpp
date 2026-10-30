// SPDX-License-Identifier: MIT
// Daedalus asset sidecars (engine-free, C++17):
//   <Asset>.sockets.json                 sockets (UE space, cm) + optional hinges (mover, pivot, open angle)
//   <Asset>[.states].material_variants.json   bb-material-variants/1: material-instance parameter manifests per state
// Schemas are written by tools/blender/sockets_sidecar.py and the blender-team variant tools; this is the C++ reader.
#pragma once
#include "daedalus/sidecar/axis.hpp"
#include "daedalus/sidecar/json.hpp"
#include <map>
#include <optional>
#include <string>
#include <vector>

namespace daedalus::sidecar {

struct Socket {
    std::string name;     // always SOCKET_*
    std::string parent;   // node the location is relative to
    Vec3 locationCm{};    // UE mesh space
    Rotator rotation;     // authoritative (sidecar wins over the native socket)
    std::string kind;     // "plain" | "attach" | ""
    std::optional<Rotator> nativePredicted;
    std::optional<bool> nativeMatches;
    // bb-skeletal-sockets/1 (rigged Mobs): parent is a bone; Blender-space copies kept for validation
    std::string bone;
    std::optional<Vec3> locationM, offsetFromBoneHeadM, offsetFromBoneHeadUeCm;
};

struct Hinge {
    std::string socket;   // SOCKET_Hinge_<Part> (or SOCKET_Spin / SOCKET_Slide)
    std::string mover;    // separate mover asset that moves
    std::vector<std::string> altMovers;
    Vec3 pivotM{};        // Blender metres, relative to the root
    std::string motion = "rotate";            // "rotate" (open pose) | "spin" | "slide"
    std::optional<Vec3> openBlenderEulerDeg;  // rotate: open pose in Blender
    std::optional<Rotator> openUe;            // rotate: open pose as a relative rotation in UE mesh space
    std::optional<Vec3> axisBlender, axisUe;  // spin / slide axis
    std::optional<std::array<double, 2>> travelM;  // slide range
    std::optional<double> rpm;                // spin rate
    double openAngleDeg() const;  // rotate: signed main angle (UE yaw for door hinges); 0 otherwise
};

struct SocketsFile {
    std::string path, schema, asset, units, space, note;  // schema "" (static) or "bb-skeletal-sockets/1"
    std::vector<Socket> sockets;
    std::vector<Hinge> hinges;
    const Socket* socket(const std::string& name) const;
    const Hinge* hingeFor(const std::string& mover) const;
};

struct Color { std::string srgbHex; std::array<double, 4> linearRgba{}; };
struct Param {
    enum class Kind { Number, Text, Color, Vector } kind = Kind::Number;
    double number = 0; std::string text; Color color; std::vector<double> vector;
};
struct MaterialInstance { std::string name, state; std::map<std::string, Param> params; };
struct MaterialVariants {
    std::string path, schema, asset, status, parentMaterial, hook, group;  // group: bundle key for multi-asset files
    int slot = 0;
    std::vector<MaterialInstance> instances;
    const MaterialInstance* forState(const std::string& state) const;
};

SocketsFile parseSockets(const Json& j, const std::string& path = "");
SocketsFile loadSockets(const std::string& path);
// A variants file holds one asset (top-level "asset") or a bundle of {"<group>": {"asset", "instances", ...}} blocks.
std::vector<MaterialVariants> parseMaterialVariants(const Json& j, const std::string& path = "");
std::vector<MaterialVariants> loadMaterialVariants(const std::string& path);

// Consistency checks; empty result = valid. Tolerances: rotation frames 1e-3, locations 0.01 cm.
std::vector<std::string> validate(const SocketsFile& f);
std::vector<std::string> validate(const MaterialVariants& m);

double srgbToLinear(double c01);

// ---- Daedalus socket hook -----------------------------------------------------------------------------------------
// Engine-free placement: a Blender-built asset is placed at locationCm with actor yaw (default -90, kPlacementYawDeg).
struct Placement { Vec3 locationCm{}; double yawDeg = kPlacementYawDeg; };
struct WorldSocket { Vec3 locationCm{}; Rotator rotation; };
WorldSocket socketWorld(const Socket& s, const Placement& p);  // root-parented sockets

class SocketRegistry {
public:
    // Recursively loads every *.sockets.json and *material_variants.json under root. Returns the number of files loaded;
    // parse errors are collected in errors().
    size_t loadDirectory(const std::string& root);
    void add(SocketsFile f);
    void add(MaterialVariants m);
    const SocketsFile* sockets(const std::string& asset) const;
    const MaterialVariants* variants(const std::string& asset) const;
    std::optional<WorldSocket> find(const std::string& asset, const std::string& socket, const Placement& p) const;
    const std::map<std::string, SocketsFile>& allSockets() const { return sockets_; }
    const std::map<std::string, MaterialVariants>& allVariants() const { return variants_; }
    const std::vector<std::string>& errors() const { return errors_; }
private:
    std::map<std::string, SocketsFile> sockets_;
    std::map<std::string, MaterialVariants> variants_;
    std::vector<std::string> errors_;
};

}  // namespace daedalus::sidecar
