(event EventBeginPlay
  (bind _returnvalue (UserInterface|CreateWidget "/Game/CodexToolEvaluation/PlayableCourtyard/20261022/R1/WBP_LanternObjective.WBP_LanternObjective_C" (Game|GetPlayerController 0)))
  (UserInterface|Viewport|AddToViewport _returnvalue 20))

(event EventEndPlay (EndPlayReason)
  (bind _foundwidgets (Widget|GetAllWidgetsOfClass "/Game/CodexToolEvaluation/PlayableCourtyard/20261022/R1/WBP_LanternObjective.WBP_LanternObjective_C"))
  (for _array_element _foundwidgets
    (Widget|RemoveFromParent _array_element)))

(event Collision|EventActorBeginOverlap (OtherActor))

(event EventTick (DeltaSeconds))
