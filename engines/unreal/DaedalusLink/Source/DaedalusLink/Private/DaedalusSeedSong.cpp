// SPDX-License-Identifier: MIT

#include "DaedalusSeedSong.h"
#include "Components/PointLightComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/Engine.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "EngineUtils.h"
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

FString ADaedalusSeedSong::Talk()
{
	if (!Ensure()) { return FString(); }
	return DaedalusSeedSongLocal::FromUtf8(State->Chapter->Talk(DaedalusSeedSongLocal::ToUtf8(NextEvent())));
}

FString ADaedalusSeedSong::Prompt(const ADaedalusHero*) const
{
	const FString Next = NextRecord();
	if (Next.IsEmpty()) { return TEXT("Talk to the gramophone"); }
	return KettleHerbs.Num() > 0 ? FString::Printf(TEXT("Mend %s"), *Next) : FString::Printf(TEXT("Listen to %s"), *Next);
}

bool ADaedalusSeedSong::Use(ADaedalusHero*)
{
	if (!Ensure()) { Tell(TEXT("The gramophone is silent (no tunes).")); return false; }
	const FString Next = NextRecord();
	if (Next.IsEmpty() || KettleHerbs.Num() == 0)
	{
		Tell(Talk());
		if (const daedalus::seedsong::Record* R = Next.IsEmpty() ? nullptr : State->Chapter->Find(DaedalusSeedSongLocal::ToUtf8(Next)))
		{
			Tell(DaedalusSeedSongLocal::FromUtf8(daedalus::seedsong::Hint(*R)));
		}
		return true;
	}
	const FString Outcome = Restore(Next, KettleHerbs);
	KettleHerbs.Reset();
	Tell(FString::Printf(TEXT("%s: %s (%d of %d mended, %d springs clean)."), *Next, *Outcome, RestoredCount(), RecordCount(), CleanSprings()));
	return true;
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
	return FString::Printf(TEXT("Draw from %s"), *SpringId);
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