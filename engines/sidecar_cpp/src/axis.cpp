// SPDX-License-Identifier: MIT
#include "daedalus/sidecar/axis.hpp"
#include <algorithm>
#include <cmath>

namespace daedalus::sidecar {
namespace {
constexpr double kPi = 3.14159265358979323846;
double rad(double d) { return d * kPi / 180.0; }
double deg(double r) { return r * 180.0 / kPi; }
double clean(double a) {
    a = std::round(a * 1e4) / 1e4 + 0.0;
    if (std::fabs(std::fabs(a) - 180.0) < 1e-3) a = 180.0;
    return a;
}
Mat3 fromColumns(const Vec3& x, const Vec3& y, const Vec3& z) {
    return {{{x[0], y[0], z[0]}, {x[1], y[1], z[1]}, {x[2], y[2], z[2]}}};
}
Vec3 col(const Mat3& m, int c) { return {m[0][c], m[1][c], m[2][c]}; }
Vec3 cross(const Vec3& a, const Vec3& b) { return {a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]}; }
double dot(const Vec3& a, const Vec3& b) { return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]; }
Vec3 unit(const Vec3& v) { double n = std::sqrt(dot(v, v)); return {v[0] / n, v[1] / n, v[2] / n}; }
const Mat3 kN = {{{1, 0, 0}, {0, -1, 0}, {0, 0, 1}}};
}  // namespace

Vec3 blenderToUe(const Vec3& m) { return {m[0] * 100.0, -m[1] * 100.0, m[2] * 100.0}; }
Vec3 gltfToUe(const Vec3& g) { return {g[0] * 100.0, g[2] * 100.0, g[1] * 100.0}; }
Vec3 blenderDirToUe(const Vec3& d) { return {d[0], -d[1], d[2]}; }
Vec3 ueToBlender(const Vec3& c) { return {c[0] / 100.0, -c[1] / 100.0, c[2] / 100.0}; }

Mat3 identity() { return {{{1, 0, 0}, {0, 1, 0}, {0, 0, 1}}}; }
Mat3 mul(const Mat3& a, const Mat3& b) {
    Mat3 r{};
    for (int i = 0; i < 3; ++i) for (int j = 0; j < 3; ++j) { double s = 0; for (int k = 0; k < 3; ++k) s += a[i][k] * b[k][j]; r[i][j] = s; }
    return r;
}
Mat3 transpose(const Mat3& a) { Mat3 r{}; for (int i = 0; i < 3; ++i) for (int j = 0; j < 3; ++j) r[i][j] = a[j][i]; return r; }
Vec3 transform(const Mat3& m, const Vec3& v) { return {dot({m[0][0], m[0][1], m[0][2]}, v), dot({m[1][0], m[1][1], m[1][2]}, v), dot({m[2][0], m[2][1], m[2][2]}, v)}; }
double maxAbsDiff(const Mat3& a, const Mat3& b) {
    double d = 0; for (int i = 0; i < 3; ++i) for (int j = 0; j < 3; ++j) d = std::max(d, std::fabs(a[i][j] - b[i][j])); return d;
}

Mat3 rotatorToMatrix(const Rotator& r) {
    double p = rad(r.pitch), y = rad(r.yaw), ro = rad(r.roll);
    double SP = std::sin(p), CP = std::cos(p), SY = std::sin(y), CY = std::cos(y), SR = std::sin(ro), CR = std::cos(ro);
    Vec3 X{CP * CY, CP * SY, SP};
    Vec3 Y{SR * SP * CY - CR * SY, SR * SP * SY + CR * CY, -SR * CP};
    Vec3 Z{-(CR * SP * CY + SR * SY), CY * SR - CR * SP * SY, CR * CP};
    return fromColumns(X, Y, Z);
}

Rotator matrixToRotator(const Mat3& m) {
    Vec3 X = col(m, 0), Y = col(m, 1), Z = col(m, 2);
    double pitch = deg(std::atan2(X[2], std::hypot(X[0], X[1])));
    double yaw = deg(std::atan2(X[1], X[0]));
    Vec3 syY = col(rotatorToMatrix({pitch, yaw, 0.0}), 1);
    double roll = deg(std::atan2(dot(Z, syY), dot(Y, syY)));
    return {clean(pitch), clean(yaw), clean(roll)};
}

Mat3 blenderEulerXyzToMatrix(const Vec3& d) {
    double x = rad(d[0]), y = rad(d[1]), z = rad(d[2]);
    Mat3 Rx = {{{1, 0, 0}, {0, std::cos(x), -std::sin(x)}, {0, std::sin(x), std::cos(x)}}};
    Mat3 Ry = {{{std::cos(y), 0, std::sin(y)}, {0, 1, 0}, {-std::sin(y), 0, std::cos(y)}}};
    Mat3 Rz = {{{std::cos(z), -std::sin(z), 0}, {std::sin(z), std::cos(z), 0}, {0, 0, 1}}};
    return mul(mul(Rz, Ry), Rx);
}

const Mat3& interchangeOffset() { static const Mat3 A = rotatorToMatrix({0, 180, -90}); return A; }
Mat3 blenderEmptyMatrix(const Mat3& d) { return mul(mul(mul(kN, d), transpose(interchangeOffset())), kN); }
Mat3 predictNative(const Mat3& rb) { return mul(mul(mul(kN, rb), kN), interchangeOffset()); }
Rotator blenderEulerToUeRotator(const Vec3& d) { return matrixToRotator(mul(mul(kN, blenderEulerXyzToMatrix(d)), kN)); }

Mat3 attachFrame(const Vec3& barrel, const Vec3& up) {
    Vec3 X = unit(blenderDirToUe(barrel)), U = blenderDirToUe(up);
    double d = dot(U, X);
    Vec3 Z = unit({U[0] - d * X[0], U[1] - d * X[1], U[2] - d * X[2]});
    return fromColumns(X, cross(Z, X), Z);
}

Vec3 applyPlacementYaw(const Vec3& v) { return transform(rotatorToMatrix({0, kPlacementYawDeg, 0}), v); }

bool rotatorsEquivalent(const Rotator& a, const Rotator& b, double tol) {
    return maxAbsDiff(rotatorToMatrix(a), rotatorToMatrix(b)) <= tol;
}

}  // namespace daedalus::sidecar
