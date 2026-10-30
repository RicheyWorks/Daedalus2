// SPDX-License-Identifier: MIT
//
// Standalone test for hofstadter_hammers.h against golden vectors generated from the Java
// HofstadterHammers (hofstadter_hammers_golden.txt), plus property, edge and compile-time checks.
// Build: g++ -std=c++17 -Wall -Wextra -Werror hofstadter_hammers_test.cpp -o t && ./t hofstadter_hammers_golden.txt
#include "hofstadter_hammers.h"

#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <random>
#include <sstream>
#include <string>
#include <vector>

namespace hh = daedalus::forge::hofstadter;

static int g_checks = 0;
static int g_failures = 0;

static void Check(bool ok, const std::string& what) {
    ++g_checks;
    if (!ok) {
        ++g_failures;
        if (g_failures <= 20) {
            std::printf("FAIL: %s\n", what.c_str());
        }
    }
}

constexpr std::int32_t CompileTimeStrike(hh::Hammer h, std::int32_t n) {
    std::int32_t buf[32] = {};
    std::int32_t v = -1;
    return hh::Strike(h, n, buf, 32, &v) == hh::Status::Ok ? v : -1;
}

static_assert(CompileTimeStrike(hh::Hammer::Q, 10) == 6, "Q(10)");
static_assert(CompileTimeStrike(hh::Hammer::Conway, 9) == 5, "a(9)");
static_assert(CompileTimeStrike(hh::Hammer::Q, 0) == -1, "Q(0) rejected");

// Iteration 7: compile-time anchors to OEIS A005185 (Q) and A004001 (Hofstadter-Conway), independent of
// the Java fixture, so a broken recurrence fails the build before any test runs.
constexpr std::int32_t kOeisQ[31] = {0, 1, 1, 2, 3, 3, 4, 5, 5, 6, 6, 6, 8, 8, 8, 10, 9,
                                     10, 11, 11, 12, 12, 12, 12, 16, 14, 14, 16, 16, 16, 16};
constexpr std::int32_t kOeisA[31] = {0, 1, 1, 2, 2, 3, 4, 4, 4, 5, 6, 7, 7, 8, 8, 8, 8,
                                     9, 10, 11, 12, 12, 13, 14, 14, 15, 15, 15, 16, 16, 16};

constexpr bool MatchesOeis() {
    std::int32_t q[31] = {};
    std::int32_t a[31] = {};
    if (hh::QSequence(30, q, 31) != hh::Status::Ok || hh::ConwaySequence(30, a, 31) != hh::Status::Ok) {
        return false;
    }
    for (int i = 0; i <= 30; ++i) {
        if (q[i] != kOeisQ[i] || a[i] != kOeisA[i]) {
            return false;
        }
    }
    return true;
}

static_assert(MatchesOeis(), "first 30 terms match OEIS A005185 and A004001");
static_assert(hh::StatusName(hh::Status::IndexFell)[0] == 'I', "StatusName is constexpr");

// Index a table by a signed term index without sign-conversion noise (the test is -Wsign-conversion clean).
static std::int32_t At(const std::vector<std::int32_t>& v, std::int32_t i) {
    return v[static_cast<std::size_t>(i)];
}

// Strict reader: M must come first and match kMaxN, rows are "Q n v" / "C n v" with nothing trailing,
// each tag's n strictly increases (no duplicates), 1..3000 is dense for both hammers, and kMaxN is present.
// Returns the number of problems found; prints the first few when verbose.
struct GoldenStats {
    int problems = 0;
    int q_rows = 0;
    int c_rows = 0;
};

static GoldenStats ReadGolden(std::istream& f, const std::vector<std::int32_t>& q, const std::vector<std::int32_t>& a,
                              bool verbose) {
    GoldenStats s;
    auto expect = [&s, verbose](bool ok, const std::string& what) {
        if (!ok) {
            ++s.problems;
            if (verbose && s.problems <= 20) {
                std::printf("FAIL: %s\n", what.c_str());
            }
        }
    };
    std::string line;
    long long last_q = 0;
    long long last_c = 0;
    bool saw_m = false;
    bool rows_before_m = false;
    bool saw_max_q = false;
    bool saw_max_c = false;
    int line_no = 0;
    while (std::getline(f, line)) {
        ++line_no;
        if (!line.empty() && line.back() == '\r') {
            line.pop_back();
        }
        if (line.empty() || line[0] == '#') {
            continue;
        }
        std::istringstream in(line);
        std::string tag;
        long long n = 0;
        long long v = 0;
        std::string extra;
        in >> tag >> n;
        const std::string where = "line " + std::to_string(line_no) + ": " + line;
        if (tag == "M") {
            expect(!saw_m && !in.fail() && !(in >> extra) && n == hh::kMaxN, "M header " + where);
            saw_m = true;
            continue;
        }
        rows_before_m = rows_before_m || !saw_m;
        in >> v;
        if (in.fail() || (in >> extra) || n < 1 || n > hh::kMaxN) {
            expect(false, "malformed " + where);
            continue;
        }
        if (tag == "Q") {
            expect(n > last_q, "Q rows strictly increase " + where);
            expect(n > 3000 || n == last_q + 1, "Q dense 1..3000 " + where);
            expect(q[static_cast<std::size_t>(n)] == v, where);
            last_q = n;
            ++s.q_rows;
            saw_max_q = saw_max_q || n == hh::kMaxN;
        } else if (tag == "C") {
            expect(n > last_c, "C rows strictly increase " + where);
            expect(n > 3000 || n == last_c + 1, "C dense 1..3000 " + where);
            expect(a[static_cast<std::size_t>(n)] == v, where);
            last_c = n;
            ++s.c_rows;
            saw_max_c = saw_max_c || n == hh::kMaxN;
        } else {
            expect(false, "unknown row " + where);
        }
    }
    expect(saw_m && !rows_before_m, "M header present and first");
    expect(s.q_rows == s.c_rows && s.q_rows > 3000, "matching Q/C coverage");
    expect(saw_max_q && saw_max_c, "kMaxN covered for both hammers");
    return s;
}

static std::string Slurp(const char* path) {
    std::ifstream f(path, std::ios::binary);
    std::ostringstream o;
    o << f.rdbuf();
    return o.str();
}

static void Golden(const char* path, const std::vector<std::int32_t>& q, const std::vector<std::int32_t>& a) {
    std::ifstream f(path);
    Check(f.good(), std::string("open golden file ") + path);
    const GoldenStats s = ReadGolden(f, q, a, true);
    Check(s.problems == 0, "golden fixture replays with no problems");
    std::printf("golden: %d Q rows, %d Conway rows, %d problems\n", s.q_rows, s.c_rows, s.problems);
}

// Iteration 10: the strict reader must reject in-memory corruptions of the real fixture (the file on disk
// is only read, never changed), so a weakened reader cannot silently pass a damaged fixture.
static std::string ReplaceFirst(std::string text, const std::string& from, const std::string& to) {
    const std::size_t at = text.find(from);
    if (at != std::string::npos) {
        text.replace(at, from.size(), to);
    }
    return text;
}

static void ReaderRejectsCorruption(const char* path, const std::vector<std::int32_t>& q,
                                    const std::vector<std::int32_t>& a) {
    const std::string good = Slurp(path);
    Check(good.find("\nQ 10 6\n") != std::string::npos && good.find("\nC 10000000 ") != std::string::npos,
          "fixture has the anchor rows the corruptions edit");
    struct Case {
        const char* name;
        std::string text;
    };
    const Case cases[] = {
        {"wrong value", ReplaceFirst(good, "\nQ 10 6\n", "\nQ 10 7\n")},
        {"trailing token", ReplaceFirst(good, "\nQ 10 6\n", "\nQ 10 6 x\n")},
        {"duplicate row", ReplaceFirst(good, "\nQ 10 6\n", "\nQ 10 6\nQ 10 6\n")},
        {"dense gap", ReplaceFirst(good, "\nQ 10 6\n", "\n")},
        {"missing M", ReplaceFirst(good, "M 10000000\n", "")},
        {"wrong M", ReplaceFirst(good, "M 10000000\n", "M 9999999\n")},
        {"second M", good + "M 10000000\n"},
        {"unknown tag", ReplaceFirst(good, "\nQ 10 6\n", "\nQ 10 6\nZ 10 6\n")},
        {"n out of range", good + "Q 10000001 1\n"},
        {"lost kMaxN", ReplaceFirst(good, "\nC 10000000 ", "\nC 9999998 ")},
    };
    for (const Case& c : cases) {
        std::istringstream in(c.text);
        Check(c.text != good, std::string("corruption applied: ") + c.name);
        Check(ReadGolden(in, q, a, false).problems > 0, std::string("reader rejects ") + c.name);
    }
    std::istringstream crlf(ReplaceFirst(good, "\nQ 10 6\n", "\nQ 10 6\r\n"));
    Check(ReadGolden(crlf, q, a, false).problems == 0, "reader tolerates CRLF");
}

static void Properties(const std::vector<std::int32_t>& q, const std::vector<std::int32_t>& a) {
    // Conway: a(2^k) = 2^(k-1), steps of 0 or 1, and a(n) >= n/2.
    for (std::int32_t k = 1; (1 << k) <= hh::kMaxN; ++k) {
        Check(a[static_cast<std::size_t>(1) << k] == (1 << (k - 1)), "a(2^k) k=" + std::to_string(k));
    }
    bool steps_ok = true;
    bool half_ok = true;
    bool q_bounds = true;
    for (std::int32_t n = 2; n <= hh::kMaxN; ++n) {
        const std::int32_t d = At(a, n) - At(a, n - 1);
        steps_ok = steps_ok && (d == 0 || d == 1);
        half_ok = half_ok && 2 * static_cast<std::int64_t>(At(a, n)) >= n;
        q_bounds = q_bounds && At(q, n) >= 1 && At(q, n) <= n;
    }
    Check(steps_ok, "Conway steps are 0 or 1");
    Check(half_ok, "Conway a(n) >= n/2");
    Check(q_bounds, "1 <= Q(n) <= n");
}

static void SingleIndex() {
    std::vector<std::int32_t> scratch(5001);
    for (std::int32_t n = 1; n <= 5000; n += 7) {
        std::vector<std::int32_t> full(static_cast<std::size_t>(n) + 1);
        std::int32_t v = 0;
        Check(hh::Q(n, scratch.data(), scratch.size(), &v) == hh::Status::Ok, "Q ok");
        hh::QSequence(n, full.data(), full.size());
        Check(v == full[static_cast<std::size_t>(n)], "Q single matches sequence n=" + std::to_string(n));
        Check(hh::Conway(n, scratch.data(), scratch.size(), &v) == hh::Status::Ok, "Conway ok");
        hh::ConwaySequence(n, full.data(), full.size());
        Check(v == full[static_cast<std::size_t>(n)], "Conway single matches n=" + std::to_string(n));
    }
}

static void StatusNames() {
    Check(std::strcmp(hh::StatusName(hh::Status::Ok), "Ok") == 0, "name Ok");
    Check(std::strcmp(hh::StatusName(hh::Status::BadArgument), "BadArgument") == 0, "name BadArgument");
    Check(std::strcmp(hh::StatusName(hh::Status::BufferTooSmall), "BufferTooSmall") == 0, "name BufferTooSmall");
    Check(std::strcmp(hh::StatusName(hh::Status::IndexFell), "IndexFell") == 0, "name IndexFell");
    Check(std::strcmp(hh::StatusName(hh::Status::NullPointer), "NullPointer") == 0, "name NullPointer");
    Check(std::strcmp(hh::StatusName(static_cast<hh::Status>(200)), "Unknown") == 0, "name unknown");
    Check(static_cast<int>(hh::Status::NullPointer) == 4, "status values are stable");
}

// Iteration 4: growing a table in chunks with *Extend equals one full fill.
static void Extend(const std::vector<std::int32_t>& q, const std::vector<std::int32_t>& a) {
    const std::int32_t n = 200000;
    std::vector<std::int32_t> gq(static_cast<std::size_t>(n) + 1, -1);
    std::vector<std::int32_t> ga(static_cast<std::size_t>(n) + 1, -1);
    std::int32_t from = 0;
    std::int32_t step = 1;
    bool ok = true;
    while (from < n) {
        const std::int32_t to = from + step > n ? n : from + step;
        ok = ok && hh::QExtend(from, to, gq.data(), gq.size()) == hh::Status::Ok;
        ok = ok && hh::ConwayExtend(from, to, ga.data(), ga.size()) == hh::Status::Ok;
        from = to;
        step = step * 3 + 1;
    }
    Check(ok, "chunked extend ok");
    bool same = At(gq, 0) == 0 && At(ga, 0) == 0;
    for (std::int32_t i = 1; i <= n; ++i) {
        same = same && At(gq, i) == At(q, i) && At(ga, i) == At(a, i);
    }
    Check(same, "chunked extend equals full fill");
    std::int32_t buf[8] = {0, 1, 1, 2, 3, 3, 4, 5};
    Check(hh::QExtend(7, 7, buf, 8) == hh::Status::Ok && buf[7] == 5, "empty extend is a no-op");
    Check(hh::QExtend(5, 4, buf, 8) == hh::Status::BadArgument, "n < from");
    Check(hh::ConwayExtend(-1, 4, buf, 8) == hh::Status::BadArgument, "from < 0");
    Check(hh::ConwayExtend(2, 8, buf, 8) == hh::Status::BufferTooSmall, "extend buffer");
    Check(hh::QExtend(2, 5, nullptr, 8) == hh::Status::NullPointer, "extend null");
    std::int32_t bad[6] = {0, 1, 1, 9, 0, 0};
    Check(hh::ConwayExtend(3, 5, bad, 6) == hh::Status::IndexFell, "corrupt Conway prefix detected");
    Check(hh::QExtend(3, 5, bad, 6) == hh::Status::IndexFell, "corrupt Q prefix detected");
}

// Iteration 5: an independent memoized-recursion model and a full re-check of both recurrences.
static std::int32_t MemoQ(std::int32_t n, std::vector<std::int32_t>& memo) {
    if (n <= 2) {
        return 1;
    }
    if (memo[static_cast<std::size_t>(n)] == 0) {
        memo[static_cast<std::size_t>(n)] = MemoQ(n - MemoQ(n - 1, memo), memo) + MemoQ(n - MemoQ(n - 2, memo), memo);
    }
    return memo[static_cast<std::size_t>(n)];
}

static std::int32_t MemoA(std::int32_t n, std::vector<std::int32_t>& memo) {
    if (n <= 2) {
        return 1;
    }
    if (memo[static_cast<std::size_t>(n)] == 0) {
        const std::int32_t p = MemoA(n - 1, memo);
        memo[static_cast<std::size_t>(n)] = MemoA(p, memo) + MemoA(n - p, memo);
    }
    return memo[static_cast<std::size_t>(n)];
}

static void Model(const std::vector<std::int32_t>& q, const std::vector<std::int32_t>& a) {
    const std::int32_t n = 4000;
    std::vector<std::int32_t> mq(static_cast<std::size_t>(n) + 1, 0);
    std::vector<std::int32_t> ma(static_cast<std::size_t>(n) + 1, 0);
    bool same = true;
    for (std::int32_t i = 1; i <= n; ++i) {  // ascending keeps the recursion shallow
        same = same && MemoQ(i, mq) == At(q, i) && MemoA(i, ma) == At(a, i);
    }
    Check(same, "memoized recursion model agrees 1..4000");
    bool rec = At(q, 1) == 1 && At(q, 2) == 1 && At(a, 1) == 1 && At(a, 2) == 1;
    for (std::int32_t i = 3; i <= hh::kMaxN; ++i) {
        rec = rec && At(q, i) == At(q, i - At(q, i - 1)) + At(q, i - At(q, i - 2)) && At(a, i) == At(a, At(a, i - 1)) + At(a, i - At(a, i - 1));
    }
    Check(rec, "both recurrences hold at every n to kMaxN");
}

// Iteration 6: canary guards; randomized n and buffer lengths around n + 1 never write past len,
// and argument failures leave the whole buffer untouched.
static void Canaries() {
    std::mt19937 rng(58921u);
    const std::int32_t kCanary = 0x5A5A5A5A;
    int writes_past = 0;
    int dirty_failures = 0;
    int wrong_status = 0;
    for (int trial = 0; trial < 3000; ++trial) {
        const std::int32_t n = static_cast<std::int32_t>(rng() % 3000);
        const int delta = static_cast<int>(rng() % 5) - 2;  // len in n-1 .. n+3
        const long long want_len = static_cast<long long>(n) + 1 + delta;
        if (want_len < 0) {
            continue;
        }
        const std::size_t len = static_cast<std::size_t>(want_len);
        std::vector<std::int32_t> buf(len + 8, kCanary);
        const bool use_q = (trial & 1) == 0;
        const hh::Status st = use_q ? hh::QSequence(n, buf.data(), len) : hh::ConwaySequence(n, buf.data(), len);
        const hh::Status want = len >= static_cast<std::size_t>(n) + 1 ? hh::Status::Ok : hh::Status::BufferTooSmall;
        wrong_status += st != want ? 1 : 0;
        for (std::size_t i = len; i < buf.size(); ++i) {
            writes_past += buf[i] != kCanary ? 1 : 0;
        }
        if (st != hh::Status::Ok) {
            for (std::size_t i = 0; i < len; ++i) {
                dirty_failures += buf[i] != kCanary ? 1 : 0;
            }
        }
    }
    Check(wrong_status == 0, "randomized status matches the length rule");
    Check(writes_past == 0, "no write past len");
    Check(dirty_failures == 0, "argument failures write nothing");
}

static void Edges() {
    std::int32_t buf[16] = {};
    std::int32_t out = 77;
    Check(hh::QSequence(-1, buf, 16) == hh::Status::BadArgument, "QSequence -1");
    Check(hh::ConwaySequence(hh::kMaxN + 1, buf, 16) == hh::Status::BadArgument, "Conway max+1");
    Check(hh::QSequence(15, buf, 15) == hh::Status::BufferTooSmall, "buffer n+1 needed");
    Check(hh::ConwaySequence(3, nullptr, 0) == hh::Status::NullPointer, "null buffer");
    Check(hh::QSequence(3, nullptr, 4) == hh::Status::NullPointer, "null buffer with length");
    Check(hh::QSequence(-1, nullptr, 0) == hh::Status::BadArgument, "range checked before pointers");
    Check(hh::QSequence(0, buf, 1) == hh::Status::Ok && buf[0] == 0, "n=0 sequence");
    Check(hh::QSequence(15, buf, 16) == hh::Status::Ok && buf[15] == 10, "Q(15)=10");
    Check(hh::Q(0, buf, 16, &out) == hh::Status::BadArgument && out == 77, "Q(0) rejected, out untouched");
    Check(hh::Conway(-5, buf, 16, &out) == hh::Status::BadArgument && out == 77, "Conway(-5)");
    Check(hh::Q(20, buf, 16, &out) == hh::Status::BufferTooSmall && out == 77, "scratch too small");
    Check(hh::Q(1, buf, 16, nullptr) == hh::Status::NullPointer, "null out");
    Check(hh::Conway(5, nullptr, 16, &out) == hh::Status::NullPointer && out == 77, "null scratch");
    Check(hh::Strike(hh::Hammer::Conway, 1, buf, 16, &out) == hh::Status::Ok && out == 1, "a(1)");
    Check(hh::GradeClaim(hh::Hammer::Q, 10, 6, buf, 16) == hh::Grade::Turned, "grade turned");
    Check(hh::GradeClaim(hh::Hammer::Conway, 10, 7, buf, 16) == hh::Grade::Slipped, "grade slipped");
    Check(hh::GradeClaim(hh::Hammer::Q, 0, 0, buf, 16) == hh::Grade::Slipped, "bad index slips");
    Check(std::strncmp(hh::ForgemasterLine(hh::Grade::Turned), "Forgemaster:", 12) == 0, "line turned");
    Check(std::strncmp(hh::ForgemasterLine(hh::Grade::Slipped), "Forgemaster:", 12) == 0, "line slipped");
    Check(std::strcmp(hh::kQuestId, "q_hofstadter_hammers") == 0, "quest id");
}

int main(int argc, char** argv) {
    const char* path = argc > 1 ? argv[1] : "hofstadter_hammers_golden.txt";
    std::vector<std::int32_t> q(static_cast<std::size_t>(hh::kMaxN) + 1);
    std::vector<std::int32_t> a(static_cast<std::size_t>(hh::kMaxN) + 1);
    Check(hh::QSequence(hh::kMaxN, q.data(), q.size()) == hh::Status::Ok, "Q to kMaxN");
    Check(hh::ConwaySequence(hh::kMaxN, a.data(), a.size()) == hh::Status::Ok, "Conway to kMaxN");
    Golden(path, q, a);
    ReaderRejectsCorruption(path, q, a);
    Properties(q, a);
    SingleIndex();
    Extend(q, a);
    Model(q, a);
    Canaries();
    Edges();
    StatusNames();
    std::printf("%s: %d checks, %d failures\n", g_failures == 0 ? "PASS" : "FAIL", g_checks, g_failures);
    return g_failures == 0 ? EXIT_SUCCESS : EXIT_FAILURE;
}
