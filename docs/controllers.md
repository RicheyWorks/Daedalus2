# Controllers

The Daedalus hero (ADR-040) plays on keyboard and mouse, on XInput pads, and on generic USB pads. Every binding
lives in one place, `ADaedalusHero::BeginPlay` plus your profile file. In Play, `DescribeBindings()` lists them
all, and so does the harness.

## Layout

| Action | Keyboard / mouse | Xbox Elite 2, GameSir, Razer Wolverine/Kishi (XInput) | Generic USB (profile) |
|---|---|---|---|
| Move | WASD | left stick, d-pad | Axis1 / Axis2 |
| Look | mouse (raw) | right stick (rate) | Axis3 / Axis4 |
| Jump | Space | A | Button2 |
| Sword (down-thrust in the air) | left mouse, J | X, RT | Button1, Button8 |
| Dash | Shift | B, RB | Button3, Button6 |
| Shield | right mouse, K | LT, LB | Button5, Button7 |

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
