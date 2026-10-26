# Authored spell overlay continuation

This selectively ports the deterministic Drowse, Lull and Gust overlays from producer checkpoint `caf1b103f6cf5a3a66a3c718c139a7091b727b9d` onto continuation `5bda1a86a3c36c8b7fb665c1728d14a1fa680038`. The producer source is described by `docs/production/PRISMHEART-ULTRA-POLISH.md` and its r2 source pins. Its exact index SHA256 is `0c4ed03f9c66b38df28eaae45205e82de8b11bac002a2168ada01e526c91220f`; extracted-byte evidence remains in the task's `gearwright-producer-caf1/EVIDENCE.json`.

The existing magic effect records the caster/job, spell status/element and this cast's existing status result. The status chance/infliction expression remains unchanged; only its result is copied into the effect. An already afflicted target reporting MISS therefore receives no new success symbol. Chronoseer Drowse/Lull attempts have motes, with sleep/hourglass symbols only on the successful cast while the target remains alive and afflicted. Beastcaller Gust adds wind ribbons from caster to target. Other jobs/spells retain their atlas effects without these overlays.

The original atlas draw remains first, followed by the authored overlay, then the previously ported status pills and responsive HUD. The producer's missing-target guard skips null/undefined atlas entries instead of drawing a ghost effect above the party; target selection and spell costs are unchanged. Positions follow the current 320/256 party pose. The overlay clips to the battle-art region `(0,0,W,144)` and restores canvas state. Time and fixed indices produce the shapes; drawing consumes no combat randomness. The current battle tick advances effect time, so existing pause boundaries retain it.

No MP, target, status, damage, queue, chance, guard, reward or asset rule changes. Shared code, data, builder and native paths are untouched.

## Focused verification plan and limits

Review the production diff before checks. A bounded DOM-free fixture should exercise actual recruitment and casts with front-line fixture placement, status and action functions, effect ticking and rendering with canonical Quill/Fennick data and canonical nonmatching jobs. ORDER already has focused coverage in the Folly continuation. Compare mechanical outcomes and RNG counts against a controlled metadata-only prior variant. Cover Drowse/Lull success, chance miss, preexisting status, immunity/dead or removed target cases, actual Gust damage and nonmatching jobs; at both widths check atlas/overlay/pill order, deterministic draw commands, clipping, state restoration, no draw mutation/RNG and paused effect time. Compile the full inline script without execution and run only justified directly affected checks, serially under Node's 128 MiB heap cap.

This is source/offline verification. It does not certify rendered asset quality, a browser playthrough, physical device behavior, native integration or runtime acceptance.

## Offline results

The single focused `spell_fx_test.js` passed 28 groups with Node's heap capped at 128 MiB, including full inline compilation without execution. It compares actual recruited casters' mechanical outcomes/RNG counts to a controlled metadata-only prior action variant, using direct front-line fixture placement. It covers cast-specific success/miss/preexisting status, immunity/cure/death, Gust damage, canonical Portal job exclusions, both widths, responsive points, deterministic commands, clipped/restored canvas state, no draw mutation/RNG, atlas/overlay/pill/HUD order, paused age and the existing 0.65-second expiry.

The existing no-live-foe action guard was verified to spend no MP or RNG and create no effect. Separate defensive null/undefined render fixtures verify the producer atlas guard and reproduce the former ghost frame when the guard is removed; no reachable crash or gameplay-progress fix is claimed. Controlled omitted-overlay and false-success variants also fail the same invariants.

The first run found one fixture setup omission: `dlg` was absent from the VM's current battle-frame context. Adding `dlg: null` allowed the focused rerun to pass; production remained unchanged. No old suites, browser, assets, shared module or native runtime were executed.
