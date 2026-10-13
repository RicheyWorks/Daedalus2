# Livestock calls from coat genome hash: soft, dark (lowpassed <=900 Hz, peak -18 dBFS, slow attack)
import numpy as np, wave, json, sys
SR=44100
M=json.load(open(sys.argv[1]))
def lp(x,fc,n=3):
    a=np.exp(-2*np.pi*fc/SR)
    for _ in range(n):
        y=np.empty_like(x); s=0.0
        for i in range(len(x)): s=a*s+(1-a)*x[i]; y[i]=s
        x=y
    return x
out=[]
for c in M:
    import hashlib; h=bytes.fromhex(c["hash"][2:]) if "hash" in c else hashlib.sha256(json.dumps(c,sort_keys=True).encode()).digest(); c.setdefault("kind","stripes" if "stripes" in c["name"] else "spots"); f0=70+h[0]%140; n=2+h[1]%3; gap=0.25+h[2]/255*0.5; T=6.0
    t=np.arange(int(T*SR))/SR; x=np.zeros_like(t); pos=0.4
    for k in range(n):
        d=(0.18+h[3+k]/255*0.25) if c["kind"]=="spots" else (0.5+h[3+k]/255*0.6)
        i0=int(pos*SR); L=int(d*SR); tt=np.arange(L)/SR; f=f0*(1+0.04*k)
        glide=f*(1-0.15*tt/d) if c["kind"]=="stripes" else f
        ph=2*np.pi*np.cumsum(glide)/SR; env=np.sin(np.pi*tt/d)**2
        tone=(np.sin(ph)+0.3*np.sin(2*ph)+0.1*np.sin(3*ph))*env
        x[i0:i0+L]+=tone[:len(x)-i0]; pos+=d+gap
    x=lp(x+0.02*np.random.default_rng(h[5]).standard_normal(len(x)),600,4)
    x=x/np.max(np.abs(x))*0.125; nm="SW_Call_PI_"+c["name"][7:]
    w=wave.open("calls/"+nm+".wav","wb"); w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((x*32767).astype(np.int16).tobytes()); w.close()
    X=np.abs(np.fft.rfft(x)); fr=np.fft.rfftfreq(len(x),1/SR); out.append((nm,int(f0),round(float(X[fr>2000].sum()/X.sum()),4)))
print(out)
