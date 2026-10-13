# Gray-Scott terrain for Prometheus Island, seeded from a token id. Writes heightmap.npy + island.json
import numpy as np, json, sys
SEED=int(sys.argv[1]) if len(sys.argv)>1 else 15
F,k=0.0545,0.062   # Coral regime, inside the stable F/k ranges
N=128; rng=np.random.default_rng(SEED)
U=np.ones((N,N)); V=np.zeros((N,N))
for _ in range(12):
    x,y=rng.integers(10,N-10,2); U[x-4:x+4,y-4:y+4]=0.5; V[x-4:x+4,y-4:y+4]=0.25
V+=rng.random((N,N))*0.02
L=lambda Z: np.roll(Z,1,0)+np.roll(Z,-1,0)+np.roll(Z,1,1)+np.roll(Z,-1,1)-4*Z
for _ in range(6000):
    uvv=U*V*V; U+=0.16*L(U)-uvv+F*(1-U); V+=0.08*L(V)+uvv-(F+k)*V
yy,xx=np.mgrid[-1:1:N*1j,-1:1:N*1j]; r=np.sqrt(xx**2+yy**2)
dome=np.clip(1-r**2,0,1)**0.7
H=dome*(0.7+0.3*V/max(V.max(),1e-6))
# carve the stream valley: spring near peak (NE) down to SW shore
for t in np.linspace(0,1,400):
    cx=int(N*(0.62-0.4*t)); cy=int(N*(0.40+0.32*t+0.06*np.sin(t*9)))
    for dx in range(-3,4):
        for dy in range(-3,4):
            if 0<=cx+dx<N and 0<=cy+dy<N: H[cx+dx,cy+dy]*=0.86+0.02*(abs(dx)+abs(dy))
np.save("heightmap.npy",H.astype(np.float32))
json.dump(dict(seed=SEED,F=F,k=k,N=N,size_m=480,peak_m=38),open("island.json","w"))
print("terrain ok max=%.3f land=%.2f"%(H.max(),float((H>0.05).mean())))
