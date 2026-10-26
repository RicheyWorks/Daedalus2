// SPDX-License-Identifier: MIT

#include "DaedalusTonic.h"
#include "Engine/Engine.h"
#include "Engine/World.h"
#include "HAL/IConsoleManager.h"
#include "HAL/PlatformMisc.h"
#include "HttpModule.h"
#include "Interfaces/IHttpRequest.h"
#include "Interfaces/IHttpResponse.h"
#include "Kismet/GameplayStatics.h"

namespace tonic = daedalus::tonic;

namespace
{
std::string Utf8(const FString& S) { return std::string(TCHAR_TO_UTF8(*S)); }
// Actor labels exist only in the editor; packaged builds rely on tags (Cane_Corso, Coat_*, Stage_*).
FString LabelOf(const AActor* A)
{
#if WITH_EDITOR
	return A->GetActorLabel();
#else
	return A->GetName();
#endif
}
FString FromUtf8(const std::string& S) { return FString(UTF8_TO_TCHAR(S.c_str())); }
std::vector<std::string> TagsOf(const AActor* A)
{
	std::vector<std::string> Out;
	for (const FName& T : A->Tags) { Out.push_back(Utf8(T.ToString())); }
	return Out;
}
bool TokenOk(const FString& Token)
{
	if (Token.IsEmpty() || Token.Len() > 8192) { return false; }
	for (TCHAR C : Token) { if (!((C >= 'a' && C <= 'z') || (C >= 'A' && C <= 'Z') || (C >= '0' && C <= '9') || C == '.' || C == '_' || C == '-')) { return false; } }
	return true;
}
}

// ---------------- Effects ----------------
UDaedalusTonicEffects::UDaedalusTonicEffects()
{
	PrimaryComponentTick.bCanEverTick = true;
	PrimaryComponentTick.TickInterval = 0.25f;
}

UDaedalusTonicEffects* UDaedalusTonicEffects::For(AActor* Actor)
{
	if (!Actor) { return nullptr; }
	if (UDaedalusTonicEffects* C = Actor->FindComponentByClass<UDaedalusTonicEffects>()) { return C; }
	UDaedalusTonicEffects* C = NewObject<UDaedalusTonicEffects>(Actor, TEXT("DaedalusTonicEffects"));
	C->RegisterComponent();
	return C;
}

double UDaedalusTonicEffects::Now() const
{
	const UWorld* W = GetWorld();
	return W ? W->GetTimeSeconds() : 0.0;
}

void UDaedalusTonicEffects::TickComponent(float Dt, ELevelTick TickType, FActorComponentTickFunction* Fn)
{
	Super::TickComponent(Dt, TickType, Fn);
	for (const std::string& Gone : Ledger.Expire(Now())) { OnTonicExpired.Broadcast(FromUtf8(Gone)); }
}

bool UDaedalusTonicEffects::ApplyTonicText(const FString& Reply)
{
	tonic::Brew B;
	const tonic::Result R = tonic::Parse(Utf8(Reply), B);
	if (!R.Ok) { Error = FromUtf8(R.Error); return false; }
	Error.Reset();
	for (const tonic::Mod& M : Ledger.Apply(B, Now()))
	{
		OnTonicPulse.Broadcast(FromUtf8(B.RecipeId), FromUtf8(M.Stat), M.Mul ? TEXT("mul") : TEXT("add"), (float)M.Value);
	}
	return true;
}

float UDaedalusTonicEffects::GetStat(const FString& Stat, float Base) const { return (float)Ledger.Stat(Utf8(Stat), Base, Now()); }
bool UDaedalusTonicEffects::HasGrant(const FString& Grant) const { return Ledger.HasGrant(Utf8(Grant), Now()); }
float UDaedalusTonicEffects::GetBreedChancePct() const { return (float)Ledger.BreedChancePct(Now()); }
bool UDaedalusTonicEffects::IsTonicActive(const FString& RecipeId) const { return Ledger.Active(Utf8(RecipeId), Now()); }

// ---------------- Trough ----------------
UDaedalusBrewTroughComponent::UDaedalusBrewTroughComponent()
{
	PrimaryComponentTick.bCanEverTick = true;
	PrimaryComponentTick.TickInterval = 0.25f;
}

double UDaedalusBrewTroughComponent::Now() const
{
	const UWorld* W = GetWorld();
	return W ? W->GetTimeSeconds() : 0.0;
}

std::string UDaedalusBrewTroughComponent::Key() const
{
	const AActor* O = GetOwner();
	return O ? Utf8(O->GetName()) : std::string("trough");
}

EDaedalusTroughPhase UDaedalusBrewTroughComponent::GetPhase() const
{
	// PhaseNow settles decay, so it is not const on the core object.
	return (EDaedalusTroughPhase)(uint8) const_cast<tonic::Trough&>(Trough).PhaseNow(Now());
}

int32 UDaedalusBrewTroughComponent::DrinksLeft() const { return const_cast<tonic::Trough&>(Trough).DrinksLeft(Now()); }

TArray<FString> UDaedalusBrewTroughComponent::Herbs() const
{
	TArray<FString> Out;
	for (const std::string& H : Trough.Herbs()) { Out.Add(FromUtf8(H)); }
	return Out;
}

bool UDaedalusBrewTroughComponent::ConfigureSession(const FString& Origin, const FString& Token)
{
	if (!IsInGameThread() || !tonic::OriginAllowed(Utf8(Origin)) || !TokenOk(Token)) { return false; }
	ClearSession();
	ServerOrigin = Origin; BearerToken = Token;
	return true;
}

void UDaedalusBrewTroughComponent::ClearSession()
{
	++Generation;
	auto Old = Pending; Pending.Reset();
	ServerOrigin.Reset(); BearerToken.Reset();
	if (Old) { Old->OnProcessRequestComplete().Unbind(); Old->CancelRequest(); }
}

bool UDaedalusBrewTroughComponent::HasSession()
{
	if (!BearerToken.IsEmpty()) { return true; }
	const FString Origin = FPlatformMisc::GetEnvironmentVariable(TEXT("DAEDALUS_KENNEL_ORIGIN"));
	const FString Token = FPlatformMisc::GetEnvironmentVariable(TEXT("DAEDALUS_KENNEL_TOKEN"));
	return !Origin.IsEmpty() && ConfigureSession(Origin, Token);
}

void UDaedalusBrewTroughComponent::OnComponentDestroyed(bool Destroying) { ClearSession(); Super::OnComponentDestroyed(Destroying); }
void UDaedalusBrewTroughComponent::EndPlay(const EEndPlayReason::Type Reason) { ClearSession(); Super::EndPlay(Reason); }

bool UDaedalusBrewTroughComponent::DepositHerb(const FString& HerbName)
{
	return Trough.Deposit(Utf8(HerbName), Now());
}

bool UDaedalusBrewTroughComponent::DepositHerbActor(AActor* Herb)
{
	if (!Herb) { return false; }
	std::string Name;
	for (const std::string& T : TagsOf(Herb)) { if (tonic::HerbFromTag(T, Name)) { return Trough.Deposit(Name, Now()); } }
	return false;
}

bool UDaedalusBrewTroughComponent::EmptyTrough()
{
	if (Trough.PhaseNow(Now()) == tonic::Phase::Steeping || Trough.PhaseNow(Now()) == tonic::Phase::Steeped) { return false; }
	Trough.Empty();
	return true;
}

AActor* UDaedalusBrewTroughComponent::FindCorso() const
{
	TArray<AActor*> Found;
	UGameplayStatics::GetAllActorsWithTag(this, TEXT("AMF_Companion"), Found);
	for (AActor* A : Found) { if (A && (A->ActorHasTag(TEXT("Cane_Corso")) || LabelOf(A).Contains(TEXT("CaneCorso")))) { return A; } }
	return nullptr;
}

bool UDaedalusBrewTroughComponent::Post(const std::string& Json, FDone Done)
{
	if (!IsInGameThread() || Pending || !HasSession()) { return false; }
	auto Request = FHttpModule::Get().CreateRequest();
	const FString Url = ServerOrigin + TEXT("/api/v1/kennel/brew");
	Request->SetURL(Url); Request->SetVerb(TEXT("POST")); Request->SetTimeout(10);
	Request->SetHeader(TEXT("Accept"), TEXT("text/plain"));
	Request->SetHeader(TEXT("Content-Type"), TEXT("application/json"));
	Request->SetHeader(TEXT("Authorization"), TEXT("Bearer ") + BearerToken);
	Request->SetContentAsString(FromUtf8(Json));
	Request->SetDelegateThreadPolicy(EHttpRequestDelegateThreadPolicy::CompleteOnGameThread);
	auto Body = MakeShared<TArray<uint8>, ESPMode::ThreadSafe>();
	if (!Request->SetResponseBodyReceiveStreamDelegateV2(FHttpRequestStreamDelegateV2::CreateLambda(
		[Body](void* Data, int64& Length)
		{
			// Contract: 4096 bytes total. Anything longer is cut off here and then refused by the parser.
			if (Length < 0 || Length > (int64)tonic::MaxBytes + 1 - Body->Num()) { Length = 0; return; }
			Body->Append(static_cast<const uint8*>(Data), static_cast<int32>(Length));
		}))) { return false; }
	TWeakObjectPtr<UDaedalusBrewTroughComponent> Self(this);
	const uint64 Session = Generation;
	Request->OnProcessRequestComplete().BindLambda([Self, Session, Body, Url, Done](FHttpRequestPtr, FHttpResponsePtr Response, bool Connected)
	{
		if (!Self.IsValid() || Self->Generation != Session) { return; }
		Self->Pending.Reset();
		const int32 Status = Response ? Response->GetResponseCode() : 0;
		// The original URL survives a redirect: the bearer must not have followed one.
		const bool Same = Response && Response->GetEffectiveURL().Equals(Url, ESearchCase::CaseSensitive);
		std::string Text;
		if (Connected && Same && Status == 200)
		{
			Text = std::string(reinterpret_cast<const char*>(Body->GetData()), (size_t)Body->Num());
		}
		Done(Same ? Status : 0, Connected, Text);
	});
	Pending = Request;
	if (!Request->ProcessRequest()) { Pending.Reset(); return false; }
	return true;
}

bool UDaedalusBrewTroughComponent::Interact(AActor* Instigator)
{
	const double T = Now();
	if (Pending || !Trough.BeginSteep(T)) { return false; }
	// The steep request only proves the herb set makes a tonic; use the Corso as the reference drinker when there is one.
	AActor* Ref = FindCorso();
	tonic::Drinker D = Ref ? tonic::DrinkerFromTags(TagsOf(Ref), Utf8(LabelOf(Ref))) : tonic::Drinker();
	if (!Ref) { D.Kind = "cane_corso"; }
	std::string Json;
	const int64_t Seed = tonic::DeriveSeed(Key(), Trough.Steeps() + 1, 0);
	if (!tonic::BuildRequest(Trough.Herbs(), D, Seed, Json).Ok) { Trough.SteepRefused(); return false; }
	const bool Sent = Post(Json, [this](int32 Status, bool, const std::string& Text)
	{
		tonic::Brew B;
		const tonic::Result R = Status == 200 ? tonic::Parse(Text, B) : tonic::Fail("HTTP " + std::to_string(Status));
		if (!R.Ok)
		{
			Trough.SteepRefused();
			OnRefused.Broadcast(Status, FromUtf8(R.Error));
			return;
		}
		Trough.SteepDone(B.RecipeId, Now());
		OnSteeped.Broadcast(FromUtf8(B.RecipeId), Trough.HerbCount());
	});
	if (!Sent) { Trough.SteepRefused(); return false; }
	return true;
}

bool UDaedalusBrewTroughComponent::Drink(AActor* Drinker)
{
	if (!Drinker || Pending || !HasSession()) { return false; }
	const double T = Now();
	uint32 Ordinal = 0;
	if (!Trough.ReserveDrink(T, Ordinal)) { return false; }
	const tonic::Drinker D = tonic::DrinkerFromTags(TagsOf(Drinker), Utf8(LabelOf(Drinker)));
	std::string Json;
	const int64_t Seed = tonic::DeriveSeed(Key(), Trough.Steeps(), Ordinal);
	if (!tonic::BuildRequest(Trough.Herbs(), D, Seed, Json).Ok) { Trough.RefundDrink(T); return false; }
	TWeakObjectPtr<AActor> Who(Drinker);
	const bool Sent = Post(Json, [this, Who](int32 Status, bool, const std::string& Text)
	{
		const double Later = Now();
		AActor* A = Who.Get();
		tonic::Brew B;
		const tonic::Result R = Status == 200 ? tonic::Parse(Text, B) : tonic::Fail("HTTP " + std::to_string(Status));
		if (!R.Ok || !A)
		{
			Trough.RefundDrink(Later);
			OnRefused.Broadcast(Status, FromUtf8(R.Ok ? std::string("drinker is gone") : R.Error));
			return;
		}
		// Apply once. A reply that Java built and the parser accepted is applied by the pet's own ledger.
		UDaedalusTonicEffects* Fx = UDaedalusTonicEffects::For(A);
		if (!Fx || !Fx->ApplyTonicText(FromUtf8(Text)))
		{
			Trough.RefundDrink(Later);
			OnRefused.Broadcast(Status, Fx ? Fx->LastError() : FString(TEXT("no effects component")));
			return;
		}
		Trough.ConfirmDrink(Later);
		OnDrunk.Broadcast(A, FromUtf8(B.RecipeId), B.SecondRoll);
	});
	if (!Sent) { Trough.RefundDrink(T); return false; }
	return true;
}

void UDaedalusBrewTroughComponent::TickComponent(float Dt, ELevelTick TickType, FActorComponentTickFunction* Fn)
{
	Super::TickComponent(Dt, TickType, Fn);
	SinceScan += Dt;
	if (!bAutoDrink || Pending || SinceScan < 0.5f) { return; }
	SinceScan = 0.f;
	if (Trough.PhaseNow(Now()) != tonic::Phase::Steeped || Trough.DrinksLeft(Now()) <= 0) { return; }
	const AActor* Owner = GetOwner();
	if (!Owner) { return; }
	const FVector Here = Owner->GetActorLocation();
	const std::string Recipe = Trough.RecipeId();
	// Companions first (the Corso), then wild pets. A pet already under this tonic does not burn another drink.
	for (const TCHAR* Tag : { TEXT("AMF_Companion"), TEXT("AMF_Wild") })
	{
		TArray<AActor*> Found;
		UGameplayStatics::GetAllActorsWithTag(this, Tag, Found);
		for (AActor* A : Found)
		{
			if (!A || FVector::Dist(A->GetActorLocation(), Here) > Reach) { continue; }
			const UDaedalusTonicEffects* Fx = A->FindComponentByClass<UDaedalusTonicEffects>();
			if (Fx && Fx->IsTonicActive(FromUtf8(Recipe))) { continue; }
			Drink(A);
			return;
		}
	}
}

// ---------------- Subsystem + console ----------------
void UDaedalusTonicSubsystem::OnWorldBeginPlay(UWorld& InWorld)
{
	Super::OnWorldBeginPlay(InWorld);
	TArray<AActor*> Found;
	UGameplayStatics::GetAllActorsWithTag(&InWorld, TEXT("Brew_Trough"), Found);
	AActor* Pick = nullptr;
	for (AActor* A : Found) { if (A && A->ActorHasTag(TEXT("Interact_Brew"))) { Pick = A; break; } }
	if (!Pick && Found.Num() > 0) { Pick = Found[0]; }
	if (!Pick) { return; }
	UDaedalusBrewTroughComponent* C = Pick->FindComponentByClass<UDaedalusBrewTroughComponent>();
	if (!C)
	{
		C = NewObject<UDaedalusBrewTroughComponent>(Pick, TEXT("DaedalusBrewTrough"));
		C->RegisterComponent();
	}
	Trough = C;
	UE_LOG(LogTemp, Log, TEXT("Daedalus tonic: trough component on %s"), *Pick->GetName());
}

UDaedalusTonicSubsystem* UDaedalusTonicSubsystem::GetTonics(const UObject* WorldContext)
{
	const UWorld* World = GEngine ? GEngine->GetWorldFromContextObject(WorldContext, EGetWorldErrorMode::ReturnNull) : nullptr;
	return World ? World->GetSubsystem<UDaedalusTonicSubsystem>() : nullptr;
}

static FAutoConsoleCommandWithWorldAndArgs GTonicSteep(
	TEXT("daedalus.tonic.steep"),
	TEXT("daedalus.tonic.steep <Herb> [Herb] [Herb]: put the herbs in the Kennel Isle trough and steep them (needs DAEDALUS_KENNEL_ORIGIN / DAEDALUS_KENNEL_TOKEN)."),
	FConsoleCommandWithWorldAndArgsDelegate::CreateLambda([](const TArray<FString>& Args, UWorld* World)
	{
		UDaedalusTonicSubsystem* S = UDaedalusTonicSubsystem::GetTonics(World);
		UDaedalusBrewTroughComponent* T = S ? S->GetTrough() : nullptr;
		if (!T) { UE_LOG(LogTemp, Warning, TEXT("daedalus.tonic.steep: no Brew_Trough in this world")); return; }
		T->EmptyTrough();
		for (const FString& H : Args) { if (!T->DepositHerb(H)) { UE_LOG(LogTemp, Warning, TEXT("daedalus.tonic.steep: trough refused herb %s"), *H); } }
		UE_LOG(LogTemp, Log, TEXT("daedalus.tonic.steep: steeping %d herbs -> %s"), T->HerbCount(), T->Interact(nullptr) ? TEXT("request sent") : TEXT("not sent"));
	}));

static FAutoConsoleCommandWithWorldAndArgs GTonicStatus(
	TEXT("daedalus.tonic.status"),
	TEXT("daedalus.tonic.status: phase, herbs, recipe and drinks left of the Kennel Isle trough."),
	FConsoleCommandWithWorldAndArgsDelegate::CreateLambda([](const TArray<FString>&, UWorld* World)
	{
		UDaedalusTonicSubsystem* S = UDaedalusTonicSubsystem::GetTonics(World);
		UDaedalusBrewTroughComponent* T = S ? S->GetTrough() : nullptr;
		if (!T) { UE_LOG(LogTemp, Log, TEXT("daedalus.tonic.status: no trough")); return; }
		UE_LOG(LogTemp, Log, TEXT("daedalus.tonic.status: phase=%d herbs=%d recipe=%s drinks=%d"), (int32)T->GetPhase(), T->HerbCount(), *T->RecipeId(), T->DrinksLeft());
	}));