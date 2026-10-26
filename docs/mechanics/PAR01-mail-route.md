# PAR01 Mail Route (contest gap G14)

Owner: hephaestus. Core: `daedalus-core/src/main/java/com/daedalus/world/parcels/MailRoute.java`, tests in `MailRouteTest.java`. Source only; the Unreal binding waits in BOARD\UNREAL-QUEUE.md.

## Story tie-in
**Postmaster Grue** runs the Parcels delivery board, which is the realm's quest system (REALM-CASTS.md). Each day, the **Courier** hero takes a satchel of letters out from the helipad on the plaza: the crossing of the middle roads, on gate 0's line. Some letters are **Express**. Sometimes the **Lost-Letter Ghost** leaves a letter at a mailbox; carrying it back to the helipad lets the helicopter fly it to another realm, which is the Ghost's cross-realm ask. The route reconnects isolated plots without anyone cutting across a claimed plot (deeds, ADR-027).

## Rules
- `MailRoute.day(seed)` gives 6 to 10 letters for distinct claimable plots of `DistrictOps`. About 1 in 4 letters is Express, and about half of all days also have one Ghost pickup.
- Each plot's **mailbox** stands on the centre line of the north-south road its side of the block faces, level with the plot's middle.
- **Boundary guidance:** `waypoints(a, b)` lists the corners of the shortest street path, and `streetCubes(a, b)` gives its length. Every path stays on road centre lines, so it never enters a plot. A delivery made from inside any plot returns `TRESPASS`.
- **Par:** the exact optimal tour (Held-Karp), from the helipad through every mailbox and back, at 5 cubes a second. Express deadlines are the par tour's arrival time x 1.25 + 10 s, so every day is solvable on time.
- **Session (host-authoritative):** each letter is delivered once, within 2 cubes of its mailbox. An Express letter past its deadline is `LATE`. `finish` only counts at the helipad.
- **Stamps:** 1 per letter, +1 per Express letter on time, +2 for returning the Ghost letter.
- **Medal** (every letter delivered): GOLD up to 1.10 x par, SILVER up to 1.35 x par, BRONZE up to 1.75 x par.

## Tests
`MailRouteTest` has 9 tests:
- The helipad sits on the plaza.
- All 60 mailboxes are on the street beside their plots.
- Street distance is symmetric, obeys the triangle inequality and matches its waypoints, and the waypoints never cross a plot.
- Days are seeded, with distinct real plots.
- Par equals brute force on 12 days of 8 or fewer stops.
- 200 days are solvable on time for GOLD.
- The medal bands hold.
- A slow round goes late and loses the medal.
- The reach, trespass, deliver-once and finish rules hold.

## Unreal later (UNREAL-QUEUE)
- Mailbox props at `mailbox(n)` cells.
- A delivery-board UI that reads `day(seed)`.
- A street arrow that follows `waypoints`.
- A Use-key delivery that calls `Session.deliver`.
- The Ghost letter glows until it is returned to the helicopter.
