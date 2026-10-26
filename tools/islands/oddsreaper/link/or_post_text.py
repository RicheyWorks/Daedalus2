import json,sys,datetime
text=sys.argv[1]
assert text.strip()
rec={"from":"oddsreaper","to":"*","type":"note","ts":datetime.datetime.now().astimezone().isoformat(timespec="seconds"),"body":{"text":text}}
with open(r"C:\Users\730ri\projects\bot-team\link\outbox\oddsreaper.jsonl","a",encoding="utf-8") as f: f.write(json.dumps(rec,ensure_ascii=False)+"\n")
print("posted")
