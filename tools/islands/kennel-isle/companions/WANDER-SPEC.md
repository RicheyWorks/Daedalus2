# Wild pets: wander behaviour (spec + Blueprint/BT plan) — art-master-flex
Targets: every actor tagged `AMF_Wild` in /Game/AMF/Maps/WildBiomes_AMF_Pets (static meshes today).

## Behaviour
States: Idle (3–8 s, small head turn) → Wander (pick point 3–12 m from **home**, NavMesh-reachable, walk 0.8–1.4 m/s) → Graze/Sit (4–10 s) → loop. Leash: never > 20 m from home (home = spawn point). Flee: player within 4 m and pet `size` SMALL → run 6–10 m away at 2.5 m/s, then resume. Night (day/night #11): 60% of pets go to Idle near home.
Per-species flavour via a DataTable row `DT_WildPet` {Mob, WalkSpeed, WanderRadius, Flees, IdleAnimHint}.

## Blueprint plan (no skeletal meshes yet)
1. `BP_WildPet` (Pawn): root StaticMesh (or Body + attached parts), `FloatingPawnMovement`, `AIControllerClass=AIC_WildPet`, vars Home, RowName.
2. `AIC_WildPet`: RunBehaviorTree `BT_WildPet`; Blackboard keys Home(Vector), Target(Vector), Threat(Object).
3. `BT_WildPet`: Selector[ Sequence(Decorator Threat set → Task FleeFrom), Sequence(Task FindWanderPoint EQS/GetRandomReachablePointInRadius(Home,R) → MoveTo → Wait 4–10), Wait 3–8 ].
4. Fake gait while static: bob the Body 2 cm at 4 Hz and ±4° roll while velocity>0 (Timeline or Tick).
5. Swap step: a one-shot editor script converts AMF_Wild StaticMeshActors → BP_WildPet with the same mesh/transform (tags kept).
Needs: NavMeshBoundsVolume over each Wild Biomes area (unreal-team / pythagoras).
