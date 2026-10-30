# Stillwater plants R8

Twelve already-admitted pond plants now form three small shoreline groups:
six Frogbit, three PinkLily and three WaterLily, all actor scale1. The middle
water stays open. New components are Movable/NoCollision over the existing solid
ground; routes, chart and garden activity assets are unchanged. The owned map is
saved cleanly with734actors. No import, Play or repeated qualification loop ran.

The measured surface is25.1cm high. Authored plant origins are at25.25cm: source
Z0 denotes the waterline, including lily roots below it. Do not bottom-snap the
negative roots. Exact positions and asset admission history are in build.json
and ../pond-native/. The shared palette lacks pre-enabled instanced-mesh usage;
ordinary actors preserve it instead of changing the shared original material.

Actual editor images are ../images/stillwater-r8-pond.png and
../images/stillwater-r8-garden.png. The new groups and open spacing are visible;
these are not runtime or visual-benchmark acceptance. Repetitive floor tiles,
dark perimeter and the bright/pale look still need production improvement.

Recommended next real feature: a friendly gardenkeeper restoration activity
using existing contextual E interaction, objective UI and local garden progress
conventions. Give the garden a useful goal rather than starting another tool
qualification or scenery-only pass. Preserve the player's current progress.
