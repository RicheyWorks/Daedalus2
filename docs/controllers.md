# Controllers

The Daedalus hero (ADR-040) plays on keyboard and mouse, on XInput pads, and on generic USB pads. Every binding
lives in one place, `ADaedalusHero::BeginPlay` plus your profile file. In Play, `DescribeBindings()` lists them
all, and so does the harness.

## Layout

Default button layout (Settings → Controller → Button Layout changes the pad column):

| Action | Keyboard / mouse | Xbox Elite 2, GameSir, Razer Wolverine/Kishi (XInput) | Generic USB (profile) |
|---|---|---|---|
| Move | WASD | left stick | Axis1 / Axis2 |
| Look (inverted if Invert Look is on) | mouse (raw) | right stick | Axis3 / Axis4 |
| Jump | Space | A | Button2 |
| Fire (blaster) / swing (sword) | left mouse | RT | Button8 |
| Melee (down-thrust in the air) | Q, J | RB, R3 | Button1 |
| Aim (zoom; shield with the sword) | right mouse, K | LT | Button5, Button7 |
| Dash | Shift | B | Button3, Button6 |
| Switch weapon | 1, 2, wheel | Y | Button4 |
| Interact (get on / off a Ghost) | E | X | |
| Call a Ghost | G | d-pad right | |
| Sprint | Left Ctrl | L3 | |
| Swap shoulder | C | LB, d-pad down | |
| Camera view (first person → over the shoulder → classic) | V | d-pad up | |
| Game Menu (pause, then Settings) | F1, F10 | Menu (three lines) | |
| Field Menu (TacMap, hero, controls, social) | Tab, M | View (two boxes) | |

**Button layouts** (Halo Infinite's set): Default, Bumper Jumper (jump on LB, melee on B), Bumper Ninja, Boxer,
Green Thumb, Recon. **Thumbstick layouts:** Default, Southpaw, Legacy, Legacy Southpaw. Both apply at once.

**Riding a Ghost (ADR-043):** left stick / WASD throttle and strafe, the bike steers where you look, RT / left mouse
fires the twin guns, LB / LT / Shift boosts, X / E gets off.

- **Elite Series 2 paddles and Razer's extra buttons:** these are mapped in Xbox Accessories or Razer Synapse to
  face buttons, so they work as whatever you assign them.
- **Rumble:** a light tick on a swing, a thump on a down-thrust bounce, a hard landing and a respawn.
  `daedalus.Rumble 0` turns it off.

## High-polling mice (Razer 8K)

Mouse look is raw. Each count the mouse reports turns the camera by `daedalus.MouseSensitivity` degrees, with no
smoothing and no scaling by frame time. A mouse polling at 8000 Hz therefore gives the same turn for the same
hand movement at any frame rate, just finer.

## Nintendo and other non-XInput pads

The Switch Pro controller (wired), N64 USB controllers and N64 adapters (Mayflash, Retro-bit and others) aren't
XInput. Unreal reads them through the **RawInput** plugin as `GenericUSBController_Button1..20` and
`_Axis1..24`. DaedalusLink turns RawInput on.

Adapters number their buttons differently, so the mapping is a file you edit:
`<Project>/Saved/Config/DaedalusControllers.json`. It's written with defaults the first time you press Play.

```json
{
  "bindings": {
    "Jump":  ["GenericUSBController_Button2"],
    "Swing": ["GenericUSBController_Button1"],
    "Move":  ["GenericUSBController_Axis1:dz1", "GenericUSBController_Axis2:y-:dz1"]
  }
}
```

Each entry is an Unreal key name with optional flags after `:`.

| Flag | Meaning |
|---|---|
| `y` | this key drives the Y axis |
| `-` | negate |
| `dz` | radial deadzone |
| `dz1` | axial deadzone (one axis) |

To find what a button is called, press Play, open the console with the backtick key, and type
`showdebug enhancedinput`, then press the button. You can also use Steam Input, which presents any controller as
XInput, and then everything in the XInput column applies.

The N64 layout from the default file:

| N64 button | Action |
|---|---|
| A | jump |
| B | sword |
| Z | shield |
| R | dash |
| C-buttons | look |

## Tuning

Set these in the console, or in `Config/DefaultEngine.ini` under `[ConsoleVariables]`.

| Variable | Default | What it does |
|---|---|---|
| `daedalus.MouseSensitivity` | 0.30 | degrees per mouse count |
| `daedalus.StickLookRate` | 200 | degrees per second at full right stick |
| `daedalus.InvertY` | 0 | 1 inverts vertical look |
| `daedalus.Deadzone` | 0.15 | stick deadzone (read when the hero spawns) |
| `daedalus.Rumble` | 1 | 0 turns rumble off |

## Menus (Halo Infinite style, ADR-041)

- **Menu** (the three-line button), or **F1** on a keyboard, pauses the game and opens the **Game Menu**:
  Resume, Settings, Respawn.
- **Settings** has a tab ribbon. Switch tabs with **LB / RB** (or **Q / E**). The tabs:
  - **Controller:** General, Movement & Aiming, Sensitivity & Acceleration, Move Thumbstick, Look Thumbstick
  - **Keyboard/Mouse**
  - **Video**
  - **Gameplay**
  - **Accessibility**
- Getting around Settings:
  - Move between rows with **up/down**, adjust with **left/right**, and flip a toggle with **A**.
  - **Y** resets the tab, and **B** goes back a page.
  - Changes apply and save at once, to `Saved/Config/DaedalusSettings.json`.
- **View** (the two-box button), or **Tab / M**, opens the **Field Menu**, Halo's Campaign Menu:
  - **Map:** the TacMap of the islands, with you on it
  - **Hero:** your record
  - **Controls**
  - **Social:** friends and party, which arrive with online play

## Web clients: one controller module for everything (`DaedalusPad`)

Every browser client loads the same file, `daedalus-server/src/main/resources/static/controllers/daedalus-pad.js`,
with its device bundle `controllers/controller-bundle.json`. The realm (`realm.html`) and the Prismheart demo
(`tools/rpg_demo`) use it today; a new page needs two lines:

```js
import "/controllers/daedalus-pad.js";      // or <script src="/controllers/daedalus-pad.js">
const pad = DaedalusPad.create({ bundle: "/controllers/controller-bundle.json", onChange: e => { /* e.type down/up, e.action */ } });
```

It reports logical actions (`up down left right confirm cancel menu select`), the positional buttons
(`a b x y l r zl zr l3 r3 start back guide`, where `a` is the south face button) and axes (`lx ly rx ry lt rt`).
`pad.label("confirm")` gives the name printed on the player's pad ("A", "Cross", "Fire", "K1", "C-Left" ...).

**Where a button's meaning comes from, highest first**

1. **BIND.** The player teaches this exact pad: up, down, left, right, confirm, back, menu. Saved per pad in the browser.
2. **The browser's standard mapping.** Xbox (360 to Series, Elite Series 2, Adaptive), Razer Wolverine V2/V3 (including
   the 8K models), GameSir in X-input mode, DualShock 4, DualSense and Edge, Switch Pro, most 8BitDo modes, GP2040-CE
   boards in X-input mode.
3. **The community map.** The bundle carries SDL_GameControllerDB (zlib licence, vendored in `data/controllers/`):
   1,018 USB controllers with per-platform mappings. That covers retro pads, adapters for N64, GameCube, Saturn,
   Dreamcast, NES, SNES, Genesis, 3DO and Jaguar, arcade sticks, encoders and Atari joysticks.
4. **A family guess.** It uses the `DaedalusControllers.json` numbering below (Button2 south, Button1 east,
   Button10 Start). A POV-hat d-pad is found from its resting value.

**Families and their customs.** The bundle sorts the 1,018 devices as: xbox 273, playstation 131, arcade 118,
snes 39, nintendo 24, n64 23, nes 17, sega 16, gamecube 15, saturn 9, neogeo 3, atari 2, pcengine 1, and generic
347. Nintendo-style pads (Switch, SNES, NES, PC Engine) confirm with the A label, which sits on the right. **Confirm:
bottom** makes the south button confirm on every pad. Fight sticks sold as "PS3/PS4/Xbox" sticks get arcade labels.

**The curated lineup.** `tools/controllers/curated_source.py` lists 145 models from 41 makers: Microsoft, Sony,
Nintendo (Switch Online NES/SNES/N64/Genesis, GameCube adapter), Razer (Wolverine V3 Pro / V3 TE / V2 line,
Kishi, Raiju, Kitsune, Panthera, Atrox), GameSir (G7 line, Cyclone 2, Kaleid Flux, Nova, T4 line, Tarantula Pro,
G8, X-series), 8BitDo, Hori, Sega (Mega Drive/Genesis Mini, Astro City Mini), Retro-bit, Atari (CX40+, CX78+,
CX30+ paddles, VCS), Hyperkin, SNK, Victrix, Qanba, Hit Box, GP2040-CE, Brook, Mayflash, Zero Delay, Xin-Mo,
Ultimarc, X-Arcade and more. `build_bundle.py` reports which models have a community mapping (101 of 145). The rest are
X-input/standard pads that need none, or new models; BIND covers both.

**Hardware that needs a rule, not a mapping**
- **One-button sticks** (Atari CX40+, CX Controller): release the fire button before 0.35 s to confirm, release after
  to go back, and hold 1.2 s for the menu.
- **No Start button:** Select opens the menu, or A+B together.
- **Arcade keyboard encoders** (I-PAC, X-Arcade mode 1, keyboard-mode cabinets) send MAME's default keys. With
  `arcadeKeys: true` the module reads them: arrows to move, Left Ctrl A, Left Alt B, Space X, Left Shift Y, 1 Start,
  5 Select (coin).
- **High-polling pads (Razer 8K):** the module samples every 4 ms, so a tap shorter than a frame still lands. The
  browser itself samples at about 250 Hz. The Unreal hero reads the full rate natively.
- **Stick to d-pad:** one cardinal direction, pressed at 0.55, released at 0.40, and switched only with a 0.10 lead.
  These are the same numbers as the native portal-controls translator. Disconnecting or losing focus releases
  everything held.

**Not covered here.** Light guns (Sinden, GUN4IR) and spinners/trackballs present as a mouse, so mouse code handles
them. Wheels and flight sticks show up in the bundle but have no driving or flying mode in the web clients yet.

**Native side, as of this audit.**
- **Unreal hero:** XInput, RawInput, raw mouse and `DaedalusControllers.json` all work. See the sections above.
- **Unreal realm widget** (`SDaedalusRealm::MapKey`): still hardcoded. It knows the keyboard, the XInput d-pad, the
  south and east face buttons, Menu and the left stick. It ignores the RawInput (Switch Pro, N64) and
  `DaedalusControllers.json` path.
- **Codex's portal-controls translator** (`DaedalusPortalControls.h`, branch `codex/portal-controller-intents-20261014`):
  covers that gap. It compiles warning-free host-free and passes `tools/controllers/portal_controls_check.cpp`
  (15/15). It is not wired into the widget yet, and the Unreal operator owns that wiring.
- **Java first-person host** (`daedalus-explore`): now hands GLFW the same community database
  (`PadMappings`, `glfwUpdateGamepadMappings`). It uses the first gamepad in any of the 16 slots, not only slot 1.

**Tests.** `tools/rpg_demo/pad_test.py` simulates real ids and numbering (45 checks): Elite Series 2, Wolverine V3
2 ms tap, Switch Pro, Mayflash N64, Mega Drive Mini 6B, Astro City Mini, Atari CX one-button, an unknown pad,
GameSir BIND, MAME keys, rumble and unplugging. `tools/controllers/realm_pad_test.py` drives `realm.html` on a
running server. To refresh the community data, replace `data/controllers/gamecontrollerdb.txt` and run
`python tools/controllers/build_bundle.py`.
