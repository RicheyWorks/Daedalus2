(fn InitGarden ()
  (Variables|Default|SetLoadBlocked true)
  (if (SaveGame|DoesSaveGameExist :SlotName "Daedalus_LanternCommons_Garden_v1" :UserIndex 0)
    (bind saved (Utilities|Casting|CastToSG_CommonsGarden :Object (SaveGame|LoadGamefromSlot :SlotName "Daedalus_LanternCommons_Garden_v1" :UserIndex 0))
      (:then
        (if (== (Class|SGCommonsGarden|GetVersion :self saved) 1)
          (if (>= (Class|SGCommonsGarden|GetGardenStage :self saved) 0)
            (if (<= (Class|SGCommonsGarden|GetGardenStage :self saved) 2)
              (Variables|Default|SetGardenSave saved)
              (Variables|Default|SetGardenStage (Class|SGCommonsGarden|GetGardenStage :self saved))
              (Variables|Default|SetLoadBlocked false)))))
      (:CastFailed))
    (else
      (bind fresh (Utilities|Casting|CastToSG_CommonsGarden :Object (SaveGame|CreateSaveGameObject :SaveGameClass "/Game/CodexToolEvaluation/PlayableCourtyard/20261022/R1/GardenActivityR7/SG_CommonsGarden.SG_CommonsGarden_C"))
        (:then
          (Variables|Default|SetGardenSave fresh)
          (Variables|Default|SetGardenStage 0)
          (Variables|Default|SetLoadBlocked false))
        (:CastFailed)))))