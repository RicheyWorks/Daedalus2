f=r'C:\Users\730ri\projects\bot-team\BOARD\LESSONS-LEARNED-UNREAL.md'
t=open(f,'rb').read().decode('utf-8')
old='written and dry-run; not yet run in an editor turn'
new='ran in round 5 (00:59-01:01 PT): lit SceneCapture shot diskSaver_island_v5.png, temps removed, world lighting untouched; exposure tuned (fill 5e5, EV100 9)'
assert t.count(old)==1
t=t.replace(old,new); i=t.index(new); j=t.index('- Status: OPEN',i)
t=t[:j]+'- Status: FIXED'+t[j+len('- Status: OPEN'):]
open(f,'wb').write(t.encode('utf-8')); print('ok')
