#!/usr/bin/env python3
"""Build fixtures from SHA-pinned, reviewed AST rule fragments, never game scripts.

No pygame import, module initialization, display, event loop or file writes from
the source are evaluated. Only the listed classes/methods and constants below
are compiled. Run: python sports_source_oracle.py --desktop PATH --output PATH
"""
import argparse
import ast
import collections
import hashlib
import math
from pathlib import Path
import random
import types

PINS = {
    "football_pygame_ce.py": "7b013f8151aa1c815ba0947c2d5d39cf559467106cde60aacca29df936ca3ebe",
    "super_dodge_ball_fixed.py": "359b4bc045b00186e9d3ee915863de214453b22df8b81a881402ee6b49d21cb6",
}
CONSTANTS = {"WIDTH", "HEIGHT", "FPS", "COUNTRIES", "WHITE", "BLACK", "RED", "BLUE",
             "GREEN", "YELLOW", "ORANGE", "PURPLE", "CYAN", "PINK", "DEADZONE",
             "AXIS_LEFT_X", "AXIS_LEFT_Y", "BTN_A", "BTN_B"}
METHODS = {
    "football_pygame_ce.py": {"Player": {"__init__", "update", "kick"}, "Ball": {"__init__", "update"}},
    "super_dodge_ball_fixed.py": {
        "Player": {"__init__", "update", "_update_human", "_update_cpu"},
        "Ball": {"__init__", "update", "throw", "try_pickup", "try_catch"},
    },
}


def fragments(path):
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != PINS[path.name]:
        raise ValueError(f"Canonical source SHA changed: {path.name}")
    source = raw.decode("utf-8-sig")
    tree = ast.parse(source, filename=path.name)
    selected = []
    for node in tree.body:
        if isinstance(node, ast.Assign) and all(isinstance(t, ast.Name) and t.id in CONSTANTS for t in node.targets):
            ast.literal_eval(node.value)  # Reject anything except the reviewed literal constants.
            selected.append(node)
        elif isinstance(node, ast.ClassDef) and node.name in METHODS[path.name]:
            methods = [n for n in node.body if isinstance(n, ast.FunctionDef) and n.name in METHODS[path.name][node.name]]
            selected.append(ast.ClassDef(name=node.name, bases=[], keywords=[], body=methods, decorator_list=[]))
        elif isinstance(node, ast.FunctionDef) and node.name in {"make_team", "aim_and_throw", "get_axis", "get_hat"}:
            selected.append(node)
    pg = types.SimpleNamespace(**{key: key for key in ("K_LEFT", "K_RIGHT", "K_UP", "K_DOWN", "K_a", "K_d", "K_w", "K_s", "K_LSHIFT", "K_RSHIFT")})
    pg.error = RuntimeError
    env = {"math": math, "random": random.Random(730), "pygame": pg,
           "get_button": lambda _: False, "add_burst": lambda *args, **kwargs: None}
    module = ast.fix_missing_locations(ast.Module(body=selected, type_ignores=[]))
    exec(compile(module, f"reviewed:{path.name}", "exec"), env)
    set_controller(env, 0, 0)
    return env, tree


def set_controller(env, ax, ay, hat_x=0, hat_y=0):
    env["controller"] = types.SimpleNamespace(
        get_axis=lambda index: ax if index == 0 else ay,
        get_numhats=lambda: 1, get_hat=lambda _: (hat_x, hat_y))


def key_state(left=0, right=0, up=0, down=0, jump=0):
    keys = collections.defaultdict(bool)
    for key, value in [("K_LEFT", left), ("K_RIGHT", right), ("K_UP", up), ("K_DOWN", down), ("K_LSHIFT", jump)]:
        keys[key] = bool(value)
    return keys


def write_fixtures(desktop, output):
    football, _ = fragments(desktop / "football_pygame_ce.py")
    dodge, dodge_tree = fragments(desktop / "super_dodge_ball_fixed.py")
    rows = ["# Sports fixtures: executed SHA-pinned Python AST fragments; no game startup."]

    def row(tag, *values):
        rows.append(" ".join([tag] + [format(float(v), ".17g") for v in values]))

    for cpu in (0, 1):
        for left, right, up, down, ax, ay in [(0,0,0,0,0,0), (1,1,1,1,0,0), (1,0,1,0,0,0), (1,0,0,0,.2,0), (1,0,0,0,.21,-.4), (0,0,0,0,-.9,.7), (0,0,0,0,.8,.1), (0,0,0,0,.15,.8)]:
            for x,y,bx,by,cd in [(200,300,400,350,0), (40,40,0,0,12), (760,560,800,600,1), (400,300,400,300,0)]:
                set_controller(football, ax, ay)
                p = football["Player"](x,y,(0,0,0),is_cpu=bool(cpu))
                b = football["Ball"]();b.x=bx;b.y=by;p.kick_cooldown=cd
                p.update(key_state(left,right,up,down),b,None)
                row("F_MOVE",cpu,left,right,up,down,ax,ay,x,y,bx,by,cd,p.x,p.y,p.kick_cooldown)
    for x,y,bx,by,cd in [(200,300,203,304,0),(200,300,200,300,0),(0,0,600,800,0),(200,300,400,300,1)]:
        p=football["Player"](x,y,(0,0,0));b=football["Ball"]();b.x=bx;b.y=by;p.kick_cooldown=cd
        success=p.kick(b)
        row("F_KICK",x,y,bx,by,cd,bool(success),b.vel_x,b.vel_y,p.kick_cooldown)
    for x,y,vx,vy in [(400,300,8,-3),(41,41,-8,-6),(759,559,8,6),(40,560,0,0),(50,221,-1,0),(750,379,1,0)]:
        b=football["Ball"]();b.x=x;b.y=y;b.vel_x=vx;b.vel_y=vy;b.update()
        row("F_BALL",x,y,vx,vy,b.x,b.y,b.vel_x,b.vel_y)

    names=list(dodge["COUNTRIES"])
    for c,name in enumerate(names):
        for cpu in (0,1):
            for slot,p in enumerate(dodge["make_team"](name,bool(cpu))):
                row("D_TEAM",c,slot,cpu,p.x,p.y,p.power,p.speed,p.health,p.facing_right)
        for super_type in (1,2):
            for charge,force in [(0,0),(30,0),(31,0),(0,1)]:
                p=dodge["make_team"](name)[0];p.has_ball=True;p.charge=charge;p.super_type=super_type
                target=types.SimpleNamespace(x=p.x+3,y=p.y+4,health=3)
                b=dodge["Ball"]();b.owner=p
                dodge["aim_and_throw"](b,p,[target],bool(force))
                row("D_THROW",c,super_type,charge,force,b.vel_x,b.vel_y,b.is_power_ball,p.throw_cooldown,p.charge,p.has_ball)
    for values in [
        (0,1,180,300,300,1,0,1,0,0,0,0,0,1,0,0,0,0),
        (0,1,180,300,300,1,30,1,0,0,0,1,1,1,1,0,0,0),
        (1,0,200,200,200,1,60,1,0,0,0,1,0,0,0,.21,-.6,0),
        (3,2,360,80,400,0,20,1,0,0,0,0,1,1,0,0,0,1),
        (7,0,60,510,200,1,1,1,0,0,0,1,0,0,1,0,0,0),
        (0,1,180,300,300,0,0,1,0,0,0,0,0,0,0,0,0,1),
        (0,1,180,250,300,1,40,0,-1,8,1,0,0,0,0,0,0,1),
        (0,1,180,299,300,0,0,0,2,1,0,0,0,0,0,0,0,0),
        (0,1,180,350,300,0,0,1,0,0,0,0,0,0,0,0,0,1),
        (0,1,180,300,300,1,0,1,0,0,0,0,0,0,0,.8,.1,0,0,0,0,0),
        (0,1,180,300,300,1,0,1,0,0,0,0,0,0,0,.15,.8,0,0,0,0,0),
        (0,1,180,300,300,1,0,1,0,0,0,0,0,0,0,0,0,0,0,0,1,0),
        (0,1,180,300,300,1,0,1,0,0,0,0,0,0,0,0,-.8,0,0,1,0,0),
    ]:
        c,slot,x,y,base,has,charge,ground,jv,jcd,prev,left,right,up,down,ax,ay,jump = values[:18]
        pad_left,pad_right,pad_up,pad_down = values[18:] if len(values)>18 else (0,0,0,0)
        p=dodge["make_team"](names[c])[slot]
        p.x=x;p.y=y;p.base_y=base;p.has_ball=bool(has);p.charge=charge;p.on_ground=bool(ground)
        p.jump_vel=jv;p.jump_cooldown=jcd;p.jump_was_down=bool(prev);p.throw_cooldown=4
        set_controller(dodge, ax, ay, pad_right-pad_left, pad_up-pad_down)
        p.update(key_state(left,right,up,down,jump),dodge["Ball"](),[])
        row("D_HUMAN",c,slot,x,y,base,has,charge,ground,jv,jcd,prev,left,right,up,down,ax,ay,jump,
            pad_left,pad_right,pad_up,pad_down,
            p.x,p.y,p.facing_right,p.charge,p.on_ground,p.jump_vel,p.jump_cooldown,p.throw_cooldown)
    for x,y,vx,vy,power in [(400,300,8,-3,0),(51,71,-12,-6,1),(749,519,8,6,0),(50,520,0,0,1),(400,300,.3,.14,1),(400,300,.3,.16,1)]:
        b=dodge["Ball"]();b.x=x;b.y=y;b.vel_x=vx;b.vel_y=vy;b.in_air=True;b.is_power_ball=bool(power);b.update()
        row("D_BALL",x,y,vx,vy,power,b.x,b.y,b.vel_x,b.vel_y,b.in_air,b.is_power_ball)
    for ground in (0,1):
        for power in (0,1):
            for health in (0,3):
                for dist in (0,17.99,18,22,22.99,23,33.99,34):
                    p=dodge["make_team"]("USA")[0];p.health=health;p.on_ground=bool(ground)
                    b=dodge["Ball"]();b.x=p.x+dist;b.y=p.y;b.in_air=True;b.is_power_ball=bool(power)
                    result=b.try_catch(p)
                    row("D_CATCH",ground,power,health,dist,result,b.in_air,b.is_power_ball,p.has_ball)
    for dist in (0,23.99,24):
        for health in (0,3):
            for air in (0,1):
                for owned in (0,1):
                    p=dodge["make_team"]("USA")[0];p.health=health
                    b=dodge["Ball"]();b.x=p.x+dist;b.y=p.y;b.in_air=bool(air);b.owner=p if owned else None
                    result=b.try_pickup(p)
                    row("D_PICKUP",dist,health,air,owned,result,p.has_ball)
    # Review-select the two actual damage assignments from main, not its loop.
    damage = next(n for n in ast.walk(dodge_tree) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=="damage" for t in n.targets))
    health = next(n for n in ast.walk(dodge_tree) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Attribute) and t.attr=="health" for t in n.targets) and isinstance(n.value,ast.Call) and isinstance(n.value.func,ast.Name) and n.value.func.id=="max")
    damage_code=compile(ast.fix_missing_locations(ast.Module(body=[damage,health],type_ignores=[])),"reviewed:damage","exec")
    for hp in (1,2,3):
        for power in (0,1):
            env={"ball":types.SimpleNamespace(is_power_ball=bool(power)),"p":types.SimpleNamespace(health=hp)}
            exec(damage_code,env)
            row("D_DAMAGE",hp,power,env["p"].health)
    output.write_text("\n".join(rows)+"\n",encoding="utf-8")
    print(f"Generated {len(rows)-1} source cases from reviewed, pinned fragments.")


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--desktop",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    write_fixtures(args.desktop,args.output)
