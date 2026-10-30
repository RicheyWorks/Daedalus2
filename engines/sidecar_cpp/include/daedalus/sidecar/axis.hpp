// SPDX-License-Identifier: MIT
// Blender -> Unreal axis conversion, mirroring tools/blender/sockets_sidecar.py (the Python reference).
//   Blender: +Z up, front = -Y, metres.   Unreal: +X forward, +Y right, +Z up, centimetres, left-handed.
//   UE = 100 * (x_b, -y_b, z_b) = 100 * (gx, gz, gy) (glTF +Y up).  The Blender front (-Y) lands on UE +Y; placement faces
//   the asset forward with actor/component yaw -90 (kPlacementYawDeg).  SOCKET_ empties are pre-rotated at export so the
//   native Interchange socket equals the sidecar frame; the sidecar rotation is authoritative.
#pragma once
#include <array>

namespace daedalus::sidecar {

using Vec3 = std::array<double, 3>;
using Mat3 = std::array<std::array<double, 3>, 3>;  // m[row][col]; a UE frame has columns X, Y, Z
struct Rotator { double pitch = 0, yaw = 0, roll = 0; };  // UE FRotator, degrees

constexpr double kPlacementYawDeg = -90.0;  // turns Blender front (UE +Y) onto UE +X

Vec3 blenderToUe(const Vec3& metres);       // -> centimetres
Vec3 gltfToUe(const Vec3& metres);          // glTF +Y up -> centimetres
Vec3 blenderDirToUe(const Vec3& d);         // direction, unitless
Vec3 ueToBlender(const Vec3& cm);           // inverse of blenderToUe

Mat3 identity();
Mat3 mul(const Mat3& a, const Mat3& b);
Mat3 transpose(const Mat3& a);
Vec3 transform(const Mat3& m, const Vec3& v);
double maxAbsDiff(const Mat3& a, const Mat3& b);

Mat3 rotatorToMatrix(const Rotator& r);     // as FRotationMatrix
Rotator matrixToRotator(const Mat3& m);     // as FMatrix::Rotator, cleaned like the Python (+-180 -> 180)
Mat3 blenderEulerXyzToMatrix(const Vec3& deg);  // R = Rz * Ry * Rx (Blender XYZ euler)

// Socket pre-rotation (team convention UEB 48793/48794): Interchange gives native = N Rb N A for an empty with
// Blender rotation Rb; A = rotator [0, 180, -90]; N = diag(1, -1, 1).
const Mat3& interchangeOffset();            // A
Mat3 blenderEmptyMatrix(const Mat3& desiredUeFrame);  // Rb so native == desired
Mat3 predictNative(const Mat3& blenderRotation);

// A Blender-space rotation (e.g. a hinge's open euler) expressed in UE mesh space: N Rb N.
Rotator blenderEulerToUeRotator(const Vec3& deg);

// Attach-socket frame: +X along the Blender barrel/shaft, +Z toward the up hint (orthogonalised).
Mat3 attachFrame(const Vec3& barrelBlender, const Vec3& upBlender = {0, 0, 1});

// Placement: rotate a UE mesh-space vector by the -90 yaw used when placing Blender-built assets.
Vec3 applyPlacementYaw(const Vec3& ueMeshSpace);

bool rotatorsEquivalent(const Rotator& a, const Rotator& b, double tol = 1e-3);  // compares frames, not angles

}  // namespace daedalus::sidecar
