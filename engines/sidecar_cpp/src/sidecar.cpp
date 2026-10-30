// SPDX-License-Identifier: MIT
#include "daedalus/sidecar/sidecar.hpp"
#include <cmath>
#include <filesystem>

namespace daedalus::sidecar {
namespace fs = std::filesystem;
namespace {
Vec3 vec3(const Json& j) { if (!j.isArray() || j.size() != 3) throw JsonError("expected [x, y, z]"); return {j[0].asNumber(), j[1].asNumber(), j[2].asNumber()}; }
Rotator rot(const Json& j) { Vec3 v = vec3(j); return {v[0], v[1], v[2]}; }
std::optional<Vec3> optVec3(const Json& j, const char* k) { const Json* v = j.find(k); if (!v || v->isNull()) return std::nullopt; return vec3(*v); }
std::string str(const Json& j, const char* k, const std::string& d = "") { const Json* v = j.find(k); return v && v->isString() ? v->str : d; }
bool endsWith(const std::string& s, const std::string& t) { return s.size() >= t.size() && s.compare(s.size() - t.size(), t.size(), t) == 0; }
std::string fmt(const Rotator& r) { return "[" + std::to_string(r.pitch) + ", " + std::to_string(r.yaw) + ", " + std::to_string(r.roll) + "]"; }
}  // namespace

double Hinge::openAngleDeg() const {
    if (!openBlenderEulerDeg || !openUe) return 0.0;
    const Vec3& e = *openBlenderEulerDeg;
    int k = 2; for (int i = 0; i < 3; ++i) if (std::fabs(e[i]) > std::fabs(e[k])) k = i;
    return k == 2 ? openUe->yaw : e[k];
}
const Socket* SocketsFile::socket(const std::string& n) const { for (auto& s : sockets) if (s.name == n) return &s; return nullptr; }
const Hinge* SocketsFile::hingeFor(const std::string& m) const { for (auto& h : hinges) if (h.mover == m) return &h; return nullptr; }
const MaterialInstance* MaterialVariants::forState(const std::string& st) const { for (auto& i : instances) if (i.state == st) return &i; return nullptr; }

SocketsFile parseSockets(const Json& j, const std::string& path) {
    SocketsFile f; f.path = path;
    f.schema = str(j, "schema"); f.asset = j["asset"].asString(); f.units = str(j, "units"); f.space = str(j, "space"); f.note = str(j, "note");
    const bool skeletal = f.schema.rfind("bb-skeletal-sockets/", 0) == 0;
    if (skeletal) { if (f.units.empty()) f.units = "cm"; if (f.space.empty()) f.space = "unreal"; }
    for (auto& s : j["sockets"].arr) {
        Socket o; o.name = s["name"].asString(); o.kind = str(s, "kind");
        if (skeletal) {
            o.bone = s["bone"].asString(); o.parent = o.bone; o.locationCm = vec3(s["location_ue_cm"]);
            o.locationM = optVec3(s, "location_m"); o.offsetFromBoneHeadM = optVec3(s, "offset_from_bone_head_m");
            o.offsetFromBoneHeadUeCm = optVec3(s, "offset_from_bone_head_ue_cm");
        } else { o.parent = str(s, "parent", f.asset); o.locationCm = vec3(s["location"]); }
        o.rotation = rot(s["rotation"]);
        if (auto* n = s.find("native_rotation_predicted")) if (n->isArray()) o.nativePredicted = rot(*n);
        if (auto* n = s.find("native_matches")) if (n->type == Json::Type::Bool) o.nativeMatches = n->b;
        f.sockets.push_back(std::move(o));
    }
    if (auto* hs = j.find("hinges")) for (auto& h : hs->arr) {
        Hinge o; o.socket = h["socket"].asString(); o.mover = str(h, "mover"); o.pivotM = vec3(h["pivot_m"]);
        o.motion = str(h, "motion", "rotate");
        if (auto* a = h.find("alt_movers")) for (auto& m : a->arr) o.altMovers.push_back(m.asString());
        o.openBlenderEulerDeg = optVec3(h, "open_blender_euler_deg");
        if (auto v = optVec3(h, "open_ue_rotator")) o.openUe = Rotator{(*v)[0], (*v)[1], (*v)[2]};
        o.axisBlender = optVec3(h, o.motion == "slide" ? "slide_axis_blender" : "spin_axis_blender");
        o.axisUe = optVec3(h, o.motion == "slide" ? "slide_axis_ue" : "spin_axis_ue");
        if (auto* t = h.find("travel_m")) if (t->isArray() && t->size() == 2) o.travelM = std::array<double, 2>{(*t)[0].asNumber(), (*t)[1].asNumber()};
        if (auto* r = h.find("rpm")) if (r->isNumber()) o.rpm = r->num;
        f.hinges.push_back(std::move(o));
    }
    return f;
}
SocketsFile loadSockets(const std::string& p) { return parseSockets(parseJsonFile(p), p); }

namespace {
Param param(const std::string& key, const Json& v) {
    Param q;
    if (v.isNumber()) { q.kind = Param::Kind::Number; q.number = v.num; }
    else if (v.type == Json::Type::Bool) { q.kind = Param::Kind::Number; q.number = v.b ? 1.0 : 0.0; }
    else if (v.isString()) { q.kind = Param::Kind::Text; q.text = v.str; }
    else if (v.isObject()) {
        q.kind = Param::Kind::Color; q.color.srgbHex = str(v, "srgb_hex");
        if (auto* l = v.find("linear_rgba")) for (size_t i = 0; i < 4 && i < l->size(); ++i) q.color.linearRgba[i] = (*l)[i].asNumber();
    } else if (v.isArray()) { q.kind = Param::Kind::Vector; for (auto& x : v.arr) if (x.isNumber()) q.vector.push_back(x.num); }
    else { q.kind = Param::Kind::Text; (void)key; }
    return q;
}
MaterialVariants one(const Json& j, const Json& top, const std::string& path, const std::string& group) {
    MaterialVariants m; m.path = path; m.group = group;
    m.schema = str(top, "schema"); m.asset = j["asset"].asString(); m.status = str(j, "status", str(top, "status")); m.hook = str(j, "hook");
    if (auto* s = j.find("slot")) if (s->isNumber()) m.slot = int(s->num);
    if (auto* pm = j.find("parent_material")) m.parentMaterial = pm->isObject() ? str(*pm, "name") : (pm->isString() ? pm->str : "");
    else m.parentMaterial = str(j, "parent");
    for (auto& kv : j["instances"].obj) {
        MaterialInstance mi; mi.name = kv.first; mi.state = str(kv.second, "state");
        const Json* ps = kv.second.find("params");
        for (auto& p : (ps && ps->isObject() ? *ps : kv.second).obj) if (p.first != "state") mi.params.emplace(p.first, param(p.first, p.second));
        m.instances.push_back(std::move(mi));
    }
    return m;
}
}  // namespace

std::vector<MaterialVariants> parseMaterialVariants(const Json& j, const std::string& path) {
    std::vector<MaterialVariants> out;
    if (j.has("asset")) { out.push_back(one(j, j, path, "")); return out; }
    for (auto& kv : j.obj) if (kv.second.isObject() && kv.second.has("asset") && kv.second.has("instances")) out.push_back(one(kv.second, j, path, kv.first));
    if (out.empty()) throw JsonError("no asset blocks with instances");
    return out;
}
std::vector<MaterialVariants> loadMaterialVariants(const std::string& p) { return parseMaterialVariants(parseJsonFile(p), p); }

double srgbToLinear(double c) { return c <= 0.04045 ? c / 12.92 : std::pow((c + 0.055) / 1.055, 2.4); }

std::vector<std::string> validate(const SocketsFile& f) {
    std::vector<std::string> e; auto bad = [&](const std::string& m) { e.push_back(f.asset + ": " + m); };
    if (f.units != "cm") bad("units != cm");
    if (f.space != "unreal") bad("space != unreal");
    for (auto& s : f.sockets) {
        if (s.name.rfind("SOCKET_", 0) != 0) bad(s.name + " lacks SOCKET_ prefix");
        Mat3 want = rotatorToMatrix(s.rotation);
        // pre-rotated empty: what we export must import natively as the sidecar frame
        if (maxAbsDiff(predictNative(blenderEmptyMatrix(want)), want) > 1e-6) bad(s.name + " pre-rotation round trip");
        if (s.nativeMatches.value_or(false) && s.nativePredicted && !rotatorsEquivalent(*s.nativePredicted, s.rotation))
            bad(s.name + " native_matches but native " + fmt(*s.nativePredicted) + " != sidecar " + fmt(s.rotation));
        if (s.kind == "plain" && !rotatorsEquivalent(s.rotation, {})) bad(s.name + " plain socket not mesh-aligned");
        if (s.kind == "attach") {  // +X along the shaft, +Z up: frame must be orthonormal right-handed in UE matrix terms
            Mat3 m = want, mt = transpose(m);
            if (maxAbsDiff(mul(mt, m), identity()) > 1e-6) bad(s.name + " attach frame not orthonormal");
        }
    }
    auto sameCm = [](const Vec3& a, const Vec3& b) { for (int i = 0; i < 3; ++i) if (std::fabs(a[i] - b[i]) > 0.01) return false; return true; };
    for (auto& s : f.sockets) {  // skeletal: UE copies must be the converted Blender values
        if (s.locationM && !sameCm(blenderToUe(*s.locationM), s.locationCm)) bad(s.name + " location_ue_cm != convert(location_m)");
        if (s.offsetFromBoneHeadM && s.offsetFromBoneHeadUeCm && !sameCm(blenderToUe(*s.offsetFromBoneHeadM), *s.offsetFromBoneHeadUeCm))
            bad(s.name + " offset_from_bone_head_ue_cm != convert(offset_from_bone_head_m)");
    }
    for (auto& h : f.hinges) {
        const Socket* s = f.socket(h.socket);
        if (!s) { bad("hinge socket missing: " + h.socket); continue; }
        if (!sameCm(blenderToUe(h.pivotM), s->locationCm)) bad(h.socket + " location != pivot_m");
        if (h.motion == "rotate") {
            if (!h.openBlenderEulerDeg || !h.openUe) { bad(h.socket + " rotate hinge without open pose"); continue; }
            Rotator conv = blenderEulerToUeRotator(*h.openBlenderEulerDeg);
            if (!rotatorsEquivalent(conv, *h.openUe)) bad(h.socket + " open_ue_rotator " + fmt(*h.openUe) + " != converted " + fmt(conv));
        } else if (h.motion == "spin" || h.motion == "slide") {
            if (!h.axisBlender || !h.axisUe) { bad(h.socket + " " + h.motion + " without axis"); continue; }
            Vec3 a = blenderDirToUe(*h.axisBlender), b = *h.axisUe;
            for (int i = 0; i < 3; ++i) if (std::fabs(a[i] - b[i]) > 1e-6) { bad(h.socket + " axis_ue != convert(axis_blender)"); break; }
        } else bad(h.socket + " unknown motion " + h.motion);
    }
    return e;
}

std::vector<std::string> validate(const MaterialVariants& m) {
    std::vector<std::string> e; auto bad = [&](const std::string& s) { e.push_back(m.asset + ": " + s); };
    if (m.schema.rfind("bb-material-variants/", 0) != 0) bad("unknown schema " + m.schema);
    if (m.instances.empty()) bad("no instances");
    for (auto& i : m.instances) {
        if (i.name.rfind("MI_", 0) != 0) bad(i.name + " lacks MI_ prefix");
        for (auto& p : i.params) if (p.second.kind == Param::Kind::Color && p.second.color.srgbHex.size() == 6) {
            for (int c = 0; c < 3; ++c) {
                double v = std::stoi(p.second.color.srgbHex.substr(size_t(c) * 2, 2), nullptr, 16) / 255.0;
                if (std::fabs(srgbToLinear(v) - p.second.color.linearRgba[size_t(c)]) > 1e-4) { bad(i.name + "." + p.first + " linear != sRGB(" + p.second.color.srgbHex + ")"); break; }
            }
        }
    }
    return e;
}

WorldSocket socketWorld(const Socket& s, const Placement& p) {
    Mat3 yaw = rotatorToMatrix({0, p.yawDeg, 0});
    Vec3 off = transform(yaw, s.locationCm);
    return {{p.locationCm[0] + off[0], p.locationCm[1] + off[1], p.locationCm[2] + off[2]}, matrixToRotator(mul(yaw, rotatorToMatrix(s.rotation)))};
}

void SocketRegistry::add(SocketsFile f) { auto k = f.asset; sockets_[k] = std::move(f); }
void SocketRegistry::add(MaterialVariants m) { auto k = m.asset; variants_[k] = std::move(m); }
const SocketsFile* SocketRegistry::sockets(const std::string& a) const { auto it = sockets_.find(a); return it == sockets_.end() ? nullptr : &it->second; }
const MaterialVariants* SocketRegistry::variants(const std::string& a) const { auto it = variants_.find(a); return it == variants_.end() ? nullptr : &it->second; }
std::optional<WorldSocket> SocketRegistry::find(const std::string& a, const std::string& n, const Placement& p) const {
    const SocketsFile* f = sockets(a); if (!f) return std::nullopt;
    const Socket* s = f->socket(n); if (!s) return std::nullopt;
    return socketWorld(*s, p);
}

size_t SocketRegistry::loadDirectory(const std::string& root) {
    size_t n = 0; std::error_code ec;
    for (fs::recursive_directory_iterator it(root, fs::directory_options::skip_permission_denied, ec), end; it != end; it.increment(ec)) {
        if (ec) { errors_.push_back(root + ": " + ec.message()); break; }
        if (!it->is_regular_file(ec)) continue;
        std::string p = it->path().string(), name = it->path().filename().string();
        try {
            if (endsWith(name, ".sockets.json")) { add(loadSockets(p)); ++n; }
            else if (endsWith(name, "material_variants.json")) { for (auto& m : loadMaterialVariants(p)) add(std::move(m)); ++n; }
        } catch (const std::exception& x) { errors_.push_back(p + ": " + x.what()); }
    }
    return n;
}

}  // namespace daedalus::sidecar
