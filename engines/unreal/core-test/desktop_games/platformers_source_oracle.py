#!/usr/bin/env python3
"""Generate pinned platformer fixtures without importing or launching either game.

Only reviewed constants, controller accessors, non-rendering class methods and
bounded reward/pickup fragments are compiled from the AST. No source imports,
module calls, draw methods or full main loops are selected. A fixed controller and
random provider make every row reproducible.
The Rect stub uses truncating integer coordinates and strict AABB overlap, matching
the pygame.Rect operations exercised by Player.update; graphics are not tested.

Run with explicitly supplied originals (both SHA256 hashes are checked):
  python -B platformers_source_oracle.py --ironwake <contra.py> \
    --ninja <shadow_ninja_platform_fixed.py> --output <platformers_parity.txt>

Rows contain tag, scenario label, then whitespace-separated numeric fields. Boolean
values are 0/1. Headers in the generated file define each record's exact ordering.
The expected values are produced by executing selected original source methods,
not by duplicating gameplay calculations in this generator.
"""

from __future__ import annotations

import argparse
import ast
import copy
import hashlib
import math
from builtins import __build_class__
from pathlib import Path
from types import SimpleNamespace


IRONWAKE_SHA = "2e845d67754fc81feeea881b7c6d3068a60042c3371e9f8fdeae5a8616d09107"
NINJA_SHA = "83dd921b95043a2723b61513d84471adbfaede29dd18744367835fbc3aa03e36"

IRONWAKE_FIELDS = (
    "world_x", "y", "vel_y", "facing_right", "on_ground", "crouching",
    "lives", "score", "shoot_cooldown", "fire_rate", "spread_shot",
    "spread_timer", "invincible",
)
NINJA_FIELDS = (
    "x", "y", "vel_x", "vel_y", "on_ground", "facing", "attack_cooldown",
    "health", "invincible", "double_jump", "spinning", "spin_cooldown",
    "on_wall", "wall_dir", "jump_was_down",
)
IRONWAKE_PLATFORMS = {
    0: [],
    1: [(300, 420, 120, 20), (500, 320, 80, 20), (650, 440, 100, 20),
        (900, 380, 150, 20), (1100, 300, 60, 20)],
    2: [(100, 400, 100, 20)],
}
NINJA_PLATFORMS = {
    0: [],
    1: [(100, 380, 150), (350, 300, 120), (550, 220, 180), (200, 480, 400)],
    2: [(100, 300, 200)],
}


class Rect:
    """The reviewed source uses only this integer rectangle overlap operation.

    pygame-ce rect.c maps RectImport_PrimitiveFromObj to pg_IntFromObj;
    base.c implements float conversion as a C int cast (truncation toward zero).
    https://github.com/pygame-community/pygame-ce/blob/main/src_c/rect.c
    https://github.com/pygame-community/pygame-ce/blob/main/src_c/base.c
    Strict edge exclusion: https://pyga.me/docs/ref/rect.html#pygame.Rect.colliderect
    This verifies the stub contract, not an installed Pygame runtime version.
    """

    def __init__(self, x, y, width, height):
        self.x, self.y, self.width, self.height = map(int, (x, y, width, height))

    def colliderect(self, other):
        return (self.x < other.x + other.width and self.x + self.width > other.x
                and self.y < other.y + other.height and self.y + self.height > other.y)

    def collidepoint(self, x, y):
        x, y = int(x), int(y)
        return (self.x <= x < self.x + self.width
                and self.y <= y < self.y + self.height)


class Controller:
    def __init__(self):
        self.axes = {}
        self.buttons = set()
        self.hat = (0, 0)

    def get_axis(self, index):
        return self.axes.get(index, 0.0)

    def get_button(self, index):
        return index in self.buttons

    def get_numbuttons(self):
        return 32

    def get_numhats(self):
        return 1

    def get_hat(self, index):
        assert index == 0
        return self.hat


class FixedRandom:
    def __init__(self):
        self.value = 0.5
        self.integer = 60

    def random(self):
        return self.value

    def randint(self, low, high):
        assert low <= self.integer <= high, (low, self.integer, high)
        return self.integer


class Keys:
    def __init__(self, down):
        self.down = down

    def __getitem__(self, key):
        return key in self.down


def select_source(path: Path, expected_sha: str, constants, functions, classes, start_line=1):
    raw = path.read_bytes()
    actual = hashlib.sha256(raw).hexdigest()
    if actual != expected_sha:
        raise ValueError(f"Source hash changed for {path.name}: {actual}")
    tree = ast.parse(raw.decode("utf-8-sig"), filename=str(path))
    selected = []
    seen_constants, seen_functions, seen_classes = set(), set(), set()
    for node in tree.body:
        if node.lineno < start_line:
            continue
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            if isinstance(target, ast.Name) and target.id in constants:
                # Constants are accepted only if literal and free of source calls.
                ast.literal_eval(node.value)
                selected.append(node)
                seen_constants.add(target.id)
        elif isinstance(node, ast.FunctionDef) and node.name in functions:
            assert not node.decorator_list
            selected.append(node)
            seen_functions.add(node.name)
        elif isinstance(node, ast.ClassDef) and node.name in classes:
            assert not node.bases and not node.decorator_list and not node.keywords
            filtered = copy.deepcopy(node)
            filtered.body = [m for m in filtered.body if isinstance(m, ast.FunctionDef)
                             and m.name in classes[node.name]]
            assert {m.name for m in filtered.body} == set(classes[node.name])
            assert all(not m.decorator_list for m in filtered.body)
            selected.append(filtered)
            seen_classes.add(node.name)
    assert seen_constants == set(constants)
    assert seen_functions == set(functions)
    assert seen_classes == set(classes)
    module = ast.Module(body=selected, type_ignores=[])
    # All calls used by reviewed methods must remain within the isolated providers.
    allowed_names = {"abs", "max", "min", "get_axis", "get_button", "get_hat",
                     "Bullet", "Sword", "NinjaStar"}
    allowed_attributes = {"get_axis", "get_button", "get_numbuttons", "get_numhats",
                          "get_hat", "Rect", "colliderect", "get_rect", "radians",
                          "cos", "sin", "append", "random", "randint"}
    for node in ast.walk(module):
        if isinstance(node, (ast.Import, ast.ImportFrom, ast.Global, ast.Nonlocal)):
            raise ValueError(f"Unexpected side-effect syntax: {type(node).__name__}")
        if isinstance(node, ast.Call):
            callee = node.func
            if isinstance(callee, ast.Name):
                assert callee.id in allowed_names, callee.id
            elif isinstance(callee, ast.Attribute):
                assert callee.attr in allowed_attributes, callee.attr
            else:
                raise ValueError("Unexpected indirect call")
    controller, random = Controller(), FixedRandom()
    key_names = ("K_LEFT", "K_RIGHT", "K_DOWN", "K_UP", "K_a", "K_d", "K_s",
                 "K_w", "K_SPACE")
    pygame = SimpleNamespace(Rect=Rect, error=RuntimeError,
                             **{name: index for index, name in enumerate(key_names)})
    env = {"__builtins__": {"abs": abs, "max": max, "min": min, "__build_class__": __build_class__},
           "__name__": "isolated_source_oracle",
           "pygame": pygame, "math": math, "random": random, "controller": controller}
    exec(compile(module, str(path), "exec"), env)
    return env


def select_fragment(path: Path, expected_sha: str, first_line: int, last_line: int):
    """Compile exactly one reviewed bounded AST branch, never the containing loop."""
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected_sha:
        raise ValueError(f"Source hash changed for {path.name}")
    tree = ast.parse(raw.decode("utf-8-sig"), filename=str(path))
    main = [node for node in tree.body if isinstance(node, ast.FunctionDef)
            and node.name == "main"][-1]
    matches = [node for node in ast.walk(main)
               if isinstance(node, (ast.For, ast.If)) and node.lineno == first_line
               and node.end_lineno == last_line]
    assert len(matches) == 1, (path.name, first_line, last_line)
    module = ast.Module(body=[copy.deepcopy(matches[0])], type_ignores=[])
    allowed_names = {"create_explosion", "isinstance"}
    allowed_attributes = {"update", "Rect", "collidepoint", "colliderect", "get_rect",
                          "remove", "hypot"}
    for node in ast.walk(module):
        if isinstance(node, (ast.Import, ast.ImportFrom, ast.Global, ast.Nonlocal, ast.While)):
            raise ValueError(f"Unexpected fragment syntax: {type(node).__name__}")
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                assert node.func.id in allowed_names, node.func.id
            elif isinstance(node.func, ast.Attribute):
                assert node.func.attr in allowed_attributes, node.func.attr
            else:
                raise ValueError("Unexpected indirect fragment call")
    return compile(module, str(path), "exec")


def read_state(obj, fields):
    return [getattr(obj, name) for name in fields]


def configure(obj, **values):
    for name, value in values.items():
        setattr(obj, name, value)
    return obj


def configure_input(env, mask, axis_x, axis_y, hat, buttons, ninja):
    controller = env["controller"]
    controller.axes = {0: axis_x, 1: axis_y}
    controller.buttons = buttons
    controller.hat = hat
    names = ("K_LEFT", "K_RIGHT", "K_UP", "K_DOWN", "K_SPACE") if ninja else (
        "K_LEFT", "K_RIGHT", "K_DOWN", "K_SPACE")
    return Keys({getattr(env["pygame"], name) for index, name in enumerate(names)
                 if mask & (1 << index)})


def bullet_state(bullet):
    return read_state(bullet, ("world_x", "y", "vx", "vy", "life"))


def attack_state(attack, star):
    return [attack.x, attack.y, attack.direction, attack.life, star,
            attack.angle if star else 0]


def build_fixtures(ironwake, ninja):
    rows = []

    def emit(tag, label, *parts):
        values = []
        for part in parts:
            values.extend(part if isinstance(part, (tuple, list)) else [part])
        rows.append((tag, label, values))

    def cstep(label, values=None, frames=1, preset=0, camera=0, mask=0,
              axis_x=0, axis_y=0, pad_down=False, pad_jump=False, player=None):
        player = player or ironwake["Player"]()
        configure(player, **(values or {}))
        before = read_state(player, IRONWAKE_FIELDS)
        keys = configure_input(ironwake, mask, axis_x, axis_y, (0, 0),
                               ({12} if pad_down else set()) | ({0} if pad_jump else set()), False)
        for _ in range(frames):
            player.update(keys, IRONWAKE_PLATFORMS[preset], camera)
        emit("CSTEP", label, before, [frames, preset, camera, mask, axis_x, axis_y,
                                     pad_down, pad_jump], read_state(player, IRONWAKE_FIELDS))
        return player

    cstep("initial_gravity")
    cstep("initial_lands", frames=12)
    for axis in (-1, -0.5, -0.15, 0, 0.15, 0.151, 0.5, 1):
        for mask in (0, 1, 2, 3):
            cstep(f"move_axis{axis}_keys{mask}", {"y": 472, "on_ground": True},
                  frames=3, mask=mask, axis_x=axis)
    for label, kwargs in (
        ("keyboard_jump", {"mask": 8}), ("controller_jump", {"pad_jump": True}),
        ("keyboard_crouch", {"mask": 4}), ("controller_crouch", {"pad_down": True}),
        ("stick_crouch", {"axis_y": 0.501}), ("stick_crouch_threshold", {"axis_y": 0.5}),
        ("crouch_blocks_jump", {"mask": 12}),
        ("pad_crouch_blocks_jump", {"pad_down": True, "pad_jump": True}),
    ):
        cstep(label, {"y": 472, "on_ground": True}, **kwargs)
    cstep("held_jump_repeats_after_landing", {"y": 472, "on_ground": True}, frames=45, mask=8)
    cstep("airborne_jump_ignored", {"y": 300, "on_ground": False, "vel_y": 2}, mask=8)
    cstep("camera_left_bound", {"world_x": 20, "y": 400}, camera=80, mask=1)
    cstep("platform_descending", {"world_x": 130.8, "y": 350.2, "vel_y": 3}, preset=2)
    cstep("platform_ascending_passes", {"world_x": 130, "y": 367, "vel_y": -3}, preset=2)
    cstep("platform_edge_no_overlap", {"world_x": 200, "y": 350, "vel_y": 3}, preset=2)
    cstep("platform_fractional_overlap", {"world_x": 99.9, "y": 352, "vel_y": 1}, preset=2)
    cstep("timers_expire", {"y": 472, "on_ground": True, "shoot_cooldown": 1,
                           "spread_shot": True, "spread_timer": 1, "invincible": 1})
    cstep("timers_count_down", {"y": 472, "on_ground": True, "shoot_cooldown": 8,
                               "spread_shot": True, "spread_timer": 900, "invincible": 90}, frames=7)
    for right in (False, True):
        for crouch in (False, True):
            for spread in (False, True):
                for cooldown in (0, 1):
                    player = configure(ironwake["Player"](), world_x=243.5, y=301.25,
                                       facing_right=right, crouching=crouch, spread_shot=spread,
                                       shoot_cooldown=cooldown)
                    initial = read_state(player, IRONWAKE_FIELDS)
                    bullets = []
                    player.shoot(bullets)
                    tail = [value for bullet in bullets for value in bullet_state(bullet)]
                    tail.extend([0] * (15 - len(tail)))
                    emit("CSHOT", f"right{int(right)}_crouch{int(crouch)}_spread{int(spread)}_cd{cooldown}",
                         initial, player.shoot_cooldown, len(bullets), tail)
    player = configure(ironwake["Player"](), fire_rate=4)
    initial = read_state(player, IRONWAKE_FIELDS)
    bullets = []
    player.shoot(bullets)
    emit("CSHOT", "rapid_fire", initial, player.shoot_cooldown, 1, bullet_state(bullets[0]) + [0] * 10)
    for vx, vy, frames in ((12, 0, 1), (-12, 0, 60), (11.5, 3.2, 7), (5, 2, 15)):
        bullet = ironwake["Bullet"](100.5, 200.25, vx, vy)
        initial = bullet_state(bullet)
        for _ in range(frames):
            bullet.update()
        emit("CBULLET", f"vx{vx}_vy{vy}_frames{frames}", initial, frames, bullet_state(bullet))
    for kind, name in enumerate(("grunt", "turret", "boss")):
        for random_float in (0.01, 0.02, 0.5):
            for px in (100, 550, 550.5, 900):
                ironwake["random"].integer = 60
                enemy = ironwake["Enemy"](550, 420, name)
                enemy.shoot_timer = 1
                initial = read_state(enemy, ("world_x", "y", "vel_x", "health", "shoot_timer")) + [kind]
                ironwake["random"].value = random_float
                ironwake["random"].integer = 80
                enemy_bullets = []
                enemy.update(SimpleNamespace(world_x=px), enemy_bullets)
                expected = read_state(enemy, ("world_x", "y", "vel_x", "health", "shoot_timer")) + [kind]
                tail = bullet_state(enemy_bullets[0]) if enemy_bullets else [0] * 5
                emit("CENEMY", f"{name}_rng{random_float}_player{px}", initial,
                     [1, px, random_float, 80], expected, len(enemy_bullets), tail)
    for kind, name in enumerate(("grunt", "turret", "boss")):
        ironwake["random"].integer = 60
        enemy = ironwake["Enemy"](550, 420, name)
        initial = read_state(enemy, ("world_x", "y", "vel_x", "health", "shoot_timer")) + [kind]
        ironwake["random"].value = 0.5
        bullets = []
        for _ in range(8):
            enemy.update(SimpleNamespace(world_x=100), bullets)
        expected = read_state(enemy, ("world_x", "y", "vel_x", "health", "shoot_timer")) + [kind]
        emit("CENEMY", f"{name}_no_shot_8frames", initial, [8, 100, 0.5, 60], expected, 0, [0] * 5)

    def nstep(label, values=None, frames=1, preset=1, mask=0,
              axis_x=0, axis_y=0, hat=(0, 0), pad_jump=False, player=None):
        player = player or ninja["Ninja"]()
        configure(player, **(values or {}))
        before = read_state(player, NINJA_FIELDS)
        keys = configure_input(ninja, mask, axis_x, axis_y, hat, {0} if pad_jump else set(), True)
        for _ in range(frames):
            player.update(keys, NINJA_PLATFORMS[preset])
        emit("NSTEP", label, before, [frames, preset, mask, axis_x, axis_y, *hat, pad_jump],
             read_state(player, NINJA_FIELDS))
        return player

    nstep("safe_initial_platform")
    for axis in (-1, -0.5, -0.2, -0.15, 0, 0.15, 0.2, 0.201, 0.5, 1):
        for mask in (0, 1, 2, 3):
            nstep(f"move_axis{axis}_keys{mask}", mask=mask, axis_x=axis)
    for hat_x in (-1, 1):
        nstep(f"hat{hat_x}_overrides_axis", axis_x=-hat_x, hat=(hat_x, 0), mask=3)
        opposing_key = 1 if hat_x > 0 else 2
        nstep(f"hat{hat_x}_opposing_keyboard", mask=opposing_key, hat=(hat_x, 0))
        nstep(f"hat{hat_x}_opposing_stick", axis_x=-hat_x, hat=(hat_x, 0))
        nstep(f"hat{hat_x}_opposing_keyboard_and_stick", mask=opposing_key,
              axis_x=-hat_x, hat=(hat_x, 0))
    player = nstep("jump_first_press", mask=16)
    player = nstep("jump_held_keeps_double", mask=16, frames=4, player=player)
    player = nstep("jump_released", player=player)
    player = nstep("jump_second_press", mask=16, player=player)
    player = nstep("double_jump_held", mask=16, frames=2, player=player)
    player = nstep("double_jump_release", player=player)
    nstep("third_jump_ignored", mask=16, player=player)
    nstep("controller_jump_first_press", pad_jump=True)
    nstep("controller_held_does_not_double", {"on_ground": False, "double_jump": True,
                                           "jump_was_down": True, "y": 350, "vel_y": -10}, pad_jump=True)
    nstep("fast_fall_crosses_platform", {"x": 150, "y": 290, "vel_y": 12, "on_ground": False}, preset=2)
    nstep("forgiving_platform_landing", {"x": 150, "y": 307, "vel_y": 2, "on_ground": False}, preset=2)
    nstep("platform_inclusive_left_edge", {"x": 100, "y": 299, "vel_y": 1}, preset=2)
    nstep("platform_inclusive_right_edge", {"x": 300, "y": 299, "vel_y": 1}, preset=2)
    nstep("ascending_platform_passes", {"x": 150, "y": 301, "vel_y": -4}, preset=2)
    nstep("fall_speed_cap", {"x": 400, "y": 100, "vel_y": 20, "on_ground": False}, preset=0)
    nstep("death_pit", {"x": 400, "y": 540, "vel_y": 1, "on_ground": False}, preset=0)
    for side, x in (("left", 30), ("right", 770)):
        nstep(f"wall_{side}_slide", {"x": x, "y": 200, "vel_y": 8, "on_ground": False}, preset=0)
        for label, kwargs in (("up_key", {"mask": 4}), ("down_key", {"mask": 8}),
                              ("up_axis", {"axis_y": -0.31}), ("down_axis", {"axis_y": 0.31}),
                              ("up_hat", {"hat": (0, 1)}), ("down_hat", {"hat": (0, -1)}),
                              ("jump", {"mask": 16})):
            nstep(f"wall_{side}_{label}", {"x": x, "y": 200, "vel_y": 0,
                                         "on_ground": False}, preset=0, **kwargs)
    nstep("timers_expire", {"attack_cooldown": 1, "spin_cooldown": 1, "spinning": 1,
                           "invincible": 1})
    nstep("spin_moves_after_platform", {"attack_cooldown": 18, "spin_cooldown": 45,
                                       "spinning": 25, "invincible": 45}, frames=3)
    for star in (False, True):
        for direction in (-1, 1):
            for cooldown in (0, 1, 12, 18):
                player = configure(ninja["Ninja"](), x=321.5, y=290.25, facing=direction,
                                   attack_cooldown=cooldown)
                initial = read_state(player, NINJA_FIELDS)
                attack = player.throw_star() if star else player.attack()
                emit("NATTACK", f"star{int(star)}_direction{direction}_cd{cooldown}", initial,
                     star, player.attack_cooldown, attack is not None,
                     attack_state(attack, star) if attack is not None else [0] * 6)
    for ground in (False, True):
        for cooldown in (0, 1, 45):
            player = configure(ninja["Ninja"](), on_ground=ground, spin_cooldown=cooldown)
            initial = read_state(player, NINJA_FIELDS)
            activated = player.spin_attack()
            emit("NSPIN", f"ground{int(ground)}_cd{cooldown}", initial,
                 player.spinning, player.spin_cooldown, activated)
    for star in (False, True):
        for direction in (-1, 1):
            for frames in (1, 7, 12, 50):
                attack = (ninja["NinjaStar"] if star else ninja["Sword"])(123.5, 287.25, direction)
                initial = attack_state(attack, star)
                for _ in range(frames):
                    attack.update()
                emit("NPROJECTILE", f"star{int(star)}_direction{direction}_frames{frames}",
                     initial, frames, attack_state(attack, star))
    for jumper in (False, True):
        for random_float in (0.01, 0.02, 0.5):
            for y in (420, 450, 460):
                enemy = ninja["Enemy"](820, y, "jumper" if jumper else "grunt")
                initial = read_state(enemy, ("x", "y", "vel_x", "vel_y", "health")) + [jumper]
                ninja["random"].value = random_float
                for _ in range(3):
                    enemy.update(SimpleNamespace())
                expected = read_state(enemy, ("x", "y", "vel_x", "vel_y", "health")) + [jumper]
                emit("NENEMY", f"jumper{int(jumper)}_rng{random_float}_y{y}", initial,
                     [3, random_float], expected)
    for bx, vx in ((700, -1), (500, -1), (720, 1)):
        for px, py in ((700, 380), (400, 380), (700, 480), (0, 380)):
            for invincible in (0, 1):
                boss = configure(ninja["Boss"](), x=bx, vel_x=vx, attack_timer=1)
                player = configure(ninja["Ninja"](), x=px, y=py, invincible=invincible)
                fields = ("x", "y", "vel_x", "health", "attack_timer")
                pfields = ("x", "y", "health", "invincible")
                initial, pinitial = read_state(boss, fields), read_state(player, pfields)
                boss.update(player)
                emit("NBOSS", f"boss{bx}_vx{vx}_player{px}_{py}_inv{invincible}", initial,
                     pinitial, 1, read_state(boss, fields), read_state(player, pfields))
    boss, player = ninja["Boss"](), ninja["Ninja"]()
    initial = read_state(boss, ("x", "y", "vel_x", "health", "attack_timer"))
    pinitial = read_state(player, ("x", "y", "health", "invincible"))
    for _ in range(40):
        boss.update(player)
    emit("NBOSS", "timer_40frame_sequence", initial, pinitial, 40,
         read_state(boss, ("x", "y", "vel_x", "health", "attack_timer")),
         read_state(player, ("x", "y", "health", "invincible")))
    return rows


def build_reward_fixtures(ironwake, ninja, fragments):
    """Source branch inputs use at most one enemy, attack, bullet or collectible."""
    rows = []

    def cenv():
        env = dict(ironwake)
        env.update(player=configure(ironwake["Player"](), world_x=100, y=480),
                   camera_x=0, bullets=[], enemy_bullets=[], enemies=[], powerups=[],
                   particles=[], game_state="PLAYING", create_explosion=lambda *args: None)
        ironwake["random"].value = 0.5
        ironwake["random"].integer = 60
        return env

    def nenv():
        env = dict(ninja)
        env["__builtins__"] = {**env["__builtins__"], "isinstance": isinstance}
        env.update(ninja=configure(ninja["Ninja"](), x=400, y=450), enemies=[], attacks=[],
                   score=0, collectibles=[], game_state="PLAYING")
        return env

    for kind, name in ((0, "grunt"), (2, "boss")):
        right, bottom = (228, 510) if kind == 0 else (260, 540)
        points = (("hit", 200, 480), ("right_edge_miss", right, 480),
                  ("bottom_edge_miss", 200, bottom), ("fractional_hit", 200.9, 480.9),
                  ("fractional_left_miss", 199.9, 480),
                  ("fractional_bottom_hit", 200, bottom - 0.1))
        for hp in (1, 2, 3):
            for label, bullet_x, bullet_y in points:
                env = cenv()
                enemy = configure(ironwake["Enemy"](200, 470, name), vel_x=0,
                                  shoot_timer=80, health=hp)
                env["enemies"] = [enemy]
                env["bullets"] = [ironwake["Bullet"](bullet_x, bullet_y, 0, 0)]
                exec(fragments["CREWARD"], env)
                rows.append(("CREWARD", f"{name}_hp{hp}_{label}",
                             [kind, hp, bullet_x, bullet_y, env["player"].score,
                              len(env["enemies"]), len(env["bullets"])]))
    for star in (False, True):
        for hp in (1, 2, 3):
            env = nenv()
            env["enemies"] = [configure(ninja["Enemy"](400, 450), health=hp)]
            env["attacks"] = [(ninja["NinjaStar"] if star else ninja["Sword"])(400, 450, 1)]
            exec(fragments["NREWARD"], env)
            rows.append(("NREWARD", f"star{int(star)}_hp{hp}",
                         [star, hp, env["score"], len(env["enemies"]), len(env["attacks"])]))
    for hp in (1, 2, 3):
        env = nenv()
        env["ninja"].spinning = 5
        env["enemies"] = [configure(ninja["Enemy"](420, 450), health=hp)]
        exec(fragments["NSREWARD"], env)
        rows.append(("NSREWARD", f"spin_hp{hp}", [hp, env["score"], len(env["enemies"])]))
    env = nenv()
    env["collectibles"] = [[400, 450, "gold"]]
    exec(fragments["NPICKUP"], env)
    rows.append(("NPICKUP", "touching_gold", [env["score"], len(env["collectibles"])]))
    for rapid in (False, True):
        env = cenv()
        env["powerups"] = [ironwake["PowerUp"](110, 490, "rapid" if rapid else "spread")]
        exec(fragments["CPICKUP"], env)
        player = env["player"]
        assert not env["powerups"], "Fixture must test a collected powerup"
        rows.append(("CPICKUP", "rapid" if rapid else "spread",
                     [rapid, player.spread_shot, player.spread_timer, player.fire_rate]))
    return rows


HEADERS = """# Source-executed platformer parity fixtures v2; no source imports/full-main/display/audio.
# Ironwake SHA256 {ironwake_sha}; latest definitions after line 582 only.
# Emberstep Ascent SHA256 {ninja_sha}; platform_fixed revision only.
# Rect provider: integer truncation toward zero and strict edge exclusion audited against pygame-ce rect.c/base.c and https://pyga.me/docs/ref/rect.html. Installed Pygame version not executed or established.
# CSTATE=x y vy facing ground crouch lives score cooldown rate spread timer invincible (13)
# NSTATE=x y vx vy ground facing attack health invincible doublejump spinning spinCooldown wall wallDir jumpWasDown (15)
# CSTEP label CSTATE frames preset camera keymask axisX axisY padDown padJump EXPECTED_CSTATE
# CSHOT label CSTATE expectedCooldown bulletCount [x y vx vy life]*3 (unused slots zero)
# CBULLET label x y vx vy life frames expected_x expected_y expected_vx expected_vy expected_life
# CENEMY label x y vx health timer kind frames playerX randomFloat randomInt expected_x expected_y expected_vx expected_health expected_timer expected_kind bulletCount bullet_x bullet_y bullet_vx bullet_vy bullet_life
# NSTEP label NSTATE frames preset keymask axisX axisY hatX hatY padJump EXPECTED_NSTATE
# NATTACK label NSTATE starBool expectedCooldown created attack_x attack_y direction life star angle (zero if blocked)
# NSPIN label NSTATE expectedSpinning expectedSpinCooldown activated
# NPROJECTILE label x y direction life star angle frames expected_x expected_y expected_direction expected_life expected_star expected_angle
# NENEMY label x y vx vy health jumper frames randomFloat expected_x expected_y expected_vx expected_vy expected_health expected_jumper
# NBOSS label x y vx health timer player_x player_y player_health player_invincible frames expected_boss_x expected_boss_y expected_boss_vx expected_boss_health expected_boss_timer expected_player_x expected_player_y expected_player_health expected_player_invincible
# CREWARD label kind hp bulletX bulletY expectedScore expectedEnemyCount expectedBulletCount; fixed Player(100,480), Enemy(200,470), vx0, shootTimer80, one stationary bullet, camera0.
# NREWARD label starBool hp expectedScore expectedEnemyCount expectedAttackCount; fixed Ninja(400,450), Enemy(400,450), one attack(400,450), initial score0.
# NSREWARD label hp expectedScore expectedEnemyCount; fixed Ninja(400,450) spinning5, Enemy(420,450), initial score0.
# NPICKUP label expectedScore expectedGoldCount; fixed Ninja(400,450), one gold(400,450), initial score0.
# CPICKUP label rapidBool expectedSpread expectedTimer expectedRate; fixed Player(100,480), PowerUp(110,490), no initial modifiers.
# Ironwake keymask bits=1left 2right 4down 8jump; Ninja bits=1left 2right 4up 8down 16jump.
# Ironwake preset0=[];preset1=[(300,420,120,20),(500,320,80,20),(650,440,100,20),(900,380,150,20),(1100,300,60,20)];preset2=[(100,400,100,20)]
# Ninja preset0=[];preset1=[(100,380,150),(350,300,120),(550,220,180),(200,480,400)];preset2=[(100,300,200)]
# Expected methods: Ironwake Player.__init__/get_rect/update/shoot (663-774), Bullet.__init__/update (813-823), Enemy.__init__/update (833-875), controller accessors(633-639).
# Expected methods: Ninja.__init__/update/attack/throw_star/spin_attack (120-264), Sword.__init__/update (301-309), NinjaStar.__init__/update (317-328), Enemy.__init__/update (344-363), Boss.__init__/update (376-396), controller accessors(69-103).
# Reward fragments: Ironwake enemy loop1104-1132/powerup loop1146-1156 and PowerUp.__init__/update904-911; Ninja attacks loop553-566/spin branch569-575/collectibles loop540-544. Explosion provider is a no-op; each list has at most one initial item.
# Omits complete main-loop orchestration/spawning/cheats/reset/events and controller trigger gating; no render/audio/controller-device/Unreal/package claims. Source quirks preserved in selected methods. Final-clamp repairs intentionally not in parity rows.
"""


def number(value):
    return str(int(value)) if isinstance(value, bool) else format(value, ".17g")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ironwake", required=True, type=Path)
    parser.add_argument("--ninja", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    ironwake = select_source(args.ironwake, IRONWAKE_SHA,
        {"WIDTH", "HEIGHT", "GRAVITY", "JUMP_STRENGTH", "PLAYER_SPEED", "BULLET_SPEED",
         "ENEMY_SPEED", "AXIS_LEFT_X", "AXIS_LEFT_Y", "BTN_A", "BTN_DOWN", "DEADZONE", "ORANGE"},
        {"get_axis", "get_button"},
        {"Player": {"__init__", "get_rect", "update", "shoot"},
         "Bullet": {"__init__", "update"}, "Enemy": {"__init__", "update"},
         "PowerUp": {"__init__", "update"}}, start_line=582)
    ninja = select_source(args.ninja, NINJA_SHA,
        {"WIDTH", "HEIGHT", "AXIS_LEFT_X", "AXIS_LEFT_Y", "BTN_A", "DEADZONE"},
        {"get_axis", "get_button", "get_hat"},
        {"Ninja": {"__init__", "update", "attack", "throw_star", "spin_attack"},
         "Sword": {"__init__", "update"}, "NinjaStar": {"__init__", "update"},
         "Enemy": {"__init__", "update"}, "Boss": {"__init__", "update"}})
    rows = build_fixtures(ironwake, ninja)
    fragments = {
        "CREWARD": select_fragment(args.ironwake, IRONWAKE_SHA, 1104, 1132),
        "CPICKUP": select_fragment(args.ironwake, IRONWAKE_SHA, 1146, 1156),
        "NREWARD": select_fragment(args.ninja, NINJA_SHA, 553, 566),
        "NSREWARD": select_fragment(args.ninja, NINJA_SHA, 569, 575),
        "NPICKUP": select_fragment(args.ninja, NINJA_SHA, 540, 544),
    }
    rows.extend(build_reward_fixtures(ironwake, ninja, fragments))
    content = HEADERS.format(ironwake_sha=IRONWAKE_SHA, ninja_sha=NINJA_SHA)
    content += "".join(f"{tag} {label} " + " ".join(map(number, values)) + "\n"
                       for tag, label, values in rows)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(content, encoding="utf-8", newline="\n")
    counts = {tag: sum(row[0] == tag for row in rows) for tag in sorted({row[0] for row in rows})}
    print(f"Generated {len(rows)} source-executed scenarios: {counts}")


if __name__ == "__main__":
    main()
