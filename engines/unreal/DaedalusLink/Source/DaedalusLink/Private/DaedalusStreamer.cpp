// SPDX-License-Identifier: MIT

#include "DaedalusStreamer.h"

#include "DaedalusStreamCore.h"
#include "Dom/JsonObject.h"
#include "Engine/LevelStreaming.h"
#include "Engine/World.h"
#include "GameFramework/Pawn.h"
#include "HAL/IConsoleManager.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"

static TAutoConsoleVariable<int32> CVarStream(TEXT("daedalus.Stream"), 1,
	TEXT("1 = load island sublevels by distance, like Minecraft's view distance (ADR-064); 0 = leave them alone."));
static TAutoConsoleVariable<float> CVarLoadKm(TEXT("daedalus.StreamLoadKm"), 1.5f, TEXT("Load an island within this many km of its edge."));
static TAutoConsoleVariable<float> CVarUnloadKm(TEXT("daedalus.StreamUnloadKm"), 2.5f, TEXT("Unload an island beyond this many km of its edge."));
static TAutoConsoleVariable<float> CVarBudgetMiB(TEXT("daedalus.StreamRamBudgetMiB"), 0.f,
	TEXT("0 = no budget; else skip island loads that would pass this many MiB resident (ADR-063 DSB rule, ram_kib in islands.json)."));

namespace
{
	/** In Play-in-Editor the package names carry a "UEDPIE_<n>_" prefix on the last segment; the list doesn't. */
	FString Plain(FString Package)
	{
		int32 Slash = INDEX_NONE;
		Package.FindLastChar(TEXT('/'), Slash);
		const FString Leaf = Package.Mid(Slash + 1);
		if (Leaf.StartsWith(TEXT("UEDPIE_")))
		{
			int32 Under = Leaf.Find(TEXT("_"), ESearchCase::CaseSensitive, ESearchDir::FromStart, 7);
			if (Under != INDEX_NONE) return Package.Left(Slash + 1) + Leaf.Mid(Under + 1);
		}
		return Package;
	}
}

bool UDaedalusStreamer::DoesSupportWorldType(const EWorldType::Type WorldType) const
{
	return WorldType == EWorldType::Game || WorldType == EWorldType::PIE;
}

UDaedalusStreamer* UDaedalusStreamer::GetStreamer(const UObject* WorldContext)
{
	const UWorld* W = WorldContext ? WorldContext->GetWorld() : nullptr;
	return W ? W->GetSubsystem<UDaedalusStreamer>() : nullptr;
}

void UDaedalusStreamer::Initialize(FSubsystemCollectionBase& Collection)
{
	Super::Initialize(Collection);
	Reload();
}

int32 UDaedalusStreamer::Reload()
{
	Isles.Reset();
	FString Text;
	if (!FFileHelper::LoadFileToString(Text, *FPaths::Combine(FPaths::ProjectSavedDir(), TEXT("Daedalus"), TEXT("islands.json")))) return 0;
	TArray<TSharedPtr<FJsonValue>> Rows;
	if (!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text), Rows)) return 0;
	for (const TSharedPtr<FJsonValue>& V : Rows)
	{
		const TSharedPtr<FJsonObject>* O = nullptr;
		if (!V.IsValid() || !V->TryGetObject(O) || !O) continue;
		FIsle I;
		if (!(*O)->TryGetStringField(TEXT("package"), I.Package) || I.Package.IsEmpty()) continue;
		I.Centre = FVector((*O)->GetNumberField(TEXT("x")), (*O)->GetNumberField(TEXT("y")), (*O)->GetNumberField(TEXT("z")));
		I.Radius = FMath::Max(0.0, (*O)->GetNumberField(TEXT("radius")));
		(*O)->TryGetBoolField(TEXT("always"), I.bAlways);
		double Ram = 0;
		if ((*O)->TryGetNumberField(TEXT("ram_kib"), Ram)) I.RamKiB = FMath::Max(0.0, Ram);
		Isles.Add(I);
	}
	return Isles.Num();
}

void UDaedalusStreamer::Tick(float DeltaTime)
{
	Next -= DeltaTime;
	if (Next > 0.f || CVarStream.GetValueOnGameThread() == 0 || Isles.Num() == 0) return;
	Next = 0.5f;
	UWorld* W = GetWorld();
	const APawn* Player = UGameplayStatics::GetPlayerPawn(this, 0);
	if (!W || !Player) return;
	// The listed islands that exist in this world, as the core sees them.
	TMap<FString, ULevelStreaming*> Levels;
	for (ULevelStreaming* L : W->GetStreamingLevels())
		if (L) Levels.Add(Plain(L->GetWorldAssetPackageName()), L);
	std::vector<daedalus::stream::Island> In;
	for (const FIsle& I : Isles)
		if (ULevelStreaming* const* L = Levels.Find(I.Package))
			In.push_back({TCHAR_TO_UTF8(*I.Package), I.Centre.X, I.Centre.Y, I.Centre.Z, I.Radius, (*L)->ShouldBeLoaded(), I.bAlways, I.RamKiB});
	daedalus::stream::Settings S;
	S.LoadDistance = CVarLoadKm.GetValueOnGameThread() * 100000.0;
	S.UnloadDistance = CVarUnloadKm.GetValueOnGameThread() * 100000.0;
	S.RamBudgetKiB = FMath::Max(0.f, CVarBudgetMiB.GetValueOnGameThread()) * 1024.0;
	const FVector P = Player->GetActorLocation();
	for (const daedalus::stream::Step& Step : daedalus::stream::Plan(In, P.X, P.Y, P.Z, S))
	{
		ULevelStreaming* L = Levels.FindRef(UTF8_TO_TCHAR(Step.Name.c_str()));
		if (!L) continue;
		const bool bLoad = Step.Do == daedalus::stream::Act::Load;
		L->SetShouldBeLoaded(bLoad);
		L->SetShouldBeVisible(bLoad);
		(bLoad ? Loads : Unloads)++;
		Last = FString::Printf(TEXT("%s %s at %.0f m"), bLoad ? TEXT("load") : TEXT("unload"), *Plain(L->GetWorldAssetPackageName()), Step.Distance / 100.0);
		UE_LOG(LogTemp, Log, TEXT("DaedalusStreamer: %s"), *Last);
	}
}

FString UDaedalusStreamer::Stats() const
{
	int32 Loaded = 0;
	if (const UWorld* W = GetWorld())
		for (const ULevelStreaming* L : W->GetStreamingLevels())
			if (L && L->ShouldBeLoaded()) ++Loaded;
	return FString::Printf(TEXT("listed=%d loaded=%d loads=%d unloads=%d last=%s"), Isles.Num(), Loaded, Loads, Unloads, *Last);
}
