# Companion follow + fight AI (Cane Corso and any pet in the party of 3) — art-master-flex
Data: stats from corso-rules.json / companion-rules.schema.json (hearts, damage, magicMeter, speed, loyalty, gear mods applied first).

## Follow
Slot points behind the hero: 2.5 m back, ±2 m sideways (slots 0..2). Walk if dist < 6 m, run (speed×1.8) if > 6 m, teleport to slot if > 35 m or no path for 3 s. Idle anims cycle sit/idle/play when hero still > 5 s.

## Fight
Engage when the hero attacks or takes damage from a foe within 15 m, or a foe comes within 6 m of the hero (Guard stance at loyalty ≥ 80).
Target pick: foe hitting the hero > lowest-HP foe in 10 m > nearest. Bite (melee 1.6 m, cooldown 1.2 s / speed, dmg = damage + gear), Guard (blocks 1 hit, 6 s cd, plays `guard`), Hit reaction `hit`, Faint at 0 hearts (`faint`, revive 30 s or with wound_salve), `victory` when area clear. Retreat to slot when its hearts < 25% unless loyalty ≥ 95 (Corso: "last stand").
XP: per foe defeated → split into life/attack/magic tracks per costs tables; stage-up per `stages`.

## Unreal build
`BP_Companion` (Character, CharacterMovement) + `AIC_Companion` + `BT_Companion`:
Selector[ Fainted→Wait, InCombat→Sequence(ChooseTarget(EQS), MoveTo(1.4 m), Bite/Guard), Follow→MoveTo(slot, acceptance 0.8 m), IdleFlavor ].
Blackboard: Hero, Slot, Target, InCombat, Hearts. Perception: AIPerception sight 15 m on foes (`Mob_` with tag Foe).
`UCompanionStats` (ActorComponent) loads the rules JSON row by kind id; gear via `EquipGear(id)` reading `gear` mods.
