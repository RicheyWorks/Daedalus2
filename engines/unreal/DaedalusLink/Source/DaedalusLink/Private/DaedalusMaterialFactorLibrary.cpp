// SPDX-License-Identifier: MIT
#include "DaedalusMaterialFactorLibrary.h"

#if WITH_EDITOR
#include "Dom/JsonObject.h"
#include "DaedalusMaterialCachedDiagnostic.h"
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

FString UDaedalusMaterialFactorLibrary::ReadMaterialFactors(const TArray<FString>& MaterialObjectPaths,
	const FString& AllowedPackageRoot, const FString& PolicyId)
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
			Inputs->SetObjectField(TEXT("base_color"), InputFacts(Material, TEXT("base_color"), Material->GetExpressionInputForProperty(MP_BaseColor), &Data->BaseColor, Data->BaseColor.UseConstant, &Data->BaseColor.Constant, nullptr, Errors));
			Inputs->SetObjectField(TEXT("metallic"), InputFacts(Material, TEXT("metallic"), Material->GetExpressionInputForProperty(MP_Metallic), &Data->Metallic, Data->Metallic.UseConstant, nullptr, &Data->Metallic.Constant, Errors));
			Inputs->SetObjectField(TEXT("roughness"), InputFacts(Material, TEXT("roughness"), Material->GetExpressionInputForProperty(MP_Roughness), &Data->Roughness, Data->Roughness.UseConstant, nullptr, &Data->Roughness.Constant, Errors));
			Record->SetObjectField(TEXT("inputs"), Inputs);
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
 }
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
