// SPDX-License-Identifier: MIT
#pragma once
#include "DaedalusTemperForgeCore.h"
#include <algorithm>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <limits>
#include <utility>
#include <vector>

// PAR01 port of MailRoute.java and DistrictOps street geometry. The caller owns
// courier identity, position, elapsed time and any settlement; receipts award nothing.
namespace daedalus::parcels
{
inline constexpr int Pace = 5, MinLetters = 6, MaxLetters = 10, Roads = 5;
inline constexpr double Reach = 2.0;

struct Coord { int X = 0, Y = 0, Z = 0; };
inline bool operator==(const Coord& a, const Coord& b) { return a.X == b.X && a.Y == b.Y && a.Z == b.Z; }
struct Stop
{
    int Road = 0, Z = 0;
    int X() const { return Road >= 0 && Road < Roads ? -26 + Road * 36 + 2 : 0; }
    Coord At() const { return {X(), 1, Z}; }
};
inline bool operator==(const Stop& a, const Stop& b) { return a.Road == b.Road && a.Z == b.Z; }
enum class Kind { Standard, Express, GhostPickup };
enum class Outcome { OnTime, Late, PickedUp, UnknownLetter, AlreadyDone, TooFar, Trespass, NotHolding };
enum class Medal { Gold, Silver, Bronze, None };
struct Letter
{
    int Id = 0, Plot = 0;
    Stop Mailbox;
    Kind Type = Kind::Standard;
    int Deadline = 0;
};
struct Day
{
    std::int64_t Seed = 0;
    std::vector<Letter> Letters;
    std::vector<int> ParOrder;
    int ParCubes = 0, ParSeconds = 0;
};
struct Receipt
{
    int Delivered = 0, Late = 0, Undelivered = 0;
    bool GhostReturned = false;
    int Stamps = 0, Seconds = 0, ParSeconds = 0;
    Medal Award = Medal::None;
};

namespace Detail
{
inline bool IsPlot(int n)
{
    return n >= 0 && n < 64 && !((n / 8 == 3 || n / 8 == 4) && (n % 8 == 3 || n % 8 == 4));
}
inline int Offset(int i) { return 4 + (i / 2) * 36 + (i % 2) * 16; }
inline int RoadZ(int road) { return -148 + road * 36 + 2; }
inline bool ValidStop(Stop stop) { return stop.Road >= 0 && stop.Road < Roads; }
inline std::int64_t Distance(int a, int b)
{
    const std::int64_t delta = static_cast<std::int64_t>(a) - b;
    return delta < 0 ? -delta : delta;
}
inline int Crossing(Stop a, Stop b)
{
    int best = 0;
    std::int64_t length = (std::numeric_limits<std::int64_t>::max)();
    for (int road = 0; road < Roads; ++road)
    {
        const std::int64_t candidate = Distance(a.Z, RoadZ(road)) + Distance(RoadZ(road), b.Z);
        if (candidate < length) { length = candidate; best = road; }
    }
    return best;
}
inline int Seconds(int cubes) { return static_cast<int>((static_cast<std::int64_t>(cubes) + Pace - 1) / Pace); }
}

inline Stop Depot() { return {Roads / 2, Detail::RoadZ(Roads / 2)}; }
inline bool Mailbox(int plot, Stop& out)
{
    if (!Detail::IsPlot(plot)) return false;
    const int column = plot % 8;
    out = {column / 2 + column % 2, -148 + Detail::Offset(plot / 8) + 8};
    return true;
}
inline bool Trespass(int x, int z)
{
    for (int plot = 0; plot < 64; ++plot)
    {
        if (!Detail::IsPlot(plot)) continue;
        const int left = -26 + Detail::Offset(plot % 8);
        const int top = -148 + Detail::Offset(plot / 8);
        if (x >= left && x <= left + 15 && z >= top && z <= top + 15) return true;
    }
    return false;
}
// Invalid stops or a distance outside the int result range return -1.
inline int StreetCubes(Stop a, Stop b)
{
    if (!Detail::ValidStop(a) || !Detail::ValidStop(b)) return -1;
    std::int64_t length = Detail::Distance(a.Z, b.Z);
    if (a.Road != b.Road)
    {
        const int z = Detail::RoadZ(Detail::Crossing(a, b));
        length = Detail::Distance(a.Z, z) + Detail::Distance(a.X(), b.X()) + Detail::Distance(z, b.Z);
    }
    return length <= (std::numeric_limits<int>::max)() ? static_cast<int>(length) : -1;
}
inline std::vector<Coord> Waypoints(Stop a, Stop b)
{
    if (StreetCubes(a, b) < 0) return {};
    std::vector<Coord> out{a.At()};
    if (a.Road != b.Road)
    {
        const int z = Detail::RoadZ(Detail::Crossing(a, b));
        out.push_back({a.X(), 1, z});
        out.push_back({b.X(), 1, z});
    }
    out.push_back(b.At());
    return out;
}
inline Medal GradeMedal(int seconds, int par)
{
    if (seconds < 0 || par <= 0) return Medal::None;
    if (static_cast<std::int64_t>(seconds) * 10 <= static_cast<std::int64_t>(par) * 11) return Medal::Gold;
    if (static_cast<std::int64_t>(seconds) * 20 <= static_cast<std::int64_t>(par) * 27) return Medal::Silver;
    if (static_cast<std::int64_t>(seconds) * 4 <= static_cast<std::int64_t>(par) * 7) return Medal::Bronze;
    return Medal::None;
}

namespace Detail
{
inline int Tour(const std::vector<Letter>& letters, const std::vector<int>& order)
{
    Stop at = Depot();
    int sum = 0;
    for (const int index : order)
    {
        if (index < 0 || static_cast<std::size_t>(index) >= letters.size()) return -1;
        const Stop next = letters[static_cast<std::size_t>(index)].Mailbox;
        const int leg = StreetCubes(at, next);
        if (leg < 0 || sum > (std::numeric_limits<int>::max)() - leg) return -1;
        sum += leg;
        at = next;
    }
    const int home = StreetCubes(at, Depot());
    return home >= 0 && sum <= (std::numeric_limits<int>::max)() - home ? sum + home : -1;
}
inline std::vector<int> Solve(const std::vector<Letter>& letters)
{
    const int n = static_cast<int>(letters.size());
    if (n < 1 || n > MaxLetters + 1) return {};
    const int masks = 1 << n, full = masks - 1;
    const int maximum = (std::numeric_limits<int>::max)();
    std::vector<int> cost(static_cast<std::size_t>(masks * n), maximum);
    std::vector<int> previous(cost.size(), -1);
    const auto index = [n](int mask, int last) { return static_cast<std::size_t>(mask * n + last); };
    for (int i = 0; i < n; ++i) cost[index(1 << i, i)] = StreetCubes(Depot(), letters[static_cast<std::size_t>(i)].Mailbox);
    // Keep Java's mask/last/next iteration and strict-less-than tie ordering.
    for (int mask = 1; mask <= full; ++mask)
        for (int last = 0; last < n; ++last)
        {
            const int current = cost[index(mask, last)];
            if (current == maximum || (mask & (1 << last)) == 0) continue;
            for (int next = 0; next < n; ++next)
            {
                if (mask & (1 << next)) continue;
                const int nextMask = mask | (1 << next);
                const int candidate = current + StreetCubes(letters[static_cast<std::size_t>(last)].Mailbox,
                                                            letters[static_cast<std::size_t>(next)].Mailbox);
                if (candidate < cost[index(nextMask, next)])
                { cost[index(nextMask, next)] = candidate; previous[index(nextMask, next)] = last; }
            }
        }
    int best = 0, bestCost = maximum;
    for (int last = 0; last < n; ++last)
    {
        const int candidate = cost[index(full, last)] + StreetCubes(letters[static_cast<std::size_t>(last)].Mailbox, Depot());
        if (candidate < bestCost) { bestCost = candidate; best = last; }
    }
    std::vector<int> order;
    int mask = full;
    for (int at = best; at >= 0;)
    {
        order.push_back(at);
        const int parent = previous[index(mask, at)];
        mask &= ~(1 << at);
        at = parent;
    }
    std::reverse(order.begin(), order.end());
    return order;
}
inline bool ValidDay(const Day& day)
{
    if (day.Letters.size() < static_cast<std::size_t>(MinLetters) ||
        day.Letters.size() > static_cast<std::size_t>(MaxLetters + 1) ||
        day.ParOrder.size() != day.Letters.size()) return false;
    bool plots[64] = {}, order[MaxLetters + 1] = {};
    int ghosts = 0;
    for (std::size_t i = 0; i < day.Letters.size(); ++i)
    {
        const Letter& letter = day.Letters[i];
        Stop expected;
        if (letter.Id != static_cast<int>(i) || !Mailbox(letter.Plot, expected) || plots[letter.Plot] ||
            !(letter.Mailbox == expected) || letter.Deadline < 0 ||
            (letter.Type != Kind::Standard && letter.Type != Kind::Express && letter.Type != Kind::GhostPickup)) return false;
        plots[letter.Plot] = true;
        if (letter.Type == Kind::GhostPickup) ++ghosts;
    }
    const std::size_t regular = day.Letters.size() - static_cast<std::size_t>(ghosts);
    if (ghosts > 1 || regular < static_cast<std::size_t>(MinLetters) || regular > static_cast<std::size_t>(MaxLetters)) return false;
    for (const int i : day.ParOrder)
    {
        if (i < 0 || static_cast<std::size_t>(i) >= day.Letters.size() || order[i]) return false;
        order[i] = true;
    }
    return day.ParCubes > 0 && day.ParCubes == Tour(day.Letters, day.ParOrder) &&
           day.ParSeconds == Seconds(day.ParCubes);
}
inline bool WithinReach(Coord a, Coord b)
{
    const double dx = static_cast<double>(a.X) - b.X, dz = static_cast<double>(a.Z) - b.Z;
    return dx * dx + dz * dz <= Reach * Reach;
}
}

inline bool MakeDay(std::int64_t seed, Day& out)
{
    forge::SplitRng rng(seed ^ 0x9A501LL);
    const int count = MinLetters + rng.NextInt(MaxLetters - MinLetters + 1);
    const bool ghost = rng.NextInt() < 0;
    bool taken[64] = {};
    std::vector<int> plots;
    while (static_cast<int>(plots.size()) < count + (ghost ? 1 : 0))
    {
        const int plot = rng.NextInt(64);
        if (Detail::IsPlot(plot) && !taken[plot]) { taken[plot] = true; plots.push_back(plot); }
    }
    Day candidate;
    candidate.Seed = seed;
    for (std::size_t i = 0; i < plots.size(); ++i)
    {
        Stop box;
        Mailbox(plots[i], box);
        const Kind kind = ghost && i + 1 == plots.size() ? Kind::GhostPickup :
                          (rng.NextInt(4) == 0 ? Kind::Express : Kind::Standard);
        candidate.Letters.push_back({static_cast<int>(i), plots[i], box, kind, 0});
    }
    candidate.ParOrder = Detail::Solve(candidate.Letters);
    candidate.ParCubes = Detail::Tour(candidate.Letters, candidate.ParOrder);
    candidate.ParSeconds = Detail::Seconds(candidate.ParCubes);
    Stop at = Depot();
    int walked = 0;
    for (const int i : candidate.ParOrder)
    {
        Letter& letter = candidate.Letters[static_cast<std::size_t>(i)];
        walked += StreetCubes(at, letter.Mailbox);
        at = letter.Mailbox;
        if (letter.Type == Kind::Express) letter.Deadline = Detail::Seconds(walked) * 5 / 4 + 10;
    }
    if (!Detail::ValidDay(candidate)) return false;
    out = std::move(candidate);
    return true;
}

class Session
{
public:
    bool Start(const Day& day)
    {
        if (!Detail::ValidDay(day)) return false;
        Day candidate = day;
        std::vector<Outcome> done(day.Letters.size(), Outcome::UnknownLetter);
        Current = std::move(candidate);
        Done = std::move(done);
        Ghost = false;
        Started = true;
        return true;
    }
    Outcome Deliver(int id, Coord courier, int elapsed)
    {
        if (!Started || elapsed < 0 || id < 0 || static_cast<std::size_t>(id) >= Done.size()) return Outcome::UnknownLetter;
        const std::size_t i = static_cast<std::size_t>(id);
        if (Done[i] != Outcome::UnknownLetter) return Outcome::AlreadyDone;
        if (Trespass(courier.X, courier.Z)) return Outcome::Trespass;
        const Letter& letter = Current.Letters[i];
        if (!Detail::WithinReach(courier, letter.Mailbox.At())) return Outcome::TooFar;
        const Outcome result = letter.Type == Kind::GhostPickup ? Outcome::PickedUp :
                               (letter.Type == Kind::Express && elapsed > letter.Deadline ? Outcome::Late : Outcome::OnTime);
        Done[i] = result;
        if (result == Outcome::PickedUp) Ghost = true;
        return result;
    }
    bool Finish(Coord courier, int elapsed, Receipt& out) const
    {
        if (!Started || elapsed < 0 || !Detail::WithinReach(courier, Depot().At())) return false;
        Receipt receipt;
        receipt.Seconds = elapsed;
        receipt.ParSeconds = Current.ParSeconds;
        receipt.GhostReturned = Ghost;
        for (std::size_t i = 0; i < Done.size(); ++i)
        {
            const Letter& letter = Current.Letters[i];
            if (letter.Type == Kind::GhostPickup) continue;
            if (Done[i] == Outcome::UnknownLetter) ++receipt.Undelivered;
            else
            {
                ++receipt.Delivered; ++receipt.Stamps;
                if (Done[i] == Outcome::Late) ++receipt.Late;
                else if (letter.Type == Kind::Express) ++receipt.Stamps;
            }
        }
        if (Ghost) receipt.Stamps += 2;
        receipt.Award = receipt.Undelivered > 0 ? Medal::None : GradeMedal(elapsed, Current.ParSeconds);
        out = receipt;
        return true;
    }
    bool HoldingGhost() const { return Started && Ghost; }
    const Day& CurrentDay() const { return Current; }
    bool IsDone(int id) const
    {
        return Started && id >= 0 && static_cast<std::size_t>(id) < Done.size() && Done[static_cast<std::size_t>(id)] != Outcome::UnknownLetter;
    }
    Outcome Result(int id) const { return IsDone(id) ? Done[static_cast<std::size_t>(id)] : Outcome::UnknownLetter; }
    bool Active() const { return Started; }

private:
    Day Current;
    std::vector<Outcome> Done;
    bool Ghost = false, Started = false;
};
}
