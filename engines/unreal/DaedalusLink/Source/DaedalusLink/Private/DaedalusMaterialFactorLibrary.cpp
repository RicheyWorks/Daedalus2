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
		if (!FJsonSerializer::Serialize(Json, TJsonWriterFactory<>::Create(&Serialized)) || FTCHARToUTF8(*Serialized).Length() > 65536)
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
	const FValues DirtyAfter = DirtyPackages();
	Json->SetArrayField(TEXT("dirty_after"), DirtyAfter);
	if (!DirtyAfter.IsEmpty()) Errors.Add(MakeShared<FJsonValueString>(TEXT("Dirty packages observed after read; no save or rollback attempted.")));
	if (Errors.IsEmpty()) Json->SetStringField(TEXT("state"), TEXT("complete"));
	return Finish();
#else
	return TEXT("{\"state\":\"held\",\"native_invoked\":false,\"errors\":[\"Editor-only material reader\"]}");
#endif
}
