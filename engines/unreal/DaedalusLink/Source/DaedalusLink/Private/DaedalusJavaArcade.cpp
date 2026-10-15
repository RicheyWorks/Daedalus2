// SPDX-License-Identifier: MIT
#include "DaedalusJavaArcade.h"

#include "DaedalusHero.h"
#include "SDaedalusJavaArcade.h"
#include "Async/Async.h"
#include "Components/StaticMeshComponent.h"
#include "Dom/JsonObject.h"
#include "Engine/GameViewportClient.h"
#include "Engine/LocalPlayer.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "Framework/Application/SlateApplication.h"
#include "GameFramework/PlayerController.h"
#include "GenericPlatform/GenericPlatformHttp.h"
#include "HAL/PlatformTime.h"
#include "HttpModule.h"
#include "IWebSocket.h"
#include "Misc/Base64.h"
#include "Misc/Guid.h"
#include "Misc/ScopeLock.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "UObject/ConstructorHelpers.h"
#include "WebSocketsModule.h"
#include "Widgets/SWeakWidget.h"

THIRD_PARTY_INCLUDES_START
#include <curl/curl.h>
THIRD_PARTY_INCLUDES_END

namespace JA = daedalus::java_arcade;

namespace JavaArcadeWire
{
    constexpr int64 MaxSafeInteger = 9007199254740991LL;
    bool HeaderValue(const FString& Value, int32 Max = 4096)
    {
        if (Value.IsEmpty() || Value.Len() > Max) return false;
        for (TCHAR C : Value) if (C < 32 || C > 126) return false;
        return true;
    }
    bool Origin(const FString& Candidate, FString& Out)
    {
        std::string Normalized;
        const FTCHARToUTF8 Converted(*Candidate, Candidate.Len());
        if (!JA::LoopbackOrigin(std::string(Converted.Get(), Converted.Length()), Normalized)) return false;
        Out = UTF8_TO_TCHAR(Normalized.c_str());
        return true;
    }
    bool String(const TSharedPtr<FJsonObject>& Json, const TCHAR* Name, FString& Out, int32 Max, bool bEmpty = false)
    {
        const TSharedPtr<FJsonValue>* Field = Json.IsValid() ? Json->Values.Find(Name) : nullptr;
        if (!Field || !Field->IsValid() || (*Field)->Type != EJson::String || !(*Field)->TryGetString(Out)
            || Out.Len() > Max || (!bEmpty && Out.IsEmpty())) return false;
        for (TCHAR C : Out) if (C == 0) return false;
        return true;
    }
    template<typename IntegerType>
    bool Integer(const TSharedPtr<FJsonObject>& Json, const TCHAR* Name, IntegerType& Out, int64 Min = 0, int64 Max = MaxSafeInteger)
    {
        double Number = 0;
        const TSharedPtr<FJsonValue>* Field = Json.IsValid() ? Json->Values.Find(Name) : nullptr;
        if (!Field || !Field->IsValid() || (*Field)->Type != EJson::Number || !(*Field)->TryGetNumber(Number) || !FMath::IsFinite(Number)
            || Number < static_cast<double>(Min) || Number > static_cast<double>(Max) || FMath::FloorToDouble(Number) != Number) return false;
        Out = static_cast<IntegerType>(Number);
        return true;
    }
    bool Bool(const TSharedPtr<FJsonObject>& Json, const TCHAR* Name, bool& Out)
    {
        const TSharedPtr<FJsonValue>* Field = Json.IsValid() ? Json->Values.Find(Name) : nullptr;
        return Field && Field->IsValid() && (*Field)->Type == EJson::Boolean && (*Field)->TryGetBool(Out);
    }
    bool DecimalLong(const TSharedPtr<FJsonObject>& Json, const TCHAR* Name, FString& Out, bool bSigned = false)
    {
        if (!String(Json, Name, Out, 20)) return false;
        const bool bNegative = Out[0] == TEXT('-');
        if (bNegative && !bSigned) return false;
        const int32 Start = bNegative ? 1 : 0;
        const int32 Digits = Out.Len() - Start;
        if (Digits < 1 || Digits > 19 || (Digits > 1 && Out[Start] == TEXT('0')) || (bNegative && Out == TEXT("-0"))) return false;
        for (int32 I = Start; I < Out.Len(); ++I) if (Out[I] < TEXT('0') || Out[I] > TEXT('9')) return false;
        const FString Limit = bNegative ? TEXT("9223372036854775808") : TEXT("9223372036854775807");
        return Digits < 19 || Out.Mid(Start).Compare(Limit, ESearchCase::CaseSensitive) <= 0;
    }
    bool SafeText(const FString& Text)
    {
        // Bound recursive JSON parser depth before parsing. Braces inside quoted strings do not count.
        int32 Depth = 0;
        bool bString = false;
        bool bEscape = false;
        for (TCHAR C : Text)
        {
            if (C == 0) return false;
            if (bString)
            {
                if (bEscape) bEscape = false;
                else if (C == TEXT('\\')) bEscape = true;
                else if (C == TEXT('"')) bString = false;
            }
            else if (C == TEXT('"')) bString = true;
            else if (C == TEXT('{') || C == TEXT('[')) { if (++Depth > 32) return false; }
            else if (C == TEXT('}') || C == TEXT(']')) { if (--Depth < 0) return false; }
        }
        return !bString && Depth == 0;
    }
    bool Secrets(const TSharedPtr<FJsonValue>& Value, int32 Depth = 0)
    {
        if (!Value.IsValid() || Depth > 32) return true;
        if (Value->Type == EJson::Object)
        {
            const TSharedPtr<FJsonObject> Object = Value->AsObject();
            for (const auto& Pair : Object->Values)
            {
                const FString Key = FString(*Pair.Key).ToLower();
                if (Key == TEXT("solution") || Key == TEXT("solvedgrid") || Key == TEXT("liveroundstate")
                    || Key == TEXT("rngstate") || Key == TEXT("holecard") || Key == TEXT("shoecards") || Key == TEXT("token")) return true;
                if (Key == TEXT("shoe") && Pair.Value.IsValid() && Pair.Value->Type == EJson::Object
                    && Pair.Value->AsObject()->HasField(TEXT("cards"))) return true;
                if (Secrets(Pair.Value, Depth + 1)) return true;
            }
        }
        else if (Value->Type == EJson::Array)
            for (const auto& Child : Value->AsArray()) if (Secrets(Child, Depth + 1)) return true;
        return false;
    }
    TSharedPtr<FJsonObject> Parse(const FString& Text)
    {
        if (!SafeText(Text)) return nullptr;
        TSharedPtr<FJsonObject> Result;
        if (!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text), Result) || !Result.IsValid()) return nullptr;
        if (Secrets(MakeShared<FJsonValueObject>(Result))) return nullptr;
        return Result;
    }
    FString Encode(const FString& Value) { return FGenericPlatformHttp::UrlEncode(Value); }
    FString Json(const TSharedPtr<FJsonObject>& Object)
    {
        FString Out;
        FJsonSerializer::Serialize(Object.ToSharedRef(), TJsonWriterFactory<>::Create(&Out));
        return Out;
    }
    bool Card(const TSharedPtr<FJsonValue>& Value, JA::VisibleCard& Out)
    {
        if (!Value.IsValid() || Value->Type != EJson::Object) return false;
        FString Rank, Suit;
        if (!String(Value->AsObject(), TEXT("rank"), Rank, 2) || !String(Value->AsObject(), TEXT("suit"), Suit, 8)) return false;
        Out = { TCHAR_TO_UTF8(*Rank), TCHAR_TO_UTF8(*Suit) };
        return JA::ValidCard(Out);
    }
    bool Cards(const TSharedPtr<FJsonObject>& Json, const TCHAR* Name, std::vector<JA::VisibleCard>& Out)
    {
        const TArray<TSharedPtr<FJsonValue>>* Values = nullptr;
        if (!Json->TryGetArrayField(Name, Values) || Values->Num() > 21) return false;
        for (const auto& Value : *Values) { JA::VisibleCard C; if (!Card(Value, C)) return false; Out.push_back(C); }
        return true;
    }
    FDaedalusJavaCard Reflect(const JA::VisibleCard& Card)
    {
        FDaedalusJavaCard Out; Out.Rank = UTF8_TO_TCHAR(Card.Rank.c_str()); Out.Suit = UTF8_TO_TCHAR(Card.Suit.c_str()); return Out;
    }
}

/** One bounded blocking libcurl task on a pool worker; no UObject is touched off the game thread.
 * UE HTTP's public interface cannot disable redirects. This small transport explicitly does. */
class FJavaArcadeHttpTask : public TSharedFromThis<FJavaArcadeHttpTask, ESPMode::ThreadSafe>
{
public:
    JA::Ticket Ticket;
    uint8 Operation = 0;
    FString Url;
    FString Verb;
    FString Body;
    TArray<FString> RequestHeaders;
    TArray<FString> ResponseHeaders;
    TArray<uint8> Response;
    SIZE_T Limit = 65536;
    int32 StatusCode = 0;
    bool bSuccess = false;
    bool bRedirect = false;
    SIZE_T HeaderBytes = 0;
    TAtomic<bool> bCancelled{false};
    TAtomic<bool> bDone{false};

    static SIZE_T Write(char* Data, SIZE_T Size, SIZE_T Count, void* User)
    {
        auto* Task = static_cast<FJavaArcadeHttpTask*>(User);
        if (Task->bCancelled.Load() || (Count > 0 && Size > Task->Limit / Count)) return 0;
        const SIZE_T Bytes = Size * Count;
        if (Bytes > Task->Limit - static_cast<SIZE_T>(Task->Response.Num())) return 0;
        Task->Response.Append(reinterpret_cast<const uint8*>(Data), static_cast<int32>(Bytes));
        return Bytes;
    }
    static SIZE_T Header(char* Data, SIZE_T Size, SIZE_T Count, void* User)
    {
        auto* Task = static_cast<FJavaArcadeHttpTask*>(User);
        if (Task->bCancelled.Load() || (Count > 0 && Size > 8192 / Count)) return 0;
        const SIZE_T Bytes = Size * Count;
        if (Bytes > 8192 - Task->HeaderBytes || Task->ResponseHeaders.Num() >= 64) return 0;
        Task->HeaderBytes += Bytes;
        const FUTF8ToTCHAR Converted(Data, static_cast<int32>(Bytes));
        const FString Line(Converted.Length(), Converted.Get());
        Task->ResponseHeaders.Add(Line.TrimStartAndEnd());
        if (Line.StartsWith(TEXT("Location:"), ESearchCase::IgnoreCase)) Task->bRedirect = true;
        return Bytes;
    }
    static int Progress(void* User, curl_off_t, curl_off_t, curl_off_t, curl_off_t)
    {
        return static_cast<FJavaArcadeHttpTask*>(User)->bCancelled.Load() ? 1 : 0;
    }
    void Run()
    {
        CURL* Curl = curl_easy_init();
        curl_slist* Headers = nullptr;
        if (Curl)
        {
            const FTCHARToUTF8 UrlUtf8(*Url), VerbUtf8(*Verb), BodyUtf8(*Body);
            for (const FString& H : RequestHeaders) Headers = curl_slist_append(Headers, TCHAR_TO_UTF8(*H));
            curl_easy_setopt(Curl, CURLOPT_URL, UrlUtf8.Get());
            curl_easy_setopt(Curl, CURLOPT_CUSTOMREQUEST, VerbUtf8.Get());
            curl_easy_setopt(Curl, CURLOPT_HTTPHEADER, Headers);
            curl_easy_setopt(Curl, CURLOPT_PROTOCOLS_STR, "http");
            curl_easy_setopt(Curl, CURLOPT_PATH_AS_IS, 1L);
            curl_easy_setopt(Curl, CURLOPT_FOLLOWLOCATION, 0L);
            curl_easy_setopt(Curl, CURLOPT_MAXREDIRS, 0L);
            curl_easy_setopt(Curl, CURLOPT_PROXY, "");
            curl_easy_setopt(Curl, CURLOPT_NOSIGNAL, 1L);
            curl_easy_setopt(Curl, CURLOPT_CONNECTTIMEOUT_MS, 3000L);
            curl_easy_setopt(Curl, CURLOPT_TIMEOUT_MS, 10000L);
            curl_easy_setopt(Curl, CURLOPT_WRITEFUNCTION, Write);
            curl_easy_setopt(Curl, CURLOPT_WRITEDATA, this);
            curl_easy_setopt(Curl, CURLOPT_HEADERFUNCTION, Header);
            curl_easy_setopt(Curl, CURLOPT_HEADERDATA, this);
            curl_easy_setopt(Curl, CURLOPT_NOPROGRESS, 0L);
            curl_easy_setopt(Curl, CURLOPT_XFERINFOFUNCTION, Progress);
            curl_easy_setopt(Curl, CURLOPT_XFERINFODATA, this);
            if (Verb != TEXT("GET"))
            {
                curl_easy_setopt(Curl, CURLOPT_POSTFIELDS, BodyUtf8.Get());
                curl_easy_setopt(Curl, CURLOPT_POSTFIELDSIZE_LARGE, static_cast<curl_off_t>(BodyUtf8.Length()));
            }
            const CURLcode Result = curl_easy_perform(Curl);
            long Code = 0;
            curl_easy_getinfo(Curl, CURLINFO_RESPONSE_CODE, &Code);
            StatusCode = static_cast<int32>(Code);
            bSuccess = Result == CURLE_OK && !bCancelled.Load() && !bRedirect && Code < 300;
            curl_easy_cleanup(Curl);
        }
        curl_slist_free_all(Headers);
        RequestHeaders.Reset(); Body.Reset(); // Do not retain credentials or command text after transport.
        bDone.Store(true);
    }
};

class FJavaArcadeSocketInbox
{
public:
    FCriticalSection Lock;
    TArray<FString> Messages;
    int32 Bytes = 0;
    bool bConnected = false;
    bool bFailure = false;
    bool bPermanent = false;
    void Add(const FString& Message)
    {
        FScopeLock Scope(&Lock);
        const int32 Size = FTCHARToUTF8(*Message).Length();
        if (Size > 65536 || Messages.Num() >= 8 || Bytes > 131072 - Size) { bFailure = true; bPermanent = true; return; }
        Messages.Add(Message); Bytes += Size;
    }
};

ADaedalusJavaArcade::ADaedalusJavaArcade()
{
    PrimaryActorTick.bCanEverTick = false;
    static ConstructorHelpers::FObjectFinder<UStaticMesh> Cube(TEXT("/Engine/BasicShapes/Cube.Cube"));
    if (Cube.Succeeded()) Body->SetStaticMesh(Cube.Object);
    Body->SetRelativeScale3D(FVector(0.8f, 0.5f, 1.1f));
    Tags.Add(TEXT("DaedalusJavaArcade"));
}
void ADaedalusJavaArcade::OnConstruction(const FTransform& Transform)
{
    Super::OnConstruction(Transform);
    if (!IsTemplate() && CabinetId.IsEmpty()) CabinetId = FGuid::NewGuid().ToString(EGuidFormats::Digits);
}
void ADaedalusJavaArcade::PostDuplicate(EDuplicateMode::Type Mode)
{
    Super::PostDuplicate(Mode);
    if (!IsTemplate() && Mode == EDuplicateMode::Normal) CabinetId = FGuid::NewGuid().ToString(EGuidFormats::Digits);
}
void ADaedalusJavaArcade::BeginPlay()
{
    Super::BeginPlay();
    if (CabinetId.IsEmpty()) CabinetId = FGuid::NewGuid().ToString(EGuidFormats::Digits);
    TWeakObjectPtr<ADaedalusJavaArcade> Self(this);
    TickHandle = FTSTicker::GetCoreTicker().AddTicker(FTickerDelegate::CreateLambda([Self](float Delta)
    {
        return Self.IsValid() ? Self->CoreTick(Delta) : false;
    }));
}
void ADaedalusJavaArcade::SetMessage(const TCHAR* Text) { View.Message = Text; }
FString ADaedalusJavaArcade::Prompt(const ADaedalusHero* Hero) const
{
    return Game == EDaedalusJavaGame::Sudoku ? TEXT("Play Sudoku") : TEXT("Play Blackjack (simulated credits)");
}
bool ADaedalusJavaArcade::HasCredentials() const
{
    return Game == EDaedalusJavaGame::Sudoku ? !BasicAuthorization.IsEmpty() : !BlackjackAuthorization.IsEmpty();
}
void ADaedalusJavaArcade::StopSocket()
{
    if (Socket.IsValid())
    {
        Socket->OnConnected().Clear(); Socket->OnMessage().Clear(); Socket->OnClosed().Clear(); Socket->OnConnectionError().Clear();
        Socket->Close(1000, TEXT("Cabinet closed"));
    }
    Socket.Reset(); SocketInbox.Reset();
}
void ADaedalusJavaArcade::CancelTransport(bool bForgetSecrets)
{
    Guard.Close();
    if (HttpTask.IsValid()) HttpTask->bCancelled.Store(true);
    StopSocket();
    LastReadOperation = Operation::None;
    bAwaitingSudokuReconcile = false; bUnknownBlackjackCreate = false;
    PendingRequestId.Reset(); PendingRequestBody.Reset(); CreateRequestId.Reset();
    Sudoku = {}; Blackjack = {}; View = {}; ActiveGame = Game; View.Game = ActiveGame;
    CsrfToken.Reset(); CsrfHeader.Reset(); CookieJar.Reset(); AuthenticatedPlayerId.Reset(); ActiveOrigin.Reset();
    if (bForgetSecrets) { BasicAuthorization.Reset(); BlackjackAuthorization.Reset(); }
}
bool ADaedalusJavaArcade::ConfigureSudokuCredentials(const FString& Username, const FString& Password)
{
    if (Username.IsEmpty() || Username.Len() > 128 || Username.Contains(TEXT(":")) || Password.IsEmpty() || Password.Len() > 256) return false;
    CancelTransport(true); Game = EDaedalusJavaGame::Sudoku; ActiveGame = Game; View.Game = Game;
    BasicAuthorization = TEXT("Basic ") + FBase64::Encode(Username + TEXT(":") + Password);
    SetMessage(TEXT("Credentials configured in memory. Start a Java Sudoku game."));
    return true;
}

bool ADaedalusJavaArcade::ApplySudoku(const TSharedPtr<FJsonObject>& Json)
{
    JA::SudokuView Candidate;
    FString Id, BoardOwner;
    int64 Number = 0;
    if (!JavaArcadeWire::String(Json, TEXT("gameId"), Id, 256) || !JavaArcadeWire::String(Json, TEXT("playerId"), BoardOwner, 128)
        || BoardOwner != AuthenticatedPlayerId || (!RequestedSudokuId.IsEmpty() && Id != RequestedSudokuId)) return false;
    Candidate.GameId = TCHAR_TO_UTF8(*Id); Candidate.Owner = TCHAR_TO_UTF8(*BoardOwner);
    if (!JavaArcadeWire::Integer(Json, TEXT("difficulty"), Number, 1, 5)) return false;
    Candidate.Difficulty = static_cast<int>(Number);
    if (!JavaArcadeWire::Integer(Json, TEXT("lives"), Number, 0, 1000)) return false;
    Candidate.Lives = static_cast<int>(Number);
    if (!JavaArcadeWire::Integer(Json, TEXT("score"), Candidate.Score, -JavaArcadeWire::MaxSafeInteger)
        || !JavaArcadeWire::Integer(Json, TEXT("hintCount"), Candidate.HintCount)
        || !JavaArcadeWire::Integer(Json, TEXT("moveCount"), Candidate.MoveCount)
        || !JavaArcadeWire::Integer(Json, TEXT("elapsedSeconds"), Candidate.ElapsedSeconds)
        || !JavaArcadeWire::Integer(Json, TEXT("timeLimitSeconds"), Candidate.TimeLimitSeconds)
        || !JavaArcadeWire::Integer(Json, TEXT("secondsLeft"), Candidate.SecondsLeft)
        || !JavaArcadeWire::Bool(Json, TEXT("solved"), Candidate.Solved)
        || !JavaArcadeWire::Bool(Json, TEXT("timeUp"), Candidate.TimeUp)
        || !JavaArcadeWire::Bool(Json, TEXT("chaosMode"), Candidate.ChaosMode)
        || !JavaArcadeWire::Bool(Json, TEXT("mirrorMode"), Candidate.MirrorMode)) return false;
    const TArray<TSharedPtr<FJsonValue>>* Rows = nullptr;
    if (!Json->TryGetArrayField(TEXT("cells"), Rows) || Rows->Num() != 9) return false;
    int32 Index = 0;
    for (const auto& Row : *Rows)
    {
        if (!Row.IsValid() || Row->Type != EJson::Array || Row->AsArray().Num() != 9) return false;
        for (const auto& Cell : Row->AsArray())
        {
            if (!Cell.IsValid() || Cell->Type != EJson::Object) return false;
            const TSharedPtr<FJsonObject> C = Cell->AsObject();
            if (!JavaArcadeWire::Integer(C, TEXT("value"), Number, 0, 9) || !JavaArcadeWire::Bool(C, TEXT("isGiven"), Candidate.Givens[Index])) return false;
            Candidate.Values[Index] = static_cast<int>(Number);
            const TArray<TSharedPtr<FJsonValue>>* Marks = nullptr;
            if (!C->TryGetArrayField(TEXT("pencilMarks"), Marks) || Marks->Num() > 9) return false;
            for (const auto& Mark : *Marks)
            {
                double Digit = 0;
                if (!Mark.IsValid() || Mark->Type != EJson::Number || !Mark->TryGetNumber(Digit) || Digit < 1 || Digit > 9 || FMath::FloorToDouble(Digit) != Digit) return false;
                Candidate.PencilMasks[Index] |= static_cast<uint16>(1u << static_cast<unsigned>(Digit));
            }
            ++Index;
        }
    }
    if (!JA::ValidSudoku(Candidate)) return false;
    // Atomic projection: malformed/wrong-board replies never partially replace an existing view.
    FDaedalusJavaArcadeState Next;
    Next.Game = EDaedalusJavaGame::Sudoku; Next.SessionId = Id; Next.bOwner = true;
    Next.Difficulty = Candidate.Difficulty; Next.Score = Candidate.Score; Next.Lives = Candidate.Lives;
    Next.bSolved = Candidate.Solved; Next.bTimeUp = Candidate.TimeUp;
    Next.bChaosMode = Candidate.ChaosMode; Next.bMirrorMode = Candidate.MirrorMode;
    Next.ElapsedSeconds = Candidate.ElapsedSeconds; Next.TimeLimitSeconds = Candidate.TimeLimitSeconds;
    Next.SecondsLeft = Candidate.SecondsLeft; Next.HintCount = Candidate.HintCount; Next.MoveCount = Candidate.MoveCount;
    for (int32 I = 0; I < 81; ++I) { Next.Cells.Add(Candidate.Values[I]); Next.Givens.Add(Candidate.Givens[I]); Next.PencilMasks.Add(Candidate.PencilMasks[I]); }
    Next.Message = View.Message; Next.HintText = View.HintText;
    Sudoku = std::move(Candidate); View = MoveTemp(Next); RequestedSudokuId = Id;
    return true;
}

bool ADaedalusJavaArcade::ApplyBlackjack(const TSharedPtr<FJsonObject>& Json, const FString& ExpectedId)
{
    JA::BlackjackView Candidate;
    FString GameId, Id, RequestId, Phase;
    int64 Number = 0;
    const TSharedPtr<FJsonObject>* Snapshot = nullptr;
    if (!JavaArcadeWire::Integer(Json, TEXT("apiVersion"), Number, 1, 1)
        || !JavaArcadeWire::String(Json, TEXT("gameId"), GameId, 16) || GameId != TEXT("blackjack")
        || !JavaArcadeWire::String(Json, TEXT("sessionId"), Id, 64)
        || !JavaArcadeWire::Integer(Json, TEXT("revision"), Candidate.Revision)
        || !JavaArcadeWire::Bool(Json, TEXT("closed"), Candidate.Closed)
        || !Json->TryGetObjectField(TEXT("snapshot"), Snapshot)) return false;
    if ((!Blackjack.SessionId.empty() && Id != UTF8_TO_TCHAR(Blackjack.SessionId.c_str())) || Candidate.Revision < Blackjack.Revision) return false;
    if (!ExpectedId.IsEmpty() && (!JavaArcadeWire::String(Json, TEXT("requestId"), RequestId, 64) || RequestId != ExpectedId)) return false;
    const auto& S = *Snapshot;
    Candidate.SessionId = TCHAR_TO_UTF8(*Id);
    if (!JavaArcadeWire::String(S, TEXT("phase"), Phase, 16)
        || !JavaArcadeWire::Integer(S, TEXT("bankroll"), Candidate.Bankroll)
        || !JavaArcadeWire::Integer(S, TEXT("pendingBet"), Candidate.PendingBet)
        || !JavaArcadeWire::Integer(S, TEXT("activeHand"), Number, -1, 3)) return false;
    Candidate.Phase = TCHAR_TO_UTF8(*Phase); Candidate.ActiveHand = static_cast<int>(Number);
    const TArray<TSharedPtr<FJsonValue>>* Hands = nullptr;
    if (!S->TryGetArrayField(TEXT("playerHands"), Hands) || Hands->Num() > 4) return false;
    for (const auto& Hand : *Hands)
    {
        if (!Hand.IsValid() || Hand->Type != EJson::Object) return false;
        JA::VisibleHand H;
        if (!JavaArcadeWire::Cards(Hand->AsObject(), TEXT("cards"), H.Cards)
            || !JavaArcadeWire::Integer(Hand->AsObject(), TEXT("bet"), H.Bet)
            || !JavaArcadeWire::Integer(Hand->AsObject(), TEXT("value"), Number, 0, 231)) return false;
        H.Value = static_cast<int>(Number); Candidate.Hands.push_back(std::move(H));
    }
    const TSharedPtr<FJsonObject>* Dealer = nullptr;
    if (!S->TryGetObjectField(TEXT("dealer"), Dealer) || !JavaArcadeWire::Cards(*Dealer, TEXT("cards"), Candidate.DealerCards)
        || !JavaArcadeWire::Integer(*Dealer, TEXT("hiddenCardCount"), Number, 0, 1)) return false;
    Candidate.HiddenDealerCards = static_cast<int>(Number);
    for (const TCHAR* Key : { TEXT("value"), TEXT("soft"), TEXT("bust"), TEXT("blackjack") })
    {
        const TSharedPtr<FJsonValue>* Value = (*Dealer)->Values.Find(Key);
        if (!Value || !Value->IsValid()) return false;
        if ((*Value)->Type != EJson::Null) Candidate.HasDealerDerivedValues = true;
    }
    const TArray<TSharedPtr<FJsonValue>>* Actions = nullptr;
    const TArray<TSharedPtr<FJsonValue>>* Bets = nullptr;
    if (!S->TryGetArrayField(TEXT("legalActions"), Actions) || Actions->Num() > 16
        || !S->TryGetArrayField(TEXT("legalBetAmounts"), Bets) || Bets->Num() > 5) return false;
    for (const auto& A : *Actions) { FString Name; if (!A.IsValid() || A->Type != EJson::String || !A->TryGetString(Name) || !JavaArcadeWire::HeaderValue(Name, 32)) return false; Candidate.LegalActions.emplace_back(TCHAR_TO_UTF8(*Name)); }
    for (const auto& B : *Bets) { double Amount = 0; if (!B.IsValid() || B->Type != EJson::Number || !B->TryGetNumber(Amount) || Amount < 0 || Amount > 500 || FMath::FloorToDouble(Amount) != Amount) return false; Candidate.LegalBetAmounts.push_back(static_cast<int>(Amount)); }
    if (!JA::ValidBlackjack(Candidate)) return false;
    FDaedalusJavaArcadeState Next;
    Next.Game = EDaedalusJavaGame::Blackjack; Next.bOwner = true; Next.SessionId = Id; Next.Revision = Candidate.Revision;
    Next.bRemoteClosed = Candidate.Closed; Next.Phase = Phase; Next.Bankroll = Candidate.Bankroll; Next.PendingBet = Candidate.PendingBet; Next.ActiveHand = Candidate.ActiveHand;
    Next.HiddenDealerCards = Candidate.HiddenDealerCards;
    if (!JavaArcadeWire::String(*Dealer, TEXT("caption"), Next.DealerCaption, 256, true)
        || !JavaArcadeWire::String(S, TEXT("resultText"), Next.ResultText, 512, true)
        || !JavaArcadeWire::Bool(S, TEXT("insuranceAcceptAllowed"), Next.bInsuranceAcceptAllowed)) return false;
    const TSharedPtr<FJsonObject>* Rules = nullptr;
    const TSharedPtr<FJsonObject>* Stats = nullptr;
    const TSharedPtr<FJsonObject>* Shoe = nullptr;
    if (!S->TryGetObjectField(TEXT("rules"), Rules) || !S->TryGetObjectField(TEXT("stats"), Stats)
        || !S->TryGetObjectField(TEXT("shoe"), Shoe)) return false;
    auto& R = Next.BlackjackRules;
    const TSharedPtr<FJsonValue>* Penetration = (*Rules)->Values.Find(TEXT("penetration"));
    if (!JavaArcadeWire::Integer(*Rules, TEXT("decks"), R.Decks, 1, 8)
        || (R.Decks != 1 && R.Decks != 2 && R.Decks != 4 && R.Decks != 6 && R.Decks != 8)
        || !JavaArcadeWire::Integer(*Rules, TEXT("maxHands"), R.MaxHands, 2, 4)
        || !Penetration || !Penetration->IsValid() || (*Penetration)->Type != EJson::Number
        || !(*Penetration)->TryGetNumber(R.Penetration)
        || !FMath::IsFinite(R.Penetration) || R.Penetration < 0 || R.Penetration > 1
        || !JavaArcadeWire::Bool(*Rules, TEXT("dealerHitsSoft17"), R.bDealerHitsSoft17)
        || !JavaArcadeWire::Bool(*Rules, TEXT("lateSurrender"), R.bLateSurrender)
        || !JavaArcadeWire::Bool(*Rules, TEXT("offerInsurance"), R.bOfferInsurance)
        || !JavaArcadeWire::Bool(*Rules, TEXT("doubleAfterSplit"), R.bDoubleAfterSplit)
        || !JavaArcadeWire::Bool(*Rules, TEXT("splitAcesOneCard"), R.bSplitAcesOneCard)
        || !JavaArcadeWire::Integer(*Rules, TEXT("blackjackPayoutNum"), R.BlackjackPayoutNum, 0, 2147483647LL)
        || !JavaArcadeWire::Integer(*Rules, TEXT("blackjackPayoutDen"), R.BlackjackPayoutDen, 1, 2147483647LL)
        || !JavaArcadeWire::Integer(*Rules, TEXT("insurancePayoutNum"), R.InsurancePayoutNum, 0, 2147483647LL)
        || !JavaArcadeWire::Integer(*Rules, TEXT("insurancePayoutDen"), R.InsurancePayoutDen, 1, 2147483647LL)) return false;
    auto& T = Next.BlackjackStats;
    if (!JavaArcadeWire::Integer(*Stats, TEXT("hands"), T.Hands, 0, 2147483647LL)
        || !JavaArcadeWire::Integer(*Stats, TEXT("wins"), T.Wins, 0, 2147483647LL)
        || !JavaArcadeWire::Integer(*Stats, TEXT("losses"), T.Losses, 0, 2147483647LL)
        || !JavaArcadeWire::Integer(*Stats, TEXT("pushes"), T.Pushes, 0, 2147483647LL)
        || !JavaArcadeWire::Integer(*Stats, TEXT("blackjacks"), T.Blackjacks, 0, 2147483647LL)
        || !JavaArcadeWire::Integer(*Stats, TEXT("busts"), T.Busts, 0, 2147483647LL)
        || !JavaArcadeWire::Integer(*Stats, TEXT("doubles"), T.Doubles, 0, 2147483647LL)
        || !JavaArcadeWire::Integer(*Stats, TEXT("splits"), T.Splits, 0, 2147483647LL)
        || !JavaArcadeWire::Integer(*Stats, TEXT("surrenders"), T.Surrenders, 0, 2147483647LL)
        || !JavaArcadeWire::Integer(*Stats, TEXT("peakBankroll"), T.PeakBankroll, 0, 2147483647LL)
        || !JavaArcadeWire::DecimalLong(*Stats, TEXT("totalWagered"), T.TotalWagered)
        || !JavaArcadeWire::DecimalLong(*Stats, TEXT("totalReturned"), T.TotalReturned)
        || !JavaArcadeWire::DecimalLong(*Stats, TEXT("net"), T.Net, true)) return false;
    auto& Q = Next.BlackjackShoe;
    if (!JavaArcadeWire::Integer(*Shoe, TEXT("decks"), Q.Decks, 1, 8) || Q.Decks != R.Decks
        || !JavaArcadeWire::Integer(*Shoe, TEXT("remaining"), Q.Remaining, 0, Q.Decks * 52)
        || !JavaArcadeWire::Integer(*Shoe, TEXT("reshuffleAt"), Q.ReshuffleAt, 0, Q.Decks * 52)
        || !JavaArcadeWire::Bool(*Shoe, TEXT("needsShuffle"), Q.bNeedsShuffle)
        || !JavaArcadeWire::Integer(S, TEXT("insuranceBet"), Next.InsuranceBet, 0, 2147483647LL)
        || !JavaArcadeWire::Integer(S, TEXT("lastNet"), Next.LastNet, -2147483648LL, 2147483647LL)
        || !JavaArcadeWire::Integer(S, TEXT("lastInsurance"), Next.LastInsurance, 0, 2147483647LL)
        || !JavaArcadeWire::Integer(S, TEXT("lastInsuranceReturn"), Next.LastInsuranceReturn, 0, 2147483647LL)) return false;
    const TArray<TSharedPtr<FJsonValue>>* Outcomes = nullptr;
    if (!S->TryGetArrayField(TEXT("lastOutcomes"), Outcomes) || Outcomes->Num() > 4) return false;
    for (const auto& Outcome : *Outcomes)
    {
        FString Name;
        if (!Outcome.IsValid() || Outcome->Type != EJson::String || !Outcome->TryGetString(Name)
            || (Name != TEXT("BLACKJACK") && Name != TEXT("WIN") && Name != TEXT("PUSH")
                && Name != TEXT("LOSS") && Name != TEXT("BUST") && Name != TEXT("SURRENDER"))) return false;
        Next.LastOutcomes.Add(Name);
    }
    Next.bDealerValueAvailable = Candidate.HasDealerDerivedValues;
    if (Next.bDealerValueAvailable
        && (!JavaArcadeWire::Integer(*Dealer, TEXT("value"), Next.DealerValue, 0, 231)
            || !JavaArcadeWire::Bool(*Dealer, TEXT("soft"), Next.bDealerSoft)
            || !JavaArcadeWire::Bool(*Dealer, TEXT("bust"), Next.bDealerBust)
            || !JavaArcadeWire::Bool(*Dealer, TEXT("blackjack"), Next.bDealerBlackjack))) return false;
    for (int32 I = 0; I < static_cast<int32>(Candidate.Hands.size()); ++I)
    {
        const auto& H = Candidate.Hands[static_cast<std::size_t>(I)];
        const auto Hand = (*Hands)[I]->AsObject();
        FDaedalusJavaHand Reflected; Reflected.Bet = H.Bet; Reflected.Value = H.Value;
        if (!JavaArcadeWire::Bool(Hand, TEXT("soft"), Reflected.bSoft)
            || !JavaArcadeWire::Bool(Hand, TEXT("bust"), Reflected.bBust)
            || !JavaArcadeWire::Bool(Hand, TEXT("blackjack"), Reflected.bBlackjack)
            || !JavaArcadeWire::Bool(Hand, TEXT("doubled"), Reflected.bDoubled)
            || !JavaArcadeWire::Bool(Hand, TEXT("surrendered"), Reflected.bSurrendered)
            || !JavaArcadeWire::Bool(Hand, TEXT("fromSplit"), Reflected.bFromSplit)
            || !JavaArcadeWire::Bool(Hand, TEXT("splitAce"), Reflected.bSplitAce)
            || !JavaArcadeWire::Bool(Hand, TEXT("stood"), Reflected.bStood)) return false;
        for (const auto& C : H.Cards) Reflected.Cards.Add(JavaArcadeWire::Reflect(C));
        Next.PlayerHands.Add(MoveTemp(Reflected));
    }
    for (const auto& C : Candidate.DealerCards) Next.DealerCards.Add(JavaArcadeWire::Reflect(C));
    for (const auto& A : Candidate.LegalActions) Next.LegalActions.Add(UTF8_TO_TCHAR(A.c_str()));
    for (int B : Candidate.LegalBetAmounts) Next.LegalBetAmounts.Add(B);
    Next.bBlackjackDetailsAvailable = true;
    Next.Message = View.Message;
    Blackjack = std::move(Candidate); View = MoveTemp(Next);
    return true;
}

bool ADaedalusJavaArcade::BeginSudoku(bool bCreate, const FString& ExistingId, int32 Difficulty, bool bResume,
    bool bChaos, bool bMirror, bool bTimeAttack)
{
    FString Origin;
    if (HttpTask.IsValid() || BasicAuthorization.IsEmpty() || Difficulty < 1 || Difficulty > 5
        || (!bCreate && (ExistingId.IsEmpty() || ExistingId.Len() > 256))
        || !JavaArcadeWire::Origin(SudokuOrigin, Origin)) return false;
    StopSocket(); Guard.Open(); Sudoku = {}; Blackjack = {}; View = {}; Game = EDaedalusJavaGame::Sudoku; ActiveGame = Game; View.Game = Game;
    ActiveOrigin = Origin; bCreateSudoku = bCreate; bResumeSudoku = bResume; RequestedSudokuId = ExistingId; RequestedDifficulty = Difficulty;
    // Capture the accepted request before async bootstrap; later UI choices cannot alter it.
    bRequestedSudokuChaos = bCreate && bChaos;
    bRequestedSudokuMirror = bCreate && bMirror;
    bRequestedSudokuTimeAttack = bCreate && bTimeAttack;
    CsrfHeader.Reset(); CsrfToken.Reset(); CookieJar.Reset(); AuthenticatedPlayerId.Reset();
    const auto Ticket = Guard.BeginRead(FPlatformTime::Seconds());
    if (!SendHttp(Operation::SudokuBootstrap, TEXT("GET"), TEXT("/api/session"), FString(), Ticket))
    {
        Guard.Reject(Ticket, true); SetMessage(TEXT("Sudoku bootstrap could not start.")); return false;
    }
    SetMessage(TEXT("Authenticating with the local Java Sudoku service…"));
    return true;
}
bool ADaedalusJavaArcade::StartSudokuGame(int32 Difficulty) { return BeginSudoku(true, FString(), Difficulty); }
bool ADaedalusJavaArcade::StartSudokuGameWithModes(int32 Difficulty, bool bChaos, bool bMirror, bool bTimeAttack)
{
    return BeginSudoku(true, FString(), Difficulty, false, bChaos, bMirror, bTimeAttack);
}
bool ADaedalusJavaArcade::OpenSudokuGame(const FString& Id) { return BeginSudoku(false, Id, 1); }
bool ADaedalusJavaArcade::ResumeSudokuGame(const FString& Id) { return BeginSudoku(false, Id, 1, true); }
bool ADaedalusJavaArcade::CreateSudokuAfterBootstrap()
{
    if (bCreateSudoku)
    {
        const auto Ticket = Guard.BeginCreation(FPlatformTime::Seconds());
        const FString Path = FString::Printf(TEXT("/api/game/new?difficulty=%d&chaos=%s&mirror=%s&timeAttack=%s"), RequestedDifficulty,
            bRequestedSudokuChaos ? TEXT("true") : TEXT("false"), bRequestedSudokuMirror ? TEXT("true") : TEXT("false"),
            bRequestedSudokuTimeAttack ? TEXT("true") : TEXT("false"));
        return SendHttp(Operation::SudokuCreate, TEXT("POST"), Path, FString(), Ticket);
    }
    if (bResumeSudoku)
    {
        const auto Ticket = Guard.BeginCreation(FPlatformTime::Seconds());
        return SendHttp(Operation::SudokuResume, TEXT("POST"), TEXT("/api/game/") + JavaArcadeWire::Encode(RequestedSudokuId) + TEXT("/resume"), FString(), Ticket);
    }
    const auto Ticket = Guard.BeginRead(FPlatformTime::Seconds());
    return SendHttp(Operation::SudokuRead, TEXT("GET"), TEXT("/api/game/") + JavaArcadeWire::Encode(RequestedSudokuId), FString(), Ticket);
}
bool ADaedalusJavaArcade::ConnectSudokuSocket()
{
    if (RequestedSudokuId.IsEmpty() || RequestedSudokuId.Len() > 256 || BasicAuthorization.IsEmpty()) return false;
    StopSocket();
    if (Guard.PendingKind() == JA::Work::None)
    {
        const auto Ticket = Guard.BeginRead(FPlatformTime::Seconds());
        if (!Guard.Current(Ticket)) return false;
    }
    LastReadOperation = Operation::SudokuSync;
    FString Origin;
    if (!JavaArcadeWire::Origin(ActiveOrigin, Origin)) return false;
    const FString Url = Origin.Replace(TEXT("http://"), TEXT("ws://")) + TEXT("/ws/game?gameId=") + JavaArcadeWire::Encode(RequestedSudokuId);
    TMap<FString, FString> Headers;
    Headers.Add(TEXT("Authorization"), BasicAuthorization);
    if (!CookieJar.IsEmpty()) Headers.Add(TEXT("Cookie"), CookieJar);
    SocketInbox = MakeShared<FJavaArcadeSocketInbox, ESPMode::ThreadSafe>();
    const auto Inbox = SocketInbox;
    Socket = FWebSocketsModule::Get().CreateWebSocket(Url, FString(), Headers);
    Socket->SetTextMessageMemoryLimit(65536);
    Socket->OnConnected().AddLambda([Inbox] { FScopeLock Scope(&Inbox->Lock); Inbox->bConnected = true; });
    Socket->OnMessage().AddLambda([Inbox](const FString& Message) { Inbox->Add(Message); });
    Socket->OnConnectionError().AddLambda([Inbox](const FString&) { FScopeLock Scope(&Inbox->Lock); Inbox->bFailure = true; });
    Socket->OnClosed().AddLambda([Inbox](int32 Code, const FString&, bool)
    {
        FScopeLock Scope(&Inbox->Lock); Inbox->bFailure = true; Inbox->bPermanent = Code == 1008;
    });
    Socket->Connect();
    SetMessage(TEXT("Connecting to the local Sudoku board; a full sync is required."));
    return true;
}
void ADaedalusJavaArcade::SocketFailure(uint64 Epoch, bool bPermanent)
{
    if (Epoch != Guard.Epoch() || Guard.GetPhase() == JA::Phase::Closed) return;
    auto Ticket = Guard.PendingTicket();
    if (Ticket.Kind == JA::Work::None) Ticket = Guard.BeginRead(FPlatformTime::Seconds());
    if (bPermanent) Guard.Reject(Ticket, true);
    else Guard.Fail(Ticket, FPlatformTime::Seconds(), Ticket.Kind == JA::Work::Read);
    StopSocket();
    SetMessage(bPermanent ? TEXT("Sudoku channel refused or exceeded bounds. Reconfigure credentials before reconnecting.")
        : TEXT("Sudoku channel lost. A pending action may have applied; refresh before deciding whether to retry."));
}
bool ADaedalusJavaArcade::SendSudokuCommand(const FString& Type, const TSharedPtr<FJsonObject>& Payload)
{
    if (Game != ActiveGame || ActiveGame != EDaedalusJavaGame::Sudoku || !GetState().bCanAct || !Socket.IsValid() || !Socket->IsConnected()) return false;
    const auto Ticket = Guard.BeginMutation(FPlatformTime::Seconds());
    if (!Guard.Current(Ticket)) return false;
    auto Command = MakeShared<FJsonObject>();
    Command->SetStringField(TEXT("type"), Type);
    if (Payload.IsValid()) Command->SetObjectField(TEXT("payload"), Payload);
    else Command->SetStringField(TEXT("payload"), TEXT(""));
    const FString Text = JavaArcadeWire::Json(Command);
    if (FTCHARToUTF8(*Text).Length() > 1024) { Guard.Reject(Ticket, false); return false; }
    bAwaitingSudokuReconcile = true;
    Socket->Send(Text);
    // Source handlers process messages synchronously on this channel. This is a reconciliation
    // request, not a correlated acknowledgement; other-device/replica broadcasts remain possible.
    Socket->Send(TEXT("{\"type\":\"sync\",\"payload\":\"\"}"));
    SetMessage(TEXT("Action sent. A board event will trigger a fresh Java GET; it is a state refresh, not a unique command receipt."));
    return true;
}
bool ADaedalusJavaArcade::SubmitSudokuMove(int32 Row, int32 Col, int32 Value)
{
    if (!JA::CanSubmitSudoku(Sudoku, TCHAR_TO_UTF8(*AuthenticatedPlayerId), Row, Col, Value)) return false;
    auto Payload = MakeShared<FJsonObject>();
    Payload->SetNumberField(TEXT("row"), Row); Payload->SetNumberField(TEXT("col"), Col);
    Payload->SetNumberField(TEXT("oldVal"), Sudoku.Values[static_cast<std::size_t>(Row * 9 + Col)]);
    Payload->SetNumberField(TEXT("newVal"), Value);
    return SendSudokuCommand(TEXT("move"), Payload);
}
bool ADaedalusJavaArcade::SudokuUndo() { return SendSudokuCommand(TEXT("undo"), nullptr); }
bool ADaedalusJavaArcade::SudokuRedo() { return SendSudokuCommand(TEXT("redo"), nullptr); }
bool ADaedalusJavaArcade::RequestSudokuHint()
{
    if (Game != EDaedalusJavaGame::Sudoku || !GetState().bCanAct || HttpTask.IsValid()) return false;
    const auto Ticket = Guard.BeginMutation(FPlatformTime::Seconds());
    if (!SendHttp(Operation::SudokuHint, TEXT("POST"), TEXT("/api/game/hint?gameId=") + JavaArcadeWire::Encode(RequestedSudokuId), FString(), Ticket))
    { Guard.Reject(Ticket, false); return false; }
    SetMessage(TEXT("Explicit hint request sent. Java controls any existing virtual gem charge."));
    return true;
}
bool ADaedalusJavaArcade::SaveSudokuGame()
{
    if (Game != ActiveGame || ActiveGame != EDaedalusJavaGame::Sudoku || !Guard.CanMutate() || HttpTask.IsValid()
        || Sudoku.Owner != TCHAR_TO_UTF8(*AuthenticatedPlayerId) || Sudoku.GameId.empty()) return false;
    const auto Ticket = Guard.BeginMutation(FPlatformTime::Seconds());
    if (!SendHttp(Operation::SudokuSave, TEXT("POST"), TEXT("/api/game/") + JavaArcadeWire::Encode(RequestedSudokuId) + TEXT("/save"), FString(), Ticket))
    { Guard.Reject(Ticket, false); return false; }
    SetMessage(TEXT("Saving through the existing Java owner-only API. No local game save is written."));
    return true;
}
void ADaedalusJavaArcade::HandleSocketMessage(uint64 Epoch, const FString& Message)
{
    if (Epoch != Guard.Epoch() || Game != EDaedalusJavaGame::Sudoku || Guard.GetPhase() == JA::Phase::Closed) return;
    if (!JA::PayloadFits(static_cast<std::size_t>(FTCHARToUTF8(*Message).Length()))) { SocketFailure(Epoch, true); return; }
    const auto Json = JavaArcadeWire::Parse(Message);
    FString Type;
    if (!JavaArcadeWire::String(Json, TEXT("type"), Type, 32)) { SocketFailure(Epoch, true); return; }
    if (Type == TEXT("board"))
    {
        const TSharedPtr<FJsonObject>* Board = nullptr;
        if (!Json->TryGetObjectField(TEXT("payload"), Board) || !ApplySudoku(*Board)) { SocketFailure(Epoch, true); return; }
        const auto Pending = Guard.PendingTicket();
        if (Pending.Kind == JA::Work::Mutation && bAwaitingSudokuReconcile)
        {
            // Board traffic alone never completes the mutation. A separate HTTP read ticket
            // reconciles current state. This protocol still cannot prove unique command receipt.
            bAwaitingSudokuReconcile = false;
            Guard.NeedsSnapshot(Pending);
            if (!RefreshSnapshot()) SetMessage(TEXT("Board changed; explicit Refresh is required before another action."));
        }
        if (Pending.Kind == JA::Work::Read && LastReadOperation == Operation::SudokuSync)
        {
            Guard.Snapshot(Pending); bAwaitingSudokuReconcile = false;
            SetMessage(TEXT("Authoritative Java board refreshed. No correlated command acknowledgement is available; inspect it before retrying."));
        }
    }
    else if (Type == TEXT("error"))
    {
        const auto Pending = Guard.PendingTicket();
        if (Pending.Kind != JA::Work::None) Guard.Reject(Pending, false);
        bAwaitingSudokuReconcile = false;
        SetMessage(TEXT("Java refused an action. Refresh the board before another command."));
        // Do not feed error->sync->error loops. Refresh is an explicit user action.
    }
    else if (Type == TEXT("gameEnd"))
    {
        SetMessage(TEXT("Java reports the game ended. Refresh the board to inspect completion or time expiry."));
        const auto Pending = Guard.PendingTicket();
        if (Pending.Kind != JA::Work::None) Guard.NeedsSnapshot(Pending);
        else { const auto Read = Guard.BeginRead(FPlatformTime::Seconds()); Guard.NeedsSnapshot(Read); }
        bAwaitingSudokuReconcile = false;
    }
    // Move/batch/hint/health/chat/status/from metadata do not prove an outcome or confer authority.
}

bool ADaedalusJavaArcade::StartBlackjackSession()
{
    FString Origin;
    if (HttpTask.IsValid() || BlackjackAuthorization.IsEmpty() || bUnknownBlackjackCreate
        || (!Blackjack.SessionId.empty() && !Blackjack.Closed) || !JavaArcadeWire::Origin(BlackjackOrigin, Origin)) return false;
    Guard.Open(); StopSocket(); Sudoku = {}; Blackjack = {}; View = {}; Game = EDaedalusJavaGame::Blackjack; ActiveGame = Game; View.Game = Game;
    ActiveOrigin = Origin; CreateRequestId = FGuid::NewGuid().ToString(EGuidFormats::Digits);
    auto BodyJson = MakeShared<FJsonObject>(); BodyJson->SetStringField(TEXT("requestId"), CreateRequestId);
    PendingRequestId = CreateRequestId; PendingRequestBody = JavaArcadeWire::Json(BodyJson);
    const auto Ticket = Guard.BeginCreation(FPlatformTime::Seconds());
    if (!SendHttp(Operation::BlackjackCreate, TEXT("POST"), TEXT("/v1/blackjack/sessions"), PendingRequestBody, Ticket))
    { Guard.Reject(Ticket, true); return false; }
    SetMessage(TEXT("Creating a local Java Blackjack session with simulated credits…"));
    return true;
}
bool ADaedalusJavaArcade::RetryBlackjackCreate()
{
    if (Game != ActiveGame || ActiveGame != EDaedalusJavaGame::Blackjack || !bUnknownBlackjackCreate || HttpTask.IsValid()
        || CreateRequestId.IsEmpty() || PendingRequestBody.IsEmpty() || PendingRequestId != CreateRequestId) return false;
    const auto Ticket = Guard.BeginExplicitCreateRecovery(FPlatformTime::Seconds());
    if (!SendHttp(Operation::BlackjackCreate, TEXT("POST"), TEXT("/v1/blackjack/sessions"), PendingRequestBody, Ticket)) return false;
    SetMessage(TEXT("Explicitly recovering the same create request ID. No fresh session request was made."));
    return true;
}
bool ADaedalusJavaArcade::IsBlackjackActionLegal(const FString& Action, int32 Amount) const
{
    return Game == ActiveGame && ActiveGame == EDaedalusJavaGame::Blackjack && Guard.CanMutate()
        && JA::CanSubmitBlackjack(Blackjack, TCHAR_TO_UTF8(*Action), Amount);
}
bool ADaedalusJavaArcade::SendBlackjackCommand(const FString& Action, const TSharedPtr<FJsonObject>& Fields)
{
    if (HttpTask.IsValid() || !IsBlackjackActionLegal(Action, Action == TEXT("bet") ? static_cast<int32>(Fields->GetNumberField(TEXT("amount"))) : 0)) return false;
    const auto Ticket = Guard.BeginMutation(FPlatformTime::Seconds());
    if (!Guard.Current(Ticket)) return false;
    PendingRequestId = FGuid::NewGuid().ToString(EGuidFormats::Digits);
    Fields->SetStringField(TEXT("requestId"), PendingRequestId);
    Fields->SetNumberField(TEXT("expectedRevision"), static_cast<double>(Blackjack.Revision));
    Fields->SetStringField(TEXT("action"), Action);
    PendingRequestBody = JavaArcadeWire::Json(Fields);
    const FString Path = TEXT("/v1/blackjack/sessions/") + JavaArcadeWire::Encode(UTF8_TO_TCHAR(Blackjack.SessionId.c_str())) + TEXT("/commands");
    if (!SendHttp(Operation::BlackjackCommand, TEXT("POST"), Path, PendingRequestBody, Ticket)) { Guard.Reject(Ticket, false); return false; }
    SetMessage(TEXT("Command sent to Java. Waiting for its revisioned visible snapshot."));
    return true;
}
bool ADaedalusJavaArcade::SubmitBlackjackAction(const FString& Action, int32 Amount, bool bAccept)
{
    if (Action == TEXT("setRule") || Action == TEXT("setDecks") || Action == TEXT("setSplitLimit")) return false;
    auto Fields = MakeShared<FJsonObject>();
    if (Action == TEXT("bet")) Fields->SetNumberField(TEXT("amount"), Amount);
    if (Action == TEXT("insurance"))
    {
        if (bAccept && !View.bInsuranceAcceptAllowed) return false;
        Fields->SetBoolField(TEXT("accept"), bAccept);
    }
    return SendBlackjackCommand(Action, Fields);
}
bool ADaedalusJavaArcade::SetBlackjackRule(const FString& Rule, bool bEnabled)
{
    if (Rule != TEXT("dealerHitsSoft17") && Rule != TEXT("lateSurrender") && Rule != TEXT("offerInsurance")
        && Rule != TEXT("doubleAfterSplit") && Rule != TEXT("splitAcesOneCard")) return false;
    auto Fields = MakeShared<FJsonObject>(); Fields->SetStringField(TEXT("rule"), Rule); Fields->SetBoolField(TEXT("enabled"), bEnabled);
    return SendBlackjackCommand(TEXT("setRule"), Fields);
}
bool ADaedalusJavaArcade::SetBlackjackDecks(int32 Decks)
{
    if (Decks != 1 && Decks != 2 && Decks != 4 && Decks != 6 && Decks != 8) return false;
    auto Fields = MakeShared<FJsonObject>(); Fields->SetNumberField(TEXT("decks"), Decks);
    return SendBlackjackCommand(TEXT("setDecks"), Fields);
}
bool ADaedalusJavaArcade::SetBlackjackSplitLimit(int32 Hands)
{
    if (Hands < 2 || Hands > 4) return false;
    auto Fields = MakeShared<FJsonObject>(); Fields->SetNumberField(TEXT("hands"), Hands);
    return SendBlackjackCommand(TEXT("setSplitLimit"), Fields);
}
bool ADaedalusJavaArcade::RefreshSnapshot()
{
    if (Game != ActiveGame || HttpTask.IsValid() || Guard.PendingKind() != JA::Work::None || Guard.GetPhase() == JA::Phase::Closed) return false;
    const auto Ticket = Guard.BeginRead(FPlatformTime::Seconds());
    if (!Guard.Current(Ticket)) return false;
    if (ActiveGame == EDaedalusJavaGame::Sudoku)
    {
        if (RequestedSudokuId.IsEmpty()) { Guard.Reject(Ticket, false); SetMessage(TEXT("No game ID is known. A new game decision must be explicit; creation is never replayed automatically.")); return false; }
        // REST read has its own response correlation and is suitable for manual reconciliation.
        if (!SendHttp(Operation::SudokuRead, TEXT("GET"), TEXT("/api/game/") + JavaArcadeWire::Encode(RequestedSudokuId), FString(), Ticket)) { Guard.Reject(Ticket, false); return false; }
    }
    else
    {
        if (Blackjack.SessionId.empty()) { Guard.Reject(Ticket, false); return false; }
        if (!SendHttp(Operation::BlackjackRead, TEXT("GET"), TEXT("/v1/blackjack/sessions/") + JavaArcadeWire::Encode(UTF8_TO_TCHAR(Blackjack.SessionId.c_str())), FString(), Ticket)) { Guard.Reject(Ticket, false); return false; }
    }
    SetMessage(TEXT("Explicitly refreshing authoritative state. Verify any previous action before retrying it."));
    return true;
}
bool ADaedalusJavaArcade::CloseRemoteBlackjackSession()
{
    if (Game != EDaedalusJavaGame::Blackjack || !Guard.CanMutate() || HttpTask.IsValid() || Blackjack.SessionId.empty() || Blackjack.Closed) return false;
    const auto Ticket = Guard.BeginMutation(FPlatformTime::Seconds());
    PendingRequestId = FGuid::NewGuid().ToString(EGuidFormats::Digits);
    auto BodyJson = MakeShared<FJsonObject>(); BodyJson->SetStringField(TEXT("requestId"), PendingRequestId);
    BodyJson->SetNumberField(TEXT("expectedRevision"), static_cast<double>(Blackjack.Revision));
    PendingRequestBody = JavaArcadeWire::Json(BodyJson);
    if (!SendHttp(Operation::BlackjackClose, TEXT("DELETE"), TEXT("/v1/blackjack/sessions/") + JavaArcadeWire::Encode(UTF8_TO_TCHAR(Blackjack.SessionId.c_str())), PendingRequestBody, Ticket))
    { Guard.Reject(Ticket, false); return false; }
    SetMessage(TEXT("Closing the Java session. Source rules may forfeit an active hand."));
    return true;
}

void ADaedalusJavaArcade::FinishHttp(Operation Op, FTicket Ticket, const TSharedPtr<FJavaArcadeHttpTask, ESPMode::ThreadSafe>& Task)
{
    if (!Guard.Current(Ticket)) return; // Canceled/closed/replaced epochs never apply old responses.
    auto InvalidReply = [this, Op, Ticket](const TCHAR* Message)
    {
        if (Op == Operation::BlackjackCreate)
        {
            Guard.Fail(Ticket, FPlatformTime::Seconds(), false);
            bUnknownBlackjackCreate = true;
        }
        else if (Ticket.Kind == JA::Work::Mutation) Guard.Fail(Ticket, FPlatformTime::Seconds(), false);
        else Guard.Reject(Ticket, true);
        SetMessage(Message);
    };
    const bool bPermanent = Task->StatusCode == 401 || Task->StatusCode == 403 || Task->bRedirect;
    if (!Task->bSuccess || Task->StatusCode < 200 || Task->StatusCode >= 300)
    {
        if (bPermanent) { Guard.Reject(Ticket, true); StopSocket(); SetMessage(TEXT("Authorization refused or redirect rejected. Reconfigure the local service credentials.")); }
        else if (Task->StatusCode >= 400 && Task->StatusCode < 500)
        {
            if (Op == Operation::BlackjackRead && !Blackjack.SessionId.empty() && JA::PayloadFits(Task->Response.Num(), 32768))
            {
                const FUTF8ToTCHAR ConvertedError(reinterpret_cast<const ANSICHAR*>(Task->Response.GetData()), Task->Response.Num());
                const auto ErrorJson = JavaArcadeWire::Parse(FString(ConvertedError.Length(), ConvertedError.Get()));
                const TSharedPtr<FJsonObject>* Error = nullptr;
                int64 ApiVersion = 0;
                FString GameId, Code;
                if (JavaArcadeWire::Integer(ErrorJson, TEXT("apiVersion"), ApiVersion, 1, 1)
                    && JavaArcadeWire::String(ErrorJson, TEXT("gameId"), GameId, 16) && GameId == TEXT("blackjack")
                    && ErrorJson->TryGetObjectField(TEXT("error"), Error) && JavaArcadeWire::String(*Error, TEXT("code"), Code, 32)
                    && ((Task->StatusCode == 409 && Code == TEXT("SESSION_CLOSED")) || (Task->StatusCode == 404 && Code == TEXT("NOT_FOUND"))))
                {
                    Blackjack.Closed = true; View.bRemoteClosed = true; Guard.Close();
                    PendingRequestId.Reset(); PendingRequestBody.Reset(); bUnknownBlackjackCreate = false;
                    SetMessage(TEXT("The Java session is closed, expired or unavailable. Start a new session explicitly; no result or reward is inferred."));
                    return;
                }
            }
            Guard.Reject(Ticket, false);
            SetMessage(TEXT("Java refused the request. Refresh known state before another action; commands are not replayed."));
        }
        else
        {
            Guard.Fail(Ticket, FPlatformTime::Seconds(), Ticket.Kind == JA::Work::Read);
            SetMessage(TEXT("Java request failed or timed out. Safe reads have a bounded retry budget; mutation outcomes require explicit recovery."));
            if (Op == Operation::BlackjackCreate) bUnknownBlackjackCreate = true;
        }
        return;
    }
    if (!JA::PayloadFits(static_cast<std::size_t>(Task->Response.Num()), Task->Limit)) { InvalidReply(TEXT("Java response was empty or exceeded bounds; the action may have applied.")); return; }
    const FUTF8ToTCHAR Converted(reinterpret_cast<const ANSICHAR*>(Task->Response.GetData()), Task->Response.Num());
    const FString Text(Converted.Length(), Converted.Get());
    const auto Json = JavaArcadeWire::Parse(Text);
    if (!Json.IsValid()) { InvalidReply(TEXT("Java response did not match the bounded visible JSON contract; recover before another action.")); return; }
    if (Op == Operation::SudokuBootstrap)
    {
        if (!JavaArcadeWire::String(Json, TEXT("playerId"), AuthenticatedPlayerId, 128)
            || !JavaArcadeWire::String(Json, TEXT("csrfHeaderName"), CsrfHeader, 64)
            || !JavaArcadeWire::String(Json, TEXT("csrfToken"), CsrfToken, 4096)
            || (CsrfHeader != TEXT("X-XSRF-TOKEN") && CsrfHeader != TEXT("X-CSRF-TOKEN"))
            || !JavaArcadeWire::HeaderValue(CsrfToken)) { Guard.Reject(Ticket, true); return; }
        TMap<FString, FString> Cookies;
        for (const FString& Header : Task->ResponseHeaders)
        {
            if (!Header.StartsWith(TEXT("Set-Cookie:"), ESearchCase::IgnoreCase)) continue;
            FString Pair = Header.Mid(11).TrimStartAndEnd();
            int32 Separator = INDEX_NONE;
            if (Pair.FindChar(TEXT(';'), Separator)) Pair.LeftInline(Separator);
            FString Name, Value;
            if (!Pair.Split(TEXT("="), &Name, &Value) || (Name != TEXT("XSRF-TOKEN") && Name != TEXT("JSESSIONID")) || !JavaArcadeWire::HeaderValue(Value)) continue;
            Cookies.Add(Name, Value);
        }
        CookieJar.Reset();
        for (const auto& Pair : Cookies) { if (!CookieJar.IsEmpty()) CookieJar += TEXT("; "); CookieJar += Pair.Key + TEXT("=") + Pair.Value; }
        if (!Cookies.Contains(TEXT("XSRF-TOKEN")) || CookieJar.Len() > 4096 || !Guard.ContinueBootstrap(Ticket) || !CreateSudokuAfterBootstrap())
        { Guard.Close(); SetMessage(TEXT("Sudoku CSRF cookie/bootstrap could not continue.")); }
        return;
    }
    if (Op == Operation::SudokuHint)
    {
        FString Hint;
        if (!JavaArcadeWire::String(Json, TEXT("hint"), Hint, 1024, true)) { InvalidReply(TEXT("Hint may have charged Java gems but its reply was invalid. Refresh before deciding whether to request another.")); return; }
        Guard.NeedsSnapshot(Ticket);
        View.HintText = Hint;
        View.Message = Hint.IsEmpty() ? TEXT("Hint response received; refreshing the authoritative board.") : Hint;
        RefreshSnapshot();
        return;
    }
    if (Op == Operation::SudokuSave)
    {
        FString Status, Id;
        if (!JavaArcadeWire::String(Json, TEXT("status"), Status, 16) || Status != TEXT("saved")
            || !JavaArcadeWire::String(Json, TEXT("gameId"), Id, 256) || Id != RequestedSudokuId) { InvalidReply(TEXT("Java may have saved the game but its reply was invalid. Refresh before deciding whether to retry.")); return; }
        Guard.NeedsSnapshot(Ticket); SetMessage(TEXT("Java saved this game. Refreshing the board.")); RefreshSnapshot();
        return;
    }
    if (Op == Operation::SudokuCreate || Op == Operation::SudokuRead || Op == Operation::SudokuResume)
    {
        if (!ApplySudoku(Json)) { InvalidReply(TEXT("Sudoku board was malformed, belonged to another account, or had a different game ID.")); StopSocket(); return; }
        Guard.Snapshot(Ticket);
        SetMessage(TEXT("Authoritative Java board refreshed. Verify prior actions before retrying."));
        if (!Socket.IsValid() || !Socket->IsConnected())
        {
            if (!ConnectSudokuSocket()) { Guard.Close(); SetMessage(TEXT("Sudoku socket could not start; local interaction is unavailable.")); }
        }
        return;
    }
    const FString Expected = Op == Operation::BlackjackRead ? FString() : PendingRequestId;
    int64 ResponseRevision = -1;
    if (!JavaArcadeWire::Integer(Json, TEXT("revision"), ResponseRevision)
        || (Op == Operation::BlackjackCreate && ResponseRevision != 0)
        || ((Op == Operation::BlackjackCommand || Op == Operation::BlackjackClose) && ResponseRevision != Blackjack.Revision + 1))
    { InvalidReply(TEXT("Blackjack response revision did not match its operation; reconcile before another command.")); return; }
    if (!ApplyBlackjack(Json, Expected)) { InvalidReply(TEXT("Blackjack visible snapshot, request ID, session or revision was invalid; the action may have applied.")); return; }
    Guard.Snapshot(Ticket); bUnknownBlackjackCreate = false;
    PendingRequestId.Reset(); PendingRequestBody.Reset();
    SetMessage(TEXT("Java Blackjack state refreshed. Credits are simulated; rules and dealing remain in Java."));
    if (Op == Operation::BlackjackCreate && !Blackjack.Closed)
    {
        // Create replay is a historical decided response, including after later closure.
        // Always reconcile its returned session before enabling gameplay.
        const auto Read = Guard.BeginRead(FPlatformTime::Seconds());
        if (!SendHttp(Operation::BlackjackRead, TEXT("GET"), TEXT("/v1/blackjack/sessions/") + JavaArcadeWire::Encode(UTF8_TO_TCHAR(Blackjack.SessionId.c_str())), FString(), Read))
            Guard.Reject(Read, true);
        return;
    }
    if (Op == Operation::BlackjackClose || Blackjack.Closed) Guard.Close();
}
bool ADaedalusJavaArcade::ConfigureBlackjackToken(const FString& Token)
{
    if (!JavaArcadeWire::HeaderValue(Token, 256) || Token.Len() < 32) return false;
    CancelTransport(true); Game = EDaedalusJavaGame::Blackjack; ActiveGame = Game; View.Game = Game;
    BlackjackAuthorization = TEXT("Bearer ") + Token;
    SetMessage(TEXT("Token configured in memory. Start a Java Blackjack session."));
    return true;
}
bool ADaedalusJavaArcade::SendHttp(Operation Op, const FString& Verb, const FString& Path, const FString& BodyText, const FTicket& Ticket)
{
    if (HttpTask.IsValid() || !Guard.Current(Ticket) || !Path.StartsWith(TEXT("/")) || BodyText.Len() > 8192) return false;
    FString Checked;
    if (!JavaArcadeWire::Origin(ActiveOrigin, Checked)) return false;
    FHttpModule::Get(); // Engine owns curl initialization/lifetime; never call global cleanup.
    auto Task = MakeShared<FJavaArcadeHttpTask, ESPMode::ThreadSafe>();
    Task->Ticket = Ticket; Task->Operation = static_cast<uint8>(Op); Task->Url = Checked + Path;
    Task->Verb = Verb; Task->Body = BodyText;
    const bool bSudoku = Op == Operation::SudokuBootstrap || Op == Operation::SudokuCreate || Op == Operation::SudokuRead || Op == Operation::SudokuHint
        || Op == Operation::SudokuSave || Op == Operation::SudokuResume;
    const FString Auth = bSudoku ? BasicAuthorization : BlackjackAuthorization;
    if (!JavaArcadeWire::HeaderValue(Auth)) return false;
    Task->Limit = bSudoku ? 65536 : 32768;
    Task->RequestHeaders = { TEXT("Accept: application/json"), TEXT("Content-Type: application/json"), TEXT("Authorization: ") + Auth };
    if (bSudoku && Verb != TEXT("GET"))
    {
        if ((CsrfHeader != TEXT("X-XSRF-TOKEN") && CsrfHeader != TEXT("X-CSRF-TOKEN"))
            || !JavaArcadeWire::HeaderValue(CsrfToken) || CookieJar.IsEmpty()) return false;
        Task->RequestHeaders.Add(CsrfHeader + TEXT(": ") + CsrfToken);
        Task->RequestHeaders.Add(TEXT("Cookie: ") + CookieJar);
    }
    else if (bSudoku && !CookieJar.IsEmpty()) Task->RequestHeaders.Add(TEXT("Cookie: ") + CookieJar);
    HttpTask = Task;
    Async(EAsyncExecution::ThreadPool, [Task] { Task->Run(); });
    if (Ticket.Kind == JA::Work::Read) LastReadOperation = Op;
    return true;
}

FDaedalusJavaArcadeState ADaedalusJavaArcade::GetState() const
{
    auto Out = View;
    Out.Game = ActiveGame;
    const auto Phase = Guard.GetPhase();
    Out.bBusy = Guard.PendingKind() != JA::Work::None;
    Out.bReady = Phase == JA::Phase::Ready;
    Out.bNeedsSync = Phase == JA::Phase::NeedsSync;
    Out.bCanAct = Game == ActiveGame && Guard.CanMutate() && !Out.bRemoteClosed;
    switch (Phase)
    {
    case JA::Phase::Closed: Out.Status = TEXT("Closed"); break;
    case JA::Phase::Connecting: Out.Status = TEXT("Connecting"); break;
    case JA::Phase::Ready: Out.Status = TEXT("Ready"); break;
    case JA::Phase::Busy: Out.Status = TEXT("Waiting for Java"); break;
    case JA::Phase::NeedsSync: Out.Status = TEXT("Refresh required"); break;
    case JA::Phase::Failed: Out.Status = TEXT("Unavailable"); break;
    }
    if (ActiveGame == EDaedalusJavaGame::Sudoku)
    {
        Out.bOwner = !AuthenticatedPlayerId.IsEmpty() && Sudoku.Owner == TCHAR_TO_UTF8(*AuthenticatedPlayerId);
        Out.bCanAct = Out.bCanAct && Out.bOwner && !Out.bSolved && !Out.bTimeUp && Socket.IsValid() && Socket->IsConnected();
    }
    return Out;
}
bool ADaedalusJavaArcade::CoreTick(float Delta)
{
    if (Game != ActiveGame) CancelTransport(true);
    const double Now = FPlatformTime::Seconds();
    const auto Timeout = Guard.Tick(Now);
    if (Timeout != JA::TimerEvent::None)
    {
        if (HttpTask.IsValid())
        {
            HttpTask->bCancelled.Store(true);
            if (static_cast<Operation>(HttpTask->Operation) == Operation::BlackjackCreate) bUnknownBlackjackCreate = true;
        }
        if (LastReadOperation == Operation::SudokuSync) StopSocket();
        bAwaitingSudokuReconcile = false;
        SetMessage(Timeout == JA::TimerEvent::MutationTimeout
            ? TEXT("Action outcome is unknown. Refresh known state or explicitly recover the same Blackjack create ID; no mutation is replayed automatically.")
            : TEXT("Read timed out; only safe reads receive a bounded retry."));
    }
    if (HttpTask.IsValid() && HttpTask->bDone.Load())
    {
        const auto Completed = HttpTask;
        HttpTask.Reset();
        FinishHttp(static_cast<Operation>(Completed->Operation), Completed->Ticket, Completed);
    }
    if (SocketInbox.IsValid())
    {
        const auto Inbox = SocketInbox;
        TArray<FString> Messages;
        bool bConnected = false, bFailure = false, bPermanent = false;
        {
            FScopeLock Scope(&Inbox->Lock);
            Messages = MoveTemp(Inbox->Messages); Inbox->Bytes = 0;
            bConnected = Inbox->bConnected; Inbox->bConnected = false;
            bFailure = Inbox->bFailure; bPermanent = Inbox->bPermanent; Inbox->bFailure = false;
        }
        const uint64 Epoch = Guard.Epoch();
        if (bFailure) SocketFailure(Epoch, bPermanent);
        else
        {
            if (bConnected && Socket.IsValid() && Guard.PendingKind() == JA::Work::Read)
                Socket->Send(TEXT("{\"type\":\"sync\",\"payload\":\"\"}"));
            for (const FString& Message : Messages)
            {
                if (SocketInbox != Inbox) break;
                HandleSocketMessage(Epoch, Message);
            }
        }
    }
    if (!HttpTask.IsValid() && Guard.ReadRetryDue(Now))
    {
        const auto Ticket = Guard.BeginRead(Now);
        bool bSent = false;
        switch (LastReadOperation)
        {
        case Operation::SudokuBootstrap: bSent = SendHttp(Operation::SudokuBootstrap, TEXT("GET"), TEXT("/api/session"), FString(), Ticket); break;
        case Operation::SudokuRead: bSent = SendHttp(Operation::SudokuRead, TEXT("GET"), TEXT("/api/game/") + JavaArcadeWire::Encode(RequestedSudokuId), FString(), Ticket); break;
        case Operation::BlackjackRead: bSent = SendHttp(Operation::BlackjackRead, TEXT("GET"), TEXT("/v1/blackjack/sessions/") + JavaArcadeWire::Encode(UTF8_TO_TCHAR(Blackjack.SessionId.c_str())), FString(), Ticket); break;
        case Operation::SudokuSync: bSent = ConnectSudokuSocket(); break;
        default: break;
        }
        if (!bSent) Guard.Reject(Ticket, true);
    }
    if (WidgetHost.IsValid()) MaintainOpenSession();
    return true;
}
bool ADaedalusJavaArcade::Use(ADaedalusHero* Hero)
{
    if (Game != ActiveGame) CancelTransport(true);
    UWorld* World = GetWorld();
    APlayerController* PC = Hero ? Cast<APlayerController>(Hero->GetController()) : nullptr;
    UGameViewportClient* Viewport = World ? World->GetGameViewport() : nullptr;
    ULocalPlayer* LocalPlayer = PC ? PC->GetLocalPlayer() : nullptr;
    if (bCloseScheduled || WidgetHost.IsValid() || !World || !Hero || Hero->GetWorld() != World || GetNetMode() != NM_Standalone
        || !PC || !PC->IsLocalController() || !LocalPlayer || !Viewport || !FSlateApplication::IsInitialized()
        || PC->bShowMouseCursor || Viewport->IgnoreInput() || Hero->IsSettingsOpen() || Hero->IsFieldOpen() || Hero->IsRealmOpen()) return false;
    ActiveGame = Game; View.Game = ActiveGame;
    OpenController = PC; OpenHero = Hero; OpenViewport = Viewport; OpenLocalPlayer = LocalPlayer;
    bPreviousMouseCursor = PC->bShowMouseCursor; PreviousCursor = PC->CurrentMouseCursor;
    PreviousCaptureMode = Viewport->GetMouseCaptureMode(); PreviousLockMode = Viewport->GetMouseLockMode();
    SlateUserIndex = FSlateApplication::Get().GetUserIndexForController(LocalPlayer->GetControllerId());
    Widget = SNew(SDaedalusJavaArcade).Game(this);
    WidgetHost = SNew(SWeakWidget).PossiblyNullContent(Widget.ToSharedRef());
    Viewport->AddViewportWidgetForPlayer(LocalPlayer, WidgetHost.ToSharedRef(), 100);
    FInputModeUIOnly Mode; Mode.SetWidgetToFocus(Widget); Mode.SetLockMouseToViewportBehavior(EMouseLockMode::DoNotLock);
    PC->SetInputMode(Mode); PC->bShowMouseCursor = true; PC->CurrentMouseCursor = EMouseCursor::Default;
    if (SlateUserIndex != INDEX_NONE) FSlateApplication::Get().SetUserFocus(SlateUserIndex, Widget, EFocusCause::SetDirectly);
    return true;
}
bool ADaedalusJavaArcade::OtherOverlayOwnsInput() const
{
    const APlayerController* PC = OpenController.Get();
    const ADaedalusHero* Hero = PC ? Cast<ADaedalusHero>(PC->GetPawn()) : nullptr;
    auto Overlay = [](const ADaedalusHero* H) { return H && (H->IsSettingsOpen() || H->IsFieldOpen() || H->IsRealmOpen()); };
    if (Overlay(OpenHero.Get()) || Overlay(Hero)) return true;
    return FSlateApplication::IsInitialized() && SlateUserIndex != INDEX_NONE
        && FSlateApplication::Get().GetUserFocusedWidget(SlateUserIndex).IsValid()
        && !(Widget.IsValid() && Widget->OwnsUserFocus(SlateUserIndex));
}
bool ADaedalusJavaArcade::MaintainOpenSession()
{
    if (!WidgetHost.IsValid() || bCloseScheduled) return false;
    const auto* PC = OpenController.Get();
    const auto* Hero = OpenHero.Get();
    if (!PC || !Hero || PC->GetWorld() != GetWorld() || PC->GetPawn() != Hero || Hero->GetController() != PC
        || !OpenViewport.IsValid() || !OpenLocalPlayer.IsValid() || OtherOverlayOwnsInput())
    { CloseArcade(); return false; }
    return true;
}
void ADaedalusJavaArcade::CloseArcade()
{
    if (bCloseScheduled) return;
    CancelTransport(true); // No credentials or unknown command retries survive a cabinet close.
    if (!WidgetHost.IsValid()) return;
    bCloseScheduled = true;
    TWeakObjectPtr<ADaedalusJavaArcade> Self(this);
    FTSTicker::GetCoreTicker().AddTicker(FTickerDelegate::CreateLambda([Self](float)
    { if (Self.IsValid()) Self->ReleaseOverlay(); return false; }));
}
void ADaedalusJavaArcade::ReleaseOverlay()
{
    const bool bOther = OtherOverlayOwnsInput();
    auto* PC = OpenController.Get();
    auto* Viewport = OpenViewport.Get();
    if (WidgetHost.IsValid() && Viewport && OpenLocalPlayer.IsValid()) Viewport->RemoveViewportWidgetForPlayer(OpenLocalPlayer.Get(), WidgetHost.ToSharedRef());
    WidgetHost.Reset(); Widget.Reset();
    if (!bOther && PC && PC->IsLocalController() && PC->GetWorld() == GetWorld())
    {
        PC->SetInputMode(FInputModeGameOnly()); PC->bShowMouseCursor = bPreviousMouseCursor; PC->CurrentMouseCursor = PreviousCursor;
        if (Viewport) { Viewport->SetMouseCaptureMode(PreviousCaptureMode); Viewport->SetMouseLockMode(PreviousLockMode); }
        if (FSlateApplication::IsInitialized() && SlateUserIndex != INDEX_NONE)
            FSlateApplication::Get().SetUserFocusToGameViewport(SlateUserIndex, EFocusCause::SetDirectly);
    }
    OpenController.Reset(); OpenHero.Reset(); OpenViewport.Reset(); OpenLocalPlayer.Reset();
    SlateUserIndex = INDEX_NONE; bCloseScheduled = false;
}
void ADaedalusJavaArcade::EndPlay(const EEndPlayReason::Type Reason)
{
    CancelTransport(true); ReleaseOverlay();
    if (TickHandle.IsValid()) FTSTicker::GetCoreTicker().RemoveTicker(TickHandle);
    TickHandle.Reset();
    Super::EndPlay(Reason);
}
