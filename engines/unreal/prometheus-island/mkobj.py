# heightmap.npy -> terrain OBJ (meters; placed at scale 100 in UE)
import numpy as np
H=np.load("heightmap.npy"); N=H.shape[0]; S=480.0; P=38.0
with open("fbx/SM_PrometheusIsland_Terrain.obj","w") as f:
    for i in range(N):
        for j in range(N):
            h=H[i,j]; z=h*P if h>0.05 else -12.0
            f.write("v %.3f %.3f %.3f\n"%((j/(N-1)-0.5)*S,(i/(N-1)-0.5)*S,z))
    for i in range(N-1):
        for j in range(N-1):
            a=i*N+j+1; f.write("f %d %d %d\nf %d %d %d\n"%(a,a+N,a+1,a+1,a+N,a+N+1))
print("obj ok")
