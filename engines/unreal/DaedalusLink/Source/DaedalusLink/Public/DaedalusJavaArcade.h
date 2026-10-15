// SPDX-License-Identifier: MIT
#pragma once

#include "CoreMinimal.h"
#include "DaedalusOrrery.h"
#include "Containers/Ticker.h"
#include "Engine/EngineBaseTypes.h"
#include "GenericPlatform/ICursor.h"

THIRD_PARTY_INCLUDES_START
#include "JavaArcade/DaedalusJavaArcadeProtocol.h"
THIRD_PARTY_INCLUDES_END

#include "DaedalusJavaArcade.generated.h"

class APlayerController;
class UGameViewportClient;
class ULocalPlayer;
class IWebSocket;
class FJsonObject;
class FJavaArcadeHttpTask;
class FJavaArcadeSocketInbox;
class SDaedalusJavaArcade;
class SWidget;

UENUM(BlueprintType)
enum class EDaedalusJavaGame : uint8 { Sudoku, Blackjack };

USTRUCT(BlueprintType)
struct DAEDALUSLINK_API FDaedalusJavaCard
{
    GENERATED_BODY()
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Java Arcade") FString Rank;
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Java Arcade") FString Suit;
};
USTRUCT(BlueprintType)
struct DAEDALUSLINK_API FDaedalusJavaHand
{
    GENERATED_BODY()
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Java Arcade") TArray<FDaedalusJavaCard> Cards;
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Java Arcade") int64 Bet = 0;
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Java Arcade") int32 Value = 0;
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Java Arcade") bool bSoft = false;
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Java Arcade") bool bBust = false;
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Java Arcade") bool bBlackjack = false;
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Java Arcade") bool bDoubled = false;
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Java Arcade") bool bSurrendered = false;
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Java Arcade") bool bFromSplit = false;
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Java Arcade") bool bSplitAce = false;
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Java Arcade") bool bStood = false;
};
/** Values accepted from Java's visible rules DTO, never local settings defaults. */
USTRUCT(BlueprintType)
struct DAEDALUSLINK_API FDaedalusJavaBlackjackRules
{
    GENERATED_BODY()
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Java Arcade") int32 Decks = 0;
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Java Arcade") int32 MaxHands = 0;
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Java Arcade") double Penetration = 0;
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Java Arcade") bool bDealerHitsSoft17 = false;
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Java Arcade") bool bLateSurrender = false;
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Java Arcade") bool bOfferInsurance = false;
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Java Arcade") bool bDoubleAfterSplit = false;
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Java Arcade") bool bSplitAcesOneCard = false;
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Java Arcade") int32 BlackjackPayoutNum = 0;
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Java Arcade") int32 BlackjackPayoutDen = 0;
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Java Arcade") int32 InsurancePayoutNum = 0;
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Java Arcade") int32 InsurancePayoutDen = 0;
};
USTRUCT(BlueprintType)
struct DAEDALUSLINK_API FDaedalusJavaBlackjackStats
{
    GENERATED_BODY()
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Java Arcade") int32 Hands = 0;
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Java Arcade") int32 Wins = 0;
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Java Arcade") int32 Losses = 0;
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Java Arcade") int32 Pushes = 0;
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Java Arcade") int32 Blackjacks = 0;
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Java Arcade") int32 Busts = 0;
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Java Arcade") int32 Doubles = 0;
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Java Arcade") int32 Splits = 0;
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Java Arcade") int32 Surrenders = 0;
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Java Arcade") int32 PeakBankroll = 0;
    // Java long values stay decimal strings so lifetime totals never pass through double.
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Java Arcade") FString TotalWagered;
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Java Arcade") FString TotalReturned;
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Java Arcade") FString Net;
};
USTRUCT(BlueprintType)
struct DAEDALUSLINK_API FDaedalusJavaBlackjackShoe
{
    GENERATED_BODY()
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Java Arcade") int32 Decks = 0;
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Java Arcade") int32 Remaining = 0;
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Java Arcade") int32 ReshuffleAt = 0;
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Java Arcade") bool bNeedsShuffle = false;
};
/** Deliberately contains only presentation data. No credentials, puzzle solution, hole-card,
 * future-shoe cards, RNG, save paths, or Java Engine objects are reflected or replicated. */
USTRUCT(BlueprintType)
struct DAEDALUSLINK_API FDaedalusJavaArcadeState
{
    GENERATED_BODY()
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Java Arcade") EDaedalusJavaGame Game = EDaedalusJavaGame::Sudoku;
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Java Arcade") FString Status = TEXT("Closed");
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Java Arcade") FString Message;
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Java Arcade") FString HintText;
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Java Arcade") bool bReady = false;
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Java Arcade") bool bBusy = false;
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Java Arcade") bool bOwner = false;
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Java Arcade") bool bCanAct = false;
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Java Arcade") bool bNeedsSync = false;
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Java Arcade") bool bSolved = false;
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Java Arcade") bool bTimeUp = false;
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Java Arcade") bool bRemoteClosed = false;
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Java Arcade") FString SessionId;
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Java Arcade") int64 Revision = 0;
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Java Arcade") TArray<int32> Cells;
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Java Arcade") TArray<bool> Givens;
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Java Arcade") TArray<int32> PencilMasks;
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Java Arcade") bool bChaosMode = false;
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Java Arcade") bool bMirrorMode = false;
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Java Arcade") int32 Difficulty = 1;
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Java Arcade") int64 Score = 0;
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Java Arcade") int32 Lives = 0;
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Java Arcade") int64 SecondsLeft = 0;
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Java Arcade") int64 ElapsedSeconds = 0;
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Java Arcade") int64 TimeLimitSeconds = 0;
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Java Arcade") int64 HintCount = 0;
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Java Arcade") int64 MoveCount = 0;
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Java Arcade") FString Phase;
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Java Arcade") int64 Bankroll = 0;
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Java Arcade") int64 PendingBet = 0;
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Java Arcade") int32 ActiveHand = -1;
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Java Arcade") TArray<FDaedalusJavaHand> PlayerHands;
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Java Arcade") TArray<FDaedalusJavaCard> DealerCards;
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Java Arcade") int32 HiddenDealerCards = 0;
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Java Arcade") FString DealerCaption;
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Java Arcade") FString ResultText;
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Java Arcade") TArray<FString> LegalActions;
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Java Arcade") TArray<int32> LegalBetAmounts;
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Java Arcade") bool bInsuranceAcceptAllowed = false;
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Java Arcade") bool bBlackjackDetailsAvailable = false;
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Java Arcade") int64 InsuranceBet = 0;
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Java Arcade") bool bDealerValueAvailable = false;
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Java Arcade") int32 DealerValue = 0;
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Java Arcade") bool bDealerSoft = false;
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Java Arcade") bool bDealerBust = false;
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Java Arcade") bool bDealerBlackjack = false;
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Java Arcade") TArray<FString> LastOutcomes;
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Java Arcade") int64 LastNet = 0;
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Java Arcade") int64 LastInsurance = 0;
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Java Arcade") int64 LastInsuranceReturn = 0;
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Java Arcade") FDaedalusJavaBlackjackRules BlackjackRules;
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Java Arcade") FDaedalusJavaBlackjackStats BlackjackStats;
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Java Arcade") FDaedalusJavaBlackjackShoe BlackjackShoe;
};

/** Placeable standalone client cabinet. Java is authoritative; this actor never deals cards,
 * checks Sudoku solutions, awards credits, or decides rules. Services are verified direct
 * 127.0.0.1 pilots. Endpoint and cabinet identity are independent of future entitlement. */
UCLASS(BlueprintType, Blueprintable)
class DAEDALUSLINK_API ADaedalusJavaArcade : public ADaedalusUsable
{
    GENERATED_BODY()
public:
    ADaedalusJavaArcade();
    virtual FString Prompt(const ADaedalusHero* Hero) const override;
    virtual bool Use(ADaedalusHero* Hero) override;
    virtual void OnConstruction(const FTransform& Transform) override;
    virtual void PostDuplicate(EDuplicateMode::Type DuplicateMode) override;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Daedalus|Java Arcade") EDaedalusJavaGame Game = EDaedalusJavaGame::Sudoku;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Daedalus|Java Arcade") FString SudokuOrigin = TEXT("http://127.0.0.1:8080");
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Daedalus|Java Arcade") FString BlackjackOrigin = TEXT("http://127.0.0.1:8091");
    UPROPERTY(EditInstanceOnly, BlueprintReadWrite, Category="Daedalus|Java Arcade") FString CabinetId;

    /** Transient parameters only: caller must supply account credentials from its own provider.
     * Neither credentials nor authorization headers become actor properties or save data. */
    UFUNCTION(BlueprintCallable, Category="Daedalus|Java Arcade") bool ConfigureSudokuCredentials(const FString& Username, const FString& Password);
    UFUNCTION(BlueprintCallable, Category="Daedalus|Java Arcade") bool ConfigureBlackjackToken(const FString& Token);
    UFUNCTION(BlueprintCallable, Category="Daedalus|Java Arcade") bool StartSudokuGame(int32 Difficulty = 1);
    /** Options apply only to the new Java-owned game; ordinary StartSudokuGame stays unchanged. */
    UFUNCTION(BlueprintCallable, Category="Daedalus|Java Arcade") bool StartSudokuGameWithModes(int32 Difficulty, bool bChaos, bool bMirror, bool bTimeAttack);
    UFUNCTION(BlueprintCallable, Category="Daedalus|Java Arcade") bool OpenSudokuGame(const FString& GameId);
    UFUNCTION(BlueprintCallable, Category="Daedalus|Java Arcade") bool ResumeSudokuGame(const FString& GameId);
    UFUNCTION(BlueprintCallable, Category="Daedalus|Java Arcade") bool SaveSudokuGame();
    UFUNCTION(BlueprintCallable, Category="Daedalus|Java Arcade") bool SubmitSudokuMove(int32 Row, int32 Col, int32 Value);
    UFUNCTION(BlueprintCallable, Category="Daedalus|Java Arcade") bool SudokuUndo();
    UFUNCTION(BlueprintCallable, Category="Daedalus|Java Arcade") bool SudokuRedo();
    /** Explicit request only. The Java service may charge existing virtual hint currency. */
    UFUNCTION(BlueprintCallable, Category="Daedalus|Java Arcade") bool RequestSudokuHint();
    UFUNCTION(BlueprintCallable, Category="Daedalus|Java Arcade") bool StartBlackjackSession();
    /** Read an existing process-local table after explicit ID entry; never creates or replays a command. */
    UFUNCTION(BlueprintCallable, Category="Daedalus|Java Arcade") bool OpenBlackjackSession(const FString& SessionId);
    UFUNCTION(BlueprintPure, Category="Daedalus|Java Arcade") bool CanOpenBlackjackSession(const FString& SessionId) const;
    /** Recover an unknown create using its retained exact request ID. Never creates a fresh ID. */
    UFUNCTION(BlueprintCallable, Category="Daedalus|Java Arcade") bool RetryBlackjackCreate();
    UFUNCTION(BlueprintCallable, Category="Daedalus|Java Arcade") bool SubmitBlackjackAction(const FString& Action, int32 Amount = 0, bool bAcceptInsurance = false);
    UFUNCTION(BlueprintCallable, Category="Daedalus|Java Arcade") bool SetBlackjackRule(const FString& Rule, bool bEnabled);
    UFUNCTION(BlueprintCallable, Category="Daedalus|Java Arcade") bool SetBlackjackDecks(int32 Decks);
    UFUNCTION(BlueprintCallable, Category="Daedalus|Java Arcade") bool SetBlackjackSplitLimit(int32 Hands);
    UFUNCTION(BlueprintCallable, Category="Daedalus|Java Arcade") bool RefreshSnapshot();
    UFUNCTION(BlueprintCallable, Category="Daedalus|Java Arcade") bool CloseRemoteBlackjackSession();
    UFUNCTION(BlueprintPure, Category="Daedalus|Java Arcade") FDaedalusJavaArcadeState GetState() const;
    UFUNCTION(BlueprintPure, Category="Daedalus|Java Arcade") bool HasCredentials() const;
    UFUNCTION(BlueprintPure, Category="Daedalus|Java Arcade") bool IsBlackjackActionLegal(const FString& Action, int32 Amount = 0) const;
    UFUNCTION(BlueprintCallable, Category="Daedalus|Java Arcade") void CloseArcade();
    bool MaintainOpenSession();
    int32 GetSlateUserIndex() const { return SlateUserIndex; }

protected:
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;

private:
    enum class Operation : uint8 { None, SudokuBootstrap, SudokuCreate, SudokuRead, SudokuHint, SudokuSync, SudokuSave, SudokuResume, BlackjackCreate, BlackjackRead, BlackjackCommand, BlackjackClose };
    using FTicket = daedalus::java_arcade::Ticket;
    void CancelTransport(bool bForgetSecrets);
    void StopSocket();
    bool CoreTick(float Delta);
    bool SendHttp(Operation Op, const FString& Verb, const FString& Path, const FString& Body, const FTicket& Ticket);
    void FinishHttp(Operation Op, FTicket Ticket, const TSharedPtr<FJavaArcadeHttpTask, ESPMode::ThreadSafe>& Task);
    bool BeginSudoku(bool bCreate, const FString& ExistingId, int32 Difficulty, bool bResume = false,
        bool bChaos = false, bool bMirror = false, bool bTimeAttack = false);
    bool CreateSudokuAfterBootstrap();
    bool ConnectSudokuSocket();
    void HandleSocketMessage(uint64 Epoch, const FString& Message);
    void SocketFailure(uint64 Epoch, bool bPermanent);
    bool SendSudokuCommand(const FString& Type, const TSharedPtr<FJsonObject>& Payload);
    bool ApplySudoku(const TSharedPtr<FJsonObject>& Json);
    bool ApplyBlackjack(const TSharedPtr<FJsonObject>& Json, const FString& ExpectedRequestId);
    bool ReadBlackjackSnapshot(const FTicket& Ticket);
    bool SendBlackjackCommand(const FString& Action, const TSharedPtr<FJsonObject>& Fields);
    void SetMessage(const TCHAR* Text);
    void ReleaseOverlay();
    bool OtherOverlayOwnsInput() const;

    daedalus::java_arcade::SessionGuard Guard;
    daedalus::java_arcade::SudokuView Sudoku;
    daedalus::java_arcade::BlackjackView Blackjack;
    FDaedalusJavaArcadeState View;
    TSharedPtr<FJavaArcadeHttpTask, ESPMode::ThreadSafe> HttpTask;
    TSharedPtr<IWebSocket> Socket;
    TSharedPtr<FJavaArcadeSocketInbox, ESPMode::ThreadSafe> SocketInbox;
    Operation LastReadOperation = Operation::None;
    bool bCreateSudoku = true;
    bool bResumeSudoku = false;
    EDaedalusJavaGame ActiveGame = EDaedalusJavaGame::Sudoku;
    int32 RequestedDifficulty = 1;
    bool bRequestedSudokuChaos = false;
    bool bRequestedSudokuMirror = false;
    bool bRequestedSudokuTimeAttack = false;
    FString RequestedSudokuId;
    // Captured query target; never reflected as an accepted session before validation.
    FString RequestedBlackjackId;
    FString ActiveOrigin;
    FString BasicAuthorization;
    FString BlackjackAuthorization;
    FString CsrfHeader;
    FString CsrfToken;
    FString CookieJar;
    FString AuthenticatedPlayerId;
    FString CreateRequestId;
    FString PendingRequestId;
    FString PendingRequestBody;
    bool bUnknownBlackjackCreate = false;
    bool bAwaitingSudokuReconcile = false;
    FTSTicker::FDelegateHandle TickHandle;

    TSharedPtr<SDaedalusJavaArcade> Widget;
    TSharedPtr<SWidget> WidgetHost;
    TWeakObjectPtr<APlayerController> OpenController;
    TWeakObjectPtr<ADaedalusHero> OpenHero;
    TWeakObjectPtr<UGameViewportClient> OpenViewport;
    TWeakObjectPtr<ULocalPlayer> OpenLocalPlayer;
    int32 SlateUserIndex = INDEX_NONE;
    bool bCloseScheduled = false;
    bool bPreviousMouseCursor = false;
    TEnumAsByte<EMouseCursor::Type> PreviousCursor = EMouseCursor::Default;
    EMouseCaptureMode PreviousCaptureMode = EMouseCaptureMode::CapturePermanently_IncludingInitialMouseDown;
    EMouseLockMode PreviousLockMode = EMouseLockMode::LockOnCapture;
};
