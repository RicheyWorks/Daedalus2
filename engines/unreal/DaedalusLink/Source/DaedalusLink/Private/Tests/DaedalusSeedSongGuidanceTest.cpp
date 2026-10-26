// SPDX-License-Identifier: MIT
#include "DaedalusSeedSong.h"

#if WITH_DEV_AUTOMATION_TESTS && WITH_EDITOR
#include "DaedalusHero.h"
#include "Engine/Engine.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "Misc/AutomationTest.h"
#include "UObject/Package.h"

// Transient non-BeginPlay world: no Hero save/load lifecycle or real viewport is started.
// The friend seam supplies the read-only Listen page without invoking the deliberate Talk quest action.
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDaedalusSeedSongGuidanceTest,
    "Daedalus.NPC.SeedSong.CleanSpringGuidance",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FDaedalusSeedSongGuidanceTest::RunTest(const FString& Parameters)
{
    using namespace daedalus::seedsong;
    UWorld* World = UWorld::CreateWorld(EWorldType::Game, false);
    if (!TestNotNull(TEXT("Isolated fixture world"), World)) { return false; }
    if (!TestNotNull(TEXT("Engine for isolated world context"), GEngine)) { World->DestroyWorld(false); return false; }
    GEngine->CreateNewWorldContext(EWorldType::Game).SetCurrentWorld(World);
    auto CleanupWorld = [World]()
    {
        UPackage* FixturePackage = World->GetOutermost();
        World->DestroyWorld(false);
        GEngine->DestroyWorldContext(World);
        // Actor moves/destruction may dirty this newly created test map. It has
        // no authored file and is owned only by this fixture, never the editor map.
        FixturePackage->SetDirtyFlag(false);
    };
    World->InitializeActorsForPlay(FURL());
    ADaedalusHero* Hero = World->SpawnActor<ADaedalusHero>();
    ADaedalusSeedSong* Song = World->SpawnActor<ADaedalusSeedSong>();
    ADaedalusSeedSpring* Near = World->SpawnActor<ADaedalusSeedSpring>(FVector(0, 1000, 0), FRotator::ZeroRotator);
    ADaedalusSeedSpring* Far = World->SpawnActor<ADaedalusSeedSpring>(FVector(0, 3000, 0), FRotator::ZeroRotator);
    ADaedalusSeedSpring* Dirty = World->SpawnActor<ADaedalusSeedSpring>(FVector(0, 100, 0), FRotator::ZeroRotator);
    APlayerController* Controller = World->SpawnActor<APlayerController>();
    if (!Hero || !Song || !Near || !Far || !Dirty || !Controller) { CleanupWorld(); return false; }
    Near->SpringId = TEXT("spring_1");
    Far->SpringId = TEXT("spring_2");
    Dirty->SpringId = TEXT("spring_3");
    Song->State = MakeShared<FDaedalusSeedSongState>();
    Song->State->Chapter = MakeUnique<Chapter>(Song->State->Tunes, Chain::Island(), 2026);
    TestNull(TEXT("Cloudy springs provide no camera destination"), Song->NearbyCleanSpring(Hero));
    Song->State->Chapter->Springs.PurifyNext("fixture_1");
    Song->State->Chapter->Springs.PurifyNext("fixture_2");
    TestTrue(TEXT("Nearest loaded clean spring is selected"), Song->NearbyCleanSpring(Hero) == Near);
    Near->SetActorHiddenInGame(true);
    TestTrue(TEXT("Hidden spring is excluded"), Song->NearbyCleanSpring(Hero) == Far);
    Near->SetActorHiddenInGame(false);
    Near->SpringId = TEXT("unknown_spring");
    TestTrue(TEXT("Unknown spring id is excluded"), Song->NearbyCleanSpring(Hero) == Far);
    Near->SpringId = TEXT("spring_1");

    const FVector HeroBefore = Hero->GetActorLocation();
    const Tally TallyBefore = Song->State->Chapter->GetTally();
    const size_t EventsBefore = Song->State->Chapter->Events.size();
    const size_t DrawsBefore = Song->State->Chapter->Springs.Events.size();
    const int QuestBefore = Song->State->Chapter->Q.Current;
    const int CountBefore = Song->State->Chapter->Q.Count;
    Song->KettleHerbs = {TEXT("Solthorn"), TEXT("Lavine"), TEXT("Solthorn")};
    auto PrepareReview = [Song, Hero, Near, Controller]()
    {
        Song->StopGuide();
        Song->ListeningHero = Hero;
        Song->GuideRealm = Hero->RealmNow();
        Song->CurrentGuidePage = GuidePage::Spring;
        Song->GuideHandle = Hero->OnDialogueChoice.AddLambda([](const FString&, int32) {});
        Song->ReviewedSpring = Near;
        Song->ReviewedSpringId = Near->SpringId;
        Song->ReviewedSpringPoint = Near->GetActorLocation();
        Song->ReviewedController = Controller;
    };
    PrepareReview();
    TestFalse(TEXT("Uncontrolled hero cannot be pointed"), Song->LookAtReviewedSpring());
    Controller->SetAsLocalPlayerController(); // normal local-controller designation used by GameModeBase
    Controller->Possess(Hero);
    if (!TestTrue(TEXT("Fixture controller is local"), Controller->IsLocalController()))
    {
        CleanupWorld();
        return false;
    }
    Controller->SetControlRotation(FRotator::ZeroRotator);
    PrepareReview();
    Near->SpringId = TEXT("spring_2");
    TestFalse(TEXT("Retargeted id invalidates the reviewed destination"), Song->LookAtReviewedSpring());
    Near->SpringId = TEXT("spring_1");
    Near->SetActorLocation(FVector(0, 1100, 0));
    TestFalse(TEXT("Moved destination requires a fresh review"), Song->LookAtReviewedSpring());
    Near->SetActorLocation(FVector(0, 1000, 0));
    Song->CurrentGuidePage = GuidePage::Water;
    TestFalse(TEXT("Directory alone cannot turn the camera"), Song->LookAtReviewedSpring());
    PrepareReview();
    Song->StopGuide();
    TestFalse(TEXT("Cancellation invalidates the camera action"), Song->LookAtReviewedSpring());
    TestTrue(TEXT("All refused actions leave the controller unchanged"), Controller->GetControlRotation().IsNearlyZero());

    PrepareReview();
    TestTrue(TEXT("Fresh exact review invokes the existing camera action"), Song->LookAtReviewedSpring());
    TestTrue(TEXT("Camera points toward the spring's side"), FMath::Abs(Controller->GetControlRotation().Yaw) > 1.f);
    TestFalse(TEXT("The completed review cannot be replayed"), Song->LookAtReviewedSpring());
    TestTrue(TEXT("Pointing keeps the hero in place"), Hero->GetActorLocation() == HeroBefore);
    TestEqual(TEXT("Pointing spends no loaded herbs"), Song->KettleHerbs.Num(), 3);
    TestEqual(TEXT("Pointing creates no native quest event"), Song->Events, 0);
    TestTrue(TEXT("Chapter and draw event ledgers stay unchanged"), Song->State->Chapter->Events.size() == EventsBefore
        && Song->State->Chapter->Springs.Events.size() == DrawsBefore);
    TestEqual(TEXT("Quest step stays unchanged"), Song->State->Chapter->Q.Current, QuestBefore);
    TestEqual(TEXT("Quest count stays unchanged"), Song->State->Chapter->Q.Count, CountBefore);
    TestEqual(TEXT("Pointing grants no clean draw"), Song->State->Chapter->GetTally().CleanDraws, TallyBefore.CleanDraws);
    PrepareReview();
    Near->Destroy();
    TestFalse(TEXT("Destroyed destination cannot be used"), Song->LookAtReviewedSpring());
    TestTrue(TEXT("Another real clean spring remains selectable"), Song->NearbyCleanSpring(Hero) == Far);
    Song->StopGuide();
    auto PickAction = [this, Hero, Song](GuideAction Action)
    {
        const std::vector<GuideChoice> Shown = Song->PresentedChoices;
        int32 Index = INDEX_NONE;
        for (int32 I = 0; I < static_cast<int32>(Shown.size()); ++I)
        {
            if (Shown[static_cast<size_t>(I)].Action == Action) { Index = I; break; }
        }
        if (!TestTrue(TEXT("Requested action was actually presented"), Index != INDEX_NONE)) { return; }
        Hero->DialogueInput(TEXT("b"));
        for (int32 I = 0; I < Index; ++I) { Hero->DialogueInput(TEXT("down")); }
        Hero->DialogueInput(TEXT("a"));
    };
    TestTrue(TEXT("Oriel opens the actual dialogue"), Song->Use(Hero));
    PickAction(GuideAction::Leave);
    TestFalse(TEXT("Opening and cancelling closes the dialogue"), Hero->IsDialogueOpen());
    TestEqual(TEXT("Opening and cancelling creates no quest event"), Song->Events, 0);
    TestTrue(TEXT("Oriel can reopen after cancelling"), Song->Use(Hero));
    PickAction(GuideAction::Leave);
    auto OpenReadOnlyListen = [this, Hero, Song]()
    {
        if (!TestFalse(TEXT("Fixture opens its read-only page only on a closed dialogue"), Hero->IsDialogueOpen())) { return false; }
        Song->StopGuide();
        Song->ListeningHero = Hero;
        Song->GuideRealm = Hero->RealmNow();
        Song->GuideHandle = Hero->OnDialogueChoice.AddUObject(Song, &ADaedalusSeedSong::OnGuideChoice);
        Song->ShowGuide(GuidePage::Listen, TEXT("Clean-spring directory fixture"));
        return true;
    };
    if (!OpenReadOnlyListen()) { CleanupWorld(); return false; }
    PickAction(GuideAction::Water);
    TestTrue(TEXT("Actual choice opens the clean-spring directory"), Song->CurrentGuidePage == GuidePage::Water);
    PickAction(GuideAction::Back);
    PickAction(GuideAction::Leave);
    TestEqual(TEXT("Directory browsing creates no quest event"), Song->Events, 0);
    TestTrue(TEXT("Directory browsing preserves chapter and draw ledgers"), Song->State->Chapter->Events.size() == EventsBefore
        && Song->State->Chapter->Springs.Events.size() == DrawsBefore);
    TestEqual(TEXT("Directory browsing preserves loaded herbs"), Song->KettleHerbs.Num(), 3);
    if (!OpenReadOnlyListen()) { CleanupWorld(); return false; }
    PickAction(GuideAction::Water);
    Controller->SetControlRotation(FRotator::ZeroRotator);
    PickAction(GuideAction::ReviewSpring);
    TestTrue(TEXT("Review alone does not turn the camera"), Controller->GetControlRotation().IsNearlyZero());
    PickAction(GuideAction::LookSpring);
    TestTrue(TEXT("Explicit dialogue confirmation turns toward the remaining real spring"), FMath::Abs(Controller->GetControlRotation().Yaw) > 1.f);
    TestFalse(TEXT("Confirmed camera choice closes the dialogue"), Hero->IsDialogueOpen());
    TestFalse(TEXT("Confirmed dialogue action cannot replay"), Song->LookAtReviewedSpring());
    TestTrue(TEXT("Confirmed dialogue action preserves player location"), Hero->GetActorLocation() == HeroBefore);
    TestEqual(TEXT("Confirmed dialogue action creates no quest event"), Song->Events, 0);
    TestEqual(TEXT("Confirmed dialogue action preserves loaded herbs"), Song->KettleHerbs.Num(), 3);
    CleanupWorld();
    return !HasAnyErrors();
}
#endif
