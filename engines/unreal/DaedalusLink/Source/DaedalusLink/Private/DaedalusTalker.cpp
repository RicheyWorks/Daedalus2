// SPDX-License-Identifier: MIT

#include "DaedalusTalker.h"

#include "Animation/AnimSequence.h"
#include "AssetRegistry/AssetRegistryModule.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/SkeletalMesh.h"
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
	Figure = CreateDefaultSubobject<USkeletalMeshComponent>(TEXT("Figure"));
	Figure->SetupAttachment(Body);
	Figure->SetRelativeScale3D(FVector(1.f / 0.6f, 1.f / 0.6f, 1.f / 1.8f));
	Figure->SetRelativeLocation(FVector(0.f, 0.f, -50.f));   // feet on the ground: the body cube is 100 cm, scaled x1.8
	Figure->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Figure->SetVisibility(false);
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
	// Sol's rigged export under /Game/Daedalus/Art/Cast/<Id>/: the skeletal mesh and its clips (daedalus_import_cast.py).
	bHasArt = false;
	// Sol's exports spell the realm more than one way (Mob_Brick_ / Mob_Bricks_, Mob_Labyrinth_ / Mob_Lab_): try each.
	FAssetRegistryModule& Reg = FModuleManager::LoadModuleChecked<FAssetRegistryModule>("AssetRegistry");
	TArray<FAssetData> Found;
	FString Id;
	for (const FString& Candidate : ArtIds())
	{
		Reg.Get().GetAssetsByPath(FName(*(TEXT("/Game/Daedalus/Art/Cast/") + Candidate)), Found, true);
		Id = Candidate;
		if (Found.Num()) break;
	}
	ArtFound = Id;
	USkeletalMesh* Mesh = nullptr;
	UAnimSequence* Idle = nullptr;
	UAnimSequence* AnyClip = nullptr;
	for (const FAssetData& D : Found)
	{
		if (D.AssetClassPath.GetAssetName() == USkeletalMesh::StaticClass()->GetFName() && !Mesh) Mesh = ::Cast<USkeletalMesh>(D.GetAsset());
		if (D.AssetClassPath.GetAssetName() == UAnimSequence::StaticClass()->GetFName())
		{
			UAnimSequence* A = ::Cast<UAnimSequence>(D.GetAsset());
			if (!AnyClip) AnyClip = A;
			if (D.AssetName.ToString().Contains(TEXT("Idle"))) Idle = A;
		}
	}
	if (Mesh && Figure)
	{
		Figure->SetSkeletalMesh(Mesh);
		Figure->SetVisibility(true);
		if (UAnimSequence* Clip = Idle ? Idle : AnyClip) { Figure->SetAnimationMode(EAnimationMode::AnimationSingleNode); Figure->PlayAnimation(Clip, true); }
		Body->SetVisibility(false);            // the block was the placeholder; collision stays on the body
		Label->SetRelativeLocation(FVector(0.f, 0.f, 130.f));
		bHasArt = true;
	}
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

TArray<FString> ADaedalusTalker::ArtIds() const
{
	// Mob_<Realm>_<WhoPascal>: Sol's convention (Mob_Gallery_CuratorVell); daedalus_import_cast.talker_asset_id is the twin.
	// Each realm lists every spelling Sol's exports have used, canonical first.
	static const TMap<FString, TArray<FString>> Realms = {{TEXT("gallery-city"), {TEXT("Gallery")}}, {TEXT("parcels"), {TEXT("Parcels")}},
		{TEXT("bricks"), {TEXT("Brick"), TEXT("Bricks")}}, {TEXT("labyrinth"), {TEXT("Labyrinth"), TEXT("Lab")}}, {TEXT("world-zero"), {TEXT("Zero")}}, {TEXT("ocean"), {TEXT("Ocean")}}};
	const TArray<FString>* R = Realms.Find(Cast.ToLower());
	TArray<FString> Spellings;
	if (R) Spellings = *R;
	else
	{
		FString Realm = Cast.Left(Cast.Find(TEXT("-")) > 0 ? Cast.Find(TEXT("-")) : Cast.Len());
		if (Realm.Len()) Realm = Realm.Left(1).ToUpper() + Realm.Mid(1).ToLower();
		Spellings.Add(Realm);
	}
	FString Pascal, Word;
	auto Flush = [&]() { if (Word.Len()) { Pascal += Word.Left(1).ToUpper() + Word.Mid(1); Word.Empty(); } };
	for (const TCHAR C : Who) { if (FChar::IsAlnum(C)) Word.AppendChar(C); else Flush(); }
	Flush();
	TArray<FString> Out;
	for (const FString& Realm : Spellings) Out.Add(FString::Printf(TEXT("Mob_%s_%s"), *Realm, *Pascal));
	return Out;
}

FString ADaedalusTalker::ArtId() const
{
	if (bHasArt && ArtFound.Len()) return ArtFound;
	const TArray<FString> Ids = ArtIds();
	return Ids.Num() ? Ids[0] : FString();
}

FString ADaedalusTalker::Prompt(const ADaedalusHero* Hero) const
{
	return TEXT("Talk to ") + Who;
}

FString ADaedalusTalker::State() const
{
	FString Flags;
	for (const std::string& F : Talk.Flags()) { if (!Flags.IsEmpty()) Flags += TEXT(","); Flags += UTF8_TO_TCHAR(F.c_str()); }
	return FString::Printf(TEXT("who=%s bound=%d where=%s flags=%s talks=%d asking=%d given=%s art=%s:%d"), *Who, Talk.Bound() ? 1 : 0, UTF8_TO_TCHAR(Talk.Where().c_str()), *Flags, Talks, bAsking ? 1 : 0, *Given, *ArtId(), bHasArt ? 1 : 0);
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
	for (const std::string& F : Talk.Flags()) if (F.rfind("gave_", 0) != 0) SharedFlags(GetWorld(), Cast).Add(UTF8_TO_TCHAR(F.c_str()));   // a gift paid is this talker's alone
	// Gifts go into the realm's satchel (the inventory's catalog names them); the script pays each once.
	for (const auto& G : B.Gifts)
	{
		const FString Id = UTF8_TO_TCHAR(G.first.c_str());
		Hero->Satchel.FindOrAdd(Id) += G.second;
		Given += (Given.IsEmpty() ? TEXT("") : TEXT(",")) + Id;
		UE_LOG(LogDaedalus, Log, TEXT("%s gives %s x%d"), *Who, *Id, G.second);
	}
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
