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
