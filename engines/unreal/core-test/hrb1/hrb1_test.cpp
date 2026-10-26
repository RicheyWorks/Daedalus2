// SPDX-License-Identifier: MIT
// Usage: hrb1_test <path to docs/contracts/hrb-v1/mint-yarrow-sage.hrb>
#include "DaedalusHerbChordCore.h"
#include <cstdio>
#include <fstream>
#include <sstream>

using daedalus::herb::Chord;
using daedalus::herb::DecodeHrb1;
static int failures = 0, checks = 0;
static void Check(bool ok, const char* what) { ++checks; if (!ok) { ++failures; std::printf("FAIL %s\n", what); } }
static bool Ok(const std::string& s, Chord& c) { std::string e; return DecodeHrb1(s, c, e); }
static bool Bad(const std::string& s) {
    Chord c; c.Root = 7; c.Quality = "keep"; std::string e;
    const bool decoded = DecodeHrb1(s, c, e);
    return !decoded && !e.empty() && c.Root == 7 && c.Quality == "keep";  // untouched on failure
}

int main(int argc, char** argv) {
    if (argc != 2) { std::printf("usage: hrb1_test fixture.hrb\n"); return 2; }
    std::ifstream in(argv[1], std::ios::binary);
    std::stringstream ss; ss << in.rdbuf();
    const std::string fixture = ss.str();
    Chord c;
    Check(Ok(fixture, c), "fixture decodes");
    Check(c.Root == 1 && c.Quality == "cluster" && c.Effect == "CHAOS", "fixture chord fields");
    Check(c.Strength == 0.3 && c.Freqs.size() == 2 && c.Freqs[0] == 277.183 && c.Freqs[1] == 349.228, "fixture numbers");
    Chord t;
    Check(Ok("HRB 1\nchord 11 major HEAL 1.000\nfreq 246.942\nfreq 311.127\nfreq 369.994\nend\n", t) && t.Root == 11 && t.Freqs.size() == 3, "triad");
    std::string twelve = "HRB 1\nchord 0 cluster CHAOS 0.400\n";
    for (int i = 0; i < 12; ++i) twelve += "freq " + std::to_string(100 + i) + ".000\n";
    Check(Ok(twelve + "end\n", t) && t.Freqs.size() == 12, "12 freqs accepted");
    const std::string head = "HRB 1\nchord 1 cluster CHAOS 0.300\n";
    const char* bad[] = {
        "", "HRB 1\n", "HRB 2\nchord 1 cluster CHAOS 0.300\nfreq 1.000\nend\n",
        "HRB 1\r\nchord 1 cluster CHAOS 0.300\nfreq 1.000\nend\n",
        "HRB 1\nchord 12 cluster CHAOS 0.300\nfreq 1.000\nend\n",
        "HRB 1\nchord 01 cluster CHAOS 0.300\nfreq 1.000\nend\n",
        "HRB 1\nchord -1 cluster CHAOS 0.300\nfreq 1.000\nend\n",
        "HRB 1\nchord 1 Cluster CHAOS 0.300\nfreq 1.000\nend\n",
        "HRB 1\nchord 1 cluster chaos 0.300\nfreq 1.000\nend\n",
        "HRB 1\nchord 1 cluster CHAOS 1.001\nfreq 1.000\nend\n",
        "HRB 1\nchord 1 cluster CHAOS 0.3\nfreq 1.000\nend\n",
        "HRB 1\nchord 1 cluster CHAOS 0,300\nfreq 1.000\nend\n",
        "HRB 1\nchord 1  cluster CHAOS 0.300\nfreq 1.000\nend\n",
        "HRB 1\nchord 1 cluster CHAOS 0.300\nend\n",
        "HRB 1\nchord 1 cluster CHAOS 0.300\nfreq 2.000\nfreq 1.000\nend\n",
        "HRB 1\nchord 1 cluster CHAOS 0.300\nfreq 0.000\nend\n",
        "HRB 1\nchord 1 cluster CHAOS 0.300\nfreq 1e3\nend\n",
        "HRB 1\nchord 1 cluster CHAOS 0.300\nfreq 1.000\n",
        "HRB 1\nchord 1 cluster CHAOS 0.300\nfreq 1.000\nend",
        "HRB 1\nchord 1 cluster CHAOS 0.300\nfreq 1.000\nend\nend\n",
        "HRB 1\nchord 1 cluster CHAOS 0.300\nfreq 1.000\nend\n\n",
        "HRB 1\nchord 1 cluster CHAOS 0.300\nlayer x 1.000\nfreq 1.000\nend\n",
        "HRB 1\nchord 1 cluster CHAOS 0.300\nfreq 1.000\nchord 1 cluster CHAOS 0.300\nend\n",
    };
    for (const char* b : bad) Check(Bad(b), b);
    Check(Bad(twelve + "freq 200.000\nend\n"), "13 freqs rejected");
    Check(Bad(head + std::string("freq 1.000\0x\nend\n", 17)), "embedded NUL rejected");
    Check(Bad(head + "freq 1.000\xC3\xA9\nend\n"), "non-ASCII rejected");
    Check(Bad(head + "freq " + std::string(600, '1') + ".000\nend\n"), "long line rejected");
    std::string big = head; while (big.size() < 5000) big += "freq 1.000\n";
    Check(Bad(big + "end\n"), "oversized body rejected");
    std::printf("hrb1: %d checks, %d failed\n", checks, failures);
    return failures ? 1 : 0;
}
