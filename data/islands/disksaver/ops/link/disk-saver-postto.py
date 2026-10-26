import json,sys
to=sys.argv[1]; t=open(sys.argv[2],encoding='utf-8-sig').read().strip()
open(r'C:\Users\730ri\projects\bot-team\link\outbox\disk-saver.jsonl','a',encoding='utf-8').write(json.dumps({"to":to,"type":"note","body":{"text":t}})+"\n")
print("posted to",to,t[:60])
