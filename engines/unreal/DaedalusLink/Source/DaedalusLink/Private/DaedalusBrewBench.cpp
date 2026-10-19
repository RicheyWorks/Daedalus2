// SPDX-License-Identifier: MIT

#include "DaedalusBrewBench.h"
#include "DaedalusTonicCore.h"
#include "Components/PointLightComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "HAL/IConsoleManager.h"
#include "HAL/PlatformMisc.h"
#include "HttpModule.h"
#include "Interfaces/IHttpRequest.h"
#include "Interfaces/IHttpResponse.h"
#include "UObject/ConstructorHelpers.h"

// Named (not anonymous) so unity builds cannot collide with the helpers in DaedalusTonic.cpp.
namespace DaedalusBrewBenchLocal
{
std::string ToUtf8(const FString& S) { return std::string(TCHAR_TO_UTF8(*S)); }
FString FromUtf8(const std::string& S) { return FString(UTF8_TO_TCHAR(S.c_str())); }
bool BearerOk(const FString& Token)
{
	if (Token.IsEmpty() || Token.Len() > 8192) { return false; }
	for (TCHAR C : Token) { if (!((C >= 'a' && C <= 'z') || (C >= 'A' && C <= 'Z') || (C >= '0' && C <= '9') || C == '.' || C == '_' || C == '-')) { return false; } }
	return true;
}
bool RecordIdOk(const FString& Id)
{
	if (Id.IsEmpty() || Id.Len() > 128) { return false; }
	for (TCHAR C : Id) { if (!((C >= 'a' && C <= 'z') || (C >= 'A' && C <= 'Z') || (C >= '0' && C <= '9') || C == '_')) { return false; } }
	return true;
}
}

// ---------------- bench ----------------
ADaedalusBrewBench::ADaedalusBrewBench()
{
	bReplicates = false;
	Tags.Add(TEXT("BrewBench"));
	Tags.Add(TEXT("Interact_BrewMelody"));
	static ConstructorHelpers::FObjectFinder<UStaticMesh> Cylinder(TEXT("/Engine/BasicShapes/Cylinder.Cylinder"));
	if (Cylinder.Succeeded())
	{
		Body->SetStaticMesh(Cylinder.Object);
		Body->SetRelativeScale3D(FVector(0.8f, 0.8f, 0.6f));
	}
	Glow->SetLightColor(FLinearColor(0.55f, 0.9f, 0.6f));
}

FString ADaedalusBrewBench::Prompt(const ADaedalusHero*) const
{
	if (IsBrewing()) { return TEXT("The kettle is singing..."); }
	return FString::Printf(TEXT("Brew a melody (%d herbs, %d records heard)"), Herbs.Num(), Records.Num());
}

bool ADaedalusBrewBench::Use(ADaedalusHero*)
{
	if (IsBrewing()) { Tell(TEXT("The kettle is still singing.")); return false; }
	if (Herbs.Num() < daedalus::brewmelody::MinHerbs)
	{
		Tell(FString::Printf(TEXT("The kettle needs %d to %d island herbs (it has %d)."), daedalus::brewmelody::MinHerbs, daedalus::brewmelody::MaxHerbs, Herbs.Num()));
		return false;
	}
	return Brew();
}

void ADaedalusBrewBench::Tell(const FString& Line) const
{
	if (UDaedalusOrrery* O = UDaedalusOrrery::Get(this)) { O->Say(Line); }
	UE_LOG(LogTemp, Log, TEXT("Daedalus brew: %s"), *Line);
}

bool ADaedalusBrewBench::ConfigureSession(const FString& Origin, const FString& Token)
{
	if (!IsInGameThread() || !daedalus::tonic::OriginAllowed(DaedalusBrewBenchLocal::ToUtf8(Origin)) || !DaedalusBrewBenchLocal::BearerOk(Token)) { return false; }
	ClearSession();
	ServerOrigin = Origin; BearerToken = Token;
	return true;
}

void ADaedalusBrewBench::ClearSession()
{
	++Generation;
	auto Old = Pending; Pending.Reset();
	ServerOrigin.Reset(); BearerToken.Reset();
	if (Old) { Old->OnProcessRequestComplete().Unbind(); Old->CancelRequest(); }
}

bool ADaedalusBrewBench::HasSession()
{
	if (!BearerToken.IsEmpty()) { return true; }
	// Same auth posture as /api/v1/kennel/brew (contract README), so the kennel session is the fallback.
	for (const TCHAR* Prefix : { TEXT("DAEDALUS_BREW"), TEXT("DAEDALUS_KENNEL") })
	{
		const FString Origin = FPlatformMisc::GetEnvironmentVariable(*(FString(Prefix) + TEXT("_ORIGIN")));
		const FString Token = FPlatformMisc::GetEnvironmentVariable(*(FString(Prefix) + TEXT("_TOKEN")));
		if (!Origin.IsEmpty() && ConfigureSession(Origin, Token)) { return true; }
	}
	return false;
}

void ADaedalusBrewBench::EndPlay(const EEndPlayReason::Type Reason)
{
	ClearSession();
	Super::EndPlay(Reason);
}

bool ADaedalusBrewBench::AddHerb(const FString& Herb)
{
	if (IsBrewing() || Herbs.Num() >= daedalus::brewmelody::MaxHerbs || !daedalus::brewmelody::KnownHerb(DaedalusBrewBenchLocal::ToUtf8(Herb))) { return false; }
	Herbs.Add(Herb);
	return true;
}

void ADaedalusBrewBench::ClearKettle()
{
	if (IsBrewing()) { return; }
	Herbs.Reset(); Stages.Reset();
}

bool ADaedalusBrewBench::RecordPlayed(const FString& RecordId)
{
	if (!DaedalusBrewBenchLocal::RecordIdOk(RecordId)) { return false; }
	if (Records.Contains(RecordId)) { return true; }
	if (Records.Num() >= daedalus::brewmelody::MaxRecords) { return false; }
	Records.Add(RecordId);
	return true;
}

bool ADaedalusBrewBench::Brew()
{
	using namespace DaedalusBrewBenchLocal;
	if (!IsInGameThread() || Pending.IsValid()) { return false; }
	std::vector<std::string> H, R; std::vector<int> S;
	for (const FString& X : Herbs) { H.push_back(ToUtf8(X)); }
	for (int32 X : Stages) { S.push_back(X); }
	for (const FString& X : Records) { R.push_back(ToUtf8(X)); }
	std::string Json, Why;
	if (!daedalus::brewmelody::BuildRequest(H, S, R, Json, Why))
	{
		Error = FromUtf8(Why);
		OnRefused.Broadcast(400, Error);
		Tell(FString::Printf(TEXT("The kettle won't take that: %s."), *Error));
		return false;
	}
	if (!HasSession())
	{
		Error = TEXT("no brew server session (DAEDALUS_BREW_ORIGIN / DAEDALUS_BREW_TOKEN)");
		OnRefused.Broadcast(0, Error);
		Tell(TEXT("The kettle is cold: no brew server is configured."));
		return false;
	}
	auto Request = FHttpModule::Get().CreateRequest();
	const FString Url = ServerOrigin + UTF8_TO_TCHAR(daedalus::brewmelody::Route());
	Request->SetURL(Url); Request->SetVerb(TEXT("POST")); Request->SetTimeout(10);
	Request->SetHeader(TEXT("Accept"), TEXT("application/json"));
	Request->SetHeader(TEXT("Content-Type"), TEXT("application/json"));
	Request->SetHeader(TEXT("Authorization"), TEXT("Bearer ") + BearerToken);
	Request->SetContentAsString(FromUtf8(Json));
	Request->SetDelegateThreadPolicy(EHttpRequestDelegateThreadPolicy::CompleteOnGameThread);
	auto Reply = MakeShared<TArray<uint8>, ESPMode::ThreadSafe>();
	if (!Request->SetResponseBodyReceiveStreamDelegateV2(FHttpRequestStreamDelegateV2::CreateLambda(
		[Reply](void* Data, int64& Length)
		{
			// Contract cap: MaxBody bytes. Anything longer is cut off here and then refused by the parser.
			if (Length < 0 || Length > (int64)daedalus::brewmelody::MaxBody + 1 - Reply->Num()) { Length = 0; return; }
			Reply->Append(static_cast<const uint8*>(Data), static_cast<int32>(Length));
		}))) { return false; }
	TWeakObjectPtr<ADaedalusBrewBench> Self(this);
	const uint64 Session = Generation;
	Request->OnProcessRequestComplete().BindLambda([Self, Session, Reply, Url](FHttpRequestPtr, FHttpResponsePtr Response, bool Connected)
	{
		if (!Self.IsValid() || Self->Generation != Session) { return; }
		Self->Pending.Reset();
		const int32 Status = Response ? Response->GetResponseCode() : 0;
		// The original URL survives a redirect: the bearer must not have followed one.
		const bool Same = Response && Response->GetEffectiveURL().Equals(Url, ESearchCase::CaseSensitive);
		std::string Text;
		if (Connected && Same && Status == 200)
		{
			Text = std::string(reinterpret_cast<const char*>(Reply->GetData()), (size_t)Reply->Num());
		}
		Self->Finish(Same ? Status : 0, Text);
	});
	Pending = Request;
	if (!Request->ProcessRequest()) { Pending.Reset(); return false; }
	Tell(TEXT("The kettle starts to sing."));
	return true;
}

void ADaedalusBrewBench::Finish(int32 Status, const std::string& Text)
{
	using namespace DaedalusBrewBenchLocal;
	const daedalus::brewmelody::Result R = daedalus::brewmelody::Parse(Status, Text);
	if (!R.Ok)
	{
		Error = FromUtf8(R.Error);
		OnRefused.Broadcast(Status, Error);
		Tell(FString::Printf(TEXT("The brew fizzles (%s)."), *Error));
		return;
	}
	Error.Reset();
	LastItemId = FromUtf8(R.Item); LastEffectId = FromUtf8(R.Effect); LastTune = FromUtf8(R.FoundTune); LastTierValue = R.Tier;
	LastNoteList.Reset();
	for (int N : R.Notes) { LastNoteList.Add(N); }
	// The server brewed it: the herbs are used up (the gameplay host owns inventory; the kettle just empties).
	Herbs.Reset(); Stages.Reset();
	OnBrewed.Broadcast(LastItemId, LastTierValue, LastTune);
	if (LastTune.IsEmpty()) { Tell(FString::Printf(TEXT("The kettle sings %d notes: %s (tier %d)."), LastNoteList.Num(), *LastItemId, LastTierValue)); }
	else { Tell(FString::Printf(TEXT("The kettle remembers %s: %s (tier %d)."), *LastTune, *LastItemId, LastTierValue)); }
}

// ---------------- jukebox ----------------
ADaedalusJukebox::ADaedalusJukebox()
{
	bReplicates = false;
	Tags.Add(TEXT("Jukebox"));
	static ConstructorHelpers::FObjectFinder<UStaticMesh> Cube(TEXT("/Engine/BasicShapes/Cube.Cube"));
	if (Cube.Succeeded())
	{
		Body->SetStaticMesh(Cube.Object);
		Body->SetRelativeScale3D(FVector(0.6f, 0.4f, 1.1f));
	}
	Glow->SetLightColor(FLinearColor(1.f, 0.75f, 0.35f));
	Records = { TEXT("Item_YTM_Record_AmericanOldTime"), TEXT("Item_YTM_Record_Alpine"), TEXT("Item_YTM_Record_CelticPipes"), TEXT("Item_YTM_Record_Gamelan"), TEXT("Item_YTM_Record_AndeanPanPipes"), TEXT("Item_YTM_Record_AppalachianHighLonesome"), TEXT("Item_YTM_Record_ArabicMaqam"), TEXT("Item_YTM_Record_ArabicTakht"), TEXT("Item_YTM_Record_ArmenianDuduk"), TEXT("Item_YTM_Record_BalkanBrass"), TEXT("Item_YTM_Record_BaroqueCounterpoint"), TEXT("Item_YTM_Record_CairoOrchestra") };
}

FString ADaedalusJukebox::Prompt(const ADaedalusHero*) const
{
	if (Records.Num() == 0) { return TEXT("The jukebox is empty"); }
	return FString::Printf(TEXT("Play %s"), *Records[Next % Records.Num()]);
}

ADaedalusBrewBench* ADaedalusJukebox::FindBench() const
{
	if (Bench) { return Bench.Get(); }
	UWorld* World = GetWorld();
	if (!World) { return nullptr; }
	ADaedalusBrewBench* Best = nullptr;
	double BestD = FMath::Square((double)BenchReach);
	for (TActorIterator<ADaedalusBrewBench> It(World); It; ++It)
	{
		const double D = FVector::DistSquared(It->GetActorLocation(), GetActorLocation());
		if (D <= BestD) { BestD = D; Best = *It; }
	}
	return Best;
}

bool ADaedalusJukebox::Use(ADaedalusHero*)
{
	if (Records.Num() == 0) { return false; }
	Playing = Records[Next % Records.Num()];
	Next = (Next + 1) % Records.Num();
	ADaedalusBrewBench* B = FindBench();
	const bool Heard = B && B->RecordPlayed(Playing);
	const FString Line = Heard ? FString::Printf(TEXT("The jukebox plays %s. The kettle is listening."), *Playing)
		: FString::Printf(TEXT("The jukebox plays %s."), *Playing);
	if (UDaedalusOrrery* O = UDaedalusOrrery::Get(this)) { O->Say(Line); }
	UE_LOG(LogTemp, Log, TEXT("Daedalus jukebox: %s"), *Line);
	return true;
}

// ---------------- console ----------------
static ADaedalusBrewBench* DaedalusFirstBrewBench(UWorld* World)
{
	if (!World) { return nullptr; }
	for (TActorIterator<ADaedalusBrewBench> It(World); It; ++It) { return *It; }
	return nullptr;
}

static FAutoConsoleCommandWithWorldAndArgs GBrewMelody(
	TEXT("daedalus.brew.melody"),
	TEXT("daedalus.brew.melody <Herb> <Herb> <Herb> [Herb] [Herb]: fill the first brew bench and brew (needs DAEDALUS_BREW_ORIGIN / DAEDALUS_BREW_TOKEN)."),
	FConsoleCommandWithWorldAndArgsDelegate::CreateLambda([](const TArray<FString>& Args, UWorld* World)
	{
		ADaedalusBrewBench* B = DaedalusFirstBrewBench(World);
		if (!B) { UE_LOG(LogTemp, Warning, TEXT("daedalus.brew.melody: no ADaedalusBrewBench in this world")); return; }
		B->ClearKettle();
		for (const FString& H : Args) { if (!B->AddHerb(H)) { UE_LOG(LogTemp, Warning, TEXT("daedalus.brew.melody: kettle refused herb %s"), *H); } }
		UE_LOG(LogTemp, Log, TEXT("daedalus.brew.melody: %d herbs -> %s"), B->Herbs.Num(), B->Brew() ? TEXT("request sent") : *B->LastError());
	}));

static FAutoConsoleCommandWithWorldAndArgs GBrewStatus(
	TEXT("daedalus.brew.status"),
	TEXT("daedalus.brew.status: kettle, records heard and the last brew of the first brew bench."),
	FConsoleCommandWithWorldAndArgsDelegate::CreateLambda([](const TArray<FString>&, UWorld* World)
	{
		ADaedalusBrewBench* B = DaedalusFirstBrewBench(World);
		if (!B) { UE_LOG(LogTemp, Log, TEXT("daedalus.brew.status: no bench")); return; }
		UE_LOG(LogTemp, Log, TEXT("daedalus.brew.status: brewing=%d herbs=%d records=%d item=%s tier=%d tune=%s error=%s"), B->IsBrewing() ? 1 : 0,
			B->Herbs.Num(), B->PlayedRecords().Num(), *B->LastItem(), B->LastTier(), *B->LastFoundTune(), *B->LastError());
	}));