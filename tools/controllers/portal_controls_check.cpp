// SPDX-License-Identifier: MIT
// Host-free check of DaedalusPortalControls.h (branch codex/portal-controller-intents-20261014, not yet on main):
//   g++ -std=c++20 -Wall -Wextra -I engines/unreal/DaedalusLink/Source/DaedalusLink/Public tools/controllers/portal_controls_check.cpp -o /tmp/pc && /tmp/pc
// East-confirm layout, alias hold/release, stick hysteresis 0.55/0.40/0.10, repeat swallowing, ReleaseAll, atomic remap refusal.
#include "DaedalusPortalControls.h"
#include <cstdio>
namespace PC = daedalus::portal_controls; using B = PC::Button;
static int fails = 0, n = 0;
#define CHECK(c, m) do { n++; if (!(c)) { fails++; std::printf("FAIL %s\n", m); } else std::printf("ok   %s\n", m); } while (0)
static bool has(const std::vector<PC::Edge>& e, B b, bool p) { for (auto& x : e) if (x.Intent == b && x.Pressed == p) return true; return false; }
int main() {
    std::string err; std::vector<PC::Edge> rel;
    PC::Translator T;
    CHECK(T.Replace(PC::Profile::Preset(PC::Layout::EastConfirm, PC::Labels::NintendoLabels), rel, err), "east-confirm profile accepted");
    CHECK(has(T.KeyDown("Gamepad_FaceButton_Right").Edges, B::A, true), "east face = confirm (A)");
    CHECK(has(T.KeyDown("Gamepad_FaceButton_Bottom").Edges, B::B, true), "south face = back (B)");
    T.KeyUp("Gamepad_FaceButton_Right"); T.KeyUp("Gamepad_FaceButton_Bottom");
    // aliases: d-pad up and W both held; releasing one keeps Up held
    CHECK(has(T.KeyDown("Gamepad_DPad_Up").Edges, B::Up, true), "d-pad up presses Up");
    CHECK(T.KeyDown("W").Edges.empty(), "second alias adds no edge");
    CHECK(T.KeyUp("Gamepad_DPad_Up").Edges.empty(), "releasing one alias keeps Up");
    CHECK(has(T.KeyUp("W").Edges, B::Up, false), "last alias releases Up");
    // stick hysteresis 0.55 / 0.40 / 0.10
    CHECK(T.Axis("Gamepad_LeftX", 0.5).Edges.empty(), "0.50 below press threshold");
    CHECK(has(T.Axis("Gamepad_LeftX", 0.6).Edges, B::Right, true), "0.60 presses Right");
    CHECK(T.Axis("Gamepad_LeftX", 0.45).Edges.empty(), "0.45 keeps Right (release is 0.40)");
    CHECK(T.Axis("Gamepad_LeftY", 0.5).Edges.empty(), "competing 0.50 does not steal");
    CHECK(has(T.Axis("Gamepad_LeftX", 0.3).Edges, B::Right, false), "0.30 releases Right");
    // repeats are swallowed; ReleaseAll clears
    T.KeyDown("Enter"); CHECK(T.KeyDown("Enter", true).Edges.empty(), "OS repeat swallowed");
    auto all = T.ReleaseAll(); CHECK(has(all, B::A, false), "ReleaseAll releases held confirm");
    // incomplete remap refused atomically
    PC::Profile P = PC::Profile::Preset();
    std::string e2; bool unb = true;
    for (auto k : {"Tab", "Gamepad_Special_Right"}) unb = P.Unbind(k, e2) && unb;
    CHECK(!unb, "removing every Menu binding is refused");
    std::printf("PORTAL-CONTROLS %d/%d\n", n - fails, n);
    return fails ? 1 : 0;
}
