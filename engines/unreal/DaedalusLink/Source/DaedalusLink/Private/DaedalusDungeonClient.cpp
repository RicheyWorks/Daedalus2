// SPDX-License-Identifier: MIT
#include "DaedalusDungeonClient.h"
#include "HttpModule.h"
#include "Interfaces/IHttpRequest.h"
#include "Interfaces/IHttpResponse.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "Misc/Guid.h"

namespace {
using FObject = TSharedPtr<FJsonObject>;
bool String(const FObject& O, const TCHAR* Key, std::string& Out, bool Optional=false) {
    FString Value;
    if(!O->TryGetStringField(Key,Value)) {
        if(Optional && (!O->HasField(Key) || O->HasTypedField<EJson::Null>(Key))) {Out.clear();return true;}
        return false;
    }
    const FTCHARToUTF8 Utf8(*Value,Value.Len());Out.assign(Utf8.Get(),Utf8.Length());return true;
}
bool Integer(const FObject& O, const TCHAR* Key, int& Out) {
    double D=0;
    if(!O->TryGetNumberField(Key,D) || !FMath::IsFinite(D) || D<0 || D>2147483647.0 || FMath::FloorToDouble(D)!=D) return false;
    Out=static_cast<int>(D);return true;
}
bool Strings(const FObject& O, const TCHAR* Key, std::vector<std::string>& Out, int32 Limit) {
    const TArray<TSharedPtr<FJsonValue>>* A=nullptr;
    if(!O->TryGetArrayField(Key,A) || A->Num()>Limit) return false;
    for(const auto& V:*A) {FString S;if(!V.IsValid() || !V->TryGetString(S)) return false;const FTCHARToUTF8 Utf8(*S,S.Len());Out.emplace_back(Utf8.Get(),Utf8.Length());}
    return true;
}
bool Decode(const FString& Body, const FString& Expected, DaedalusDungeon::Snapshot& Out) {
    int Depth=0;bool InString=false,Escape=false;
    for(TCHAR C:Body) {
        if(InString) {if(Escape) Escape=false;else if(C==TEXT('\\')) Escape=true;else if(C==TEXT('"')) InString=false;}
        else if(C==TEXT('"')) InString=true;
        else if(C==TEXT('{') || C==TEXT('[')) {if(++Depth>32) return false;}
        else if(C==TEXT('}') || C==TEXT(']')) {if(--Depth<0) return false;}
    }
    if(Depth || InString) return false;
    FObject Root;
    const auto Reader=TJsonReaderFactory<>::Create(Body);
    if(!FJsonSerializer::Deserialize(Reader,Root) || !Root.IsValid()) return false;
    FString Type, Id; int Version=0;
    if(!Root->TryGetStringField(TEXT("type"),Type) || Type!=TEXT("game_status") || !Integer(Root,TEXT("version"),Version) || Version!=1
        || !Root->TryGetStringField(TEXT("requestId"),Id) || Id!=Expected) return false;
    const FObject* P=nullptr;
    if(!Root->TryGetObjectField(TEXT("payload"),P) || !P->IsValid()) return false;
    const auto& O=*P;
    if(!Integer(O,TEXT("chaosLevel"),Out.Chaos) || !O->TryGetBoolField(TEXT("combatActive"),Out.Combat)
        || !Strings(O,TEXT("availableChoices"),Out.Choices,64) || !Strings(O,TEXT("recentHistory"),Out.History,30)
        || !String(O,TEXT("location"),Out.Location,true) || !String(O,TEXT("playHint"),Out.PlayHint,true)) return false;
    const TArray<TSharedPtr<FJsonValue>>* Party=nullptr;
    if(!O->TryGetArrayField(TEXT("party"),Party) || Party->Num()<1 || Party->Num()>16) return false;
    for(const auto& V:*Party) {
        const FObject* M=nullptr; DaedalusDungeon::Member Member;
        if(!V.IsValid() || !V->TryGetObject(M) || !M->IsValid() || !String(*M,TEXT("name"),Member.Name)
            || !String(*M,TEXT("role"),Member.Role) || !Integer(*M,TEXT("hp"),Member.Hp)
            || !Integer(*M,TEXT("maxHp"),Member.MaxHp) || !(*M)->TryGetBoolField(TEXT("alive"),Member.Alive)) return false;
        Out.Party.push_back(MoveTemp(Member));
    }
    if(O->HasField(TEXT("quest")) && !O->HasTypedField<EJson::Null>(TEXT("quest"))) {
        const FObject* Q=nullptr;
        if(!O->TryGetObjectField(TEXT("quest"),Q) || !Q->IsValid()) return false;
        Out.HasQuest=true;
        if(!String(*Q,TEXT("title"),Out.QuestTitle) || !String(*Q,TEXT("sceneId"),Out.SceneId,true)
            || !String(*Q,TEXT("sceneDescription"),Out.SceneDescription,true)
            || !(*Q)->TryGetBoolField(TEXT("completed"),Out.Completed) || !(*Q)->TryGetBoolField(TEXT("failed"),Out.Failed)
            || !(*Q)->TryGetNumberField(TEXT("progress"),Out.Progress)) return false;
    }
    return DaedalusDungeon::Valid(Out);
}
}

FDaedalusDungeonClient::~FDaedalusDungeonClient() {Cancel();}
bool FDaedalusDungeonClient::Configure(const FString& Url, const FString& Token) {
    check(IsInGameThread());
    FString NewBase=Url;NewBase.RemoveFromEnd(TEXT("/"));
    // Deployment configuration, never supplied by narration or a remote asset.
    const bool Local=NewBase.StartsWith(TEXT("http://127.0.0.1:")) || NewBase.StartsWith(TEXT("http://localhost:"));
    if((!NewBase.StartsWith(TEXT("https://")) && !Local) || NewBase.Contains(TEXT("?")) || NewBase.Contains(TEXT("#"))
        || NewBase.Contains(TEXT("@")) || NewBase.Contains(TEXT("\n")) || NewBase.Contains(TEXT("\r"))
        || Token.IsEmpty() || Token.Len()>8192 || Token.Contains(TEXT("\n")) || Token.Contains(TEXT("\r"))) {
        LastError=TEXT("A configured HTTPS service (or loopback HTTP) and session bearer are required.");return false;
    }
    if(Base==NewBase && Bearer==Token) return true; // never clear uncertain actions by reconnecting same identity
    if(Policy.Busy()) {LastError=TEXT("Finish or cancel the pending request before changing session.");return false;}
    Base=NewBase;Bearer=Token;Prefix=FGuid::NewGuid().ToString(EGuidFormats::Digits);
    Policy.NewSession();LastError.Empty();return true;
}
bool FDaedalusDungeonClient::Refresh() {
    check(IsInGameThread());
    if(Base.IsEmpty()) {LastError=TEXT("Dungeon Master is not configured.");return false;}
    const uint64 Id=Policy.BeginStatus();return Id && Send(Id,TEXT("GET"),TEXT("/v2/status"),TEXT(""));
}
bool FDaedalusDungeonClient::Choose(int32 Index) {
    check(IsInGameThread());
    std::string Body;
    const uint64 Id=Index<0?0:Policy.BeginAction(static_cast<std::size_t>(Index),Body);
    if(!Id) {LastError=TEXT("Choice unavailable, request pending, or previous action outcome requires host reconciliation.");return false;}
    return Send(Id,TEXT("POST"),TEXT("/v2/action"),UTF8_TO_TCHAR(Body.c_str()));
}
void FDaedalusDungeonClient::Cancel() {
    if(Active.IsValid()) {Active->OnProcessRequestComplete().Unbind();Active->CancelRequest();Active.Reset();}
    // Pending actions remain uncertain, even when transport is cancelled locally.
    // Token is owned by this client, not logged or replicated.
    // Completion is normally handled by Send; cancellation needs its pending ID.
    if(PendingId) Policy.Fail(PendingId);
    PendingId=0;
}
bool FDaedalusDungeonClient::Send(uint64 Id, const FString& Verb, const FString& Path, const FString& Body) {
    const FString RequestId=Prefix+TEXT("-")+LexToString(Id);
    auto Request=FHttpModule::Get().CreateRequest();
    Request->SetDelegateThreadPolicy(EHttpRequestDelegateThreadPolicy::CompleteOnGameThread);
    Request->SetURL(Base+Path);Request->SetVerb(Verb);Request->SetTimeout(10.0f);
    Request->SetHeader(TEXT("Authorization"),TEXT("Bearer ")+Bearer);
    Request->SetHeader(TEXT("X-Request-Id"),RequestId);
    Request->SetHeader(TEXT("Accept"),TEXT("application/json"));
    if(!Body.IsEmpty()) {Request->SetHeader(TEXT("Content-Type"),TEXT("application/json"));Request->SetContentAsString(Body);}
    TWeakPtr<FDaedalusDungeonClient> Weak=AsShared();
    Request->OnProcessRequestComplete().BindLambda([Weak,Id,RequestId](FHttpRequestPtr Req,FHttpResponsePtr Res,bool Ok) {
        const auto Self=Weak.Pin();if(!Self.IsValid() || Self->PendingId!=Id) return;
        Self->Active.Reset();Self->PendingId=0;
        DaedalusDungeon::Snapshot Value;
        if(!Ok || !Res.IsValid() || Res->GetResponseCode()!=200 || Res->GetContent().Num()>static_cast<int32>(DaedalusDungeon::MaxBodyBytes)
            || !Decode(Res->GetContentAsString(),RequestId,Value) || !Self->Policy.Accept(Id,1,"game_status",Value)) {
            Self->Policy.Fail(Id);
            Self->LastError=Self->Policy.ActionUncertain()?TEXT("Action outcome uncertain. Do not retry; host reconciliation required.")
                :TEXT("Dungeon status unavailable or invalid; retaining last valid display.");
            return;
        }
        Self->LastError=Self->Policy.ActionUncertain()?TEXT("Status refreshed; previous action still requires host reconciliation."):TEXT("");
    });
    Active=Request;PendingId=Id;
    if(!Request->ProcessRequest()) {Request->OnProcessRequestComplete().Unbind();Active.Reset();PendingId=0;Policy.Fail(Id);LastError=TEXT("Dungeon request could not start.");return false;}
    return true;
}

