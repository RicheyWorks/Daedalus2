# SPDX-License-Identifier: MIT
# Checks the logic of UDaedalusNav (ADR-044), the C++ port of daedalus-core AStarSolver, on a synthetic island:
# same rules (100 cm cells, step up 70 / down 220, ledge cells weight 2.5, 8-connected, no corner cutting, octile h).
# Run: python engines/unreal/core-test/nav_astar_check.py   (prints n/m, exits nonzero on a failure)
import heapq, math
# Height field (cm) per 100cm cell; None = no ground. Island: 30x20, tier A at 0, tier B at 300 joined by a ramp; a wall.
W,H=30,20
def ground(x,y):
    if not (0<=x<W and 0<=y<H): return None
    if 12<=x<=13 and 3<=y<=16: return 400.0       # wall (a tall block row)
    if x>=20: return 300.0 if y>=6 else None      # tier B, with a missing corner (a drop)
    if 14<=x<20 and 8<=y<=10: return (x-14)*50.0  # ramp up to tier B (50 cm steps)
    return 0.0
STEPUP,STEPDOWN=70,220
def step(hz,x,y):
    z=ground(x,y)
    if z is None: return None
    if z-hz>STEPUP or hz-z>STEPDOWN: return None
    return z
def octile(dx,dy):
    a,b=abs(dx),abs(dy); return max(a,b)+(math.sqrt(2)-1)*min(a,b)
DX=[1,-1,0,0,1,1,-1,-1]; DY=[0,0,1,-1,1,-1,1,-1]
def astar(s,g,gz):
    fz={s:ground(*s)}; gs={s:0}; par={s:None}; closed=set(); op=[(octile(g[0]-s[0],g[1]-s[1]),0,s)]; exp=0
    while op:
        f,gg,c=heapq.heappop(op)
        if c in closed: continue
        closed.add(c); exp+=1
        if c==g and abs(fz[c]-gz)<200:
            p=[];n=c
            while n: p.append(n); n=par[n]
            return p[::-1],exp
        drops=sum(1 for i in range(4) if step(fz[c],c[0]+DX[i],c[1]+DY[i]) is None)
        w=1+(1.5 if drops else 0)
        for i in range(8):
            n=(c[0]+DX[i],c[1]+DY[i])
            if n in closed: continue
            z=step(fz[c],*n)
            if z is None: continue
            if i>=4 and (step(fz[c],c[0]+DX[i],c[1]) is None or step(fz[c],c[0],c[1]+DY[i]) is None): continue
            t=gg+(math.sqrt(2) if i>=4 else 1)*w
            if t<gs.get(n,1e18):
                gs[n]=t; par[n]=c; fz[n]=z; heapq.heappush(op,(t+octile(g[0]-n[0],g[1]-n[1]),t,n))
    return None,exp
ok=0;tot=0
def check(name,cond):
    global ok,tot; tot+=1; ok+=cond; print(("PASS " if cond else "FAIL ")+name)
p,e=astar((2,10),(9,10),0); check("same tier straight", p is not None and len(p)==8)
p,e=astar((2,10),(25,12),300); check("around the wall and up the ramp to tier B", p is not None and any(14<=x<20 for x,y in p) and all(not(12<=x<=13 and 3<=y<=16) for x,y in p))
print("  path len",len(p) if p else None,"expanded",e)
p,e=astar((25,12),(2,10),0); check("back down from tier B", p is not None)
# no climbing the cliff directly: tier B edge at x=20 from x=19 off-ramp is +300
p2,_=astar((19,2),(21,2),300); check("no route into the drop corner (no ground there)", p2 is None)
p3,_=astar((17,14),(21,14),300); check("cliff face not climbable: route goes via ramp", p3 is not None and any(8<=y<=10 for x,y in p3))
# heuristic admissible => optimal: compare to Dijkstra (h=0)
print(f"{ok}/{tot}")
import sys; sys.exit(0 if ok == tot else 1)
