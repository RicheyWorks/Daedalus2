// SPDX-License-Identifier: MIT
#pragma once

#include "DaedalusSimulationWire.h"
#include <algorithm>
#include <array>
#include <atomic>
#include <cmath>
#include <cstdint>
#include <limits>
#include <mutex>
#include <utility>

namespace daedalus::simulation {

enum class Intake { Accepted, Duplicate, Stale, Conflict, Invalid, WrongSession, Full, Busy };
enum class Intent { Stop, Rest, Work, RequestWater };

// One owner (game/server thread) calls Begin, Pump, Fresh and Current. Any producer may TryPush.
// A producer cannot block a frame: both mailbox operations use try_lock, with at most four inputs per Pump.
class Mailbox {
public:
    static constexpr std::size_t Capacity = 4;
    static constexpr double LeaseSeconds = 5.0;

    std::uint64_t Begin(std::string World, std::string Npc) {
        const auto Previous = Epoch.load();
        if (Previous == std::numeric_limits<std::uint64_t>::max()) return 0;
        WorldId = std::move(World); NpcId = std::move(Npc);
        HasCurrent = false; Conflict = false; LastReceived = -1.0;
        // Explicit binding reset only; network retries keep this epoch and the confirmed revision unchanged.
        Epoch.store(Previous + 1);
        return Previous + 1;
    }

    Intake TryPush(std::uint64_t Session, View Value, double ReceivedAt) {
        if (Session == 0 || Session != Epoch.load()) return Intake::WrongSession;
        if (!std::isfinite(ReceivedAt) || ReceivedAt < 0.0 || !ValidateView(Value)) return Intake::Invalid;
        std::unique_lock<std::mutex> Lock(Mutex, std::try_to_lock);
        if (!Lock.owns_lock()) return Intake::Busy;
        if (Session != Epoch.load()) return Intake::WrongSession;
        if (Count == Capacity) return Intake::Full;
        Queue[(Head + Count) % Capacity] = Entry{Session, std::move(Value), ReceivedAt};
        ++Count;
        return Intake::Accepted;
    }

    Intake Pump(double Now) {
        if (!std::isfinite(Now) || Now < 0.0) return Intake::Invalid;
        std::unique_lock<std::mutex> Lock(Mutex, std::try_to_lock);
        if (!Lock.owns_lock()) return Intake::Busy;
        Intake Result = Intake::Stale;
        for (std::size_t N = Count; N > 0; --N) {
            Entry E = std::move(Queue[Head]);
            Head = (Head + 1) % Capacity; --Count;
            if (E.Session != Epoch.load()) { Result = Intake::WrongSession; continue; }
            if (E.Value.WorldId != WorldId || E.Value.NpcId != NpcId) { Result = Intake::Invalid; continue; }
            if (E.At > Now || Now - E.At >= LeaseSeconds) { Result = Intake::Stale; continue; }
            if (HasCurrent && E.Value.Revision < Confirmed.Revision) { Result = Intake::Stale; continue; }
            if (HasCurrent && E.Value.Revision == Confirmed.Revision) {
                if (E.Value.StateHash != Confirmed.StateHash) {
                    Conflict = true; Result = Intake::Conflict; continue;
                }
                // A fresh GET of an unchanged state is a valid liveness confirmation. No effects replay.
                LastReceived = std::max(LastReceived, E.At);
                Result = Intake::Duplicate; continue;
            }
            if (HasCurrent && (E.Value.Tick < Confirmed.Tick || E.Value.EventSequence < Confirmed.EventSequence)) {
                Conflict = true; Result = Intake::Conflict; continue;
            }
            Confirmed = std::move(E.Value);
            LastReceived = E.At; HasCurrent = true;
            // Conflict stays latched until an explicit rebind/reconciliation, never auto-trust a later packet.
            Result = Intake::Accepted;
        }
        return Result;
    }

    bool Fresh(double Now) const {
        return HasCurrent && !Conflict && std::isfinite(Now) && Now >= LastReceived
            && Now - LastReceived < LeaseSeconds;
    }
    Intent Desired(double Now) const {
        if (!Fresh(Now)) return Intent::Stop;
        if (Confirmed.Task == "REST") return Intent::Rest;
        if (Confirmed.Task == "WORK") return Intent::Work;
        return Intent::RequestWater;
    }
    const View* Current() const { return HasCurrent ? &Confirmed : nullptr; }
    bool NeedsReconcile() const { return Conflict; }

private:
    struct Entry { std::uint64_t Session = 0; View Value; double At = 0; };
    std::array<Entry, Capacity> Queue;
    std::mutex Mutex;
    std::atomic<std::uint64_t> Epoch{0};
    std::size_t Head = 0, Count = 0;
    std::string WorldId, NpcId;
    View Confirmed;
    double LastReceived = -1.0;
    bool HasCurrent = false, Conflict = false;
};

struct Point { double X = 0, Y = 0, Z = 0; };
inline bool Finite(Point P) { return std::isfinite(P.X) && std::isfinite(P.Y) && std::isfinite(P.Z); }

// The Java task selects a locally configured marker, never a remote teleport or a persistent effect.
// Unreal still validates ground and sweeps the returned movement against local collision.
inline Point Step(Point At, Point Goal, double Speed, double Dt, double Radius = 50.0) {
    if (!Finite(At) || !Finite(Goal) || !std::isfinite(Speed) || !std::isfinite(Dt)
        || !std::isfinite(Radius) || Speed <= 0 || Dt <= 0 || Radius < 0) return {};
    const double X = Goal.X - At.X, Y = Goal.Y - At.Y;
    const double Distance = std::hypot(X, Y);
    if (!std::isfinite(Distance) || Distance <= Radius) return {};
    const double Move = std::min(Distance - Radius, std::min(Speed, 300.0) * std::min(Dt, 0.05));
    return {X / Distance * Move, Y / Distance * Move, 0.0};
}

} // namespace daedalus::simulation
