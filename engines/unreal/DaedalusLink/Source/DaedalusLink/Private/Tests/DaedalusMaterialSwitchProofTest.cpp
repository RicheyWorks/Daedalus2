// SPDX-License-Identifier: MIT
#if WITH_EDITOR && WITH_DEV_AUTOMATION_TESTS
#include "DaedalusMaterialSwitchProofPolicy.h"
#include "Misc/AutomationTest.h"

namespace
{
using namespace DaedalusMaterialSwitchProofPolicy;
FParameterProof Parameter(int32 Count, bool Value)
{
	FParameterProof Proof;
	Proof.InfoCount = Proof.GuidCount = Count;
	Proof.Matches = 1;
	Proof.bEnumerationComplete = Proof.bContextExact = Proof.bNodeGuidValid = true;
	Proof.bReturnedGuidExact = Proof.bQuerySucceeded = Proof.bDynamicKnown = true;
	Proof.bValue = Value;
	return Proof;
}
FBoolProof DirectBool(bool Value)
{
	FBoolProof Proof;
	Proof.bConnected = Proof.bTypedStaticBool = Proof.bValueKnown = true;
	Proof.bValue = Value;
	return Proof;
}
FBranch DirectBranch()
{
	FBranch Branch;
	Branch.bPresent = Branch.bTraceDirect = Branch.bOwnerExact = true;
	return Branch;
}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDaedalusMaterialSwitchParameterContext,
	"Daedalus.Material.Switch.ParameterContext", EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FDaedalusMaterialSwitchParameterContext::RunTest(const FString& Parameters)
{
	bool Value = true;
	TestFalse(TEXT("Default proof never fabricates a parameter result"), ParameterValue(FParameterProof(), Value));
	TestTrue(TEXT("Refusal leaves output unchanged"), Value);
	for (int32 Count = 1; Count <= 128; ++Count)
		for (bool Actual : {false, true})
		{
			Value = !Actual;
			TestTrue(TEXT("Every complete paired inventory1..128 permits its unique exact context"), ParameterValue(Parameter(Count, Actual), Value));
			TestEqual(TEXT("Successful false and true queries retain actual bool"), Value, Actual);
		}
	const auto Refuse = [this](const TCHAR* Label, FParameterProof Proof)
	{
		bool Output = false;
		Proof.bValue = true; // untrusted query storage must not leak into output on failure.
		TestFalse(Label, ParameterValue(Proof, Output));
		TestFalse(TEXT("Failed qualification does not overwrite output from query/default storage"), Output);
	};
	for (int32 Count : {-1, 0, 129, 256}) Refuse(TEXT("Incomplete or excessive inventory count refused"), Parameter(Count, true));
	auto Proof = Parameter(128, true);
	Proof.GuidCount = 127; Refuse(TEXT("Paired inventory counts must agree"), Proof);
	Proof = Parameter(1, true); Proof.GuidCount = 0; Refuse(TEXT("Missing GUID inventory refused"), Proof);
	Proof = Parameter(1, true); Proof.bEnumerationComplete = false; Refuse(TEXT("Partial enumeration cannot prove uniqueness"), Proof);
	for (int32 Matches : {0, 2, 128})
	{
		Proof = Parameter(128, true); Proof.Matches = Matches;
		Refuse(TEXT("Exactly one context/GUID match is required"), Proof);
	}
	Proof = Parameter(1, true); Proof.bContextExact = false; Refuse(TEXT("Wrong name/association/index/call context refused"), Proof);
	Proof = Parameter(1, true); Proof.bNodeGuidValid = false; Refuse(TEXT("Missing or zero node GUID refused"), Proof);
	Proof = Parameter(1, true); Proof.bReturnedGuidExact = false; Refuse(TEXT("Returned GUID must equal node and unique inventory match"), Proof);
	Proof = Parameter(1, true); Proof.bQuerySucceeded = false; Refuse(TEXT("Query success is independent of returned bool storage"), Proof);
	Proof = Parameter(1, true); Proof.bDynamicKnown = false; Refuse(TEXT("Unknown DynamicBranch cannot become static"), Proof);
	Proof = Parameter(1, true); Proof.bDynamic = true; Refuse(TEXT("Dynamic switch refused even with successful query"), Proof);
	Proof = Parameter(1, false); Value = true;
	TestTrue(TEXT("Successful query returning false is valid"), ParameterValue(Proof, Value));
	TestFalse(TEXT("Successful false selects false without authored default fallback"), Value);
	Proof.bQuerySucceeded = false; Value = true;
	TestFalse(TEXT("Failed query containing false is still failure"), ParameterValue(Proof, Value));
	TestTrue(TEXT("Failed false query leaves previous output unchanged"), Value);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDaedalusMaterialSwitchSelector,
	"Daedalus.Material.Switch.Selector", EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FDaedalusMaterialSwitchSelector::RunTest(const FString& Parameters)
{
	bool Value = true;
	TestFalse(TEXT("Default selector proof is unknown"), StaticValue(FBoolProof(), Value));
	TestTrue(TEXT("Unknown selector leaves output untouched"), Value);
	for (bool Actual : {false, true})
	{
		FBoolProof Disconnected;
		Disconnected.bDefaultKnown = true; Disconnected.bDefault = Actual;
		Value = !Actual;
		TestTrue(TEXT("Explicitly disconnected Value may use known typed DefaultValue"), StaticValue(Disconnected, Value));
		TestEqual(TEXT("Disconnected default uses actual bool"), Value, Actual);
		auto Direct = DirectBool(Actual);
		Direct.bDefaultKnown = true; Direct.bDefault = !Actual;
		Value = !Actual;
		TestTrue(TEXT("Direct typed StaticBool qualifies"), StaticValue(Direct, Value));
		TestEqual(TEXT("Connected direct bool wins over irrelevant default"), Value, Actual);
		auto Bound = Direct;
		Bound.bUniqueBinding = true; Bound.FunctionInputType = 8;
		Value = !Actual;
		TestTrue(TEXT("Unique FunctionInput_StaticBool8 to direct caller StaticBool qualifies"), StaticValue(Bound, Value));
		TestEqual(TEXT("Bound StaticBool preserves successful false as well as true"), Value, Actual);
	}
	const auto Refuse = [this](const TCHAR* Label, FBoolProof Proof)
	{
		bool Output = false;
		Proof.bValue = Proof.bDefault = true;
		TestFalse(Label, StaticValue(Proof, Output));
		TestFalse(TEXT("Refused connected/unknown proof never falls back or overwrites output"), Output);
	};
	FBoolProof Proof;
	Proof.bValueKnown = Proof.bTypedStaticBool = true;
	Refuse(TEXT("Disconnected but missing typed default remains unknown"), Proof);
	Proof = DirectBool(true); Proof.bDefaultKnown = true; Proof.bValueKnown = false;
	Refuse(TEXT("Connected unknown Value never uses known DefaultValue"), Proof);
	Proof = DirectBool(true); Proof.bDefaultKnown = true; Proof.bTypedStaticBool = false;
	Refuse(TEXT("Connected non-StaticBool class never uses default"), Proof);
	Proof = DirectBool(true); Proof.FunctionInputType = 8;
	Refuse(TEXT("FunctionInput_StaticBool requires unique manifest binding"), Proof);
	for (int32 InputType : {-1, 0, 2, 7, 9, 11, 12})
	{
		Proof = DirectBool(true); Proof.bUniqueBinding = true; Proof.FunctionInputType = InputType;
		Refuse(TEXT("Bound input type must be8, never Bool11 or numeric/vector types"), Proof);
	}
	Proof = DirectBool(true); Proof.FunctionInputType = 11;
	Refuse(TEXT("Bool11 never passes as a direct static bool lane"), Proof);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDaedalusMaterialSwitchTraceAndBounds,
	"Daedalus.Material.Switch.TraceAndBounds", EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FDaedalusMaterialSwitchTraceAndBounds::RunTest(const FString& Parameters)
{
	TestFalse(TEXT("Missing branches never qualify"), BothDirect(FBranch(), FBranch()));
	TestTrue(TEXT("Both exact direct traces qualify independent of chosen endpoint value"), BothDirect(DirectBranch(), DirectBranch()));
	for (int32 Side = 0; Side < 2; ++Side)
		for (int32 Defect = 0; Defect < 4; ++Defect)
		{
			auto A = DirectBranch(), B = DirectBranch();
			auto& Branch = Side == 0 ? A : B;
			if (Defect == 0) Branch.bPresent = false;
			if (Defect == 1) Branch.bTraceDirect = false;
			if (Defect == 2) Branch.bReroute = true;
			if (Defect == 3) Branch.bOwnerExact = false;
			TestFalse(TEXT("Either chosen or unchosen missing/indirect/reroute/wrong-owner trace refuses"), BothDirect(A, B));
		}
	FUsage Usage;
	TestEqual(TEXT("New material starts with zero roots"), Usage.Roots, 0);
	TestFalse(TEXT("No metadata before root admission"), Usage.TryMetadata());
	TestFalse(TEXT("No details before root admission"), Usage.TryDetail());
	TestFalse(TEXT("No parameter query before root admission"), Usage.TryQuery());
	TestFalse(TEXT("No lane edge before root admission"), Usage.TryEdge(1));
	TestTrue(TEXT("First root admitted"), Usage.TryRoot());
	for (int32 N = 0; N < 9; ++N) TestTrue(TEXT("Metadata1..9 admitted"), Usage.TryMetadata());
	TestFalse(TEXT("Metadata10 refused"), Usage.TryMetadata());
	TestEqual(TEXT("Refused metadata does not increment"), Usage.Metadata, 9);
	for (int32 N = 0; N < 3; ++N) TestTrue(TEXT("Parameter query1..3 admitted"), Usage.TryQuery());
	TestFalse(TEXT("Parameter query4 refused"), Usage.TryQuery());
	TestEqual(TEXT("Refused query does not increment"), Usage.Queries, 3);
	for (int32 RootIndex = 0; RootIndex < 3; ++RootIndex)
	{
		if (RootIndex) TestTrue(TEXT("Next bounded root admitted"), Usage.TryRoot());
		for (int32 N = 0; N < 5; ++N) TestTrue(TEXT("Detail1..5 per root admitted"), Usage.TryDetail());
		TestFalse(TEXT("Sixth detail in same root refused"), Usage.TryDetail());
		TestEqual(TEXT("Per-root detail bound retained"), Usage.RootDetails, 5);
	}
	TestFalse(TEXT("Fourth root refused"), Usage.TryRoot());
	TestFalse(TEXT("Sixteenth material detail refused"), Usage.TryDetail());
	TestEqual(TEXT("Root cap3 retained"), Usage.Roots, 3);
	TestEqual(TEXT("Material detail cap15 retained"), Usage.Details, 15);
	TestTrue(TEXT("First prospective lane edge admitted"), Usage.TryEdge(1));
	TestTrue(TEXT("Second prospective lane edge admitted"), Usage.TryEdge(2));
	for (int32 Edges : {-1, 0, 3, 4}) TestFalse(TEXT("Only prospective edge counts1..2 accepted"), Usage.TryEdge(Edges));
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDaedalusMaterialSwitchChosenLeaf,
	"Daedalus.Material.Switch.ChosenLeaf", EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FDaedalusMaterialSwitchChosenLeaf::RunTest(const FString& Parameters)
{
	const TArray<ELeaf> Types = {ELeaf::StaticBool, ELeaf::RGB, ELeaf::Scalar, ELeaf::Unsupported};
	for (const auto Actual : Types)
		for (const auto Expected : Types)
			TestEqual(TEXT("Exact typed chosen leaf only; unsupported never qualifies"),
				ChosenLeaf(Actual, Expected, true, true, true, true), Actual == Expected && Actual != ELeaf::Unsupported);
	for (const auto Kind : {ELeaf::StaticBool, ELeaf::RGB, ELeaf::Scalar})
	{
		TestFalse(TEXT("Nonprimary output refused"), ChosenLeaf(Kind, Kind, false, true, true, true));
		TestFalse(TEXT("Invalid selected output metadata refused"), ChosenLeaf(Kind, Kind, true, false, true, true));
		TestFalse(TEXT("Wrong bool/scalar/RGB mask context refused"), ChosenLeaf(Kind, Kind, true, true, false, true));
		TestFalse(TEXT("Unproven graph ownership refused"), ChosenLeaf(Kind, Kind, true, true, true, false));
	}
	TestTrue(TEXT("Both branch traces can be direct while unchosen value class is unsupported"), BothDirect(DirectBranch(), DirectBranch()));
	TestFalse(TEXT("Unsupported chosen endpoint remains refused without arbitrary evaluation"), ChosenLeaf(ELeaf::Unsupported, ELeaf::RGB, true, true, true, true));
	return true;
}
#endif

// R5 transparent-chain tests append to the existing registered translation unit.
#if WITH_EDITOR && WITH_DEV_AUTOMATION_TESTS
#include "DaedalusMaterialTransparentChainPolicy.h"

namespace
{
namespace CP = DaedalusMaterialTransparentChainPolicy;

TArray<CP::FBinding> ChainBindings(int32 Count, const FString& Prefix)
{
	TArray<CP::FBinding> Rows;
	for (int32 Index = 0; Index < Count; ++Index)
	{
		CP::FBinding Row;
		Row.Index = Index;
		Row.BindingGuid = Row.NodeGuid = FGuid(1, 2, 3, Index + 1);
		Row.NodePath = FString::Printf(TEXT("%s.Node%d"), *Prefix, Index);
		Row.bPointerValid = Row.bOwnerExact = Row.bClassExact = true;
		Rows.Add(Row);
	}
	return Rows;
}

CP::FFrame ChainFrame(const FString& Id, const FString& Parent, const FString& Function,
	const FString& ParentFunction, int32 Inputs = 0, int32 Outputs = 1)
{
	CP::FFrame Frame;
	Frame.Id = Frame.CallerPath = Id;
	Frame.Parent = Parent;
	Frame.FunctionPath = Function;
	Frame.CallerOwner = ParentFunction;
	Frame.InputsCount = Inputs; Frame.OutputsCount = Outputs;
	Frame.bFunctionExact = Frame.bCallerExact = Frame.bCachedBindingsComplete = true;
	Frame.Inputs = ChainBindings(Inputs, Function + TEXT(".Input"));
	Frame.Outputs = ChainBindings(Outputs, Function + TEXT(".Output"));
	return Frame;
}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDaedalusMaterialChainTraversal,
	"Daedalus.Material.Chain.Traversal", EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FDaedalusMaterialChainTraversal::RunTest(const FString& Parameters)
{
	CP::FTraversal Traversal;
	TestEqual(TEXT("A new lane has zero explicit steps"), Traversal.Steps, 0);
	TestEqual(TEXT("A new lane has zero visits"), Traversal.Visited.Num(), 0);
	TestFalse(TEXT("Empty frame is not an observed identity"), Traversal.TryStep(TEXT(""), TEXT("Node"), 0));
	TestFalse(TEXT("Empty node is not an observed identity"), Traversal.TryVisit(TEXT("root"), TEXT(""), 0));
	TestFalse(TEXT("Negative output is not a connection"), Traversal.TryStep(TEXT("root"), TEXT("Node"), -1));
	TestEqual(TEXT("Invalid attempts do not consume steps"), Traversal.Steps, 0);
	TestEqual(TEXT("Invalid attempts do not insert visits"), Traversal.Visited.Num(), 0);
	TestTrue(TEXT("First exact connection admitted"), Traversal.TryStep(TEXT("root"), TEXT("Node"), 0));
	TestFalse(TEXT("Repeated node/frame/output is a cycle"), Traversal.TryStep(TEXT("root"), TEXT("Node"), 0));
	TestTrue(TEXT("Cycle classified explicitly"), Traversal.Failure == CP::EStepFailure::Cycle);
	TestEqual(TEXT("Cycle does not consume another step"), Traversal.Steps, 1);
	TestEqual(TEXT("Cycle does not insert another visit"), Traversal.Visited.Num(), 1);
	TestTrue(TEXT("Same node and output in distinct frame is distinct"), Traversal.TryStep(TEXT("child"), TEXT("Node"), 0));
	TestTrue(TEXT("Same frame and node with distinct output is distinct"), Traversal.TryStep(TEXT("root"), TEXT("Node"), 1));

	CP::FTraversal Named;
	for (int32 Index = 0; Index < 32; ++Index)
	{
		TestTrue(TEXT("Explicit named usage step1..32 admitted"),
			Named.TryStep(TEXT("root"), FString::Printf(TEXT("Usage%d"), Index), 0));
		TestTrue(TEXT("Implicit declaration is cycle-marked without an extra step"),
			Named.TryVisit(TEXT("root"), FString::Printf(TEXT("Declaration%d"), Index), 0));
	}
	TestEqual(TEXT("32 named usage records are32 explicit steps"), Named.Steps, 32);
	TestEqual(TEXT("32 declaration visits fit separate64-visit bound"), Named.Visited.Num(), 64);
	TestFalse(TEXT("Explicit step33 is refused"), Named.TryStep(TEXT("root"), TEXT("ExtraUsage"), 0));
	TestTrue(TEXT("Explicit exhaustion is classified"), Named.Failure == CP::EStepFailure::StepLimit);
	TestFalse(TEXT("Implicit visit65 is refused"), Named.TryVisit(TEXT("root"), TEXT("ExtraDeclaration"), 0));
	TestTrue(TEXT("Visit exhaustion is classified separately"), Named.Failure == CP::EStepFailure::VisitLimit);
	TestFalse(TEXT("Previously marked declaration cannot be revisited"), Named.TryVisit(TEXT("root"), TEXT("Declaration0"), 0));
	TestTrue(TEXT("A repeated declaration is a cycle even at visit cap"), Named.Failure == CP::EStepFailure::Cycle);
	TestEqual(TEXT("All refused attempts retain step cap"), Named.Steps, 32);
	TestEqual(TEXT("All refused attempts retain visit cap"), Named.Visited.Num(), 64);
	CP::FTraversal DeclarationCycle;
	TestTrue(TEXT("Usage starts another lane"), DeclarationCycle.TryStep(TEXT("root"), TEXT("Usage"), 0));
	TestTrue(TEXT("Cached declaration marked"), DeclarationCycle.TryVisit(TEXT("root"), TEXT("Declaration"), 0));
	TestFalse(TEXT("Following declaration back to usage is a cycle"), DeclarationCycle.TryStep(TEXT("root"), TEXT("Usage"), 0));
	TestEqual(TEXT("Named cycle consumes only its first emitted step"), DeclarationCycle.Steps, 1);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDaedalusMaterialChainFrames,
	"Daedalus.Material.Chain.Frames", EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FDaedalusMaterialChainFrames::RunTest(const FString& Parameters)
{
	const FString Root = TEXT("/Game/Chain/F0.F0");
	CP::FFrames Frames(Root);
	TestEqual(TEXT("Implicit root depth is0"), Frames.Depth(TEXT("root")), 0);
	TestEqual(TEXT("Unknown frame has no inferred depth"), Frames.Depth(TEXT("missing")), -1);
	FString Parent = TEXT("root"), ParentFunction = Root;
	for (int32 Depth = 1; Depth <= 4; ++Depth)
	{
		const FString Id = FString::Printf(TEXT("%s.Call%d"), *ParentFunction, Depth);
		const FString Function = FString::Printf(TEXT("/Game/Chain/F%d.F%d"), Depth, Depth);
		const auto Frame = ChainFrame(Id, Parent, Function, ParentFunction);
		TestTrue(TEXT("Parent-before-child frame1..4 admitted with zero input function"), Frames.TryAdd(Frame));
		TestEqual(TEXT("Exact nested depth retained"), Frames.Depth(Id), Depth);
		const auto* Found = Frames.Find(Id);
		TestNotNull(TEXT("Admitted exact caller ID resolves"), Found);
		if (Found) TestEqual(TEXT("Zero-input function remains factual"), Found->InputsCount, 0);
		Parent = Id; ParentFunction = Function;
	}
	TestFalse(TEXT("Fifth frame/depth5 refused"), Frames.TryAdd(ChainFrame(ParentFunction + TEXT(".Call5"), Parent,
		TEXT("/Game/Chain/F5.F5"), ParentFunction)));
	TestEqual(TEXT("Refused fifth frame does not alter retained four"), Frames.Items.Num(), 4);
	TestEqual(TEXT("No fifth frame was silently registered"), Frames.Depth(ParentFunction + TEXT(".Call5")), -1);

	const auto Base = ChainFrame(Root + TEXT(".Call1"), TEXT("root"), TEXT("/Game/Chain/F1.F1"), Root);
	const auto Refuse = [this, &Root](const TCHAR* Label, CP::FFrame Frame)
	{
		CP::FFrames Candidate(Root);
		TestFalse(Label, Candidate.TryAdd(Frame));
		TestEqual(TEXT("Refused frame leaves registry empty"), Candidate.Items.Num(), 0);
	};
	auto Frame = Base; Frame.Id = TEXT(""); Refuse(TEXT("Empty child ID refused"), Frame);
	Frame = Base; Frame.Id = Frame.CallerPath = TEXT("root"); Refuse(TEXT("Root ID cannot be shadowed"), Frame);
	Frame = Base; Frame.Id = Frame.CallerPath = TEXT("material"); Refuse(TEXT("Material ID cannot be shadowed"), Frame);
	Frame = Base; Frame.CallerPath += TEXT("Other"); Refuse(TEXT("Child ID must equal exact caller path"), Frame);
	Frame = Base; Frame.Parent = TEXT("missing"); Refuse(TEXT("Unknown or later parent refused"), Frame);
	Frame = Base; Frame.Parent = Frame.Id; Refuse(TEXT("Self parent refused"), Frame);
	Frame = Base; Frame.CallerOwner += TEXT("Wrong"); Refuse(TEXT("Caller must belong to exact parent function"), Frame);
	Frame = Base; Frame.FunctionPath = Root; Refuse(TEXT("Root function recursion refused"), Frame);
	Frame = Base; Frame.FunctionPath.Empty(); Refuse(TEXT("Unknown function path refused"), Frame);
	Frame = Base; Frame.bFunctionExact = false; Refuse(TEXT("Function instances or unknown function classes refused"), Frame);
	Frame = Base; Frame.bCallerExact = false; Refuse(TEXT("Unknown caller class refused"), Frame);
	Frame = Base; Frame.bCachedBindingsComplete = false; Refuse(TEXT("Partial binding manifests refuse entire frame"), Frame);
	Frame = Base; Frame.InputsCount = 1; Refuse(TEXT("Missing counted input manifest refused"), Frame);
	Frame = Base; Frame.OutputsCount = 0; Refuse(TEXT("Extra output manifest row refused"), Frame);
	CP::FFrames MissingRoot(TEXT(""));
	TestFalse(TEXT("Absent exact root function cannot admit frames"), MissingRoot.TryAdd(Base));
	CP::FFrames Ancestry(Root);
	TestTrue(TEXT("First ancestor admitted"), Ancestry.TryAdd(Base));
	TestFalse(TEXT("Duplicate child ID refused, caller may reuse Find instead"), Ancestry.TryAdd(Base));
	TestFalse(TEXT("Nested repeated function ancestry refused"), Ancestry.TryAdd(ChainFrame(
		Base.FunctionPath + TEXT(".Recursive"), Base.Id, Base.FunctionPath, Base.FunctionPath)));
	TestTrue(TEXT("Independent sibling may reference same function without recursion"), Ancestry.TryAdd(ChainFrame(
		Root + TEXT(".OtherCall"), TEXT("root"), Base.FunctionPath, Root)));
	CP::FFrames Siblings(Root);
	for (int32 Index = 0; Index < 4; ++Index)
		TestTrue(TEXT("Distinct shallow frames1..4 admitted"), Siblings.TryAdd(ChainFrame(
			Root + FString::Printf(TEXT(".Call%d"), Index), TEXT("root"), Base.FunctionPath, Root)));
	TestFalse(TEXT("Fifth distinct shallow frame also refused"), Siblings.TryAdd(ChainFrame(
		Root + TEXT(".Fifth"), TEXT("root"), Base.FunctionPath, Root)));
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDaedalusMaterialChainBindings,
	"Daedalus.Material.Chain.Bindings", EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FDaedalusMaterialChainBindings::RunTest(const FString& Parameters)
{
	for (int32 Count : {0, 1, 127, 128})
		TestTrue(TEXT("Complete input manifests including zero and128 qualify"), CP::ValidBindings(ChainBindings(Count, TEXT("Input")), Count, 128));
	for (int32 Count : {0, 1, 15, 16})
		TestTrue(TEXT("Complete output manifests including zero and16 qualify independently"), CP::ValidBindings(ChainBindings(Count, TEXT("Output")), Count, 16));
	TestFalse(TEXT("Input129 refused"), CP::ValidBindings(ChainBindings(129, TEXT("Input")), 129, 128));
	TestFalse(TEXT("Output17 refused"), CP::ValidBindings(ChainBindings(17, TEXT("Output")), 17, 16));
	TestFalse(TEXT("Negative count refused"), CP::ValidBindings({}, -1, 128));
	TestFalse(TEXT("Unknown cap cannot weaken closed manifest bounds"), CP::ValidBindings({}, 0, 129));
	TestFalse(TEXT("Unpaired missing counted row refused"), CP::ValidBindings(ChainBindings(1, TEXT("Input")), 2, 128));
	TestFalse(TEXT("Unpaired extra row refused"), CP::ValidBindings(ChainBindings(2, TEXT("Input")), 1, 128));
	for (int32 Defect = 0; Defect < 8; ++Defect)
	{
		auto Rows = ChainBindings(2, TEXT("Input"));
		if (Defect == 0) Rows[1].Index = 0;
		if (Defect == 1) Rows[0].Index = 1;
		if (Defect == 2) Rows[1].BindingGuid = Rows[1].NodeGuid = Rows[0].NodeGuid;
		if (Defect == 3) Rows[1].NodePath = Rows[0].NodePath;
		if (Defect == 4) Rows[1].BindingGuid = FGuid(9, 9, 9, 9);
		if (Defect == 5) Rows[1].BindingGuid = Rows[1].NodeGuid = FGuid();
		if (Defect == 6) Rows[1].NodePath.Empty();
		if (Defect == 7) Rows[1].bPointerValid = false;
		TestFalse(TEXT("Duplicate index/GUID/path, unpaired/zero GUID or invalid pointer refused"), CP::ValidBindings(Rows, 2, 128));
	}
	for (int32 Defect = 0; Defect < 2; ++Defect)
	{
		auto Rows = ChainBindings(1, TEXT("Input"));
		if (Defect == 0) Rows[0].bOwnerExact = false;
		else Rows[0].bClassExact = false;
		TestFalse(TEXT("Binding requires exact cached node owner/class"), CP::ValidBindings(Rows, 1, 128));
	}
	for (const auto Lane : {CP::ELane::Scalar, CP::ELane::Vector3, CP::ELane::StaticBool})
		for (int32 Type : {-1, 0, 1, 2, 3, 8, 11, 12})
		{
			const bool Expected = (Lane == CP::ELane::Scalar && Type == 0)
				|| (Lane == CP::ELane::Vector3 && Type == 2) || (Lane == CP::ELane::StaticBool && Type == 8);
			TestEqual(TEXT("Only exact Scalar0/Vector3=2/StaticBool8 qualifies; never Bool11"), CP::InputType(Lane, Type), Expected);
			TestEqual(TEXT("Exact typed caller binding retains type oracle"), CP::InputBinding(Lane, Type, true, true, true), Expected);
			TestFalse(TEXT("Input pointer mismatch refused"), CP::InputBinding(Lane, Type, false, true, true));
			TestFalse(TEXT("Nonunique manifest row refused"), CP::InputBinding(Lane, Type, true, false, true));
			TestFalse(TEXT("Wrong input owner refused"), CP::InputBinding(Lane, Type, true, true, false));
		}
	for (const auto Route : {CP::ERoute::Reroute, CP::ERoute::NamedDeclaration, CP::ERoute::NamedUsage, CP::ERoute::FunctionInput})
	{
		TestTrue(TEXT("Known zero-output transparent route qualifies"), CP::RouteAllowed(Route, true, true, true));
		TestFalse(TEXT("Known non-function-output route needs output0"), CP::RouteAllowed(Route, false, true, true));
		TestFalse(TEXT("Known route needs exact cached input pointer"), CP::RouteAllowed(Route, true, false, true));
		TestFalse(TEXT("Known route needs exact graph owner"), CP::RouteAllowed(Route, true, true, false));
	}
	TestTrue(TEXT("Function output may select nonzero manifest-validated index"), CP::RouteAllowed(CP::ERoute::FunctionOutput, false, true, true));
	TestFalse(TEXT("Unknown reroute/subclass is never transparently traversed"), CP::RouteAllowed(CP::ERoute::Unsupported, true, true, true));
	const FGuid Guid(1, 2, 3, 4), Other(5, 6, 7, 8);
	TestTrue(TEXT("Exact valid cached named link qualifies"), CP::NamedLink(Guid, Guid, true, true, true));
	TestFalse(TEXT("Named declaration GUID mismatch refused"), CP::NamedLink(Guid, Other, true, true, true));
	TestFalse(TEXT("Zero paired named GUIDs refused"), CP::NamedLink(FGuid(), FGuid(), true, true, true));
	TestFalse(TEXT("Named cached declaration pointer mismatch refused"), CP::NamedLink(Guid, Guid, false, true, true));
	TestFalse(TEXT("Named declaration validity is mandatory"), CP::NamedLink(Guid, Guid, true, false, true));
	TestFalse(TEXT("Named declaration must remain in same graph"), CP::NamedLink(Guid, Guid, true, true, false));
	bool Value = true;
	auto ParameterProof = Parameter(1, false);
	TestTrue(TEXT("Existing parameter helper preserves successful false query"), ParameterValue(ParameterProof, Value));
	TestFalse(TEXT("Successful false is an actual selector result"), Value);
	ParameterProof.bQuerySucceeded = false; Value = true;
	TestFalse(TEXT("Failed false query cannot promote an authored default"), ParameterValue(ParameterProof, Value));
	TestTrue(TEXT("Failed query leaves output unknown to caller"), Value);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDaedalusMaterialChainMasks,
	"Daedalus.Material.Chain.Masks", EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FDaedalusMaterialChainMasks::RunTest(const FString& Parameters)
{
	const CP::FMask Zero, RGB{1, 1, 1, 1, 0}, Red{1, 1, 0, 0, 0}, Alpha{1, 0, 0, 0, 1};
	for (const auto Lane : {CP::ELane::Scalar, CP::ELane::Vector3, CP::ELane::StaticBool})
	{
		TestTrue(TEXT("Explicit all-zero mask qualifies every lane"), CP::LaneMask(Lane, Zero));
		TestEqual(TEXT("Full RGB qualifies Vector3 only"), CP::LaneMask(Lane, RGB), Lane == CP::ELane::Vector3);
		TestFalse(TEXT("Channel-only mask remains held"), CP::LaneMask(Lane, Red));
		TestFalse(TEXT("Alpha mask remains held"), CP::LaneMask(Lane, Alpha));
		TestFalse(TEXT("Mask0 with nonzero normalized channels is not explicit unmasked context"), CP::LaneMask(Lane, {0, 1, 1, 1, 0}));
	}
	CP::FMask Effective = Red;
	TestTrue(TEXT("Zero raw Mask selects valid cached output mask"), CP::EffectiveMasks(Zero, RGB, true, Effective));
	TestTrue(TEXT("Output fallback is the exact full RGB mask"), CP::SameMask(Effective, RGB));
	TestFalse(TEXT("A falsified reported effective zero mask cannot equal fallback"), CP::SameMask(Effective, Zero));
	TestTrue(TEXT("Nonzero raw Mask selects raw input instead of output"), CP::EffectiveMasks(Red, RGB, true, Effective));
	TestTrue(TEXT("Raw channel-only mask remains actual, not broadened to RGB"), CP::SameMask(Effective, Red));
	TestFalse(TEXT("Raw channel-only selection remains inadmissible"), CP::LaneMask(CP::ELane::Vector3, Effective));
	TestTrue(TEXT("Full raw RGB may ignore a valid different output mask"), CP::EffectiveMasks(RGB, Alpha, true, Effective));
	TestTrue(TEXT("Full raw RGB retained"), CP::SameMask(Effective, RGB));
	TestFalse(TEXT("Invalid selected output never qualifies even when raw Mask is set"), CP::EffectiveMasks(RGB, Zero, false, Effective));
	TestTrue(TEXT("Output-invalid refusal leaves prior observation untouched"), CP::SameMask(Effective, RGB));
	for (int32 Field = 0; Field < 5; ++Field)
		for (int32 Invalid : {-1, 2})
		{
			CP::FMask Bad = Zero;
			if (Field == 0) Bad.Mask = Invalid;
			if (Field == 1) Bad.R = Invalid;
			if (Field == 2) Bad.G = Invalid;
			if (Field == 3) Bad.B = Invalid;
			if (Field == 4) Bad.A = Invalid;
			TestFalse(TEXT("Mask predicates require normalized explicit bits"), CP::ValidMask(Bad));
			TestFalse(TEXT("Invalid raw mask refuses before fallback"), CP::EffectiveMasks(Bad, Zero, true, Effective));
			TestFalse(TEXT("Invalid cached output mask refuses even with raw Mask set"), CP::EffectiveMasks(RGB, Bad, true, Effective));
			TestTrue(TEXT("Invalid mask refusal preserves result"), CP::SameMask(Effective, RGB));
		}
	return true;
}
#endif
