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
