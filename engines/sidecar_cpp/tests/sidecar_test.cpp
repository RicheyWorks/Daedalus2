// SPDX-License-Identifier: MIT
// daedalus_sidecar_test [fixtures_dir] [staging_dir ...]
// Unit checks of the axis maths, then every *.sockets.json / *material_variants.json under each directory is parsed and
// validated. Exit code 0 only if all pass and every directory yielded at least one file.
#include "daedalus/sidecar/sidecar.hpp"
#include <cmath>
#include <cstdio>
#include <string>

using namespace daedalus::sidecar;
static int g_fail = 0, g_pass = 0;
#define CHECK(c) do { if (c) ++g_pass; else { ++g_fail; std::printf("FAIL %s:%d %s\n", __FILE__, __LINE__, #c); } } while (0)
static bool near(const Vec3& a, const Vec3& b, double t = 1e-9) { for (int i = 0; i < 3; ++i) if (std::fabs(a[i] - b[i]) > t) return false; return true; }

static void unitTests() {
    CHECK(near(blenderToUe({1, -2, 3}), {100, 200, 300}));
    CHECK(near(gltfToUe({1, 3, 2}), {100, 200, 300}));
    CHECK(near(ueToBlender(blenderToUe({0.3, -0.7, 1.1})), {0.3, -0.7, 1.1}, 1e-12));
    // Blender front (-Y) -> UE +Y; placement yaw -90 turns it onto UE +X.
    Vec3 front = blenderDirToUe({0, -1, 0});
    CHECK(near(front, {0, 1, 0}));
    CHECK(near(applyPlacementYaw(front), {1, 0, 0}, 1e-12));
    CHECK(kPlacementYawDeg == -90.0);
    // rotator <-> matrix round trips
    for (Rotator r : {Rotator{0, 0, 0}, Rotator{10, 20, 30}, Rotator{-45, 170, -90}, Rotator{90, 0, -90}, Rotator{0, -90, 0}})
        CHECK(rotatorsEquivalent(matrixToRotator(rotatorToMatrix(r)), r));
    // Interchange offset A = [0, 180, -90]; an identity empty reads A natively (UEB 48794)
    CHECK(rotatorsEquivalent(matrixToRotator(predictNative(identity())), {0, 180, -90}));
    // pre-rotated empties import as the desired frame (plain and attach)
    for (Rotator r : {Rotator{}, Rotator{90, 0, -90}, Rotator{0, 90, 0}})
        CHECK(maxAbsDiff(predictNative(blenderEmptyMatrix(rotatorToMatrix(r))), rotatorToMatrix(r)) < 1e-9);
    // attach frame: Blender +Z shaft, up hint -Y (front) -> UE [90, 0, -90]-style frame, X along +Z
    Mat3 af = attachFrame({0, 0, 1}, {0, -1, 0});
    CHECK(std::fabs(af[2][0] - 1.0) < 1e-12);
    // hinge: Blender +90 about Z is UE yaw -90 (Y flip)
    CHECK(rotatorsEquivalent(blenderEulerToUeRotator({0, 0, 90}), {0, -90, 0}));
    CHECK(rotatorsEquivalent(blenderEulerToUeRotator({0, 0, -90}), {0, 90, 0}));
    // JSON reader basics
    Json j = parseJson("{\"a\": [1, -2.5e1, true, null, \"x\\u00e9\\n\"], \"b\": {}}");
    CHECK(j["a"][1].asNumber() == -25.0);
    CHECK(j["a"][4].asString() == "x\xc3\xa9\n");
    bool threw = false; try { parseJson("{\"a\": }"); } catch (const JsonError&) { threw = true; }
    CHECK(threw);
    // socket hook: socket at UE +Y 100 cm on an asset placed at (1000, 0, 0) with yaw -90 -> world (1100, 0, 0)
    Socket s; s.name = "SOCKET_T"; s.locationCm = {0, 100, 0};
    WorldSocket w = socketWorld(s, {{1000, 0, 0}, kPlacementYawDeg});
    CHECK(near(w.locationCm, {1100, 0, 0}, 1e-9));
    CHECK(rotatorsEquivalent(w.rotation, {0, -90, 0}));
    CHECK(std::fabs(srgbToLinear(0x6B / 255.0) - 0.147027) < 1e-5);
}

static void dirTest(const std::string& dir) {
    SocketRegistry reg;
    size_t n = reg.loadDirectory(dir);
    size_t socks = 0, hinges = 0, attach = 0, inst = 0, bad = 0;
    for (auto& e : reg.errors()) { std::printf("FAIL parse %s\n", e.c_str()); ++bad; }
    for (auto& kv : reg.allSockets()) {
        socks += kv.second.sockets.size(); hinges += kv.second.hinges.size();
        for (auto& s : kv.second.sockets) attach += s.kind == "attach";
        for (auto& e : validate(kv.second)) { std::printf("FAIL %s (%s)\n", e.c_str(), kv.second.path.c_str()); ++bad; }
    }
    for (auto& kv : reg.allVariants()) {
        inst += kv.second.instances.size();
        for (auto& e : validate(kv.second)) { std::printf("FAIL %s (%s)\n", e.c_str(), kv.second.path.c_str()); ++bad; }
    }
    std::printf("dir %s: %zu files, %zu socket assets, %zu sockets (%zu attach), %zu hinges, %zu variant assets, %zu instances, %zu problems\n",
                dir.c_str(), n, reg.allSockets().size(), socks, attach, hinges, reg.allVariants().size(), inst, bad);
    CHECK(n > 0); CHECK(bad == 0);
    if (auto* td = reg.sockets("Bld_Lab_TwinDoors")) {  // known staged asset: hinge open angles
        const Hinge* a = td->hingeFor("Bld_Lab_TwinDoors_DoorA");
        CHECK(a && std::fabs(a->openAngleDeg() + 90.0) < 1e-6);
        auto ws = reg.find("Bld_Lab_TwinDoors", "SOCKET_Hinge_DoorA", {{0, 0, 0}, kPlacementYawDeg});
        CHECK(ws && near(ws->locationCm, {0, 230, 0}, 1e-6));
    }
    if (auto* rp = reg.sockets("Prop_YTM_RecordPlayer")) {  // spin hinges
        const Hinge* sp = rp->hingeFor("Prop_YTM_Record_Whole");
        CHECK(sp && sp->motion == "spin" && sp->rpm && *sp->rpm == 78.0 && sp->openAngleDeg() == 0.0);
    }
    if (auto* owl = reg.sockets("Mob_Bird_Owl")) {  // skeletal sockets are bone-parented
        const Socket* t = owl->socket("SOCKET_Talon");
        CHECK(t && t->bone == "Leg_L" && owl->schema == "bb-skeletal-sockets/1");
    }
}

int main(int argc, char** argv) {
    unitTests();
    for (int i = 1; i < argc; ++i) dirTest(argv[i]);
    std::printf("%d passed, %d failed\n", g_pass, g_fail);
    return g_fail == 0 ? 0 : 1;
}
