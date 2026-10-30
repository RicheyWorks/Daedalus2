import json,sys,datetime
t=open(sys.argv[1],encoding='utf-8-sig').read().strip()
open(r'C:\Users\730ri\projects\bot-team\link\outbox\disk-saver.jsonl','a',encoding='utf-8').write(json.dumps({"to":"*","type":"note","body":{"text":t}})+"\n")
print("posted",t[:60])
