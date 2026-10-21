// Source-only proposal: AUTHORED, UNCOMPILED, UNRUN. Sole operator stages it.
#include "DaedalusProspectorMineReadLibrary.h"
#if WITH_EDITOR
#include "DaedalusMineSourceHash.h"
#include "AnimPose.h"
#include "Animation/AnimSequence.h"
#include "Animation/AnimData/IAnimationDataModel.h"
#include "Animation/Skeleton.h"
#include "Animation/AnimBoneCompressionSettings.h"
#include "Animation/AnimCurveCompressionSettings.h"
#include "Animation/InterchangeAnimationPayloadInterface.h"
#include "AssetRegistry/AssetRegistryModule.h"
#include "AssetRegistry/IAssetRegistry.h"
#include "Dom/JsonObject.h"
#include "Editor.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"
#include "FileHelpers.h"
#include "HAL/FileManager.h"
#include "HAL/PlatformMisc.h"
#include "HAL/PlatformProcess.h"
#include "InterchangeAnimSequenceFactoryNode.h"
#include "InterchangeAnimationTrackSetNode.h"
#include "InterchangeAssetImportData.h"
#include "InterchangeCommonPipelineDataFactoryNode.h"
#include "InterchangeGenericAssetsPipeline.h"
#include "InterchangeGenericAssetsPipelineSharedSettings.h"
#include "InterchangeHelper.h"
#include "InterchangeJointNode.h"
#include "InterchangeManager.h"
#include "InterchangeResult.h"
#include "InterchangeResultsContainer.h"
#include "InterchangeSceneNode.h"
#include "InterchangeSourceData.h"
#include "InterchangeTranslatorBase.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Misc/PackageName.h"
#include "Misc/ScopeExit.h"
#include "Modules/ModuleManager.h"
#include "ReferenceSkeleton.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonWriter.h"
#include "UObject/StrongObjectPtr.h"
#include "UObject/UObjectGlobals.h"

namespace ProspectorRead
{
using J=TSharedRef<FJsonObject>;
using A=TArray<TSharedPtr<FJsonValue>>;
constexpr int32 Budget=512*1024;
static const FString Root=TEXT("/Game/Daedalus/ShardsteadWorkers/Probe_20261016T1628Z/Prospector/Twaker_Prospector/SkeletalMeshes");
static const FString MeshPath=Root+TEXT("/Twaker_Prospector.Twaker_Prospector");
static const FString SkeletonPath=Root+TEXT("/Twaker_Prospector_Skeleton.Twaker_Prospector_Skeleton");
static const FString ClipPath=Root+TEXT("/Twaker_ProspectorMine.Twaker_ProspectorMine");
static const FString FactoryUid=TEXT("\\AnimSequence\\SkeletalAnimation\\\\Scene\\Twaker_Prospector_scene_0\\Twaker_Prospector_node_15\\Twaker_Prospector_joint_13_4");
static const FString SourceFile=TEXT("C:/Users/730ri/Documents/Codex/2026-10-14/shardstead-workers-activities-01/Twaker_Prospector.glb");
static const FString SourceSha=TEXT("0c47c958e29b590e531c3dc804c10656054d7d6b20f2aa5e182f5cde4f004f14");
static const TCHAR* Names[]={TEXT("root"),TEXT("pelvis"),TEXT("spine"),TEXT("head"),TEXT("arm_L"),TEXT("forearm_L"),TEXT("arm_R"),TEXT("forearm_R"),TEXT("thigh_L"),TEXT("calf_L"),TEXT("foot_L"),TEXT("thigh_R"),TEXT("calf_R"),TEXT("foot_R")};
static bool Readable(const UObject* O){return IsValid(O)&&!O->HasAnyFlags(RF_NeedLoad|RF_NeedPostLoad);}
static void Error(A& E,const FString& S){if(E.Num()<16)E.Add(MakeShared<FJsonValueString>(S.Left(1024)));}
static FString Serialize(J O){FString S; FJsonSerializer::Serialize(O,TJsonWriterFactory<TCHAR,TCondensedJsonPrintPolicy<TCHAR>>::Create(&S));return S;}
static J Identity(const UObject* O){J R=MakeShared<FJsonObject>();R->SetStringField(TEXT("path"),O->GetPathName());R->SetStringField(TEXT("class"),O->GetClass()->GetPathName());return R;}
static bool Transform(const FTransform& T,J O)
{
    const FVector P=T.GetTranslation(),S=T.GetScale3D();const FQuat Q=T.GetRotation();
    const double V[]={P.X,P.Y,P.Z,Q.X,Q.Y,Q.Z,Q.W,S.X,S.Y,S.Z};for(double X:V)if(!FMath::IsFinite(X))return false;
    A Pj,Qj,Sj;for(double X:{P.X,P.Y,P.Z})Pj.Add(MakeShared<FJsonValueNumber>(X));
    for(double X:{Q.X,Q.Y,Q.Z,Q.W})Qj.Add(MakeShared<FJsonValueNumber>(X));
    for(double X:{S.X,S.Y,S.Z})Sj.Add(MakeShared<FJsonValueNumber>(X));
    O->SetArrayField(TEXT("translation_cm"),Pj);O->SetArrayField(TEXT("rotation_xyzw"),Qj);O->SetArrayField(TEXT("scale"),Sj);return true;
}
static bool Reference(const FReferenceSkeleton& Ref,A& Rows,A& E)
{
    const auto& Info=Ref.GetRawRefBoneInfo();const auto& Pose=Ref.GetRawRefBonePose();
    if(Info.Num()!=14||Pose.Num()!=14){Error(E,TEXT("Raw reference must contain exactly14 original bones"));return false;}
    TSet<FName> Seen;
    for(int32 I=0;I<14;++I){const FMeshBoneInfo& B=Info[I];if(Seen.Contains(B.Name)||B.ParentIndex>=I||B.ParentIndex<INDEX_NONE){Error(E,TEXT("Raw reference hierarchy is invalid"));return false;}Seen.Add(B.Name);
        J R=MakeShared<FJsonObject>(),T=MakeShared<FJsonObject>();if(!Transform(Pose[I],T)){Error(E,TEXT("Nonfinite reference pose"));return false;}
        R->SetStringField(TEXT("name"),B.Name.ToString());R->SetNumberField(TEXT("parent_index"),B.ParentIndex);R->SetObjectField(TEXT("local"),T);Rows.Add(MakeShared<FJsonValueObject>(R));}
    for(const TCHAR* Name:Names)if(!Seen.Contains(FName(Name))){Error(E,TEXT("Raw bone membership differs"));return false;}return true;
}
static bool Pose(UAnimSequence* Clip,const TArray<double>& Times,A& Samples,A& E)
{
    FAnimPoseEvaluationOptions Opt;Opt.EvaluationType=EAnimDataEvalType::Source;Opt.bShouldRetarget=false;
    Opt.bExtractRootMotion=false;Opt.bIncorporateRootMotionIntoPose=true;Opt.bEvaluateCurves=false;
    Opt.bRetrieveAdditiveAsFullPose=false;Opt.OptionalSkeletalMesh=nullptr;
    for(double Time:Times){FAnimPose P;UAnimPoseExtensions::GetAnimPoseAtTime(Clip,Time,Opt,P);
        if(!P.IsValid()){Error(E,TEXT("Fresh Source pose is invalid; no retained output fallback"));return false;}
        TArray<FName> Actual;UAnimPoseExtensions::GetBoneNames(P,Actual);TSet<FName> Set;for(FName N:Actual)Set.Add(N);
        if(Actual.Num()!=14||Set.Num()!=14){Error(E,TEXT("Fresh Source pose roster incomplete; no Identity fallback"));return false;}
        for(const TCHAR* N:Names)if(!Set.Contains(FName(N))){Error(E,TEXT("Sampled bone absent; refusing Identity fallback"));return false;}
        J R=MakeShared<FJsonObject>(),Poses=MakeShared<FJsonObject>();for(const TCHAR* N:Names){J T=MakeShared<FJsonObject>();if(!Transform(UAnimPoseExtensions::GetBonePose(P,FName(N),EAnimPoseSpaces::Local),T)){Error(E,TEXT("Nonfinite sampled transform"));return false;}Poses->SetObjectField(N,T);}
        R->SetNumberField(TEXT("time_s"),Time);R->SetBoolField(TEXT("valid"),true);R->SetBoolField(TEXT("bone_names_verified"),true);
        R->SetStringField(TEXT("evaluation"),TEXT("Source_NoRetarget_NoRootExtraction_NoCurves"));R->SetObjectField(TEXT("poses"),Poses);Samples.Add(MakeShared<FJsonValueObject>(R));}
    return true;
}
static bool SourceOracle(double Rate,double Start,double Stop,const FTransform& Offset,const TArray<double>& Times,J Out,A& E,int32& Translations,bool IncludeHierarchy=false)
{
    // Closed actual target profile. Do not guess general pivot/retarget behavior.
    if(!Offset.Equals(FTransform::Identity,0.0)){Error(E,TEXT("Nonidentity final offset requires a separately qualified conversion"));return false;}
    TArray<uint8> Bytes;FString Hash;
    if(IFileManager::Get().FileSize(*SourceFile)!=212424||!FFileHelper::LoadFileToArray(Bytes,*SourceFile)||Bytes.Num()!=212424||!DaedalusMineSourceHash::Compute(Bytes.GetData(),static_cast<uint32>(Bytes.Num()),Hash)||Hash!=SourceSha){Error(E,TEXT("Independent source bytes/hash differ"));return false;}
    UInterchangeManager& Manager=UInterchangeManager::GetInterchangeManager();
    TStrongObjectPtr<UInterchangeSourceData> Data(UInterchangeManager::CreateSourceData(SourceFile));
    TStrongObjectPtr<UInterchangeTranslatorBase> Translator(Data.IsValid()?Manager.GetTranslatorForSourceData(Data.Get()):nullptr);
    if(!Translator.IsValid()||Translator->GetClass()->GetPathName()!=TEXT("/Script/InterchangeImport.InterchangeGLTFTranslator")){Error(E,TEXT("Exact registered glTF translator unavailable; no FBX/default substitution"));return false;}
    TStrongObjectPtr<UInterchangeResultsContainer> Results(NewObject<UInterchangeResultsContainer>());
    Translator->SetResultsContainer(Results.Get());ON_SCOPE_EXIT{Translator->ReleaseSource();};
    TStrongObjectPtr<UInterchangeBaseNodeContainer> Nodes(NewObject<UInterchangeBaseNodeContainer>());
    ++Translations;if(!Translator->Translate(*Nodes.Get())){Error(E,TEXT("Independent glTF source translation failed"));return false;}
    const FString TrackUid=FactoryUid.RightChop(FString(TEXT("\\AnimSequence")).Len());
    const auto* Track=Cast<UInterchangeSkeletalAnimationTrackNode>(Nodes->GetNode(TrackUid));
    const auto* PayloadInterface=Cast<IInterchangeAnimationPayloadInterface>(Translator.Get());
    if(!Track||!PayloadInterface){Error(E,TEXT("Exact fresh Mine track or public animation payload interface unavailable"));return false;}
    TMap<FString,FString> Keys;TMap<FString,uint8> Types;Track->GetSceneNodeAnimationPayloadKeys(Keys,Types);
    if(Keys.Num()!=14||Types.Num()!=14){Error(E,TEXT("Complete fresh Mine source payload roster required"));return false;}
    TArray<UE::Interchange::FAnimationPayloadQuery> Queries;TMap<FString,FString> AliasByUid;J Reference=MakeShared<FJsonObject>();
    for(const auto& Pair:Keys){const auto* Joint=Cast<UInterchangeJointNode>(Nodes->GetNode(Pair.Key));const uint8* Type=Types.Find(Pair.Key);
        if(!Joint||!Type||*Type!=static_cast<uint8>(EInterchangeAnimationPayLoadType::BAKED)||!Pair.Value.StartsWith(TEXT("4:"))){Error(E,TEXT("Source Mine joint/payload type differs"));return false;}
        const FString Alias=UE::Interchange::MakeSanitizedName(Joint->GetDisplayLabel(),true);
        if(AliasByUid.FindKey(Alias)){Error(E,TEXT("Ambiguous source joint alias"));return false;}AliasByUid.Add(Pair.Key,Alias);
        FTransform Bind;if(!Joint->GetBindPoseLocalTransform(Bind)){Error(E,TEXT("Source inverse-bind-derived pose absent; no T0 fallback"));return false;}
        if(Alias==TEXT("root")){const auto* Parent=Cast<UInterchangeSceneNode>(Nodes->GetNode(Joint->GetParentUid()));FTransform ParentGlobal;
            if(!Parent||!Parent->GetCustomGlobalTransform(Nodes.Get(),FTransform::Identity,ParentGlobal)||!ParentGlobal.Equals(FTransform::Identity,0.0)||!Bind.Equals(FTransform::Identity,0.0)){Error(E,TEXT("Source root/ancestor is not the closed identity profile"));return false;}}
        J T=MakeShared<FJsonObject>();if(!Transform(FTransform(FTransform3f(Bind)),T)){Error(E,TEXT("Nonfinite source bind pose"));return false;}Reference->SetObjectField(Alias,T);
        Queries.Emplace(Pair.Key,FInterchangeAnimationPayLoadKey(Pair.Value,EInterchangeAnimationPayLoadType::BAKED),Rate,Start,Stop);}
    for(const TCHAR* N:Names)if(!AliasByUid.FindKey(FString(N))){Error(E,TEXT("Fresh source bone names differ"));return false;}
    if(IncludeHierarchy){J Parents=MakeShared<FJsonObject>();for(const auto& Pair:AliasByUid){
        const auto* Joint=Cast<UInterchangeJointNode>(Nodes->GetNode(Pair.Key));
        const FString* Parent=Joint?AliasByUid.Find(Joint->GetParentUid()):nullptr;
        if(Pair.Value==TEXT("root")){if(Parent){Error(E,TEXT("Source root has a joint parent"));return false;}Parents->SetField(Pair.Value,MakeShared<FJsonValueNull>());}
        else if(Parent)Parents->SetStringField(Pair.Value,*Parent);
        else{Error(E,TEXT("Source joint parent absent from exact roster"));return false;}}
        Out->SetObjectField(TEXT("bone_parents"),Parents);}
    const auto Payloads=PayloadInterface->GetAnimationPayloadData(Queries);
    if(Payloads.Num()!=14){Error(E,TEXT("Incomplete independent source payloads"));return false;}
    TMap<FString,const UE::Interchange::FAnimationPayloadData*> ByUid;
    const int32 Count=FMath::RoundToInt32((Stop-Start)*Rate)+1;
    for(const auto& P:Payloads){const FString* Key=Keys.Find(P.SceneNodeUniqueID);
        if(!Key||ByUid.Contains(P.SceneNodeUniqueID)||P.PayloadKey.UniqueId!=*Key||P.PayloadKey.Type!=EInterchangeAnimationPayLoadType::BAKED||P.BakeFrequency!=Rate||P.RangeStartTime!=Start||P.RangeEndTime!=Stop||P.Transforms.Num()!=Count){Error(E,TEXT("Source payload identity/range/keys differ"));return false;}ByUid.Add(P.SceneNodeUniqueID,&P);}
    A Samples;for(double Time:Times){const int32 Index=FMath::RoundToInt32(Time*Rate);
        if(Index<0||Index>=Count||static_cast<double>(Index)/Rate!=Time){Error(E,TEXT("Requested oracle sample is not an exact baked-frame time; no interpolation guess"));return false;}
        J R=MakeShared<FJsonObject>(),Poses=MakeShared<FJsonObject>();for(const auto& Pair:AliasByUid){const auto* P=ByUid.FindRef(Pair.Key);J T=MakeShared<FJsonObject>();
            if(!P||!Transform(FTransform(FTransform3f(P->Transforms[Index])),T)){Error(E,TEXT("Source sampled transform missing/nonfinite"));return false;}Poses->SetObjectField(Pair.Value,T);}
        R->SetNumberField(TEXT("time_s"),Time);R->SetObjectField(TEXT("poses"),Poses);Samples.Add(MakeShared<FJsonValueObject>(R));}
    // Translation/payload extraction reopen the source path internally. Do not
    // bind their result to a hash taken only before that work.
    TArray<uint8> AfterBytes;
    if(IFileManager::Get().FileSize(*SourceFile)!=212424||!FFileHelper::LoadFileToArray(AfterBytes,*SourceFile)||AfterBytes!=Bytes){Error(E,TEXT("Source changed during independent translation/payload read"));return false;}
    A Messages;const auto NativeMessages=Results->GetResults();if(NativeMessages.Num()>16){Error(E,TEXT("Source diagnostic bound exceeded; no omitted-success prefix"));return false;}
    for(const UInterchangeResult* M:NativeMessages){if(!M){Error(E,TEXT("Null source diagnostic"));return false;}const FString Text=M->GetText().ToString();if(Text.Len()>2048){Error(E,TEXT("Source diagnostic text bound exceeded"));return false;}Messages.Add(MakeShared<FJsonValueString>(Text));if(M->GetResultType()==EInterchangeResultType::Error)Error(E,TEXT("Source translator reported an error"));}
    Out->SetStringField(TEXT("state"),TEXT("SOURCE_CONVERSION_CANDIDATE_NOT_YET_QUALIFIED"));Out->SetStringField(TEXT("source_sha256"),SourceSha);
    Out->SetStringField(TEXT("coordinate_space"),TEXT("UE_LOCAL_CM"));Out->SetStringField(TEXT("conversion_contract"),TEXT("PINNED_GLTF_CANONICAL_TRANSLATOR_IDENTITY_ROOT_BAKED_FRAME_V1"));
    Out->SetBoolField(TEXT("source_unchanged_after_payload"),true);
    Out->SetStringField(TEXT("translator_class"),Translator->GetClass()->GetPathName());Out->SetStringField(TEXT("track_uid"),TrackUid);
    Out->SetObjectField(TEXT("reference_pose"),Reference);Out->SetArrayField(TEXT("samples"),Samples);Out->SetArrayField(TEXT("translator_messages"),Messages);return E.Num()==0;
}

} // namespace ProspectorRead
#endif

#if WITH_EDITOR
namespace ProspectorFresh
{
using namespace ProspectorRead;
static const FString FreshPath=TEXT("/Game/CodexToolEvaluation/MineClipRoundtrip/FreshR1/Twaker_ProspectorMine.Twaker_ProspectorMine");
static bool Active=false;
static J Envelope(const TCHAR* Kind){J Out=MakeShared<FJsonObject>();Out->SetStringField(TEXT("schema"),Kind);Out->SetBoolField(TEXT("native_invoked"),true);Out->SetNumberField(TEXT("pid"),FPlatformProcess::GetCurrentProcessId());Out->SetStringField(TEXT("observed_utc"),FDateTime::UtcNow().ToIso8601());Out->SetStringField(TEXT("source_sha256"),SourceSha);Out->SetStringField(TEXT("source_path"),SourceFile);Out->SetBoolField(TEXT("native_runtime_qualified"),false);return Out;}
static bool Context(A& E,bool AllowFreshDirty){
    if(!IsInGameThread()||Active||!GEditor||GEditor->PlayWorld||!GEditor->GetEditorWorldContext().World()||GEditor->GetEditorWorldContext().World()->GetPathName()!=TEXT("/Game/Daedalus/DaedalusWorld.DaedalusWorld")){ProspectorRead::Error(E,TEXT("Closed fresh editor context refused"));return false;}
    TArray<UPackage*> Maps,Content;UEditorLoadingAndSavingUtils::GetDirtyMapPackages(Maps);UEditorLoadingAndSavingUtils::GetDirtyContentPackages(Content);
    if(Maps.Num()){ProspectorRead::Error(E,TEXT("Dirty map refused"));return false;}
    const FString Package=FPackageName::ObjectPathToPackageName(FreshPath);
    for(UPackage* P:Content)if(!AllowFreshDirty||!P||P->GetName()!=Package){ProspectorRead::Error(E,TEXT("Unexpected dirty content refused"));return false;}return true;
}
static FString Finish(J Out,A& E,int32 Translations=0){Out->SetArrayField(TEXT("errors"),E);Out->SetStringField(TEXT("state"),E.Num()?TEXT("held"):TEXT("complete"));Out->SetNumberField(TEXT("source_translations"),Translations);const FString Text=Serialize(Out);if(FTCHARToUTF8(*Text).Length()>Budget)return TEXT("{\"state\":\"held\",\"errors\":[\"Fresh proof UTF8 cap\"]}");return Text;}
static bool References(J Out,A& E){
    auto* Mesh=Cast<USkeletalMesh>(StaticFindObject(USkeletalMesh::StaticClass(),nullptr,*MeshPath));auto* Skeleton=Cast<USkeleton>(StaticFindObject(USkeleton::StaticClass(),nullptr,*SkeletonPath));
    if(!Readable(Mesh)||!Readable(Skeleton)||Mesh->GetSkeleton()!=Skeleton){ProspectorRead::Error(E,TEXT("Exact original loaded mesh/Skeleton context required"));return false;}
    A MR,SR;if(!Reference(Mesh->GetRefSkeleton(),MR,E)||!Reference(Skeleton->GetReferenceSkeleton(),SR,E))return false;
    Out->SetStringField(TEXT("skeleton_path"),SkeletonPath);Out->SetStringField(TEXT("mesh_path"),MeshPath);Out->SetArrayField(TEXT("mesh_reference"),MR);Out->SetArrayField(TEXT("skeleton_reference"),SR);return true;
}
}
#endif

FString UDaedalusProspectorMineReadLibrary::ReadFreshMineSource(UInterchangeBaseNodeContainer* JobNodes)
{
#if WITH_EDITOR
    using namespace ProspectorFresh;J Out=Envelope(TEXT("daedalus.mine-fresh-source.v1"));A E;int32 Translations=0;
    auto Run=[&](){if(!Context(E,false)||!Readable(JobNodes)){ProspectorRead::Error(E,TEXT("Actual live job nodes required"));return;}TGuardValue<bool> Guard(Active,true);
        if(!References(Out,E))return;
        const auto* Factory=Cast<UInterchangeAnimSequenceFactoryNode>(JobNodes->GetFactoryNode(FactoryUid));const auto* Common=UInterchangeCommonPipelineDataFactoryNode::GetUniqueInstance(JobNodes);
        double Rate=0,Start=0,Stop=0;bool Bake=false,Tracks=false;FTransform Offset;FSoftObjectPath SpecifiedSkeleton;
        if(!Factory||!Common||!Factory->GetCustomImportBoneTracksSampleRate(Rate)||!Factory->GetCustomImportBoneTracksRangeStart(Start)||!Factory->GetCustomImportBoneTracksRangeStop(Stop)||!Factory->GetCustomImportBoneTracks(Tracks)||!Common->GetBakeMeshes(Bake)||!Common->GetCustomGlobalOffsetTransform(Offset)||Rate!=24||Start!=0||!FMath::IsFinite(Stop)||Stop<=1||Stop>=2||!Tracks||!Bake||!Offset.Equals(FTransform::Identity,0.0)){ProspectorRead::Error(E,TEXT("Closed actual final common/factory profile refused"));return;}
        if(!Factory->GetCustomSkeletonSoftObjectPath(SpecifiedSkeleton)||SpecifiedSkeleton.ToString()!=SkeletonPath){ProspectorRead::Error(E,TEXT("Explicit final factory Skeleton differs"));return;}
        J P=MakeShared<FJsonObject>(),OT=MakeShared<FJsonObject>();if(!Transform(Offset,OT)){ProspectorRead::Error(E,TEXT("Nonfinite offset"));return;}P->SetStringField(TEXT("skeleton_path"),SpecifiedSkeleton.ToString());
        P->SetStringField(TEXT("factory_uid"),FactoryUid);P->SetStringField(TEXT("job_container"),JobNodes->GetPathName());P->SetNumberField(TEXT("sample_rate"),Rate);P->SetNumberField(TEXT("range_start"),Start);P->SetNumberField(TEXT("range_stop"),Stop);P->SetBoolField(TEXT("bake_meshes"),Bake);P->SetBoolField(TEXT("bone_tracks"),Tracks);P->SetObjectField(TEXT("global_offset"),OT);Out->SetObjectField(TEXT("live_profile"),P);
        J Oracle=MakeShared<FJsonObject>();if(!SourceOracle(Rate,Start,Stop,Offset,{0.0,1.0},Oracle,E,Translations,true))return;Out->SetObjectField(TEXT("source_oracle"),Oracle);
    };Run();return Finish(Out,E,Translations);
#else
    (void)JobNodes;return TEXT("{\"state\":\"held\",\"errors\":[\"Editor only\"]}");
#endif
}

FString UDaedalusProspectorMineReadLibrary::ReadFreshMineClip(const FString& AssetPath)
{
#if WITH_EDITOR
    using namespace ProspectorFresh;J Out=Envelope(TEXT("daedalus.mine-fresh-clip.v1"));A E;
    auto Run=[&](){if(AssetPath!=FreshPath){ProspectorRead::Error(E,TEXT("Exact private fresh Mine path required; no load"));return;}if(!Context(E,true))return;TGuardValue<bool> Guard(Active,true);
        if(!References(Out,E))return;
        auto* Clip=Cast<UAnimSequence>(StaticFindObject(UAnimSequence::StaticClass(),nullptr,*AssetPath));auto* Skeleton=Cast<USkeleton>(StaticFindObject(USkeleton::StaticClass(),nullptr,*SkeletonPath));
        if(!Readable(Clip)||Clip->GetClass()!=UAnimSequence::StaticClass()||Clip->GetSkeleton()!=Skeleton||Clip->GetAdditiveAnimType()!=AAT_None){ProspectorRead::Error(E,TEXT("Fresh clip class/Skeleton/nonadditive context refused"));return;}
        Out->SetStringField(TEXT("asset_path"),AssetPath);Out->SetStringField(TEXT("clip_skeleton_path"),Clip->GetSkeleton()->GetPathName());Out->SetNumberField(TEXT("length_s"),Clip->GetPlayLength());
        const auto* Data=Cast<UInterchangeAssetImportData>(UInterchangeAssetImportData::GetFromObject(Clip));const auto* Factory=Data?Cast<UInterchangeAnimSequenceFactoryNode>(Data->GetStoredFactoryNode(FactoryUid)):nullptr;
        double Rate=0,Start=0,Stop=0;if(!Data||Data->NodeUniqueID!=FactoryUid||Data->GetSourceFileCount()!=1||!Factory||!Factory->GetCustomImportBoneTracksSampleRate(Rate)||!Factory->GetCustomImportBoneTracksRangeStart(Start)||!Factory->GetCustomImportBoneTracksRangeStop(Stop)){ProspectorRead::Error(E,TEXT("Fresh exact stored source/factory profile absent"));return;}
        Out->SetStringField(TEXT("stored_source_path"),FPaths::ConvertRelativePathToFull(Data->GetFirstFilename()));Out->SetNumberField(TEXT("sample_rate"),Rate);Out->SetNumberField(TEXT("range_start"),Start);Out->SetNumberField(TEXT("range_stop"),Stop);
        if(!Clip->GetDataModel()){ProspectorRead::Error(E,TEXT("Fresh source animation data model absent"));return;}
        TArray<FName> Tracks;Clip->GetDataModel()->GetBoneTrackNames(Tracks);if(Tracks.Num()!=14){ProspectorRead::Error(E,TEXT("Fresh exact14 bone tracks required"));return;}A NamesJson;for(FName N:Tracks)NamesJson.Add(MakeShared<FJsonValueString>(N.ToString()));Out->SetArrayField(TEXT("track_names"),NamesJson);
        A Samples;if(!Pose(Clip,{0.0,1.0},Samples,E))return;Out->SetArrayField(TEXT("samples"),Samples);
    };Run();return Finish(Out,E);
#else
    (void)AssetPath;return TEXT("{\"state\":\"held\",\"errors\":[\"Editor only\"]}");
#endif
}
FString UDaedalusProspectorMineReadLibrary::ReadMinePrerequisites(const TArray<double>& SampleTimes)
{
#if WITH_EDITOR
    using namespace ProspectorRead;J Out=MakeShared<FJsonObject>();A E;int32 Translations=0;
    Out->SetStringField(TEXT("schema"),TEXT("daedalus.prospector-mine-prerequisites.v1"));Out->SetBoolField(TEXT("native_invoked"),true);Out->SetStringField(TEXT("evidence_kind"),TEXT("native_capture"));
    Out->SetStringField(TEXT("project_path"),FPaths::ConvertRelativePathToFull(FPaths::GetProjectFilePath()));Out->SetNumberField(TEXT("pid"),FPlatformProcess::GetCurrentProcessId());
    Out->SetStringField(TEXT("observed_utc"),FDateTime::UtcNow().ToIso8601());
    static bool Active=false;auto Run=[&]()
    {
        if(!IsInGameThread()||Active||!GEditor||GEditor->PlayWorld||!GEditor->GetEditorWorldContext().World()||GEditor->GetEditorWorldContext().World()->GetPathName()!=TEXT("/Game/Daedalus/DaedalusWorld.DaedalusWorld")||SampleTimes.Num()<2||SampleTimes.Num()>8){ProspectorRead::Error(E,TEXT("Closed editor/sample admission refused"));return;}
        TGuardValue<bool> Guard(Active,true);double Last=-1;for(double T:SampleTimes){if(!FMath::IsFinite(T)||T<=Last||T<0||T>1.5416666269302368){ProspectorRead::Error(E,TEXT("Invalid requested sample times"));return;}Last=T;}
        TArray<UPackage*> Dirty;UEditorLoadingAndSavingUtils::GetDirtyMapPackages(Dirty);UEditorLoadingAndSavingUtils::GetDirtyContentPackages(Dirty);if(Dirty.Num()){ProspectorRead::Error(E,TEXT("Dirty package precondition"));return;}
        auto* Mesh=Cast<USkeletalMesh>(StaticFindObject(USkeletalMesh::StaticClass(),nullptr,*MeshPath));auto* Skeleton=Cast<USkeleton>(StaticFindObject(USkeleton::StaticClass(),nullptr,*SkeletonPath));auto* Clip=Cast<UAnimSequence>(StaticFindObject(UAnimSequence::StaticClass(),nullptr,*ClipPath));
        if(!Readable(Mesh)||!Readable(Skeleton)||!Readable(Clip)||Mesh->GetClass()!=USkeletalMesh::StaticClass()||Skeleton->GetClass()!=USkeleton::StaticClass()||Clip->GetClass()!=UAnimSequence::StaticClass()||Mesh->GetSkeleton()!=Skeleton||Clip->GetSkeleton()!=Skeleton){ProspectorRead::Error(E,TEXT("Exact already loaded target/Skeleton links required; no load"));return;}
        if(Clip->GetAdditiveAnimType()!=AAT_None||!Clip->BoneCompressionSettings.IsResolved()||!Clip->CurveCompressionSettings.IsResolved()||!Readable(Clip->BoneCompressionSettings.Get())||!Readable(Clip->CurveCompressionSettings.Get())){ProspectorRead::Error(E,TEXT("Non-additive/resolved compression context unavailable"));return;}
        for(double T:SampleTimes)if(T>Clip->GetPlayLength()){ProspectorRead::Error(E,TEXT("Sample time beyond actual clip"));return;}
        Out->SetStringField(TEXT("mesh_path"),MeshPath);Out->SetStringField(TEXT("skeleton_path"),SkeletonPath);Out->SetStringField(TEXT("clip_path"),ClipPath);Out->SetStringField(TEXT("mesh_skeleton_path"),Mesh->GetSkeleton()->GetPathName());Out->SetStringField(TEXT("clip_skeleton_path"),Clip->GetSkeleton()->GetPathName());
        Out->SetNumberField(TEXT("length_s"),Clip->GetPlayLength());J Context=MakeShared<FJsonObject>();Context->SetStringField(TEXT("additive_type"),TEXT("AAT_None"));Context->SetStringField(TEXT("pose_data_source"),TEXT("Source_NoCompressedPlaybackQualification"));Context->SetBoolField(TEXT("compression_identity_complete"),true);Context->SetObjectField(TEXT("bone_compression"),Identity(Clip->BoneCompressionSettings.Get()));Context->SetObjectField(TEXT("curve_compression"),Identity(Clip->CurveCompressionSettings.Get()));Out->SetObjectField(TEXT("animation_context"),Context);
        auto& Registry=FModuleManager::LoadModuleChecked<FAssetRegistryModule>(TEXT("AssetRegistry")).Get();if(Registry.IsLoadingAssets()){ProspectorRead::Error(E,TEXT("Registry is discovering; no scan/wait"));return;}TArray<FAssetData> Assets;Registry.GetAssetsByPath(FName(*Root),Assets,false,false);if(Assets.Num()>32){ProspectorRead::Error(E,TEXT("Named directory inventory bound exceeded"));return;}TArray<FString> ClipNames;for(const FAssetData& A:Assets)if(A.AssetClassPath==UAnimSequence::StaticClass()->GetClassPathName())ClipNames.Add(A.GetObjectPathString());ClipNames.Sort();A Inventory;for(const FString& P:ClipNames)Inventory.Add(MakeShared<FJsonValueString>(P));Out->SetArrayField(TEXT("all_clip_paths"),Inventory);
        A MR,SR;if(!Reference(Mesh->GetRefSkeleton(),MR,E)||!Reference(Skeleton->GetReferenceSkeleton(),SR,E))return;Out->SetArrayField(TEXT("mesh_reference"),MR);Out->SetArrayField(TEXT("skeleton_reference"),SR);
        const auto* Data=Cast<UInterchangeAssetImportData>(UInterchangeAssetImportData::GetFromObject(Clip));if(!Data||Data->NodeUniqueID!=FactoryUid){ProspectorRead::Error(E,TEXT("Exact Mine stored Interchange factory identity unavailable"));return;}
        FString StoredFilename=FPaths::ConvertRelativePathToFull(Data->GetFirstFilename());FPaths::NormalizeFilename(StoredFilename);
        if(Data->GetSourceFileCount()!=1||!FPaths::IsSamePath(StoredFilename,SourceFile)){ProspectorRead::Error(E,TEXT("Stored source index zero must resolve to the one original pinned GLB"));return;}
        J StoredSource=MakeShared<FJsonObject>();StoredSource->SetNumberField(TEXT("source_index"),0);StoredSource->SetNumberField(TEXT("file_count"),1);StoredSource->SetStringField(TEXT("resolved_filename"),StoredFilename);Out->SetObjectField(TEXT("stored_source"),StoredSource);
        const auto* Nodes=Data->GetNodeContainer();const auto* Factory=Cast<UInterchangeAnimSequenceFactoryNode>(Data->GetStoredFactoryNode(FactoryUid));const auto* Common=Nodes?UInterchangeCommonPipelineDataFactoryNode::GetUniqueInstance(Nodes):nullptr;
        double Rate=0,Start=0,Stop=0;bool Bake=false;FTransform Offset;
        if(!Factory||!Common||!Factory->GetCustomImportBoneTracksSampleRate(Rate)||!Factory->GetCustomImportBoneTracksRangeStart(Start)||!Factory->GetCustomImportBoneTracksRangeStop(Stop)||!Common->GetBakeMeshes(Bake)||!Common->GetCustomGlobalOffsetTransform(Offset)||!FMath::IsFinite(Rate)||!FMath::IsFinite(Start)||!FMath::IsFinite(Stop)||Rate<=0||Rate>480||Start!=0||Stop<=Start||Stop>2){ProspectorRead::Error(E,TEXT("Final stored bake/range/common attributes missing or unsupported; only zero-start range is qualified"));return;}
        int32 GenericCount=0;for(UObject* Pipeline:Data->GetPipelines())if(const auto* Generic=Cast<UInterchangeGenericAssetsPipeline>(Pipeline)){++GenericCount;if(!Generic->CommonSkeletalMeshesAndAnimationsProperties.IsResolved()||!Readable(Generic->CommonSkeletalMeshesAndAnimationsProperties.Get())||Generic->CommonSkeletalMeshesAndAnimationsProperties->bUseT0AsRefPose){ProspectorRead::Error(E,TEXT("Stored T0 context unavailable or not bind pose"));return;}}
        if(GenericCount!=1){ProspectorRead::Error(E,TEXT("One actual generic stored pipeline required"));return;}
        J Profile=MakeShared<FJsonObject>(),OT=MakeShared<FJsonObject>();if(!Transform(Offset,OT)){ProspectorRead::Error(E,TEXT("Nonfinite final offset"));return;}Profile->SetStringField(TEXT("uid"),FactoryUid);Profile->SetBoolField(TEXT("attributes_complete"),true);Profile->SetNumberField(TEXT("sample_rate"),Rate);Profile->SetNumberField(TEXT("range_start"),Start);Profile->SetNumberField(TEXT("range_stop"),Stop);Profile->SetBoolField(TEXT("bake_meshes"),Bake);Profile->SetObjectField(TEXT("global_offset"),OT);Out->SetObjectField(TEXT("factory"),Profile);
        A Samples;if(!Pose(Clip,SampleTimes,Samples,E))return;Out->SetArrayField(TEXT("samples"),Samples);
        J Oracle=MakeShared<FJsonObject>();if(!SourceOracle(Rate,Start,Stop,Offset,SampleTimes,Oracle,E,Translations))return;Out->SetObjectField(TEXT("source_oracle_candidate"),Oracle);
        J Source=MakeShared<FJsonObject>();Source->SetNumberField(TEXT("bytes"),212424);Source->SetStringField(TEXT("sha256"),SourceSha);Out->SetObjectField(TEXT("source"),Source);
        TArray<UPackage*> After;UEditorLoadingAndSavingUtils::GetDirtyMapPackages(After);UEditorLoadingAndSavingUtils::GetDirtyContentPackages(After);if(After.Num())ProspectorRead::Error(E,TEXT("Dirty package postcondition"));
    };Run();
    J Effects=MakeShared<FJsonObject>();for(const TCHAR* K:{TEXT("asset_load_requests"),TEXT("imports"),TEXT("reimports"),TEXT("saves"),TEXT("authored_asset_edits")})Effects->SetNumberField(K,0);Effects->SetNumberField(TEXT("source_translations"),Translations);Effects->SetStringField(TEXT("temporary_effects"),TEXT("Official stored import-data getters can materialize transient metadata; fresh registered glTF translator creates independent transient source nodes/payloads; AnimPose evaluates Source data. Private-cache immutability and global implicit dependency loads are not claimed."));Out->SetObjectField(TEXT("effects"),Effects);
    Out->SetArrayField(TEXT("errors"),E);Out->SetStringField(TEXT("state"),E.Num()?TEXT("held"):TEXT("complete"));Out->SetBoolField(TEXT("native_runtime_qualified"),false);
    const FString Text=ProspectorRead::Serialize(Out);if(FTCHARToUTF8(*Text).Length()>Budget)return TEXT("{\"schema\":\"daedalus.prospector-mine-prerequisites.v1\",\"state\":\"held\",\"errors\":[\"UTF8 budget exceeded\"]}");return Text;
#else
    (void)SampleTimes;return TEXT("{\"schema\":\"daedalus.prospector-mine-prerequisites.v1\",\"state\":\"held\",\"errors\":[\"Editor-only collector unavailable\"]}");
#endif
}
