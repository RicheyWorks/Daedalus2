#include "../DaedalusLink/Source/DaedalusLink/Public/DaedalusMailRouteCore.h"
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <iostream>
#include <limits>
#include <vector>

namespace
{
using namespace daedalus::parcels;
int ChecksTotal = 0;
int Failures = 0;
void Check(bool value, const char* label)
{
    ++ChecksTotal;
    if (!value) { ++Failures; std::cerr << "FAIL " << label << '\n'; }
}
bool SameDay(const Day& a, const Day& b)
{
    if (a.Seed != b.Seed || a.ParCubes != b.ParCubes || a.ParSeconds != b.ParSeconds ||
        a.ParOrder != b.ParOrder || a.Letters.size() != b.Letters.size()) return false;
    for (std::size_t i = 0; i < a.Letters.size(); ++i)
    {
        const Letter& x = a.Letters[i]; const Letter& y = b.Letters[i];
        if (x.Id != y.Id || x.Plot != y.Plot || !(x.Mailbox == y.Mailbox) ||
            x.Type != y.Type || x.Deadline != y.Deadline) return false;
    }
    return true;
}
bool SameReceipt(const Receipt& a, const Receipt& b)
{
    return a.Delivered == b.Delivered && a.Late == b.Late && a.Undelivered == b.Undelivered &&
           a.GhostReturned == b.GhostReturned && a.Stamps == b.Stamps && a.Seconds == b.Seconds &&
           a.ParSeconds == b.ParSeconds && a.Award == b.Award;
}
int Tour(const Day& day, const std::vector<int>& order)
{
    Stop at = Depot(); int total = 0;
    for (const int i : order)
    {
        const Stop next = day.Letters[static_cast<std::size_t>(i)].Mailbox;
        total += StreetCubes(at, next); at = next;
    }
    return total + StreetCubes(at, Depot());
}
bool FindDay(int wanted, Day& out)
{
    // Deterministic fixture selection, bounded to sixty-four tiny generated routes.
    for (std::int64_t seed = 0; seed < 64; ++seed)
    {
        Day day; if (!MakeDay(seed, day)) return false;
        bool match = wanted == 2 ? day.Letters.size() == 11 : wanted == 3 ? day.Letters.size() <= 7 : false;
        for (const Letter& letter : day.Letters)
            if ((wanted == 0 && letter.Type == Kind::Express) || (wanted == 1 && letter.Type == Kind::GhostPickup)) match = true;
        if (match) { out = std::move(day); return true; }
    }
    return false;
}
bool Walk(const Day& day, int slowdown, Receipt& out, bool omitGhost = false)
{
    Session session; if (!session.Start(day)) return false;
    Stop at = Depot(); int walked = 0;
    for (const int i : day.ParOrder)
    {
        const Letter& letter = day.Letters[static_cast<std::size_t>(i)];
        walked += StreetCubes(at, letter.Mailbox); at = letter.Mailbox;
        if (omitGhost && letter.Type == Kind::GhostPickup) continue;
        const int elapsed = ((walked + 4) / 5) * slowdown / 100;
        const Outcome expected = letter.Type == Kind::GhostPickup ? Outcome::PickedUp :
                                 (letter.Type == Kind::Express && elapsed > letter.Deadline ? Outcome::Late : Outcome::OnTime);
        if (session.Deliver(letter.Id, letter.Mailbox.At(), elapsed) != expected ||
            !session.IsDone(letter.Id) || session.Result(letter.Id) != expected) return false;
    }
    return session.Finish(Depot().At(), day.ParSeconds * slowdown / 100, out);
}
}

int main()
{
    Check(Depot().At() == Coord{48, 1, -74}, "depot is on the authored plaza and gate-zero line");
    Stop first, last;
    Check(Mailbox(0, first) && first == Stop{0, -136} && Mailbox(63, last) && last == Stop{4, -12},
          "negative district offsets and mailbox centre rounding");
    Stop untouched{3, 123};
    Check(!Mailbox(-1, untouched) && !Mailbox(64, untouched) && !Mailbox(27, untouched) &&
          !Mailbox(28, untouched) && !Mailbox(35, untouched) && !Mailbox(36, untouched) && untouched == Stop{3, 123},
          "unknown plots and plaza refuse without changing output");
    int boxes = 0; bool streetBoxes = true;
    for (int plot = 0; plot < 64; ++plot)
    {
        Stop box;
        if (Mailbox(plot, box)) { ++boxes; streetBoxes = streetBoxes && !Trespass(box.X(), box.Z); }
    }
    Check(boxes == 60 && streetBoxes, "all sixty claimable plots have street mailboxes");
    Check(Trespass(-22, -144) && Trespass(-7, -129) && !Trespass(-24, -136) &&
          !Trespass(48, -74) && !Trespass(30, -92), "plot boundaries exclude streets and four plaza plots");
    const auto tiedPath = Waypoints(Stop{0, -136}, Stop{1, -64});
    Check(tiedPath == std::vector<Coord>{{-24, 1, -136}, {-24, 1, -110}, {12, 1, -110}, {12, 1, -64}},
          "equally short crossings choose Java's earliest road");
    Check(StreetCubes(Stop{0, -136}, Stop{1, -64}) == 108 && StreetCubes(first, first) == 0,
          "street distance includes the road detour");

    const std::vector<Stop> stops{Depot(), first, last, Stop{1, -120}, Stop{2, -100}, Stop{3, -28}};
    bool geometry = true;
    for (const Stop a : stops) for (const Stop b : stops)
    {
        const int distance = StreetCubes(a, b);
        geometry = geometry && distance == StreetCubes(b, a);
        const auto path = Waypoints(a, b);
        int length = 0;
        for (std::size_t i = 1; i < path.size(); ++i)
        {
            const Coord p = path[i - 1], q = path[i];
            const int dx = q.X - p.X, dz = q.Z - p.Z;
            geometry = geometry && (dx == 0 || dz == 0);
            const int steps = std::abs(dx) + std::abs(dz);
            length += steps;
            for (int s = 0; s <= steps; ++s)
                geometry = geometry && !Trespass(p.X + (dx > 0 ? s : dx < 0 ? -s : 0),
                                                 p.Z + (dz > 0 ? s : dz < 0 ? -s : 0));
        }
        geometry = geometry && length == distance;
        for (const Stop c : stops) geometry = geometry && distance <= StreetCubes(a, c) + StreetCubes(c, b);
    }
    Check(geometry, "bounded street paths are metric and never enter plots");
    Check(StreetCubes(Stop{-1, 0}, first) == -1 && Waypoints(first, Stop{5, 0}).empty() &&
          StreetCubes(Stop{0, (std::numeric_limits<int>::min)()}, Stop{0, (std::numeric_limits<int>::max)()}) == -1,
          "invalid roads and unrepresentable distance refuse safely");

    Day day, repeat, other;
    Check(MakeDay(4, day) && MakeDay(4, repeat) && SameDay(day, repeat), "seeded day repeatability");
    Check(MakeDay(5, other) && !SameDay(day, other), "different seeded route");
    bool generated = true, allGold = true;
    for (std::int64_t seed = 0; seed < 8; ++seed)
    {
        Day route; generated = generated && MakeDay(seed, route);
        bool plots[64] = {}; int ghosts = 0, express = 0;
        for (std::size_t i = 0; i < route.Letters.size(); ++i)
        {
            const Letter& letter = route.Letters[i]; Stop box;
            const bool validPlot = Mailbox(letter.Plot, box);
            if (!validPlot) { generated = false; continue; }
            generated = generated && validPlot && letter.Id == static_cast<int>(i) && letter.Mailbox == box && !plots[letter.Plot];
            plots[letter.Plot] = true;
            if (letter.Type == Kind::GhostPickup) ++ghosts;
            if (letter.Type == Kind::Express) ++express;
            generated = generated && ((letter.Deadline > 0) == (letter.Type == Kind::Express));
        }
        const int normal = static_cast<int>(route.Letters.size()) - ghosts;
        generated = generated && normal >= 6 && normal <= 10 && ghosts <= 1 &&
                    Tour(route, route.ParOrder) == route.ParCubes && route.ParSeconds == (route.ParCubes + 4) / 5;
        Receipt receipt;
        allGold = allGold && Walk(route, 100, receipt) && receipt.Delivered == normal && receipt.Late == 0 &&
                  receipt.Undelivered == 0 && receipt.GhostReturned == (ghosts != 0) &&
                  receipt.Stamps == normal + express + ghosts * 2 && receipt.Award == Medal::Gold;
    }
    Check(generated, "generated letters are distinct real plots with exact deadlines and tour totals");
    Check(allGold, "actual par tours deliver on time for gold with exact receipt facts");
    Day eleven;
    Check(FindDay(2, eleven) && eleven.Letters.size() == 11 && eleven.ParOrder.size() == 11,
          "ten ordinary letters plus Ghost support eleven solver stops");
    Day small;
    bool optimal = FindDay(3, small);
    if (optimal)
    {
        std::vector<int> order;
        for (std::size_t i = 0; i < small.Letters.size(); ++i) order.push_back(static_cast<int>(i));
        int best = (std::numeric_limits<int>::max)();
        do { best = (std::min)(best, Tour(small, order)); } while (std::next_permutation(order.begin(), order.end()));
        optimal = best == small.ParCubes;
    }
    Check(optimal, "Held-Karp par equals exhaustive optimum on one bounded small route");
    Day extreme;
    Check(MakeDay(-1, extreme) && MakeDay((std::numeric_limits<std::int64_t>::min)(), extreme) &&
          MakeDay((std::numeric_limits<std::int64_t>::max)(), extreme), "full signed Java seed domain");

    Session session;
    Receipt marker; marker.Stamps = 777;
    Check(!session.Active() && !session.IsDone(0) && session.Result(0) == Outcome::UnknownLetter &&
          session.Deliver(0, Depot().At(), 0) == Outcome::UnknownLetter && !session.Finish(Depot().At(), 0, marker) && marker.Stamps == 777,
          "inactive session cannot deliver or produce a receipt");
    Check(session.Start(day) && session.Active() && SameDay(session.CurrentDay(), day), "start freezes a copied host day");
    int id = 0;
    while (day.Letters[static_cast<std::size_t>(id)].Type == Kind::GhostPickup) ++id;
    const Letter letter = day.Letters[static_cast<std::size_t>(id)];
    const Coord box = letter.Mailbox.At();
    Check(session.Deliver(-1, box, 0) == Outcome::UnknownLetter && session.Deliver(99, box, 0) == Outcome::UnknownLetter &&
          session.Deliver(id, box, -1) == Outcome::UnknownLetter && !session.IsDone(id), "invalid IDs or negative elapsed do not consume a letter");
    Check(session.Deliver(id, Coord{-22, 1, -136}, 0) == Outcome::Trespass && !session.IsDone(id),
          "delivery inside any plot refuses before reach and irrespective of deeds");
    Check(session.Deliver(id, Coord{box.X + 1, box.Y, box.Z + 2}, 0) == Outcome::TooFar && !session.IsDone(id),
          "horizontal Euclidean reach is not a square radius");
    Check(session.Deliver(id, Coord{box.X, (std::numeric_limits<int>::max)(), box.Z + 2}, 0) == Outcome::OnTime && session.IsDone(id),
          "exact reach-two delivery ignores height as Java does");
    Check(session.Deliver(id, box, 999) == Outcome::AlreadyDone && session.Result(id) == Outcome::OnTime,
          "repeated delivery leaves first outcome unchanged");
    const Receipt previous = marker;
    Check(!session.Finish(Coord{Depot().X(), 1, Depot().Z + 3}, 10, marker) && SameReceipt(marker, previous) &&
          !session.Finish(Depot().At(), -1, marker) && SameReceipt(marker, previous), "refused finish leaves receipt output unchanged");
    Receipt partial;
    Check(session.Finish(Depot().At(), 10, partial) && partial.Delivered == 1 && partial.Undelivered > 0 && partial.Award == Medal::None,
          "partial return reports undelivered letters without a medal");

    bool atomic = true;
    for (int variant = 0; variant < 7; ++variant)
    {
        Day bad = day;
        switch (variant)
        {
        case 0: bad.ParOrder[0] = bad.ParOrder[1]; break;
        case 1: bad.Letters[0].Plot = 27; break;
        case 2: bad.Letters[0].Mailbox.Road = 5; break;
        case 3: bad.Letters[0].Type = static_cast<Kind>(99); break;
        case 4: bad.Letters[0].Deadline = -1; break;
        case 5: ++bad.ParSeconds; break;
        default: bad.Letters.resize(12); break;
        }
        Receipt after;
        const bool rejected = !session.Start(bad);
        atomic = atomic && rejected && session.Active() && session.IsDone(id) &&
                 SameDay(session.CurrentDay(), day) && session.Finish(Depot().At(), 10, after) && SameReceipt(after, partial);
    }
    Check(atomic, "malformed host days refuse without replacing live progress");
    Day supplied = day; supplied.Seed ^= 123;
    Session notAuthority;
    Check(notAuthority.Start(supplied), "structural day validation does not claim canonical seed authentication");

    Day expressDay;
    bool boundary = FindDay(0, expressDay);
    if (boundary)
    {
        const auto found = std::find_if(expressDay.Letters.begin(), expressDay.Letters.end(), [](const Letter& x) { return x.Type == Kind::Express; });
        Session onTime, late;
        boundary = onTime.Start(expressDay) && late.Start(expressDay) &&
                   onTime.Deliver(found->Id, found->Mailbox.At(), found->Deadline) == Outcome::OnTime &&
                   late.Deliver(found->Id, found->Mailbox.At(), found->Deadline + 1) == Outcome::Late;
    }
    Check(boundary, "Express is on time at exact deadline and late one second after");
    Receipt slow;
    Check(Walk(expressDay, 300, slow) && slow.Late > 0 && slow.Award == Medal::None, "slow actual route loses Express bonus and medal");
    Check(GradeMedal(110, 100) == Medal::Gold && GradeMedal(111, 100) == Medal::Silver &&
          GradeMedal(135, 100) == Medal::Silver && GradeMedal(136, 100) == Medal::Bronze &&
          GradeMedal(175, 100) == Medal::Bronze && GradeMedal(176, 100) == Medal::None, "all authored medal boundaries");
    Check(GradeMedal(-1, 100) == Medal::None && GradeMedal(1, 0) == Medal::None &&
          GradeMedal((std::numeric_limits<int>::max)(), (std::numeric_limits<int>::max)()) == Medal::Gold,
          "medal invalid inputs and widened multiplication");

    Day ghostDay;
    bool ghost = FindDay(1, ghostDay);
    Receipt withoutGhost;
    ghost = ghost && Walk(ghostDay, 100, withoutGhost, true) && !withoutGhost.GhostReturned &&
            withoutGhost.Undelivered == 0 && withoutGhost.Award == Medal::Gold;
    Check(ghost, "uncollected Ghost is excluded from ordinary delivery and medal count");
    Session pickup; pickup.Start(ghostDay);
    const auto ghostLetter = std::find_if(ghostDay.Letters.begin(), ghostDay.Letters.end(), [](const Letter& x) { return x.Type == Kind::GhostPickup; });
    bool picked = ghostLetter != ghostDay.Letters.end();
    if (picked) picked = pickup.Deliver(ghostLetter->Id, ghostLetter->Mailbox.At(), 0) == Outcome::PickedUp && pickup.HoldingGhost();
    Receipt returned, repeated;
    Check(picked && pickup.Finish(Depot().At(), 0, returned) && returned.GhostReturned && returned.Stamps == 2 &&
          pickup.Finish(Depot().At(), 0, repeated) && SameReceipt(returned, repeated) && pickup.HoldingGhost() && pickup.Active(),
          "Ghost receipt facts are repeatable and do not consume state or settle awards");

    std::cout << (Failures ? "MAIL_ROUTE_CORE_FAIL " : "MAIL_ROUTE_CORE_PASS ")
              << ChecksTotal - Failures << '/' << ChecksTotal << " checks\n";
    return Failures ? 1 : 0;
}
