# Prometheus Island beds: stream (water) + island song. Dark/soft: everything low-passed <= ~1.2 kHz, peaks -18 dBFS.
import numpy as np, wave, json
SR=44100
def lp(x,fc):
    a=np.exp(-2*np.pi*fc/SR); y=np.zeros_like(x); s=0.0
    for i in range(len(x)): s=a*s+(1-a)*x[i]; y[i]=s
    return y
def save(n,x):
    x=x/np.max(np.abs(x))*0.125; x=(np.clip(x,-1,1)*32767).astype(np.int16)
    w=wave.open(n,"wb"); w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(x.tobytes()); w.close()
rng=np.random.default_rng(15); T=24; t=np.arange(T*SR)/SR
n=rng.standard_normal(len(t)); b=lp(lp(lp(lp(n,500),500),600),600)
gurgle=sum(np.sin(2*np.pi*f*t+rng.random()*6)*(0.5+0.5*np.sin(2*np.pi*rng.uniform(.1,.4)*t)) for f in rng.uniform(160,420,6))*0.05
st=b+gurgle; fade=np.minimum(1,np.minimum(t,T-t)/1.5); save("SW_PI_Stream.wav",st*fade)
# island song: Turing-style walk over D minor pentatonic, low register, soft sine+2nd harmonic, light passing notes
scale=[0,3,5,7,10]; root=146.83/2; notes=[]; st_=0; state=0; out=np.zeros(len(t))
k=0; pos=0.0
while pos<T-2:
    state=(state*5+3)%7; step=[0,1,-1,2,-1,0,1][state]; st_=max(0,min(9,st_+step))
    deg=scale[st_%5]+12*(st_//5); f=root*2**(deg/12); dur=[1.5,1.0,0.75,1.5,2.0,1.0,0.5][state]
    amp=0.25 if dur<0.8 else 0.6   # passing notes stay light
    i0=int(pos*SR); L=int((dur+1.2)*SR); tt=np.arange(L)/SR
    env=np.minimum(tt/0.25,1)*np.exp(-tt/1.6); tone=(np.sin(2*np.pi*f*tt)+0.25*np.sin(4*np.pi*f*tt))*env*amp
    out[i0:i0+L]+=tone[:len(out)-i0]; notes.append(round(f,1)); pos+=dur
drone=0.15*np.sin(2*np.pi*root/2*t)*(0.7+0.3*np.sin(2*np.pi*0.05*t))
song=lp(out+drone,1100); save("SW_PI_Song.wav",song*fade)
json.dump(dict(notes=notes[:40],max_hz=max(notes)),open("audio_meta.json","w")); print("audio ok max note",max(notes))
