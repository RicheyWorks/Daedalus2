// SPDX-License-Identifier: MIT
#include "DaedalusTwinDoors.h"

#if WITH_DEV_AUTOMATION_TESTS && WITH_EDITOR
#include "DaedalusHero.h"
#include "Engine/Engine.h"
#include "Engine/World.h"
#include "Framework/Application/SlateApplication.h"
#include "Misc/AutomationTest.h"
#include "UObject/Package.h"

// Source-only regression fixture for the editor owner. No map, asset, save or real viewport is modified:
// the unpossessed Hero's existing dialogue is driven through DialogueInput on an isolated transient world.
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDaedalusTwinDoorsGuideTest,
    "Daedalus.NPC.TwinDoors.GuideChoices",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FDaedalusTwinDoorsGuideTest::RunTest(const FString& Parameters)
{
    if (!TestTrue(TEXT("Editor Slate is initialized"), FSlateApplication::IsInitialized())) { return false; }
    UWorld* World = UWorld::CreateWorld(EWorldType::Game, false);
    if (!TestNotNull(TEXT("Isolated test world"), World)) { return false; }
    if (!TestNotNull(TEXT("Engine for isolated world context"), GEngine)) { World->DestroyWorld(false); return false; }
    GEngine->CreateNewWorldContext(EWorldType::Game).SetCurrentWorld(World);
    auto CleanupWorld = [World]()
    {
        UPackage* FixturePackage = World->GetOutermost();
        World->DestroyWorld(false);
        GEngine->DestroyWorldContext(World);
        FixturePackage->SetDirtyFlag(false); // only this newly created, unsaved test-world package
    };
    World->InitializeActorsForPlay(FURL());
    ADaedalusHero* Hero = World->SpawnActor<ADaedalusHero>();
    ADaedalusTwinDoors* Doors = World->SpawnActor<ADaedalusTwinDoors>();
    if (!Hero || !Doors) { CleanupWorld(); return false; }
    Hero->InventoryRealm = TEXT("labyrinth");
    Doors->Seed = 42;
    Doors->Difficulty = 1;
    Doors->ResetRiddle();
    auto Pick = [Hero](int32 Index)
    {
        Hero->DialogueInput(TEXT("b")); // finish the newly opened text; the first choice is now highlighted
        for (int32 I = 0; I < Index; ++I) { Hero->DialogueInput(TEXT("down")); }
        Hero->DialogueInput(TEXT("a"));
    };
    auto CloseResult = [Hero]() { Hero->DialogueInput(TEXT("b")); Hero->DialogueInput(TEXT("a")); };

    TestTrue(TEXT("Interact opens a conversation"), Doors->Use(Hero));
    TestFalse(TEXT("Opening does not spend a question"), Doors->HasAsked());
    Pick(1);
    TestFalse(TEXT("Not now leaves before asking"), Hero->IsDialogueOpen());
    TestFalse(TEXT("Leaving does not ask"), Doors->HasAsked());
    TestEqual(TEXT("Leaving preserves the seed"), Doors->Seed, static_cast<int64>(42));

    Doors->Use(Hero);
    Doors->AskQuestion = EDaedalusTwinQuestion::Self; // configuration changes after the embedded question is shown
    Pick(0);
    TestTrue(TEXT("Ask submits the presented question"), Doors->HasAsked());
    TestEqual(TEXT("Presented embedded question still proves a door"), Doors->Deduced(), 0);
    Pick(2); // clue
    Pick(0); // replay the heard bell
    TestEqual(TEXT("Clue/replay preserve the heard answer"), Doors->Deduced(), 0);
    Pick(3); // leave the door menu
    TestFalse(TEXT("Leave closes the guide after asking"), Hero->IsDialogueOpen());

    Doors->Use(Hero);
    Doors->ResetRiddle();
    Pick(0); // a now-stale door-menu answer must not ask or choose in the new puzzle
    TestFalse(TEXT("Reset invalidates old dialogue choices"), Doors->HasAsked());
    TestFalse(TEXT("Reset leaves the puzzle unsolved"), Doors->IsSolved());
    TestFalse(TEXT("Old menu closes without another line"), Hero->IsDialogueOpen());

    Doors->AskQuestion = EDaedalusTwinQuestion::Embedded;
    Doors->Use(Hero);
    Pick(0);
    Hero->SetActorLocation(Doors->GetActorLocation() + FVector(0.f, 1000.f, 0.f));
    Pick(0); // seed 42/difficulty 1: explicit left is safe, even while standing nearer the other side
    TestTrue(TEXT("Explicit left choice opens the safe door"), Doors->IsSolved());
    CloseResult();
    TestFalse(TEXT("Result closes without reopening the guide"), Hero->IsDialogueOpen());

    Doors->ResetRiddle();
    Doors->Use(Hero);
    Pick(0);
    const int32 Wrong = 1 - Doors->Deduced();
    Pick(Wrong);
    TestEqual(TEXT("Wrong door advances the existing seed"), Doors->Seed, static_cast<int64>(43));
    TestFalse(TEXT("Wrong door resets only this riddle"), Doors->HasAsked());
    TestFalse(TEXT("Wrong door remains unsolved"), Doors->IsSolved());
    CloseResult();

    Doors->Use(Hero);
    Doors->Destroy();
    Pick(0);
    TestFalse(TEXT("Destroyed guard actor leaves no active callback"), Hero->IsDialogueOpen());
    CleanupWorld();
    return !HasAnyErrors();
}
#endif
