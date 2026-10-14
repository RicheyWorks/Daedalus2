"""Owned shared humanoid body builder; equipment belongs to each realm generator."""
from pathlib import Path
exec(compile(Path(__file__).with_name('portal_common.py').read_text(),__file__,'exec'))

def humanoid_body(coat):
    box((0,0,1.22),(.46,.30,.47),coat,'spine',.025)
    box((0,0,.96),(.45,.32,.12),brass,'pelvis')
    ball((0,0,1.73),(.14,.13,.18),face,'head')
    for x in [-.05,.05]:box((x,-.13,1.77),(.026,.02,.022),ink,'head',0)
    for side,x in [('L',.21),('R',-.21)]:
        segment((x*.6,0,.94),(x*.6,0,.55),.085,coat,'thigh.'+side)
        segment((x*.6,0,.55),(x*.6,0,.15),.065,ink,'calf.'+side)
        box((x*.6,-.05,.12),(.16,.25,.22),ink,'foot.'+side)
        segment((x,0,1.44),(x*1.48,0,1.15),.09,coat,'arm.'+side)
        segment((x*1.48,0,1.15),(x*1.6,-.03,.93),.065,coat,'forearm.'+side)
        ball((x*1.6,-.03,.92),(.065,.065,.07),face,'forearm.'+side)
