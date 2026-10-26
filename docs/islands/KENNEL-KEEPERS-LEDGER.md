# Kennel Isle in Unreal: the Keeper's Ledger (contest G102)

Source-only Unreal binding for the Kennel Isle care rules. Owner: art-master-flex.

## Story: the Keeper's Ledger

When the arks came down on the shattered planet, the kennel keepers kept one book per hound: what it ate,
what it drank, which tonic it was given, how many throws it fetched, and what it would do when called.
The ledger is why a hound raised on Kennel Isle answers the same way every time the same day is replayed:
the keepers wrote the day's luck down before the day began.

> Keeper Wren: "A hound remembers every bowl you forgot. Write it down, then close the day."
>
> Keeper Wren (a drill refused at Pup stage): "Too young for that. Come first; the rest waits for size."
>
> Keeper Wren (tier rises): "There. It looks at you before it looks at the gate."

In code, the ledger is `FPet` plus its seeded rolls: the spurt roll for a day and each drill's roll come from
the pet's name, the day number and a salt, so the same pet replays the same days on every machine.

## What is in it

| File | Role |
|---|---|
| `engines/unreal/DaedalusLink/Source/DaedalusLink/Public/DaedalusKennelPetCore.h` | Engine-free pet state: once-a-day care, `EndDay` (G65 growth with seeded spurt roll + G37 bond step), drills (stage gate, tier gate, seeded roll vs G61 odds), `Bond_NN` / `CareDays_NN` tag parsing, status line. |
| `.../Public/DaedalusKennel.h`, `.../Private/DaedalusKennel.cpp` | `UDaedalusKennelPet` component (Blueprint care / end-day / drill, delegates for day end, tier change, stage change, drill) and `UDaedalusKennelSubsystem` (adopts every `AMF_Companion` / `AMF_Wild` actor at BeginPlay; `EndDayAll`). |
| `engines/unreal/core-test/kennel_pet_core_test.cpp` | 44 checks, gcc (ASan/UBSan) and clang in the Engines workflow. Proves `EndDay` equals the G84 `StepBond` + `GrowCareDays` for a 90-day script, so the binding inherits the Java parity of `DaedalusKennelCore.h`. |

All rules stay in `DaedalusKennelCore.h` (G84, parity-tested against Java). The UE files only forward and broadcast.
No network, no credentials, nothing saved yet.

## Console (PIE)

```
daedalus.kennel.status [Pet]
daedalus.kennel.care feed|water|tonic [Pet]
daedalus.kennel.care fetch <Catches> [Pet]
daedalus.kennel.endday
daedalus.kennel.drill come|stay|fetch|guard|rescue [Pet]
```

`Pet` matches part of the actor name (case-insensitive); omitted means the first pet (companions first).

## Rules recap

- Care: feed, water and tonic count once a day; fetch catches add up (99 a day max; the bond rule caps the gain at 5).
- End of day: neglected (not fed or not watered) means no growth and -11 bond; otherwise +1 care-day, +1 more when
  the pet had a tonic or fetched and the seeded roll is under 15, and the G37 bond gain.
- Drill: Newborn none, Pup come, Juvenile come/stay/fetch, Adult all, Elder all but rescue; then the tier must
  allow it (Familiar come; Loyal stay, fetch; Devoted guard, rescue); then roll < clamp(40 + bond/2 - difficulty, 5, 95).

## Next (UNREAL-QUEUE, behind GATE)

Compile in the UE build, PIE run of the console script above on the Kennel Isle map, pet panel widget bound to
`GetTier` / `GetStage` / `DrillSuccessPct`, and save/load of `FPet` with the island save.
