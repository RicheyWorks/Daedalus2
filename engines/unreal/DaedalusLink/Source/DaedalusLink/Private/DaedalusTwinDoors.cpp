// SPDX-License-Identifier: MIT

#include "DaedalusTwinDoors.h"
#include "DaedalusHero.h"
#include "Components/PointLightComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/Engine.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "HAL/IConsoleManager.h"
#include "UObject/ConstructorHelpers.h"

// Named (not anonymous) so unity builds cannot collide with other files' helpers.
namespace DaedalusTwinDoorsLocal
{
daedalus::twindoors::Question ToCore(EDaedalusTwinQuestion Q) { return static_cast<daedalus::twindoors::Question>(static_cast<uint8>(Q)); }
const TCHAR* GuardName(int32 Guard) { return Guard == 0 ? TEXT("The left guard") : TEXT("The right guard"); }
const TCHAR* DoorName(int32 Door) { return Door == 0 ? TEXT("left") : TEXT("right"); }
UStaticMeshComponent* MakePart(AActor* Owner, USceneComponent* Parent, const TCHAR* Name, UStaticMesh* Mesh, const FVector& At, const FVector& Scale)
{
	UStaticMeshComponent* C = Owner->CreateDefaultSubobject<UStaticMeshComponent>(Name);
	C->SetupAttachment(Parent);
	if (Mesh) { C->SetStaticMesh(Mesh); }
	C->SetRelativeLocation(At);
	C->SetRelativeScale3D(Scale);
	return C;
}
ADaedalusTwinDoors* FirstTwinDoors(UWorld* World)
{
	if (!World) { return nullptr; }
	TActorIterator<ADaedalusTwinDoors> It(World);
	return It ? *It : nullptr;
}
}

ADaedalusTwinDoors::ADaedalusTwinDoors()
{
	PrimaryActorTick.bCanEverTick = true;
	bReplicates = false;
	Tags.Add(TEXT("TwinDoors"));
	Tags.Add(TEXT("Interact_TwinDoors"));
	static ConstructorHelpers::FObjectFinder<UStaticMesh> Cube(TEXT("/Engine/BasicShapes/Cube.Cube"));
	static ConstructorHelpers::FObjectFinder<UStaticMesh> Cylinder(TEXT("/Engine/BasicShapes/Cylinder.Cylinder"));
	UStaticMesh* CubeMesh = Cube.Succeeded() ? Cube.Object : nullptr;
	UStaticMesh* PillarMesh = Cylinder.Succeeded() ? Cylinder.Object : nullptr;
	// Frame: a lintel 4 m wide at 2.6 m. Doors are 1.4 x 2.4 m, each hanging from a hinge at its outer edge (y = -/+220 cm),
	// so rotating the hinge swings the door. Guards stand in front of the frame.
	Body->SetCollisionProfileName(TEXT("NoCollision"));
	Frame = DaedalusTwinDoorsLocal::MakePart(this, Body, TEXT("Frame"), CubeMesh, FVector(0.f, 0.f, 260.f), FVector(0.3f, 4.f, 0.4f));
	HingeA = CreateDefaultSubobject<USceneComponent>(TEXT("HingeA"));
	HingeA->SetupAttachment(Body);
	HingeA->SetRelativeLocation(FVector(0.f, -220.f, 0.f));
	HingeB = CreateDefaultSubobject<USceneComponent>(TEXT("HingeB"));
	HingeB->SetupAttachment(Body);
	HingeB->SetRelativeLocation(FVector(0.f, 220.f, 0.f));
	DoorA = DaedalusTwinDoorsLocal::MakePart(this, HingeA, TEXT("DoorA"), CubeMesh, FVector(0.f, 70.f, 120.f), FVector(0.1f, 1.4f, 2.4f));
	DoorB = DaedalusTwinDoorsLocal::MakePart(this, HingeB, TEXT("DoorB"), CubeMesh, FVector(0.f, -70.f, 120.f), FVector(0.1f, 1.4f, 2.4f));
	GuardA = DaedalusTwinDoorsLocal::MakePart(this, Body, TEXT("GuardA"), PillarMesh, FVector(150.f, -260.f, 100.f), FVector(0.5f, 0.5f, 2.f));
	GuardB = DaedalusTwinDoorsLocal::MakePart(this, Body, TEXT("GuardB"), PillarMesh, FVector(150.f, 260.f, 100.f), FVector(0.5f, 0.5f, 2.f));
	for (UStaticMeshComponent* C : {Frame.Get(), DoorA.Get(), DoorB.Get(), GuardA.Get(), GuardB.Get()})
	{
		C->SetMobility(EComponentMobility::Movable);
		C->SetCollisionProfileName(TEXT("BlockAllDynamic"));
	}
	Glow->SetLightColor(FLinearColor(0.55f, 0.6f, 0.9f));
}

void ADaedalusTwinDoors::BeginPlay()
{
	Super::BeginPlay();
	ResetRiddle();
}

void ADaedalusTwinDoors::ResetRiddle()
{
	StopGuide(); // an answer to an old visible menu must not choose a door in the new riddle
	++RiddleRevision;
	Riddle = MakeUnique<daedalus::twindoors::Riddle>(static_cast<int64_t>(Seed), Difficulty);
	Run = MakeUnique<daedalus::twindoors::Session>(*Riddle);
	if (!Riddle->Valid()) { UE_LOG(LogTemp, Warning, TEXT("Daedalus twin doors: difficulty %d is not 0 or 1; using %d"), Difficulty, Riddle->GetDifficulty()); }
	bSolved = false;
	OpenDoor = -1;
	SwingT = 0.f;
	HingeA->SetRelativeRotation(FRotator::ZeroRotator);
	HingeB->SetRelativeRotation(FRotator::ZeroRotator);
}

bool ADaedalusTwinDoors::HasAsked() const { return Run.IsValid() && Run->Asked(); }

int32 ADaedalusTwinDoors::Deduced() const
{
	if (!HasAsked()) { return -1; }
	return daedalus::twindoors::Deduce(Riddle->GetDifficulty(), HeardGuard, HeardQuestion, HeardDoor, Run->HeardTone());
}

bool ADaedalusTwinDoors::Ask(int32 Guard, EDaedalusTwinQuestion Question, int32 Door)
{
	if (!Run.IsValid()) { ResetRiddle(); }
	daedalus::twindoors::Tone Heard = daedalus::twindoors::Tone::High;
	const daedalus::twindoors::Step S = Run->Ask(Guard, DaedalusTwinDoorsLocal::ToCore(Question), Door, Heard);
	if (S == daedalus::twindoors::Step::AlreadyAsked) { Tell(TEXT("The guards answer only one question. Choose a door.")); return false; }
	if (S != daedalus::twindoors::Step::Ok) { Tell(TEXT("There are two guards and two doors (0 or 1).")); return false; }
	HeardGuard = Guard;
	HeardDoor = Door;
	HeardQuestion = DaedalusTwinDoorsLocal::ToCore(Question);
	const bool bLow = Heard == daedalus::twindoors::Tone::Low;
	Tell(FString::Printf(TEXT("%s rings the %s bell (%.3f Hz)."), DaedalusTwinDoorsLocal::GuardName(Guard), bLow ? TEXT("low") : TEXT("high"), daedalus::twindoors::Hz(Heard)));
	OnBell.Broadcast(Guard, bLow, static_cast<float>(daedalus::twindoors::Hz(Heard)));
	return true;
}

bool ADaedalusTwinDoors::Choose(int32 Door)
{
	if (!Run.IsValid()) { ResetRiddle(); }
	bool bOpened = false;
	const daedalus::twindoors::Step S = Run->Choose(Door, bOpened);
	if (S == daedalus::twindoors::Step::AskFirst) { Tell(TEXT("Ask one guard one question first.")); return false; }
	if (S == daedalus::twindoors::Step::AlreadyChosen) { Tell(bSolved ? TEXT("The archive is already open.") : TEXT("You already chose.")); return false; }
	if (S != daedalus::twindoors::Step::Ok) { Tell(TEXT("There are only two doors (0 or 1).")); return false; }
	StopGuide(); // Blueprint/console choices invalidate a currently visible conversation too
	if (bOpened)
	{
		bSolved = true;
		OpenDoor = Door;
		SwingT = 0.f;
		Tell(UTF8_TO_TCHAR(daedalus::twindoors::GuideResult(Door, true).c_str()));
		OnDoorPicked.Broadcast(Door, true); // listeners observe the applied state and may safely reset it
		return true;
	}
	Tell(UTF8_TO_TCHAR(daedalus::twindoors::GuideResult(Door, false).c_str()));
	Seed += 1;
	ResetRiddle();
	OnDoorPicked.Broadcast(Door, false);
	return false;
}

void ADaedalusTwinDoors::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	if (GuideHandle.IsValid() && (!IsGuideCurrent() || !ListeningHero->IsDialogueOpen())) { StopGuide(); }
	if (OpenDoor < 0 || SwingT >= 1.f) { return; }
	SwingT = FMath::Min(1.f, SwingT + DeltaSeconds / FMath::Max(0.1f, SwingSeconds));
	const float Eased = FMath::InterpEaseInOut(0.f, 1.f, SwingT, 2.f);
	USceneComponent* H = OpenDoor == 0 ? HingeA : HingeB;
	H->SetRelativeRotation(FRotator(0.f, (OpenDoor == 0 ? OpenYawA : OpenYawB) * Eased, 0.f));
}

void ADaedalusTwinDoors::EndPlay(const EEndPlayReason::Type Reason)
{
	bEndingPlay = true;
	StopGuide();
	Super::EndPlay(Reason);
}

FString ADaedalusTwinDoors::Prompt(const ADaedalusHero* Hero) const
{
	if (bSolved) { return TEXT("The archive is open"); }
	return HasAsked() ? TEXT("Choose a door with the guards") : TEXT("Talk to the guards");
}

bool ADaedalusTwinDoors::Use(ADaedalusHero* Hero)
{
	if (bEndingPlay || !IsValid(Hero) || Hero->GetWorld() != GetWorld() || Hero->IsDialogueOpen()) { return false; }
	if (ADaedalusHero* Listener = ListeningHero.Get())
		if (Listener->IsDialogueOpen()) { return false; }
	StopGuide();
	if (bSolved)
	{
		Hero->Speak(TEXT("Twin Doors"), TEXT("The archive is already open. Take your time exploring."), {});
		return Hero->IsDialogueOpen();
	}
	if (!Run.IsValid()) { ResetRiddle(); }
	ListeningHero = Hero;
	GuideRealm = Hero->RealmNow();
	GuideRevision = RiddleRevision;
	GuideHandle = Hero->OnDialogueChoice.AddUObject(this, &ADaedalusTwinDoors::OnGuideChoice);
	ShowGuide(HasAsked() ? daedalus::twindoors::GuidePage::Doors : daedalus::twindoors::GuidePage::Welcome);
	// Speak can decline to open over another menu. Opening a conversation spends no question and picks no door.
	if (!Hero->IsDialogueOpen()) { StopGuide(); return false; }
	return true;
}

void ADaedalusTwinDoors::StopGuide()
{
	if (ADaedalusHero* Hero = ListeningHero.Get())
		if (GuideHandle.IsValid()) { Hero->OnDialogueChoice.Remove(GuideHandle); }
	GuideHandle.Reset();
	ListeningHero.Reset();
	GuideRealm.Empty();
}

bool ADaedalusTwinDoors::IsGuideCurrent() const
{
	const ADaedalusHero* Hero = ListeningHero.Get();
	return !bEndingPlay && Hero && Hero->GetWorld() == GetWorld()
		&& Hero->RealmNow() == GuideRealm && GuideRevision == RiddleRevision;
}

void ADaedalusTwinDoors::ShowGuide(daedalus::twindoors::GuidePage Page)
{
	using namespace daedalus::twindoors;
	ADaedalusHero* Hero = ListeningHero.Get();
	if (!IsGuideCurrent()) { StopGuide(); return; }
	CurrentGuidePage = Page;
	std::string Text;
	if (Page == GuidePage::Welcome)
	{
		PresentedQuestion = AskQuestion;
		PresentedGuard = AskGuard;
		PresentedDoor = AskDoor;
		Text = GuideWelcome(DaedalusTwinDoorsLocal::ToCore(PresentedQuestion), PresentedGuard, PresentedDoor);
	}
	else if (HasAsked())
		Text = Page == GuidePage::Clue
			? GuideClue(Riddle->GetDifficulty(), HeardGuard, HeardQuestion, HeardDoor, Run->HeardTone())
			: GuideAnswer(HeardQuestion, HeardGuard, HeardDoor, Run->HeardTone());
	else { StopGuide(); return; }
	TArray<FString> Choices;
	for (const GuideChoice& Choice : GuideChoices(Page)) { Choices.Add(UTF8_TO_TCHAR(Choice.Label.c_str())); }
	Hero->Speak(TEXT("Twin Doors"), UTF8_TO_TCHAR(Text.c_str()), Choices);
}

void ADaedalusTwinDoors::OnGuideChoice(const FString& Speaker, int32 Choice)
{
	using namespace daedalus::twindoors;
	ADaedalusHero* Hero = ListeningHero.Get();
	if (!IsGuideCurrent() || !GuideHandle.IsValid()) { StopGuide(); return; }
	if (Speaker != TEXT("Twin Doors")) { return; }
	const GuideAction Action = GuidePick(CurrentGuidePage, Choice);
	if (Action == GuideAction::Leave || bSolved) { StopGuide(); return; }
	if (Action == GuideAction::Ask)
	{
		if (!Ask(PresentedGuard, PresentedQuestion, PresentedDoor))
		{
			StopGuide();
			Hero->Speak(TEXT("Twin Doors"), Line, {});
			return;
		}
		// OnBell listeners may reset the puzzle. ResetRiddle removes this conversation's subscription.
		if (IsGuideCurrent() && HasAsked() && !bSolved) { ShowGuide(GuidePage::Doors); }
		return;
	}
	if (!HasAsked()) { StopGuide(); return; }
	if (Action == GuideAction::Left || Action == GuideAction::Right)
	{
		// Choose can reset the puzzle. Release the old menu first, and never infer a door from player position.
		const TWeakObjectPtr<ADaedalusHero> Listener = ListeningHero;
		const FString Realm = GuideRealm;
		const uint64 Revision = RiddleRevision;
		StopGuide();
		const int32 Door = Action == GuideAction::Left ? 0 : 1;
		const bool bOpened = Choose(Door);
		// Synchronous door listeners may end a participant, change realms, or reset again. Do not speak stale results.
		Hero = Listener.Get();
		if (!bEndingPlay && Hero && Hero->GetWorld() == GetWorld() && Hero->RealmNow() == Realm
			&& RiddleRevision == Revision + (bOpened ? 0u : 1u) && bSolved == bOpened
			&& (bOpened || !HasAsked()))
		{
			// A refused external Ask/Choose may overwrite LastLine without invalidating the riddle.
			Hero->Speak(TEXT("Twin Doors"), UTF8_TO_TCHAR(GuideResult(Door, bOpened).c_str()), {});
		}
		return;
	}
	if (Action == GuideAction::Repeat)
	{
		const Tone Heard = Run->HeardTone();
		OnBell.Broadcast(HeardGuard, Heard == Tone::Low, static_cast<float>(Hz(Heard)));
		if (!IsGuideCurrent() || !HasAsked() || bSolved) { StopGuide(); return; }
	}
	ShowGuide(Action == GuideAction::Clue ? GuidePage::Clue : GuidePage::Doors);
}

FString ADaedalusTwinDoors::Wire() const
{
	return Riddle.IsValid() ? FString(UTF8_TO_TCHAR(Riddle->ToWire().c_str())) : FString();
}

FString ADaedalusTwinDoors::Status() const
{
	return FString::Printf(TEXT("seed %lld, difficulty %d, asked %s, deduced %d, solved %s"), static_cast<long long>(Seed), Difficulty,
	                       HasAsked() ? TEXT("yes") : TEXT("no"), Deduced(), bSolved ? TEXT("yes") : TEXT("no"));
}

void ADaedalusTwinDoors::Tell(const FString& Text)
{
	Line = Text;
	UE_LOG(LogTemp, Log, TEXT("Daedalus twin doors: %s"), *Text);
	if (GEngine) { GEngine->AddOnScreenDebugMessage(-1, 5.f, FColor(170, 180, 240), Text); }
}

static FAutoConsoleCommandWithWorldAndArgs GTwinDoorsAsk(
	TEXT("daedalus.twindoors.ask"), TEXT("daedalus.twindoors.ask <guard 0|1> <direct|other|embedded|self> <door 0|1>: ask the one question"),
	FConsoleCommandWithWorldAndArgsDelegate::CreateLambda([](const TArray<FString>& Args, UWorld* World)
	{
		ADaedalusTwinDoors* D = DaedalusTwinDoorsLocal::FirstTwinDoors(World);
		if (!D || Args.Num() < 3) { UE_LOG(LogTemp, Warning, TEXT("daedalus.twindoors.ask: no twin doors in the world, or missing arguments")); return; }
		const FString Q = Args[1].ToLower();
		const EDaedalusTwinQuestion E = Q.StartsWith(TEXT("dir")) ? EDaedalusTwinQuestion::Direct
			: Q.StartsWith(TEXT("oth")) ? EDaedalusTwinQuestion::OtherGuard
			: Q.StartsWith(TEXT("self")) ? EDaedalusTwinQuestion::Self : EDaedalusTwinQuestion::Embedded;
		D->Ask(FCString::Atoi(*Args[0]), E, FCString::Atoi(*Args[2]));
	}));

static FAutoConsoleCommandWithWorldAndArgs GTwinDoorsChoose(
	TEXT("daedalus.twindoors.choose"), TEXT("daedalus.twindoors.choose <door 0|1>: open a door after asking"),
	FConsoleCommandWithWorldAndArgsDelegate::CreateLambda([](const TArray<FString>& Args, UWorld* World)
	{
		ADaedalusTwinDoors* D = DaedalusTwinDoorsLocal::FirstTwinDoors(World);
		if (!D || Args.Num() < 1) { UE_LOG(LogTemp, Warning, TEXT("daedalus.twindoors.choose: no twin doors in the world, or no door")); return; }
		D->Choose(FCString::Atoi(*Args[0]));
	}));

static FAutoConsoleCommandWithWorldAndArgs GTwinDoorsStatus(
	TEXT("daedalus.twindoors.status"), TEXT("daedalus.twindoors.status: seed, difficulty, asked, deduced, solved"),
	FConsoleCommandWithWorldAndArgsDelegate::CreateLambda([](const TArray<FString>&, UWorld* World)
	{
		ADaedalusTwinDoors* D = DaedalusTwinDoorsLocal::FirstTwinDoors(World);
		UE_LOG(LogTemp, Log, TEXT("Daedalus twin doors: %s"), D ? *D->Status() : TEXT("none in the world"));
	}));
