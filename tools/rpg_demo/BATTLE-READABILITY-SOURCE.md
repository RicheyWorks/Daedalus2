# Battle readability source continuation

This selectively ports the authored status pills and party HUD from authenticated producer checkpoint `caf1b103f6cf5a3a66a3c718c139a7091b727b9d` onto continuation `ee616996e6211d105859461ae86a6e46e3e88bf3`. The source is documented by `docs/production/PRISMHEART-ULTRA-POLISH.md` and the r2 source pins. The exact producer index SHA256 is `0c4ed03f9c66b38df28eaae45205e82de8b11bac002a2168ada01e526c91220f`; extracted-byte evidence is retained in the task's `gearwright-producer-caf1/EVIDENCE.json`.

## Authored change and responsive adaptation

Enemy status pills paint after every sprite and atlas spell effect, preserving their existing status rotation and alive-only rule. Each pill uses the producer's dark 24-by-9 backdrop and colored leading edge. The party window gains PARTY/HP/MP headings, a selected-command row and separated name/status/stat columns. Low HP retains its warning text and uses the authored warning gauge color.

The original producer assumed 320 pixels. This port keeps the current 320/256 split, command window, three-option chooser footer and queued-summon information. Party names display uppercase before clipping to nine/seven characters; the command actor name is similarly bounded to nine/five in its existing position. Numeric slots show exact values through 9999/999 and then explicit `9999+`/`999+` overflow text; stored and combat values are unchanged. Headers sit at y147, rows at y159 plus 15 pixels, and gauges finish above the bottom border. Ordinary four-foe status pills finish by pixel143, above the command windows.

The current hit-flash pause guard, lifecycle simulation gate, party/sprite positions, targeting, resources, statuses, damage and randomness remain unchanged. No bespoke spell overlays are part of this slice. Shared code, data, builder and assets are untouched.

## Focused verification plan and limits

Review the production diff before checks. A bounded DOM-free canvas spy should call actual `statusPill`/`drawBattle` with canonical parties, statuses, four-foe formations and existing atlas effects at both widths. Verify paint order, status rotation/alive rules, selected rows, KO/low-HP presentation, column/font/bounds, long restored names and safe-integer overflow display, chooser/footer preservation and draw purity (allowing only the existing active hit-flash countdown). Confirm paused flashes do not tick. Use controlled former render variants to demonstrate the old occlusion/unlabeled-column gaps. Compile the complete inline script without executing it, then run only directly affected drawing fixtures with actual helper dependencies, serially under Node's 128 MiB heap cap.

This is source/offline verification. No browser screenshots, generated assets, physical device, native editor or runtime acceptance are certified by this continuation.

## Offline results

Serial Node checks with the heap capped at 128 MiB passed on their first runs: `battle_readability_test.js` 15 groups and `battle_choice_info_test.js` 19 groups. The full inline script compiles without execution. The canvas spy covers the real four-foe formation, every authored status/rotation, post-art paint order, KO/low-HP/selection, canonical start/quest values, accepted long names and safe-integer values, both widths, unchanged target cursors/chooser footer, active flash countdown and paused draw purity. Controlled former render variants fail the same invariants.

The three existing fixtures that extract `drawBattle` directly now include the actual `statusPill` source; their assertions were unchanged and those suites were not rerun. No setup failure or production defect occurred during this verification. No broader tests, browser, assets, shared module or native runtime were executed.
