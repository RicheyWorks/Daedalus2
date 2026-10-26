# Commons collect-and-plant R7

Open the saved Commons and play normally when desired. Near the entrance, follow
the continuous amber approach. The small right-hand activity panel shows the
current objective; within 2.4 m, E collects the seed pouch, then E at the round
planter plants the poppy. Completion reads **Flower planted**. The chart and its
Explorer Log remain independent. Existing E input is shared without consumption;
paused/settings/field/dialogue states refuse the activity action.

The owned Actor Blueprint loads only `Daedalus_LanternCommons_Garden_v1`, version
1 with stage 0..2. Each transition saves before advancing the local state. A failed
save keeps the old stage and permits retry; malformed/unavailable saved state is
held rather than overwritten. This is a built mechanism, not runtime persistence
acceptance. No Play or save/reload loop was run for this production batch.

EventGraph: BeginPlay calls InitGarden, creates WBP_CommonsGarden, adds it at
ZOrder21, enables non-consuming E input and a 0.2-second RefreshGarden timer.
E Pressed calls TryGardenInteract. EndPlay clears its own timer, disables its input
and removes only its widget. The four authored function recipes are adjacent DSL
files. The three saved Blueprint/UMG assets are in Content/.../GardenActivityR7.

The existing C++ Usable methods are not Blueprint events, Starbloom is harvest
only, and the current private Hero save has no plant field. This small native
Blueprint/SaveGame activity fills that demonstrated gap without changing shared
inventory, save format, progress or native code. It is not a general planting API.

The approach is 14.5 x 2.4 m. Eight scattered R6 stones and the identified legacy
CourtyardInstructions text are hidden, not deleted. The 104 x 105 m continuous
physical ground, 273 floor instances, prior gardens, controls and peaceful rules
remain. New scenery is NoCollision above the unchanged physical floor.

Images: ../images/plant-r7-arrival.png and ../images/plant-r7-garden.png are actual
editor captures, not runtime HUD or benchmark acceptance. The environment still
needs substantial visual refinement, especially ground repetition.

Pond intake: reviewed v2 pagination code is locally integrated. Native page 0
refused the exact protected-context binding twice, including one new attempt after
an intermediate matching readback. No completed page/index/queue/import exists.
The helper checks context both before and after loads, so metadata load count is
unknown. See pond-intake-status.json; do not fabricate provenance or weaken checks.
