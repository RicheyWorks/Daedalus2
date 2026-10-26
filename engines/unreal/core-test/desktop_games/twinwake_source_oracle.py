#!/usr/bin/env python3
"""Review-safe oracle: execute only latest Twinwake's bounded numeric frame statements.

No imports or complete game execution. No pygame, display, filesystem persistence,
controller device or event loop runs. Default checks a committed synthetic fixture.
"""
import argparse
import ast
import hashlib
from pathlib import Path
from types import SimpleNamespace

PIN = "f098754ca1d5171f34560eb1f444d1b2cfd42b90a81478c737e182d2e2957d23"
FIELDS = ("player_y", "ai_y", "ball_x", "ball_y", "ball_vx", "ball_vy", "player_score", "ai_score")

def generate(path):
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != PIN:
        raise RuntimeError("Canonical latest Twinwake source changed")
    lines = raw.decode("utf-8-sig").splitlines()
    first = next(i + 1 for i, s in enumerate(lines) if "# Player controls" in s)
    last = next(i + 1 for i, s in enumerate(lines) if s.strip() == "# Draw")
    tree = ast.parse(raw.decode("utf-8-sig"))
    loop = next(n for n in tree.body if isinstance(n, ast.While))
    nodes = [n for n in loop.body if first < n.lineno < last]
    for node in ast.walk(ast.Module(body=nodes, type_ignores=[])):
        if isinstance(node, (ast.Import, ast.ImportFrom, ast.While, ast.For, ast.With, ast.Try)):
            raise RuntimeError("Oracle fragment contains forbidden execution")
    code = compile(ast.Module(body=nodes, type_ignores=[]), "reviewed-pong-frame", "exec")
    cases = [
        ("neutral", (250,250,400,300,5,3,0,0),0,0,0),
        ("up", (250,250,400,300,5,3,0,0),1,0,0),
        ("down", (250,250,400,300,5,3,0,0),0,1,0),
        ("both", (250,250,400,300,5,3,0,0),1,1,0),
        ("stick", (250,250,400,300,5,3,0,0),0,0,0.75),
        ("deadzone", (250,250,400,300,5,3,0,0),0,0,0.2),
        ("ai_near_target", (250,250,400,301,5,3,0,0),0,0,0),
        ("player_scores", (200,250,799,50,5,3,6,2),0,0,0),
        ("computer_scores", (200,250,1,50,-5,-3,6,2),0,0,0),
        ("first_paddle_hit", (250,250,65,300,-5,3,0,0),0,0,0),
        ("first_wall_hit", (250,250,400,588,5,3,0,0),0,0,0),
    ]
    result = ["TWINWAKE 1", "# latest twinwake (1).py SHA256 " + PIN]
    for name, before, up, down, axis in cases:
        env = dict(zip(FIELDS, before))
        env.update(pygame=SimpleNamespace(K_UP=1,K_DOWN=2,key=SimpleNamespace(get_pressed=lambda: {1:bool(up),2:bool(down)})),
                   controller=SimpleNamespace(get_axis=lambda _: axis), __builtins__={"abs":abs,"max":max,"min":min})
        exec(code, env)
        result.append(" ".join(map(str, (name,*before,up,down,axis,*(env[n] for n in FIELDS)))))
    return "\n".join(result)+"\n"

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source",type=Path,required=True)
    p.add_argument("--output",type=Path,default=Path(__file__).with_name("twinwake_parity.txt"))
    p.add_argument("--write",action="store_true")
    args=p.parse_args(); data=generate(args.source)
    if args.write: args.output.write_text(data,encoding="utf-8",newline="\n")
    elif args.output.read_text(encoding="utf-8")!=data: raise RuntimeError("Twinwake source fixture mismatch")
    print("Twinwake source oracle: 11 reviewed numeric cases PASS")

if __name__=="__main__": main()
