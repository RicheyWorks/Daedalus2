#include "DaedalusOceanHostClient.h"
#include "HttpModule.h"
#include "Interfaces/IHttpRequest.h"
#include "Interfaces/IHttpResponse.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "Misc/Base64.h"

namespace
{
bool Axis(int32 Value) { return Value>=-134217728 && Value<=134217727; }
bool OriginAllowed(FString Origin)
{
    const bool Secure=Origin.RemoveFromStart(TEXT("https://"));
    if (!Secure && !Origin.RemoveFromStart(TEXT("http://"))) return false;
    FString Host=Origin,Port;
    if (Origin.Split(TEXT(":"),&Host,&Port))
    {
        if (Port.IsEmpty() || Port.Len()>5) return false;
        for (TCHAR C:Port) if (C<'0' || C>'9') return false;
        const int32 Number=FCString::Atoi(*Port);if (Number<1 || Number>65535) return false;
    }
    if (!Secure && Host!=TEXT("127.0.0.1")) return false;
    if (Host.IsEmpty() || Host.Len()>253) return false;
    TArray<FString> Labels;Host.ParseIntoArray(Labels,TEXT("."),false);
    for (const FString& Label:Labels)
    {
        if (Label.IsEmpty() || Label.Len()>63 || Label[0]=='-' || Label[Label.Len()-1]=='-') return false;
        for (TCHAR C:Label) if (!((C>='a'&&C<='z')||(C>='A'&&C<='Z')||(C>='0'&&C<='9')||C=='-')) return false;
    }
    return true;
}
bool Integer(const TSharedPtr<FJsonObject>& Json,const TCHAR* Name,double& Out)
{
    return Json->TryGetNumberField(Name,Out) && FMath::IsFinite(Out) && Out==FMath::FloorToDouble(Out);
}
}

bool UDaedalusOceanHostClient::DecodeChunk(const FString& Text,int32 X,int32 Y,int32 Z,FDaedalusOceanChunkView& Out)
{
    Out={};
    if (Text.Len()>65536 || !Axis(X)||!Axis(Y)||!Axis(Z)) return false;
    TSharedPtr<FJsonObject> Json;
    if (!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Json) || !Json) return false;
    double NX,NY,NZ,Revision;
    bool Present=false;FString Data;
    const TArray<TSharedPtr<FJsonValue>>* Names=nullptr;
    if (!Integer(Json,TEXT("x"),NX)||NX!=X || !Integer(Json,TEXT("y"),NY)||NY!=Y
        || !Integer(Json,TEXT("z"),NZ)||NZ!=Z || !Integer(Json,TEXT("revision"),Revision)
        || Revision<0 || Revision>9007199254740991.0 || !Json->TryGetBoolField(TEXT("present"),Present)
        || !Json->TryGetStringField(TEXT("data"),Data) || !Json->TryGetArrayField(TEXT("palette"),Names)
        || !Names || Names->IsEmpty() || Names->Num()>256) return false;
    FDaedalusOceanChunkView Next;Next.X=X;Next.Y=Y;Next.Z=Z;Next.Revision=static_cast<int64>(Revision);
    TSet<FString> Seen;
    for (const auto& Value:*Names)
    {
        FString Name;if (!Value || !Value->TryGetString(Name) || Name.IsEmpty() || Name.Len()>48 || Seen.Contains(Name)) return false;
        for (TCHAR C:Name) if (!((C>='A'&&C<='Z')||C=='_')) return false;
        Seen.Add(Name);Next.Palette.Add(Name);
    }
    if (Next.Palette[0]!=TEXT("AIR")) return false;
    if (!Present)
    {
        if (!Data.IsEmpty()) return false;
        Next.Blocks.Init(0,4096);
    }
    else
    {
        if (Data.Len()!=5464 || !FBase64::Decode(Data,Next.Blocks) || Next.Blocks.Num()!=4096
            || FBase64::Encode(Next.Blocks)!=Data) return false;
        for (uint8 Ordinal:Next.Blocks) if (Ordinal>=Next.Palette.Num()) return false;
    }
    Out=MoveTemp(Next);return true;
}

bool UDaedalusOceanHostClient::ConfigureSession(const FString& Origin,const FString& Token)
{
    if (!IsInGameThread() || !OriginAllowed(Origin) || Token.IsEmpty() || Token.Len()>8192) return false;
    for (TCHAR C:Token) if (!((C>='a'&&C<='z')||(C>='A'&&C<='Z')||(C>='0'&&C<='9')||C=='.'||C=='_'||C=='-')) return false;
    ClearSession();ServerOrigin=Origin;BearerToken=Token;return true;
}
void UDaedalusOceanHostClient::ClearSession()
{
    ++Generation;
    auto Old=Pending;Pending.Reset();ServerOrigin.Reset();BearerToken.Reset();
    if (Old) { Old->OnProcessRequestComplete().Unbind();Old->CancelRequest(); }
}
void UDaedalusOceanHostClient::OnComponentDestroyed(bool Destroying)
{
    ClearSession();Super::OnComponentDestroyed(Destroying);
}
bool UDaedalusOceanHostClient::RequestChunk(int32 X,int32 Y,int32 Z)
{
    if (!IsInGameThread() || Pending || BearerToken.IsEmpty() || !Axis(X)||!Axis(Y)||!Axis(Z)) return false;
    auto Request=FHttpModule::Get().CreateRequest();
    const FString Url=ServerOrigin+FString::Printf(TEXT("/api/v1/ocean/v1/chunk?x=%d&y=%d&z=%d"),X,Y,Z);
    Request->SetURL(Url);Request->SetVerb(TEXT("GET"));Request->SetTimeout(10);
    Request->SetHeader(TEXT("Accept"),TEXT("application/json"));
    Request->SetHeader(TEXT("Authorization"),TEXT("Bearer ")+BearerToken);
    Request->SetDelegateThreadPolicy(EHttpRequestDelegateThreadPolicy::CompleteOnGameThread);
    auto Body=MakeShared<TArray<uint8>,ESPMode::ThreadSafe>();
    if (!Request->SetResponseBodyReceiveStreamDelegateV2(FHttpRequestStreamDelegateV2::CreateLambda(
        [Body](void* Data,int64& Length)
        {
            if (Length<0 || Length>65536-Body->Num()) { Length=0;return; }
            Body->Append(static_cast<const uint8*>(Data),static_cast<int32>(Length));
        }))) return false;
    TWeakObjectPtr<UDaedalusOceanHostClient> Self(this);const uint64 Session=Generation;
    Request->OnProcessRequestComplete().BindLambda([Self,Session,Body,Url,X,Y,Z](FHttpRequestPtr,FHttpResponsePtr Response,bool Connected)
    {
        if (!Self.IsValid() || Self->Generation!=Session) return;
        Self->Pending.Reset();
        const int32 Status=Response?Response->GetResponseCode():0;
        if (!Connected || !Response || Status!=200 || Response->GetURL()!=Url)
        { Self->OnFailure.Broadcast(Status,TEXT("Ocean request failed"));return; }
        FDaedalusOceanChunkView Chunk;
        const FUTF8ToTCHAR Converted(reinterpret_cast<const ANSICHAR*>(Body->GetData()),Body->Num());
        if (!DecodeChunk(FString(Converted.Length(),Converted.Get()),X,Y,Z,Chunk))
        { Self->OnFailure.Broadcast(Status,TEXT("Invalid Ocean chunk response"));return; }
        Self->OnChunk.Broadcast(Chunk);
    });
    Pending=Request;
    if (!Request->ProcessRequest()) { Pending.Reset();return false; }
    return true;
}
