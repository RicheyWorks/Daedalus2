// SPDX-License-Identifier: MIT

#include "DaedalusSeedSong.h"
#include "DaedalusHero.h"
#include "Components/PointLightComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/Engine.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/PlayerController.h"
#include "HAL/IConsoleManager.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "UObject/ConstructorHelpers.h"

// Named (not anonymous) so unity builds cannot collide with other files' helpers.
namespace DaedalusSeedSongLocal
{
std::string ToUtf8(const FString& S) { return std::string(TCHAR_TO_UTF8(*S)); }
FString FromUtf8(const std::string& S) { return FString(UTF8_TO_TCHAR(S.c_str())); }
}

// ---------------- gramophone ----------------
ADaedalusSeedSong::ADaedalusSeedSong()
{
	PrimaryActorTick.bCanEverTick = true;
	bReplicates = false;
	Tags.Add(TEXT("SeedSong"));
	Tags.Add(TEXT("Interact_SeedSong"));
	static ConstructorHelpers::FObjectFinder<UStaticMesh> Cone(TEXT("/Engine/BasicShapes/Cone.Cone"));
	if (Cone.Succeeded())
	{
		Body->SetStaticMesh(Cone.Object);
		Body->SetRelativeScale3D(FVector(0.6f, 0.6f, 0.8f));
	}
	Glow->SetLightColor(FLinearColor(0.7f, 0.6f, 1.f));
}

void ADaedalusSeedSong::BeginPlay()
{
	Super::BeginPlay();
	Ensure();
}

bool ADaedalusSeedSong::Ensure()
{
	if (IsReady()) { return true; }
	const FString Path = FPaths::Combine(FPaths::ProjectPluginsDir(), TEXT("DaedalusLink/Content/YTM/found_tunes.csv"));
	FString Text;
	if (!FFileHelper::LoadFileToString(Text, *Path))
	{
		UE_LOG(LogTemp, Warning, TEXT("Daedalus seed song: cannot read %s"), *Path);
		return false;
	}
	TSharedPtr<FDaedalusSeedSongState> S = MakeShared<FDaedalusSeedSongState>();
	if (!daedalus::seedsong::ParseTunes(DaedalusSeedSongLocal::ToUtf8(Text), S->Tunes) || S->Tunes.empty())
	{
		UE_LOG(LogTemp, Warning, TEXT("Daedalus seed song: %s does not parse"), *Path);
		return false;
	}
	// Tunes is final before the chapter takes pointers into it.
	S->Chapter = MakeUnique<daedalus::seedsong::Chapter>(S->Tunes, daedalus::seedsong::Chain::Island(), static_cast<int64_t>(Seed));
	State = S;
	UE_LOG(LogTemp, Log, TEXT("Daedalus seed song: %d records, seed %lld"), RecordCount(), static_cast<long long>(Seed));
	return true;
}

FString ADaedalusSeedSong::NextEvent()
{
	return FString::Printf(TEXT("%s-%d"), *GetName(), ++Events);
}

void ADaedalusSeedSong::Tell(const FString& Line) const
{
	if (UDaedalusOrrery* O = UDaedalusOrrery::Get(this)) { O->Say(Line); }
	UE_LOG(LogTemp, Log, TEXT("Daedalus seed song: %s"), *Line);
}

int32 ADaedalusSeedSong::RecordCount() const { return IsReady() ? static_cast<int32>(State->Chapter->Records.size()) : 0; }
int32 ADaedalusSeedSong::RestoredCount() const { return IsReady() ? State->Chapter->GetTally().Restored : 0; }
int32 ADaedalusSeedSong::CleanSprings() const { return IsReady() ? State->Chapter->GetTally().SpringsPurified : 0; }

FString ADaedalusSeedSong::NextRecord() const
{
	if (!IsReady()) { return FString(); }
	for (const daedalus::seedsong::Record& R : State->Chapter->Records)
	{
		if (!State->Chapter->IsRestored(R.Item())) { return DaedalusSeedSongLocal::FromUtf8(R.Item()); }
	}
	return FString();
}

FString ADaedalusSeedSong::Restore(const FString& RecordItem, const TArray<FString>& Herbs)
{
	if (!Ensure()) { return TEXT("IGNORED"); }
	std::vector<std::string> H;
	for (const FString& X : Herbs) { H.push_back(DaedalusSeedSongLocal::ToUtf8(X)); }
	const daedalus::seedsong::BrewOutcome Brew = H.size() >= static_cast<size_t>(daedalus::seedsong::MinHerbs)
		? daedalus::seedsong::BrewOutcome::Brewed : daedalus::seedsong::BrewOutcome::MissingHerbs;
	const daedalus::seedsong::Restore R = State->Chapter->Apply(DaedalusSeedSongLocal::ToUtf8(NextEvent()), DaedalusSeedSongLocal::ToUtf8(RecordItem), H, true, Brew);
	return DaedalusSeedSongLocal::FromUtf8(daedalus::seedsong::OutcomeName(R.Result));
}

FString ADaedalusSeedSong::Draw(const FString& SpringId)
{
	if (!Ensure()) { return TEXT("IGNORED"); }
	const daedalus::seedsong::Draw D = State->Chapter->DrawAt(DaedalusSeedSongLocal::ToUtf8(NextEvent()), DaedalusSeedSongLocal::ToUtf8(SpringId));
	return FString::Printf(TEXT("%s %s %d"), UTF8_TO_TCHAR(daedalus::seedsong::DrawName(D.Outcome)), *DaedalusSeedSongLocal::FromUtf8(D.Item), D.Amount);
}

FString ADaedalusSeedSong::SpringName(const FString& SpringId) const
{
	if (IsReady())
	{
		const int32 Index = State->Chapter->Springs.Index(DaedalusSeedSongLocal::ToUtf8(SpringId));
		if (Index >= 0) { return DaedalusSeedSongLocal::FromUtf8(State->Chapter->Springs.Springs[static_cast<size_t>(Index)].Name); }
	}
	return SpringId;
}

FString ADaedalusSeedSong::Talk()
{
	if (!Ensure()) { return FString(); }
	return DaedalusSeedSongLocal::FromUtf8(State->Chapter->Talk(DaedalusSeedSongLocal::ToUtf8(NextEvent())));
}

FString ADaedalusSeedSong::Prompt(const ADaedalusHero*) const { return TEXT("Listen at Keeper Oriel's gramophone"); }

bool ADaedalusSeedSong::Use(ADaedalusHero* Hero)
{
	if (bEndingPlay || !IsValid(Hero) || Hero->GetWorld() != GetWorld() || Hero->IsDialogueOpen()) { return false; }
	if (ADaedalusHero* Listener = ListeningHero.Get())
		if (Listener->IsDialogueOpen()) { return false; }
	StopGuide();
	if (!Ensure())
	{
		Tell(TEXT("The gramophone is silent (no tunes)."));
		Hero->Speak(TEXT("Keeper Oriel"), TEXT("The gramophone is silent. Try again when its tunes are available."), {});
		return Hero->IsDialogueOpen();
	}
	ListeningHero = Hero;
	GuideRealm = Hero->RealmNow();
	GuideHandle = Hero->OnDialogueChoice.AddUObject(this, &ADaedalusSeedSong::OnGuideChoice);
	ShowGuide(daedalus::seedsong::GuidePage::Home);
	// A refused overlay must leave no subscription, quest event or spent herbs behind.
	if (!Hero->IsDialogueOpen()) { StopGuide(); return false; }
	return true;
}

void ADaedalusSeedSong::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	if (GuideHandle.IsValid() && (!IsGuideCurrent() || !ListeningHero->IsDialogueOpen())) { StopGuide(); }
}

void ADaedalusSeedSong::EndPlay(const EEndPlayReason::Type Reason)
{
	bEndingPlay = true;
	StopGuide();
	Super::EndPlay(Reason);
}

void ADaedalusSeedSong::StopGuide()
{
	if (ADaedalusHero* Hero = ListeningHero.Get())
		if (GuideHandle.IsValid()) { Hero->OnDialogueChoice.Remove(GuideHandle); }
	GuideHandle.Reset();
	ListeningHero.Reset();
	GuideRealm.Empty();
	PresentedChoices.clear();
	PresentedReview = daedalus::seedsong::GuideReview();
	ReviewedSpring.Reset();
	ReviewedController.Reset();
	ReviewedSpringId.Empty();
	ReviewedSpringPoint = FVector::ZeroVector;
}

bool ADaedalusSeedSong::IsGuideCurrent() const
{
	const ADaedalusHero* Hero = ListeningHero.Get();
	return !bEndingPlay && Hero && Hero->GetWorld() == GetWorld() && Hero->RealmNow() == GuideRealm;
}

daedalus::seedsong::GuideReview ADaedalusSeedSong::CurrentReview() const
{
	daedalus::seedsong::GuideReview Review;
	const FString Next = NextRecord();
	Review.RecordItem = DaedalusSeedSongLocal::ToUtf8(Next);
	if (const daedalus::seedsong::Record* R = IsReady() && !Next.IsEmpty()
		? State->Chapter->Find(Review.RecordItem) : nullptr)
	{
		Review.RecordName = R->T->SeedSong;
	}
	for (const FString& Herb : KettleHerbs) { Review.Herbs.push_back(DaedalusSeedSongLocal::ToUtf8(Herb)); }
	// Restore, Draw and Talk already allocate an event id. Even an external attempt invalidates an old review.
	Review.ProgressRevision = Events;
	return Review;
}

void ADaedalusSeedSong::ShowGuide(daedalus::seedsong::GuidePage Page, const FString& Line)
{
	using namespace daedalus::seedsong;
	if (!IsGuideCurrent()) { StopGuide(); return; }
	ADaedalusHero* Hero = ListeningHero.Get();
	const GuideReview Current = CurrentReview();
	FString Text = Line;
	if (Page == GuidePage::Review)
	{
		if (Current.CanAttempt())
		{
			PresentedReview = Current;
			if (!Text.IsEmpty()) { Text += TEXT("\n"); }
			Text += DaedalusSeedSongLocal::FromUtf8(GuideReviewText(PresentedReview));
		}
		else { Page = GuidePage::Home; }
	}
	if (Page == GuidePage::Home)
	{
		if (!Text.IsEmpty()) { Text += TEXT("\n"); }
		Text += DaedalusSeedSongLocal::FromUtf8(GuideHome(RestoredCount(), RecordCount(), CleanSprings(),
			!Current.RecordItem.empty(), !Current.Herbs.empty()));
	}
	CurrentGuidePage = Page;
	const bool CanGuideSpring = Page == GuidePage::Spring ? IsSpringReviewCurrent()
		: Page == GuidePage::Water && LocalGuideController() && NearbyCleanSpring(Hero);
	PresentedChoices = GuideChoices(Page, !Current.RecordItem.empty(), !Current.Herbs.empty(), CanGuideSpring);
	TArray<FString> Choices;
	for (const GuideChoice& Choice : PresentedChoices) { Choices.Add(DaedalusSeedSongLocal::FromUtf8(Choice.Label)); }
	Hero->Speak(TEXT("Keeper Oriel"), Text, Choices);
}

bool ADaedalusSeedSong::IsGuidanceSpring(const ADaedalusSeedSpring* Spring) const
{
	// Keep the existing one-chapter spring binding and stay within this placed island level. No cross-island
	// destination, unloaded actor, hidden spring or walking route is inferred from a chapter name alone.
	return IsReady() && IsValid(Spring) && !Spring->IsActorBeingDestroyed() && !Spring->IsHidden()
		&& Spring->GetWorld() == GetWorld() && Spring->GetLevel() == GetLevel()
		&& ADaedalusSeedSong::Find(Spring) == this && !Spring->GetActorLocation().ContainsNaN()
		&& State->Chapter->Springs.Clean(DaedalusSeedSongLocal::ToUtf8(Spring->SpringId));
}

ADaedalusSeedSpring* ADaedalusSeedSong::NearbyCleanSpring(const ADaedalusHero* Hero) const
{
	using namespace daedalus::seedsong;
	if (!IsValid(Hero) || Hero->GetWorld() != GetWorld() || Hero->GetActorLocation().ContainsNaN()) { return nullptr; }
	std::vector<GuideSpringTarget> Candidates;
	TArray<ADaedalusSeedSpring*> Actors;
	for (TActorIterator<ADaedalusSeedSpring> It(GetWorld()); It; ++It)
	{
		ADaedalusSeedSpring* Spring = *It;
		if (!IsGuidanceSpring(Spring)) { continue; }
		Actors.Add(Spring);
		Candidates.push_back({DaedalusSeedSongLocal::ToUtf8(Spring->SpringId),
			DaedalusSeedSongLocal::ToUtf8(SpringName(Spring->SpringId)), DaedalusSeedSongLocal::ToUtf8(Spring->GetPathName()),
			FVector::DistSquared(Hero->GetActorLocation(), Spring->GetActorLocation()), true, true});
	}
	const int Index = GuideNearestSpring(Candidates);
	return Actors.IsValidIndex(Index) ? Actors[Index] : nullptr;
}

APlayerController* ADaedalusSeedSong::LocalGuideController() const
{
	if (!IsGuideCurrent()) { return nullptr; }
	APlayerController* Controller = Cast<APlayerController>(ListeningHero->GetController());
	return IsValid(Controller) && Controller->IsLocalController() && Controller->GetPawn() == ListeningHero.Get() ? Controller : nullptr;
}

void ADaedalusSeedSong::ShowWater(const FString& Notice)
{
	using namespace daedalus::seedsong;
	std::vector<GuideSpring> Springs;
	if (IsReady())
		for (const Spring& Source : State->Chapter->Springs.Springs)
			Springs.push_back({Source.Name, State->Chapter->Springs.Clean(Source.Id)});
	FString Text = Notice;
	if (!Text.IsEmpty()) { Text += TEXT("\n"); }
	Text += DaedalusSeedSongLocal::FromUtf8(GuideWaterText(Springs));
	if (Notice.IsEmpty() && !NearbyCleanSpring(ListeningHero.Get()))
		Text += TEXT("\n") + DaedalusSeedSongLocal::FromUtf8(GuideSpringUnavailableText());
	ShowGuide(GuidePage::Water, Text);
}

void ADaedalusSeedSong::ReviewSpring(const FString& Notice)
{
	using namespace daedalus::seedsong;
	if (!IsGuideCurrent()) { StopGuide(); return; }
	ADaedalusSeedSpring* Spring = NearbyCleanSpring(ListeningHero.Get());
	APlayerController* Controller = LocalGuideController();
	if (!Spring || !Controller) { ShowWater(DaedalusSeedSongLocal::FromUtf8(GuideSpringUnavailableText())); return; }
	ReviewedSpring = Spring;
	ReviewedController = Controller;
	ReviewedSpringId = Spring->SpringId;
	ReviewedSpringPoint = Spring->GetActorLocation();
	FString Text = Notice;
	if (!Text.IsEmpty()) { Text += TEXT("\n"); }
	Text += DaedalusSeedSongLocal::FromUtf8(GuideSpringReviewText(DaedalusSeedSongLocal::ToUtf8(SpringName(ReviewedSpringId))));
	ShowGuide(GuidePage::Spring, Text);
}

bool ADaedalusSeedSong::IsSpringReviewCurrent() const
{
	const ADaedalusSeedSpring* Spring = ReviewedSpring.Get();
	return CurrentGuidePage == daedalus::seedsong::GuidePage::Spring && IsGuideCurrent() && GuideHandle.IsValid()
		&& LocalGuideController() && LocalGuideController() == ReviewedController.Get()
		&& IsGuidanceSpring(Spring) && Spring->SpringId == ReviewedSpringId && Spring->GetActorLocation() == ReviewedSpringPoint;
}

bool ADaedalusSeedSong::LookAtReviewedSpring()
{
	if (!IsSpringReviewCurrent()) { return false; }
	ADaedalusHero* Hero = ListeningHero.Get();
	const FVector Point = ReviewedSpringPoint;
	StopGuide();
	Hero->AimAt(Point); // existing control rotation only; native choice outcome closes the conversation
	return true;
}

void ADaedalusSeedSong::OnGuideChoice(const FString& Speaker, int32 Choice)
{
	using namespace daedalus::seedsong;
	if (!IsGuideCurrent() || !GuideHandle.IsValid()) { StopGuide(); return; }
	if (Speaker != TEXT("Keeper Oriel")) { return; }
	const GuideAction Action = GuidePick(PresentedChoices, Choice);
	if (Action == GuideAction::Leave) { StopGuide(); return; }
	if (Action == GuideAction::Listen)
	{
		// Talk can complete the existing quest's talk step. Opening, reading a clue and returning cannot.
		ShowGuide(GuidePage::Listen, Talk());
		return;
	}
	if (Action == GuideAction::Water)
	{
		ShowWater();
		return;
	}
	if (Action == GuideAction::ReviewSpring)
	{
		ReviewSpring();
		return;
	}
	if (Action == GuideAction::LookSpring)
	{
		if (!LookAtReviewedSpring()) { ReviewSpring(DaedalusSeedSongLocal::FromUtf8(GuideSpringChangedText())); }
		return;
	}
	if (Action == GuideAction::Clue)
	{
		const FString Next = NextRecord();
		const Record* R = IsReady() && !Next.IsEmpty() ? State->Chapter->Find(DaedalusSeedSongLocal::ToUtf8(Next)) : nullptr;
		ShowGuide(GuidePage::Clue, R ? DaedalusSeedSongLocal::FromUtf8(Hint(*R)) : TEXT("Every record is mended."));
		return;
	}
	if (Action == GuideAction::Review)
	{
		ShowGuide(GuidePage::Review);
		return;
	}
	if (Action == GuideAction::Confirm)
	{
		if (CurrentGuidePage != GuidePage::Review || !PresentedReview.CanAttempt()
			|| !SameReview(PresentedReview, CurrentReview()))
		{
			ShowGuide(GuidePage::Review, DaedalusSeedSongLocal::FromUtf8(GuideChanged()));
			return;
		}
		const FString RecordItem = DaedalusSeedSongLocal::FromUtf8(PresentedReview.RecordItem);
		const TArray<FString> Herbs = KettleHerbs;
		const FString Outcome = Restore(RecordItem, Herbs);
		KettleHerbs.Reset(); // preserve the original attempted-mend consumption rule, including failed attempts
		Tell(FString::Printf(TEXT("%s: %s (%d of %d mended, %d springs clean)."), *RecordItem, *Outcome, RestoredCount(), RecordCount(), CleanSprings()));
		ShowGuide(GuidePage::Result, DaedalusSeedSongLocal::FromUtf8(GuideResult(DaedalusSeedSongLocal::ToUtf8(Outcome),
			RestoredCount(), RecordCount(), CleanSprings())));
		return;
	}
	ShowGuide(GuidePage::Home);
}

ADaedalusSeedSong* ADaedalusSeedSong::Find(const UObject* WorldContext)
{
	UWorld* World = GEngine ? GEngine->GetWorldFromContextObject(WorldContext, EGetWorldErrorMode::ReturnNull) : nullptr;
	if (!World) { return nullptr; }
	TActorIterator<ADaedalusSeedSong> It(World);
	return It ? *It : nullptr;
}

// ---------------- spring ----------------
ADaedalusSeedSpring::ADaedalusSeedSpring()
{
	bReplicates = false;
	Tags.Add(TEXT("SeedSpring"));
	Tags.Add(TEXT("Interact_SeedSpring"));
	static ConstructorHelpers::FObjectFinder<UStaticMesh> Sphere(TEXT("/Engine/BasicShapes/Sphere.Sphere"));
	if (Sphere.Succeeded())
	{
		Body->SetStaticMesh(Sphere.Object);
		Body->SetRelativeScale3D(FVector(0.7f, 0.7f, 0.25f));
	}
	Glow->SetLightColor(FLinearColor(0.4f, 0.75f, 1.f));
}

FString ADaedalusSeedSpring::Prompt(const ADaedalusHero*) const
{
	const ADaedalusSeedSong* Song = ADaedalusSeedSong::Find(this);
	const FString Name = Song ? Song->SpringName(SpringId) : SpringId;
	return FString::Printf(TEXT("Draw from %s"), *Name);
}

bool ADaedalusSeedSpring::Use(ADaedalusHero*)
{
	ADaedalusSeedSong* Song = ADaedalusSeedSong::Find(this);
	const FString Line = Song ? FString::Printf(TEXT("%s: %s"), *SpringId, *Song->Draw(SpringId)) : FString::Printf(TEXT("%s is dry (no seed song chapter here)."), *SpringId);
	if (UDaedalusOrrery* O = UDaedalusOrrery::Get(this)) { O->Say(Line); }
	UE_LOG(LogTemp, Log, TEXT("Daedalus seed spring: %s"), *Line);
	return Song != nullptr;
}

// ---------------- console ----------------
static FAutoConsoleCommandWithWorldAndArgs GSeedSongRestore(
	TEXT("daedalus.seedsong.restore"),
	TEXT("daedalus.seedsong.restore <Herb> <Herb> <Herb> [...]: mend the next scratched record with these herbs."),
	FConsoleCommandWithWorldAndArgsDelegate::CreateLambda([](const TArray<FString>& Args, UWorld* World)
	{
		ADaedalusSeedSong* S = ADaedalusSeedSong::Find(World);
		if (!S) { UE_LOG(LogTemp, Warning, TEXT("daedalus.seedsong.restore: no ADaedalusSeedSong in this world")); return; }
		const FString Next = S->NextRecord();
		UE_LOG(LogTemp, Log, TEXT("daedalus.seedsong.restore: %s -> %s"), *Next, Next.IsEmpty() ? TEXT("all mended") : *S->Restore(Next, Args));
	}));

static FAutoConsoleCommandWithWorldAndArgs GSeedSongDraw(
	TEXT("daedalus.seedsong.draw"),
	TEXT("daedalus.seedsong.draw <spring_N>: draw from a spring of the seed song chapter."),
	FConsoleCommandWithWorldAndArgsDelegate::CreateLambda([](const TArray<FString>& Args, UWorld* World)
	{
		ADaedalusSeedSong* S = ADaedalusSeedSong::Find(World);
		if (!S || Args.Num() < 1) { UE_LOG(LogTemp, Warning, TEXT("daedalus.seedsong.draw: need a chapter and a spring id")); return; }
		UE_LOG(LogTemp, Log, TEXT("daedalus.seedsong.draw: %s -> %s"), *Args[0], *S->Draw(Args[0]));
	}));

static FAutoConsoleCommandWithWorldAndArgs GSeedSongStatus(
	TEXT("daedalus.seedsong.status"),
	TEXT("daedalus.seedsong.status: records mended, springs clean and the next record."),
	FConsoleCommandWithWorldAndArgsDelegate::CreateLambda([](const TArray<FString>&, UWorld* World)
	{
		ADaedalusSeedSong* S = ADaedalusSeedSong::Find(World);
		if (!S) { UE_LOG(LogTemp, Log, TEXT("daedalus.seedsong.status: no chapter")); return; }
		UE_LOG(LogTemp, Log, TEXT("daedalus.seedsong.status: ready=%d records=%d mended=%d springs=%d next=%s"), S->IsReady() ? 1 : 0, S->RecordCount(), S->RestoredCount(), S->CleanSprings(), *S->NextRecord());
	}));
