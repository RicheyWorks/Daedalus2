// SPDX-License-Identifier: MIT
#include "DaedalusTideglassWorkshopComponent.h"
#include "DaedalusTideglassCraftCore.h"
#include "DaedalusOrrery.h"
#include "DaedalusSkyDirector.h"
#include "GameFramework/Actor.h"
#include "Engine/World.h"

namespace TideglassWorkshop
{
using namespace daedalus::tideglass;

static bool Lossless(const FString& Value)
{
	for (int32 Index = 0; Index < Value.Len(); ++Index) if (Value[Index] == TCHAR(0)) return false;
	const FTCHARToUTF8 Encoded(*Value);
	return Value == FString(UTF8_TO_TCHAR(Encoded.Get()));
}
static bool Lossless(const FDaedalusTideglassConfig& C)
{
	if (!Lossless(C.ValveItem) || !Lossless(C.WaterItem) || !Lossless(C.RewardItem)) return false;
	for (const auto& Item : C.ValveInputs) if (!Lossless(Item.Key)) return false;
	return true;
}

static State ToCore(const FDaedalusTideglassState& S)
{
	State Out;
	Out.revision = S.Revision;
	Out.valveCrafted = S.bValveCrafted; Out.conduitOpen = S.bConduitOpen; Out.commissionPaid = S.bCommissionPaid;
	for (const auto& Item : S.Items) Out.items.emplace(TCHAR_TO_UTF8(*Item.Key), Item.Value);
	for (const auto& Receipt : S.Receipts) Out.receipts.emplace(TCHAR_TO_UTF8(*Receipt.Key), TCHAR_TO_UTF8(*Receipt.Value));
	return Out;
}
static FDaedalusTideglassState FromCore(const State& S)
{
	FDaedalusTideglassState Out;
	Out.Revision = S.revision;
	Out.bValveCrafted = S.valveCrafted; Out.bConduitOpen = S.conduitOpen; Out.bCommissionPaid = S.commissionPaid;
	for (const auto& Item : S.items) Out.Items.Add(UTF8_TO_TCHAR(Item.first.c_str()), Item.second);
	for (const auto& Receipt : S.receipts) Out.Receipts.Add(UTF8_TO_TCHAR(Receipt.first.c_str()), UTF8_TO_TCHAR(Receipt.second.c_str()));
	return Out;
}
static Config ToCore(const FDaedalusTideglassConfig& C)
{
	Config Out;
	Out.valveInputs.clear();
	for (const auto& Item : C.ValveInputs) Out.valveInputs.emplace(TCHAR_TO_UTF8(*Item.Key), Item.Value);
	Out.valveItem = TCHAR_TO_UTF8(*C.ValveItem); Out.waterItem = TCHAR_TO_UTF8(*C.WaterItem);
	Out.rewardItem = TCHAR_TO_UTF8(*C.RewardItem);
	Out.waterUnits = C.WaterUnits; Out.rewardUnits = C.RewardUnits;
	Out.installStartHour = C.InstallStartHour; Out.installEndHour = C.InstallEndHour;
	return Out;
}
static EDaedalusTideglassStatus FromCore(Status S)
{
	switch (S)
	{
	case Status::AlreadyCommitted: return EDaedalusTideglassStatus::AlreadyCommitted;
	case Status::Insufficient: return EDaedalusTideglassStatus::Insufficient;
	case Status::WrongWindow: return EDaedalusTideglassStatus::WrongWindow;
	case Status::UnsafeWeather: return EDaedalusTideglassStatus::UnsafeWeather;
	case Status::WaterUnavailable: return EDaedalusTideglassStatus::WaterUnavailable;
	case Status::PrerequisiteMissing: return EDaedalusTideglassStatus::PrerequisiteMissing;
	case Status::AlreadyComplete: return EDaedalusTideglassStatus::AlreadyComplete;
	case Status::Stale: return EDaedalusTideglassStatus::Stale;
	case Status::Overflow: return EDaedalusTideglassStatus::Overflow;
	case Status::ReceiptLimit: return EDaedalusTideglassStatus::ReceiptLimit;
	default: return EDaedalusTideglassStatus::Invalid;
	}
}
static FString Message(const FDaedalusTideglassResult& R)
{
	switch (R.Status)
	{
	case EDaedalusTideglassStatus::Committed:
		if (R.Action == EDaedalusTideglassAction::CraftValve) return TEXT("Pulse valve made. Install it after the filter is clean, during a dry morning.");
		if (R.Action == EDaedalusTideglassAction::InstallValve) return TEXT("The conduit opens. Deliver the requested clean water to complete the harbour commission.");
		return TEXT("Water delivery recorded. Your harbour credit and restored conduit are saved by the inventory host.");
	case EDaedalusTideglassStatus::AlreadyCommitted: return TEXT("That action is already recorded. No materials were used again.");
	case EDaedalusTideglassStatus::Insufficient: return TEXT("The workshop needs more materials. Your stock is unchanged.");
	case EDaedalusTideglassStatus::WrongWindow: return TEXT("Installation needs the configured morning window. Read the shared sky clock.");
	case EDaedalusTideglassStatus::UnsafeWeather: return TEXT("Rain prevents the seal from setting. Wait for dry weather.");
	case EDaedalusTideglassStatus::WaterUnavailable: return TEXT("Repair the existing water filter first.");
	case EDaedalusTideglassStatus::PrerequisiteMissing: return TEXT("Complete the preceding workshop task first.");
	case EDaedalusTideglassStatus::AlreadyComplete: return TEXT("This commission task is complete.");
	case EDaedalusTideglassStatus::Stale: return TEXT("The stock changed. No prepared transaction was applied.");
	case EDaedalusTideglassStatus::Unbound: return TEXT("The workshop awaits its inventory and save connection.");
	case EDaedalusTideglassStatus::NoClock: return TEXT("The shared sky clock is unavailable.");
	case EDaedalusTideglassStatus::NoAuthority: return TEXT("Only the inventory authority may commit this action.");
	case EDaedalusTideglassStatus::CommitUncertain: return TEXT("The save outcome needs owner reconciliation. Do not repeat the action.");
	case EDaedalusTideglassStatus::HostRejected: return TEXT("The inventory host refused the commit. No success is claimed.");
	case EDaedalusTideglassStatus::ReadFailed: return TEXT("The inventory host could not provide a valid snapshot.");
	case EDaedalusTideglassStatus::Overflow: return TEXT("Stock capacity would overflow. No materials were used.");
	case EDaedalusTideglassStatus::ReceiptLimit: return TEXT("The saved receipt limit needs owner attention.");
	default: return TEXT("The workshop configuration or saved state is invalid.");
	}
}
}

UDaedalusTideglassWorkshopComponent::UDaedalusTideglassWorkshopComponent()
{
	PrimaryComponentTick.bCanEverTick = false;
}

bool UDaedalusTideglassWorkshopComponent::ReadState(FDaedalusTideglassState& State) const
{
	if (!IsInGameThread()) return false;
	UObject* Host = InventoryHost.GetObject();
	if (!IsValid(Host) || !Host->GetClass()->ImplementsInterface(UDaedalusTideglassHost::StaticClass())) return false;
	FDaedalusTideglassState Snapshot;
	if (!IDaedalusTideglassHost::Execute_ReadTideglassState(Host, Snapshot) || InventoryHost.GetObject() != Host ||
		Snapshot.Version != 1 ||
		!daedalus::tideglass::detail::validState(TideglassWorkshop::ToCore(Snapshot))) return false;
	for (const auto& Item : Snapshot.Items) if (!TideglassWorkshop::Lossless(Item.Key)) return false;
	for (const auto& Receipt : Snapshot.Receipts)
		if (!TideglassWorkshop::Lossless(Receipt.Key) || !TideglassWorkshop::Lossless(Receipt.Value)) return false;
	// Reject lossy UTF-8/embedded-NUL conversion instead of dropping or aliasing host stock keys.
	const FDaedalusTideglassState RoundTrip = TideglassWorkshop::FromCore(TideglassWorkshop::ToCore(Snapshot));
	if (!Snapshot.Items.OrderIndependentCompareEqual(RoundTrip.Items) ||
		!Snapshot.Receipts.OrderIndependentCompareEqual(RoundTrip.Receipts)) return false;
	State = MoveTemp(Snapshot);
	return true;
}

FDaedalusTideglassResult UDaedalusTideglassWorkshopComponent::Finish(FDaedalusTideglassResult Result)
{
	Result.Message = TideglassWorkshop::Message(Result);
	Result.Cue = Result.Status == EDaedalusTideglassStatus::Committed ? TEXT("tideglass.commit") :
		Result.Status == EDaedalusTideglassStatus::AlreadyCommitted ? TEXT("tideglass.recorded") : TEXT("tideglass.blocked");
	// A refusal from a worker thread must not call Blueprint/UI/audio handlers on that thread.
	if (IsInGameThread()) OnFeedback.Broadcast(Result);
	return Result;
}

FDaedalusTideglassResult UDaedalusTideglassWorkshopComponent::TryAction(EDaedalusTideglassAction Action,
	const FString& OperationId)
{
	using namespace daedalus::tideglass;
	FDaedalusTideglassResult Result;
	Result.Action = Action; Result.OperationId = OperationId;
	if (!IsInGameThread() || !GetWorld() || !GetWorld()->IsGameWorld() || !GetOwner() || !GetOwner()->HasAuthority())
	{ Result.Status = EDaedalusTideglassStatus::NoAuthority; return Finish(Result); }
	if (bNeedsReconciliation)
	{ Result.Status = EDaedalusTideglassStatus::CommitUncertain; return Finish(Result); }
	if (!TideglassWorkshop::Lossless(OperationId) || !TideglassWorkshop::Lossless(Config))
	{ Result.Status = EDaedalusTideglassStatus::Invalid; return Finish(Result); }
	UObject* Host = InventoryHost.GetObject();
	if (!IsValid(Host) || !Host->GetClass()->ImplementsInterface(UDaedalusTideglassHost::StaticClass()))
	{ Result.Status = EDaedalusTideglassStatus::Unbound; return Finish(Result); }
	FDaedalusTideglassState Before;
	if (!ReadState(Before)) { Result.Status = EDaedalusTideglassStatus::ReadFailed; return Finish(Result); }
	Result.Revision = Before.Revision;
	ADaedalusSkyDirector* Sky = ADaedalusSkyDirector::Find(this);
	if (!Sky) { Result.Status = EDaedalusTideglassStatus::NoClock; return Finish(Result); }
	Context Environment;
	Environment.day = Sky->GetDay(); Environment.hour = Sky->GetHour();
	switch (Sky->Weather)
	{
	case EDaedalusWeather::Clear: case EDaedalusWeather::Overcast: case EDaedalusWeather::Fog: break;
	case EDaedalusWeather::Rain: case EDaedalusWeather::Storm: Environment.raining = true; break;
	default: Result.Status = EDaedalusTideglassStatus::Invalid; return Finish(Result);
	}
	if (bUseOrreryFilter)
	{
		const UDaedalusOrrery* Orrery = UDaedalusOrrery::Get(this);
		Environment.cleanWaterAvailable = Orrery && Orrery->bCleanWater;
	}
	else Environment.cleanWaterAvailable = IDaedalusTideglassHost::Execute_HasCleanWaterForTideglass(Host);
	const Plan Prepared = prepare(TideglassWorkshop::ToCore(Before), TideglassWorkshop::ToCore(Config),
		static_cast<daedalus::tideglass::Action>(Action), Environment, TCHAR_TO_UTF8(*OperationId), Before.Revision);
	for (const auto& Missing : Prepared.missing) Result.Missing.Add(UTF8_TO_TCHAR(Missing.first.c_str()), Missing.second);
	if (Prepared.status != Status::Ready) { Result.Status = TideglassWorkshop::FromCore(Prepared.status); return Finish(Result); }
	if (!IDaedalusTideglassHost::Execute_CanCommitTideglassState(Host) || InventoryHost.GetObject() != Host)
	{ Result.Status = EDaedalusTideglassStatus::HostRejected; return Finish(Result); }
	const FDaedalusTideglassState Proposed = TideglassWorkshop::FromCore(Prepared.after);
	const EDaedalusTideglassHostCommit Reply = IDaedalusTideglassHost::Execute_TryCommitTideglassState(Host, Before, Proposed, OperationId);
	FDaedalusTideglassState Observed;
	const bool bReadback = IsValid(Host) && InventoryHost.GetObject() == Host && ReadState(Observed);
	const bool bExactCommit = bReadback && TideglassWorkshop::ToCore(Observed) == Prepared.after;
	if (Reply == EDaedalusTideglassHostCommit::Committed && bExactCommit)
	{
		Result.Status = EDaedalusTideglassStatus::Committed; Result.Revision = Observed.Revision;
		OnConsequence.Broadcast(Action, Observed);
		return Finish(Result);
	}
	if (Reply == EDaedalusTideglassHostCommit::Rejected && bReadback && TideglassWorkshop::ToCore(Observed) == Prepared.before)
	{ Result.Status = EDaedalusTideglassStatus::HostRejected; return Finish(Result); }
	// Never compensate/replay an ambiguous save. The owner must inspect the durable receipt.
	bNeedsReconciliation = true; UncertainOperation = OperationId; UncertainProposed = Proposed;
	UncertainHost = Host;
	Result.Status = EDaedalusTideglassStatus::CommitUncertain;
	return Finish(Result);
}

bool UDaedalusTideglassWorkshopComponent::ReconcileCommittedOperation(const FString& OperationId)
{
	if (!IsInGameThread() || !GetOwner() || !GetOwner()->HasAuthority() || !bNeedsReconciliation ||
		OperationId != UncertainOperation || !UncertainHost.IsValid() ||
		InventoryHost.GetObject() != UncertainHost.Get()) return false;
	FDaedalusTideglassState Observed;
	if (!ReadState(Observed) || Observed.Revision < UncertainProposed.Revision) return false;
	const FString* ActualReceipt = Observed.Receipts.Find(OperationId);
	const FString* ExpectedReceipt = UncertainProposed.Receipts.Find(OperationId);
	if (!ActualReceipt || !ExpectedReceipt || *ActualReceipt != *ExpectedReceipt ||
		(UncertainProposed.bValveCrafted && !Observed.bValveCrafted) ||
		(UncertainProposed.bConduitOpen && !Observed.bConduitOpen) ||
		(UncertainProposed.bCommissionPaid && !Observed.bCommissionPaid)) return false;
	UObject* Host = UncertainHost.Get();
	if (!IDaedalusTideglassHost::Execute_ConfirmDurableTideglassReceipt(Host, OperationId,
		*ExpectedReceipt, UncertainProposed.Revision) || InventoryHost.GetObject() != Host) return false;
	FDaedalusTideglassState Fresh;
	if (!ReadState(Fresh) || TideglassWorkshop::ToCore(Fresh) != TideglassWorkshop::ToCore(Observed)) return false;
	bNeedsReconciliation = false; UncertainOperation.Reset(); UncertainProposed = FDaedalusTideglassState();
	UncertainHost.Reset();
	return true;
}
