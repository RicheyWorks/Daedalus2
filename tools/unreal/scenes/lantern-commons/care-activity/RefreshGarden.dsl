(fn RefreshGarden ()
  (Rendering|SetActorHiddenInGame :self (Variables|Default|GetCareBloomLeft) :bNewHidden true)
  (Rendering|SetActorHiddenInGame :self (Variables|Default|GetCareBloomRight) :bNewHidden true)
  (if (== (Variables|Default|GetGardenStage) 2)
    (if (Variables|Default|GetCareComplete)
      (Rendering|SetActorHiddenInGame :self (Variables|Default|GetCareBloomLeft) :bNewHidden false)
      (Rendering|SetActorHiddenInGame :self (Variables|Default|GetCareBloomRight) :bNewHidden false)))

  (Widget|SetVisibility :self (Class|WBPCommonsGarden|GetKeeperMessage :self (Variables|Default|GetGardenUI)) :InVisibility "Collapsed")

  (Rendering|SetActorHiddenInGame :self (Variables|Default|GetSeedActor) :bNewHidden (> (Variables|Default|GetGardenStage) 0))
  (Rendering|SetActorHiddenInGame :self (Variables|Default|GetFlowerActor) :bNewHidden (< (Variables|Default|GetGardenStage) 2))
  (Utilities|IsValid (Game|GetPlayerPawn :PlayerIndex 0)
    (:"Is Valid"

  (if (> (Transformation|GetDistanceTo :self (Variables|Default|GetKeeperActor) :OtherActor (Game|GetPlayerPawn :PlayerIndex 0)) 240.0)
    (Variables|Default|SetKeeperOpen false))
  (if (Variables|Default|GetLoadBlocked)
    (Variables|Default|SetKeeperOpen false)
    (else
      (if (Variables|Default|GetSaveFailed)
        (Variables|Default|SetKeeperOpen false)
        (else
          (if (<= (Transformation|GetDistanceTo :self (Variables|Default|GetKeeperActor) :OtherActor (Game|GetPlayerPawn :PlayerIndex 0)) 240.0)
            (Widget|SetVisibility :self (Variables|Default|GetGardenUI) :InVisibility "HitTestInvisible")
            (Widget|SetText(Text) :self (Class|WBPCommonsGarden|GetGardenTitle :self (Variables|Default|GetGardenUI)) :InText "Gardenkeeper")
            (Widget|SetVisibility :self (Class|WBPCommonsGarden|GetGardenPrompt :self (Variables|Default|GetGardenUI)) :InVisibility "HitTestInvisible")
            (Widget|SetText(Text) :self (Class|WBPCommonsGarden|GetGardenPrompt :self (Variables|Default|GetGardenUI)) :InText "[E] Gardenkeeper")
            (if (Variables|Default|GetKeeperOpen)
              (Widget|SetText(Text) :self (Class|WBPCommonsGarden|GetGardenTitle :self (Variables|Default|GetGardenUI)) :InText "Gardenkeeper")
              (Widget|SetVisibility :self (Class|WBPCommonsGarden|GetKeeperMessage :self (Variables|Default|GetGardenUI)) :InVisibility "HitTestInvisible")
              (Widget|SetText(Text) :self (Class|WBPCommonsGarden|GetGardenPrompt :self (Variables|Default|GetGardenUI)) :InText "[E] Close")
              (if (== (Variables|Default|GetGardenStage) 0)
                (Widget|SetText(Text) :self (Class|WBPCommonsGarden|GetKeeperMessage :self (Variables|Default|GetGardenUI)) :InText "Welcome! Take a seed from the teal stand.")
                (else
                  (if (== (Variables|Default|GetGardenStage) 1)
                    (Widget|SetText(Text) :self (Class|WBPCommonsGarden|GetKeeperMessage :self (Variables|Default|GetGardenUI)) :InText "Your seed is ready. Plant it in the pink pot.")
                    (else
                      (if (Variables|Default|GetCareComplete)
                        (Widget|SetText(Text) :self (Class|WBPCommonsGarden|GetKeeperMessage :self (Variables|Default|GetGardenUI)) :InText "Thank you! You've cared for the garden.")
                        (else
                          (if (Variables|Default|GetHasWater)
                            (Widget|SetText(Text) :self (Class|WBPCommonsGarden|GetKeeperMessage :self (Variables|Default|GetGardenUI)) :InText "Now tend the flower in the pink pot.")
                            (else
                              (Widget|SetText(Text) :self (Class|WBPCommonsGarden|GetKeeperMessage :self (Variables|Default|GetGardenUI)) :InText "Your flower is planted. Bring it water from the small barrel."))))))))))
            (return))))))
      (if (== (Variables|Default|GetGardenStage) 2) (CallFunction|RefreshCareUI) (return))
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