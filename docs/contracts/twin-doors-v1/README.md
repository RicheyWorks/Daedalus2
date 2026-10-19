# TWD 1: Twin Doors riddle (twin-doors-v1)

Text, LF line endings, invariant locale. Contest gap G04 (Labyrinth LAB07).

    TWD 1
    doors <seed> <difficulty 0|1> <safeDoor 0|1> <liarGuard 0|1> <lowMeansYes 0|1>
    ask <guard 0|1> <DIRECT|OTHER_GUARD|EMBEDDED|SELF> <door 0|1> <LOW|HIGH> <deduced 0|1|->
    ... (16 ask lines: question x guard x door)
    end

- RNG: SplitMix64 seeded with `seed ^ 0x54574431`. Draws in order: safeDoor u%2, liarGuard u%2,
  then lowMeansYes u%2 at difficulty 1 only (difficulty 0: low bell always means yes).
- One guard always tells the truth, the other always lies. Guards answer yes/no with a bell:
  LOW = D3 146.832 Hz, HIGH = A3 219.999 Hz, gain 0.5 (ear rules: soft, no bright tones).
- Questions about door d:
  - DIRECT "Is door d safe?"
  - OTHER_GUARD "Would the other guard say door d is safe?" (always the opposite; solves only when bell meaning is known)
  - EMBEDDED "If I asked you whether door d is safe, would you ring the low bell?" (LOW iff d is safe, for every world)
  - SELF "Are you the truth guard?" (both answer yes; teaches the yes-bell at difficulty 1, says nothing about doors)
- `deduced` is what a careful player can prove from that one answer: the safe door if every world
  consistent with it agrees, else `-`.
- Game rule: one question to one guard, then one door. Wrong door = puzzle resets with a new seed.

`riddles.twd` = seeds {1, 42, -7, 0x5EEDCAFE, Long.MIN_VALUE} x difficulty 0-1.
