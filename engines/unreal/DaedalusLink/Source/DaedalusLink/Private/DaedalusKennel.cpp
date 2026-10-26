// SPDX-License-Identifier: MIT

#include "DaedalusKennel.h"
#include "Engine/Engine.h"
#include "Engine/World.h"
#include "HAL/IConsoleManager.h"
#include "Kismet/GameplayStatics.h"

namespace kennel = ::daedalus::kennel;

namespace
{
std::string KennelUtf8(const FString& S) { return std::string(TCHAR_TO_UTF8(*S)); }
FString KennelFromUtf8(const char* S) { return FString(UTF8_TO_TCHAR(S)); }
kennel::ECommand KennelCommandOf(const FString& S) { return kennel::CommandOf(KennelUtf8(S.ToLower()).c_str()); }
EDaedalusKennelDrill KennelToUe(kennel::EDrill D)
{
	switch (D)
	{
	case kennel::EDrill::Obeyed: return EDaedalusKennelDrill::Obeyed;
	case kennel::EDrill::Failed: return EDaedalusKennelDrill::Failed;
	case kennel::EDrill::TierLocked: return EDaedalusKennelDrill::TierLocked;
	case kennel::EDrill::StageLocked: return EDaedalusKennelDrill::StageLocked;
	default: return EDaedalusKennelDrill::Unknown;
	}
}
}

// ---------------- Pet ----------------
UDaedalusKennelPet::UDaedalusKennelPet()
{
	PrimaryComponentTick.bCanEverTick = false;
}

UDaedalusKennelPet* UDaedalusKennelPet::For(AActor* Actor)
{
	if (!Actor) { return nullptr; }
	if (UDaedalusKennelPet* C = Actor->FindComponentByClass<UDaedalusKennelPet>()) { return C; }
	UDaedalusKennelPet* C = NewObject<UDaedalusKennelPet>(Actor, TEXT("DaedalusKennelPet"));
	C->RegisterComponent();
	C->SeedFromOwner();
	return C;
}

void UDaedalusKennelPet::SeedFromOwner()
{
	const AActor* Owner = GetOwner();
	if (!Owner) { return; }
	std::vector<std::string> Tags;
	for (const FName& T : Owner->Tags) { Tags.push_back(KennelUtf8(T.ToString())); }
	// The object name is stable for a placed actor, so the same pet rolls the same days in every session.
	Pet = kennel::PetFromTags(Tags, KennelUtf8(Owner->GetName()));
}

bool UDaedalusKennelPet::Care(const FString& What, int32 Catches)
{
	return Pet.Care(kennel::CareOf(KennelUtf8(What.ToLower()).c_str()), Catches);
}

void UDaedalusKennelPet::EndDay()
{
	const kennel::FDayReport R = Pet.EndDay();
	OnDayEnded.Broadcast(Pet.Day, Pet.Bond, Pet.CareDays, GetTier(), GetStage());
	if (R.TierChanged()) { OnTierChanged.Broadcast(KennelFromUtf8(kennel::TierName(R.TierBefore)), KennelFromUtf8(kennel::TierName(R.TierAfter))); }
	if (R.StageChanged()) { OnStageChanged.Broadcast(KennelFromUtf8(kennel::StageName(R.StageBefore)), KennelFromUtf8(kennel::StageName(R.StageAfter))); }
}

EDaedalusKennelDrill UDaedalusKennelPet::Drill(const FString& Command)
{
	int Roll = -1, Pct = 0;
	const EDaedalusKennelDrill Out = KennelToUe(Pet.Drill(KennelCommandOf(Command), &Roll, &Pct));
	OnDrilled.Broadcast(Command.ToLower(), Out, Pct);
	return Out;
}

FString UDaedalusKennelPet::GetTier() const { return KennelFromUtf8(kennel::TierName(Pet.Tier())); }
FString UDaedalusKennelPet::GetStage() const { return KennelFromUtf8(kennel::StageName(Pet.Stage())); }

bool UDaedalusKennelPet::CanDrill(const FString& Command) const
{
	const kennel::ECommand C = KennelCommandOf(Command);
	return C != kennel::ECommand::Unknown && kennel::StageAllows(Pet.Stage(), C) && kennel::Obeys(Pet.Bond, C);
}

int32 UDaedalusKennelPet::DrillSuccessPct(const FString& Command) const
{
	const kennel::ECommand C = KennelCommandOf(Command);
	return C == kennel::ECommand::Unknown ? 0 : kennel::SuccessPct(Pet.Bond, C);
}

FString UDaedalusKennelPet::StatusLine() const { return FString(UTF8_TO_TCHAR(kennel::StatusLine(Pet).c_str())); }

// ---------------- Subsystem ----------------
void UDaedalusKennelSubsystem::OnWorldBeginPlay(UWorld& InWorld)
{
	Super::OnWorldBeginPlay(InWorld);
	Pets.Reset();
	for (const TCHAR* Tag : { TEXT("AMF_Companion"), TEXT("AMF_Wild") })
	{
		TArray<AActor*> Found;
		UGameplayStatics::GetAllActorsWithTag(&InWorld, Tag, Found);
		for (AActor* A : Found) { Adopt(A); }
	}
	UE_LOG(LogTemp, Log, TEXT("Daedalus kennel: %d pets"), Pets.Num());
}

UDaedalusKennelPet* UDaedalusKennelSubsystem::Adopt(AActor* Actor)
{
	UDaedalusKennelPet* P = UDaedalusKennelPet::For(Actor);
	if (P && !Pets.Contains(TWeakObjectPtr<UDaedalusKennelPet>(P))) { Pets.Add(P); }
	return P;
}

TArray<UDaedalusKennelPet*> UDaedalusKennelSubsystem::GetPets() const
{
	TArray<UDaedalusKennelPet*> Out;
	for (const TWeakObjectPtr<UDaedalusKennelPet>& P : Pets) { if (P.IsValid()) { Out.Add(P.Get()); } }
	return Out;
}

UDaedalusKennelPet* UDaedalusKennelSubsystem::FindPet(const FString& Name) const
{
	for (const TWeakObjectPtr<UDaedalusKennelPet>& P : Pets)
	{
		if (!P.IsValid() || !P->GetOwner()) { continue; }
		if (Name.IsEmpty() || P->GetOwner()->GetName().Contains(Name, ESearchCase::IgnoreCase)) { return P.Get(); }
	}
	return nullptr;
}

int32 UDaedalusKennelSubsystem::EndDayAll()
{
	int32 N = 0;
	for (const TWeakObjectPtr<UDaedalusKennelPet>& P : Pets) { if (P.IsValid()) { P->EndDay(); ++N; } }
	return N;
}

UDaedalusKennelSubsystem* UDaedalusKennelSubsystem::GetKennel(const UObject* WorldContext)
{
	const UWorld* World = GEngine ? GEngine->GetWorldFromContextObject(WorldContext, EGetWorldErrorMode::ReturnNull) : nullptr;
	return World ? World->GetSubsystem<UDaedalusKennelSubsystem>() : nullptr;
}

// ---------------- Console ----------------
namespace
{
UDaedalusKennelPet* KennelPetArg(UWorld* World, const TArray<FString>& Args, int32 Index, const TCHAR* Cmd)
{
	UDaedalusKennelSubsystem* K = UDaedalusKennelSubsystem::GetKennel(World);
	UDaedalusKennelPet* P = K ? K->FindPet(Args.IsValidIndex(Index) ? Args[Index] : FString()) : nullptr;
	if (!P) { UE_LOG(LogTemp, Warning, TEXT("%s: no matching pet (tag AMF_Companion / AMF_Wild)"), Cmd); }
	return P;
}
}

static FAutoConsoleCommandWithWorldAndArgs GKennelStatus(
	TEXT("daedalus.kennel.status"),
	TEXT("daedalus.kennel.status [Pet]: day, bond, tier, care-days, stage and today's care for one pet, or every pet."),
	FConsoleCommandWithWorldAndArgsDelegate::CreateLambda([](const TArray<FString>& Args, UWorld* World)
	{
		UDaedalusKennelSubsystem* K = UDaedalusKennelSubsystem::GetKennel(World);
		if (!K) { UE_LOG(LogTemp, Log, TEXT("daedalus.kennel.status: no kennel")); return; }
		if (Args.Num() > 0)
		{
			if (UDaedalusKennelPet* P = KennelPetArg(World, Args, 0, TEXT("daedalus.kennel.status"))) { UE_LOG(LogTemp, Log, TEXT("daedalus.kennel.status: %s"), *P->StatusLine()); }
			return;
		}
		for (UDaedalusKennelPet* P : K->GetPets()) { UE_LOG(LogTemp, Log, TEXT("daedalus.kennel.status: %s"), *P->StatusLine()); }
	}));

static FAutoConsoleCommandWithWorldAndArgs GKennelCare(
	TEXT("daedalus.kennel.care"),
	TEXT("daedalus.kennel.care <feed|water|tonic|fetch> [Catches] [Pet]: care for a pet today (fetch takes a catch count)."),
	FConsoleCommandWithWorldAndArgsDelegate::CreateLambda([](const TArray<FString>& Args, UWorld* World)
	{
		if (Args.Num() < 1) { UE_LOG(LogTemp, Warning, TEXT("daedalus.kennel.care: what?")); return; }
		int32 Catches = 1, PetIndex = 1;
		if (Args.IsValidIndex(1) && Args[1].IsNumeric()) { Catches = FCString::Atoi(*Args[1]); PetIndex = 2; }
		UDaedalusKennelPet* P = KennelPetArg(World, Args, PetIndex, TEXT("daedalus.kennel.care"));
		if (!P) { return; }
		const bool bOk = P->Care(Args[0], Catches);
		UE_LOG(LogTemp, Log, TEXT("daedalus.kennel.care: %s %s -> %s"), *Args[0], bOk ? TEXT("done") : TEXT("refused"), *P->StatusLine());
	}));

static FAutoConsoleCommandWithWorldAndArgs GKennelEndDay(
	TEXT("daedalus.kennel.endday"),
	TEXT("daedalus.kennel.endday: close the kennel day for every pet (bond step, growth, fresh day)."),
	FConsoleCommandWithWorldAndArgsDelegate::CreateLambda([](const TArray<FString>&, UWorld* World)
	{
		UDaedalusKennelSubsystem* K = UDaedalusKennelSubsystem::GetKennel(World);
		const int32 N = K ? K->EndDayAll() : 0;
		UE_LOG(LogTemp, Log, TEXT("daedalus.kennel.endday: %d pets stepped"), N);
		if (K) { for (UDaedalusKennelPet* P : K->GetPets()) { UE_LOG(LogTemp, Log, TEXT("daedalus.kennel.endday: %s"), *P->StatusLine()); } }
	}));

static FAutoConsoleCommandWithWorldAndArgs GKennelDrill(
	TEXT("daedalus.kennel.drill"),
	TEXT("daedalus.kennel.drill <come|stay|fetch|guard|rescue> [Pet]: one seeded drill (stage gate, tier gate, roll)."),
	FConsoleCommandWithWorldAndArgsDelegate::CreateLambda([](const TArray<FString>& Args, UWorld* World)
	{
		if (Args.Num() < 1) { UE_LOG(LogTemp, Warning, TEXT("daedalus.kennel.drill: which command?")); return; }
		UDaedalusKennelPet* P = KennelPetArg(World, Args, 1, TEXT("daedalus.kennel.drill"));
		if (!P) { return; }
		const int32 Pct = P->DrillSuccessPct(Args[0]);
		const EDaedalusKennelDrill D = P->Drill(Args[0]);
		static const TCHAR* Names[] = { TEXT("OBEYED"), TEXT("FAILED"), TEXT("TIER_LOCKED"), TEXT("STAGE_LOCKED"), TEXT("UNKNOWN") };
		UE_LOG(LogTemp, Log, TEXT("daedalus.kennel.drill: %s %s (%d%%) -> %s"), *Args[0], Names[(int32)D], Pct, *P->StatusLine());
	}));
