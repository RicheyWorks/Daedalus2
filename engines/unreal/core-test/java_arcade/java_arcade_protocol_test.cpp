// SPDX-License-Identifier: MIT
#include "JavaArcade/DaedalusJavaArcadeProtocol.h"
#include <array>
#include <cstdlib>
#include <iostream>
#include <limits>

namespace JA = daedalus::java_arcade;
static unsigned Checks = 0;
static void Check(bool Good, const char* What)
{
    ++Checks;
    if (!Good) { std::cerr << "FAILED: " << What << '\n'; std::exit(1); }
}
struct ObservedGuard
{
    JA::Phase State;
    JA::Ticket Pending;
    std::uint64_t Epoch;
    bool CanMutate;
    bool Uncertain;
    bool RetryDue;
};

static ObservedGuard Observe(const JA::SessionGuard& S, double Now)
{
    return {S.GetPhase(), S.PendingTicket(), S.Epoch(), S.CanMutate(),
        S.HasUncertainOutcome(), S.ReadRetryDue(Now)};
}

static bool Same(const ObservedGuard& A, const ObservedGuard& B)
{
    return A.State == B.State && A.Pending.Generation == B.Pending.Generation
        && A.Pending.Serial == B.Pending.Serial && A.Pending.Kind == B.Pending.Kind
        && A.Epoch == B.Epoch && A.CanMutate == B.CanMutate
        && A.Uncertain == B.Uncertain && A.RetryDue == B.RetryDue;
}

// Delayed network completions must be inert even when another request is pending.
// All four completion entry points are checked against public session state.
static void RefuseCompletion(JA::SessionGuard& S, const JA::Ticket& Stale, double Now)
{
    const ObservedGuard Before = Observe(S, Now);
    Check(!S.Current(Stale), "foreign callback ticket is not current");
    Check(!S.ContinueBootstrap(Stale), "foreign authentication callback is refused");
    Check(!S.Snapshot(Stale), "foreign snapshot callback is refused");
    Check(!S.NeedsSnapshot(Stale), "foreign mutation acknowledgment is refused");
    Check(!S.Reject(Stale, true), "foreign authorization callback is refused");
    Check(!S.Fail(Stale, Now, true), "foreign failure callback cannot schedule a retry");
    Check(Same(Before, Observe(S, Now)), "foreign completions preserve observable session state");
}

static void ExistingTrace()
{
    JA::SessionGuard S;
    Check(!S.CanMutate(), "closed session refuses mutation");
    Check(S.BeginRead(0).Kind == JA::Work::None, "closed session refuses request");
    S.Open();
    const auto Read = S.BeginRead(10);
    Check(Read.Kind == JA::Work::Read, "bootstrap read starts");
    Check(S.BeginRead(10).Kind == JA::Work::None, "one read in flight");
    Check(S.BeginMutation(10).Kind == JA::Work::None, "bootstrap locks mutations");
    Check(S.Snapshot(Read) && S.CanMutate(), "valid authoritative snapshot enables command");
    Check(!S.Snapshot(Read), "duplicate callback rejected");
    const auto Command = S.BeginMutation(11);
    Check(Command.Kind == JA::Work::Mutation, "one mutation starts");
    Check(S.BeginMutation(11).Kind == JA::Work::None, "no queued double action");
    Check(S.BeginRead(11).Kind == JA::Work::None, "read cannot race mutation");
    Check(S.Tick(20.999) == JA::TimerEvent::None, "deadline retained before timeout");
    Check(S.Tick(21) == JA::TimerEvent::MutationTimeout, "mutation times out");
    Check(S.HasUncertainOutcome() && !S.CanMutate(), "ambiguous result locks commands");
    Check(!S.ReadRetryDue(100), "mutation is never auto replayed or silently resynced");
    Check(!S.Snapshot(Command), "late timed-out mutation callback rejected");
    const auto Sync = S.BeginRead(22);
    Check(S.Snapshot(Sync) && S.CanMutate() && !S.HasUncertainOutcome(), "explicit authoritative resync unlocks");
    const auto Old = S.BeginMutation(23);
    S.Close();
    Check(!S.Current(Old) && !S.Snapshot(Old), "close invalidates all late callbacks");
    S.Open();
    Check(!S.Current(Old), "reopen does not revive previous session callback");
    auto R = S.BeginRead(30);
    Check(S.Fail(R, 30, true), "retryable safe read fails");
    Check(!S.ReadRetryDue(30.999) && S.ReadRetryDue(31), "first retry waits one second");
    R = S.BeginRead(31);
    Check(S.Fail(R, 31, true), "second safe read fails");
    Check(!S.ReadRetryDue(32.999) && S.ReadRetryDue(33), "second retry waits two seconds");
    R = S.BeginRead(33);
    Check(S.Fail(R, 33, true), "third safe read fails");
    Check(!S.ReadRetryDue(100) && S.GetPhase() == JA::Phase::Failed, "retry budget capped at two");
    S.Open();
    R = S.BeginRead(40);
    Check(S.Reject(R, true) && S.GetPhase() == JA::Phase::Failed, "authorization failure fails closed");
    Check(!S.ReadRetryDue(100), "authorization never auto retried");
    S.Open();
    Check(S.BeginRead(-1).Kind == JA::Work::None, "negative clock refused");
    Check(S.BeginRead(std::numeric_limits<double>::quiet_NaN()).Kind == JA::Work::None, "NaN clock refused");
    Check(S.BeginRead(std::numeric_limits<double>::infinity()).Kind == JA::Work::None, "infinite clock refused");
    R = S.BeginRead(50);
    Check(S.Tick(std::numeric_limits<double>::infinity()) == JA::TimerEvent::None, "invalid clock cannot expire request");
    Check(S.Tick(60) == JA::TimerEvent::ReadTimeout, "safe read deadline expires");
    Check(!S.Snapshot(R), "late read timeout response rejected");
    Check(S.ReadRetryDue(61), "read timeout schedules bounded retry");
    R = S.BeginRead(61);
    Check(S.Snapshot(R), "successful retry refreshes authoritative state");
    const auto C = S.BeginMutation(62);
    Check(S.NeedsSnapshot(C) && !S.CanMutate(), "ack without snapshot remains locked");
    R = S.BeginRead(63);
    Check(S.Snapshot(R) && S.CanMutate(), "authoritative board after ack unlocks");
    Check(JA::SessionGuard::MaxPayloadBytes == 65536, "response cap defined");
}

static void TicketIdentityAndCancellation()
{
    JA::SessionGuard S;
    RefuseCompletion(S, {}, 0);
    S.Open();
    const auto First = S.BeginRead(1);
    Check(S.Snapshot(First), "first bootstrap snapshot is accepted");
    const auto Second = S.BeginRead(2);
    Check(First.Generation == Second.Generation && First.Serial != Second.Serial,
        "successive requests in one session use distinct serials");
    RefuseCompletion(S, First, 2);
    const std::array<JA::Ticket, 4> Forged{{
        {Second.Generation + 1, Second.Serial, Second.Kind},
        {Second.Generation, Second.Serial + 1, Second.Kind},
        {Second.Generation, Second.Serial, JA::Work::Mutation},
        {Second.Generation, Second.Serial, JA::Work::None}
    }};
    for (const auto& Ticket : Forged) RefuseCompletion(S, Ticket, 2);
    Check(S.Current(Second), "foreign completions do not cancel the real request");

    const auto BeforeReopen = S.Epoch();
    S.Open(); // Connecting to another cabinet/service invalidates the old read.
    Check(S.Epoch() != BeforeReopen && S.PendingKind() == JA::Work::None,
        "open replaces the epoch and cancels an existing request");
    RefuseCompletion(S, Second, 3);
    const auto Fresh = S.BeginRead(3);
    RefuseCompletion(S, Second, 3);
    Check(S.Snapshot(Fresh), "new session accepts only its own authoritative snapshot");
    const auto Mutation = S.BeginMutation(4);
    S.Close();
    S.Close();
    RefuseCompletion(S, Mutation, 5);
    Check(S.GetPhase() == JA::Phase::Closed && !S.ReadRetryDue(1000),
        "repeated close leaves no pending work or background retry");
}

static void NoImplicitRequestQueue()
{
    JA::SessionGuard S;
    S.Open();
    const auto Bootstrap = S.BeginRead(0);
    for (int Attempt = 0; Attempt < 8; ++Attempt)
    {
        Check(S.BeginRead(0).Kind == JA::Work::None, "busy bootstrap rejects another read");
        Check(S.BeginMutation(0).Kind == JA::Work::None, "busy bootstrap rejects a command");
        Check(S.BeginCreation(0).Kind == JA::Work::None, "busy bootstrap rejects a creation request");
    }
    Check(S.Snapshot(Bootstrap) && S.PendingKind() == JA::Work::None,
        "bootstrap completion does not run a queued request");
    const auto Mutation = S.BeginMutation(1);
    for (int Attempt = 0; Attempt < 8; ++Attempt)
    {
        Check(S.BeginRead(1).Kind == JA::Work::None, "busy mutation rejects a racing read");
        Check(S.BeginMutation(1).Kind == JA::Work::None, "busy mutation rejects duplicate input");
        Check(S.BeginCreation(1).Kind == JA::Work::None, "busy mutation rejects session replacement");
    }
    Check(S.NeedsSnapshot(Mutation) && S.PendingKind() == JA::Work::None,
        "acknowledgment does not send rejected duplicate commands later");
    Check(S.BeginMutation(2).Kind == JA::Work::None,
        "acknowledgment without authoritative state cannot enable another mutation");
    const auto Sync = S.BeginRead(2);
    Check(S.Snapshot(Sync) && S.CanMutate(), "only explicit state refresh restores command readiness");
}

static void InvalidClockPreservesState()
{
    const std::array<double, 4> Invalid{{-1.0, std::numeric_limits<double>::quiet_NaN(),
        std::numeric_limits<double>::infinity(), -std::numeric_limits<double>::infinity()}};
    JA::SessionGuard S;
    S.Open();
    for (double Clock : Invalid)
    {
        const auto Before = Observe(S, 0);
        Check(S.BeginRead(Clock).Kind == JA::Work::None, "invalid bootstrap clock refuses a request");
        Check(Same(Before, Observe(S, 0)), "invalid bootstrap clock cannot change the guard");
    }
    const auto Bootstrap = S.BeginRead(0);
    Check(S.Snapshot(Bootstrap), "zero is a valid monotonic clock origin");
    for (double Clock : Invalid)
    {
        const auto Before = Observe(S, 0);
        Check(S.BeginMutation(Clock).Kind == JA::Work::None, "invalid command clock refuses a mutation");
        Check(Same(Before, Observe(S, 0)), "invalid command clock keeps authoritative readiness");
    }
    const auto Mutation = S.BeginMutation(1);
    for (double Clock : Invalid)
    {
        const auto Before = Observe(S, 1);
        Check(!S.Fail(Mutation, Clock, true), "invalid failure clock cannot abandon current work");
        Check(S.Tick(Clock) == JA::TimerEvent::None, "invalid ticker clock cannot expire current work");
        Check(!S.ReadRetryDue(Clock), "invalid retry clock cannot release work");
        Check(Same(Before, Observe(S, 1)), "invalid clock paths preserve current request and flags");
    }
    Check(S.Current(Mutation) && S.Tick(10.999) == JA::TimerEvent::None,
        "invalid clocks leave the original finite deadline intact");
    Check(S.Tick(11) == JA::TimerEvent::MutationTimeout, "original deadline still expires precisely");
}

static void SafeReadRetryBudget()
{
    JA::SessionGuard S;
    S.Open();
    auto Read = S.BeginRead(0);
    Check(S.Tick(10) == JA::TimerEvent::ReadTimeout, "bootstrap read expires after ten seconds");
    RefuseCompletion(S, Read, 10);
    Check(!S.ReadRetryDue(10.999) && S.ReadRetryDue(11), "first safe retry uses one-second backoff");
    Read = S.BeginRead(11);
    Check(S.Tick(21) == JA::TimerEvent::ReadTimeout, "first retry has its own deadline");
    RefuseCompletion(S, Read, 21);
    Check(!S.ReadRetryDue(22.999) && S.ReadRetryDue(23), "second safe retry uses two-second backoff");
    Read = S.BeginRead(23);
    Check(S.Tick(33) == JA::TimerEvent::ReadTimeout, "second retry can time out");
    RefuseCompletion(S, Read, 33);
    Check(S.GetPhase() == JA::Phase::Failed && !S.CanMutate() && !S.ReadRetryDue(1e6),
        "exhausted read retries fail closed without an unbounded reconnect loop");
    Check(S.Tick(1e6) == JA::TimerEvent::None, "expired read cannot create repeated timeout events");

    // An explicit successful refresh starts a new retry budget; retrying a failed
    // mutation itself is never part of this safe-read policy.
    Read = S.BeginRead(40);
    Check(S.Snapshot(Read), "explicit successful read recovers a failed connection");
    Read = S.BeginRead(41);
    Check(S.Fail(Read, 41, true) && S.ReadRetryDue(42), "success resets the safe-read retry budget");
    Read = S.BeginRead(42);
    Check(S.Reject(Read, true), "authorization failure is accepted only for current request");
    Check(S.GetPhase() == JA::Phase::Failed && !S.ReadRetryDue(1000),
        "authorization failure does not consume the reconnect retry path");
}

static void AmbiguousMutationRequiresReconciliation()
{
    for (bool RetryableReadFlag : {false, true})
    {
        JA::SessionGuard S;
        S.Open();
        auto Read = S.BeginRead(0);
        Check(S.Snapshot(Read), "mutation scenario starts from authoritative state");
        const auto Mutation = S.BeginMutation(1);
        Check(S.Fail(Mutation, 2, RetryableReadFlag), "transport failure marks the current mutation uncertain");
        Check(S.HasUncertainOutcome() && S.GetPhase() == JA::Phase::NeedsSync && !S.CanMutate(),
            "unknown mutation outcome disables all new commands");
        Check(!S.ReadRetryDue(1e6) && S.BeginMutation(3).Kind == JA::Work::None,
            "mutation never replays even when caller labels a failure retryable");
        RefuseCompletion(S, Mutation, 3);

        Read = S.BeginRead(4);
        Check(S.Fail(Read, 4, true), "explicit reconciliation read may use the bounded read retry policy");
        Check(S.HasUncertainOutcome() && !S.CanMutate(), "failed reconciliation retains ambiguity");
        Read = S.BeginRead(5);
        Check(S.Fail(Read, 5, true), "second reconciliation read may fail");
        Read = S.BeginRead(7);
        Check(S.Fail(Read, 7, true), "last reconciliation read may fail");
        Check(S.GetPhase() == JA::Phase::NeedsSync && S.HasUncertainOutcome() && !S.ReadRetryDue(1e6),
            "retry exhaustion cannot turn an uncertain mutation into a known failure or success");
        Check(S.BeginMutation(8).Kind == JA::Work::None, "uncertain outcome still blocks a replacement action");
        Read = S.BeginRead(8);
        Check(S.Snapshot(Read) && !S.HasUncertainOutcome() && S.CanMutate(),
            "only a current validated authoritative snapshot clears mutation ambiguity");
        RefuseCompletion(S, Mutation, 8);
    }
}

static void ReopenCallbackLifecycles()
{
    JA::SessionGuard S;
    JA::Ticket Previous;
    std::uint64_t PreviousEpoch = 0;
    for (int Session = 0; Session < 16; ++Session)
    {
        const double Now = Session * 100.0;
        S.Open();
        Check(S.Epoch() != PreviousEpoch && S.Epoch() != 0, "each reopened session has a distinct nonzero epoch");
        PreviousEpoch = S.Epoch();
        const auto Read = S.BeginRead(Now);
        RefuseCompletion(S, Previous, Now);
        Check(S.Snapshot(Read), "new session bootstrap succeeds after old callbacks are rejected");
        Previous = S.BeginMutation(Now + 1);
        Check(S.Tick(Now + 11) == JA::TimerEvent::MutationTimeout, "each session can leave an uncertain command");
        S.Close();
        RefuseCompletion(S, Previous, Now + 12);
        Check(!S.CanMutate() && !S.HasUncertainOutcome() && !S.ReadRetryDue(Now + 1000),
            "closed session clears its own uncertainty and schedules no work");
    }
}

// This exercises only the portable ticket policy. The actor's event routing is
// reviewed separately: a WS board is a wake-up for a fresh GET, not its receipt.
static void FreshReadReconciliationTickets()
{
    JA::SessionGuard S;
    S.Open();
    const auto InitialRead = S.BeginRead(0);
    Check(S.Snapshot(InitialRead), "reconciliation starts with an authoritative board");
    const auto Command = S.BeginMutation(1);
    Check(S.NeedsSnapshot(Command) && !S.CanMutate(),
        "board notification can leave a command locked pending a separate read");
    Check(S.BeginMutation(2).Kind == JA::Work::None,
        "notification alone cannot authorize the next mutation");
    const auto FreshGet = S.BeginRead(2);
    Check(FreshGet.Kind == JA::Work::Read && FreshGet.Serial != Command.Serial,
        "reconciliation GET has a distinct local request ticket");
    RefuseCompletion(S, InitialRead, 2);
    RefuseCompletion(S, Command, 2);
    Check(!S.CanMutate() && S.Current(FreshGet),
        "old bootstrap or command completions cannot finish the fresh GET");
    Check(S.Snapshot(FreshGet) && S.CanMutate(),
        "only the current validated GET restores visible-state readiness");
    RefuseCompletion(S, FreshGet, 3);
    const auto Next = S.BeginMutation(3);
    RefuseCompletion(S, Command, 3);
    RefuseCompletion(S, FreshGet, 3);
    Check(S.Current(Next), "late prior reconciliation cannot complete a later action");

    Check(S.Fail(Next, 4, false) && S.HasUncertainOutcome(),
        "true action transport failure remains an unknown outcome");
    Check(!S.ReadRetryDue(1000), "unknown mutation never schedules its own replay or refresh");
    const auto ExplicitGet = S.BeginRead(5);
    Check(S.Tick(15) == JA::TimerEvent::ReadTimeout && S.HasUncertainOutcome(),
        "a timed-out explicit read does not erase prior action uncertainty");
    const auto RetriedGet = S.BeginRead(16);
    RefuseCompletion(S, ExplicitGet, 16);
    Check(S.Snapshot(RetriedGet) && S.CanMutate() && !S.HasUncertainOutcome(),
        "a fresh successful safe read resolves visible state without replaying the action");
}

static void CreationBootstrapIsNotGameplayAuthority()
{
    JA::SessionGuard S;
    S.Open();
    Check(S.BeginMutation(0).Kind == JA::Work::None,
        "connected credentials alone do not authorize gameplay commands");
    const auto Authentication = S.BeginRead(0);
    Check(S.ContinueBootstrap(Authentication) && !S.CanMutate(),
        "authentication metadata continues bootstrap without publishing a board");
    RefuseCompletion(S, Authentication, 0);
    const auto Creation = S.BeginCreation(1);
    Check(Creation.Kind == JA::Work::Mutation, "new game creation is classified as a mutation");
    const auto Before = Observe(S, 1);
    Check(!S.ContinueBootstrap(Creation), "creation response cannot be mistaken for authentication metadata");
    Check(Same(Before, Observe(S, 1)), "invalid bootstrap completion keeps creation pending");
    Check(S.Tick(11) == JA::TimerEvent::MutationTimeout,
        "lost create response has an uncertain mutation outcome");
    Check(!S.ReadRetryDue(1000) && S.BeginCreation(12).Kind == JA::Work::None,
        "lost create response is never automatically replaced with another new game");

    const auto ReconnectAuthentication = S.BeginRead(12);
    // Reauthentication may be refused or allowed to progress, but it must not
    // turn an unknown-outcome mutation into authority to create a replacement.
    S.ContinueBootstrap(ReconnectAuthentication);
    Check(S.HasUncertainOutcome() && !S.CanMutate() && S.BeginCreation(13).Kind == JA::Work::None,
        "reauthentication cannot bypass uncertain-outcome reconciliation");
    if (S.Current(ReconnectAuthentication))
        Check(S.NeedsSnapshot(ReconnectAuthentication), "rejected reauthentication can finish without accepting game state");
    const auto Authoritative = S.BeginRead(14);
    Check(S.Snapshot(Authoritative) && S.CanMutate(), "explicit authoritative reconciliation resolves lost creation");
    RefuseCompletion(S, Creation, 14);
    const auto Replacement = S.BeginCreation(15);
    Check(Replacement.Kind == JA::Work::Mutation, "known-state explicit new game may replace the completed session");
    S.Close();
    RefuseCompletion(S, Replacement, 16);
}

static void PayloadBoundaries()
{
    Check(!JA::PayloadFits(0), "empty response is not an authoritative snapshot");
    Check(JA::PayloadFits(1), "nonempty response can enter bounded decoding");
    Check(JA::PayloadFits(65535) && JA::PayloadFits(65536), "response limit includes its exact boundary");
    Check(!JA::PayloadFits(65537), "oversized response is refused before typed decoding");
    Check(!JA::PayloadFits(std::numeric_limits<std::size_t>::max()), "length overflow cannot evade the response cap");
    Check(!JA::PayloadFits(1, 0), "zero configured limit accepts no response");
    Check(JA::PayloadFits(1024, 1024) && !JA::PayloadFits(1025, 1024), "smaller endpoint limits retain strict bounds");
}

static void EndpointBoundaries()
{
    const std::array<const char*, 7> Accepted{{"http://127.0.0.1:1", "http://127.0.0.1:80",
        "http://127.0.0.1:8080", "http://127.0.0.1:8091", "http://127.0.0.1:65535",
        "http://127.0.0.1:00080", "http://127.0.0.1:8080/"}};
    for (const char* Candidate : Accepted)
    {
        std::string Out = "unchanged";
        Check(JA::LoopbackOrigin(Candidate, Out), "direct IPv4 loopback endpoint accepts valid numeric port");
        std::string Expected = Candidate;
        if (Expected.back() == '/') Expected.pop_back();
        Check(Out == Expected, "endpoint normalization removes only one allowed trailing slash");
    }
    const std::array<const char*, 33> Refused{{"", "http://127.0.0.1", "http://127.0.0.1:",
        "http://127.0.0.1:0", "http://127.0.0.1:65536", "http://127.0.0.1:999999", "http://127.0.0.1:-1",
        "http://127.0.0.1:+80", "http://127.0.0.1:8.0", "http://127.0.0.1: 80", " http://127.0.0.1:80",
        "http://127.0.0.1:80 ", "HTTP://127.0.0.1:80", "https://127.0.0.1:80", "ws://127.0.0.1:80",
        "http://localhost:80", "http://127.0.0.2:80", "http://[::1]:80", "http://2130706433:80",
        "http://127.0.0.1.example:80", "http://127.0.0.1:80@example.com", "http://user@127.0.0.1:80",
        "https://example.com", "http://127.0.0.1:80/path", "http://127.0.0.1:80//", "http://127.0.0.1:80/../",
        "http://127.0.0.1:80?next=external", "http://127.0.0.1:80#fragment", "http://127.0.0.1:80\\external",
        "http://127.0.0.1:80\r\nAuthorization: bad", "http://127.0.0.1:%38%30", "http://127.0.0.1:80:81",
        "http://127.0.0.1:\xEF\xBC\x91"}};
    for (const char* Candidate : Refused)
    {
        std::string Out = "unchanged";
        Check(!JA::LoopbackOrigin(Candidate, Out), "external, ambiguous or decorated endpoint is refused");
        Check(Out == "unchanged", "refused endpoint cannot partially replace the previous origin");
    }
    const char EmbeddedNull[] = "http://127.0.0.1:80\0@example.com";
    std::string Out = "unchanged";
    Check(!JA::LoopbackOrigin(std::string(EmbeddedNull, sizeof(EmbeddedNull) - 1), Out),
        "embedded NUL cannot truncate a candidate into an accepted origin");
    Check(Out == "unchanged", "embedded NUL refusal preserves the previous origin");
}

static void ExplicitDeduplicatedCreateRecovery()
{
    JA::SessionGuard S;
    Check(S.BeginExplicitCreateRecovery(0).Kind == JA::Work::None, "closed session cannot request create recovery");
    S.Open();
    Check(S.BeginExplicitCreateRecovery(0).Kind == JA::Work::None, "ordinary bootstrap has no uncertain create to recover");
    const auto Creation = S.BeginCreation(1);
    Check(S.Fail(Creation, 2, true), "initial creation transport failure is uncertain");
    Check(S.BeginExplicitCreateRecovery(-1).Kind == JA::Work::None, "invalid clock refuses manual create recovery");
    const auto Recovery = S.BeginExplicitCreateRecovery(3);
    Check(Recovery.Kind == JA::Work::Mutation && Recovery.Serial != Creation.Serial,
        "manual recovery has a new local ticket while caller retains the same wire request ID");
    Check(S.BeginCreation(3).Kind == JA::Work::None && S.BeginExplicitCreateRecovery(3).Kind == JA::Work::None,
        "manual create recovery remains one request in flight");
    RefuseCompletion(S, Creation, 3);
    Check(S.Tick(13) == JA::TimerEvent::MutationTimeout && S.HasUncertainOutcome() && !S.ReadRetryDue(1000),
        "failed manual recovery still never schedules an automatic create retry");
    const auto Retry = S.BeginExplicitCreateRecovery(14);
    Check(Retry.Kind == JA::Work::Mutation, "another manually requested deduplicated recovery may start");
    Check(S.Snapshot(Retry) && S.CanMutate() && !S.HasUncertainOutcome(),
        "current validated deduplicated create response restores authority");
    RefuseCompletion(S, Recovery, 14);
    Check(S.BeginExplicitCreateRecovery(15).Kind == JA::Work::None,
        "resolved create cannot enter the uncertain recovery path again");
}

// These are authored visible DTOs shaped from the pinned source contracts,
// not HTTP captures or Java game-rule oracles. JSON parsing and transport
// authentication remain separate native/service acceptance stages.
static JA::SudokuView SudokuFixture()
{
    JA::SudokuView V;
    V.GameId = "00000000-0000-4000-8000-000000000042";
    V.Owner = "fixture_player";
    V.Difficulty = 2;
    V.Lives = 3;
    V.Values[0] = 5; V.Givens[0] = true;
    V.Values[1] = 3; V.Givens[1] = true;
    V.PencilMasks[2] = (1u << 1) | (1u << 2) | (1u << 4);
    V.ElapsedSeconds = 21;
    V.MoveCount = 7;
    return V;
}

static void SudokuVisibleBoundsAndIntent()
{
    const JA::SudokuView Original = SudokuFixture();
    Check(Original.Values.size() == 81 && Original.Givens.size() == 81 && Original.PencilMasks.size() == 81,
        "typed Sudoku snapshot has exactly 81 visible cells");
    Check(JA::ValidSudoku(Original), "source-shaped Sudoku visible snapshot is accepted");
    Check(JA::CanSubmitSudoku(Original, "fixture_player", 0, 2, 4), "owner may submit a nongiven move intent");
    Check(!JA::CanSubmitSudoku(Original, "another_player", 0, 2, 4), "spectator identity cannot submit owned-play intent");
    Check(!JA::CanSubmitSudoku(Original, "player_1791849600000", 0, 2, 4),
        "synthetic cell timestamp identity is not board ownership");
    Check(!JA::CanSubmitSudoku(Original, "fixture_player", 0, 0, 0)
        && !JA::CanSubmitSudoku(Original, "fixture_player", 0, 0, 5), "given clues cannot be erased or replaced locally");
    auto Filled = Original;
    Filled.Values[2] = 4;
    Check(JA::CanSubmitSudoku(Filled, "fixture_player", 0, 2, 0)
        && JA::CanSubmitSudoku(Filled, "fixture_player", 0, 2, 7),
        "filled nongivens remain erasable and replaceable despite source isEditable false");
    for (int Index = 0; Index < 81; ++Index)
    {
        auto Invalid = Original;
        Invalid.Values[static_cast<std::size_t>(Index)] = -1;
        Check(!JA::ValidSudoku(Invalid), "negative cell values are refused at every position");
        Invalid.Values[static_cast<std::size_t>(Index)] = 10;
        Check(!JA::ValidSudoku(Invalid), "values above nine are refused at every position");
        Invalid = Original;
        Invalid.PencilMasks[static_cast<std::size_t>(Index)] = 1u;
        Check(!JA::ValidSudoku(Invalid), "zero is not a pencil note");
        Invalid.PencilMasks[static_cast<std::size_t>(Index)] = 1u << 10;
        Check(!JA::ValidSudoku(Invalid), "pencil notes above nine are refused at every position");
    }
    auto Notes = Original;
    Notes.PencilMasks.fill(0x3fe);
    Check(JA::ValidSudoku(Notes), "all nine server pencil marks fit the visible note mask");
    for (const std::array<int, 3>& Intent : {std::array<int, 3>{-1, 0, 1}, {9, 0, 1}, {0, -1, 1},
        {0, 9, 1}, {0, 2, -1}, {0, 2, 10}, {std::numeric_limits<int>::max(), 2, 1}})
    {
        Check(!JA::CanSubmitSudoku(Original, "fixture_player", Intent[0], Intent[1], Intent[2]),
            "out-of-board or out-of-value intent is refused before indexing");
    }
    auto Ended = Original;
    Ended.Solved = true;
    Check(!JA::CanSubmitSudoku(Ended, "fixture_player", 0, 2, 4), "authoritative solved flag closes move submission");
    Ended.Solved = false; Ended.TimeUp = true;
    Check(!JA::CanSubmitSudoku(Ended, "fixture_player", 0, 2, 4), "authoritative expiry closes move submission");
    for (int BadField = 0; BadField < 10; ++BadField)
    {
        auto Invalid = Original;
        switch (BadField)
        {
        case 0: Invalid.GameId.clear(); break;
        case 1: Invalid.GameId.assign(257, 'x'); break;
        case 2: Invalid.Owner.clear(); break;
        case 3: Invalid.Owner.assign(129, 'x'); break;
        case 4: Invalid.Difficulty = 0; break;
        case 5: Invalid.Difficulty = 6; break;
        case 6: Invalid.Lives = -1; break;
        case 7: Invalid.ElapsedSeconds = -1; break;
        case 8: Invalid.SecondsLeft = -1; break;
        default: Invalid.TimeLimitSeconds = -1; break;
        }
        Check(!JA::ValidSudoku(Invalid), "malformed Sudoku identity or server metadata is refused");
        Check(!JA::CanSubmitSudoku(Invalid, "fixture_player", 0, 2, 4), "malformed snapshot never enables a move");
    }
    auto InvalidCount = Original;
    InvalidCount.HintCount = -1;
    Check(!JA::ValidSudoku(InvalidCount), "negative authoritative hint counter is refused");
    InvalidCount = Original; InvalidCount.MoveCount = -1;
    Check(!JA::ValidSudoku(InvalidCount), "negative authoritative move counter is refused");
    for (std::size_t Index = 0; Index < Original.Values.size(); ++Index)
    {
        auto EmptyGiven = Original;
        EmptyGiven.Values[Index] = 0; EmptyGiven.Givens[Index] = true;
        Check(!JA::ValidSudoku(EmptyGiven), "a source given clue cannot be empty at any position");
    }
    auto ContradictoryEnd = Original;
    ContradictoryEnd.Solved = true; ContradictoryEnd.TimeUp = true;
    Check(!JA::ValidSudoku(ContradictoryEnd), "simultaneous solved and expired state is refused");
    for (int Field = 0; Field < 7; ++Field)
    {
        auto Overflow = Original;
        switch (Field)
        {
        case 0: Overflow.Score = 2147483648LL; break;
        case 1: Overflow.Score = -2147483649LL; break;
        case 2: Overflow.HintCount = 2147483648LL; break;
        case 3: Overflow.MoveCount = 2147483648LL; break;
        case 4: Overflow.ElapsedSeconds = 9007199254740992LL; break;
        case 5: Overflow.SecondsLeft = 9007199254740992LL; break;
        default: Overflow.TimeLimitSeconds = 9007199254740992LL; break;
        }
        Check(!JA::ValidSudoku(Overflow), "out-of-range Java integer or exact JSON clock metadata is refused");
    }
    auto Variants = Original;
    Variants.ChaosMode = true; Variants.MirrorMode = true;
    Variants.TimeLimitSeconds = 600; Variants.SecondsLeft = 579; Variants.HintCount = 2;
    Check(JA::ValidSudoku(Variants) && Variants.Values == Original.Values,
        "variant and clock metadata are accepted without simulating local Java effects");
}

static JA::BlackjackView BlackjackFixture()
{
    JA::BlackjackView V;
    V.SessionId = "fixture_session_01";
    V.Revision = 3;
    V.Phase = "PLAYER";
    V.Bankroll = 975;
    V.ActiveHand = 0;
    V.Hands.push_back({{{"10", "CLUBS"}, {"6", "HEARTS"}}, 25, 16});
    V.DealerCards.push_back({"A", "SPADES"});
    V.HiddenDealerCards = 1;
    V.LegalActions = {"hit", "stand", "insurance"};
    return V;
}

static void BlackjackVisibleBoundsAndDeclaredLegality()
{
    const JA::BlackjackView Original = BlackjackFixture();
    Check(JA::ValidBlackjack(Original), "source-shaped visible Blackjack snapshot is accepted");
    Check(JA::CanSubmitBlackjack(Original, "hit") && !JA::CanSubmitBlackjack(Original, "split"),
        "Java-declared legal actions are used without recreating Blackjack rules");
    Check(!JA::CanSubmitBlackjack(Original, "cashOut") && !JA::KnownBlackjackAction("setBankroll"),
        "unknown financial and direct-balance actions are absent from protocol");
    const std::array<const char*, 13> Ranks{{"A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"}};
    const std::array<const char*, 4> Suits{{"CLUBS", "DIAMONDS", "HEARTS", "SPADES"}};
    for (const char* Rank : Ranks)
    {
        for (const char* Suit : Suits)
        {
            Check(JA::ValidCard({Rank, Suit}), "all 52 source rank/suit pairs are accepted");
        }
    }
    Check(!JA::ValidCard({"1", "CLUBS"}) && !JA::ValidCard({"10", "UNKNOWN"}), "unknown rank and suit literals are refused");
    for (int BadField = 0; BadField < 12; ++BadField)
    {
        auto Invalid = Original;
        switch (BadField)
        {
        case 0: Invalid.SessionId.clear(); break;
        case 1: Invalid.SessionId.assign(65, 'x'); break;
        case 2: Invalid.Revision = -1; break;
        case 3: Invalid.Bankroll = -1; break;
        case 4: Invalid.PendingBet = -1; break;
        case 5: Invalid.Phase = "UNKNOWN"; break;
        case 6: Invalid.ActiveHand = 1; break;
        case 7: Invalid.ActiveHand = -2; break;
        case 8: Invalid.HiddenDealerCards = 2; break;
        case 9: Invalid.HasDealerDerivedValues = true; break;
        case 10: Invalid.DealerCards.push_back({"K", "HEARTS"}); break;
        default: Invalid.LegalActions.push_back("unknown"); break;
        }
        Check(!JA::ValidBlackjack(Invalid), "malformed or hidden-information Blackjack projection is refused");
        Check(!JA::CanSubmitBlackjack(Invalid, "hit"), "malformed Blackjack projection disables commands");
    }
    auto EmptyUpcard = Original;
    EmptyUpcard.DealerCards.clear();
    Check(!JA::ValidBlackjack(EmptyUpcard), "hidden-hole snapshot must contain exactly its one visible upcard");
    for (const char* LivePhase : {"DEALING", "INSURANCE", "PLAYER"})
    {
        auto MislabelledHidden = Original;
        MislabelledHidden.Phase = LivePhase;
        if (MislabelledHidden.Phase != "PLAYER") MislabelledHidden.ActiveHand = -1;
        Check(JA::ValidBlackjack(MislabelledHidden), "live source phases accept one upcard and hidden hole marker");
        MislabelledHidden.HiddenDealerCards = 0;
        MislabelledHidden.DealerCards.push_back({"K", "HEARTS"});
        Check(!JA::ValidBlackjack(MislabelledHidden),
            "live phase rejects a second dealer card even when hidden count falsely says zero");
        MislabelledHidden.DealerCards.resize(1);
        MislabelledHidden.HasDealerDerivedValues = true;
        Check(!JA::ValidBlackjack(MislabelledHidden),
            "live phase rejects dealer totals even when hidden count falsely says zero");
        MislabelledHidden.HasDealerDerivedValues = false;
        Check(!JA::ValidBlackjack(MislabelledHidden), "live upcard projection requires its hidden hole marker");
    }
    auto EmptyDealing = Original;
    EmptyDealing.Phase = "DEALING"; EmptyDealing.ActiveHand = -1;
    EmptyDealing.DealerCards.clear(); EmptyDealing.HiddenDealerCards = 0;
    Check(JA::ValidBlackjack(EmptyDealing), "transient undealt source phase reveals no dealer information");
    for (const char* LivePhase : {"INSURANCE", "PLAYER"})
    {
        auto MissingDealer = EmptyDealing;
        MissingDealer.Phase = LivePhase;
        if (MissingDealer.Phase == "PLAYER") MissingDealer.ActiveHand = 0;
        Check(!JA::ValidBlackjack(MissingDealer), "play and insurance phases cannot omit the source upcard");
    }
    auto FourHands = Original;
    FourHands.Hands.resize(4, Original.Hands[0]);
    FourHands.ActiveHand = 3;
    Check(JA::ValidBlackjack(FourHands), "four source player hands and the last active index fit");
    FourHands.Hands.push_back(Original.Hands[0]);
    Check(!JA::ValidBlackjack(FourHands), "fifth player hand is refused");
    auto ManyCards = Original;
    ManyCards.Hands[0].Cards.resize(21, {"A", "CLUBS"});
    Check(JA::ValidBlackjack(ManyCards), "bounded long player hand is accepted");
    ManyCards.Hands[0].Cards.push_back({"A", "CLUBS"});
    Check(!JA::ValidBlackjack(ManyCards), "oversized player hand is refused");
    auto Revealed = Original;
    Revealed.HiddenDealerCards = 0; Revealed.HasDealerDerivedValues = true;
    Revealed.Phase = "BETTING"; Revealed.ActiveHand = -1;
    Revealed.DealerCards.resize(21, {"A", "CLUBS"});
    Check(JA::ValidBlackjack(Revealed), "post-round fully visible bounded dealer state is accepted");
    Revealed.DealerCards.push_back({"A", "CLUBS"});
    Check(!JA::ValidBlackjack(Revealed), "oversized revealed dealer hand is refused");
    auto Betting = Original;
    Betting.Phase = "BETTING"; Betting.ActiveHand = -1;
    Betting.HiddenDealerCards = 0; Betting.DealerCards.clear();
    Betting.LegalActions = {"bet"}; Betting.LegalBetAmounts = {1, 5, 25, 100, 500};
    Check(JA::ValidBlackjack(Betting), "source chip menu projection is accepted");
    for (int Amount : Betting.LegalBetAmounts)
    {
        Check(JA::CanSubmitBlackjack(Betting, "bet", Amount), "only Java-declared chip amounts are submitted");
    }
    Check(!JA::CanSubmitBlackjack(Betting, "bet", 0) && !JA::CanSubmitBlackjack(Betting, "bet", 2),
        "undeclared zero and arbitrary credit amounts are refused");
    Betting.LegalBetAmounts = {5};
    Check(JA::CanSubmitBlackjack(Betting, "bet", 5) && !JA::CanSubmitBlackjack(Betting, "bet", 500),
        "current server bankroll-dependent legal chip subset is respected");
    Betting.Closed = true;
    Check(!JA::CanSubmitBlackjack(Betting, "bet", 5), "closed session never re-enables a declared action");
    for (int Field = 0; Field < 4; ++Field)
    {
        auto Overflow = Original;
        switch (Field)
        {
        case 0: Overflow.Revision = 9007199254740992LL; break;
        case 1: Overflow.Bankroll = 2147483648LL; break;
        case 2: Overflow.PendingBet = 2147483648LL; break;
        default: Overflow.Hands[0].Bet = 2147483648LL; break;
        }
        Check(!JA::ValidBlackjack(Overflow), "out-of-range exact revision or source credit integer is refused");
    }
    auto LastRevision = Original;
    LastRevision.Revision = 9007199254740991LL;
    Check(JA::ValidBlackjack(LastRevision) && !JA::CanSubmitBlackjack(LastRevision, "hit"),
        "last exact JSON revision can display but cannot request an inexact next revision");
}

int main()
{
    ExistingTrace();
    TicketIdentityAndCancellation();
    NoImplicitRequestQueue();
    InvalidClockPreservesState();
    SafeReadRetryBudget();
    AmbiguousMutationRequiresReconciliation();
    ReopenCallbackLifecycles();
    FreshReadReconciliationTickets();
    CreationBootstrapIsNotGameplayAuthority();
    PayloadBoundaries();
    EndpointBoundaries();
    ExplicitDeduplicatedCreateRecovery();
    SudokuVisibleBoundsAndIntent();
    BlackjackVisibleBoundsAndDeclaredLegality();
    std::cout << "Java arcade transport policy: " << Checks << " checks passed\n";
}
