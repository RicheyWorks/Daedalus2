"""title/end cards for 'the recording isle' (richeyworks style: black, white, lowercase, plex mono, dragon stamp)."""
from PIL import Image, ImageDraw, ImageFont
import os, sys
B="/workspace/youtube/branding"; OUT=os.path.join(os.path.dirname(os.path.abspath(__file__)),"cards"); os.makedirs(OUT,exist_ok=True)
W,H=1920,1080; BG=(11,11,11); FG=(255,255,255); DIM=(138,138,138)
def font(sz,b=False): return ImageFont.truetype(f"{B}/plex-{'Bold' if b else 'Regular'}.ttf",sz)
dragon=Image.open(f"{B}/dragon_white_1200.png").convert("RGBA")
def card(name,lines,stamp=360,sub=None):
    im=Image.new("RGB",(W,H),BG); d=ImageDraw.Draw(im)
    if stamp:
        s=dragon.resize((stamp,int(stamp*dragon.height/dragon.width))); im.paste(s,((W-s.width)//2,H//2-s.height-40),s)
    y=H//2+(20 if stamp else -60)
    for i,t in enumerate(lines):
        f=font(64 if i==0 else 40, i==0); w=d.textlength(t,font=f); d.text(((W-w)/2,y),t,font=f,fill=FG if i==0 else DIM); y+=90 if i==0 else 60
    if sub: f=font(28); w=d.textlength(sub,font=f); d.text(((W-w)/2,H-90),sub,font=f,fill=DIM)
    im.save(os.path.join(OUT,name+".png"))
# overlay lower-third captions (transparent PNGs)
def caption(name,text):
    im=Image.new("RGBA",(W,H),(0,0,0,0)); d=ImageDraw.Draw(im); f=font(44)
    d.rectangle([80,H-170,80+d.textlength(text,font=f)+60,H-90],fill=(11,11,11,170)); d.text((110,H-160),text,font=f,fill=FG)
    s=dragon.resize((90,int(90*dragon.height/dragon.width))); im.paste(s,(W-150,50),s)
    im.save(os.path.join(OUT,"cap_"+name+".png"))
card("title",["richeyworks","the recording isle"])
card("end",["daedalus","richeyworks"],stamp=260,sub="music: reaction / diffusion / song (seed song)")
for k,t in {"island":"one planet. one rock. ten thousand pieces.","youngmeadow":"young meadow","pinestand":"pine stand",
            "oldgrowthoak":"old-growth oak","willowriverbank":"willow riverbank","spring":"drink before you build.","brambles":"bramble scrub",
            "shrine":"every seed grows a song.","garden":"rise. fall. come home.","farm":"feed. water. wait.","dock":"the arks carried what they could."}.items(): caption(k,t)
print("cards ok", sorted(os.listdir(OUT)))
# youtube thumbnail 1280x720: real frame if given (THUMB_BG=path), else banner turing crop; darkened, big lowercase title, stamp
def thumb(bg=None):
    src=Image.open(bg).convert("RGB") if bg else Image.open(f"{B}/banner_2560x1440.png").convert("RGB").crop((0,0,880,495))  # pattern-only corner
    r=max(1280/src.width,720/src.height); src=src.resize((int(src.width*r)+1,int(src.height*r)+1))
    l=(src.width-1280)//2; t=(src.height-720)//2; im=src.crop((l,t,l+1280,t+720))
    im=Image.blend(im,Image.new("RGB",im.size,BG),0.55); d=ImageDraw.Draw(im)
    f=font(112,True); y=720-300
    for line in ("the recording","isle"): d.text((70,y),line,font=f,fill=FG); y+=120
    d.text((74,90),"daedalus",font=font(40),fill=DIM)
    s=dragon.resize((200,int(200*dragon.height/dragon.width))); im.paste(s,(1280-250,60),s)
    im.save(os.path.join(OUT,"thumb.png"))
thumb(os.environ.get("THUMB_BG")); print("thumb ok")
