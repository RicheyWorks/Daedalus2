// SPDX-License-Identifier: MIT
#include "DaedalusMaterialFactorLibrary.h"

#if WITH_EDITOR
#include "Dom/JsonObject.h"
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

static FJson CachedFunctionFacts(UMaterial* Material, UMaterialEditorOnlyData* Data)
{
	FJson Value = MakeShared<FJsonObject>();
	FValues Errors, Calls;
	Value->SetStringField(TEXT("schema"), TEXT("daedalus.material-cached-function-facts.v2"));
	Value->SetField(TEXT("material"), CachedIdentity(Material));
	Value->SetBoolField(TEXT("evaluation_performed"), false);
	Value->SetBoolField(TEXT("admission_changed"), false);
	Value->SetNumberField(TEXT("explicit_load_requests"), 0);
	Value->SetNumberField(TEXT("cache_refreshes"), 0);
	Value->SetNumberField(TEXT("virtual_getoutputs_calls"), 0);
	FJson Inputs = MakeShared<FJsonObject>();
	TMap<UMaterialExpressionMaterialFunctionCall*, TSet<int32>> Selected;
	const auto Add = [&](const TCHAR* Name, EMaterialProperty Property, const FExpressionInput* Typed, bool bUseConstant)
	{
		const FExpressionInput* Current = Material->GetExpressionInputForProperty(Property);
		FJson Fact = MakeShared<FJsonObject>();
		const bool bSame = Current && Current == Typed;
		Fact->SetBoolField(TEXT("current_input_pointer_equal"), bSame);
		Fact->SetBoolField(TEXT("uses_input_constant"), bUseConstant);
		if (bSame)
		{
			Fact->SetObjectField(TEXT("connection"), CachedConnection(*Current, Errors));
			UMaterialExpression* Expression = Current->Expression;
			if (CachedReadable(Expression) && Expression->GetClass() == UMaterialExpressionMaterialFunctionCall::StaticClass()
				&& Expression->GetOuter() == Material)
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
	else Errors.Add(MakeShared<FJsonValueString>(TEXT("Current public editor-only data unavailable")));
	Value->SetObjectField(TEXT("current_typed_inputs"), Inputs);
	if (Selected.Num() > 1) Errors.Add(MakeShared<FJsonValueString>(TEXT("More than one current function call; bounded capture refuses traversal")));
	else for (const auto& Item : Selected)
	{
		const auto* Call = Item.Key;
		FJson Captured = MakeShared<FJsonObject>();
		Captured->SetField(TEXT("caller"), CachedIdentity(Call));
		Captured->SetField(TEXT("owning_material"), CachedIdentity(Material));
		Captured->SetField(TEXT("material_function"), CachedIdentity(CachedResolved(Call->MaterialFunction, Call->GetPathName() + TEXT(".MaterialFunction"), Errors)));
		Captured->SetNumberField(TEXT("function_input_count"), Call->FunctionInputs.Num());
		Captured->SetNumberField(TEXT("function_output_count"), Call->FunctionOutputs.Num());
		FValues FunctionInputs, FunctionOutputs;
		if (Call->FunctionInputs.Num() > 64 || Call->FunctionOutputs.Num() > 64)
			Errors.Add(MakeShared<FJsonValueString>(Call->GetPathName() + TEXT(": function binding arrays exceed 64; not traversed")));
		else
		{
			for (int32 Index = 0; Index < Call->FunctionInputs.Num(); ++Index)
			{
				const auto& Binding = Call->FunctionInputs[Index];
				FJson Entry = MakeShared<FJsonObject>();
				Entry->SetNumberField(TEXT("index"), Index);
				Entry->SetObjectField(TEXT("expression_input_id"), CachedGuid(Binding.ExpressionInputId));
				const auto* Node = CachedResolved(Binding.ExpressionInput, Call->GetPathName() + FString::Printf(TEXT(".FunctionInputs[%d].ExpressionInput"), Index), Errors);
				Entry->SetField(TEXT("expression_input"), CachedIdentity(Node));
				Entry->SetObjectField(TEXT("caller_input"), CachedConnection(Binding.Input, Errors));
				if (Node)
				{
					FJson NodeValue = MakeShared<FJsonObject>();
					NodeValue->SetObjectField(TEXT("id"), CachedGuid(Node->Id));
					NodeValue->SetStringField(TEXT("input_name"), Node->InputName.ToString());
					NodeValue->SetNumberField(TEXT("input_type"), static_cast<int32>(Node->InputType.GetValue()));
					NodeValue->SetBoolField(TEXT("use_preview_value_as_default"), Node->bUsePreviewValueAsDefault);
					NodeValue->SetStringField(TEXT("preview_value_type"), TEXT("FVector4f"));
					const FVector4f& V = Node->PreviewValue;
					NodeValue->SetField(TEXT("preview_value"), CachedVector(V.X, V.Y, V.Z, V.W, Node->GetPathName(), Errors));
					NodeValue->SetObjectField(TEXT("preview"), CachedConnection(Node->Preview, Errors));
					Entry->SetObjectField(TEXT("node"), NodeValue);
				}
				else Entry->SetField(TEXT("node"), MakeShared<FJsonValueNull>());
				FunctionInputs.Add(MakeShared<FJsonValueObject>(Entry));
			}
			TArray<int32> Indices = Item.Value.Array();
			Indices.Sort();
			for (int32 Index : Indices)
			{
				if (!Call->FunctionOutputs.IsValidIndex(Index))
				{
					Errors.Add(MakeShared<FJsonValueString>(Call->GetPathName() + TEXT(": selected function output index unavailable")));
					continue;
				}
				const auto& Binding = Call->FunctionOutputs[Index];
				FJson Entry = MakeShared<FJsonObject>();
				Entry->SetNumberField(TEXT("index"), Index);
				Entry->SetObjectField(TEXT("expression_output_id"), CachedGuid(Binding.ExpressionOutputId));
				const auto& Output = Binding.Output;
				Entry->SetObjectField(TEXT("binding_output_masks"), CachedMasks(Output.Mask, Output.MaskR, Output.MaskG, Output.MaskB, Output.MaskA));
				const auto* Node = CachedResolved(Binding.ExpressionOutput, Call->GetPathName() + FString::Printf(TEXT(".FunctionOutputs[%d].ExpressionOutput"), Index), Errors);
				Entry->SetField(TEXT("expression_output"), CachedIdentity(Node));
				if (Node)
				{
					FJson NodeValue = MakeShared<FJsonObject>();
					NodeValue->SetObjectField(TEXT("id"), CachedGuid(Node->Id));
					NodeValue->SetStringField(TEXT("output_name"), Node->OutputName.ToString());
					NodeValue->SetObjectField(TEXT("a"), CachedConnection(Node->A, Errors));
					Entry->SetObjectField(TEXT("node"), NodeValue);
				}
				else Entry->SetField(TEXT("node"), MakeShared<FJsonValueNull>());
				FunctionOutputs.Add(MakeShared<FJsonValueObject>(Entry));
			}
		}
		Captured->SetArrayField(TEXT("function_inputs"), FunctionInputs);
		Captured->SetArrayField(TEXT("selected_function_outputs"), FunctionOutputs);
		Calls.Add(MakeShared<FJsonValueObject>(Captured));
	}
	Value->SetArrayField(TEXT("calls"), Calls);
	Value->SetArrayField(TEXT("field_errors"), Errors);
	Value->SetStringField(TEXT("state"), Errors.IsEmpty() ? TEXT("cached_facts_captured") : TEXT("partial"));
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
		if (!FJsonSerializer::Serialize(Json, TJsonWriterFactory<>::Create(&Serialized)) || FTCHARToUTF8(*Serialized).Length() > 524288)
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
		Record->SetObjectField(TEXT("cached_function_facts"), CachedFunctionFacts(Material, Data));
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
	const FValues DirtyAfter = DirtyPackages();
	Json->SetArrayField(TEXT("dirty_after"), DirtyAfter);
	if (!DirtyAfter.IsEmpty()) Errors.Add(MakeShared<FJsonValueString>(TEXT("Dirty packages observed after read; no save or rollback attempted.")));
	if (Errors.IsEmpty()) Json->SetStringField(TEXT("state"), TEXT("complete"));
	return Finish();
#else
	return TEXT("{\"state\":\"held\",\"native_invoked\":false,\"errors\":[\"Editor-only material reader\"]}");
#endif
}
