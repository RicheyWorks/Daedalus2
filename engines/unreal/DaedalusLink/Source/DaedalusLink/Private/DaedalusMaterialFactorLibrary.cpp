// SPDX-License-Identifier: MIT
#include "DaedalusMaterialFactorLibrary.h"

#if WITH_EDITOR
#include "Dom/JsonObject.h"
#include "DaedalusMaterialCachedDiagnostic.h"
#include "DaedalusMaterialSwitchProofPolicy.h"
#include "Editor.h"
#include "Engine/World.h"
#include "FileHelpers.h"
#include "MaterialDomain.h"
#include "Materials/Material.h"
#include "Materials/MaterialExpressionConstant.h"
#include "Materials/MaterialExpressionConstant3Vector.h"
#include "Materials/MaterialExpressionScalarParameter.h"
#include "Materials/MaterialExpressionVectorParameter.h"
#include "Materials/MaterialExpressionMaterialFunctionCall.h"
#include "Materials/MaterialExpressionFunctionInput.h"
#include "Materials/MaterialExpressionFunctionOutput.h"
#include "Materials/MaterialFunctionInterface.h"
#include "Materials/MaterialInterface.h"
#include "Materials/MaterialParameters.h"
#include "Materials/MaterialExpressionStaticSwitchParameter.h"
#include "Materials/MaterialExpressionStaticSwitch.h"
#include "Materials/MaterialExpressionStaticBool.h"
#include "Materials/MaterialExpressionRerouteBase.h"
#include "Misc/PackageName.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonWriter.h"
#include "UObject/Package.h"
#include "UObject/UObjectGlobals.h"

namespace DaedalusMaterialFactors
{
using FJson = TSharedRef<FJsonObject>;
using FValues = TArray<TSharedPtr<FJsonValue>>;

static FValues DirtyPackages()
{
	TArray<UPackage*> Packages;
	UEditorLoadingAndSavingUtils::GetDirtyMapPackages(Packages);
	UEditorLoadingAndSavingUtils::GetDirtyContentPackages(Packages);
	TArray<FString> Names;
	for (const UPackage* Package : Packages) if (Package) Names.AddUnique(Package->GetName());
	Names.Sort();
	FValues Values;
	for (const FString& Name : Names) Values.Add(MakeShared<FJsonValueString>(Name));
	return Values;
}

static void Masks(FJson Json, const FString& Prefix, int32 M, int32 R, int32 G, int32 B, int32 A)
{
	Json->SetNumberField(Prefix + TEXT("mask"), M);
	Json->SetNumberField(Prefix + TEXT("mask_r"), R);
	Json->SetNumberField(Prefix + TEXT("mask_g"), G);
	Json->SetNumberField(Prefix + TEXT("mask_b"), B);
	Json->SetNumberField(Prefix + TEXT("mask_a"), A);
}

static void UnknownMasks(FJson Json, const FString& Prefix)
{
	for (const TCHAR* Field : {TEXT("mask"), TEXT("mask_r"), TEXT("mask_g"), TEXT("mask_b"), TEXT("mask_a")})
		Json->SetField(Prefix + Field, MakeShared<FJsonValueNull>());
}

static bool KnownClass(const UMaterialExpression* Expression)
{
	return Expression && (Expression->GetClass() == UMaterialExpressionConstant::StaticClass()
		|| Expression->GetClass() == UMaterialExpressionConstant3Vector::StaticClass()
		|| Expression->GetClass() == UMaterialExpressionScalarParameter::StaticClass()
		|| Expression->GetClass() == UMaterialExpressionVectorParameter::StaticClass());
}

static bool FlatUniqueParameter(const UMaterial* Material, const UMaterialExpressionParameter* Parameter)
{
	const auto Expressions = Material->GetExpressions();
	if (Expressions.Num() > 4096 || Parameter->ParameterName.IsNone()) return false;
	int32 Matches = 0;
	int32 DirectOccurrences = 0;
	for (const auto& Entry : Expressions)
	{
		const UMaterialExpression* Expression = Entry.Get();
		// Functions/layers and unknown flat nodes leave effective defaults unproved.
		if (!IsValid(Expression) || !KnownClass(Expression)) return false;
		DirectOccurrences += Expression == Parameter ? 1 : 0;
		const auto* Other = Cast<UMaterialExpressionParameter>(Expression);
		if (Other && Other->ParameterName == Parameter->ParameterName) ++Matches;
	}
	return DirectOccurrences == 1 && Matches == 1;
}

// Diagnostic only. Public cached fields are not a material evaluator. In particular,
// never refresh transient function pointers or ask unknown nodes for virtual outputs.
static bool CachedReadable(const UObject* Object)
{
	return IsValid(Object) && !Object->HasAnyFlags(RF_NeedLoad | RF_NeedPostLoad);
}

template <typename T>
static const T* CachedResolved(const TObjectPtr<T>& Reference, const FString& Where, FValues& Errors)
{
	if (!Reference.IsResolved())
	{
		Errors.Add(MakeShared<FJsonValueString>(Where + TEXT(": unresolved object handle; not resolved or loaded")));
		return nullptr;
	}
	const T* Object = Reference.Get();
	if (!CachedReadable(Object))
	{
		Errors.Add(MakeShared<FJsonValueString>(Where + TEXT(": missing, invalid or incomplete cached object; not refreshed")));
		return nullptr;
	}
	return Object;
}

static TSharedPtr<FJsonValue> CachedIdentity(const UObject* Object)
{
	if (!CachedReadable(Object)) return MakeShared<FJsonValueNull>();
	FJson Value = MakeShared<FJsonObject>();
	Value->SetStringField(TEXT("path"), Object->GetPathName());
	Value->SetStringField(TEXT("class"), Object->GetClass()->GetPathName());
	if (Object->GetOuter()) Value->SetStringField(TEXT("owner"), Object->GetOuter()->GetPathName());
	else Value->SetField(TEXT("owner"), MakeShared<FJsonValueNull>());
	return MakeShared<FJsonValueObject>(Value);
}

static FJson CachedGuid(const FGuid& Guid)
{
	FJson Value = MakeShared<FJsonObject>();
	Value->SetStringField(TEXT("hex128"), Guid.ToString(EGuidFormats::Digits).ToLower());
	Value->SetBoolField(TEXT("valid"), Guid.IsValid());
	FJson Limbs = MakeShared<FJsonObject>();
	Limbs->SetNumberField(TEXT("A"), static_cast<double>(Guid.A));
	Limbs->SetNumberField(TEXT("B"), static_cast<double>(Guid.B));
	Limbs->SetNumberField(TEXT("C"), static_cast<double>(Guid.C));
	Limbs->SetNumberField(TEXT("D"), static_cast<double>(Guid.D));
	Value->SetObjectField(TEXT("raw_uint32_limbs"), Limbs);
	return Value;
}

static FJson CachedMasks(int32 M, int32 R, int32 G, int32 B, int32 A, bool bNormalize = false)
{
	FJson Value = MakeShared<FJsonObject>();
	Value->SetNumberField(TEXT("Mask"), bNormalize ? !!M : M);
	Value->SetNumberField(TEXT("MaskR"), bNormalize ? !!R : R);
	Value->SetNumberField(TEXT("MaskG"), bNormalize ? !!G : G);
	Value->SetNumberField(TEXT("MaskB"), bNormalize ? !!B : B);
	Value->SetNumberField(TEXT("MaskA"), bNormalize ? !!A : A);
	return Value;
}

static TSharedPtr<FJsonValue> CachedVector(float X, float Y, float Z, float W,
	const FString& Where, FValues& Errors)
{
	if (!FMath::IsFinite(X) || !FMath::IsFinite(Y) || !FMath::IsFinite(Z) || !FMath::IsFinite(W))
	{
		Errors.Add(MakeShared<FJsonValueString>(Where + TEXT(": nonfinite typed vector")));
		return MakeShared<FJsonValueNull>();
	}
	FValues Values;
	for (float V : {X, Y, Z, W}) Values.Add(MakeShared<FJsonValueNumber>(V));
	return MakeShared<FJsonValueArray>(Values);
}

static FJson CachedDirectValue(const UMaterialExpression* Expression, FValues& Errors)
{
	FJson Value = MakeShared<FJsonObject>();
	Value->SetStringField(TEXT("state"), CachedReadable(Expression) ? TEXT("unsupported_expression_class") : TEXT("unconnected_or_unavailable"));
	Value->SetField(TEXT("raw_value"), MakeShared<FJsonValueNull>());
	if (!CachedReadable(Expression)) return Value;
	Value->SetStringField(TEXT("class"), Expression->GetClass()->GetPathName());
	if (!KnownClass(Expression)) return Value;
	const bool bVector = Expression->GetClass() == UMaterialExpressionConstant3Vector::StaticClass()
		|| Expression->GetClass() == UMaterialExpressionVectorParameter::StaticClass();
	const bool bParameter = Expression->GetClass() == UMaterialExpressionVectorParameter::StaticClass()
		|| Expression->GetClass() == UMaterialExpressionScalarParameter::StaticClass();
	Value->SetStringField(TEXT("state"), bParameter ? TEXT("authored_parameter_default_only") : TEXT("typed_constant"));
	Value->SetStringField(TEXT("raw_value_type"), bVector ? TEXT("FLinearColor") : TEXT("float"));
	if (bParameter)
	{
		const auto* Parameter = CastChecked<UMaterialExpressionParameter>(Expression);
		Value->SetStringField(TEXT("parameter_name"), Parameter->ParameterName.ToString());
		Value->SetBoolField(TEXT("effective_binding_qualified"), false);
	}
	if (bVector)
	{
		FLinearColor Color = FLinearColor::Black;
		if (bParameter)
		{
			const auto* Parameter = CastChecked<UMaterialExpressionVectorParameter>(Expression);
			Color = Parameter->DefaultValue;
			Value->SetBoolField(TEXT("uses_custom_primitive_data"), Parameter->bUseCustomPrimitiveData);
			Value->SetNumberField(TEXT("primitive_data_index"), Parameter->PrimitiveDataIndex);
		}
		else Color = CastChecked<UMaterialExpressionConstant3Vector>(Expression)->Constant;
		Value->SetField(TEXT("raw_value"), CachedVector(Color.R, Color.G, Color.B, Color.A, Expression->GetPathName(), Errors));
	}
	else
	{
		float Scalar = 0;
		if (bParameter)
		{
			const auto* Parameter = CastChecked<UMaterialExpressionScalarParameter>(Expression);
			Scalar = Parameter->DefaultValue;
			Value->SetBoolField(TEXT("uses_custom_primitive_data"), Parameter->bUseCustomPrimitiveData);
			Value->SetNumberField(TEXT("primitive_data_index"), Parameter->PrimitiveDataIndex);
		}
		else Scalar = CastChecked<UMaterialExpressionConstant>(Expression)->R;
		if (FMath::IsFinite(Scalar)) Value->SetNumberField(TEXT("raw_value"), Scalar);
		else Errors.Add(MakeShared<FJsonValueString>(Expression->GetPathName() + TEXT(": nonfinite typed scalar")));
	}
	return Value;
}

static FJson CachedConnection(const FExpressionInput& Input, FValues& Errors)
{
	FJson Value = MakeShared<FJsonObject>();
	const UMaterialExpression* Expression = Input.Expression;
	Value->SetField(TEXT("expression"), CachedIdentity(Expression));
	Value->SetBoolField(TEXT("expression_present"), Expression != nullptr);
	Value->SetNumberField(TEXT("output_index"), Input.OutputIndex);
	Value->SetObjectField(TEXT("raw_masks"), CachedMasks(Input.Mask, Input.MaskR, Input.MaskG, Input.MaskB, Input.MaskA));
	FJson Effective = CachedMasks(Input.Mask, Input.MaskR, Input.MaskG, Input.MaskB, Input.MaskA, true);
	Value->SetField(TEXT("selected_cached_output"), MakeShared<FJsonValueNull>());
	Value->SetField(TEXT("selected_cached_index_valid"), MakeShared<FJsonValueNull>());
	Value->SetStringField(TEXT("selected_metadata_source"), TEXT("public cached Outputs only; virtual GetOutputs not invoked"));
	if (CachedReadable(Expression))
	{
		const auto& Outputs = Expression->Outputs;
		Value->SetNumberField(TEXT("cached_output_count"), Outputs.Num());
		const bool bValid = Outputs.Num() <= 64 && Outputs.IsValidIndex(Input.OutputIndex);
		Value->SetBoolField(TEXT("selected_cached_index_valid"), bValid);
		if (Outputs.Num() > 64) Errors.Add(MakeShared<FJsonValueString>(Expression->GetPathName() + TEXT(": cached outputs exceed 64; not traversed")));
		if (bValid)
		{
			const FExpressionOutput& Output = Outputs[Input.OutputIndex];
			FJson Selected = MakeShared<FJsonObject>();
			Selected->SetStringField(TEXT("name"), Output.OutputName.ToString());
			Selected->SetObjectField(TEXT("masks"), CachedMasks(Output.Mask, Output.MaskR, Output.MaskG, Output.MaskB, Output.MaskA));
			Value->SetObjectField(TEXT("selected_cached_output"), Selected);
			if (!Input.Mask) Effective = CachedMasks(Output.Mask, Output.MaskR, Output.MaskG, Output.MaskB, Output.MaskA, true);
		}
	}
	else if (Expression) Errors.Add(MakeShared<FJsonValueString>(TEXT("Non-null invalid or incomplete cached expression; not dereferenced")));
	Value->SetObjectField(TEXT("effective_masks"), Effective);
	Value->SetObjectField(TEXT("direct_value"), CachedDirectValue(Expression, Errors));
	return Value;
}

static FJson CachedRichInput(const UMaterialExpressionMaterialFunctionCall* Call, int32 Index)
{
 FJson Entry = MakeShared<FJsonObject>(); FValues Errors;
 Entry->SetNumberField(TEXT("index"), Index);
 if (!Call->FunctionInputs.IsValidIndex(Index))
 {
  Entry->SetBoolField(TEXT("capture_complete"), false); return Entry;
 }
 const auto& Binding = Call->FunctionInputs[Index];
 const auto* Node = CachedResolved(Binding.ExpressionInput, Call->GetPathName() + TEXT(".rich_input"), Errors);
 Entry->SetObjectField(TEXT("expression_input_id"), CachedGuid(Binding.ExpressionInputId));
 Entry->SetField(TEXT("expression_input"), CachedIdentity(Node));
 Entry->SetObjectField(TEXT("caller_input"), CachedConnection(Binding.Input, Errors));
 const bool Ready = Node && Node->GetClass() == UMaterialExpressionFunctionInput::StaticClass();
 if (Ready)
 {
  FJson N = MakeShared<FJsonObject>();
  N->SetObjectField(TEXT("id"), CachedGuid(Node->Id));
  N->SetStringField(TEXT("input_name"), Node->InputName.ToString());
  N->SetNumberField(TEXT("input_type"), static_cast<int32>(Node->InputType.GetValue()));
  N->SetBoolField(TEXT("use_preview_value_as_default"), Node->bUsePreviewValueAsDefault);
  N->SetStringField(TEXT("preview_value_type"), TEXT("FVector4f"));
  const auto& V = Node->PreviewValue;
  N->SetField(TEXT("preview_value"), CachedVector(V.X, V.Y, V.Z, V.W, Node->GetPathName(), Errors));
  N->SetObjectField(TEXT("preview"), CachedConnection(Node->Preview, Errors));
  Entry->SetObjectField(TEXT("node"), N);
 }
 else Entry->SetField(TEXT("node"), MakeShared<FJsonValueNull>());
 Entry->SetBoolField(TEXT("capture_complete"), Ready && Errors.IsEmpty() && Binding.ExpressionInputId.IsValid() && Binding.ExpressionInputId == Node->Id);
 Entry->SetArrayField(TEXT("field_errors"), Errors);
 return Entry;
}

static FJson CachedFunctionFacts(UMaterial* Material, UMaterialEditorOnlyData* Data,
 const TArray<FString>& DiagnosticPath, TArray<DaedalusMaterialCachedDiagnostic::FProjection>& Work)
{
 namespace CD = DaedalusMaterialCachedDiagnostic;
 FJson Value = MakeShared<FJsonObject>(); FValues Errors, Calls;
 Value->SetStringField(TEXT("schema"), TEXT("daedalus.material-cached-function-facts.v3"));
 Value->SetField(TEXT("material"), CachedIdentity(Material));
 Value->SetBoolField(TEXT("evaluation_performed"), false);
 Value->SetBoolField(TEXT("admission_changed"), false);
 Value->SetNumberField(TEXT("explicit_load_requests"), 0);
 Value->SetNumberField(TEXT("cache_refreshes"), 0);
 Value->SetNumberField(TEXT("virtual_getoutputs_calls"), 0);
 Value->SetStringField(TEXT("state"), TEXT("partial"));
 FJson Inputs = MakeShared<FJsonObject>();
 TMap<UMaterialExpressionMaterialFunctionCall*, TSet<int32>> Selected;
 const auto Add = [&](const TCHAR* Name, EMaterialProperty Property, const FExpressionInput* Typed, bool UseConstant)
 {
  const FExpressionInput* Current = Material->GetExpressionInputForProperty(Property);
  FJson Fact = MakeShared<FJsonObject>();
  const bool Same = Current && Current == Typed;
  Fact->SetBoolField(TEXT("current_input_pointer_equal"), Same);
  Fact->SetBoolField(TEXT("uses_input_constant"), UseConstant);
  if (Same)
  {
   Fact->SetObjectField(TEXT("connection"), CachedConnection(*Current, Errors));
   auto* Expression = Current->Expression;
   if (CachedReadable(Expression) && Expression->GetClass() == UMaterialExpressionMaterialFunctionCall::StaticClass() && Expression->GetOuter() == Material)
    Selected.FindOrAdd(CastChecked<UMaterialExpressionMaterialFunctionCall>(Expression)).Add(Current->OutputIndex);
  }
  else Errors.Add(MakeShared<FJsonValueString>(FString(Name) + TEXT(": current/typed input pointer mismatch")));
  Inputs->SetObjectField(Name, Fact);
 };
 if (Data)
 {
  Add(TEXT("base_color"), MP_BaseColor, &Data->BaseColor, Data->BaseColor.UseConstant);
  Add(TEXT("metallic"), MP_Metallic, &Data->Metallic, Data->Metallic.UseConstant);
  Add(TEXT("roughness"), MP_Roughness, &Data->Roughness, Data->Roughness.UseConstant);
 }
 else Errors.Add(MakeShared<FJsonValueString>(TEXT("Current editor-only data unavailable")));
 Value->SetObjectField(TEXT("current_typed_inputs"), Inputs);
 if (Selected.Num() > 1) Errors.Add(MakeShared<FJsonValueString>(TEXT("More than one current function call; not traversed")));
 else for (const auto& Item : Selected)
 {
  const auto* Call = Item.Key;
  CD::FProjection P;
  P.InputCount = Call->FunctionInputs.Num(); P.OutputCount = Call->FunctionOutputs.Num();
  P.Selected = Item.Value.Array(); P.Selected.Sort();
  P.Path = DiagnosticPath; P.Path.Append({TEXT("calls"), TEXT("0")});
  P.Call->SetField(TEXT("caller"), CachedIdentity(Call));
  P.Call->SetField(TEXT("owning_material"), CachedIdentity(Material));
  P.Call->SetField(TEXT("material_function"), CachedIdentity(CachedResolved(Call->MaterialFunction, Call->GetPathName() + TEXT(".MaterialFunction"), Errors)));
  P.Call->SetNumberField(TEXT("function_input_count"), P.InputCount);
  P.Call->SetNumberField(TEXT("function_output_count"), P.OutputCount);
  // Output capture is independent of an oversized/missing input manifest.
  if (P.OutputCount <= CD::MaxOutputs && P.Selected.Num() <= CD::MaxSelected)
   for (int32 Index : P.Selected)
   {
    if (!Call->FunctionOutputs.IsValidIndex(Index)) continue;
    const auto& Binding = Call->FunctionOutputs[Index];
    CD::FOutput O; O.Index = Index; O.BindingId = Binding.ExpressionOutputId;
    const auto* Node = CachedResolved(Binding.ExpressionOutput, Call->GetPathName() + TEXT(".selected_output"), Errors);
    O.bReady = Node && Node->GetClass() == UMaterialExpressionFunctionOutput::StaticClass();
    O.Fact->SetNumberField(TEXT("index"), Index);
    O.Fact->SetObjectField(TEXT("expression_output_id"), CachedGuid(Binding.ExpressionOutputId));
    O.Fact->SetField(TEXT("expression_output"), CachedIdentity(Node));
    const auto& Output = Binding.Output;
    O.Fact->SetObjectField(TEXT("binding_output_masks"), CachedMasks(Output.Mask, Output.MaskR, Output.MaskG, Output.MaskB, Output.MaskA));
    if (O.bReady)
    {
     O.NodeId = Node->Id; O.NodePath = Node->GetPathName();
     FJson N = MakeShared<FJsonObject>();
     N->SetObjectField(TEXT("id"), CachedGuid(Node->Id));
     N->SetStringField(TEXT("output_name"), Node->OutputName.ToString());
     N->SetObjectField(TEXT("a"), CachedConnection(Node->A, Errors));
     O.Fact->SetObjectField(TEXT("node"), N);
     const auto* A = Node->A.Expression;
     if (CachedReadable(A) && A->GetClass() == UMaterialExpressionFunctionInput::StaticClass())
     {
      O.Route = CD::ERoute::FunctionInput;
      O.AInputId = CastChecked<UMaterialExpressionFunctionInput>(A)->Id; O.AInputPath = A->GetPathName();
     }
     else if (CachedReadable(A) && (A->GetClass() == UMaterialExpressionConstant::StaticClass() || A->GetClass() == UMaterialExpressionConstant3Vector::StaticClass()))
      O.Route = CD::ERoute::DirectLeaf;
    }
    else O.Fact->SetField(TEXT("node"), MakeShared<FJsonValueNull>());
    P.Outputs.Add(MoveTemp(O));
   }
  if (P.InputCount <= CD::MaxInputs)
   for (int32 Index = 0; Index < P.InputCount; ++Index)
   {
    const auto& Binding = Call->FunctionInputs[Index];
    CD::FInput I; I.Index = Index; I.BindingId = Binding.ExpressionInputId;
    const auto* Node = CachedResolved(Binding.ExpressionInput, Call->GetPathName() + TEXT(".input_manifest"), Errors);
    I.bReady = Node && Node->GetClass() == UMaterialExpressionFunctionInput::StaticClass();
    I.Fact->SetNumberField(TEXT("index"), Index);
    I.Fact->SetObjectField(TEXT("expression_input_id"), CachedGuid(Binding.ExpressionInputId));
    I.Fact->SetField(TEXT("expression_input"), CachedIdentity(Node));
    I.Fact->SetBoolField(TEXT("exact_input_class"), I.bReady);
    if (I.bReady) { I.NodeId = Node->Id; I.NodePath = Node->GetPathName(); I.Fact->SetObjectField(TEXT("node_id"), CachedGuid(Node->Id)); }
    else I.Fact->SetField(TEXT("node_id"), MakeShared<FJsonValueNull>());
    P.Inputs.Add(MoveTemp(I));
   }
  P.BuildRich = [Call](int32 Index) { return CachedRichInput(Call, Index); };
  P.Initialize();
  Calls.Add(MakeShared<FJsonValueObject>(P.Call)); Work.Add(MoveTemp(P));
 }
 Value->SetArrayField(TEXT("calls"), Calls);
 Value->SetArrayField(TEXT("field_errors"), Errors);
 return Value;
}

namespace SP = DaedalusMaterialSwitchProofPolicy;
namespace CD = DaedalusMaterialCachedDiagnostic;
static const TCHAR* SwitchFunction = TEXT("/InterchangeAssets/gltf/MaterialBodies/MF_Default_Body.MF_Default_Body");

static void ProofError(FValues& Errors, const FString& Where, const TCHAR* Reason)
{
 Errors.Add(MakeShared<FJsonValueString>(Where + TEXT(": ") + Reason));
}

static bool ProofOwner(const UMaterialExpression* Node, const UMaterial* Material, const UObject* Function)
{
 return CachedReadable(Node) && (Node->GetOuter() == Material || Node->GetOuter() == Function);
}

static SP::ELeaf ProofLeafClass(const UMaterialExpression* Node)
{
 if (!CachedReadable(Node)) return SP::ELeaf::Unsupported;
 if (Node->GetClass() == UMaterialExpressionStaticBool::StaticClass()) return SP::ELeaf::StaticBool;
 if (Node->GetClass() == UMaterialExpressionConstant3Vector::StaticClass()) return SP::ELeaf::RGB;
 if (Node->GetClass() == UMaterialExpressionConstant::StaticClass()) return SP::ELeaf::Scalar;
 return SP::ELeaf::Unsupported;
}

// Inspect only public cached output metadata. No virtual outputs or graph evaluation.
static bool ProofConnection(const FExpressionInput& Input, bool bRGB)
{
 const auto* Node = Input.Expression;
 if (!CachedReadable(Node) || Input.OutputIndex != 0 || Node->Outputs.Num() > 64
     || !Node->Outputs.IsValidIndex(Input.OutputIndex)) return false;
 const auto& Output = Node->Outputs[Input.OutputIndex];
 const bool M = Input.Mask ? !!Input.Mask : !!Output.Mask;
 const bool R = Input.Mask ? !!Input.MaskR : !!Output.MaskR;
 const bool G = Input.Mask ? !!Input.MaskG : !!Output.MaskG;
 const bool B = Input.Mask ? !!Input.MaskB : !!Output.MaskB;
 const bool A = Input.Mask ? !!Input.MaskA : !!Output.MaskA;
 return (!M && !R && !G && !B && !A) || (bRGB && M && R && G && B && !A);
}

static FJson ProofDetail(const FExpressionInput& Input, FValues& Errors)
{
 FJson Fact = CachedConnection(Input, Errors);
 const auto* Node = Input.Expression;
 if (CachedReadable(Node) && Node->GetClass() == UMaterialExpressionStaticBool::StaticClass())
  Fact->SetBoolField(TEXT("static_bool_value"), CastChecked<UMaterialExpressionStaticBool>(Node)->Value != 0);
 return Fact;
}

// Metadata only for BOTH branches. Reject reroute ancestry BEFORE tracing: the
// installed non-reroute GetTracedInput returns *this, so this cannot recurse.
static FJson ProofBranch(const FExpressionInput& Input, const UMaterial* Material,
 const UObject* Function, SP::FUsage& Usage, SP::FBranch& Result)
{
 FJson Fact = MakeShared<FJsonObject>();
 const auto* Node = Input.Expression;
 const bool bAdmitted = Usage.TryMetadata();
 Result.bPresent = bAdmitted && CachedReadable(Node);
 Result.bOwnerExact = bAdmitted && ProofOwner(Node, Material, Function);
 Result.bReroute = Result.bPresent && Node->IsA(UMaterialExpressionRerouteBase::StaticClass());
 bool bTracedConnected = false;
 if (Result.bPresent && !Result.bReroute)
 {
  const FExpressionInput Traced = Input.GetTracedInput();
  bTracedConnected = CachedReadable(Traced.Expression);
  Result.bTraceDirect = bTracedConnected && Traced.Expression == Node
   && Traced.OutputIndex == Input.OutputIndex && Traced.Mask == Input.Mask
   && Traced.MaskR == Input.MaskR && Traced.MaskG == Input.MaskG
   && Traced.MaskB == Input.MaskB && Traced.MaskA == Input.MaskA;
 }
 Fact->SetBoolField(TEXT("expression_present"), Node != nullptr);
 Fact->SetField(TEXT("expression"), CachedIdentity(Node));
 Fact->SetBoolField(TEXT("traced_connected"), bTracedConnected);
 Fact->SetBoolField(TEXT("traced_direct_equal"), Result.bTraceDirect);
 Fact->SetBoolField(TEXT("is_reroute_base"), Result.bReroute);
 return Fact;
}

// ONE selected lane, at most FunctionInput -> direct typed caller leaf. This is
// deliberately not recursive and does not inspect Preview/default expressions.
static bool ProofLane(const FExpressionInput& Input, SP::ELeaf Expected,
 const UMaterial* Material, const UObject* Function,
 const UMaterialExpressionMaterialFunctionCall* Call, const CD::FProjection& Projection,
 SP::FUsage& Usage, FValues& Rich, FJson& Detail, bool& BoolValue,
 int32& InputType, FValues& Errors)
{
 const auto* Node = Input.Expression;
 const bool bRGB = Expected == SP::ELeaf::RGB;
 if (!Usage.TryEdge(1) || !Usage.TryDetail() || !ProofOwner(Node, Material, Function)
     || !ProofConnection(Input, bRGB)) return false;
 if (Node->GetClass() != UMaterialExpressionFunctionInput::StaticClass() && ProofLeafClass(Node) != Expected) return false;
 Detail = ProofDetail(Input, Errors);
 const FExpressionInput* LeafInput = &Input;
 InputType = -1;
 if (Node->GetClass() == UMaterialExpressionFunctionInput::StaticClass())
 {
  const auto* FunctionInput = CastChecked<UMaterialExpressionFunctionInput>(Node);
  const int32 ExpectedType = Expected == SP::ELeaf::StaticBool ? 8 : bRGB ? 2 : 0;
  InputType = static_cast<int32>(FunctionInput->InputType.GetValue());
  if (Node->GetOuter() != Function || InputType != ExpectedType || Rich.Num() >= 2
      || !Usage.TryEdge(2) || !Usage.TryDetail()) return false;
  int32 MatchIndex = INDEX_NONE, Matches = 0;
  for (const auto& Entry : Projection.Inputs)
   if (Entry.bReady && Entry.BindingId == FunctionInput->Id && Entry.NodeId == FunctionInput->Id
       && Entry.NodePath == FunctionInput->GetPathName()) { MatchIndex = Entry.Index; ++Matches; }
  if (Matches != 1 || !Call->FunctionInputs.IsValidIndex(MatchIndex)) return false;
  const auto& Binding = Call->FunctionInputs[MatchIndex];
  const auto* BoundNode = CachedResolved(Binding.ExpressionInput, TEXT("switch rich binding"), Errors);
  if (BoundNode != Node || Binding.ExpressionInputId != FunctionInput->Id) return false;
  LeafInput = &Binding.Input;
  if (!CachedReadable(LeafInput->Expression) || LeafInput->Expression->GetOuter() != Material) return false;
  FJson Entry = MakeShared<FJsonObject>();
  Entry->SetNumberField(TEXT("index"), MatchIndex);
  Entry->SetObjectField(TEXT("expression_input_id"), CachedGuid(Binding.ExpressionInputId));
  Entry->SetField(TEXT("expression_input"), CachedIdentity(Node));
  FJson N = MakeShared<FJsonObject>();
  N->SetObjectField(TEXT("id"), CachedGuid(FunctionInput->Id));
  N->SetNumberField(TEXT("input_type"), InputType);
  N->SetStringField(TEXT("input_type_name"), Expected == SP::ELeaf::StaticBool
   ? TEXT("FunctionInput_StaticBool") : bRGB ? TEXT("FunctionInput_Vector3") : TEXT("FunctionInput_Scalar"));
  Entry->SetObjectField(TEXT("node"), N);
  // Only the expected typed direct leaf is expanded; numeric parameters and
  // nested graphs do not acquire authored defaults through this helper.
  if (ProofLeafClass(LeafInput->Expression) != Expected) return false;
  Entry->SetObjectField(TEXT("caller_input"), ProofDetail(*LeafInput, Errors));
  Rich.Add(MakeShared<FJsonValueObject>(Entry));
 }
 const auto* Leaf = LeafInput->Expression;
 const bool bOutputValid = CachedReadable(Leaf) && Leaf->Outputs.Num() <= 64 && Leaf->Outputs.IsValidIndex(LeafInput->OutputIndex);
 if (!SP::ChosenLeaf(ProofLeafClass(Leaf), Expected, LeafInput->OutputIndex == 0,
      bOutputValid, ProofConnection(*LeafInput, bRGB), ProofOwner(Leaf, Material, Function))) return false;
 if (Expected == SP::ELeaf::StaticBool) BoolValue = CastChecked<UMaterialExpressionStaticBool>(Leaf)->Value != 0;
 else if (Expected == SP::ELeaf::RGB)
 {
  const auto V = CastChecked<UMaterialExpressionConstant3Vector>(Leaf)->Constant;
  if (!FMath::IsFinite(V.R) || !FMath::IsFinite(V.G) || !FMath::IsFinite(V.B) || !FMath::IsFinite(V.A)) return false;
 }
 else if (!FMath::IsFinite(CastChecked<UMaterialExpressionConstant>(Leaf)->R)) return false;
 return true;
}

static bool ProofParameter(const UMaterialExpressionStaticSwitchParameter* Node,
 const UMaterial* Material, const UMaterialExpressionMaterialFunctionCall* Call,
 const UObject* Function, SP::FUsage& Usage, FJson Switch, bool& Selected)
{
 if (!Usage.TryMetadata() || !Usage.TryQuery()) return false;
 FJson Info = MakeShared<FJsonObject>();
 Info->SetStringField(TEXT("name"), Node->ParameterName.ToString());
 Info->SetStringField(TEXT("association"), TEXT("GlobalParameter"));
 Info->SetNumberField(TEXT("index"), INDEX_NONE);
 const FMaterialParameterInfo ParameterInfo(Node->ParameterName, GlobalParameter, INDEX_NONE);
 TArray<FMaterialParameterInfo> Infos; TArray<FGuid> Guids;
 Material->GetAllStaticSwitchParameterInfo(Infos, Guids);
 SP::FParameterProof P;
 P.InfoCount = Infos.Num(); P.GuidCount = Guids.Num();
 P.bEnumerationComplete = P.InfoCount == P.GuidCount && P.InfoCount >= 1 && P.InfoCount <= 128;
 P.bContextExact = Call->GetOuter() == Material && Node->GetOuter() == Function && !Node->ParameterName.IsNone();
 P.bNodeGuidValid = Node->ExpressionGUID.IsValid();
 P.bDynamicKnown = true; P.bDynamic = Node->DynamicBranch != 0;
 FValues Matches;
 if (P.bEnumerationComplete)
  for (int32 Index = 0; Index < Infos.Num(); ++Index)
   if (Infos[Index].Name == ParameterInfo.Name && Infos[Index].Association == ParameterInfo.Association
       && Infos[Index].Index == ParameterInfo.Index)
   {
    ++P.Matches;
    FJson Match = MakeShared<FJsonObject>(); Match->SetObjectField(TEXT("parameter_info"), Info);
    Match->SetStringField(TEXT("expression_guid"), Guids[Index].ToString(EGuidFormats::Digits).ToLower());
    Matches.Add(MakeShared<FJsonValueObject>(Match));
    if (Guids[Index] != Node->ExpressionGUID) P.bContextExact = false;
   }
 bool Value = false; FGuid ReturnedGuid;
 // No query for invalid/ambiguous/dynamic context, and no authored-default fallback.
 if (P.bEnumerationComplete && P.Matches == 1 && P.bContextExact && P.bNodeGuidValid && !P.bDynamic)
  P.bQuerySucceeded = Material->GetStaticSwitchParameterValue(FHashedMaterialParameterInfo(ParameterInfo), Value, ReturnedGuid, false);
 P.bReturnedGuidExact = P.bQuerySucceeded && ReturnedGuid == Node->ExpressionGUID;
 P.bValue = Value;
 FJson Query = MakeShared<FJsonObject>();
 Query->SetStringField(TEXT("api"), TEXT("UMaterialInterface::GetStaticSwitchParameterValue"));
 Query->SetStringField(TEXT("material_path"), Material->GetPathName());
 Query->SetStringField(TEXT("caller_path"), Call->GetPathName());
 Query->SetStringField(TEXT("function_path"), Function->GetPathName());
 Query->SetStringField(TEXT("node_expression_guid"), Node->ExpressionGUID.ToString(EGuidFormats::Digits).ToLower());
 Query->SetObjectField(TEXT("parameter_info"), Info);
 Query->SetBoolField(TEXT("enumeration_complete"), P.bEnumerationComplete);
 Query->SetNumberField(TEXT("enumerated_count"), Infos.Num());
 Query->SetNumberField(TEXT("parameter_info_count"), Infos.Num());
 Query->SetNumberField(TEXT("parameter_guid_count"), Guids.Num());
 Query->SetArrayField(TEXT("enumerated_matches"), Matches);
 Query->SetBoolField(TEXT("query_succeeded"), P.bQuerySucceeded);
 Query->SetBoolField(TEXT("overridden_only"), false);
 if (P.bQuerySucceeded)
 {
  Query->SetStringField(TEXT("returned_expression_guid"), ReturnedGuid.ToString(EGuidFormats::Digits).ToLower());
  Query->SetBoolField(TEXT("value"), Value);
 }
 else
 {
  Query->SetField(TEXT("returned_expression_guid"), MakeShared<FJsonValueNull>());
  Query->SetField(TEXT("value"), MakeShared<FJsonValueNull>());
 }
 Switch->SetBoolField(TEXT("dynamic_branch"), P.bDynamic);
 Switch->SetStringField(TEXT("expression_guid"), Node->ExpressionGUID.ToString(EGuidFormats::Digits).ToLower());
 Switch->SetStringField(TEXT("parameter_name"), Node->ParameterName.ToString());
 Switch->SetObjectField(TEXT("parameter_query"), Query);
 return SP::ParameterValue(P, Selected);
}

static void CaptureSwitchProofs(UMaterial* Material, UMaterialEditorOnlyData* Data,
 CD::FProjection& Projection, FValues& Errors)
{
 FValues Routes; Projection.Call->SetArrayField(TEXT("route_proofs"), Routes);
 if (!Data || Projection.InputCount != 89 || Projection.OutputCount != 12
     || !CD::ValidManifest(Projection.Inputs, 89) || Projection.Selected != TArray<int32>{0, 1, 3})
 { ProofError(Errors, Material->GetPathName(), TEXT("Complete exact 89/12 binding projection required")); return; }
 const auto* Call = Cast<UMaterialExpressionMaterialFunctionCall>(Data->BaseColor.Expression);
 if (!CachedReadable(Call) || Call->GetClass() != UMaterialExpressionMaterialFunctionCall::StaticClass()
     || Call->GetOuter() != Material || Call->GetName() != TEXT("MaterialExpressionMaterialFunctionCall_0")
     || Data->Metallic.Expression != Call || Data->Roughness.Expression != Call)
 { ProofError(Errors, Material->GetPathName(), TEXT("One exact current material-owned call required")); return; }
 const auto* Function = CachedResolved(Call->MaterialFunction, TEXT("switch function"), Errors);
 if (!Function || Function->GetPathName() != SwitchFunction || Function->GetClass()->GetPathName() != TEXT("/Script/Engine.MaterialFunction"))
 { ProofError(Errors, Material->GetPathName(), TEXT("Exact already resolved MF_Default_Body required")); return; }
 for (const auto& Entry : Projection.Inputs)
  if (!Entry.NodePath.StartsWith(FString(SwitchFunction) + TEXT(":MaterialExpressionFunctionInput_")))
  { ProofError(Errors, Material->GetPathName(), TEXT("Manifest input outside exact function")); return; }
 const TCHAR* Names[]{TEXT("base_color"), TEXT("metallic"), TEXT("roughness")};
 const int32 Indices[]{0, 1, 3};
 const TCHAR* GuidTexts[]{TEXT("a12e80f64d5d5086a53effa8549c2e45"), TEXT("84cbc44b43d0c29c1c8969a5f9388f36"), TEXT("bf502fd74d9826b42ae945948da8833e")};
 const TCHAR* OutputNames[]{TEXT("MaterialExpressionFunctionOutput_0"), TEXT("MaterialExpressionFunctionOutput_11"), TEXT("MaterialExpressionFunctionOutput_13")};
 const TCHAR* SwitchNames[]{TEXT("MaterialExpressionStaticSwitchParameter_0"), TEXT("MaterialExpressionStaticSwitch_3"), TEXT("MaterialExpressionStaticSwitch_4")};
 SP::FUsage Usage;
 for (int32 Lane = 0; Lane < 3; ++Lane)
 {
  const FString Where = Material->GetPathName() + TEXT("/") + Names[Lane];
  if (!Usage.TryRoot() || !Usage.TryDetail() || !Call->FunctionOutputs.IsValidIndex(Indices[Lane]))
  { ProofError(Errors, Where, TEXT("Switch/output bound refused")); break; }
  const auto& Binding = Call->FunctionOutputs[Indices[Lane]];
  const auto* Output = CachedResolved(Binding.ExpressionOutput, Where, Errors);
  const auto* Expression = Output ? Output->A.Expression : nullptr;
  const UClass* ExpectedClass = Lane == 0 ? UMaterialExpressionStaticSwitchParameter::StaticClass() : UMaterialExpressionStaticSwitch::StaticClass();
  if (!CachedReadable(Output) || Output->GetClass() != UMaterialExpressionFunctionOutput::StaticClass()
      || Output->GetOuter() != Function || Output->GetName() != OutputNames[Lane]
      || Output->Id != Binding.ExpressionOutputId || Output->Id.ToString(EGuidFormats::Digits).ToLower() != GuidTexts[Lane]
      || !CachedReadable(Expression) || Expression->GetClass() != ExpectedClass
      || Expression->GetName() != SwitchNames[Lane] || Expression->GetOuter() != Function || !ProofConnection(Output->A, false))
  { ProofError(Errors, Where, TEXT("Exact output GUID/identity/unmasked switch root required")); continue; }
  FJson Route = MakeShared<FJsonObject>(), Switch = MakeShared<FJsonObject>(); FValues Rich;
  Route->SetStringField(TEXT("property"), Names[Lane]); Switch->SetField(TEXT("expression"), CachedIdentity(Expression));
  const FExpressionInput* A = nullptr; const FExpressionInput* B = nullptr;
  const auto* Parameter = Lane == 0 ? CastChecked<UMaterialExpressionStaticSwitchParameter>(Expression) : nullptr;
  const auto* Ordinary = Lane != 0 ? CastChecked<UMaterialExpressionStaticSwitch>(Expression) : nullptr;
  if (Parameter) { A = &Parameter->A; B = &Parameter->B; }
  else { A = &Ordinary->A; B = &Ordinary->B; }
  SP::FBranch PA, PB;
  FJson AF = ProofBranch(*A, Material, Function, Usage, PA), BF = ProofBranch(*B, Material, Function, Usage, PB);
  Switch->SetObjectField(TEXT("a"), AF); Switch->SetObjectField(TEXT("b"), BF);
  bool bSelected = false, bSelectorReady = false;
  if (!SP::BothDirect(PA, PB)) ProofError(Errors, Where, TEXT("Both branches require readable direct trace/owner equality and no reroute ancestry"));
  else if (Parameter) bSelectorReady = ProofParameter(Parameter, Material, Call, Function, Usage, Switch, bSelected);
  else if (Usage.TryMetadata())
  {
   SP::FBoolProof Proof; Proof.bConnected = Ordinary->Value.Expression != nullptr;
   Proof.bDefaultKnown = true; Proof.bDefault = Ordinary->DefaultValue != 0;
   Switch->SetBoolField(TEXT("default_value"), Proof.bDefault);
   FJson Value = MakeShared<FJsonObject>();
   Value->SetBoolField(TEXT("expression_present"), Proof.bConnected);
   Value->SetField(TEXT("expression"), CachedIdentity(Ordinary->Value.Expression));
   if (Proof.bConnected)
   {
    bool TypedValue = false; int32 InputType = -1;
    Proof.bValueKnown = ProofLane(Ordinary->Value, SP::ELeaf::StaticBool, Material, Function, Call, Projection, Usage, Rich, Value, TypedValue, InputType, Errors);
    Proof.FunctionInputType = InputType; Proof.bUniqueBinding = InputType == 8;
    Proof.bTypedStaticBool = Proof.bValueKnown; Proof.bValue = TypedValue;
   }
   Switch->SetObjectField(TEXT("value"), Value);
   bSelectorReady = SP::StaticValue(Proof, bSelected);
  }
  if (!bSelectorReady) ProofError(Errors, Where, TEXT("Static selector lacks unique typed current-context proof; no default fallback"));
  else
  {
   FJson Chosen = MakeShared<FJsonObject>(); bool Unused = false; int32 InputType = -1;
   const bool bLeafReady = ProofLane(bSelected ? *A : *B, Lane == 0 ? SP::ELeaf::RGB : SP::ELeaf::Scalar,
     Material, Function, Call, Projection, Usage, Rich, Chosen, Unused, InputType, Errors);
   if (!bLeafReady) ProofError(Errors, Where, TEXT("Chosen lane lacks bounded exact typed constant proof"));
   // Reuse real trace observations on the selected detailed connection. The
   // unchosen endpoint keeps identity metadata only, without value expansion.
   Chosen->SetBoolField(TEXT("traced_connected"), (bSelected ? AF : BF)->GetBoolField(TEXT("traced_connected")));
   Chosen->SetBoolField(TEXT("traced_direct_equal"), (bSelected ? AF : BF)->GetBoolField(TEXT("traced_direct_equal")));
   Chosen->SetBoolField(TEXT("is_reroute_base"), (bSelected ? AF : BF)->GetBoolField(TEXT("is_reroute_base")));
   Switch->SetObjectField(bSelected ? TEXT("a") : TEXT("b"), Chosen);
   Route->SetStringField(TEXT("selected_branch"), bSelected ? TEXT("a") : TEXT("b"));
  }
  Route->SetObjectField(TEXT("switch"), Switch); Route->SetArrayField(TEXT("rich_inputs"), Rich);
  Routes.Add(MakeShared<FJsonValueObject>(Route));
 }
 Projection.Call->SetArrayField(TEXT("route_proofs"), Routes);
 FJson Counts = MakeShared<FJsonObject>();
 Counts->SetNumberField(TEXT("roots"), Usage.Roots); Counts->SetNumberField(TEXT("metadata"), Usage.Metadata);
 Counts->SetNumberField(TEXT("details"), Usage.Details); Counts->SetNumberField(TEXT("queries"), Usage.Queries);
 Projection.Call->SetObjectField(TEXT("switch_proof_usage"), Counts);
}


static FJson InputFacts(UMaterial* Material, const TCHAR* Name, FExpressionInput* Current,
	const FExpressionInput* Typed, bool bUseConstant, const FLinearColor* Color,
	const float* Scalar, FValues& Errors)
{
	FJson Json = MakeShared<FJsonObject>();
	Json->SetBoolField(TEXT("current_input_present"), Current && Current == Typed);
	Json->SetBoolField(TEXT("uses_input_constant"), bUseConstant);
	Json->SetStringField(TEXT("value_route"), TEXT("unsupported"));
	Json->SetField(TEXT("value"), MakeShared<FJsonValueNull>());
	Json->SetField(TEXT("raw_value"), MakeShared<FJsonValueNull>());
	Json->SetField(TEXT("raw_value_type"), MakeShared<FJsonValueNull>());
	UnknownMasks(Json, TEXT(""));
	UnknownMasks(Json, TEXT("selected_output_"));
	UnknownMasks(Json, TEXT("effective_"));
	Json->SetBoolField(TEXT("selected_output_valid"), false);
	Json->SetField(TEXT("output_index"), MakeShared<FJsonValueNull>());
	const auto Hold = [&](const TCHAR* Reason)
	{
		Errors.Add(MakeShared<FJsonValueString>(Material->GetPathName() + TEXT("/") + Name + TEXT(": ") + Reason));
		return Json;
	};
	if (!Current || Current != Typed) return Hold(TEXT("Current public input differs from typed editor data."));
	Masks(Json, TEXT(""), Current->Mask, Current->MaskR, Current->MaskG, Current->MaskB, Current->MaskA);
	Masks(Json, TEXT("effective_"), !!Current->Mask, !!Current->MaskR, !!Current->MaskG, !!Current->MaskB, !!Current->MaskA);
	Json->SetNumberField(TEXT("output_index"), Current->OutputIndex);
	UMaterialExpression* Expression = Current->Expression;
	Json->SetBoolField(TEXT("expression_present"), Expression != nullptr);
	if (IsValid(Expression))
	{
		Json->SetStringField(TEXT("expression_class"), Expression->GetClass()->GetPathName());
		Json->SetStringField(TEXT("expression_path"), Expression->GetPathName());
	}
	else
	{
		Json->SetField(TEXT("expression_class"), MakeShared<FJsonValueNull>());
		Json->SetField(TEXT("expression_path"), MakeShared<FJsonValueNull>());
	}
	// Unknown/function expressions are not asked to construct their virtual outputs.
	if (IsValid(Expression) && KnownClass(Expression))
	{
		const auto& Outputs = Expression->GetOutputs();
		if (Outputs.IsValidIndex(Current->OutputIndex))
		{
			const FExpressionOutput& Output = Outputs[Current->OutputIndex];
			Json->SetBoolField(TEXT("selected_output_valid"), true);
			Masks(Json, TEXT("selected_output_"), Output.Mask, Output.MaskR, Output.MaskG, Output.MaskB, Output.MaskA);
			// MaterialShared GetConnectionMask: explicit input wins; otherwise output fallback.
			if (!Current->Mask) Masks(Json, TEXT("effective_"), !!Output.Mask, !!Output.MaskR, !!Output.MaskG, !!Output.MaskB, !!Output.MaskA);
		}
	}
	// Legacy CompileWithDefault and experimental MIR differ for contradictory data.
	// Neither precedence is asserted universally. Unambiguous authored routes only.
	if (bUseConstant && Expression) return Hold(TEXT("Inline constant plus expression has compiler-dependent precedence."));
	FLinearColor VectorValue;
	float ScalarValue = 0;
	if (bUseConstant)
	{
		Json->SetStringField(TEXT("value_route"), TEXT("input_constant"));
		if (Color) VectorValue = *Color;
		else ScalarValue = *Scalar;
	}
	else
	{
		if (!IsValid(Expression)) return Hold(TEXT("Missing authored expression; engine default is not evidence."));
		if (Expression->GetOuter() != Material || Current->OutputIndex != 0
			|| !Json->GetBoolField(TEXT("selected_output_valid"))) return Hold(TEXT("Require exact material-owned primary output with valid output metadata."));
		Json->SetStringField(TEXT("value_route"), TEXT("direct_expression"));
		if (Color && Expression->GetClass() == UMaterialExpressionConstant3Vector::StaticClass())
			VectorValue = CastChecked<UMaterialExpressionConstant3Vector>(Expression)->Constant;
		else if (!Color && Expression->GetClass() == UMaterialExpressionConstant::StaticClass())
			ScalarValue = CastChecked<UMaterialExpressionConstant>(Expression)->R;
		else if (Color && Expression->GetClass() == UMaterialExpressionVectorParameter::StaticClass())
		{
			const auto* Parameter = CastChecked<UMaterialExpressionVectorParameter>(Expression);
			Json->SetStringField(TEXT("parameter_name"), Parameter->ParameterName.ToString());
			Json->SetBoolField(TEXT("uses_custom_primitive_data"), Parameter->bUseCustomPrimitiveData);
			Json->SetNumberField(TEXT("primitive_data_index"), Parameter->PrimitiveDataIndex);
			const bool bFlatUnique = FlatUniqueParameter(Material, Parameter);
			Json->SetBoolField(TEXT("flat_parameter_binding_qualified"), bFlatUnique);
			if (Parameter->bUseCustomPrimitiveData || !bFlatUnique) return Hold(TEXT("Primitive data or unqualified parameter defaults."));
			VectorValue = Parameter->DefaultValue;
		}
		else if (!Color && Expression->GetClass() == UMaterialExpressionScalarParameter::StaticClass())
		{
			const auto* Parameter = CastChecked<UMaterialExpressionScalarParameter>(Expression);
			Json->SetStringField(TEXT("parameter_name"), Parameter->ParameterName.ToString());
			Json->SetBoolField(TEXT("uses_custom_primitive_data"), Parameter->bUseCustomPrimitiveData);
			Json->SetNumberField(TEXT("primitive_data_index"), Parameter->PrimitiveDataIndex);
			const bool bFlatUnique = FlatUniqueParameter(Material, Parameter);
			Json->SetBoolField(TEXT("flat_parameter_binding_qualified"), bFlatUnique);
			if (Parameter->bUseCustomPrimitiveData || !bFlatUnique) return Hold(TEXT("Primitive data or unqualified parameter defaults."));
			ScalarValue = Parameter->DefaultValue;
		}
		else return Hold(TEXT("Unsupported direct expression class or value type."));
	}
	if (Color)
	{
		if (!FMath::IsFinite(VectorValue.R) || !FMath::IsFinite(VectorValue.G) || !FMath::IsFinite(VectorValue.B) || !FMath::IsFinite(VectorValue.A)) return Hold(TEXT("Nonfinite raw color."));
		FValues Raw, RGB;
		for (float Value : {VectorValue.R, VectorValue.G, VectorValue.B, VectorValue.A}) Raw.Add(MakeShared<FJsonValueNumber>(Value));
		for (float Value : {VectorValue.R, VectorValue.G, VectorValue.B}) RGB.Add(MakeShared<FJsonValueNumber>(Value));
		Json->SetStringField(TEXT("raw_value_type"), TEXT("FLinearColor"));
		Json->SetArrayField(TEXT("raw_value"), Raw);
		Json->SetArrayField(TEXT("value"), RGB);
	}
	else
	{
		if (!FMath::IsFinite(ScalarValue)) return Hold(TEXT("Nonfinite raw scalar."));
		Json->SetStringField(TEXT("raw_value_type"), TEXT("float"));
		Json->SetNumberField(TEXT("raw_value"), ScalarValue);
		Json->SetNumberField(TEXT("value"), ScalarValue);
	}
	return Json;
}
} // namespace DaedalusMaterialFactors
#endif

static FString ReadMaterialFactsImpl(const TArray<FString>& MaterialObjectPaths,
	const FString& AllowedPackageRoot, const FString& PolicyId, bool bSwitchProof)
{
#if WITH_EDITOR
	using namespace DaedalusMaterialFactors;
	FJson Json = MakeShared<FJsonObject>();
	FValues Errors, Materials;
	Json->SetStringField(TEXT("schema"), TEXT("daedalus.material-factor-connections.v1"));
	Json->SetStringField(TEXT("policy_id"), PolicyId);
	Json->SetStringField(TEXT("allowed_root"), AllowedPackageRoot);
	Json->SetStringField(TEXT("state"), TEXT("held"));
	Json->SetBoolField(TEXT("native_invoked"), false);
	Json->SetNumberField(TEXT("mutations"), 0);
	Json->SetNumberField(TEXT("asset_loads"), 0);
	const auto Finish = [&]()
	{
		Json->SetArrayField(TEXT("errors"), Errors);
		Json->SetArrayField(TEXT("materials"), Materials);
		FString Serialized;
		if (!FJsonSerializer::Serialize(Json, TJsonWriterFactory<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>::Create(&Serialized)) || FTCHARToUTF8(*Serialized).Length() > 524288)
			return FString(TEXT("{\"state\":\"held\",\"errors\":[\"Native receipt serialization/cap failure\"]}"));
		return Serialized;
	};
	if (!IsInGameThread() || !GEditor || GEditor->PlayWorld || !GEditor->GetEditorWorldContext().World())
	{
		Errors.Add(MakeShared<FJsonValueString>(TEXT("Requires current editor game thread/world and no PIE.")));
		return Finish();
	}
	const FValues DirtyBefore = DirtyPackages();
	Json->SetArrayField(TEXT("dirty_before"), DirtyBefore);
	Json->SetArrayField(TEXT("dirty_after"), DirtyBefore);
	bool bPolicyIdValid = PolicyId.Len() == 64;
	for (TCHAR C : PolicyId) bPolicyIdValid &= (C >= '0' && C <= '9') || (C >= 'a' && C <= 'f');
	if (MaterialObjectPaths.Num() != 2 || !bPolicyIdValid || AllowedPackageRoot.Len() > 512
		|| !AllowedPackageRoot.StartsWith(TEXT("/Game/CodexToolEvaluation/"))
		|| !FPackageName::IsValidLongPackageName(AllowedPackageRoot) || AllowedPackageRoot.EndsWith(TEXT("/")) || !DirtyBefore.IsEmpty())
	{
		Errors.Add(MakeShared<FJsonValueString>(TEXT("Require two explicit material paths, canonical owned root, policy SHA256 and clean packages.")));
		return Finish();
	}
	TSet<FString> Seen;
	TArray<UMaterial*> Targets;
	for (const FString& Path : MaterialObjectPaths)
	{
		if (Path.Len() > 1024)
		{
			Errors.Add(MakeShared<FJsonValueString>(TEXT("Material path exceeds the bounded request length.")));
			return Finish();
		}
		const FString Package = FPackageName::ObjectPathToPackageName(Path);
		const FString Asset = FPackageName::GetLongPackageAssetName(Package);
		UObject* Object = Path.Len() <= 1024 ? FindObject<UObject>(nullptr, *Path) : nullptr;
		if (!Path.StartsWith(AllowedPackageRoot + TEXT("/")) || !FPackageName::IsValidLongPackageName(Package)
			|| Path != Package + TEXT(".") + Asset || Seen.Contains(Path.ToLower())
			|| !IsValid(Object) || Object->GetPathName() != Path || Object->GetClass() != UMaterial::StaticClass()
			|| !Object->IsAsset() || Object->GetOuter() != Object->GetOutermost()
			|| Object->GetOutermost()->IsDirty() || Object->GetOutermost()->HasAnyPackageFlags(PKG_ContainsMap))
		{
			Errors.Add(MakeShared<FJsonValueString>(TEXT("Require exact distinct already loaded clean non-map UMaterial assets, no instances/subobjects.")));
			return Finish();
		}
		Seen.Add(Path.ToLower());
		Targets.Add(CastChecked<UMaterial>(Object));
	}
	Json->SetBoolField(TEXT("native_invoked"), true);
 if (bSwitchProof)
 {
  FJson Observation = MakeShared<FJsonObject>();
  Observation->SetStringField(TEXT("schema"), TEXT("daedalus.material-static-switch-proof-observation.v1"));
  Observation->SetStringField(TEXT("capture_id"), FGuid::NewGuid().ToString(EGuidFormats::DigitsWithHyphensLower));
  Observation->SetStringField(TEXT("observed_at_utc"), FDateTime::UtcNow().ToIso8601());
  Observation->SetBoolField(TEXT("native_invoked"), true);
  Json->SetObjectField(TEXT("proof_observation"), Observation);
 }
	for (UMaterial* Material : Targets)
	{
		FJson Record = MakeShared<FJsonObject>();
		Record->SetStringField(TEXT("material_path"), Material->GetPathName());
		Record->SetStringField(TEXT("material_class"), Material->GetClass()->GetPathName());
		Record->SetStringField(TEXT("blend_mode"), StaticEnum<EBlendMode>()->GetNameStringByValue(Material->BlendMode));
		Record->SetStringField(TEXT("material_domain"), StaticEnum<EMaterialDomain>()->GetNameStringByValue(Material->MaterialDomain));
		Record->SetBoolField(TEXT("two_sided"), Material->TwoSided != 0);
		Record->SetBoolField(TEXT("uses_material_attributes"), Material->bUseMaterialAttributes != 0);
		UMaterialEditorOnlyData* Data = Material->GetEditorOnlyData();
		if (!Data)
		{
			Record->SetField(TEXT("front_material_connected"), MakeShared<FJsonValueNull>());
			Errors.Add(MakeShared<FJsonValueString>(TEXT("Current typed material editor data unavailable.")));
		}
		else
		{
			Record->SetBoolField(TEXT("front_material_connected"), Data->FrontMaterial.Expression != nullptr);
			FJson Inputs = MakeShared<FJsonObject>();
   FValues DirectErrors; FValues& InputErrors = bSwitchProof ? DirectErrors : Errors;
			Inputs->SetObjectField(TEXT("base_color"), InputFacts(Material, TEXT("base_color"), Material->GetExpressionInputForProperty(MP_BaseColor), &Data->BaseColor, Data->BaseColor.UseConstant, &Data->BaseColor.Constant, nullptr, InputErrors));
			Inputs->SetObjectField(TEXT("metallic"), InputFacts(Material, TEXT("metallic"), Material->GetExpressionInputForProperty(MP_Metallic), &Data->Metallic, Data->Metallic.UseConstant, nullptr, &Data->Metallic.Constant, InputErrors));
			Inputs->SetObjectField(TEXT("roughness"), InputFacts(Material, TEXT("roughness"), Material->GetExpressionInputForProperty(MP_Roughness), &Data->Roughness, Data->Roughness.UseConstant, nullptr, &Data->Roughness.Constant, InputErrors));
			Record->SetObjectField(TEXT("inputs"), Inputs);
   if (bSwitchProof) Record->SetArrayField(TEXT("direct_reader_limits"), DirectErrors);
		}
		Materials.Add(MakeShared<FJsonValueObject>(Record));
	}

 // Establish the complete outer frame, original errors, both materials and every
 // diagnostic skeleton BEFORE measuring any candidate input/output append.
 Json->SetArrayField(TEXT("materials"), Materials); Json->SetArrayField(TEXT("errors"), Errors);
 TArray<DaedalusMaterialCachedDiagnostic::FProjection> Work;
 for (int32 Index = 0; Index < Targets.Num(); ++Index)
 {
  const TArray<FString> Path{TEXT("materials"), FString::FromInt(Index), TEXT("cached_function_facts")};
  Materials[Index]->AsObject()->SetObjectField(TEXT("cached_function_facts"),
   CachedFunctionFacts(Targets[Index], Targets[Index]->GetEditorOnlyData(), Path, Work));
  if (bSwitchProof)
  {
   if (Work.Num() != Index + 1) ProofError(Errors, Targets[Index]->GetPathName(), TEXT("One exact cached call projection required"));
   else CaptureSwitchProofs(Targets[Index], Targets[Index]->GetEditorOnlyData(), Work[Index], Errors);
  }
 }
 // Include the NEW operation's errors and all switch proofs in each prospective
 // full-envelope append; original direct-reader errors remain informational only.
 if (bSwitchProof) Json->SetArrayField(TEXT("errors"), Errors);
 DaedalusMaterialCachedDiagnostic::FEnvelopeBudget Budget(Json);
 DaedalusMaterialCachedDiagnostic::CaptureAll(Budget, Work);
 for (int32 Index = 0; Index < Targets.Num(); ++Index)
 {
  auto Diagnostic = Materials[Index]->AsObject()->GetObjectField(TEXT("cached_function_facts"));
  bool Complete = Diagnostic->GetArrayField(TEXT("field_errors")).IsEmpty();
  for (const auto& Call : Diagnostic->GetArrayField(TEXT("calls")))
   for (const TCHAR* Key : {TEXT("input_manifest_status"), TEXT("selected_outputs_status"), TEXT("rich_inputs_status")})
    Complete &= Call->AsObject()->GetObjectField(Key)->GetBoolField(TEXT("complete"));
  Diagnostic->SetStringField(TEXT("state"), Complete ? TEXT("cached_facts_captured") : TEXT("partial"));
  if (bSwitchProof && !Complete) ProofError(Errors, Targets[Index]->GetPathName(), TEXT("New proof binding capture is incomplete"));
 }
 if (!Budget.Finish())
  return TEXT("{\"state\":\"held\",\"native_invoked\":true,\"diagnostic_complete\":false,\"errors\":[\"Bounded diagnostic outer envelope exceeded UTF8 cap\"]}");

	const FValues DirtyAfter = DirtyPackages();
	Json->SetArrayField(TEXT("dirty_after"), DirtyAfter);
	if (!DirtyAfter.IsEmpty()) Errors.Add(MakeShared<FJsonValueString>(TEXT("Dirty packages observed after read; no save or rollback attempted.")));
	if (Errors.IsEmpty()) Json->SetStringField(TEXT("state"), TEXT("complete"));
	return Finish();
#else
	return TEXT("{\"state\":\"held\",\"native_invoked\":false,\"errors\":[\"Editor-only material reader\"]}");
#endif
}


FString UDaedalusMaterialFactorLibrary::ReadMaterialFactors(const TArray<FString>& Paths,
 const FString& Root, const FString& PolicyId)
{
 return ReadMaterialFactsImpl(Paths, Root, PolicyId, false);
}

FString UDaedalusMaterialFactorLibrary::ReadMaterialSwitchProof(const TArray<FString>& Paths,
 const FString& Root, const FString& PolicyId)
{
 return ReadMaterialFactsImpl(Paths, Root, PolicyId, true);
}
