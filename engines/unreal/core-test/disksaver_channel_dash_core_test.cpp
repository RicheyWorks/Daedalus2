// SPDX-License-Identifier: MIT
// G561 port check: DaedalusDiskSaverChannelDashCore.h replays disksaver_channel_dash_parity.txt
// (written from channel_dash.py by tools/streaming/disksaver_cpp_parity.py) line for line.
#include "DaedalusDiskSaverChannelDashCore.h"
#include "disksaver_parity.h"

namespace CD = DaedalusDiskSaver::ChannelDash;
using namespace DiskSaverParity;

static bool SignedInt(const std::string& S, int& V) {
    if (!S.empty() && S[0] == '-') {
        if (!ToInt(S.substr(1), V) || V == 0) return false;
        V = -V;
        return true;
    }
    return ToInt(S, V);
}

int main(int argc, char** argv) {
    CD::Channel C;
    C.Dock = CD::Width;
    Check(!CD::ValidChannel(C), "dock off the channel refused");
    C.Dock = 0;
    C.Lanes.push_back({1u << CD::Width, 1});
    Check(!CD::ValidChannel(C), "lane wider than the channel refused");
    C.Lanes[0] = {1u, -1};
    Check(CD::Busy(C, 1, 8, 1) && !CD::Busy(C, 1, 0, 1) && CD::Busy(C, 1, 8, 1000000000000ULL),
          "drift wraps west (Python modulo) with a huge tick (10^12 = 1 mod 9)");

    std::string Case;
    int Cases = 0, Trials = 0, Par = -1;
    for (const auto& T : ReadLines(argc > 1 ? argv[1] : "disksaver_channel_dash_parity.txt")) {
        const std::string Line = Case + ":" + T[0] + (T.size() > 1 ? " " + T[1] : "");
        if (T[0] == "C" && T.size() == 2) {
            Case = T[1];
            ++Cases;
        } else if (T[0] == "L" && T.size() == 4) {
            C = CD::Channel{};
            for (const std::string& L : Split(T[1], ',')) {
                const std::vector<std::string> P = Split(L, ':');
                int V = 0;
                Check(P.size() == 2 && P[0].size() == static_cast<std::size_t>(CD::Width) && SignedInt(P[1], V),
                      Line + " lane " + L);
                if (P.size() != 2) continue;
                CD::Lane Ln;
                for (int c = 0; c < CD::Width && c < static_cast<int>(P[0].size()); ++c) {
                    Check(P[0][c] == '0' || P[0][c] == '1', Line + " lane cell");
                    if (P[0][c] == '1') Ln.Cells |= 1u << c;
                }
                Ln.Velocity = V;
                C.Lanes.push_back(Ln);
            }
            Check(ToInt(T[2], C.Dock) && ToInt(T[3], C.Start) && CD::ValidChannel(C), Line + " channel");
        } else if (T[0] == "P" && T.size() == 3) {
            int Got = -1;
            std::string Plan;
            const bool Ok = CD::Solve(C, Got, Plan);
            Par = Ok ? Got : -1;
            Check((Ok ? std::to_string(Got) : "-1") == T[1] && (Ok && !Plan.empty() ? Plan : "-") == T[2],
                  Line + " got " + std::to_string(Par) + " " + Plan);
        } else if (T[0] == "T" && (T.size() == 4 || T.size() == 8)) {
            ++Trials;
            const CD::Result R = CD::Play(C, Par, T[1] == "-" ? "" : T[1]);
            if (T[2] == "err") {
                Check(R.Err != CD::Error::None && T[3] == CD::ErrorName(R.Err), Line + " want err " + T[3]);
            } else {
                Check(R.Err == CD::Error::None && T.size() == 8 && T[2] == "ok" && std::to_string(R.Ticks) == T[3] &&
                          std::to_string(R.HitTick) == T[4] && std::to_string(R.Row) == T[5] &&
                          std::to_string(R.Col) == T[6] && T[7] == CD::VerdictName(R.V),
                      Line + " got " + std::to_string(R.Ticks) + " " + std::to_string(R.HitTick) + " " +
                          std::to_string(R.Row) + " " + std::to_string(R.Col) + " " + CD::VerdictName(R.V));
            }
        } else {
            Check(false, "unknown line " + Line);
        }
    }
    return Finish("channel_dash", Cases, Trials);
}
