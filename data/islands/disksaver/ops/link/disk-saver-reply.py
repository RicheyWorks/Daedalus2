import json,sys
to,reply,req,f=sys.argv[1],sys.argv[2],sys.argv[3],sys.argv[4]
t=open(f,encoding='utf-8-sig').read().strip()
m={"to":to,"type":"note","body":{"text":t}}
if req: m["body"]["request_id"]=req
if reply: m["reply_to"]=int(reply)
open(r'C:\Users\730ri\projects\bot-team\link\outbox\disk-saver.jsonl','a',encoding='utf-8').write(json.dumps(m)+"\n")
print("posted to",to,"reply_to",reply,t[:50])
