#include "../DaedalusLink/Source/DaedalusLink/Public/DaedalusExplorationTerrainCore.h"
#include <iostream>
#include <limits>
using namespace DaedalusExplorationTerrain;
#define CHECK(expr) do { if (!(expr)) { std::cerr << "Failed line " << __LINE__ << '\n'; return 1; } ++checks; } while (0)
int main()
{
    int checks=0;
    for (const auto realm : {Realm::Prairie, Realm::Ocean})
    {
        const Patch left=Build(realm,-256,0,64,4), right=Build(realm,0,0,64,4);
        CHECK(left.Vertices.size()==4225 && left.Indices.size()==24576);
        for (unsigned row=0; row<=64; ++row)
        {
            const auto& a=left.Vertices[row*65+64];
            const auto& b=right.Vertices[row*65];
            CHECK(a.X==b.X && a.Y==b.Y && a.Z==b.Z);
            const auto n=SurfaceNormal(realm,a.X,a.Y), m=SurfaceNormal(realm,b.X,b.Y);
            CHECK(n.X==m.X && n.Y==m.Y && n.Z==m.Z);
            CHECK(std::abs(n.X*n.X+n.Y*n.Y+n.Z*n.Z-1.0)<1.e-10 && n.Z>0);
        }
        for (auto index:left.Indices) CHECK(index<left.Vertices.size());
        for (const auto& v:left.Vertices) CHECK(std::isfinite(v.Z));
        for (std::size_t i=0;i<left.Indices.size();i+=3)
        {
            const auto& a=left.Vertices[left.Indices[i]];
            const auto& b=left.Vertices[left.Indices[i+1]];
            const auto& c=left.Vertices[left.Indices[i+2]];
            CHECK((b.X-a.X)*(c.Y-a.Y)-(b.Y-a.Y)*(c.X-a.X)>0);
        }
    }
    for (int x=-10000;x<=10000;x+=10)
    {
        CHECK(Height(Realm::Prairie,x,0)==0);
        CHECK(Height(Realm::Ocean,x,0)<-20);
    }
    CHECK(Build(Realm::Ocean,0,0,257,4).Vertices.empty());
    CHECK(std::isnan(Height(Realm::Prairie,std::numeric_limits<double>::infinity(),0)));
    CHECK(Build(Realm::Ocean,std::numeric_limits<double>::max(),0,256,
                std::numeric_limits<double>::max()).Vertices.empty());
    std::cout << "EXPLORATION_TERRAIN_PASS " << checks << " checks\n";
}
