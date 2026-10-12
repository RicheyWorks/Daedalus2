# ADR-043: The Ghost, a hover bike that shoots

Status: accepted, 2026-10-12

## Why

"Players shoot and also drive the vehicles to be able to shoot. Very important mechanic." Halo's Ghost is the
model: a fast one-seat hover bike that steers where you look and fires twin guns.

## Decision

`ADaedalusGhost` (APawn, C++ in DaedalusLink, no assets):

- **Body:** a box hull for collision and a blocky purple frame with side pods, a seat, glowing intakes and two
  guns; it banks into turns and strafes.
- **Getting on and off:** Interact (X / E) within `InteractReach` (350 cm) of a free Ghost mounts it: the hero is
  hidden, carried and his controller possesses the bike. Interact again sets him down beside it and gives him
  back. `SpawnVehicle()` on the hero places one 4 m ahead on the ground.
- **Driving:** left stick / WASD throttle and strafe; the bike turns toward the camera's yaw at 240°/s; LB / LT /
  Shift boost (1900 → 3200 cm/s). It hovers 110 cm up on a down trace with a spring, falls off island edges, and
  is put back on its last ground if it drops 30 m below it.
- **Guns:** RT / left mouse, alternating left and right about twelve bolts a second, heat and overheat like the
  blaster. Bolts aim at whatever is under the screen centre, so the hero's reticle is right. 12 damage; kills
  credit the rider's Kills and Exp.
- **Look settings:** the bike reads the hero's console variables, so invert, sensitivity and look rate carry over.
- **Harness hooks:** `Mount`, `Dismount`, `Drive(forward, right, boost)`, `FireGuns`, and the record
  (ShotsFired, Hits, Heat, Velocity, bGrounded, Rider).

## Held

More seats (a Warthog-style buggy with a gunner), vehicle health and hijacking, and sound.
