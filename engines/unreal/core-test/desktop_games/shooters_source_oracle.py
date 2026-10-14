#!/usr/bin/env python3
"""Generate shooter rule fixtures from SHA-pinned, reviewed original AST nodes.

This does not import any game module, import pygame, execute module startup,
create a display, read saves, or run a game loop. Only explicitly allowlisted
constants/classes/methods below are compiled. Source execution receives a
restricted builtins dictionary, math, deterministic input/random stubs and a
minimal integer Rect. Rendering methods, imports and top-level calls are absent.

Usage: python shooters_source_oracle.py --desktop-dir PATH [--output PATH]
The supplied desktop directory must contain the three unchanged selected files.
The checked-in fixture remains usable by native CI without those local files.
"""

import argparse
import ast
import hashlib
import math
from pathlib import Path
from types import SimpleNamespace


PINS = {
    "asteroids_pygame_ce.py": "8a46338b4d93d9447df7feab40dff21b99bfa0ce7614698681b8a5c91f0fc20b",
    "sega_space_shooter.py": "5108b3065fa91332570445adaccbb8c5bb77e437bc0bd8e37213737e931ad0db",
    "star_shootergpt1_fixed.py": "05ac3a0fabddab94adb3d3a7b2c6eb9f7e1543390a48805db247a3ffd40d8281",
}

METHODS = {
    "asteroids_pygame_ce.py": {
        "Ship": {"__init__", "update", "shoot"},
        "Bullet": {"__init__", "update"},
        "Asteroid": {"__init__", "update", "split"},
    },
    "sega_space_shooter.py": {
        "Player": {"__init__", "update", "shoot"},
        "Bullet": {"__init__", "update"},
        "Enemy": {"__init__", "update"},
        "PowerUp": {"__init__", "update"},
    },
    "star_shootergpt1_fixed.py": {
        "Player": {"__init__", "reset_powerups", "update", "wants_to_shoot", "shoot", "get_rect", "hit"},
        "Bullet": {"__init__", "update", "get_rect"},
        "Enemy": {"__init__", "start_dive", "update", "shoot", "get_rect"},
        "Boss": {"__init__", "_check_phases", "update", "shoot", "get_rect"},
        "Powerup": {"__init__", "update", "get_rect", "apply"},
    },
}

CONSTANTS = {
    "WIDTH", "HEIGHT", "FPS", "BLACK", "WHITE", "CYAN", "RED", "YELLOW",
    "GREEN", "ORANGE", "GRAY", "PURPLE", "LBLUE", "DKRED", "GOLD", "PINK",
    "LIME", "AXIS_LEFT_X", "AXIS_LEFT_Y", "AXIS_RT", "DIFF_CONFIGS", "ENEMY_DATA",
}
KEY_NAMES = ("K_LEFT", "K_RIGHT", "K_UP", "K_a", "K_d", "K_w", "K_DOWN", "K_s", "K_SPACE")
KINDS = ("bee", "butterfly", "cruiser")
DIFFICULTIES = ("Easy", "Medium", "Hard")
PATTERNS = ("spread", "ring", "aimed")
STATES = ("entering", "pacing", "charging", "returning")


class Rect:
    """The source uses four-value Rect construction; floats truncate to integers."""
    def __init__(self, x, y, w, h):
        self.x, self.y, self.w, self.h = map(int, (x, y, w, h))

    def colliderect(self, other):
        return (self.w > 0 and self.h > 0 and other.w > 0 and other.h > 0
                and self.x < other.x + other.w and self.x + self.w > other.x
                and self.y < other.y + other.h and self.y + self.h > other.y)


class Keys(dict):
    def __missing__(self, key):
        return False


class Inputs:
    def __init__(self):
        self.mask = 0
        self.axes = (0.0, 0.0)
        self.hat = (0, 0)
        self.trigger = 0.0

    def keys(self):
        return Keys({name: bool(self.mask & (1 << i)) for i, name in enumerate(KEY_NAMES)})


class SuppliedRandom:
    """Explicit bounded deterministic values; no Python/native RNG parity claim."""
    def __init__(self):
        self.uniform_fraction = 0.5
        self.integer_fraction = 0.5
        self.roll = 1.0
        self.choice_index = 0

    def uniform(self, low, high):
        return low + (high - low) * self.uniform_fraction

    def randint(self, low, high):
        return low + int((high - low) * self.integer_fraction)

    def random(self):
        return self.roll

    def choice(self, values):
        return values[self.choice_index % len(values)]


def target_names(node):
    if isinstance(node, ast.Name):
        return {node.id}
    if isinstance(node, (ast.Tuple, ast.List)):
        return set().union(*(target_names(item) for item in node.elts))
    return set()


def load_rules(desktop, filename):
    path = desktop / filename
    raw = path.read_bytes()
    actual = hashlib.sha256(raw).hexdigest()
    if actual != PINS[filename]:
        raise ValueError(f"Source changed: {filename}: expected {PINS[filename]}, received {actual}")
    tree = ast.parse(raw.decode("utf-8-sig"), filename=filename)
    nodes = []
    found = {}
    for node in tree.body:
        if isinstance(node, ast.Assign):
            names = set().union(*(target_names(target) for target in node.targets))
            if names and names <= CONSTANTS:
                # Selected constant expressions cannot call arbitrary source code.
                if any(isinstance(part, ast.Call) for part in ast.walk(node)):
                    raise ValueError(f"Unexpected call in selected constant: {filename}:{node.lineno}")
                nodes.append(node)
        elif isinstance(node, ast.ClassDef) and node.name in METHODS[filename]:
            if node.bases or node.decorator_list or node.keywords:
                raise ValueError(f"Unexpected class decoration: {filename}:{node.name}")
            keep = []
            found[node.name] = set()
            for member in node.body:
                if isinstance(member, ast.FunctionDef) and member.name in METHODS[filename][node.name]:
                    if member.decorator_list:
                        raise ValueError("Unexpected decorated rule method")
                    keep.append(member)
                    found[node.name].add(member.name)
                elif isinstance(member, ast.Assign):
                    if any(isinstance(part, ast.Call) for part in ast.walk(member)):
                        raise ValueError("Unexpected call in selected class constant")
                    keep.append(member)
            nodes.append(ast.ClassDef(name=node.name, bases=[], keywords=[], body=keep, decorator_list=[]))
    if found != METHODS[filename]:
        raise ValueError(f"Selected methods not found: {filename}: {found}")

    if filename == "sega_space_shooter.py":
        # Reviewed main() collection effect only. Do not execute main() or its loop.
        main = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "main")
        candidates = [node for node in ast.walk(main) if isinstance(node, ast.If)
                      and ast.unparse(node.test) == "p.kind == 'power'"]
        if len(candidates) != 1:
            raise ValueError("Sega powerup effect fragment is not unique")
        effect = ast.FunctionDef(name="apply_power", args=ast.arguments(
            posonlyargs=[], args=[ast.arg(arg="p"), ast.arg(arg="player")],
            kwonlyargs=[], kw_defaults=[], defaults=[]),
            body=[candidates[0]], decorator_list=[])
        nodes.append(effect)

    inputs = Inputs()
    random = SuppliedRandom()
    pygame = SimpleNamespace(Rect=Rect, key=SimpleNamespace(get_pressed=inputs.keys),
                             time=SimpleNamespace(get_ticks=lambda: 0))
    for name in KEY_NAMES:
        setattr(pygame, name, name)
    builtins = {name: value for name, value in {
        "__build_class__": __build_class__, "object": object, "bool": bool,
        "int": int, "float": float, "str": str, "list": list, "dict": dict,
        "abs": abs, "min": min, "max": max, "round": round, "len": len,
        "range": range,
    }.items()}
    environment = {"__builtins__": builtins, "__name__": "reviewed_source_rules",
                   "math": math, "random": random, "pygame": pygame,
                   "get_axis": lambda index: inputs.axes[index],
                   "get_hat": lambda: inputs.hat,
                   "get_trigger": lambda index: inputs.trigger,
                   "explode": lambda x, y, color, particles, count=20: particles.extend([None] * count)}
    module = ast.fix_missing_locations(ast.Module(body=nodes, type_ignores=[]))
    exec(compile(module, filename + "::<reviewed-rules-only>", "exec"), environment)
    return environment, inputs, random


class Fixtures:
    def __init__(self):
        self.lines = ["# Shooter source fixtures v1; finite per-frame rule calls only.",
                      "# FORMAT LABEL|space-separated numeric inputs|space-separated numeric outputs",
                      "# Keys mask bits: left=1 right=2 up=4 a=8 d=16 w=32 down=64 s=128 space=256.",
                      "# Kind bee=0 butterfly=1 cruiser=2; difficulty Easy=0 Medium=1 Hard=2.",
                      "# Boss state entering=0 pacing=1 charging=2 returning=3; pattern spread=0 ring=1 aimed=2.",
                      "# Random: explicit uniform fraction, randint fraction=0.5 (floor midpoint), roll=1 (no dive).",
                      "# Particle output counts use explode stub; particles/rendering are not parity targets.",
                      "# Rect stub models source four-number construction with truncation toward zero."]
        self.count = 0
        for filename, digest in PINS.items():
            self.lines.append(f"# SOURCE {filename} SHA256 {digest}")

    def schema(self, label, inputs, outputs):
        self.lines.append(f"# {label}|{inputs}|{outputs}")

    def emit(self, label, inputs, outputs):
        def number(value):
            if isinstance(value, bool):
                return "1" if value else "0"
            if isinstance(value, int):
                return str(value)
            if not math.isfinite(value):
                raise ValueError("Fixture contains non-finite number")
            return format(value, ".17g")
        self.lines.append(f"{label}|{' '.join(map(number, inputs))}|{' '.join(map(number, outputs))}")
        self.count += 1

    def write(self, path):
        path.write_text("\n".join(self.lines) + f"\n# TOTAL {self.count}\n", encoding="utf-8", newline="\n")


def packed_bullets(bullets, maximum, velocity_names):
    values = []
    for bullet in bullets:
        values.extend((bullet.x, bullet.y, getattr(bullet, velocity_names[0]), getattr(bullet, velocity_names[1])))
    if len(bullets) > maximum:
        raise ValueError("Unexpected source pattern size")
    return values + [0] * ((maximum - len(bullets)) * 4)


def asteroid_fixtures(rules, inputs, output):
    output.schema("AST_SHIP", "x y angle vx vy cooldown keymask ax ay hatx haty frames", "x y angle vx vy cooldown thrust")
    starts = [(400, 300, -90, 0, 0, 0), (1, 1, 0, -3, -3, 8), (799, 599, 45, 3, 3, 1)]
    controls = [(0, 0, 0, 0, 0), (1, 0, 0, 0, 0), (2, 0, 0, 0, 0),
                (3, 0, 0, 0, 0), (4, 0, 0, 0, 0), (32, 0, 0, 0, 0),
                (5, 0.5, -0.5, 1, 1), (0, -0.75, -0.4, -1, 0), (0, 0, -0.4001, 0, 0)]
    for start in starts:
        for control in controls:
            for frames in (1, 8, 45):
                ship = rules["Ship"]()
                ship.x, ship.y, ship.angle, ship.vel_x, ship.vel_y, ship.shoot_cooldown = start
                inputs.mask, ax, ay, hx, hy = control
                inputs.axes, inputs.hat = (ax, ay), (hx, hy)
                for _ in range(frames):
                    ship.update(inputs.keys())
                output.emit("AST_SHIP", (*start, *control, frames),
                            (ship.x, ship.y, ship.angle, ship.vel_x, ship.vel_y, ship.shoot_cooldown, ship.thrust))
    output.schema("AST_SHOT", "x y angle cooldown", "count cooldown bullet_x bullet_y bullet_vx bullet_vy life")
    for angle in (-90, 0, 45, 180, 360):
        for cooldown in (0, 1, 8):
            ship = rules["Ship"]()
            ship.x, ship.y, ship.angle, ship.shoot_cooldown = 400, 300, angle, cooldown
            bullet = ship.shoot()
            values = (bullet.x, bullet.y, bullet.vel_x, bullet.vel_y, bullet.life) if bullet else (0, 0, 0, 0, 0)
            output.emit("AST_SHOT", (400, 300, angle, cooldown), (int(bullet is not None), ship.shoot_cooldown, *values))
    output.schema("AST_BULLET", "x y angle life frames", "x y vx vy life")
    for x, y, angle in ((799, 300, 0), (1, 300, 180), (400, 1, -90), (400, 599, 90), (0, 0, 45)):
        for frames in (1, 2, 45, 46):
            bullet = rules["Bullet"](x, y, angle)
            for _ in range(frames):
                bullet.update()
            output.emit("AST_BULLET", (x, y, angle, 45, frames), (bullet.x, bullet.y, bullet.vel_x, bullet.vel_y, bullet.life))
    output.schema("AST_ROCK", "x y size vx vy angle rotation frames", "x y angle radius split_count")
    for size in (1, 2, 3):
        for frames in (1, 8):
            rock = rules["Asteroid"](799, 1, size)
            rock.vel_x, rock.vel_y, rock.angle, rock.rot_speed = 2, -2, 90, -1.5
            for _ in range(frames):
                rock.update()
            output.emit("AST_ROCK", (799, 1, size, 2, -2, 90, -1.5, frames),
                        (rock.x, rock.y, rock.angle, rock.radius, len(rock.split())))


def sega_fixtures(rules, inputs, output):
    output.schema("SEGA_PLAYER", "x y speed cooldown invincible keymask ax ay frames", "x y speed cooldown invincible")
    controls = [(1, 0, 0), (2, 0, 0), (3, 0, 0), (4, 0, 0), (64, 0, 0),
                (68, 0, 0), (1, 0.2, 0.2), (1, 0.2001, 0), (2, -0.5, 0.5), (128, 0, 0)]
    for x, y, speed, cd, inv in ((150, 300, 5, 0, 0), (30, 20, 8, 6, 60), (750, 580, 5, 1, 1)):
        for mask, ax, ay in controls:
            for frames in (1, 8):
                player = rules["Player"]()
                player.x, player.y, player.speed, player.shoot_cooldown, player.invincible = x, y, speed, cd, inv
                inputs.mask, inputs.axes = mask, (ax, ay)
                for _ in range(frames):
                    player.update(inputs.keys())
                output.emit("SEGA_PLAYER", (x, y, speed, cd, inv, mask, ax, ay, frames),
                            (player.x, player.y, player.speed, player.shoot_cooldown, player.invincible))
    output.schema("SEGA_SHOT", "x y power cooldown", "count cooldown [x y speed dy]x3 (zero padded)")
    for power in (1, 2, 3):
        for cd in (0, 1, 6):
            player = rules["Player"]()
            player.power_level, player.shoot_cooldown = power, cd
            bullets = player.shoot()
            output.emit("SEGA_SHOT", (player.x, player.y, power, cd),
                        (len(bullets), player.shoot_cooldown, *packed_bullets(bullets, 3, ("speed", "dy"))))
    output.schema("SEGA_ENEMY", "kind x y speed timer player_y frames (basic=0 chaser=1)", "x y health timer")
    for kind_index, kind in enumerate(("basic", "chaser")):
        for player_y in (20, 300, 580):
            for frames in (1, 8, 60):
                enemy = rules["Enemy"](820, 100, kind)
                enemy.speed, enemy.shoot_timer = 3.25, 2
                player = rules["Player"]()
                player.y = player_y
                for _ in range(frames):
                    enemy.update(player)
                output.emit("SEGA_ENEMY", (kind_index, 820, 100, 3.25, 2, player_y, frames),
                            (enemy.x, enemy.y, enemy.health, enemy.shoot_timer))
    output.schema("SEGA_POWER", "kind power speed lives x y frames (power=0 speed=1 life=2)", "power speed lives x y")
    for kind_index, kind in enumerate(("power", "speed", "life")):
        for power, speed, lives in ((1, 5, 3), (3, 8, 5), (2, 7, 4)):
            player = rules["Player"]()
            player.power_level, player.speed, player.lives = power, speed, lives
            pu = rules["PowerUp"](300, 200)
            pu.kind = kind
            rules["apply_power"](pu, player)
            for _ in range(8):
                pu.update()
            output.emit("SEGA_POWER", (kind_index, power, speed, lives, 300, 200, 8),
                        (player.power_level, player.speed, player.lives, pu.x, pu.y))
    output.schema("SEGA_BULLET", "x y speed dy frames", "x y")
    for speed, dy in ((10, 0), (9, -1.5), (9, 1.5)):
        for frames in (1, 8, 60):
            bullet = rules["Bullet"](170, 300, speed, dy)
            for _ in range(frames):
                bullet.update()
            output.emit("SEGA_BULLET", (170, 300, speed, dy, frames), (bullet.x, bullet.y))


def star_fixtures(rules, inputs, supplied_random, output):
    output.schema("STAR_PLAYER", "x y cooldown invincible boost keymask ax ay frames", "x y cooldown invincible")
    controls = [(0, 0.5, -0.25), (1, 0.5, 0.5), (2, -0.5, 0.5),
                (3, 0, 0), (68, 0, 0), (128, 0, 0), (8, 0, 0)]
    for x, y, cd, inv in ((400, 500, 10, 90), (20, 20, 0, 0), (780, 580, 1, 1)):
        for boost in (False, True):
            for mask, ax, ay in controls:
                player = rules["Player"]()
                player.x, player.y, player.shoot_cooldown, player.invincible = x, y, cd, inv
                player.speed_boost = boost
                inputs.mask, inputs.axes = mask, (ax, ay)
                for _ in range(8):
                    player.update()
                output.emit("STAR_PLAYER", (x, y, cd, inv, boost, mask, ax, ay, 8),
                            (player.x, player.y, player.shoot_cooldown, player.invincible))
    output.schema("STAR_SHOT", "x y triple cooldown", "count cooldown [x y dx dy]x3 (zero padded)")
    for triple in (False, True):
        for cd in (0, 1, 10):
            player = rules["Player"]()
            player.triple, player.shoot_cooldown = triple, cd
            bullets = player.shoot()
            output.emit("STAR_SHOT", (player.x, player.y, triple, cd),
                        (len(bullets), player.shoot_cooldown, *packed_bullets(bullets, 3, ("dx", "dy"))))
    output.schema("STAR_HIT", "lives shield", "lives shield invincible gameover particle_count")
    for lives in (1, 3, 5):
        for shield in (False, True):
            player = rules["Player"](lives)
            player.shield = shield
            particles = []
            gameover = player.hit(particles)
            output.emit("STAR_HIT", (lives, shield), (player.lives, player.shield, player.invincible, gameover, len(particles)))
    output.schema("STAR_WANTS", "space trigger", "wants_shoot")
    for space in (False, True):
        for trigger in (0, 0.5, 0.5001, 1):
            inputs.mask, inputs.trigger = (256 if space else 0), trigger
            output.emit("STAR_WANTS", (space, trigger), (rules["Player"]().wants_to_shoot(),))
    output.schema("STAR_STATS", "kind difficulty wave uniform_fraction", "speed hp size base_pts dive_pts shoot_lo shoot_hi dive_speed")
    for kind_index, kind in enumerate(KINDS):
        for diff_index, diff_name in enumerate(DIFFICULTIES):
            for wave in (1, 3, 6, 9, 30):
                for fraction in (0, 0.5, 1):
                    supplied_random.uniform_fraction = fraction
                    enemy = rules["Enemy"](wave, kind, x=400, diff=rules["DIFF_CONFIGS"][diff_name])
                    output.emit("STAR_STATS", (kind_index, diff_index, wave, fraction),
                                (enemy.speed, enemy.hp, enemy.size, enemy.base_pts, enemy.dive_pts,
                                 enemy.shoot_lo, enemy.shoot_hi, enemy.dive_speed))
    supplied_random.uniform_fraction = 0.5
    output.schema("STAR_ENEMY_SHOT", "kind x y timer", "count timer [x y dx dy]x3 (zero padded)")
    for kind_index, kind in enumerate(KINDS):
        for timer in (0, 1):
            enemy = rules["Enemy"](1, kind, x=400)
            enemy.y, enemy.shoot_timer = 100, timer
            bullets = enemy.shoot()
            output.emit("STAR_ENEMY_SHOT", (kind_index, 400, 100, timer),
                        (len(bullets), enemy.shoot_timer, *packed_bullets(bullets, 3, ("dx", "dy"))))
    output.schema("STAR_DIVE", "kind x y player_x player_y frames", "x y dive_dx dive_dy timer diving alive")
    for kind_index, kind in enumerate(KINDS[:2]):
        for px, py in ((400, 500), (100, 500), (700, 50)):
            for frames in (1, 8, 60):
                enemy = rules["Enemy"](1, kind, x=400)
                enemy.y = 100
                enemy.start_dive(px, py)
                for _ in range(frames):
                    enemy.update(px, py, 1)
                output.emit("STAR_DIVE", (kind_index, 400, 100, px, py, frames),
                            (enemy.x, enemy.y, enemy.dive_dx, enemy.dive_dy, enemy.dive_timer, enemy.state == "dive", enemy.alive))
    output.schema("STAR_BOSS", "wave difficulty hp", "max_hp speed rate pattern phase66 phase33 summon_count")
    for wave in (5, 10, 15, 30):
        for diff_index, diff_name in enumerate(DIFFICULTIES):
            boss = rules["Boss"](wave, rules["DIFF_CONFIGS"][diff_name])
            for hp in sorted({boss.max_hp, int(boss.max_hp * 0.66) + 1,
                              int(boss.max_hp * 0.66), int(boss.max_hp * 0.33) + 1,
                              int(boss.max_hp * 0.33), 0}):
                boss = rules["Boss"](wave, rules["DIFF_CONFIGS"][diff_name])
                summons = []
                boss.summon_fn = summons.append
                boss.hp = hp
                boss._check_phases()
                boss._check_phases()  # phases must summon only once each
                output.emit("STAR_BOSS", (wave, diff_index, hp),
                            (boss.max_hp, boss.speed, boss.shoot_rate, PATTERNS.index(boss.pattern),
                             boss.phase66, boss.phase33, sum(summons)))
    output.schema("STAR_BOSS_SHOT", "wave pattern state timer x y player_x player_y", "count timer [x y dx dy]x8 (zero padded)")
    for wave in (5, 10, 15):
        for pattern_index, pattern in enumerate(PATTERNS):
            for state_index, state in enumerate(STATES):
                for timer in (0, 1):
                    boss = rules["Boss"](wave)
                    boss.x, boss.y, boss.pattern, boss.state, boss.shoot_timer = 400, 120, pattern, state, timer
                    bullets = boss.shoot(500, 500)
                    output.emit("STAR_BOSS_SHOT", (wave, pattern_index, state_index, timer, 400, 120, 500, 500),
                                (len(bullets), boss.shoot_timer, *packed_bullets(bullets, 8, ("dx", "dy"))))
    output.schema("STAR_BOSS_MOVE", "wave state x y direction move_timer charge_timer shot_timer hp player_x player_y frames", "x y direction move_timer charge_timer shot_timer state speed rate phase66 phase33 summon_count")
    cases = [(0, 400, -100, 1, 0, 410, 80, 60, 110),
             (1, 400, 120, 1, 120, 410, 1, 60, 1),
             (1, 400, 120, 1, 0, 1, 1, 60, 1),
             (1, 400, 120, 1, 0, 410, 80, 39, 1),
             (1, 400, 120, 1, 0, 410, 80, 19, 1),
             (2, 400, 660, 1, 0, 410, 1, 60, 1),
             (3, 400, 116, 1, 0, 410, 1, 60, 1)]
    for state, x, y, direction, move, charge, shot, hp, frames in cases:
        boss = rules["Boss"](5)
        boss.state, boss.x, boss.y = STATES[state], x, y
        boss.dir, boss.move_timer, boss.charge_timer, boss.shoot_timer, boss.hp = direction, move, charge, shot, hp
        boss.charge_dx, boss.charge_dy = 0, 6
        summons = []
        boss.summon_fn = summons.append
        for _ in range(frames):
            boss.update(400, 500)
        output.emit("STAR_BOSS_MOVE", (5, state, x, y, direction, move, charge, shot, hp, 400, 500, frames),
                    (boss.x, boss.y, boss.dir, boss.move_timer, boss.charge_timer, boss.shoot_timer,
                     STATES.index(boss.state), boss.speed, boss.shoot_rate, boss.phase66, boss.phase33, sum(summons)))
    output.schema("STAR_POWER", "kind triple shield boost x y frames (triple=0 shield=1 speed=2)", "triple shield boost x y alive bob")
    for kind_index, kind in enumerate(("triple", "shield", "speed")):
        for already_owned in (False, True):
            for y in (200, 620):
                player = rules["Player"]()
                player.triple = player.shield = player.speed_boost = already_owned
                pu = rules["Powerup"](300, y, kind)
                pu.apply(player)
                for _ in range(8):
                    pu.update()
                output.emit("STAR_POWER", (kind_index, already_owned, already_owned, already_owned, 300, y, 8),
                            (player.triple, player.shield, player.speed_boost, pu.x, pu.y, pu.alive, pu.bob))
    output.schema("STAR_BULLET", "x y dx dy big frames", "x y alive rect_x rect_y rect_w rect_h")
    for x, y, dx, dy in ((400, 500, 0, -13), (-19, 100, -1, 0), (819, 100, 1, 0), (400, -19, 0, -1), (400, 619, 0, 1), (0.5, 0.5, -1, -1)):
        for big in (False, True):
            for frames in (1, 8):
                bullet = rules["Bullet"](x, y, dx, dy, rules["CYAN"], big=big)
                for _ in range(frames):
                    bullet.update()
                rect = bullet.get_rect()
                output.emit("STAR_BULLET", (x, y, dx, dy, big, frames),
                            (bullet.x, bullet.y, bullet.alive, rect.x, rect.y, rect.w, rect.h))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--desktop-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path(__file__).with_name("shooters_parity.txt"))
    args = parser.parse_args()
    output = Fixtures()
    rules, inputs, random = load_rules(args.desktop_dir, "asteroids_pygame_ce.py")
    asteroid_fixtures(rules, inputs, output)
    rules, inputs, random = load_rules(args.desktop_dir, "sega_space_shooter.py")
    sega_fixtures(rules, inputs, output)
    rules, inputs, random = load_rules(args.desktop_dir, "star_shootergpt1_fixed.py")
    star_fixtures(rules, inputs, random, output)
    output.write(args.output)
    print(f"Generated {output.count} reviewed-source fixtures at {args.output}")


if __name__ == "__main__":
    main()
