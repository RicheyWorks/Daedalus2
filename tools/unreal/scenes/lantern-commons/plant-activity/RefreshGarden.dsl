(fn RefreshGarden ()
  (Rendering|SetActorHiddenInGame :self (Variables|Default|GetSeedActor) :bNewHidden (> (Variables|Default|GetGardenStage) 0))
  (Rendering|SetActorHiddenInGame :self (Variables|Default|GetFlowerActor) :bNewHidden (< (Variables|Default|GetGardenStage) 2))
  (Utilities|IsValid (Game|GetPlayerPawn :PlayerIndex 0)
    (:"Is Valid"
      (if (> (Transformation|GetDistanceTo :self (Variables|Default|GetPlanterActor) :OtherActor (Game|GetPlayerPawn :PlayerIndex 0)) 1600.0)
        (Widget|SetVisibility :self (Variables|Default|GetGardenUI) :InVisibility "Collapsed")
        (else
          (Widget|SetVisibility :self (Variables|Default|GetGardenUI) :InVisibility "HitTestInvisible")
          (Widget|SetVisibility :self (Class|WBPCommonsGarden|GetGardenPrompt :self (Variables|Default|GetGardenUI)) :InVisibility "Collapsed")
          (if (Variables|Default|GetLoadBlocked)
            (Widget|SetText(Text) :self (Class|WBPCommonsGarden|GetGardenTitle :self (Variables|Default|GetGardenUI)) :InText "Garden save unavailable")
            (else
              (if (== (Variables|Default|GetGardenStage) 2)
                (Widget|SetText(Text) :self (Class|WBPCommonsGarden|GetGardenTitle :self (Variables|Default|GetGardenUI)) :InText "Flower planted")
                (else
                  (if (== (Variables|Default|GetGardenStage) 0)
                    (Widget|SetText(Text) :self (Class|WBPCommonsGarden|GetGardenTitle :self (Variables|Default|GetGardenUI)) :InText "Collect seed")
                    (Widget|SetText(Text) :self (Class|WBPCommonsGarden|GetGardenPrompt :self (Variables|Default|GetGardenUI)) :InText "[E] Collect seed")
                    (if (<= (Transformation|GetDistanceTo :self (Variables|Default|GetSeedActor) :OtherActor (Game|GetPlayerPawn :PlayerIndex 0)) 240.0)
                      (Widget|SetVisibility :self (Class|WBPCommonsGarden|GetGardenPrompt :self (Variables|Default|GetGardenUI)) :InVisibility "HitTestInvisible"))
                    (else
                      (Widget|SetText(Text) :self (Class|WBPCommonsGarden|GetGardenTitle :self (Variables|Default|GetGardenUI)) :InText "Plant seed")
                      (Widget|SetText(Text) :self (Class|WBPCommonsGarden|GetGardenPrompt :self (Variables|Default|GetGardenUI)) :InText "[E] Plant seed")
                      (if (<= (Transformation|GetDistanceTo :self (Variables|Default|GetPlanterActor) :OtherActor (Game|GetPlayerPawn :PlayerIndex 0)) 240.0)
                        (Widget|SetVisibility :self (Class|WBPCommonsGarden|GetGardenPrompt :self (Variables|Default|GetGardenUI)) :InVisibility "HitTestInvisible"))))
                  (if (Variables|Default|GetSaveFailed)
                    (Widget|SetText(Text) :self (Class|WBPCommonsGarden|GetGardenTitle :self (Variables|Default|GetGardenUI)) :InText "Couldn't save")
                    (Widget|SetText(Text) :self (Class|WBPCommonsGarden|GetGardenPrompt :self (Variables|Default|GetGardenUI)) :InText "[E] Try again")))))))))
    (:"Is Not Valid"
      (Widget|SetVisibility :self (Variables|Default|GetGardenUI) :InVisibility "Collapsed"))))