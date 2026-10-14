#!/usr/bin/env python3
"""Pinned-source oracle for Desktop Dungeon, Pac-Man and Zelda numeric rules.

Only reviewed AST-selected class methods and is_wall execute with controlled
Rect, input and random stubs. No source imports, pygame, display, device access,
main/event loops or complete game scripts execute. Sources remain read-only.
"""
import argparse
import ast
import hashlib
import math
from pathlib import Path
from types import SimpleNamespace

PINS = {
    "dungeon": "cbf19aa131cfe9815f36ef4812638cf0992141666d4eb3a0fce0b92e662e99a4",
    "pacman": "6cad8d138888c7a18d80e0e034546a49e57618610ac3e5dcce9886a7358ad8ed",
    "zelda": "713f6de7c27a92d65fdedd77a6c15a7e80a964d098d5ba209dbf32e648cc9bdd",
}
KEY_NAMES = ("K_LEFT", "K_a", "K_RIGHT", "K_d", "K_UP", "K_w", "K_DOWN", "K_s")
PG = SimpleNamespace(**{name: i for i, name in enumerate(KEY_NAMES)})


class Rect:
    def __init__(self, x, y, w, h):
        self.x, self.y, self.w, self.h = map(int, (x, y, w, h))

    def colliderect(self, other):
        return self.x < other.x+other.w and self.x+self.w > other.x and self.y < other.y+other.h and self.y+self.h > other.y


PG.Rect = Rect


class FixedRandom:
    """Predictable source choices; these cases do not assert seeded RNG parity."""
    def __init__(self, samples=(0.9, 0.9)):
        self.samples = iter(samples)

    def random(self):
        return next(self.samples, 0.9)

    def randint(self, low, high):
        return (low+high)//2

    def choice(self, seq):
        return seq[0]

    def shuffle(self, seq):
        # The native injected-choice tests use this same exact order.
        seq[:] = [(1, 0), (-1, 0), (0, 1), (0, -1)]


def reviewed_env(path, label, class_methods, functions=()):
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != PINS[label]:
        raise RuntimeError(f"Canonical {label} source hash changed; review before regenerating")
    tree = ast.parse(raw.decode("utf-8-sig"))
    env = {"pygame": PG, "math": math, "random": FixedRandom(),
           "get_axis": lambda _: 0.0, "AXIS_LEFT_X": 0, "AXIS_LEFT_Y": 1,
           "__builtins__": {"abs": abs, "max": max, "min": min, "int": int, "range": range, "len": len}}
    selected = []
    for node in tree.body:
        if isinstance(node, ast.Assign):
            try:
                value = ast.literal_eval(node.value)
            except (ValueError, TypeError):
                continue
            for target in node.targets:
                if isinstance(target, ast.Name):
                    env[target.id] = value
        elif isinstance(node, ast.FunctionDef) and node.name in functions:
            selected.append(node)
        elif isinstance(node, ast.ClassDef) and node.name in class_methods:
            methods = [n for n in node.body if isinstance(n, ast.FunctionDef) and n.name in class_methods[node.name]]
            if {m.name for m in methods} != set(class_methods[node.name]):
                raise RuntimeError(f"Missing reviewed methods for {node.name}")
            selected.append(ast.ClassDef(name=node.name, bases=[], keywords=[], body=methods, decorator_list=[]))
    # Draw methods, top-level init and all source event loops are absent.
    module = ast.fix_missing_locations(ast.Module(body=selected, type_ignores=[]))
    for node in ast.walk(module):
        if isinstance(node, (ast.Import, ast.ImportFrom, ast.While, ast.With, ast.Try, ast.Global)):
            raise RuntimeError("Forbidden execution in reviewed numeric fragment")
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in ("open", "exec", "eval", "compile", "__import__"):
            raise RuntimeError("Forbidden callable in source fragment")
    # Class creation itself needs a controlled __build_class__, not general imports.
    import builtins
    env["__builtins__"]["__build_class__"] = builtins.__build_class__
    env["__name__"] = "reviewed_maze_rules"
    exec(compile(module, f"reviewed-{label}-rules", "exec"), env)
    return env


def keys(left=0, right=0, up=0, down=0):
    return {PG.K_LEFT: bool(left), PG.K_a: False, PG.K_RIGHT: bool(right), PG.K_d: False,
            PG.K_UP: bool(up), PG.K_w: False, PG.K_DOWN: bool(down), PG.K_s: False}


def row(*values):
    return " ".join(str(int(v)) if isinstance(v, bool) else str(v) for v in values)


def generate(desktop):
    d = reviewed_env(desktop/"PythonGames"/"main.py", "dungeon", {}, ("is_wall",))
    p = reviewed_env(desktop/"pacman.py", "pacman", {
        "PacMan": ("__init__", "update", "collides", "get_rect"),
        "Ghost": ("__init__", "update", "collides", "get_rect"),
    })
    z = reviewed_env(desktop/"zelda.py", "zelda", {
        "Link": ("__init__", "update", "attack", "get_rect", "get_attack_rect"),
        "Enemy": ("__init__", "update", "get_rect"),
        "Projectile": ("__init__", "update", "get_rect"),
        "Collectible": ("__init__", "update", "get_rect"),
    })
    lines = ["MAZE 1", *("# "+name+" SHA256 "+pin for name, pin in PINS.items())]
    for i, text in enumerate(d["MAP"]):
        lines.append(row("DUNGEON_ROW", i, text))
    for y in range(len(d["MAP"])):
        for x in range(len(d["MAP"][y])):
            lines.append(row("DUNGEON_WALL", x*40, y*40, d["is_wall"](x*40, y*40)))
    for i, text in enumerate(p["MAZE"]):
        lines.append(row("PAC_ROW", i, text))
    p["walls"] = [Rect(c*20, r*20, 20, 20) for r, text in enumerate(p["MAZE"]) for c, ch in enumerate(text) if ch == "#"]
    player_cases = [
        ("source_stuck_spawn", 280,460,0,0,0,0,0,0,1,0,0,0,0,5),
        ("right",290,470,0,0,0,0,0,0,1,0,0,0,0,6),
        ("left",290,470,0,0,0,0,18,1,0,0,0,0,0,6),
        ("buffer_wall_turn",290,470,1,0,0,0,0,0,0,1,0,0,0,6),
        ("precedence",290,470,0,0,0,0,0,1,1,1,1,0,0,4),
        ("stick_right",290,470,0,0,0,0,0,0,0,0,0,0.9,0.1,6),
        ("stick_equal_down",270,110,0,0,0,0,0,0,0,0,0,0.8,0.8,4),
        ("deadzone",290,470,0,0,0,0,0,0,0,0,0,0.3,0,4),
        ("wall_left",30,30,-1,0,-1,0,0,1,0,0,0,0,0,12),
        ("wall_up",30,30,0,-1,0,-1,0,0,0,1,0,0,0,12),
    ]
    for name,x,y,dx,dy,nx,ny,mouth,left,right,up,down,ax,ay,steps in player_cases:
        hero=p["PacMan"](); hero.x=x; hero.y=y; hero.dir=(dx,dy); hero.next_dir=(nx,ny); hero.mouth=mouth
        p["get_axis"] = lambda a, vx=ax, vy=ay: vx if a==0 else vy
        for _ in range(steps):
            hero.update(keys(left,right,up,down))
        lines.append(row("PAC_PLAYER",name,x,y,dx,dy,nx,ny,mouth,left,right,up,down,ax,ay,steps,
                         hero.x,hero.y,*hero.dir,*hero.next_dir,hero.mouth))
    # Collision fixtures include pygame's fractional-coordinate truncation.
    for x,y in [(280,460),(290,470),(30,30),(22.5,30),(22,30),(21.9,30),(190,290),(190,270),(250,290),(10,290),(550,290)]:
        hero=p["PacMan"](); lines.append(row("PAC_COLLISION",x,y,hero.collides(x,y)))
    ghost_cases=[
        ("horizontal_chase",290,470,1,0,1,0,0,390,470,0.9,0.1),
        ("vertical_chase",30,110,1,0,1,0,0,30,210,0.9,0.1),
        ("no_chase",290,470,-1,0,1,0,0,390,470,0.9,0.9),
        ("frightened",290,470,-1,0,1,1,300,390,470,0.9,0.1),
        ("expires_and_chases",290,470,-1,0,1,1,1,390,470,0.9,0.1),
        ("turn_sample",290,470,-1,0,1,0,0,390,470,0.01,0.9),
        ("blocked_turn",30,30,-1,0,1,0,0,390,470,0.9,0.9),
        ("dead_frozen",290,470,-1,0,0,1,100,390,470,0.01,0.1),
    ]
    for name,x,y,dx,dy,alive,frightened,timer,px,py,turn,chase in ghost_cases:
        ghost=p["Ghost"](x,y,(255,0,0),"Blinky"); ghost.dir=(dx,dy); ghost.alive=bool(alive); ghost.frightened=bool(frightened); ghost.frightened_timer=timer
        hero=p["PacMan"](); hero.x=px; hero.y=py; p["random"]=FixedRandom((turn,chase))
        ghost.update(hero,[])
        lines.append(row("PAC_GHOST",name,x,y,dx,dy,alive,frightened,timer,px,py,turn,chase,
                         ghost.x,ghost.y,*ghost.dir,ghost.alive,ghost.frightened,ghost.frightened_timer))
    face_names=("right","left","up","down")
    link_cases=[
        ("neutral",400,450,3,0,0,0,0,0,0,0,0,0,0,1),
        ("right",400,450,3,0,0,0,0,1,0,0,0,0,0,12),
        ("diagonal",400,450,3,0,0,0,0,1,1,0,0,0,0,12),
        ("both_precedence",400,450,3,0,0,0,1,1,1,1,0,0,0,4),
        ("stick",400,450,3,0,0,0,0,0,0,0,0.4,0.8,0,10),
        ("tiny_stick",400,450,3,0,0,0,0,0,0,0,0.15,0.15,0,5),
        ("threshold",400,450,3,0,0,0,0,0,0,0,0.2,0.2,0,5),
        ("x_deadzone",400,450,3,0,0,0,0,0,0,0,0.15,0.8,0,3),
        ("bounds",778,578,3,0,0,0,0,1,0,1,0,0,0,10),
        ("timers",400,450,3,18,45,1,0,0,0,0,0,0,0,18),
    ]
    for name,x,y,face,at,inv,attacking,left,right,up,down,ax,ay,unused,steps in link_cases:
        hero=z["Link"](); hero.x=x; hero.y=y; hero.facing=face_names[face]; hero.attack_timer=at; hero.invincible=inv; hero.attacking=bool(attacking)
        z["get_axis"] = lambda a,vx=ax,vy=ay: (vx if abs(vx)>0.15 else 0) if a==0 else (vy if abs(vy)>0.15 else 0)
        for _ in range(steps): hero.update(keys(left,right,up,down))
        lines.append(row("ZELDA_PLAYER",name,x,y,face,at,inv,attacking,left,right,up,down,ax,ay,steps,
                         hero.x,hero.y,face_names.index(hero.facing),hero.attack_timer,hero.invincible,hero.attacking))
    for face in range(4):
        for at in (0,1,18):
            hero=z["Link"](); hero.x=400.75; hero.y=450.75; hero.facing=face_names[face]; hero.attack_timer=at
            success=hero.attack(); r=hero.get_attack_rect()
            lines.append(row("ZELDA_ATTACK",face,at,hero.x,hero.y,success,hero.attack_timer,hero.attacking,r.x,r.y,r.w,r.h))
    enemy_cases=[("moblin_far","moblin",550,200,400,450), ("moblin_zero","moblin",400,450,400,450),
                 ("moblin_bounds","moblin",29,29,20,20), ("armos_far","armos",300,380,400,450),
                 ("armos_near","armos",300,380,340,400), ("armos_at_threshold","armos",300,380,420,380),
                 ("armos_zero","armos",400,450,400,450), ("octorok_still","octorok",200,150,400,450)]
    for name,kind,x,y,px,py in enemy_cases:
        z["random"]=FixedRandom((0.9,)); enemy=z["Enemy"](x,y,kind); enemy.hit_flash=12; enemy.shoot_timer=60
        hero=z["Link"]();hero.x=px;hero.y=py;result=enemy.update(hero)
        lines.append(row("ZELDA_ENEMY",name,("octorok","moblin","armos").index(kind),x,y,px,py,
                         enemy.x,enemy.y,enemy.health,enemy.shoot_timer,enemy.hit_flash,result=="shoot"))
    for x,y,dx,dy in [(400,300,2.5,0),(799,300,2.5,0),(1,300,-2.5,0),(400,1,0,-2.5),(400,599,0,2.5),(400,300,0,0),(2.5,20,-2.5,0)]:
        projectile=z["Projectile"](x,y,dx,dy);projectile.update(); r=projectile.get_rect()
        lines.append(row("ZELDA_PROJECTILE",x,y,dx,dy,projectile.x,projectile.y,projectile.alive,r.x,r.y,r.w,r.h))
    return "\n".join(lines)+"\n"


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--desktop",type=Path,required=True)
    parser.add_argument("--output",type=Path,default=Path(__file__).with_name("maze_parity.txt"))
    parser.add_argument("--write",action="store_true")
    args=parser.parse_args(); data=generate(args.desktop)
    if args.write: args.output.write_text(data,encoding="utf-8",newline="\n")
    elif args.output.read_text(encoding="utf-8")!=data: raise RuntimeError("Maze source fixture mismatch")
    print(f"Maze source oracle: {sum(bool(s) and not s.startswith('#') for s in data.splitlines())-1} reviewed source cases PASS")


if __name__ == "__main__":
    main()
