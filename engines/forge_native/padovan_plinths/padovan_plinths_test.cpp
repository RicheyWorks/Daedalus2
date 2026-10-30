// SPDX-License-Identifier: MIT
//
// Standalone test for padovan_plinths.h against golden vectors generated from the Java
// PadovanPlinths (padovan_plinths_golden.txt), plus identity, edge and compile-time checks.
// Build: g++ -std=c++17 -Wall -Wextra -Werror padovan_plinths_test.cpp -o t && ./t padovan_plinths_golden.txt
#include "padovan_plinths.h"

#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <limits>
#include <sstream>
#include <string>

namespace pp = daedalus::forge::padovan;

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

static bool ParseI64(const std::string& s, std::int64_t* out) {
    std::istringstream in(s);
    long long v = 0;
    in >> v;
    if (in.fail()) {
        return false;
    }
    *out = static_cast<std::int64_t>(v);
    return true;
}

static_assert(pp::kMaxIndex == 156, "max index");
static_assert(pp::IndexOf(1) == 0, "first 1");
static_assert(pp::IndexOf(2) == 3, "first 2");
static_assert(pp::GradeClaim(10, 12) == pp::Grade::Turned, "grade");

static void Golden(const char* path) {
    std::ifstream f(path);
    Check(f.good(), std::string("open golden file ") + path);
    std::string line;
    int terms = 0;
    int index_rows = 0;
    int sum_rows = 0;
    int overflow_rows = 0;
    while (std::getline(f, line)) {
        if (line.empty() || line[0] == '#') {
            continue;
        }
        std::istringstream in(line);
        std::string tag;
        in >> tag;
        if (tag == "M") {
            int mx = 0;
            in >> mx;
            Check(mx == pp::kMaxIndex, "M " + line);
        } else if (tag == "T") {
            int n = 0;
            std::string vs;
            in >> n >> vs;
            std::int64_t want = 0;
            std::int64_t got = 0;
            Check(ParseI64(vs, &want), "parse " + line);
            Check(pp::Padovan(n, &got) == pp::Status::Ok && got == want, line);
            ++terms;
        } else if (tag == "I") {
            std::string vs;
            int want = 0;
            in >> vs >> want;
            std::int64_t v = 0;
            Check(ParseI64(vs, &v), "parse " + line);
            Check(pp::IndexOf(v) == want, line);
            Check(pp::IsPadovan(v) == (want >= 0), "is " + line);
            ++index_rows;
        } else if (tag == "S") {
            int a = 0;
            int b = 0;
            std::string vs;
            in >> a >> b >> vs;
            std::int64_t got = 0;
            const pp::Status st = pp::RunSum(a, b, &got);
            if (vs == "OVERFLOW") {
                Check(st == pp::Status::Overflow, line);
                ++overflow_rows;
            } else {
                std::int64_t want = 0;
                Check(ParseI64(vs, &want), "parse " + line);
                Check(st == pp::Status::Ok && got == want, line);
            }
            ++sum_rows;
        } else {
            Check(false, "unknown row " + line);
        }
    }
    Check(terms == pp::kMaxIndex + 1, "every term covered");
    Check(index_rows > 5000, "index rows");
    Check(sum_rows > 500 && overflow_rows > 0, "sum and overflow rows");
    std::printf("golden: %d terms, %d index rows, %d run sums (%d overflow)\n", terms, index_rows, sum_rows,
                overflow_rows);
}

static void Identities() {
    for (int n = 5; n <= pp::kMaxIndex; ++n) {
        std::int64_t a = 0;
        std::int64_t b = 0;
        std::int64_t c = 0;
        pp::Padovan(n, &a);
        pp::Padovan(n - 1, &b);
        pp::Padovan(n - 5, &c);
        Check(a == b + c, "P(n)=P(n-1)+P(n-5) n=" + std::to_string(n));
    }
    for (int n = 0; n + 5 <= pp::kMaxIndex; ++n) {
        std::int64_t s = 0;
        std::int64_t p = 0;
        Check(pp::RunSum(0, n, &s) == pp::Status::Ok, "sum ok n=" + std::to_string(n));
        pp::Padovan(n + 5, &p);
        Check(s == p - 2, "sum identity n=" + std::to_string(n));
    }
}

static void Edges() {
    const std::int64_t kMax = std::numeric_limits<std::int64_t>::max();
    const std::int64_t kMin = std::numeric_limits<std::int64_t>::min();
    std::int64_t out = 77;
    Check(!pp::CheckedAdd(kMax, 1, &out) && out == 77, "max+1 overflows, out untouched");
    Check(!pp::CheckedAdd(kMin, -1, &out) && out == 77, "min-1 overflows");
    Check(pp::CheckedAdd(kMax, 0, &out) && out == kMax, "max+0");
    Check(pp::CheckedAdd(kMax, kMin, &out) && out == -1, "max+min");
    Check(pp::CheckedAdd(kMax - 5, 5, &out) && out == kMax, "max-5+5");
    std::int64_t next = 0;
    std::int64_t p2 = 0;
    std::int64_t p1 = 0;
    pp::Padovan(pp::kMaxIndex - 1, &p2);
    pp::Padovan(pp::kMaxIndex - 2, &p1);
    Check(!pp::CheckedAdd(p2, p1, &next), "P(max+1) = P(max-1)+P(max-2) overflows int64");
    out = 5;
    Check(pp::Padovan(-1, &out) == pp::Status::BadArgument && out == 5, "n=-1");
    Check(pp::Padovan(pp::kMaxIndex + 1, &out) == pp::Status::BadArgument, "n=max+1");
    Check(pp::RunSum(5, 4, &out) == pp::Status::BadArgument, "b<a");
    Check(pp::RunSum(-1, 3, &out) == pp::Status::BadArgument, "a<0");
    Check(pp::RunSum(0, pp::kMaxIndex + 1, &out) == pp::Status::BadArgument, "b>max");
    Check(pp::RunSum(0, pp::kMaxIndex, &out) == pp::Status::Overflow, "full run overflows");
    Check(pp::RunSum(4, 4, &out) == pp::Status::Ok && out == 2, "single plinth");
    Check(!pp::IsPadovan(0) && !pp::IsPadovan(kMax) && !pp::IsPadovan(kMin), "non-members");
    Check(pp::GradeClaim(10, 13) == pp::Grade::Slipped, "grade slipped");
    Check(pp::GradeClaim(-1, 1) == pp::Grade::Slipped, "bad index slips");
    Check(std::strncmp(pp::ForgemasterLine(pp::Grade::Turned), "Forgemaster:", 12) == 0, "line turned");
    Check(std::strncmp(pp::ForgemasterLine(pp::Grade::Slipped), "Forgemaster:", 12) == 0, "line slipped");
    Check(std::strcmp(pp::kQuestId, "q_padovan_plinths") == 0, "quest id");
}

int main(int argc, char** argv) {
    const char* path = argc > 1 ? argv[1] : "padovan_plinths_golden.txt";
    Golden(path);
    Identities();
    Edges();
    std::printf("%s: %d checks, %d failures\n", g_failures == 0 ? "PASS" : "FAIL", g_checks, g_failures);
    return g_failures == 0 ? EXIT_SUCCESS : EXIT_FAILURE;
}
