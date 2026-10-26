# ADR-041: Menus and settings, the Halo Infinite way

Status: accepted, 2026-10-12

## Why

Richmond plays on an Xbox Elite Series 2, GameSir and Razer pads, and a Razer 8K mouse. He likes inverted look,
and he likes Halo Infinite's menus. The hero (ADR-040) had controls but no way to change them in the game.

## Decision

The menus are built in Slate from C++, so they need no assets and a harness can drive them. They follow Halo
Infinite's flow, which we researched (sources below).

- **Menu** (the three-line button), or **F1** / **F10**, pauses the game and opens the **Game Menu**: Resume,
  Settings, Respawn. Nothing else shows until you choose Settings.
- **Settings** has a tab ribbon, switched with LB / RB or Q / E. Its tabs and sections:

  | Tab | Sections |
  |---|---|
  | Controller | General; Movement & Aiming; Sensitivity & Acceleration; Move Thumbstick; Look Thumbstick |
  | Keyboard/Mouse | Movement & Aiming; Sensitivity |
  | Video | Camera |
  | Gameplay | Combat |
  | Accessibility | Camera |

  Rows sit on the left and the selected row's explanation on the right, with button hints along the bottom.
  Left / right adjusts a row, A flips a toggle, Y resets the tab and B goes back a page. Every change applies at
  once and is saved to `Saved/Config/DaedalusSettings.json`.
- **View** (the two-box button), or **Tab / M**, opens the **Field Menu**, Halo's Campaign Menu, with four tabs:
  - **Map:** a TacMap of every island chunk, with the hero as a marker that turns with him.
  - **Hero:** his record.
  - **Controls:** the layout.
  - **Social:** a placeholder for friends, party and voice, which arrive with online play.
- **No placeholder settings.** Audio and Upgrades tabs wait until the game has sound and upgrades.

## Proven live (UE 5.8.3)

The harness drove the menus through `MenuInput` and `FieldInput`:
- Pause, then Settings, tabs back and forth, and rows down.
- Inverted look set to 1: the console variable read 1, and the setting was saved.
- Back to Pause, and closed again.
- The Field Menu's TacMap drew 99 chunks, and its tabs switched.

## Next

- Camera views: first person with a centred reticle (Halo), over-the-shoulder with a shoulder swap (Gears),
  and the current chase camera.
- Shooting.
- Vehicles with mounted guns.
- Friends, party and team voice (Epic Online Services, or the Daedalus server's presence).

## Sources

- [Guide to Halo Infinite Game Settings](https://support.halowaypoint.com/hc/en-us/articles/4407649252116-Guide-to-Halo-Infinite-Game-Settings)
- [Halopedia: Halo Infinite control schemes](https://halopedia.org/HINF:Control_schemes)
