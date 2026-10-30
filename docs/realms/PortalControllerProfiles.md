# Portal controller profiles and prompts

Status: **UNVALIDATED, source-only complementary module with no default wiring.**
No tests, builds, services, input/settings changes, native installation or editor
work were performed. Actual controller model and hardware compatibility remain
**UNVERIFIED**. BRICKS draft PR148 is preserved as a separate source feature.

The new engine-free `DaedalusPortalControls.h` translates remappable physical
keys and movement axes into the Portal core's existing seven buttons. It also
provides matching prompts with optional Nintendo-style labels and an east-face
confirm layout. The host can use it through the existing `Realm::Press` and
`Realm::Release` methods without adding gameplay commands or a second authority.

## Canon and actual source gap

The inspected [realm guide](../REALMS.md), [ADR-052](../adr/ADR-052-portal-realm.md),
[Portal buildout](PORTAL-BUILDOUT.md), [Sol Reach](SolReach.md) and Sol Reach runtime
note establish Portal as the existing original 8-bit adventure. Its party, keys,
chests, battles, dialogue, inventories, saves and seed-generated maps remain
authoritative. Sol Reach is a district inside Portal. This module defines no new
realm id, origin, world generator, progression rule, inventory or reward.

At fresh main `170790d0`, `SDaedalusRealm::MapKey` hardcodes keyboard/D-pad
directions, bottom-face confirm (`Button::A`), right-face back (`Button::B`) and
the right special/menu key (`Button::Start`). Its analog handler chooses one
cardinal direction from the left stick. The separate 3D hero EnhancedInput
profiles in `DaedalusControllers.json` do not remap this widget's hardcoded path.
Shared Hero, Slate widget and input/settings files belong to the existing owner
and are untouched here.

The core stores one held boolean per direction. Consequently a release from one
alias can stop another alias that is still held. This optional translator tracks
physical sources together, emitting a logical release only after the last
digital/analog source releases it. The core still owns walking timing and every
interaction outcome.

## Original, provisional design choices

- **Separate layout and labels.** `ExistingBottomConfirm` retains the widget's
  current pad positions. `EastConfirm` uses east for confirm and south for back.
  `Position`, `NintendoLabels` and `XboxLabels` control display independently.
  Nintendo labels show A east, B south, X north and Y west. A user can keep south
  confirm while selecting these labels; that then correctly prompts B south for
  confirm. Labels do not identify a physical device or change key translation.
- **Complete atomic remaps.** A profile contains at most 64 unique physical-key
  bindings. `Remap` and `Unbind` validate a candidate before replacement and retain
  a route to all four directions, confirm, back and menu. Explicit observed key
  names/custom labels can describe a generic controller without guessing USB
  button numbers. Keyboard, pad and observed families select preferred prompts.
- **Movement tuning.** Configurable X/Y key names, swap, inversion, press/release
  thresholds and direction bias turn analog input into one existing cardinal
  button. The proposed defaults are 0.55 press, 0.40 release and 0.10 switch bias.
  A held direction stays active above release until a competing direction passes
  both press and bias. Values clamp to [-1, 1]; nonfinite input releases this
  adapter's stick source. Both empty axis names disable analog translation.
- **Lifecycle releases.** Successful profile replacement returns releases for
  the old profile. `ReleaseAll` clears owned input on focus loss, disconnect or
  portal exit. Releases preserve other held aliases within this translator.
- **No simulated repeats.** Duplicate key downs and OS repeats are consumed
  without repeating a core press. Field walking already repeats in `Realm::Tick`;
  menu/actions retain the core's existing press semantics.

These choices implement the user's controller-first direction in a reusable
source seam. They are not claims of current native adoption or exact-controller
support. No art, borrowed game names/characters or trademarked imagery is added.

## Prompts follow the actual game context

`ContextOf` reads public `IsLoaded`, `TopBox` and `CurrentMode`. Message/list/status
boxes take precedence over battle phase. It hides prompts for unknown/unloaded
contexts. It does not parse debug text or infer context from `Busy`, which groups
several different states.

| Context | Directions | Confirm/A intent | Back/B intent | Menu/Start intent |
|---|---|---|---|---|
| Title | hidden | Continue | Continue | Continue |
| Field | Move | Interact | Commands | Commands |
| Message | hidden | Continue | Continue | hidden |
| Status | hidden | Close | Close | hidden |
| Field command grid | Choose | Select | Back | hidden |
| Lists and battle command | up/down only | Select/Confirm | Back/Undo choice | hidden |
| Battle target | Choose | Confirm target | Back to commands | hidden |
| Battle intro | hidden | Continue | Continue | hidden |
| Battle playback | hidden | Advance faster | Advance faster | hidden |
| Battle ending | hidden | Continue when ready | Continue when ready | hidden |

The prompt's `Key` and `Glyph` come from the selected binding, so a remap changes
both translation and presentation. These texts reflect the existing command
semantics: B opens commands in the field and advances messages; it is not a
universal cancel or exit key. Start does nothing in menus/messages/battles. A/B
in a message can reveal typing or advance/close it. Public inspection does not
expose typing/page readiness, so the prompt conservatively says Continue.
The actual exit remains walking onto the existing portal and completing its
message. Existing party and battle commands remain in `DaedalusRealmCore`.

## Opt-in host seam

The following is illustrative source usage, not an executed integration:

```cpp
namespace PC = daedalus::portal_controls;
PC::Translator Controls;
PC::Profile Proposed = PC::Profile::Preset(PC::Layout::EastConfirm,
                                         PC::Labels::NintendoLabels);
std::vector<PC::Edge> Releases;
std::string Error;
if (Controls.Replace(Proposed, Releases, Error))
    PC::Translator::Forward(Game, Releases);

// physicalKey is the actual FKey name delivered by the existing owned host.
const PC::Dispatch Event = Controls.KeyDown(physicalKey, isRepeat);
PC::Translator::Forward(Game, Event.Edges);
// Use Event.Consumed for the host's handled/unhandled decision.
const PC::Prompt Confirm = PC::DescribePrompt(Controls.GetProfile(),
    daedalus::realm::Button::A, PC::ContextOf(Game), PC::Family::Pad);
```

The same host forwards `KeyUp`/`Axis` edges exactly once. For an accepted remap,
forward the returned releases before processing new input. Forward `ReleaseAll`
on focus loss/disconnect/exit. If the host resets input when a game context
changes, use the same release path; do not preserve swallowed held input across
such a reset. The host retains focus ownership, controller selection, device
disconnect signals, calibration, settings storage/localization and any existing
input injection facility. Use one translator per active local focus session.

This module is unused by the existing Slate widget. It creates no mappings,
raw-device listeners, config files, automatic input hooks or global settings.
The widget's current keyboard/pad behavior remains the fallback. Future native
wiring belongs to the existing shared input owner and is a separate task.

## Source review and deferred acceptance

Manual review inspected the actual widget mapping, core Press/Release semantics,
public context queries and current documented 3D profile contract. Independent
source review identified and corrected a stick hysteresis case where a competing
axis below press threshold could release a still-held direction. No executable
validation is claimed for that correction or the rest of this module.

Later acceptance must compile the actual header/native host, verify layout and
prompt consistency after remaps, test actual observed device axes/buttons,
aliases and focus/disconnect releases, cardinal/tie/hysteresis behavior, complete
profile refusal, and title/menu/dialogue/battle transitions. It must show actual
native movement, menus and actions with the user's real controller. Deferred
tests, source code and presentation labels do not prove hardware compatibility
or gameplay delivery.
