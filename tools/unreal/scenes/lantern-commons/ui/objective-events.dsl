(event UserInterface|EventPreConstruct (IsDesignTime))

(event UserInterface|EventDestruct
  (Utilities|Time|ClearTimerbyFunctionName self "RefreshObjective"))

(event UserInterface|EventConstruct
  (Utilities|Time|SetTimerbyFunctionName self "RefreshObjective" 0.2 true true))

(event UserInterface|EventTick (MyGeometry InDeltaTime))
