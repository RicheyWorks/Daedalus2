// SPDX-License-Identifier: MIT
// Focused offline checks of Keeper Oriel's guide against the existing dialogue and Seed-Song rules.
#include "DaedalusSeedSongGuide.h"
#include "DaedalusSeedSongCore.h"
#include "DaedalusDialogueCore.h"
#include <cstdio>
#include <limits>
#include <utility>

using namespace daedalus::seedsong;

static int Passed = 0, Total = 0;
static void Expect(bool Ok, const char* Name)
{
    ++Total;
    if (Ok) { ++Passed; }
    std::printf("%s %s\n", Ok ? "PASS" : "FAIL", Name);
}

static std::vector<GuideSpring> SpringView(const Chain& Springs)
{
    std::vector<GuideSpring> Out;
    for (const Spring& SpringState : Springs.Springs)
        Out.push_back({SpringState.Name, Springs.Clean(SpringState.Id)});
    return Out;
}

static std::vector<GuideSpringTarget> SpringTargets(const Chain& Springs)
{
    std::vector<GuideSpringTarget> Out;
    for (size_t I = 0; I < Springs.Springs.size(); ++I)
    {
        const Spring& SpringState = Springs.Springs[I];
        Out.push_back({SpringState.Id, SpringState.Name, "/Test/" + SpringState.Id,
            static_cast<double>((Springs.Springs.size() - I) * 100), Springs.Clean(SpringState.Id), true});
    }
    return Out;
}

int main()
{
    bool Menus = true, Cancel = true, Reveal = true, Invalid = true, Explicit = true, SpringExplicit = true;
    bool LegacyDefaults = true;
    for (GuidePage Page : {GuidePage::Home, GuidePage::Listen, GuidePage::Clue, GuidePage::Review, GuidePage::Result,
        GuidePage::Water, GuidePage::Spring})
        for (bool HasRecord : {false, true})
            for (bool HasHerbs : {false, true})
                for (bool CanGuideSpring : {false, true})
            {
                const auto Choices = GuideChoices(Page, HasRecord, HasHerbs, CanGuideSpring);
                Menus &= !Choices.empty() && Choices.size() <= 4 && Choices.back().Label == "Not now"
                    && Choices.back().Action == GuideAction::Leave;
                Invalid &= GuidePick(Choices, -1) == GuideAction::Leave && GuidePick(Choices, 99) == GuideAction::Leave;
                bool HasSpringReview = false, HasSpringLook = false;
                for (const GuideChoice& Choice : Choices)
                {
                    if (Choice.Action == GuideAction::Confirm)
                        Explicit &= Page == GuidePage::Review && HasRecord && HasHerbs;
                    if (Choice.Action == GuideAction::Review)
                        Explicit &= Page == GuidePage::Home && HasRecord && HasHerbs;
                    if (Choice.Action == GuideAction::ReviewSpring) { HasSpringReview = true; }
                    if (Choice.Action == GuideAction::LookSpring) { HasSpringLook = true; }
                }
                SpringExplicit &= HasSpringReview == (Page == GuidePage::Water && CanGuideSpring)
                    && HasSpringLook == (Page == GuidePage::Spring && CanGuideSpring);
                const auto Defaults = GuideChoices(Page, HasRecord, HasHerbs);
                const auto Unavailable = GuideChoices(Page, HasRecord, HasHerbs, false);
                LegacyDefaults &= Defaults.size() == Unavailable.size();
                for (size_t I = 0; I < Defaults.size() && I < Unavailable.size(); ++I)
                    LegacyDefaults &= Defaults[I].Label == Unavailable[I].Label && Defaults[I].Action == Unavailable[I].Action;
                if (Page != GuidePage::Water && Page != GuidePage::Spring)
                {
                    LegacyDefaults &= Defaults.size() == Choices.size();
                    for (size_t I = 0; I < Defaults.size() && I < Choices.size(); ++I)
                        LegacyDefaults &= Defaults[I].Label == Choices[I].Label && Defaults[I].Action == Choices[I].Action;
                }

                // Use the actual native B/Escape behavior, rather than assuming B closes a choice menu.
                daedalus::dlg::Dialogue Dialogue;
                std::vector<std::string> Labels;
                for (const GuideChoice& Choice : Choices) { Labels.push_back(Choice.Label); }
                Dialogue.Say("Keeper Oriel", "Take your time.", Labels);
                daedalus::dlg::Outcome Out;
                Reveal &= !Dialogue.Press(daedalus::dlg::Button::B, Out) && Dialogue.Choosing();
                Reveal &= !Dialogue.Press(daedalus::dlg::Button::B, Out);
                Cancel &= Dialogue.Press(daedalus::dlg::Button::A, Out)
                    && GuidePick(Choices, Out.Choice) == GuideAction::Leave;
            }
    Expect(Menus, "all availability states have at most four choices with Not now last");
    Expect(Reveal, "skipping text emits no confirmation");
    Expect(Cancel, "native B then A leaves every page");
    Expect(Invalid, "closed lines and invalid choices cannot mend");
    Expect(Explicit, "confirmation exists only in a review with a record and loaded herbs");
    Expect(SpringExplicit, "spring review and camera confirmation appear only on their own available pages");
    Expect(LegacyDefaults, "three-argument menus preserve unavailable defaults and other pages ignore spring availability");
    const auto Home = GuideChoices(GuidePage::Home, true, true);
    Expect(GuidePick(Home, 0) == GuideAction::Listen && GuidePick(Home, 1) == GuideAction::Clue
        && GuidePick(Home, 2) == GuideAction::Review, "home choices separate listening, clues and mend review");
    const auto ReviewChoices = GuideChoices(GuidePage::Review, true, true);
    Expect(GuidePick(ReviewChoices, 0) == GuideAction::Confirm && GuidePick(ReviewChoices, 1) == GuideAction::Back,
        "review requires its own confirmation and offers Back");
    const auto ListenChoices = GuideChoices(GuidePage::Listen, true, true);
    const auto WaterChoices = GuideChoices(GuidePage::Water, true, true);
    Expect(ListenChoices.size() == 3 && ListenChoices[0].Label == "Which springs are clean?"
        && GuidePick(ListenChoices, 0) == GuideAction::Water && GuidePick(ListenChoices, 1) == GuideAction::Back
        && WaterChoices.size() == 2 && GuidePick(WaterChoices, 0) == GuideAction::Back
        && GuidePick(WaterChoices, 1) == GuideAction::Leave,
        "listening offers a separate water query and the water page offers Back or Not now");
    const auto WaterAvailable = GuideChoices(GuidePage::Water, false, false, true);
    const auto SpringAvailable = GuideChoices(GuidePage::Spring, false, false, true);
    const auto SpringUnavailable = GuideChoices(GuidePage::Spring, false, false, false);
    Expect(WaterAvailable.size() == 3 && GuidePick(WaterAvailable, 0) == GuideAction::ReviewSpring
        && GuidePick(WaterAvailable, 1) == GuideAction::Back && GuidePick(WaterAvailable, 2) == GuideAction::Leave
        && SpringAvailable.size() == 3 && GuidePick(SpringAvailable, 0) == GuideAction::LookSpring
        && GuidePick(SpringAvailable, 1) == GuideAction::Back && GuidePick(SpringAvailable, 2) == GuideAction::Leave
        && SpringUnavailable.size() == 2 && GuidePick(SpringUnavailable, 0) == GuideAction::Back
        && GuidePick(SpringUnavailable, 1) == GuideAction::Leave,
        "water reviews before a separate camera action, and unavailable spring pages offer Back or Not now");

    const std::string SpringText = GuideSpringReviewText("Homestead Well");
    Expect(SpringText.find("Homestead Well") != std::string::npos && SpringText.find("camera") != std::string::npos
        && SpringText.find("stay where you are") != std::string::npos && SpringText.find("safe path") != std::string::npos
        && SpringText.find("/Test/") == std::string::npos
        && GuideSpringReviewText("") == GuideSpringUnavailableText()
        && std::string(GuideSpringChangedText()).find("choose a spring again") != std::string::npos,
        "spring review names only the supplied spring and explains camera-only looking with a safe-path caution");

    const GuideSpringTarget ValidTarget{"spring_1", "Homestead Well", "/Test/Z", 25, true, true};
    std::vector<GuideSpringTarget> Targets;
    Targets.push_back(ValidTarget);
    GuideSpringTarget Target = ValidTarget;
    Target.DistanceSquared = 0; Target.Clean = false; Targets.push_back(Target);
    Target = ValidTarget; Target.DistanceSquared = 0; Target.Available = false; Targets.push_back(Target);
    Target = ValidTarget; Target.DistanceSquared = 0; Target.Id.clear(); Targets.push_back(Target);
    Target = ValidTarget; Target.DistanceSquared = 0; Target.Name.clear(); Targets.push_back(Target);
    Target = ValidTarget; Target.DistanceSquared = 0; Target.ActorKey.clear(); Targets.push_back(Target);
    Target = ValidTarget; Target.DistanceSquared = -1; Targets.push_back(Target);
    Target = ValidTarget; Target.DistanceSquared = std::numeric_limits<double>::quiet_NaN(); Targets.push_back(Target);
    Target = ValidTarget; Target.DistanceSquared = std::numeric_limits<double>::infinity(); Targets.push_back(Target);
    Target = ValidTarget; Target.DistanceSquared = -std::numeric_limits<double>::infinity(); Targets.push_back(Target);
    Target = ValidTarget; Target.DistanceSquared = 100; Targets.push_back(Target);
    Expect(GuideNearestSpring({}) == -1 && GuideNearestSpring(Targets) == 0,
        "nearest selection excludes dirty, unavailable, unnamed, unidentified and invalid-distance targets");
    Targets[0].Available = false;
    Targets.back().Available = false;
    Expect(GuideNearestSpring(Targets) == -1, "no eligible spring returns no target instead of a fallback");
    Target = ValidTarget; Target.DistanceSquared = 0;
    Expect(GuideNearestSpring({ValidTarget, Target}) == 1, "a zero-distance clean available spring is eligible");
    std::vector<GuideSpringTarget> Tied = {
        {"spring_2", "Reed Seep", "/Test/Z", 25, true, true},
        {"spring_2", "Reed Seep", "/Test/A", 25, true, true},
        {"spring_1", "Homestead Well", "/Test/A", 25, true, true}};
    Expect(GuideNearestSpring(Tied) == 2, "equal distances select actor key first then spring id");
    std::swap(Tied.front(), Tied.back());
    Expect(GuideNearestSpring(Tied) == 0, "selection of the same tied spring survives a changed discovery order");

    const GuideReview Presented{"record_1", "test tune", {"Solthorn", "Lavine", "Solthorn"}, 7};
    GuideReview Changed = Presented;
    bool Stale = SameReview(Presented, Changed);
    Changed.RecordItem = "record_2";
    Stale &= !SameReview(Presented, Changed);
    Changed = Presented; Changed.Herbs = {"Lavine", "Solthorn", "Solthorn"};
    Stale &= !SameReview(Presented, Changed);
    Changed = Presented; Changed.Herbs.push_back("Mimint");
    Stale &= !SameReview(Presented, Changed);
    Changed = Presented; Changed.Herbs.clear();
    Stale &= !SameReview(Presented, Changed) && !Changed.CanAttempt();
    Changed = Presented; ++Changed.ProgressRevision;
    Stale &= !SameReview(Presented, Changed);
    Expect(Stale, "review detects replaced records, reordered/replaced herbs and external progress before spending");
    const std::string ReviewText = GuideReviewText(Presented);
    Expect(ReviewText.find("test tune") != std::string::npos
        && ReviewText.find("Solthorn, Lavine, Solthorn") != std::string::npos
        && ReviewText.find("uses all these herbs") != std::string::npos
        && ReviewText.find("even if") != std::string::npos,
        "review shows the selected record, exact herb order and existing attempted-mend consumption");

    std::vector<Tune> Tunes;
    for (int I = 0; I < 3; ++I)
        Tunes.push_back({"test_" + std::to_string(I), "test tune", {"Solthorn", "Lavine", "Solthorn"},
            {7, 9, 7}, "record_" + std::to_string(I)});
    Chapter ChapterState(Tunes, Chain::Island(), 2026);
    for (int I = 0; I < 3; ++I)
        ChapterState.Apply("restore_" + std::to_string(I), Tunes[static_cast<size_t>(I)].LearnedFrom,
            Tunes[static_cast<size_t>(I)].Herbs, true, BrewOutcome::Brewed);
    ChapterState.DrawAt("draw", "spring_1");
    const int QuestBefore = ChapterState.Q.Current;
    const auto TallyBefore = ChapterState.GetTally();
    const size_t QuestEventsBefore = ChapterState.Q.Seen.size(), RestoreEventsBefore = ChapterState.Events.size();
    const auto DrawEventsBefore = ChapterState.Springs.Events;
    const std::string Status = GuideHome(TallyBefore.Restored, 3, TallyBefore.SpringsPurified, false, true);
    const std::string Clue = Hint(ChapterState.Records[0]);
    const std::string Water = GuideWaterText(SpringView(ChapterState.Springs));
    auto PlacedTargets = SpringTargets(ChapterState.Springs);
    const int NearestClean = GuideNearestSpring(PlacedTargets);
    const std::string PlacedReview = GuideSpringReviewText(PlacedTargets[2].Name);
    PlacedTargets[2].Available = false; // Native availability excludes hidden/unloaded/ineligible actors.
    const int NearestVisibleClean = GuideNearestSpring(PlacedTargets);
    Expect(QuestBefore == 2 && ChapterState.Q.Current == QuestBefore && !ChapterState.Q.Complete()
        && ChapterState.Q.Seen.size() == QuestEventsBefore && ChapterState.Events.size() == RestoreEventsBefore
        && ChapterState.Springs.Events == DrawEventsBefore && ChapterState.GetTally().CleanDraws == TallyBefore.CleanDraws
        && !Status.empty() && !Clue.empty() && !Water.empty() && !PlacedReview.empty(),
        "progress, hints, spring advice and camera review leave the pending talk step, event ledgers and draw count untouched");
    Expect(NearestClean == 2 && NearestVisibleClean == 1,
        "actual partial island cleanliness rejects closer dirty springs and unavailable clean actors");
    std::string ExpectedWater = "These song springs run clean:";
    for (size_t I = 0; I < 3; ++I) { ExpectedWater += "\n" + ChapterState.Springs.Springs[I].Name; }
    Expect(Water == ExpectedWater, "partial spring advice lists exactly the actual clean spring names and no cloudy spring names");
    Chain FreshSprings = Chain::Island();
    const auto FreshEvents = FreshSprings.Events;
    const auto FreshPurified = FreshSprings.PurifiedBy;
    const std::string NoWater = GuideWaterText(SpringView(FreshSprings));
    bool NoNames = true;
    for (const Spring& SpringState : FreshSprings.Springs)
        NoNames &= NoWater.find(SpringState.Name) == std::string::npos;
    Expect(NoNames && NoWater.find("None of these song springs") != std::string::npos
        && NoWater.find("Each record you mend clears the next song spring") != std::string::npos
        && FreshSprings.Events == FreshEvents && FreshSprings.PurifiedBy == FreshPurified,
        "no-clean advice concerns song springs only, explains record progress and changes no spring state");
    Expect(GuideNearestSpring(SpringTargets(FreshSprings)) == -1,
        "actual unmended island springs cannot produce a camera target");
    Chain AllSprings = Chain::Island();
    for (size_t I = 0; I < AllSprings.Springs.size(); ++I) { AllSprings.PurifyNext("test tune"); }
    const auto AllEvents = AllSprings.Events;
    const auto AllPurified = AllSprings.PurifiedBy;
    std::string ExpectedAll = "These song springs run clean:";
    for (const Spring& SpringState : AllSprings.Springs) { ExpectedAll += "\n" + SpringState.Name; }
    Expect(AllSprings.Springs.size() == 12 && GuideWaterText(SpringView(AllSprings)) == ExpectedAll
        && AllSprings.Events == AllEvents && AllSprings.PurifiedBy == AllPurified,
        "all-clean advice lists the twelve existing supplied spring names without inventing locations or events");
    Expect(GuideNearestSpring(SpringTargets(AllSprings)) == 11,
        "all-clean island selects the nearest available placed spring using the existing twelve identities");
    Expect(ChapterState.Talk("listen") == Thanks() && ChapterState.Q.Complete(),
        "explicit listening uses the existing authored Thanks and completes the original talk step");

    Chapter Failed(Tunes, Chain::Island(), 2026);
    const auto Miss = Failed.Apply("miss", Tunes[0].LearnedFrom, {"Lavine", "Solthorn", "Solthorn"}, true, BrewOutcome::Brewed);
    const auto Short = Failed.Apply("short", Tunes[0].LearnedFrom, {"Solthorn"}, true, BrewOutcome::MissingHerbs);
    Expect(Miss.Result == Outcome::NeedleSkips && Failed.GetTally().Skipped == 1
        && Short.Result == Outcome::MissingHerbs && Failed.GetTally().Restored == 0
        && GuideResult(OutcomeName(Miss.Result), 0, 3, 0).find("still needs mending") != std::string::npos
        && GuideResult(OutcomeName(Short.Result), 0, 3, 0).find("at least " + std::to_string(MinHerbs)) != std::string::npos,
        "guide explains existing failed outcomes without changing restoration rules");

    std::printf("%d/%d\n", Passed, Total);
    return Passed == Total ? 0 : 1;
}
