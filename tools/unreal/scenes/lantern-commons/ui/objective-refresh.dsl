(fn RefreshObjective ()
  (if (Utilities|Array|ContainsItem (Class|DaedalusOrrery|GetCharts (Daedalus|Orrery|GetOrrery)) "Lantern")
    (if (Variables|Default|GetCompletionShown)
      (Widget|SetVisibility (Variables|WBP_LanternObjective|GetInteractionPrompt) "Collapsed")
      (else
        (Widget|SetText(Text) (Variables|WBP_LanternObjective|GetObjectiveTitle) "NSLOCTEXT(\"\", \"0FBC571348FDFF709731CA9728B6ADAA\", \"Lantern chart found!\")")
        (Widget|SetText(Text) (Variables|WBP_LanternObjective|GetObjectiveDetail) "NSLOCTEXT(\"\", \"AA75B7E948472D2D46E2E6915C2CA867\", \"You did it! Take your time and explore the Commons. There is no rush.\")")
        (Variables|Default|SetCompletionShown true)
        (Widget|SetVisibility (Variables|WBP_LanternObjective|GetInteractionPrompt) "Collapsed")))
    (else
      (bind _returnvalue (Actor|GetActorOfClass "/Script/DaedalusLink.DaedalusStarChart"))
      (Utilities|IsValid _returnvalue
        (:"Is Valid"
          (if (<= (Transformation|GetDistanceTo _returnvalue (Game|GetPlayerPawn 0)) 300.0)
            (Widget|SetVisibility (Variables|WBP_LanternObjective|GetInteractionPrompt) "HitTestInvisible")
            (else
              (Widget|SetVisibility (Variables|WBP_LanternObjective|GetInteractionPrompt) "Collapsed"))))
        (:"Is Not Valid"
          (Widget|SetVisibility (Variables|WBP_LanternObjective|GetInteractionPrompt) "Collapsed"))))))
