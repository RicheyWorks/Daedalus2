#pragma once
#include <cmath>
#include <cstdint>
#include <vector>
#include <limits>

// Metres, world coordinates. Pure geometry; native collision/streaming is separate.
namespace DaedalusExplorationTerrain
{
enum class Realm { Prairie, Ocean };
struct Vertex { double X, Y, Z; };
struct Patch { std::vector<Vertex> Vertices; std::vector<std::uint32_t> Indices; };
inline double Height(Realm realm, double x, double y)
{
    if (!std::isfinite(x) || !std::isfinite(y))
        return std::numeric_limits<double>::quiet_NaN();
    const double hills = 3.0 * std::sin(x / 140.0) * std::cos(y / 180.0)
                       + 0.6 * std::sin((x + y) / 37.0);
    if (realm == Realm::Ocean)
        return -45.0 + 18.0 * std::sin(x / 360.0) * std::cos(y / 420.0)
                     + 2.0 * std::sin((x + y) / 85.0);
    // Long open range with a smooth, flat east-west travel corridor.
    const double t = std::fmin(1.0, std::fmax(0.0, (std::abs(y) - 8.0) / 24.0));
    return hills * t * t * (3.0 - 2.0 * t);
}
inline Patch Build(Realm realm, double originX, double originY,
                   unsigned cells, double spacing)
{
    if (cells == 0 || cells > 256 || !std::isfinite(spacing) || spacing <= 0.0
        || !std::isfinite(originX) || !std::isfinite(originY)
        || !std::isfinite(originX + cells * spacing)
        || !std::isfinite(originY + cells * spacing))
        return {};
    Patch result;
    const unsigned stride = cells + 1;
    result.Vertices.reserve(static_cast<std::size_t>(stride) * stride);
    result.Indices.reserve(static_cast<std::size_t>(cells) * cells * 6);
    for (unsigned row = 0; row <= cells; ++row)
        for (unsigned col = 0; col <= cells; ++col)
        {
            const double x = originX + col * spacing, y = originY + row * spacing;
            result.Vertices.push_back({x, y, Height(realm, x, y)});
        }
    for (unsigned row = 0; row < cells; ++row)
        for (unsigned col = 0; col < cells; ++col)
        {
            const std::uint32_t a = row * stride + col, b = a + 1;
            const std::uint32_t c = a + stride, d = c + 1;
            result.Indices.insert(result.Indices.end(), {a,b,c,b,d,c});
        }
    return result;
}
inline Vertex SurfaceNormal(Realm realm, double x, double y)
{
    // World-coordinate derivative: shared patch edges have identical normals.
    constexpr double delta = 0.01;
    const double dx = (Height(realm,x+delta,y)-Height(realm,x-delta,y))/(2.0*delta);
    const double dy = (Height(realm,x,y+delta)-Height(realm,x,y-delta))/(2.0*delta);
    const double length = std::sqrt(dx*dx+dy*dy+1.0);
    return {-dx/length,-dy/length,1.0/length};
}
}
