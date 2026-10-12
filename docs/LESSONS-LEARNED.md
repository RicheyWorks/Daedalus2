# Lessons learned

Lessons that held up in practice and should shape the next piece of work. Each one has the evidence
behind it. Newest at the top of each section.

## Design

### Modular, portable design wins over the long run (2026-10-11)

> "Yes, modular design philosophy wins the long run." (RicheyWorks)

**The lesson.** Modularity pays when the boundaries are in the right places, and the right places are
found by reusing a piece for real. Split too early, before the seams are known, and you pay for
interfaces nobody uses.

**Why it worked here.** Daedalus' boundaries were proven by moving things. The maze engine went into a
2D web well, then a 3D realm, then Blender, then Unreal Engine 5. Each move tested whether the seams
held. That is why the game (ADR-036 on) arrives quickly: each new feature mostly composes parts that are
already tested.

**Two habits keep it winning:**
1. **Guard the boundaries with tests, not intentions.** Agents (Claude, Grok, anyone) take shortcuts
   across a boundary that nobody checks. Here:
   - `PortabilityTest`: `daedalus-core` imports only the JDK and itself.
   - The C++ mesh core's parity tests against the Java mesher (`engines/unreal/core-test`).
   - The Unreal import's own verifier, which checks the result against the manifest (`verify_judge_test.py`).
2. **The contract is the product.** These outlive any one engine:
   - the World Package format
   - `/api/v1/...`, including the published rules such as `/api/v1/hero/rules`
   - the shared C++ core

   Keep them stable and versioned, and the presentation layer (three.js, Unreal, Blender, VR) can change
   without touching the game.

**The shape to keep:** Java engine (rules, plain JDK) → stable interface (data and HTTP) → engine adapter
(DaedalusLink, the realm, Blender) → gameplay. Platform code belongs in adapters, never in the core.

## Verification

### Make a tool check its own work, and prove the check can fail (2026-10-11)

The Unreal import used to report only "done". Now it reopens the level and checks it against the
manifest, and each check prints PASS or FAIL. The judging logic is pure Python, so it is tested without
Unreal: each kind of broken project fails exactly the check that names it (13/13). A check that cannot
fail proves nothing.

### Wait on outcomes, not timers (ADR-037)

In the browser harness, software WebGL runs at about 5 frames a second with six pages open. Checks that
waited a fixed time (a 1.3 s jump, a knockback measured after 300 ms, one thrust after 450 ms) failed
when frames came late. Physics only advances when a frame arrives. The harness now waits until something
happens (a landing, a numbered thrust that met a foe, the knockback settling), as a player would.

## Portability across machines

### What runs here may not run on the user's PC (2026-10-11, `setup-unreal.ps1`)

Every one of these passed in the Linux sandbox and failed on Windows:
- **Windows PowerShell 5.1 and wildcards.** A wildcard in the middle of a `-Recurse` path matches
  nothing there, so an old server jar looked current. The server it ran had no World Packages.
- **UE 5.8 and MSVC.** UE 5.8 refuses MSVC 14.40–14.43, and the installed VS 2022 had 14.41.
- **The VS installer and `--passive`.** It refuses `--passive` without elevation (exit 5007).
- **A plugin that never loaded.** It declared `"EngineVersion": "5.4.0"`, so UE 5.8 skipped it silently.
- **Unbuilt plugins.** The editor won't open a project that enables a plugin that isn't compiled yet.

**The lesson.** A setup script must look, report what it found, and recover on the real target. Run it
there early, and read its full output.
