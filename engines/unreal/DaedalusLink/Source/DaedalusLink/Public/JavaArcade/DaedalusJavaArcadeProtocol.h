// SPDX-License-Identifier: MIT
#pragma once

#include <cmath>
#include <array>
#include <cstddef>
#include <cstdint>
#include <string>
#include <vector>

namespace daedalus::java_arcade
{
// Transport policy only. Sudoku and Blackjack rules remain in their Java services.
enum class Phase : std::uint8_t { Closed, Connecting, Ready, Busy, NeedsSync, Failed };
enum class Work : std::uint8_t { None, Read, Mutation };
enum class TimerEvent : std::uint8_t { None, ReadTimeout, MutationTimeout };
struct Ticket
{
    std::uint64_t Generation = 0;
    std::uint64_t Serial = 0;
    Work Kind = Work::None;
};

class SessionGuard
{
public:
    static constexpr std::size_t MaxPayloadBytes = 65536;
    static constexpr double TimeoutSeconds = 10.0;
    static constexpr unsigned MaxReadRetries = 2;

    void Open()
    {
        NextGeneration();
        State = Phase::Connecting;
        Pending = {};
        Retries = 0;
        RetryAt = 0.0;
        Uncertain = false;
    }
    void Close()
    {
        NextGeneration();
        Pending = {};
        State = Phase::Closed;
        Retries = 0;
        RetryAt = 0.0;
        Uncertain = false;
    }
    Ticket BeginRead(double Now)
    {
        if (!ValidClock(Now) || State == Phase::Closed || Pending.Kind != Work::None)
            return {};
        return Start(Work::Read, Now);
    }
    Ticket BeginMutation(double Now)
    {
        if (!ValidClock(Now) || State != Phase::Ready || Pending.Kind != Work::None)
            return {};
        Retries = 0;
        RetryAt = 0.0;
        return Start(Work::Mutation, Now);
    }
    Ticket BeginCreation(double Now)
    {
        if (!ValidClock(Now) || Uncertain || Pending.Kind != Work::None
            || (State != Phase::Connecting && State != Phase::Ready)) return {};
        Retries = 0;
        RetryAt = 0.0;
        return Start(Work::Mutation, Now);
    }
    bool ContinueBootstrap(const Ticket& T)
    {
        if (!Current(T) || T.Kind != Work::Read || Uncertain) return false;
        Pending = {};
        State = Phase::Connecting;
        Retries = 0;
        RetryAt = 0.0;
        return true;
    }
    Ticket BeginExplicitCreateRecovery(double Now)
    {
        if (!ValidClock(Now) || !Uncertain || State != Phase::NeedsSync || Pending.Kind != Work::None) return {};
        return Start(Work::Mutation, Now);
    }
    bool Current(const Ticket& T) const
    {
        return T.Kind != Work::None && T.Generation == Generation && T.Serial == Pending.Serial
            && T.Kind == Pending.Kind && State != Phase::Closed;
    }
    bool Snapshot(const Ticket& T)
    {
        if (!Current(T)) return false;
        Pending = {};
        State = Phase::Ready;
        Retries = 0;
        RetryAt = 0.0;
        // Uncertain is cleared only after the user-visible authoritative resync.
        Uncertain = false;
        return true;
    }
    bool NeedsSnapshot(const Ticket& T)
    {
        if (!Current(T)) return false;
        Pending = {};
        State = Phase::NeedsSync;
        return true;
    }
    bool Reject(const Ticket& T, bool AuthorizationFailure)
    {
        if (!Current(T)) return false;
        Pending = {};
        State = AuthorizationFailure ? Phase::Failed : Phase::NeedsSync;
        RetryAt = 0.0;
        return true;
    }
    bool Fail(const Ticket& T, double Now, bool RetryableRead)
    {
        if (!Current(T) || !ValidClock(Now)) return false;
        const Work Kind = Pending.Kind;
        Pending = {};
        if (Kind == Work::Mutation)
        {
            State = Phase::NeedsSync;
            Uncertain = true;
            RetryAt = 0.0; // Unknown-outcome mutations are never automatically replayed.
        }
        else if (RetryableRead && Retries < MaxReadRetries)
        {
            ++Retries;
            RetryAt = Now + static_cast<double>(Retries); // One second, then two seconds.
            State = Uncertain ? Phase::NeedsSync : Phase::Connecting;
        }
        else
        {
            State = Uncertain ? Phase::NeedsSync : Phase::Failed;
            RetryAt = 0.0;
        }
        return true;
    }
    TimerEvent Tick(double Now)
    {
        if (!ValidClock(Now) || Pending.Kind == Work::None || Now < Deadline) return TimerEvent::None;
        const Ticket Expired = Pending;
        const bool Mutation = Expired.Kind == Work::Mutation;
        Fail(Expired, Now, !Mutation);
        return Mutation ? TimerEvent::MutationTimeout : TimerEvent::ReadTimeout;
    }
    bool ReadRetryDue(double Now) const
    {
        return ValidClock(Now) && RetryAt > 0.0 && Now >= RetryAt && Pending.Kind == Work::None
            && State != Phase::Closed;
    }
    Phase GetPhase() const { return State; }
    Work PendingKind() const { return Pending.Kind; }
    Ticket PendingTicket() const { return Pending; }
    bool CanMutate() const { return State == Phase::Ready && Pending.Kind == Work::None; }
    bool HasUncertainOutcome() const { return Uncertain; }
    std::uint64_t Epoch() const { return Generation; }

private:
    static bool ValidClock(double Now) { return std::isfinite(Now) && Now >= 0.0; }
    void NextGeneration() { ++Generation; if (Generation == 0) ++Generation; }
    Ticket Start(Work Kind, double Now)
    {
        ++Serial;
        if (Serial == 0) ++Serial;
        Pending = { Generation, Serial, Kind };
        Deadline = Now + TimeoutSeconds;
        RetryAt = 0.0;
        State = Phase::Busy;
        return Pending;
    }
    Phase State = Phase::Closed;
    Ticket Pending;
    std::uint64_t Generation = 0;
    std::uint64_t Serial = 0;
    double Deadline = 0.0;
    double RetryAt = 0.0;
    unsigned Retries = 0;
    bool Uncertain = false;
};

inline bool PayloadFits(std::size_t Bytes, std::size_t Limit = SessionGuard::MaxPayloadBytes)
{
    return Bytes > 0 && Bytes <= Limit;
}
inline bool LoopbackOrigin(const std::string& Candidate, std::string& Out)
{
    std::string Value = Candidate;
    if (!Value.empty() && Value.back() == '/') Value.pop_back();
    const std::string Prefix = "http://127.0.0.1:";
    if (Value.compare(0, Prefix.size(), Prefix) != 0) return false;
    const std::string Port = Value.substr(Prefix.size());
    if (Port.empty() || Port.size() > 5) return false;
    unsigned Number = 0;
    for (char C : Port) { if (C < '0' || C > '9') return false; Number = Number * 10u + static_cast<unsigned>(C - '0'); }
    if (Number < 1 || Number > 65535) return false;
    Out = Value;
    return true;
}
struct SudokuView
{
    std::string GameId;
    std::string Owner;
    std::array<int, 81> Values{};
    std::array<bool, 81> Givens{};
    std::array<std::uint16_t, 81> PencilMasks{};
    bool ChaosMode = false;
    bool MirrorMode = false;
    bool Solved = false;
    bool TimeUp = false;
    int Difficulty = 1;
    std::int64_t Score = 0;
    int Lives = 0;
    std::int64_t ElapsedSeconds = 0;
    std::int64_t SecondsLeft = 0;
    std::int64_t TimeLimitSeconds = 0;
    std::int64_t HintCount = 0;
    std::int64_t MoveCount = 0;
};
inline bool ValidSudoku(const SudokuView& V)
{
    if (V.GameId.empty() || V.GameId.size() > 256 || V.Owner.empty() || V.Owner.size() > 128
        || V.Difficulty < 1 || V.Difficulty > 5 || V.Lives < 0 || V.Lives > 1000
        || V.ElapsedSeconds < 0 || V.SecondsLeft < 0 || V.TimeLimitSeconds < 0 || V.HintCount < 0 || V.MoveCount < 0
        || V.MoveCount > 2147483647LL || V.HintCount > 2147483647LL || V.Score < -2147483648LL || V.Score > 2147483647LL
        || V.ElapsedSeconds > 9007199254740991LL || V.SecondsLeft > 9007199254740991LL || V.TimeLimitSeconds > 9007199254740991LL
        || (V.Solved && V.TimeUp)) return false;
    for (std::size_t I = 0; I < V.Values.size(); ++I)
        if (V.Values[I] < 0 || V.Values[I] > 9 || (V.Givens[I] && V.Values[I] == 0)) return false;
    for (std::uint16_t Mask : V.PencilMasks) if ((Mask & ~static_cast<std::uint16_t>(0x3fe)) != 0) return false;
    return true;
}
inline constexpr std::size_t SudokuSavedListLimit = 10;
// A list contains complete board DTOs, so it needs an aggregate response budget.
inline constexpr std::size_t SudokuSavedListMaxPayloadBytes = SessionGuard::MaxPayloadBytes * SudokuSavedListLimit;
struct SudokuSavedGame
{
    std::string GameId;
    int Difficulty = 1;
    int FilledCells = 0;
    int GivensCount = 0;
    int Lives = 0;
    std::int64_t ElapsedSeconds = 0;
    bool Solved = false;
    bool TimeUp = false;
};
// The service returns full boards. Publish only a completely validated,
// account-scoped metadata list; browsing never applies a board to the live game.
inline bool ProjectSavedSudokuGames(const std::vector<SudokuView>& Boards,
    const std::string& AuthenticatedOwner, std::vector<SudokuSavedGame>& Out)
{
    if (AuthenticatedOwner.empty() || AuthenticatedOwner.size() > 128
        || AuthenticatedOwner.find('\0') != std::string::npos
        || Boards.size() > SudokuSavedListLimit) return false;
    std::vector<SudokuSavedGame> Candidate;
    Candidate.reserve(Boards.size());
    for (const SudokuView& Board : Boards)
    {
        if (!ValidSudoku(Board) || Board.Owner != AuthenticatedOwner
            || Board.GameId.find('\0') != std::string::npos) return false;
        for (const SudokuSavedGame& Previous : Candidate)
            if (Previous.GameId == Board.GameId) return false;
        SudokuSavedGame Summary;
        Summary.GameId = Board.GameId;
        Summary.Difficulty = Board.Difficulty;
        Summary.Lives = Board.Lives;
        Summary.ElapsedSeconds = Board.ElapsedSeconds;
        Summary.Solved = Board.Solved;
        Summary.TimeUp = Board.TimeUp;
        for (std::size_t I = 0; I < Board.Values.size(); ++I)
        {
            if (Board.Values[I] != 0) ++Summary.FilledCells;
            if (Board.Givens[I]) ++Summary.GivensCount;
        }
        Candidate.push_back(Summary);
    }
    Out.swap(Candidate);
    return true;
}
inline bool CanSubmitSudoku(const SudokuView& V, const std::string& AuthenticatedPlayer, int Row, int Col, int Value)
{
    return ValidSudoku(V) && !V.Solved && !V.TimeUp && AuthenticatedPlayer == V.Owner
        && Row >= 0 && Row < 9 && Col >= 0 && Col < 9 && Value >= 0 && Value <= 9
        && !V.Givens[static_cast<std::size_t>(Row * 9 + Col)];
}
struct VisibleCard { std::string Rank; std::string Suit; };
inline bool ValidCard(const VisibleCard& C)
{
    const bool Rank = C.Rank == "A" || C.Rank == "2" || C.Rank == "3" || C.Rank == "4"
        || C.Rank == "5" || C.Rank == "6" || C.Rank == "7" || C.Rank == "8"
        || C.Rank == "9" || C.Rank == "10" || C.Rank == "J" || C.Rank == "Q" || C.Rank == "K";
    const bool Suit = C.Suit == "CLUBS" || C.Suit == "DIAMONDS" || C.Suit == "HEARTS" || C.Suit == "SPADES";
    return Rank && Suit;
}
struct VisibleHand
{
    std::vector<VisibleCard> Cards;
    std::int64_t Bet = 0;
    int Value = 0;
};
struct BlackjackView
{
    std::string SessionId;
    std::int64_t Revision = 0;
    std::string Phase;
    std::int64_t Bankroll = 0;
    std::int64_t PendingBet = 0;
    int ActiveHand = -1;
    std::vector<VisibleHand> Hands;
    std::vector<VisibleCard> DealerCards;
    int HiddenDealerCards = 0;
    bool HasDealerDerivedValues = false;
    std::vector<std::string> LegalActions;
    std::vector<int> LegalBetAmounts;
    bool Closed = false;
};
inline bool KnownBlackjackAction(const std::string& A)
{
    return A == "bet" || A == "clearBet" || A == "rebet" || A == "deal" || A == "hit"
        || A == "stand" || A == "double" || A == "split" || A == "surrender" || A == "insurance"
        || A == "setRule" || A == "setDecks" || A == "setSplitLimit" || A == "reload" || A == "newSession";
}
inline bool ValidBlackjack(const BlackjackView& V)
{
    if (V.SessionId.empty() || V.SessionId.size() > 64 || V.Revision < 0 || V.Revision > 9007199254740991LL
        || V.Bankroll < 0 || V.Bankroll > 2147483647LL || V.PendingBet < 0 || V.PendingBet > 2147483647LL
        || V.Hands.size() > 4 || V.DealerCards.size() > 21 || V.HiddenDealerCards < 0 || V.HiddenDealerCards > 1
        || (V.HiddenDealerCards > 0 && (V.HasDealerDerivedValues || V.DealerCards.size() != 1)) || V.LegalActions.size() > 16
        || V.LegalBetAmounts.size() > 5 || V.ActiveHand < -1 || V.ActiveHand > 3) return false;
    if (V.Phase != "BETTING" && V.Phase != "DEALING" && V.Phase != "INSURANCE" && V.Phase != "PLAYER"
        && V.Phase != "DEALER" && V.Phase != "SETTLE") return false;
    const bool LiveHidden = V.Phase == "DEALING" || V.Phase == "INSURANCE" || V.Phase == "PLAYER";
    if (LiveHidden && (V.HasDealerDerivedValues || V.DealerCards.size() > 1
        || (!V.DealerCards.empty() && V.HiddenDealerCards != 1))) return false;
    if ((V.Phase == "PLAYER" || V.Phase == "INSURANCE") && (V.DealerCards.size() != 1 || V.HiddenDealerCards != 1)) return false;
    if ((V.Phase == "PLAYER" && V.ActiveHand < 0) || (V.Phase != "PLAYER" && V.ActiveHand != -1)) return false;
    if (V.ActiveHand >= 0 && static_cast<std::size_t>(V.ActiveHand) >= V.Hands.size()) return false;
    for (const VisibleHand& H : V.Hands)
    {
        if (H.Cards.size() > 21 || H.Bet < 0 || H.Bet > 2147483647LL || H.Value < 0 || H.Value > 231) return false;
        for (const VisibleCard& C : H.Cards) if (!ValidCard(C)) return false;
    }
    for (const VisibleCard& C : V.DealerCards) if (!ValidCard(C)) return false;
    for (const std::string& A : V.LegalActions) if (!KnownBlackjackAction(A)) return false;
    for (int N : V.LegalBetAmounts) if (N != 1 && N != 5 && N != 25 && N != 100 && N != 500) return false;
    return true;
}
inline bool CanSubmitBlackjack(const BlackjackView& V, const std::string& Action, int Amount = 0)
{
    if (!ValidBlackjack(V) || V.Closed || V.Revision >= 9007199254740991LL || !KnownBlackjackAction(Action)) return false;
    bool Legal = false;
    for (const std::string& A : V.LegalActions) if (A == Action) Legal = true;
    if (!Legal) return false;
    if (Action != "bet") return true;
    for (int N : V.LegalBetAmounts) if (N == Amount) return true;
    return false;
}
}
