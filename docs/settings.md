# Settings: one schema, Halo Infinite's tabs, every client

All settings live in one schema, `data/settings/settings-schema.json`. Every client reads it: the Unreal hero and
menu, the realm web client, and the Prismheart demo. Its tabs and sections follow Halo Infinite's Settings
([game settings guide](https://support.halowaypoint.com/hc/en-us/articles/4407649252116-Guide-to-Halo-Infinite-Game-Settings),
[accessibility guide](https://support.halowaypoint.com/hc/en-us/articles/4408122295444-Accessibility-features-in-Halo-Infinite)).

| Tab | Sections (Infinite's names; *ours* marked) |
|---|---|
| **CONTROLLER** | General (Button Layout, Thumbstick Layout, Vibration, Vibration Strength, *Menu Confirm Button*) · Movement & Aiming · Sensitivity & Acceleration · Trigger Deadzone · Move Thumbstick · Look Thumbstick |
| **KEYBOARD/MOUSE** | Movement & Aiming · Sensitivity |
| **VIDEO** | Display (Field of View) · *Camera* (Camera View, Shoulder, Reticle, Camera Distance) |
| **AUDIO** | Volume (Main, Voice, Music, Menu Music, Sound Effects, Inactive Mute) · Hardware (Dynamic Range) |
| **GAMEPLAY** | *Combat* (Shield) · Heads-up Display (Tips & Tutorials, FPS Counter) |
| **ACCESSIBILITY** | Menu Navigation (Text Size, Notification Duration) · *Camera* (Camera Smoothing) |

## How it reuses what we have

- **Native rows come from the C++.** `tools/settings/build_schema.py` reads the `Add(...)` rows in `DaedalusSettings.cpp`
  (ids, kinds, defaults, ranges, choices, help text) and the layout tables in `DaedalusHero.cpp` (`PadButtons`, the
  thumbstick switch). Nothing native is retyped. `--check` fails if the schema and the C++ drift apart.
- **Audio defaults come from `data/settings/defaults.json`:** Main 80, Music 60, Effects 80.
- **Saved values use the native format:** a flat `{"Id": number}` object. Unreal keeps it in
  `Saved/Config/DaedalusSettings.json`; the web keeps it in localStorage `daedalus.settings`. The panel's
  *Copy settings* (X) gives a file Unreal reads unchanged.
- **New rows need a reader.** A new row is added only when something reads it. Each row lists its readers in
  `consumers`: `unreal`, `web-pad`, `realm`, `demo` or `settings-panel`.

## Modules (web)

| File | What it is |
|---|---|
| `static/settings/daedalus-settings.js` | `DaedalusSettings.create({schema})`: `get`, `set`, `nudge`, `on(id or "*")`, `resetTab`, `export`/`import`, `layout()`. `DaedalusSettings.mountPanel({settings, pad})` is the Halo-style panel. |
| `static/settings/settings-schema.json` | The web copy of the schema (written by the builder). |
| `static/controllers/daedalus-pad.js` | Controllers; with `settings:` it applies the Controller tab (see `docs/controllers.md`). |

**App-local rows.** An app can add its own rows to the shared tabs without changing the schema, using
`settings.extend({tab, section, rows})`. Kinds are `toggle`, `choice`, `slider`, `action` (a button run through
`settings.onAction(id, fn)`) and `info` (live text). Local rows are saved in the browser but kept out of `export()`,
so Unreal never sees them. `DaedalusSettings.addPadRows(settings, pad)` adds the controller rows every app shares to
Controller > Devices: *Connected* (what is plugged in and how it is read), *Teach Buttons* (BIND, shown as an
Infinite-style prompt over the tabs) and *Forget Taught Buttons*.

**The panel.** It works like Infinite's: a tab ribbon (LB/RB, Q/E or tap), sections of rows, a description pane, and
hints for A Change, Y Reset tab, X Copy settings and B Back. Up/down picks a row and left/right adjusts it; held
directions repeat. Mouse, touch, keyboard and every pad DaedalusPad knows all work. Rows are at least 48 px tall.
On a phone the description pane hides and each control drops under its label. Text Size scales the panel itself.

**Wired in today.**
- **Realm (`realm.html`):** Menu or F1 opens Settings, and View enters or leaves play. Rows read: Button Layout and
  Thumbstick Layout (the hero's own tables), look sensitivity/invert/acceleration (the hero's 200°/s rate),
  every dead zone, vibration, Field of View (converted from Unreal's horizontal angle), mouse sensitivity, Tips &
  Tutorials, FPS Counter and Notification Duration.
- **Prismheart demo:** it is a full-screen display with nothing else on screen. Settings opens from the title's OPTIONS,
  Esc on the title, F1, View/Select on a pad, or the gear on touch screens. Its own rows: Controller > Touch
  (Touch Controls: Auto/On/Off), Keyboard/Mouse > Keys (keyboard and arcade-encoder keys), Audio > Jukebox (Jukebox
  Monitor, Now Playing), and Gameplay > Saved Game (the journey saved at the inn, Erase). Audio drives the jukebox chain: Main, Music,
  Menu Music for the title cue, Effects, Voice (dialogue blips), Dynamic Range (Compressed lowers the limiter for
  night listening) and Inactive Mute. Also read: Menu Confirm Button and Tips & Tutorials.

## Native follow-ups (Unreal operator)

1. **Add the AUDIO tab** between VIDEO and GAMEPLAY, with the schema's rows and ids.
2. **Match Infinite's placement:** Button Layout and Thumbstick Layout belong in *General*, not *Layouts*, and
   Field of View in *Display*. `build_schema.py` prints these differences.
3. **Layout names.** Infinite's button layouts are Default, Legacy, Bumper Jumper, Recon, Button Puncher, Helljumper
   and Custom. Ours are Default, Bumper Jumper, Bumper Ninja, Boxer, Green Thumb and Recon (Halo 3/MCC names).
   Whether to add Infinite's set is Richey's call.
4. **The hero's sticks use a cross-shaped dead zone.** Each axis key (`Gamepad_LeftX`, `Gamepad_LeftY`, ...) gets
   its own axial `UInputModifierDeadZone`, so a slight diagonal loses its smaller axis: x = 0.10 under a 0.15 dead
   zone reads as straight ahead. Infinite uses a radial center dead zone, plus *Max Input Threshold* and an optional
   *Axial Deadzone*. Fix: in the Default and Southpaw layouts, map `Gamepad_Left2D`/`Gamepad_Right2D` with a radial
   dead zone. Legacy layouts split the sticks, so they keep 1D keys. The web module does it right
   (`tools/settings/settings_test.js`).
5. **Generic USB profile sticks** (`DaedalusControllers.json`) take their dead zone from `daedalus.Deadzone` when
   mapped. The menu's Center Dead Zone rows never reach them, and the thumbstick layout doesn't swap them.
6. **The realm widget (`SDaedalusRealm`) still hard-codes its keys.** Codex's `DaedalusPortalControls.h` fixes this,
   and the schema's Menu Confirm Button row maps to its `Layout::EastConfirm`.

## Tests

- `node tools/settings/settings_test.js`: 27 checks covering the store, dead zones, triggers, layouts, confirm and vibration.
- `python tools/settings/build_schema.py --check`: the schema matches the C++.
- `python tools/settings/panel_test.py DEMO_DIR`: the panel driven by pad, keyboard and touch, including the audio gains and phone width.
- `python tools/controllers/realm_pad_test.py URL`: the realm against a live server.
