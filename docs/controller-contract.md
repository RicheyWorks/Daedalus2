# Controller contract, version 1 (frozen)

`data/controllers/controller-contract.json` says what every Daedalus controller implementation must do. It holds the
rules and the vectors: inputs with the expected held actions. It is generated from `tools/controllers/contract_source.py`.
Version 1 is frozen. A change in behaviour is version 2, never an edit; `contract_check.py --check-frozen` enforces this.

**Implementations and how they are checked**

| Implementation | Runner | Vectors |
|---|---|---|
| Web: `static/controllers/daedalus-pad.js` (realm, Prismheart, any page) | `tools/controllers/contract_web.js` (node) | 12 |
| Native: `DaedalusPortalControls.h` (Codex's portal-controls translator) | generated C++, `g++ -std=c++20 -Wall -Wextra` | 10 |

`python tools/controllers/contract_check.py` runs both and prints the table. It takes the native header from main, or
from the branch `codex/portal-controller-intents-20261014` until that is merged. Today both implementations pass
everything they claim.

**What it pins** (the rules are in the JSON)
- **Confirm layout:** south or east, named by the layout, not the device.
- **Aliases:** a second source never releases an action the first still holds.
- **Digital stick:** one cardinal. Press at 0.55. Hold while the held direction's own signed part is above 0.40;
  0.40 exactly releases. Switch only on a lead of more than 0.10. A flick to the opposite side switches at once.
- **Release-all:** on focus loss, disconnect or exit. A held input then stays released until it is let go and pressed
  again.
- **Repeats:** an OS key repeat never presses twice.
- **Web-only analog rules:** a radial center dead zone with rescale (no cross-shaped dead zone), max input, axial
  dead zone, trigger inner and outer, the one-button rule (350 ms / 1200 ms), and no-start.
- **Coordinates:** stick y is up-positive, Unreal's convention. The web runner flips the browser's y.

**What writing it found in the web module:** three divergences from the native translator, now fixed. Running the
vectors against the pre-fix module fails exactly these three:
1. **Boundary:** at exactly 0.40 it held the direction; native releases.
2. **Flick:** it judged the held direction by absolute value, so a right-to-left flick kept reporting RIGHT.
3. **Re-grab:** after focus loss it re-read still-pressed buttons on the next sample; native waits for a fresh press.
