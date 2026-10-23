// SPDX-License-Identifier: MIT
#pragma once
#if WITH_EDITOR
#include "CoreMinimal.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonWriter.h"

namespace DaedalusMaterialCachedDiagnostic
{
using FJson = TSharedRef<FJsonObject>;
using FValues = TArray<TSharedPtr<FJsonValue>>;
inline constexpr int32 MaxInputs = 128, MaxOutputs = 16, MaxSelected = 3, MaxRich = 3;
inline constexpr int32 ReceiptBytes = 524288;

inline FString Serialize(FJson Value)
{
	FString Text;
	if (!FJsonSerializer::Serialize(Value, TJsonWriterFactory<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>::Create(&Text))) return FString();
	return Text;
}
inline int32 Utf8Bytes(FJson Value) { const FString Text = Serialize(Value); return Text.IsEmpty() ? MAX_int32 : FTCHARToUTF8(*Text).Length(); }

// Resolve an object path in JSON only; numeric segments address arrays.
inline TSharedPtr<FJsonObject> ObjectAt(FJson Root, const TArray<FString>& Path)
{
	TSharedPtr<FJsonValue> Current = MakeShared<FJsonValueObject>(Root);
	for (const FString& Part : Path)
	{
		if (!Current) return nullptr;
		if (Current->Type == EJson::Object)
		{
			Current = Current->AsObject()->TryGetField(FStringView(Part));
			if (!Current) return nullptr;
		}
		else if (Current->Type == EJson::Array && Part.IsNumeric())
		{
			const int32 Index = FCString::Atoi(*Part);
			if (!Current->AsArray().IsValidIndex(Index)) return nullptr;
			Current = Current->AsArray()[Index];
		}
		else return nullptr;
	}
	return Current && Current->Type == EJson::Object ? Current->AsObject() : nullptr;
}

struct FEnvelopeBudget
{
	FJson Root;
	int32 Limit;
	// Included in every prospective serialized envelope, then removed at Finish.
	// All status keys/omission lists/reasons already exist before collection. Reasons
	// start at128ASCII chars and only shrink; counts grow by at most12 bytes total.
	static constexpr int32 FramingReserve = 256;
	explicit FEnvelopeBudget(FJson InRoot, int32 InLimit = ReceiptBytes) : Root(InRoot), Limit(InLimit)
	{
		Root->SetStringField(TEXT("_diagnostic_budget_reserve"), FString::ChrN(FramingReserve, TEXT('x')));
	}
	bool TryAppend(const TArray<FString>& Path, const FString& Key, TSharedPtr<FJsonValue> Entry)
	{
		// Candidate is a separate DOM. Actual escaped UTF8 and enclosing framing are
		// measured BEFORE changing the retained envelope; failure leaves it untouched.
		TSharedPtr<FJsonObject> Candidate;
		if (!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Serialize(Root)), Candidate) || !Candidate) return false;
		auto Target = ObjectAt(Candidate.ToSharedRef(), Path);
		auto Actual = ObjectAt(Root, Path);
		if (!Target || !Actual || !Target->HasTypedField<EJson::Array>(Key)) return false;
		FValues Prospective = Target->GetArrayField(Key);
		Prospective.Add(Entry);
		Target->SetArrayField(Key, Prospective);
		if (Utf8Bytes(Candidate.ToSharedRef()) > Limit) return false;
		FValues Accepted = Actual->GetArrayField(Key);
		Accepted.Add(Entry);
		Actual->SetArrayField(Key, Accepted);
		return true;
	}
	bool Finish()
	{
		Root->RemoveField(TEXT("_diagnostic_budget_reserve"));
		return Utf8Bytes(Root) <= Limit;
	}
};

struct FInput
{
	int32 Index = -1;
	FGuid BindingId, NodeId;
	FString NodePath;
	bool bReady = false; // resolved, readable, exact FunctionInput class
	FJson Fact = MakeShared<FJsonObject>();
};
enum class ERoute { DirectLeaf, FunctionInput, Unsupported };
struct FOutput
{
	int32 Index = -1;
	FGuid BindingId, NodeId, AInputId;
	FString NodePath, AInputPath;
	bool bReady = false; // resolved, readable, exact FunctionOutput class
	ERoute Route = ERoute::Unsupported;
	FJson Fact = MakeShared<FJsonObject>();
};

inline bool ValidManifest(const TArray<FInput>& Inputs, int32 Expected)
{
	if (Expected < 0 || Expected > MaxInputs || Inputs.Num() != Expected) return false;
	TSet<FGuid> Bindings, Nodes;
	TSet<FString> Paths;
	TSet<int32> Indices;
	for (const auto& Input : Inputs)
	{
		if (!Input.bReady || !Input.BindingId.IsValid() || Input.BindingId != Input.NodeId
			|| Input.NodePath.IsEmpty() || Input.Index < 0 || Input.Index >= Expected
			|| Bindings.Contains(Input.BindingId) || Nodes.Contains(Input.NodeId)
			|| Paths.Contains(Input.NodePath) || Indices.Contains(Input.Index)) return false;
		Bindings.Add(Input.BindingId); Nodes.Add(Input.NodeId); Paths.Add(Input.NodePath); Indices.Add(Input.Index);
	}
	return true;
}

inline bool SelectRich(const TArray<FInput>& Inputs, const TArray<FOutput>& Outputs, TArray<int32>& Selected)
{
	Selected.Reset();
	for (const auto& Output : Outputs)
	{
		if (!Output.bReady || !Output.BindingId.IsValid() || Output.BindingId != Output.NodeId) return false;
		if (Output.Route != ERoute::FunctionInput) continue; // no recursion/default inference
		int32 Matches = 0, Match = -1;
		for (const auto& Input : Inputs)
			if (Input.bReady && Output.AInputId.IsValid() && Input.BindingId == Output.AInputId
				&& Input.NodeId == Output.AInputId && Input.NodePath == Output.AInputPath) { ++Matches; Match = Input.Index; }
		if (Matches != 1) return false;
		Selected.AddUnique(Match);
		if (Selected.Num() > MaxRich) return false;
	}
	Selected.Sort();
	return true;
}

inline FValues Numbers(const TArray<int32>& Indices)
{
	FValues Values; for (int32 Index : Indices) Values.Add(MakeShared<FJsonValueNumber>(Index)); return Values;
}
inline FJson Status(int32 Expected, const TArray<int32>& Omitted)
{
	FJson Value = MakeShared<FJsonObject>();
	Value->SetNumberField(TEXT("expected_count"), Expected);
	Value->SetNumberField(TEXT("captured_count"), 0);
	Value->SetBoolField(TEXT("complete"), false);
	Value->SetStringField(TEXT("reason"), FString::ChrN(128, TEXT('r')));
	Value->SetArrayField(TEXT("omitted_indices"), Numbers(Omitted));
	return Value;
}

struct FProjection
{
	FJson Call = MakeShared<FJsonObject>();
	TArray<FString> Path;
	TArray<FInput> Inputs;
	TArray<FOutput> Outputs;
	TArray<int32> Selected, RichIndices;
	int32 InputCount = 0, OutputCount = 0;
	FJson ManifestStatus = MakeShared<FJsonObject>(), OutputStatus = MakeShared<FJsonObject>(), RichStatus = MakeShared<FJsonObject>();
	bool bManifestValid = false, bRichSelectionValid = false;
	TFunction<FJson(int32)> BuildRich;

	void Initialize()
	{
		RichIndices.Reset();
		TArray<int32> Omitted;
		if (InputCount <= MaxInputs) for (int32 I = 0; I < InputCount; ++I) Omitted.Add(I);
		ManifestStatus = Status(InputCount, Omitted);
		ManifestStatus->SetNumberField(TEXT("omitted_range_count"), InputCount > MaxInputs ? InputCount : 0);
		bManifestValid = ValidManifest(Inputs, InputCount);
		ManifestStatus->SetBoolField(TEXT("identities_valid"), bManifestValid);
		OutputStatus = Status(Selected.Num(), Selected);
		bRichSelectionValid = bManifestValid && SelectRich(Inputs, Outputs, RichIndices);
		RichStatus = Status(RichIndices.Num(), RichIndices);
		RichStatus->SetBoolField(TEXT("selection_qualified"), bRichSelectionValid);
		TArray<int32> Intentional, Unsupported;
		for (const auto& I : Inputs) if (!RichIndices.Contains(I.Index)) Intentional.Add(I.Index);
		for (const auto& O : Outputs) if (O.Route == ERoute::Unsupported) Unsupported.Add(O.Index);
		RichStatus->SetArrayField(TEXT("intentionally_omitted_input_indices"), Numbers(Intentional));
		RichStatus->SetArrayField(TEXT("unsupported_output_indices"), Numbers(Unsupported));
		Call->SetArrayField(TEXT("function_inputs"), {});
		Call->SetArrayField(TEXT("selected_function_outputs"), {});
		Call->SetArrayField(TEXT("rich_inputs"), {});
		Call->SetObjectField(TEXT("input_manifest_status"), ManifestStatus);
		Call->SetObjectField(TEXT("selected_outputs_status"), OutputStatus);
		Call->SetObjectField(TEXT("rich_inputs_status"), RichStatus);
	}
	bool Complete() const { return ManifestStatus->GetBoolField(TEXT("complete")) && OutputStatus->GetBoolField(TEXT("complete")) && RichStatus->GetBoolField(TEXT("complete")); }
};

inline void UpdateStatus(FJson State, const TArray<int32>& Omitted, int32 Captured, bool Complete, const TCHAR* Reason)
{
	State->SetArrayField(TEXT("omitted_indices"), Numbers(Omitted));
	State->SetNumberField(TEXT("captured_count"), Captured);
	State->SetBoolField(TEXT("complete"), Complete);
	State->SetStringField(TEXT("reason"), Reason);
}

inline void CaptureAll(FEnvelopeBudget& Budget, TArray<FProjection>& Work)
{
	// All calls' selected outputs precede ANY input manifest growth.
	for (auto& W : Work)
	{
		TArray<int32> Omitted = W.Selected;
		int32 Count = 0; bool Valid = true;
		TSet<FGuid> Ids; TSet<int32> Indices; TSet<FString> NodePaths;
		const bool BoundValid = W.OutputCount >= 0 && W.OutputCount <= MaxOutputs && W.Selected.Num() <= MaxSelected && W.Outputs.Num() <= MaxSelected;
		if (BoundValid)
			for (const auto& O : W.Outputs)
			{
				if (!W.Selected.Contains(O.Index) || O.Index < 0 || O.Index >= W.OutputCount || Indices.Contains(O.Index)) { Valid = false; continue; }
				Indices.Add(O.Index);
				Valid &= O.bReady && O.BindingId.IsValid() && O.BindingId == O.NodeId && !Ids.Contains(O.BindingId) && !O.NodePath.IsEmpty() && !NodePaths.Contains(O.NodePath);
				Ids.Add(O.BindingId); NodePaths.Add(O.NodePath);
				if (Budget.TryAppend(W.Path, TEXT("selected_function_outputs"), MakeShared<FJsonValueObject>(O.Fact))) { ++Count; Omitted.Remove(O.Index); }
			}
		UpdateStatus(W.OutputStatus, Omitted, Count, BoundValid && Valid && Omitted.IsEmpty() && Count == W.Selected.Num(),
			W.OutputCount > MaxOutputs ? TEXT("output_array_bound") : !Valid ? TEXT("invalid_output_identity") : Omitted.IsEmpty() ? TEXT("complete") : TEXT("output_missing_or_budget"));
	}
	for (auto& W : Work)
	{
		TArray<int32> Omitted;
		if (W.InputCount <= MaxInputs) for (int32 I = 0; I < W.InputCount; ++I) Omitted.Add(I);
		int32 Count = 0;
		if (W.InputCount >= 0 && W.InputCount <= MaxInputs && W.Inputs.Num() <= MaxInputs)
			for (const auto& I : W.Inputs)
				if (Budget.TryAppend(W.Path, TEXT("function_inputs"), MakeShared<FJsonValueObject>(I.Fact))) { ++Count; Omitted.Remove(I.Index); }
		const bool Complete = W.bManifestValid && Omitted.IsEmpty() && Count == W.InputCount;
		UpdateStatus(W.ManifestStatus, Omitted, Count, Complete, W.InputCount > MaxInputs ? TEXT("input_manifest_bound") : !W.bManifestValid ? TEXT("invalid_missing_duplicate_identity") : Complete ? TEXT("complete") : TEXT("input_budget"));
	}
	for (auto& W : Work)
	{
		TArray<int32> Omitted = W.RichIndices;
		int32 Count = 0; bool Valid = true;
		const bool Eligible = W.bRichSelectionValid && W.ManifestStatus->GetBoolField(TEXT("complete")) && W.OutputStatus->GetBoolField(TEXT("complete"));
		W.RichStatus->SetBoolField(TEXT("selection_qualified"), Eligible);
		if (Eligible && W.RichIndices.Num() <= MaxRich && W.BuildRich)
			for (int32 Index : W.RichIndices)
			{
				const FJson Fact = W.BuildRich(Index);
				Valid &= Fact->HasTypedField<EJson::Boolean>(TEXT("capture_complete")) && Fact->GetBoolField(TEXT("capture_complete"));
				if (Budget.TryAppend(W.Path, TEXT("rich_inputs"), MakeShared<FJsonValueObject>(Fact))) { ++Count; Omitted.Remove(Index); }
			}
		const bool Complete = Eligible && Valid && Omitted.IsEmpty();
		UpdateStatus(W.RichStatus, Omitted, Count, Complete, !Eligible ? TEXT("manifest_or_output_identity_incomplete") : !Valid ? TEXT("rich_capture_incomplete") : Complete ? TEXT("complete_selected_subset") : TEXT("rich_budget"));
	}
}
} // namespace DaedalusMaterialCachedDiagnostic
#endif
