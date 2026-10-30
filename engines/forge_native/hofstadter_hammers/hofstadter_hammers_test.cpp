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

// Strict reader: M must come first and match kMaxN, rows are "Q n v" / "C n v" with nothing trailing,
// each tag's n strictly increases (no duplicates), 1..3000 is dense for both hammers, and kMaxN is present.
static void Golden(const char* path, const std::vector<std::int32_t>& q, const std::vector<std::int32_t>& a) {
    std::ifstream f(path);
    Check(f.good(), std::string("open golden file ") + path);
    std::string line;
    int q_rows = 0;
    int c_rows = 0;
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
            Check(!saw_m && !in.fail() && !(in >> extra) && n == hh::kMaxN, "M header " + where);
            saw_m = true;
            continue;
        }
        rows_before_m = rows_before_m || !saw_m;
        in >> v;
        if (in.fail() || (in >> extra) || n < 1 || n > hh::kMaxN) {
            Check(false, "malformed " + where);
            continue;
        }
        if (tag == "Q") {
            Check(n > last_q, "Q rows strictly increase " + where);
            if (n <= 3000) {
                Check(n == last_q + 1, "Q dense 1..3000 " + where);
            }
            Check(q[static_cast<std::size_t>(n)] == v, where);
            last_q = n;
            ++q_rows;
            saw_max_q = saw_max_q || n == hh::kMaxN;
        } else if (tag == "C") {
            Check(n > last_c, "C rows strictly increase " + where);
            if (n <= 3000) {
                Check(n == last_c + 1, "C dense 1..3000 " + where);
            }
            Check(a[static_cast<std::size_t>(n)] == v, where);
            last_c = n;
            ++c_rows;
            saw_max_c = saw_max_c || n == hh::kMaxN;
        } else {
            Check(false, "unknown row " + where);
        }
    }
    Check(saw_m && !rows_before_m, "M header present and first");
    Check(q_rows == c_rows && q_rows > 3000, "matching Q/C coverage");
    Check(saw_max_q && saw_max_c, "kMaxN covered for both hammers");
    std::printf("golden: %d Q rows, %d Conway rows, max_n covered: %s\n", q_rows, c_rows,
                saw_max_q && saw_max_c ? "yes" : "no");
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
        const std::int32_t d = a[n] - a[n - 1];
        steps_ok = steps_ok && (d == 0 || d == 1);
        half_ok = half_ok && 2 * static_cast<std::int64_t>(a[n]) >= n;
        q_bounds = q_bounds && q[n] >= 1 && q[n] <= n;
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
    Properties(q, a);
    SingleIndex();
    Edges();
    StatusNames();
    std::printf("%s: %d checks, %d failures\n", g_failures == 0 ? "PASS" : "FAIL", g_checks, g_failures);
    return g_failures == 0 ? EXIT_SUCCESS : EXIT_FAILURE;
}