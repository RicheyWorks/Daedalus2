(event EventBeginPlay)

(event EventDestroyed
  (Development|PrintString "LANTERN CHART COLLECTED!  Great exploring - keep roaming the Commons." true true "(R=0.000000,G=0.660000,B=1.000000,A=1.000000)" 18.0))

(event Collision|EventActorBeginOverlap (OtherActor))

(event EventTick (DeltaSeconds))
