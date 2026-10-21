// SPDX-License-Identifier: MIT
// CONDITIONAL PROPOSAL ONLY. No build, invocation or adoption has occurred.
#include "DaedalusImportedFactorReadLibrary.h"

#if WITH_EDITOR
#include "Dom/JsonObject.h"
#include "Editor.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "FileHelpers.h"
#include "HAL/FileManager.h"
#include "HAL/PlatformMisc.h"
#include "HAL/PlatformProcess.h"
#include "InterchangeAssetImportData.h"
#include "InterchangeMaterialFactoryNode.h"
#include "InterchangeShaderGraphNode.h"
#include "MaterialDomain.h"
#include "Materials/Material.h"
#include "Materials/MaterialExpressionConstant.h"
#include "Materials/MaterialExpressionConstant3Vector.h"
#include "Materials/MaterialExpressionFunctionInput.h"
#include "Materials/MaterialExpressionMaterialFunctionCall.h"
#include "Materials/MaterialExpressionScalarParameter.h"
#include "Materials/MaterialExpressionVectorParameter.h"
#include "Materials/MaterialFunction.h"
#include "Materials/MaterialParameters.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Misc/SecureHash.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonWriter.h"
#include "UObject/Package.h"
#include "UObject/UObjectGlobals.h"

namespace ImportedFactorProposal
{
using J = TSharedRef<FJsonObject>;
using A = TArray<TSharedPtr<FJsonValue>>;
constexpr int32 Budget = 512 * 1024;
static const FString Root = TEXT("/Game/CodexToolEvaluation/EpicIntegrationR1/Import/Prop_PracticeCrate");
static const FString Body = TEXT("/InterchangeAssets/gltf/MaterialBodies/MF_Default_Body.MF_Default_Body");
static const FString SourceSha = TEXT("4e83515ecb6c49139db195354651fd6e23cebdf6150b2011778755ec8c41581f");
static const FString FixtureSha = TEXT("8799e75c65c2828123bd078ee97871703a83f76cca12a19f3ad2d20e832b5a1d");
static const TCHAR* Lanes[] = { TEXT("base_color"), TEXT("metallic"), TEXT("roughness") };
static const TCHAR* Roles[] = { TEXT("BaseColorFactor_RGB"), TEXT("MetallicFactor"), TEXT("RoughnessFactor") };
static const TCHAR* OutputNames[] = { TEXT("BaseColor"), TEXT("Metallic"), TEXT("Roughness") };
static const int32 OutputIndices[] = { 0, 1, 3 };

static void Error(A& Errors, const FString& Message)
{
    if (Errors.Num() < 16) Errors.Add(MakeShared<FJsonValueString>(Message.Left(1024)));
}
static bool Readable(const UObject* Value)
{
    return IsValid(Value) && !Value->HasAnyFlags(RF_NeedLoad | RF_NeedPostLoad);
}
template<class T> static const T* Resolved(const TObjectPtr<T>& Value)
{
    return Value.IsResolved() && Readable(Value.Get()) ? Value.Get() : nullptr;
}
static J Object(const UObject* Value)
{
    J Out = MakeShared<FJsonObject>();
    if (Value)
    {
        Out->SetStringField(TEXT("path"), Value->GetPathName());
        Out->SetStringField(TEXT("class"), Value->GetClass()->GetPathName());
        Out->SetStringField(TEXT("owner"), Value->GetOuter() ? Value->GetOuter()->GetPathName() : FString());
    }
    return Out;
}
static FString Serialize(J Value)
{
    FString Text;
    FJsonSerializer::Serialize(Value, TJsonWriterFactory<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>::Create(&Text));
    return Text;
}
static bool Fits(J Value, int32 Reserve = 8192)
{
    const FString Text = Serialize(Value);
    return FTCHARToUTF8(*Text).Length() <= Budget - Reserve;
}
static bool ValidText(const FString& Value, int32 Max = 512)
{
    return !Value.IsEmpty() && Value.Len() <= Max && !Value.Contains(TEXT("\n")) && !Value.Contains(TEXT("\r"));
}
static bool Hex(const FString& Value, int32 Count)
{
    if (Value.Len() != Count) return false;
    for (TCHAR C : Value) if (!((C >= '0' && C <= '9') || (C >= 'a' && C <= 'f'))) return false;
    return true;
}
static FString Guid(const FGuid& Value) { return Value.ToString(EGuidFormats::Digits).ToLower(); }
static J Source()
{
    J Out = MakeShared<FJsonObject>(); Out->SetNumberField(TEXT("bytes"), 18576); Out->SetStringField(TEXT("sha256"), SourceSha); return Out;
}
static A Dirty()
{
    TArray<UPackage*> Packages;
    UEditorLoadingAndSavingUtils::GetDirtyMapPackages(Packages);
    UEditorLoadingAndSavingUtils::GetDirtyContentPackages(Packages);
    TArray<FString> Names;
    for (const UPackage* P : Packages) if (P) Names.AddUnique(P->GetName());
    Names.Sort(); A Out;
    for (const FString& Name : Names) Out.Add(MakeShared<FJsonValueString>(Name));
    return Out;
}
static bool Mask(J& Out, int32 M, int32 R, int32 G, int32 B, int32 Alpha)
{
    Out = MakeShared<FJsonObject>();
    const int32 Values[] = { M, R, G, B, Alpha };
    const TCHAR* Keys[] = { TEXT("mask"), TEXT("r"), TEXT("g"), TEXT("b"), TEXT("a") };
    for (int32 I=0; I<5; ++I)
    {
        if (Values[I] != 0 && Values[I] != 1) return false;
        Out->SetNumberField(Keys[I], Values[I]);
    }
    return true;
}
static bool Connection(const FExpressionInput& Input, J Out, const UMaterial* Material, A& Errors)
{
    const UMaterialExpression* Expr = Input.Expression;
    if (!Readable(Expr) || Expr->GetOuter() != Material || Input.OutputIndex != 0 || !Expr->Outputs.IsValidIndex(Input.OutputIndex))
    { Error(Errors, TEXT("Direct caller primary output/owner unavailable; no graph fallback")); return false; }
    const FExpressionOutput& Selected = Expr->Outputs[Input.OutputIndex];
    J Raw = MakeShared<FJsonObject>(), Cached = MakeShared<FJsonObject>();
    if (!Mask(Raw, Input.Mask, Input.MaskR, Input.MaskG, Input.MaskB, Input.MaskA)
        || !Mask(Cached, Selected.Mask, Selected.MaskR, Selected.MaskG, Selected.MaskB, Selected.MaskA))
    { Error(Errors, TEXT("Unsupported nonbinary cached masks")); return false; }
    Out->SetBoolField(TEXT("expression_present"), true); Out->SetObjectField(TEXT("expression"), Object(Expr));
    Out->SetNumberField(TEXT("output_index"), Input.OutputIndex); Out->SetBoolField(TEXT("selected_output_valid"), true);
    Out->SetObjectField(TEXT("raw_masks"), Raw); Out->SetObjectField(TEXT("selected_output_masks"), Cached);
    Out->SetObjectField(TEXT("effective_masks"), Input.Mask ? Raw : Cached);
    return true;
}
static TSharedPtr<FJsonValue> Color(const FLinearColor& Value)
{
    if (!FMath::IsFinite(Value.R) || !FMath::IsFinite(Value.G) || !FMath::IsFinite(Value.B) || !FMath::IsFinite(Value.A)) return nullptr;
    A Values; for (float V : {Value.R,Value.G,Value.B,Value.A}) Values.Add(MakeShared<FJsonValueNumber>(V));
    return MakeShared<FJsonValueArray>(Values);
}
static J Info(const FMaterialParameterInfo& Value)
{
    J Out = MakeShared<FJsonObject>(); Out->SetStringField(TEXT("name"), Value.Name.ToString());
    const TCHAR* Association = Value.Association == GlobalParameter ? TEXT("GlobalParameter") : Value.Association == LayerParameter ? TEXT("LayerParameter") : TEXT("BlendParameter");
    Out->SetStringField(TEXT("association"), Association); Out->SetNumberField(TEXT("index"), Value.Index); return Out;
}
static bool Parameter(const UMaterial* Material, const UMaterialExpressionParameter* Leaf, bool bVector, J Out, A& Errors)
{
    TArray<FMaterialParameterInfo> Infos; TArray<FGuid> Ids;
    if (bVector) Material->GetAllVectorParameterInfo(Infos, Ids); else Material->GetAllScalarParameterInfo(Infos, Ids);
    if (Infos.Num() < 1 || Infos.Num() > 128 || Infos.Num() != Ids.Num() || !Leaf->ExpressionGUID.IsValid())
    { Error(Errors, TEXT("Complete bounded parameter info/GUID inventory unavailable")); return false; }
    A Entries; TSet<FString> Seen; int32 Match = INDEX_NONE, GuidCount = 0;
    for (int32 I=0; I<Infos.Num(); ++I)
    {
        const FMaterialParameterInfo& P = Infos[I];
        const FString Key = P.Name.ToString() + TEXT("|") + LexToString(static_cast<int32>(P.Association)) + TEXT("|") + LexToString(P.Index);
        if (Seen.Contains(Key) || P.Name.IsNone() || !Ids[I].IsValid()
            || (P.Association!=GlobalParameter && P.Association!=LayerParameter && P.Association!=BlendParameter)
            || P.Index<INDEX_NONE || P.Index>128)
        { Error(Errors,TEXT("Ambiguous/unsupported parameter inventory")); return false; }
        Seen.Add(Key); J Entry = MakeShared<FJsonObject>(); Entry->SetObjectField(TEXT("parameter_info"), Info(P));
        Entry->SetStringField(TEXT("expression_guid"), Guid(Ids[I])); Entries.Add(MakeShared<FJsonValueObject>(Entry));
        if (Ids[I] == Leaf->ExpressionGUID) { ++GuidCount; Match=I; }
    }
    if (GuidCount != 1 || Match == INDEX_NONE || Infos[Match].Name != Leaf->ParameterName
        || Infos[Match].Association != GlobalParameter || Infos[Match].Index != INDEX_NONE)
    { Error(Errors,TEXT("Selected leaf parameter is not uniquely bound in exact global context")); return false; }
    FMaterialParameterMetadata Metadata;
    const EMaterialParameterType Type = bVector ? EMaterialParameterType::Vector : EMaterialParameterType::Scalar;
    const bool bFound = Material->GetParameterValue(Type, FMemoryImageMaterialParameterInfo(Infos[Match]), Metadata, EMaterialGetParameterValueFlags::Default);
    if (!bFound || Metadata.Value.Type != Type || Metadata.ExpressionGuid != Leaf->ExpressionGUID || Metadata.bOverride || Metadata.PrimitiveDataIndex != INDEX_NONE || Metadata.bDynamicSwitchParameter)
    { Error(Errors,TEXT("Parameter query failed/overridden/primitive/context ambiguous; no default substitution")); return false; }
    TSharedPtr<FJsonValue> Value = bVector ? Color(Metadata.Value.AsLinearColor()) : TSharedPtr<FJsonValue>(MakeShared<FJsonValueNumber>(Metadata.Value.AsScalar()));
    if (!Value || (!bVector && !FMath::IsFinite(Metadata.Value.AsScalar()))) { Error(Errors,TEXT("Nonfinite parameter value")); return false; }
    J Enum = MakeShared<FJsonObject>(); Enum->SetBoolField(TEXT("complete"), true); Enum->SetNumberField(TEXT("info_count"), Infos.Num());
    Enum->SetNumberField(TEXT("guid_count"), Ids.Num()); Enum->SetArrayField(TEXT("entries"), Entries);
    J Meta = MakeShared<FJsonObject>(); Meta->SetStringField(TEXT("expression_guid"), Guid(Metadata.ExpressionGuid));
    Meta->SetBoolField(TEXT("b_override"), Metadata.bOverride); Meta->SetNumberField(TEXT("primitive_data_index"), Metadata.PrimitiveDataIndex);
    Meta->SetBoolField(TEXT("dynamic_switch_parameter"), Metadata.bDynamicSwitchParameter); Meta->SetField(TEXT("value"), Value);
    J Query = MakeShared<FJsonObject>(); Query->SetStringField(TEXT("api"), TEXT("UMaterialInterface::GetParameterValue"));
    Query->SetStringField(TEXT("flags"), TEXT("Default")); Query->SetBoolField(TEXT("succeeded"), bFound);
    Query->SetStringField(TEXT("interface_path"), Material->GetPathName()); Query->SetObjectField(TEXT("parameter_info"), Info(Infos[Match]));
    Query->SetStringField(TEXT("type"), bVector ? TEXT("Vector") : TEXT("Scalar")); Query->SetObjectField(TEXT("metadata"), Meta);
    Out->SetStringField(TEXT("type"), bVector ? TEXT("Vector") : TEXT("Scalar")); Out->SetObjectField(TEXT("parameter_info"), Info(Infos[Match]));
    Out->SetObjectField(TEXT("enumeration"), Enum); Out->SetObjectField(TEXT("query"), Query); return true;
}
static bool Leaf(const UMaterial* Material, const FExpressionInput& Input, bool bVector, J Out, A& Errors)
{
    const UMaterialExpression* Expr=Input.Expression;
    Out->SetStringField(TEXT("expression_path"), Expr->GetPathName());
    if (bVector && Expr->GetClass()==UMaterialExpressionConstant3Vector::StaticClass())
    {
        TSharedPtr<FJsonValue> Value=Color(CastChecked<UMaterialExpressionConstant3Vector>(Expr)->Constant);
        if (!Value) { Error(Errors,TEXT("Nonfinite Constant3Vector")); return false; }
        Out->SetStringField(TEXT("value_kind"),TEXT("FLinearColor")); Out->SetField(TEXT("value"),Value); return true;
    }
    if (!bVector && Expr->GetClass()==UMaterialExpressionConstant::StaticClass())
    {
        const float V=CastChecked<UMaterialExpressionConstant>(Expr)->R;
        if (!FMath::IsFinite(V)) { Error(Errors,TEXT("Nonfinite Constant")); return false; }
        Out->SetStringField(TEXT("value_kind"),TEXT("float32")); Out->SetNumberField(TEXT("value"),V); return true;
    }
    const bool bParameter = Expr->GetClass()==(bVector ? UMaterialExpressionVectorParameter::StaticClass() : UMaterialExpressionScalarParameter::StaticClass());
    if (!bParameter) { Error(Errors,TEXT("Unsupported direct factor leaf; no traversal/evaluation")); return false; }
    if ((bVector && CastChecked<UMaterialExpressionVectorParameter>(Expr)->bUseCustomPrimitiveData)
        || (!bVector && CastChecked<UMaterialExpressionScalarParameter>(Expr)->bUseCustomPrimitiveData))
    { Error(Errors,TEXT("Custom primitive factor is unsupported")); return false; }
    const auto* Param=CastChecked<UMaterialExpressionParameter>(Expr); J Proof=MakeShared<FJsonObject>();
    Out->SetStringField(TEXT("expression_guid"),Guid(Param->ExpressionGUID));
    if (!Parameter(Material,Param,bVector,Proof,Errors)) return false;
    Out->SetObjectField(TEXT("parameter"),Proof); return true;
}

static bool Provenance(const UMaterial* Material, const FString& Name, J Out, A& Errors, int32& ImportGetterCalls)
{
    const UInterchangeAssetImportData* Data=Cast<UInterchangeAssetImportData>(Resolved(Material->AssetImportData));
    if (!Data || Data->GetOuter()!=Material || Data->SourceData.SourceFiles.Num()!=1 || !Data->SourceData.SourceFiles[0].FileHash.IsValid())
    { Error(Errors,TEXT("Typed original import data/source digest unavailable")); return false; }
    const FString Filename=Data->ScriptGetFirstFilename(); TArray<uint8> Bytes;
    if (!ValidText(Filename,1024) || FPaths::IsRelative(Filename) || IFileManager::Get().FileSize(*Filename)!=18576
        || !FFileHelper::LoadFileToArray(Bytes,*Filename) || Bytes.Num()!=18576)
    { Error(Errors,TEXT("Current resolved source bytes unavailable; no alternate path")); return false; }
    FSHA256Signature Signature;
    if (!FPlatformMisc::GetSHA256Signature(Bytes.GetData(),static_cast<uint32>(Bytes.Num()),Signature) || Signature.ToString().ToLower()!=SourceSha)
    { Error(Errors,TEXT("Current source SHA256 differs")); return false; }
    // OFFICIAL GETTER: may deserialize persisted import nodes to transient objects.
    // No private-cache inspection, Serialize/ExportText snapshot, cache refresh or setter.
    ++ImportGetterCalls; const UInterchangeBaseNodeContainer* Container=Data->GetNodeContainer();
    ++ImportGetterCalls; const auto* Factory=Cast<UInterchangeMaterialFactoryNode>(Data->GetStoredFactoryNode(Data->NodeUniqueID));
    if (!Readable(Container) || !Readable(Factory) || Factory->GetUniqueID()!=Data->NodeUniqueID)
    { Error(Errors,TEXT("Stored typed import factory/container unavailable")); return false; }
    TArray<FString> Targets; Factory->GetTargetNodeUids(Targets);
    if (Targets.Num()<1 || Targets.Num()>16) { Error(Errors,TEXT("Stored target inventory outside bound")); return false; }
    const UInterchangeShaderGraphNode* Graph=nullptr; TSet<FString> Seen;
    for (const FString& Target:Targets)
    {
        if (!ValidText(Target) || Seen.Contains(Target)) { Error(Errors,TEXT("Ambiguous stored target UID")); return false; }
        Seen.Add(Target);
        ++ImportGetterCalls; const auto* Candidate=Cast<UInterchangeShaderGraphNode>(Data->GetStoredNode(Target));
        if (Candidate && Candidate->GetDisplayLabel()==Name)
        { if (Graph) { Error(Errors,TEXT("Ambiguous source material graph")); return false; } Graph=Candidate; }
    }
    if (!Readable(Graph)) { Error(Errors,TEXT("Source material graph not bound to factory")); return false; }
    FString FunctionUid; J Connections=MakeShared<FJsonObject>();
    for (int32 Lane=0;Lane<3;++Lane)
    {
        FString Connected,Output;
        if (!UInterchangeShaderPortsAPI::GetInputConnection(Graph,OutputNames[Lane],Connected,Output) || Output!=OutputNames[Lane]
            || (Lane>0 && FunctionUid!=Connected)) { Error(Errors,TEXT("Stored root property/function mapping unavailable")); return false; }
        FunctionUid=Connected; J C=MakeShared<FJsonObject>(); C->SetStringField(TEXT("connected_shader_uid"),Connected);
        C->SetStringField(TEXT("output_name"),Output); Connections->SetObjectField(Lanes[Lane],C);
    }
    ++ImportGetterCalls; const auto* Function=Cast<UInterchangeFunctionCallShaderNode>(Data->GetStoredNode(FunctionUid)); FString FunctionPath;
    if (!Readable(Function) || FunctionUid==Graph->GetUniqueID() || !Function->GetCustomMaterialFunction(FunctionPath) || FunctionPath!=Body)
    { Error(Errors,TEXT("Stored exact function shader unavailable")); return false; }
    J Attributes=MakeShared<FJsonObject>();
    for (int32 Lane=0;Lane<3;++Lane)
    {
        J Attribute=MakeShared<FJsonObject>(); const FString Key=UInterchangeShaderPortsAPI::MakeInputValueKey(Roles[Lane]);
        Attribute->SetStringField(TEXT("input_name"),Roles[Lane]); Attribute->SetBoolField(TEXT("read_succeeded"),true);
        if (Lane==0)
        {
            FLinearColor Value;
            if (!Function->GetLinearColorAttribute(Key,Value) || !Color(Value)) { Error(Errors,TEXT("Stored typed RGB factor absent")); return false; }
            Attribute->SetStringField(TEXT("attribute_kind"),TEXT("LinearColor")); Attribute->SetField(TEXT("value"),Color(Value));
        }
        else
        {
            float Value;
            if (!Function->GetFloatAttribute(Key,Value) || !FMath::IsFinite(Value)) { Error(Errors,TEXT("Stored typed scalar factor absent")); return false; }
            Attribute->SetStringField(TEXT("attribute_kind"),TEXT("Float")); Attribute->SetNumberField(TEXT("value"),Value);
        }
        Attributes->SetObjectField(Lanes[Lane],Attribute);
    }
    Out->SetObjectField(TEXT("asset_import_data"),Object(Data)); Out->SetStringField(TEXT("first_filename"),Filename);
    Out->SetStringField(TEXT("current_source_filename"),Filename); Out->SetObjectField(TEXT("current_source_file"),Source());
    Out->SetStringField(TEXT("source_material_name"),Name); J Stored=MakeShared<FJsonObject>();
    Stored->SetStringField(TEXT("algorithm"),TEXT("MD5")); Stored->SetStringField(TEXT("hex"),LexToString(Data->SourceData.SourceFiles[0].FileHash).ToLower());
    Out->SetObjectField(TEXT("stored_source_digest"),Stored); Out->SetStringField(TEXT("asset_node_unique_id"),Data->NodeUniqueID);
    Out->SetStringField(TEXT("factory_uid"),Factory->GetUniqueID()); Out->SetStringField(TEXT("factory_node_cast"),TEXT("UInterchangeMaterialFactoryNode"));
    A TargetValues; for (const FString& T:Targets) TargetValues.Add(MakeShared<FJsonValueString>(T)); Out->SetArrayField(TEXT("factory_target_uids"),TargetValues);
    Out->SetStringField(TEXT("shader_graph_uid"),Graph->GetUniqueID()); Out->SetStringField(TEXT("shader_graph_label"),Graph->GetDisplayLabel());
    Out->SetStringField(TEXT("function_shader_uid"),FunctionUid); Out->SetStringField(TEXT("function_node_cast"),TEXT("UInterchangeFunctionCallShaderNode"));
    Out->SetStringField(TEXT("function_path"),FunctionPath); Out->SetObjectField(TEXT("graph_property_connections"),Connections);
    Out->SetObjectField(TEXT("factor_attributes"),Attributes); return true;
}

static bool Material(UMaterial* Mat,const UStaticMesh* Mesh,const FString& Name,J Out,A& Errors,int32& ImportGetterCalls,bool bIncludeProvenance=true)
{
    int32 SlotMatches=0;
    if (Mesh->GetStaticMaterials().Num()>32) { Error(Errors,TEXT("Mesh slot bound exceeded")); return false; }
    for (const FStaticMaterial& Slot:Mesh->GetStaticMaterials())
        if (Slot.MaterialSlotName==FName(*Name) && Resolved(Slot.MaterialInterface)==Mat) ++SlotMatches;
    if (SlotMatches!=1 || Mat->GetBlendMode()!=BLEND_Opaque || Mat->MaterialDomain!=MD_Surface || !Mat->IsTwoSided())
    { Error(Errors,TEXT("Original mesh slot/opaque/two-sided context differs")); return false; }
    const UMaterialEditorOnlyData* Data=Mat->GetEditorOnlyData();
    if (!Readable(Data) || Mat->bUseMaterialAttributes || Mat->HasSubstrateFrontMaterialConnected())
    { Error(Errors,TEXT("Unsupported material attributes/front-material route")); return false; }
    const auto* Call=Cast<UMaterialExpressionMaterialFunctionCall>(Data->BaseColor.Expression);
    if (!Readable(Call) || Call->GetClass()!=UMaterialExpressionMaterialFunctionCall::StaticClass() || Call->GetOuter()!=Mat)
    { Error(Errors,TEXT("Current root caller differs")); return false; }
    const auto* Fn=Cast<UMaterialFunction>(Resolved(Call->MaterialFunction));
    if (!Fn || Fn->GetClass()!=UMaterialFunction::StaticClass() || Fn->GetPathName()!=Body || Call->FunctionInputs.Num()<1
        || Call->FunctionInputs.Num()>128 || Call->FunctionOutputs.Num()>16)
    { Error(Errors,TEXT("Exact cached function/counts unavailable")); return false; }
    J Current=MakeShared<FJsonObject>(),Bindings=MakeShared<FJsonObject>();
    const FExpressionInput* Typed[]={&Data->BaseColor,&Data->Metallic,&Data->Roughness};
    const EMaterialProperty Properties[]={MP_BaseColor,MP_Metallic,MP_Roughness};
    const bool Constants[]={!!Data->BaseColor.UseConstant,!!Data->Metallic.UseConstant,!!Data->Roughness.UseConstant};
    for (int32 Lane=0;Lane<3;++Lane)
    {
        const FExpressionInput* Input=Mat->GetExpressionInputForProperty(Properties[Lane]); const int32 Index=OutputIndices[Lane];
        if (Input!=Typed[Lane] || Constants[Lane] || Input->Expression!=Call || Input->OutputIndex!=Index || !Call->Outputs.IsValidIndex(Index)
            || Call->Outputs[Index].OutputName.ToString()!=OutputNames[Lane]) { Error(Errors,TEXT("Current property/caller output binding differs")); return false; }
        J Raw=MakeShared<FJsonObject>(),Selected=MakeShared<FJsonObject>(); const FExpressionOutput& O=Call->Outputs[Index];
        if (!Mask(Raw,Input->Mask,Input->MaskR,Input->MaskG,Input->MaskB,Input->MaskA) || !Mask(Selected,O.Mask,O.MaskR,O.MaskG,O.MaskB,O.MaskA))
        { Error(Errors,TEXT("Unsupported root masks")); return false; }
        J B=MakeShared<FJsonObject>(); B->SetBoolField(TEXT("current_input_present"),true); B->SetBoolField(TEXT("uses_input_constant"),Constants[Lane]);
        B->SetBoolField(TEXT("current_pointer_equal"),Input==Typed[Lane]); B->SetStringField(TEXT("expression_path"),Call->GetPathName());
        B->SetNumberField(TEXT("output_index"),Input->OutputIndex); B->SetBoolField(TEXT("selected_output_valid"),true);
        B->SetStringField(TEXT("selected_output_name"),O.OutputName.ToString()); B->SetObjectField(TEXT("raw_masks"),Raw);
        B->SetObjectField(TEXT("selected_output_masks"),Selected); B->SetObjectField(TEXT("effective_masks"),Input->Mask?Raw:Selected); Bindings->SetObjectField(Lanes[Lane],B);
    }
    static const TCHAR* Types[]={TEXT("Scalar"),TEXT("Vector2"),TEXT("Vector3"),TEXT("Vector4"),TEXT("Texture2D"),TEXT("TextureCube"),TEXT("Texture2DArray"),TEXT("VolumeTexture"),TEXT("StaticBool"),TEXT("MaterialAttributes"),TEXT("TextureExternal"),TEXT("Bool"),TEXT("Substrate")};
    const auto Expressions=Fn->GetExpressions();
    if (Expressions.Num()>4096) { Error(Errors,TEXT("Cached function expression identity bound exceeded")); return false; }
    A Roster; TSet<FString> Names,Ids,Paths; int32 RoleIndex[]={INDEX_NONE,INDEX_NONE,INDEX_NONE};
    for (int32 I=0;I<Call->FunctionInputs.Num();++I)
    {
        const FFunctionExpressionInput& Entry=Call->FunctionInputs[I]; const auto* Node=Resolved(Entry.ExpressionInput);
        int32 PointerCount=0; for (const auto& Ref:Expressions) if (Ref.IsResolved() && Ref.Get()==Node) ++PointerCount;
        const int32 Type=Node?static_cast<int32>(Node->InputType):INDEX_NONE;
        if (!Node || Node->GetClass()!=UMaterialExpressionFunctionInput::StaticClass() || Node->GetOuter()!=Fn || PointerCount!=1
            || !Node->Id.IsValid() || Node->Id!=Entry.ExpressionInputId || Type<0 || Type>=13 || Node->InputName.IsNone())
        { Error(Errors,TEXT("Unpaired/unknown cached function input")); return false; }
        const FString NodeId=Guid(Node->Id),InputName=Node->InputName.ToString(),Path=Node->GetPathName();
        if (!ValidText(InputName,128) || !ValidText(Path) || Names.Contains(InputName) || Ids.Contains(NodeId) || Paths.Contains(Path))
        { Error(Errors,TEXT("Ambiguous named function roster")); return false; }
        Names.Add(InputName); Ids.Add(NodeId); Paths.Add(Path); J R=MakeShared<FJsonObject>(); R->SetNumberField(TEXT("index"),I);
        R->SetStringField(TEXT("input_name"),InputName); R->SetStringField(TEXT("input_type"),FString(TEXT("FunctionInput_"))+Types[Type]);
        R->SetNumberField(TEXT("input_type_value"),Type); R->SetObjectField(TEXT("node"),Object(Node)); R->SetStringField(TEXT("node_guid"),NodeId);
        R->SetStringField(TEXT("caller_input_guid"),Guid(Entry.ExpressionInputId)); R->SetBoolField(TEXT("cached_pointer_equal"),true);
        Roster.Add(MakeShared<FJsonValueObject>(R));
        for (int32 Lane=0;Lane<3;++Lane) if (InputName==Roles[Lane]) RoleIndex[Lane]=I;
        Current->SetArrayField(TEXT("input_roster"),Roster);
        if (!Fits(Current)) { Error(Errors,TEXT("Prospective roster UTF8 budget exceeded")); return false; }
    }
    J Factors=MakeShared<FJsonObject>();
    for (int32 Lane=0;Lane<3;++Lane)
    {
        if (RoleIndex[Lane]==INDEX_NONE) { Error(Errors,TEXT("Original factor role absent from complete current roster")); return false; }
        const FFunctionExpressionInput& Entry=Call->FunctionInputs[RoleIndex[Lane]]; const auto* Node=Resolved(Entry.ExpressionInput);
        if (Node->InputType!=(Lane==0?FunctionInput_Vector3:FunctionInput_Scalar)) { Error(Errors,TEXT("Factor lane type differs")); return false; }
        J C=MakeShared<FJsonObject>(),L=MakeShared<FJsonObject>();
        if (!Connection(Entry.Input,C,Mat,Errors) || !Leaf(Mat,Entry.Input,Lane==0,L,Errors)) return false;
        J F=MakeShared<FJsonObject>(); F->SetNumberField(TEXT("roster_index"),RoleIndex[Lane]); F->SetStringField(TEXT("input_node_guid"),Guid(Node->Id));
        F->SetStringField(TEXT("caller_input_guid"),Guid(Entry.ExpressionInputId)); F->SetBoolField(TEXT("current_pointer_equal"),true);
        F->SetObjectField(TEXT("connection"),C); F->SetObjectField(TEXT("leaf"),L); Factors->SetObjectField(Lanes[Lane],F);
    }
    J P=MakeShared<FJsonObject>(); if (bIncludeProvenance && !Provenance(Mat,Name,P,Errors,ImportGetterCalls)) return false;
    Current->SetObjectField(TEXT("caller"),Object(Call)); Current->SetObjectField(TEXT("function"),Object(Fn));
    Current->SetObjectField(TEXT("property_bindings"),Bindings); Current->SetNumberField(TEXT("input_count"),Call->FunctionInputs.Num());
    Current->SetBoolField(TEXT("input_roster_complete"),true);
    Out->SetStringField(TEXT("source_material_name"),Name); Out->SetObjectField(TEXT("material"),Object(Mat)); Out->SetStringField(TEXT("mesh_path"),Mesh->GetPathName());
    Out->SetStringField(TEXT("slot_name"),Name); Out->SetStringField(TEXT("slot_material_path"),Mat->GetPathName()); Out->SetBoolField(TEXT("two_sided"),Mat->IsTwoSided());
    Out->SetStringField(TEXT("blend_mode"),TEXT("BLEND_Opaque")); Out->SetStringField(TEXT("material_domain"),TEXT("MD_Surface"));
    J Context=MakeShared<FJsonObject>(); Context->SetStringField(TEXT("interface_path"),Mat->GetPathName()); Context->SetStringField(TEXT("exact_class"),Mat->GetClass()->GetPathName());
    Context->SetBoolField(TEXT("is_instance"),false); Context->SetArrayField(TEXT("parent_chain"),A()); Out->SetObjectField(TEXT("interface_context"),Context);
    if (bIncludeProvenance) Out->SetObjectField(TEXT("import_provenance"),P); Out->SetObjectField(TEXT("current_call"),Current); Out->SetObjectField(TEXT("factors"),Factors); return Fits(Out);
}
} // namespace ImportedFactorProposal
#endif

FString UDaedalusImportedFactorReadLibrary::ReadImportedFactorBindings(const TArray<FString>& MaterialObjectPaths,
    const FString& AllowedPackageRoot, const FString& PolicyId)
{
#if WITH_EDITOR
    using namespace ImportedFactorProposal;
    J Out=MakeShared<FJsonObject>(); A Errors,Rows; int32 ImportGetterCalls=0;
    Out->SetStringField(TEXT("schema"),TEXT("daedalus.imported-factor-native-fragment.v1"));
    Out->SetStringField(TEXT("target_capture_schema"),TEXT("daedalus.imported-factor-facts.v1"));
    Out->SetStringField(TEXT("criterion"),TEXT("IMPORTED_FACTOR_RETENTION_ONLY")); Out->SetStringField(TEXT("policy_id"),PolicyId);
    Out->SetBoolField(TEXT("native_invoked"),true); Out->SetBoolField(TEXT("cancelled"),false);
    Out->SetStringField(TEXT("evidence_kind"),TEXT("native_capture")); Out->SetObjectField(TEXT("source"),Source()); Out->SetStringField(TEXT("fixture_sha256"),FixtureSha);
    J Observation=MakeShared<FJsonObject>(); Observation->SetStringField(TEXT("capture_id"),FGuid::NewGuid().ToString(EGuidFormats::DigitsWithHyphens).ToLower());
    Observation->SetStringField(TEXT("observed_at_utc"),FDateTime::UtcNow().ToIso8601()); Observation->SetNumberField(TEXT("editor_pid"),FPlatformProcess::GetCurrentProcessId());
    Observation->SetStringField(TEXT("project_path"),FPaths::ConvertRelativePathToFull(FPaths::GetProjectFilePath())); Out->SetObjectField(TEXT("native_observation"),Observation);
    static bool Active=false;
    if (!IsInGameThread() || Active || !GEditor || GEditor->PlayWorld || !GEditor->GetEditorWorldContext().World()
        || GEditor->GetEditorWorldContext().World()->GetPathName()!=TEXT("/Game/Daedalus/DaedalusWorld.DaedalusWorld")
        || AllowedPackageRoot!=Root || !Hex(PolicyId,64) || MaterialObjectPaths.Num()!=2)
    { ImportedFactorProposal::Error(Errors,TEXT("Closed native editor/caller/scope admission refused")); }
    else
    {
        TGuardValue<bool> Guard(Active,true); const A Before=Dirty(); Out->SetArrayField(TEXT("dirty_before"),Before);
        const FString MeshPath=Root+TEXT("/Prop_PracticeCrate.Prop_PracticeCrate");
        const UStaticMesh* Mesh=Cast<UStaticMesh>(StaticFindObject(UStaticMesh::StaticClass(),nullptr,*MeshPath));
        if (!Readable(Mesh) || Before.Num()!=0) ImportedFactorProposal::Error(Errors,TEXT("Original mesh absent/incomplete or dirty; no load"));
        for (int32 I=0;Errors.Num()==0 && I<2;++I)
        {
            const FString Name=FString::Printf(TEXT("Prop_PracticeCrate_M%d"),I); const FString Path=Root+TEXT("/")+Name+TEXT(".")+Name;
            UMaterial* Mat=Cast<UMaterial>(StaticFindObject(UMaterial::StaticClass(),nullptr,*Path));
            if (MaterialObjectPaths[I]!=Path || !Readable(Mat) || Mat->GetClass()!=UMaterial::StaticClass()) { ImportedFactorProposal::Error(Errors,TEXT("Exact loaded original material unavailable")); break; }
            J Row=MakeShared<FJsonObject>(); if (!Material(Mat,Mesh,Name,Row,Errors,ImportGetterCalls)) { if (!Errors.Num()) ImportedFactorProposal::Error(Errors,TEXT("Material payload budget exceeded")); break; }
            A Proposed=Rows; Proposed.Add(MakeShared<FJsonValueObject>(Row)); Out->SetArrayField(TEXT("materials"),Proposed);
            if (!Fits(Out)) { Out->SetArrayField(TEXT("materials"),Rows); ImportedFactorProposal::Error(Errors,TEXT("Prospective total UTF8 budget exceeded; no false complete prefix")); break; }
            Rows=MoveTemp(Proposed);
        }
        const A After=Dirty(); Out->SetArrayField(TEXT("dirty_after"),After); if (After.Num()!=0) ImportedFactorProposal::Error(Errors,TEXT("Dirty state changed during factual read"));
    }
    Out->SetArrayField(TEXT("materials"),Rows); Out->SetArrayField(TEXT("errors"),Errors);
    Out->SetStringField(TEXT("native_fields_state"),Errors.Num()==0 && Rows.Num()==2?TEXT("complete"):TEXT("held"));
    Out->SetStringField(TEXT("state"),Errors.Num()==0 && Rows.Num()==2?TEXT("native_fields_complete_host_evidence_pending"):TEXT("held"));
    Out->SetNumberField(TEXT("explicit_asset_load_requests"),0); Out->SetNumberField(TEXT("authored_material_write_requests"),0);
    Out->SetNumberField(TEXT("material_cache_refreshes"),0); Out->SetNumberField(TEXT("evaluations"),0); Out->SetNumberField(TEXT("compilations"),0);
    J GetterEffects=MakeShared<FJsonObject>(); GetterEffects->SetNumberField(TEXT("getter_invocations"),ImportGetterCalls);
    GetterEffects->SetField(TEXT("transient_deserialization_observed"),MakeShared<FJsonValueNull>());
    GetterEffects->SetField(TEXT("legacy_migration_observed"),MakeShared<FJsonValueNull>());
    GetterEffects->SetBoolField(TEXT("private_cache_unchanged_claimed"),false); Out->SetObjectField(TEXT("official_import_metadata_effects"),GetterEffects);
    Out->SetStringField(TEXT("official_import_getter_effects"),TEXT("May materialize transient persisted import nodes; legacy migration branch not publicly observable. Report separately from material CachedExpressionData refresh. Host must verify original graph/factors/parameters/world/camera/selection/dirty state and saved files; no Serialize/ExportText/private access used."));
    Out->SetBoolField(TEXT("root_output_equivalence_proven"),false); Out->SetBoolField(TEXT("native_runtime_qualified"),false);
    if (!Fits(Out,0)) return TEXT("{\"schema\":\"daedalus.imported-factor-native-fragment.v1\",\"state\":\"held\",\"native_fields_state\":\"held\",\"errors\":[\"Terminal UTF8 budget exceeded\"]}");
    return ImportedFactorProposal::Serialize(Out);
#else
    (void)MaterialObjectPaths; (void)AllowedPackageRoot; (void)PolicyId;
    return TEXT("{\"schema\":\"daedalus.imported-factor-native-fragment.v1\",\"state\":\"held\",\"errors\":[\"Editor-only producer unavailable\"]}");
#endif
}

FString UDaedalusImportedFactorReadLibrary::ReadImportedFactorProtection(
    const TArray<FString>& MaterialObjectPaths, const FString& AllowedPackageRoot)
{
#if WITH_EDITOR
    using namespace ImportedFactorProposal;
    J Out=MakeShared<FJsonObject>(), Snapshot=MakeShared<FJsonObject>();
    A Errors,Rows; int32 ImportGetterCalls=0;
    Out->SetStringField(TEXT("schema"),TEXT("daedalus.imported-factor-protection.v1"));
    Out->SetBoolField(TEXT("native_invoked"),true);
    J Observation=MakeShared<FJsonObject>();
    Observation->SetStringField(TEXT("capture_id"),FGuid::NewGuid().ToString(EGuidFormats::DigitsWithHyphens).ToLower());
    Observation->SetStringField(TEXT("observed_at_utc"),FDateTime::UtcNow().ToIso8601());
    Observation->SetNumberField(TEXT("editor_pid"),FPlatformProcess::GetCurrentProcessId());
    Observation->SetStringField(TEXT("project_path"),FPaths::ConvertRelativePathToFull(FPaths::GetProjectFilePath()));
    Out->SetObjectField(TEXT("native_observation"),Observation);
    static bool Active=false;
    if (!IsInGameThread() || Active || !GEditor || GEditor->PlayWorld ||
        !GEditor->GetEditorWorldContext().World() ||
        GEditor->GetEditorWorldContext().World()->GetPathName()!=TEXT("/Game/Daedalus/DaedalusWorld.DaedalusWorld") ||
        AllowedPackageRoot!=Root || MaterialObjectPaths.Num()!=2)
        ImportedFactorProposal::Error(Errors,TEXT("Closed protection-reader scope refused"));
    else
    {
        TGuardValue<bool> Guard(Active,true);
        const A Before=Dirty(); Out->SetArrayField(TEXT("dirty_before"),Before);
        const FString MeshPath=Root+TEXT("/Prop_PracticeCrate.Prop_PracticeCrate");
        const UStaticMesh* Mesh=Cast<UStaticMesh>(StaticFindObject(UStaticMesh::StaticClass(),nullptr,*MeshPath));
        if (!Readable(Mesh) || Before.Num()!=0)
            ImportedFactorProposal::Error(Errors,TEXT("Original mesh absent/incomplete or dirty; no load"));
        for (int32 I=0; Errors.Num()==0 && I<2; ++I)
        {
            const FString Name=FString::Printf(TEXT("Prop_PracticeCrate_M%d"),I);
            const FString Path=Root+TEXT("/")+Name+TEXT(".")+Name;
            UMaterial* Mat=Cast<UMaterial>(StaticFindObject(UMaterial::StaticClass(),nullptr,*Path));
            if (MaterialObjectPaths[I]!=Path || !Readable(Mat) || Mat->GetClass()!=UMaterial::StaticClass())
            { ImportedFactorProposal::Error(Errors,TEXT("Exact loaded original material unavailable")); break; }
            J Row=MakeShared<FJsonObject>();
            if (!Material(Mat,Mesh,Name,Row,Errors,ImportGetterCalls,false))
            { if (!Errors.Num()) ImportedFactorProposal::Error(Errors,TEXT("Protection row budget exceeded")); break; }
            Rows.Add(MakeShared<FJsonValueObject>(Row));
            Snapshot->SetArrayField(TEXT("materials"),Rows);
            if (!Fits(Snapshot))
            { ImportedFactorProposal::Error(Errors,TEXT("Protection snapshot budget exceeded")); break; }
        }
        const A After=Dirty(); Out->SetArrayField(TEXT("dirty_after"),After);
        if (After.Num()!=0) ImportedFactorProposal::Error(Errors,TEXT("Protection read observed dirty state"));
    }
    if (ImportGetterCalls!=0)
        ImportedFactorProposal::Error(Errors,TEXT("Protection reader invoked import metadata unexpectedly"));
    const bool Complete=Errors.Num()==0 && Rows.Num()==2;
    Snapshot->SetStringField(TEXT("schema"),TEXT("daedalus.imported-factor-current-projection.v1"));
    if (Complete) Out->SetObjectField(TEXT("snapshot"),Snapshot);
    else Out->SetField(TEXT("snapshot"),MakeShared<FJsonValueNull>());
    Out->SetStringField(TEXT("state"),Complete?TEXT("complete"):TEXT("held"));
    Out->SetArrayField(TEXT("errors"),Errors);
    Out->SetNumberField(TEXT("official_import_getter_invocations"),ImportGetterCalls);
    Out->SetNumberField(TEXT("explicit_asset_load_requests"),0);
    Out->SetNumberField(TEXT("authored_material_write_requests"),0);
    Out->SetNumberField(TEXT("material_cache_refreshes"),0);
    Out->SetNumberField(TEXT("evaluations"),0);
    Out->SetNumberField(TEXT("compilations"),0);
    Out->SetBoolField(TEXT("native_runtime_qualified"),false);
    Out->SetStringField(TEXT("hash_coverage"),TEXT("Complete existing imported-factor current-call/roster/three-factor projection and applicable parameter proofs; not every serialized material/function property or arbitrary unused parameter value"));
    if (!Fits(Out,0))
        return TEXT("{\"schema\":\"daedalus.imported-factor-protection.v1\",\"state\":\"held\",\"snapshot\":null,\"errors\":[\"Terminal UTF8 budget exceeded\"]}");
    return ImportedFactorProposal::Serialize(Out);
#else
    (void)MaterialObjectPaths; (void)AllowedPackageRoot;
    return TEXT("{\"schema\":\"daedalus.imported-factor-protection.v1\",\"state\":\"held\",\"snapshot\":null,\"errors\":[\"Editor-only protection reader unavailable\"]}");
#endif
}
