// SPDX-License-Identifier: MIT

#include "DaedalusTalker.h"

#include "Components/StaticMeshComponent.h"
#include "Components/TextRenderComponent.h"
#include "DaedalusHero.h"
#include "DaedalusLinkModule.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"

ADaedalusTalker::ADaedalusTalker()
{
	Body->SetCollisionProfileName(TEXT("Pawn"));
	if (UStaticMesh* Cube = LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Cube.Cube")))
	{
		Body->SetStaticMesh(Cube);
		Body->SetRelativeScale3D(FVector(0.6f, 0.6f, 1.8f));
	}
	Label = CreateDefaultSubobject<UTextRenderComponent>(TEXT("Label"));
	Label->SetupAttachment(Body);
	Label->SetHorizontalAlignment(EHTA_Center);
	Label->SetWorldSize(22.f);
	Label->SetTextRenderColor(FColor(235, 225, 200));
	Label->SetRelativeLocation(FVector(0.f, 0.f, 120.f));
	Label->SetRelativeScale3D(FVector(1.f / 0.6f, 1.f / 0.6f, 1.f / 1.8f));   // undo the body's stretch
	Tags.Add(TEXT("DaedalusTalker"));
}

TSet<FString>& ADaedalusTalker::SharedFlags(const UWorld* World, const FString& Cast)
{
	static TMap<FString, TSet<FString>> ByKey;
	return ByKey.FindOrAdd(FString::Printf(TEXT("%p:%s"), World, *Cast));
}

bool ADaedalusTalker::Rebind()
{
	const FString Path = FPaths::Combine(FPaths::ProjectPluginsDir(), TEXT("DaedalusLink"), TEXT("Content"), TEXT("Casts"), Cast + TEXT(".dcs"));
	FString Text;
	if (!FFileHelper::LoadFileToString(Text, *Path)) { UE_LOG(LogDaedalus, Warning, TEXT("Talker %s: no cast at %s"), *Who, *Path); return false; }
	TSharedPtr<daedalus::cast::Cast> C = MakeShared<daedalus::cast::Cast>();
	std::string Err;
	if (!C->Parse(TCHAR_TO_UTF8(*Text), Err)) { UE_LOG(LogDaedalus, Warning, TEXT("Talker %s: cast %s: %s"), *Who, *Cast, UTF8_TO_TCHAR(Err.c_str())); return false; }
	const daedalus::cast::Script* S = C->Find(TCHAR_TO_UTF8(*Who));
	if (!S) { UE_LOG(LogDaedalus, Warning, TEXT("Talker: %s is not in cast %s"), *Who, *Cast); return false; }
	Script = C;
	Talk.Bind(S);
	if (!Progress.IsEmpty()) Talk.Restore(TCHAR_TO_UTF8(*Progress));
	if (Label) Label->SetText(FText::FromString(Who));
	// Sol's export, when it shipped: Mob_<Cast>_<Who> with spaces and dashes as underscores.
	FString Asset = FString::Printf(TEXT("Mob_%s_%s"), *Cast, *Who);
	Asset.ReplaceInline(TEXT(" "), TEXT("_")); Asset.ReplaceInline(TEXT("-"), TEXT("_"));
	if (SetArt(TEXT("Mobs"), Asset, 1.f)) Label->SetRelativeScale3D(FVector(1.f));
	return true;
}

void ADaedalusTalker::BeginPlay()
{
	Super::BeginPlay();
	Rebind();
}

void ADaedalusTalker::EndPlay(const EEndPlayReason::Type Reason)
{
	if (ADaedalusHero* H = Talking.Get()) if (ChoiceHandle.IsValid()) H->OnDialogueChoice.Remove(ChoiceHandle);
	Super::EndPlay(Reason);
}

FString ADaedalusTalker::Prompt(const ADaedalusHero* Hero) const
{
	return TEXT("Talk to ") + Who;
}

FString ADaedalusTalker::State() const
{
	FString Flags;
	for (const std::string& F : Talk.Flags()) { if (!Flags.IsEmpty()) Flags += TEXT(","); Flags += UTF8_TO_TCHAR(F.c_str()); }
	return FString::Printf(TEXT("who=%s bound=%d where=%s flags=%s talks=%d asking=%d"), *Who, Talk.Bound() ? 1 : 0, UTF8_TO_TCHAR(Talk.Where().c_str()), *Flags, Talks, bAsking ? 1 : 0);
}

bool ADaedalusTalker::Use(ADaedalusHero* Hero)
{
	if (!Hero || !Talk.Bound() || Hero->IsDialogueOpen()) return false;
	// Realm-wide flags other talkers set (the Choir sings once the Curator's quest is done).
	std::string Line = Talk.Save();
	for (const FString& F : SharedFlags(GetWorld(), Cast)) Line += " " + std::string(TCHAR_TO_UTF8(*F));
	Talk.Restore(Line);
	++Talks;
	Talking = Hero;
	if (!ChoiceHandle.IsValid()) ChoiceHandle = Hero->OnDialogueChoice.AddUObject(this, &ADaedalusTalker::OnChoice);
	Continue(Hero, -1);
	return true;
}

void ADaedalusTalker::Continue(ADaedalusHero* Hero, int32 Choice)
{
	daedalus::cast::Beat B = Choice >= 0 ? Talk.Picked(Choice) : Talk.Talk();
	Deliver(Hero, B);
}

void ADaedalusTalker::Deliver(ADaedalusHero* Hero, const daedalus::cast::Beat& B)
{
	Progress = UTF8_TO_TCHAR(Talk.Save().c_str());
	for (const std::string& F : Talk.Flags()) SharedFlags(GetWorld(), Cast).Add(UTF8_TO_TCHAR(F.c_str()));
	if (B.Over)
	{
		bAsking = false;
		if (ChoiceHandle.IsValid()) { Hero->OnDialogueChoice.Remove(ChoiceHandle); ChoiceHandle.Reset(); }
		Talking = nullptr;
		return;
	}
	TArray<FString> Choices;
	for (const std::string& C : B.Choices) Choices.Add(UTF8_TO_TCHAR(C.c_str()));
	bAsking = !Choices.IsEmpty();
	Hero->Speak(Who, UTF8_TO_TCHAR(B.Text.c_str()), Choices);
}

void ADaedalusTalker::OnChoice(const FString& Speaker, int32 Choice)
{
	ADaedalusHero* Hero = Talking.Get();
	if (!Hero || Speaker != Who) return;
	// A plain line closed (Choice -1): say the next one; a choice: branch.
	Continue(Hero, bAsking ? Choice : -1);
}
