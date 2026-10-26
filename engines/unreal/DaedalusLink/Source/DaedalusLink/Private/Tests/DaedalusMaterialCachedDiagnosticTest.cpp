// SPDX-License-Identifier: MIT
#if WITH_EDITOR && WITH_DEV_AUTOMATION_TESTS
#include "DaedalusMaterialCachedDiagnostic.h"
#include "Misc/AutomationTest.h"

namespace
{
using namespace DaedalusMaterialCachedDiagnostic;

struct FFixture
{
	FJson Root = MakeShared<FJsonObject>();
	TArray<FProjection> Work;
	TSharedRef<int32> RichCalls = MakeShared<int32>(0);
};

FGuid InputId(int32 Index, int32 Salt = 1) { return FGuid(0x12345678u, Salt, Index + 1, 0xabcdef01u); }

FFixture Fixture(int32 InputCount, int32 OutputCount, const TArray<int32>& Selected = {0, 1, 3}, int32 Materials = 1, int32 InputPayload = 0)
{
	FFixture Result;
	Result.Root->SetStringField(TEXT("schema"), TEXT("actual-helper-test-envelope"));
	Result.Root->SetBoolField(TEXT("admission_changed"), false);
	// Actual escaping and non-ASCII UTF8 are part of the enclosing frame.
	Result.Root->SetStringField(TEXT("frame"), TEXT("quoted \"frame\"\n\u00e9\u6f22"));
	FValues MaterialRows;
	for (int32 MaterialIndex = 0; MaterialIndex < Materials; ++MaterialIndex)
	{
		FProjection W;
		W.InputCount = InputCount; W.OutputCount = OutputCount; W.Selected = Selected;
		W.Path = {TEXT("materials"), FString::FromInt(MaterialIndex), TEXT("call")};
		for (int32 Index = 0; Index < InputCount; ++Index)
		{
			FInput I;
			I.Index = Index; I.BindingId = I.NodeId = InputId(Index, MaterialIndex + 1);
			I.NodePath = FString::Printf(TEXT("/Game/CodexToolEvaluation/Test/F%d.F%d:Input_%d"), MaterialIndex, MaterialIndex, Index);
			I.bReady = true;
			I.Fact->SetNumberField(TEXT("index"), Index);
			I.Fact->SetStringField(TEXT("binding_id"), I.BindingId.ToString(EGuidFormats::Digits));
			I.Fact->SetStringField(TEXT("node_path"), I.NodePath);
			if (InputPayload) I.Fact->SetStringField(TEXT("payload"), FString::ChrN(InputPayload, TEXT('p')));
			W.Inputs.Add(MoveTemp(I));
		}
		for (int32 N = 0; N < Selected.Num(); ++N)
		{
			FOutput O;
			O.Index = Selected[N]; O.BindingId = O.NodeId = InputId(1000 + N, MaterialIndex + 1);
			O.NodePath = FString::Printf(TEXT("/Game/CodexToolEvaluation/Test/F%d.F%d:Output_%d"), MaterialIndex, MaterialIndex, O.Index);
			O.bReady = true;
			O.Route = N < W.Inputs.Num() ? ERoute::FunctionInput : ERoute::DirectLeaf;
			if (N < W.Inputs.Num()) { O.AInputId = W.Inputs[N].NodeId; O.AInputPath = W.Inputs[N].NodePath; }
			O.Fact->SetNumberField(TEXT("index"), O.Index);
			O.Fact->SetStringField(TEXT("binding_id"), O.BindingId.ToString(EGuidFormats::Digits));
			O.Fact->SetStringField(TEXT("node_path"), O.NodePath);
			W.Outputs.Add(MoveTemp(O));
		}
		const auto Calls = Result.RichCalls;
		W.BuildRich = [Calls](int32 Index)
		{
			++*Calls;
			FJson Rich = MakeShared<FJsonObject>();
			Rich->SetNumberField(TEXT("index"), Index);
			Rich->SetBoolField(TEXT("capture_complete"), true);
			return Rich;
		};
		W.Initialize();
		FJson Material = MakeShared<FJsonObject>();
		Material->SetStringField(TEXT("name"), FString::Printf(TEXT("M%d"), MaterialIndex));
		Material->SetObjectField(TEXT("call"), W.Call);
		MaterialRows.Add(MakeShared<FJsonValueObject>(Material));
		Result.Work.Add(MoveTemp(W));
	}
	Result.Root->SetArrayField(TEXT("materials"), MaterialRows);
	return Result;
}

void Reinitialize(FFixture& Value) { for (auto& W : Value.Work) W.Initialize(); }
bool Run(FFixture& Value, int32 Limit = ReceiptBytes)
{
	FEnvelopeBudget Budget(Value.Root, Limit);
	CaptureAll(Budget, Value.Work);
	return Budget.Finish();
}
int32 Count(FJson Status) { return static_cast<int32>(Status->GetNumberField(TEXT("captured_count"))); }
bool Complete(FJson Status) { return Status->GetBoolField(TEXT("complete")); }
int32 Bytes(FJson Root)
{
	// Independent byte measurement for budget assertions, not a second collector.
	const FString Text = Serialize(Root);
	return FTCHARToUTF8(*Text).Length();
}

FJson ByteRoot(TSharedPtr<FJsonValue> Entry = nullptr)
{
	FJson Root = MakeShared<FJsonObject>();
	FJson First = MakeShared<FJsonObject>(), Second = MakeShared<FJsonObject>();
	FValues Rows;
	if (Entry) Rows.Add(Entry);
	First->SetArrayField(TEXT("rows"), Rows);
	Second->SetStringField(TEXT("sibling_frame"), TEXT("\u6f22\u00e9 \"quoted\"\nsecond material"));
	FValues Materials = {MakeShared<FJsonValueObject>(First), MakeShared<FJsonValueObject>(Second)};
	Root->SetArrayField(TEXT("materials"), Materials);
	Root->SetStringField(TEXT("outer_frame"), TEXT("prefix\n\"suffix\""));
	return Root;
}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDaedalusMaterialCachedBounds,
	"Daedalus.Material.Cached.Bounds", EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FDaedalusMaterialCachedBounds::RunTest(const FString& Parameters)
{
	for (int32 Inputs : {127, 128, 129})
	{
		auto F = Fixture(Inputs, 12);
		TestTrue(TEXT("Bounded envelope finalizes"), Run(F));
		const auto& W = F.Work[0];
		TestEqual(TEXT("Input expected count retained"), static_cast<int32>(W.ManifestStatus->GetNumberField(TEXT("expected_count"))), Inputs);
		TestEqual(TEXT("Input capture count obeys independent cap"), Count(W.ManifestStatus), Inputs <= MaxInputs ? Inputs : 0);
		TestEqual(TEXT("Input completeness obeys cap"), Complete(W.ManifestStatus), Inputs <= MaxInputs);
		TestTrue(TEXT("Over-limit inputs do not suppress selected outputs"), Complete(W.OutputStatus));
		TestEqual(TEXT("Three selected outputs remain captured"), Count(W.OutputStatus), 3);
		if (Inputs > MaxInputs)
		{
			TestEqual(TEXT("Over-limit omission range is explicit"), static_cast<int32>(W.ManifestStatus->GetNumberField(TEXT("omitted_range_count"))), Inputs);
			TestEqual(TEXT("No rich callback from over-limit manifest"), *F.RichCalls, 0);
		}
	}
	for (int32 Outputs : {15, 16, 17})
	{
		auto F = Fixture(89, Outputs);
		TestTrue(TEXT("Output boundary envelope finalizes"), Run(F));
		TestTrue(TEXT("Over-limit outputs do not suppress input manifest"), Complete(F.Work[0].ManifestStatus));
		TestEqual(TEXT("Output completeness obeys independent cap"), Complete(F.Work[0].OutputStatus), Outputs <= MaxOutputs);
		TestEqual(TEXT("Output capture count obeys cap"), Count(F.Work[0].OutputStatus), Outputs <= MaxOutputs ? 3 : 0);
		if (Outputs > MaxOutputs)
		{
			TestEqual(TEXT("Three omitted output indices are explicit"), F.Work[0].OutputStatus->GetArrayField(TEXT("omitted_indices")).Num(), 3);
			TestEqual(TEXT("No rich callback with output capture incomplete"), *F.RichCalls, 0);
		}
	}
	auto Observed = Fixture(89, 12, {0, 1, 3}, 2);
	TestTrue(TEXT("Observed two-material 89/12 envelope finalizes"), Run(Observed));
	for (const auto& W : Observed.Work)
	{
		TestTrue(TEXT("Observed complete route projection"), W.Complete());
		TestEqual(TEXT("Every input identity captured"), Count(W.ManifestStatus), 89);
		TestEqual(TEXT("Only three rich inputs captured"), Count(W.RichStatus), 3);
		TestEqual(TEXT("Unneeded rich subset is explicitly intentional"), W.RichStatus->GetArrayField(TEXT("intentionally_omitted_input_indices")).Num(), 86);
		const auto& Captured = W.Call->GetArrayField(TEXT("selected_function_outputs"));
		TestEqual(TEXT("Exactly three actual selected entries before indexing"), Captured.Num(), 3);
		if (Captured.Num() == 3)
		{
			TestEqual(TEXT("Actual selected output0"), static_cast<int32>(Captured[0]->AsObject()->GetNumberField(TEXT("index"))), 0);
			TestEqual(TEXT("Actual selected output1"), static_cast<int32>(Captured[1]->AsObject()->GetNumberField(TEXT("index"))), 1);
			TestEqual(TEXT("Actual selected output3"), static_cast<int32>(Captured[2]->AsObject()->GetNumberField(TEXT("index"))), 3);
		}
	}
	for (const TArray<int32>& Request : {TArray<int32>({-1, 1, 3}), TArray<int32>({0, 0, 3})})
	{
		auto Invalid = Fixture(89, 12, Request);
		TestTrue(TEXT("Invalid selected-index receipt finalizes"), Run(Invalid));
		TestFalse(TEXT("Negative or duplicate selected request cannot qualify"), Complete(Invalid.Work[0].OutputStatus));
		TestTrue(TEXT("Invalid selection leaves independent manifest complete"), Complete(Invalid.Work[0].ManifestStatus));
		TestEqual(TEXT("Invalid selection never invokes enrichment"), *Invalid.RichCalls, 0);
	}
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDaedalusMaterialCachedIdentity,
	"Daedalus.Material.Cached.Identity", EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FDaedalusMaterialCachedIdentity::RunTest(const FString& Parameters)
{
	const auto CheckBad = [this](const TCHAR* Label, TFunction<void(FProjection&)> Change)
	{
		auto F = Fixture(5, 12);
		Change(F.Work[0]); Reinitialize(F);
		TestFalse(Label, F.Work[0].bManifestValid);
		TestTrue(TEXT("Invalid identity receipt still fits"), Run(F));
		TestFalse(TEXT("Invalid identity cannot become complete"), Complete(F.Work[0].ManifestStatus));
		TestTrue(TEXT("Independent output facts survive invalid input identity"), Complete(F.Work[0].OutputStatus));
		TestEqual(TEXT("Invalid complete-manifest gate blocks all enrichment"), *F.RichCalls, 0);
	};
	CheckBad(TEXT("Duplicate binding/node GUID rejected"), [](FProjection& W) { W.Inputs[1].BindingId = W.Inputs[1].NodeId = W.Inputs[0].BindingId; });
	CheckBad(TEXT("Duplicate node path rejected"), [](FProjection& W) { W.Inputs[1].NodePath = W.Inputs[0].NodePath; });
	CheckBad(TEXT("Duplicate index rejected"), [](FProjection& W) { W.Inputs[1].Index = W.Inputs[0].Index; });
	CheckBad(TEXT("Missing manifest entry rejected"), [](FProjection& W) { W.Inputs.Pop(); });
	CheckBad(TEXT("Unresolved cached node is unready"), [](FProjection& W) { W.Inputs[0].bReady = false; });
	CheckBad(TEXT("Type-mismatched cached node is unready"), [](FProjection& W) { W.Inputs[2].bReady = false; });
	CheckBad(TEXT("Binding and node GUID disagreement rejected"), [](FProjection& W) { W.Inputs[2].NodeId = InputId(77); });
	CheckBad(TEXT("Zero GUID rejected"), [](FProjection& W) { W.Inputs[0].BindingId = W.Inputs[0].NodeId = FGuid(); });
	for (int32 Kind = 0; Kind < 4; ++Kind)
	{
		auto F = Fixture(5, 12);
		auto& W = F.Work[0];
		if (Kind == 0) W.Outputs[1].BindingId = W.Outputs[1].NodeId = W.Outputs[0].BindingId;
		if (Kind == 1) W.Outputs[1].NodePath = W.Outputs[0].NodePath;
		if (Kind == 2) W.Outputs[0].bReady = false;
		if (Kind == 3) W.Outputs.Pop();
		Reinitialize(F);
		TestTrue(TEXT("Invalid output receipt fits"), Run(F));
		TestFalse(TEXT("Duplicate/unready/missing output cannot qualify"), Complete(W.OutputStatus));
		TestEqual(TEXT("Invalid outputs block rich callbacks"), *F.RichCalls, 0);
	}
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDaedalusMaterialCachedRich,
	"Daedalus.Material.Cached.RichSelection", EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FDaedalusMaterialCachedRich::RunTest(const FString& Parameters)
{
	auto Three = Fixture(6, 12);
	TArray<int32> Chosen;
	TestTrue(TEXT("Three exact GUID/path matches qualify"), SelectRich(Three.Work[0].Inputs, Three.Work[0].Outputs, Chosen));
	TestTrue(TEXT("Three exact selected input indices"), Chosen == TArray<int32>({0, 1, 2}));
	auto Four = Fixture(6, 12, {0, 1, 2, 3});
	TestFalse(TEXT("Fourth distinct rich input rejected"), SelectRich(Four.Work[0].Inputs, Four.Work[0].Outputs, Chosen));
	TestTrue(TEXT("Over-limit selection receipt fits"), Run(Four));
	TestEqual(TEXT("Four selected routes never call enrichment"), *Four.RichCalls, 0);
	for (int32 Kind = 0; Kind < 3; ++Kind)
	{
		auto Bad = Fixture(6, 12);
		if (Kind == 0) Bad.Work[0].Outputs[0].AInputPath += TEXT("_unrelated");
		if (Kind == 1) Bad.Work[0].Outputs[0].AInputId = InputId(99);
		if (Kind == 2) Bad.Work[0].Inputs[1] = Bad.Work[0].Inputs[0];
		Reinitialize(Bad);
		TestTrue(TEXT("Unmatched/ambiguous input receipt fits"), Run(Bad));
		TestFalse(TEXT("Only exact unique GUID and node identity can select rich input"), Complete(Bad.Work[0].RichStatus));
		TestEqual(TEXT("No rich callback for unrelated/missing/ambiguous binding"), *Bad.RichCalls, 0);
	}
	auto Unsupported = Fixture(89, 12);
	for (auto& O : Unsupported.Work[0].Outputs)
	{
		O.Route = ERoute::Unsupported;
		O.AInputPath = TEXT("/Game/CodexToolEvaluation/Test/F.F:SelfCall"); // cyclic/indirect, never followed
	}
	Reinitialize(Unsupported);
	TestTrue(TEXT("Unsupported A diagnostic fits"), Run(Unsupported));
	TestEqual(TEXT("Unsupported/cyclic A never invokes callback or recursion"), *Unsupported.RichCalls, 0);
	TestEqual(TEXT("Unsupported output indices remain explicit"), Unsupported.Work[0].RichStatus->GetArrayField(TEXT("unsupported_output_indices")).Num(), 3);
	TestEqual(TEXT("No inferred default rich values"), Count(Unsupported.Work[0].RichStatus), 0);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDaedalusMaterialCachedUtf8Budget,
	"Daedalus.Material.Cached.Utf8Budget", EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FDaedalusMaterialCachedUtf8Budget::RunTest(const FString& Parameters)
{
	FJson Entry = MakeShared<FJsonObject>();
	Entry->SetStringField(TEXT("escaped"), TEXT("\u6f22\u00e9 \"quoted\"\nline\tend"));
	const auto JsonEntry = MakeShared<FJsonValueObject>(Entry);
	const TArray<FString> Target = {TEXT("materials"), TEXT("0")};
	auto Candidate = ByteRoot(JsonEntry);
	FEnvelopeBudget CandidateBudget(Candidate);
	const int32 ExactBytes = Bytes(Candidate);
	TestTrue(TEXT("Serialized candidate contains JSON quote escape"), Serialize(Candidate).Contains(TEXT("\\\"quoted\\\"")));
	TestTrue(TEXT("Serialized candidate contains JSON newline escape"), Serialize(Candidate).Contains(TEXT("\\n")));
	auto Fit = ByteRoot();
	FEnvelopeBudget Fits(Fit, ExactBytes);
	TestTrue(TEXT("Exact total UTF8 edge including outer sibling/frame is accepted"), Fits.TryAppend(Target, TEXT("rows"), JsonEntry));
	TestEqual(TEXT("Independent UTF8 measurement matches exact edge"), Bytes(Fit), ExactBytes);
	TestTrue(TEXT("Finish removes reserve and remains bounded"), Fits.Finish());
	TestTrue(TEXT("Final envelope remains within its total budget"), Bytes(Fit) <= ExactBytes);
	auto Refused = ByteRoot();
	FEnvelopeBudget TooSmall(Refused, ExactBytes - 1);
	const FString Before = Serialize(Refused);
	TestFalse(TEXT("One UTF8 byte below exact edge is refused before append"), TooSmall.TryAppend(Target, TEXT("rows"), JsonEntry));
	TestEqual(TEXT("Failed prospective append leaves entire actual envelope unchanged"), Serialize(Refused), Before);
	const auto RefusedTarget = ObjectAt(Refused, Target);
	TestTrue(TEXT("Refused actual target still resolves"), RefusedTarget.IsValid());
	if (RefusedTarget) TestEqual(TEXT("No silently appended target entries"), RefusedTarget->GetArrayField(TEXT("rows")).Num(), 0);
	TestTrue(TEXT("Refused candidate still finalizes safely"), TooSmall.Finish());

	// Both calls' output facts must survive before even the first large manifest
	// entry can consume budget. No rich callback may run on a partial manifest.
	auto Tight = Fixture(89, 12, {0, 1, 3}, 2, 8192);
	FEnvelopeBudget TightBudget(Tight.Root);
	TightBudget.Limit = Bytes(Tight.Root) + 2000;
	CaptureAll(TightBudget, Tight.Work);
	for (const auto& W : Tight.Work)
	{
		TestTrue(TEXT("Cross-call output priority preserves selected output diagnostics"), Complete(W.OutputStatus));
		TestEqual(TEXT("Each call retains three outputs under input pressure"), Count(W.OutputStatus), 3);
		TestFalse(TEXT("Budget-limited manifest is explicitly incomplete"), Complete(W.ManifestStatus));
		TestEqual(TEXT("Oversize input entries never append"), Count(W.ManifestStatus), 0);
		TestEqual(TEXT("All89 omitted identities are explicit"), W.ManifestStatus->GetArrayField(TEXT("omitted_indices")).Num(), 89);
		TestFalse(TEXT("Partial prefix never qualifies rich projection"), Complete(W.RichStatus));
		TestFalse(TEXT("Partial wire manifest never attests rich selection qualification"), W.RichStatus->GetBoolField(TEXT("selection_qualified")));
	}
	TestEqual(TEXT("Incomplete manifests prevent every rich callback"), *Tight.RichCalls, 0);
	TestTrue(TEXT("Budget failure emits a bounded incomplete envelope"), TightBudget.Finish());
	TestTrue(TEXT("Whole two-material envelope within actual byte limit"), Bytes(Tight.Root) <= TightBudget.Limit);
	return true;
}
#endif
