// SPDX-License-Identifier: MIT
#include "DaedalusSolReachJournal.h"
#include "DaedalusSolReachCore.h"
#include "DaedalusSkyDirector.h"
#include "GameFramework/Actor.h"
#include "Net/UnrealNetwork.h"
#include <limits>

namespace DaedalusSolJournalInternal {
using namespace daedalus::sol;
bool Read(const FDaedalusSolSnapshot& In, State& Out) {
    if(In.Schema!=1 || In.Herbs.Num()!=6 || In.Facts<0 || In.Discoveries<0) return false;
    Out.CleanWater=In.CleanWater; Out.DirtyWater=In.DirtyWater; Out.Eggs=In.Eggs; Out.Milk=In.Milk;
    Out.Facts=static_cast<uint32_t>(In.Facts); Out.Discoveries=static_cast<uint32_t>(In.Discoveries);
    Out.KeeperMeals=In.KeeperMeals;
    for(int I=0;I<6;++I) Out.Herbs[I]=In.Herbs[I];
    return Valid(Out);
}
void Write(const State& In, FDaedalusSolSnapshot& Out) {
    Out.CleanWater=In.CleanWater; Out.DirtyWater=In.DirtyWater; Out.Eggs=In.Eggs; Out.Milk=In.Milk;
    Out.Facts=static_cast<int32>(In.Facts); Out.Discoveries=static_cast<int32>(In.Discoveries);
    Out.KeeperMeals=In.KeeperMeals;
    for(int I=0;I<6;++I) Out.Herbs[I]=In.Herbs[I];
}
Sky Context(const ADaedalusSkyDirector* Director) {
    if(!IsValid(Director)) return {-1,0,Weather::Clear};
    Weather W=Weather::Clear;
    switch(Director->Weather) {
        case EDaedalusWeather::Overcast: W=Weather::Overcast; break;
        case EDaedalusWeather::Rain: W=Weather::Rain; break;
        case EDaedalusWeather::Storm: W=Weather::Storm; break;
        case EDaedalusWeather::Fog: W=Weather::Fog; break;
        default: break;
    }
    return {Director->GetHour(),Director->GetWetness(),W};
}
const TCHAR* FailureName(daedalus::sol::Error E) {
    switch(E) {
        case daedalus::sol::Error::None: return TEXT("");
        case daedalus::sol::Error::InvalidState: return TEXT("Invalid journal state");
        case daedalus::sol::Error::InvalidRecipe: return TEXT("The ring is not closed or its centre has no effect");
        case daedalus::sol::Error::MissingHerbs: return TEXT("Not enough herbs");
        case daedalus::sol::Error::MissingWater: return TEXT("Clean water required");
        case daedalus::sol::Error::MissingFood: return TEXT("Egg and milk required");
        default: return TEXT("Dirty well water required");
    }
}
}

UDaedalusSolReachJournal::UDaedalusSolReachJournal() {
    PrimaryComponentTick.bCanEverTick=true;
    PrimaryComponentTick.TickInterval=1.f;
    SetIsReplicatedByDefault(true);
    Effects.SetNum(6);
    // Defaults mirror data/herbs/combos.json; callers can supply the shared table.
    Effects[1].Id=TEXT("heat_shield"); Effects[1].DurationSeconds=120;
    Effects[2].Id=TEXT("fire_resist"); Effects[2].DurationSeconds=120;
    Effects[3].Id=TEXT("slow_hunger"); Effects[3].DurationSeconds=300;
    Effects[4].Id=TEXT("stamina_regen_x2"); Effects[4].DurationSeconds=90;
}
void UDaedalusSolReachJournal::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const {
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);
    DOREPLIFETIME_CONDITION(UDaedalusSolReachJournal,Snapshot,COND_OwnerOnly);
}
bool UDaedalusSolReachJournal::CanMutate() const { return IsValid(GetOwner()) && GetOwner()->HasAuthority(); }
void UDaedalusSolReachJournal::Changed() { OnJournalChanged.Broadcast(Snapshot); SampleEnvironment(); }
void UDaedalusSolReachJournal::OnRepSnapshot() { Changed(); }
void UDaedalusSolReachJournal::TickComponent(float DeltaTime,ELevelTick TickType,FActorComponentTickFunction* ThisTickFunction) {
    Super::TickComponent(DeltaTime,TickType,ThisTickFunction);
    SampleEnvironment();
}
void UDaedalusSolReachJournal::SampleEnvironment() {
    bool Visible=IsCisternClueVisible();
    auto Place=GetKeeperPlace();
    if(!bSampledEnvironment || Visible!=bLastClueVisible || Place!=LastKeeperPlace) {
        bSampledEnvironment=true; bLastClueVisible=Visible; LastKeeperPlace=Place;
        OnEnvironmentChanged.Broadcast(Visible,Place);
    }
}

bool UDaedalusSolReachJournal::Deposit(EDaedalusSolSupply Supply,int32 Amount) {
    daedalus::sol::State S;
    if(!CanMutate() || Amount<=0 || !DaedalusSolJournalInternal::Read(Snapshot,S)) return false;
    int* Target=nullptr;
    switch(Supply) {
        case EDaedalusSolSupply::CleanWater: Target=&S.CleanWater; break;
        case EDaedalusSolSupply::DirtyWater: Target=&S.DirtyWater; break;
        case EDaedalusSolSupply::Egg: Target=&S.Eggs; break;
        case EDaedalusSolSupply::Milk: Target=&S.Milk; break;
        default: {
            const int Index=static_cast<int>(Supply)-static_cast<int>(EDaedalusSolSupply::Dawnleaf);
            if(Index<0 || Index>=6) return false;
            Target=&S.Herbs[Index]; break;
        }
    }
    if(*Target>std::numeric_limits<int>::max()-Amount) return false;
    *Target+=Amount; DaedalusSolJournalInternal::Write(S,Snapshot); Changed(); return true;
}
bool UDaedalusSolReachJournal::FilterWellWater() {
    daedalus::sol::State S;
    if(!CanMutate() || !DaedalusSolJournalInternal::Read(Snapshot,S) || daedalus::sol::FilterWell(S)!=daedalus::sol::Error::None) return false;
    DaedalusSolJournalInternal::Write(S,Snapshot); Changed(); return true;
}
FDaedalusSolBrewResult UDaedalusSolReachJournal::BrewRing(const TArray<FName>& OrderedHerbs) {
    FDaedalusSolBrewResult Out; daedalus::sol::State S;
    if(!CanMutate() || !DaedalusSolJournalInternal::Read(Snapshot,S)) { Out.Failure=TEXT("Authority and valid journal required"); return Out; }
    if(OrderedHerbs.Num()!=3 || Effects.Num()!=6) { Out.Failure=TEXT("Three herbs and a six-entry effect table required"); return Out; }
    static const FName Names[6]={TEXT("dawnleaf"),TEXT("rillprism"),TEXT("cinderbud"),TEXT("stillmoss"),TEXT("stridefern"),TEXT("clearbell")};
    std::array<daedalus::sol::Herb,3> Ring;
    for(int I=0;I<3;++I) {
        int Index=-1;
        for(int J=0;J<6;++J) if(OrderedHerbs[I]==Names[J]) Index=J;
        if(Index<0) { Out.Failure=TEXT("Unknown herb"); return Out; }
        Ring[I]=static_cast<daedalus::sol::Herb>(Index);
    }
    daedalus::sol::Effects Table;
    for(int I=0;I<6;++I) {
        Table[I].Id=Effects[I].Id.IsNone()?std::string():std::string(TCHAR_TO_UTF8(*Effects[I].Id.ToString()));
        Table[I].Duration=Effects[I].DurationSeconds;
    }
    auto Result=daedalus::sol::Brew(S,Ring,Table);
    Out.Failure=DaedalusSolJournalInternal::FailureName(Result.Failure);
    if(Result.Failure!=daedalus::sol::Error::None) return Out;
    Out.bSuccess=true; Out.Effect=FName(UTF8_TO_TCHAR(Result.EffectId.c_str()));
    Out.DurationSeconds=Result.Duration; Out.bDoubled=Result.Doubled;
    DaedalusSolJournalInternal::Write(S,Snapshot); Changed(); return Out;
}
bool UDaedalusSolReachJournal::CookAndShareCustard() {
    daedalus::sol::State S;
    if(!CanMutate() || !DaedalusSolJournalInternal::Read(Snapshot,S) || daedalus::sol::CookForKeeper(S)!=daedalus::sol::Error::None) return false;
    DaedalusSolJournalInternal::Write(S,Snapshot); Changed(); return true;
}
bool UDaedalusSolReachJournal::DiscoverHiddenCistern() {
    daedalus::sol::State S;
    if(!CanMutate() || !DaedalusSolJournalInternal::Read(Snapshot,S) || !IsValid(HiddenStairMarker) ||
       !FMath::IsFinite(DiscoveryReachCm) || DiscoveryReachCm<=0) return false;
    bool Near=FVector::DistSquared(GetOwner()->GetActorLocation(),HiddenStairMarker->GetActorLocation())<=FMath::Square(DiscoveryReachCm);
    if(!daedalus::sol::DiscoverCistern(S,DaedalusSolJournalInternal::Context(SkyDirector),Near)) return false;
    DaedalusSolJournalInternal::Write(S,Snapshot); Changed(); return true;
}
bool UDaedalusSolReachJournal::RestoreJournal(const FDaedalusSolSnapshot& Saved) {
    daedalus::sol::State S;
    if(!CanMutate() || !DaedalusSolJournalInternal::Read(Saved,S)) return false;
    Snapshot=Saved; Changed(); return true;
}
EDaedalusSolStage UDaedalusSolReachJournal::GetAdventureStage() const {
    daedalus::sol::State S; if(!DaedalusSolJournalInternal::Read(Snapshot,S)) return EDaedalusSolStage::RestoreWaterworks;
    return static_cast<EDaedalusSolStage>(daedalus::sol::AdventureStage(S));
}
EDaedalusSolKeeperPlace UDaedalusSolReachJournal::GetKeeperPlace() const {
    daedalus::sol::State S; if(!DaedalusSolJournalInternal::Read(Snapshot,S)) return EDaedalusSolKeeperPlace::Home;
    return static_cast<EDaedalusSolKeeperPlace>(daedalus::sol::KeeperLocation(S,DaedalusSolJournalInternal::Context(SkyDirector)));
}
FString UDaedalusSolReachJournal::GetKeeperLine() const {
    daedalus::sol::State S; if(!DaedalusSolJournalInternal::Read(Snapshot,S)) return TEXT("The journal needs to be restored.");
    return FString(UTF8_TO_TCHAR(daedalus::sol::KeeperLine(S).c_str()));
}
bool UDaedalusSolReachJournal::IsCisternClueVisible() const { return daedalus::sol::CisternClueVisible(DaedalusSolJournalInternal::Context(SkyDirector)); }
