// SPDX-License-Identifier: MIT
// G561 Channel Dash core, header-only C++17 port of tools/streaming/channel_dash.py (G574 batch 2).
// Takes an already-laid-out channel (barge cells at tick 0 and velocity per lane, dock and start
// columns, as laid out by the Python tool) and ports barge drift, the exact BFS par over
// (row, col, tick mod 9) in the same U/D/L/R/. order, move validation and the verdict.
// Engine-free: no Unreal includes, no exceptions, no RTTI; errors come back as codes.
#pragma once

#include <cstdint>
#include <string>
#include <vector>

namespace DaedalusDiskSaver {
namespace ChannelDash {

constexpr int Width = 9;
constexpr int MaxLanes = 8;     // Python lays out 3..5
constexpr int MaxSpeed = Width;  // |velocity| cap; Python uses 1 or 2
enum class Error { None, Letter, Dock, Leaves };
enum class Verdict { Swift, Safe, Swamped };

struct Lane {
    unsigned Cells = 0;  // bit c = barge on column c at tick 0
    int Velocity = 0;
};

struct Channel {
    std::vector<Lane> Lanes;  // top (row 1) to bottom
    int Dock = 0, Start = 0;
};

inline bool ValidChannel(const Channel& C) {
    if (C.Lanes.size() > static_cast<std::size_t>(MaxLanes)) return false;
    for (const Lane& L : C.Lanes)
        if (L.Cells >= (1u << Width) || L.Velocity < -MaxSpeed || L.Velocity > MaxSpeed) return false;
    return C.Dock >= 0 && C.Dock < Width && C.Start >= 0 && C.Start < Width;
}

// busy(): Python's (col - v*t) % 9 is never negative; reduce t first so nothing overflows.
inline bool Busy(const Channel& C, int Row, int Col, std::uint64_t Tick) {
    const int Home = static_cast<int>(C.Lanes.size()) + 1;
    if (Row == 0 || Row == Home) return false;
    const Lane& L = C.Lanes[Row - 1];
    const int T = static_cast<int>(Tick % Width);
    const int X = ((Col - L.Velocity * T) % Width + Width) % Width;
    return (L.Cells >> X) & 1u;
}

inline int MoveOf(char M, int& Dr, int& Dc) {
    switch (M) {
        case 'U': Dr = -1; Dc = 0; return 0;
        case 'D': Dr = 1; Dc = 0; return 1;
        case 'L': Dr = 0; Dc = -1; return 2;
        case 'R': Dr = 0; Dc = 1; return 3;
        case '.': Dr = 0; Dc = 0; return 4;
        default: return -1;
    }
}

inline bool Solve(const Channel& C, int& Par, std::string& Plan) {
    if (!ValidChannel(C)) return false;
    const int Home = static_cast<int>(C.Lanes.size()) + 1;
    const auto Key = [](int R, int Col, int T) { return (static_cast<std::size_t>(R) * Width + Col) * Width + T; };
    std::vector<std::int64_t> Prev(static_cast<std::size_t>(Home + 1) * Width * Width, -2);
    std::vector<char> How(Prev.size(), 0);
    const std::size_t S0 = Key(Home, C.Start, 0);
    Prev[S0] = -1;
    std::vector<std::size_t> Queue{S0};
    static const char Order[5] = {'U', 'D', 'L', 'R', '.'};
    for (std::size_t Head = 0; Head < Queue.size(); ++Head) {
        std::size_t S = Queue[Head];
        const int T = static_cast<int>(S % Width);
        const int Col = static_cast<int>((S / Width) % Width);
        const int R = static_cast<int>(S / (Width * Width));
        if (R == 0 && Col == C.Dock) {
            Plan.clear();
            while (Prev[S] != -1) {
                Plan.insert(Plan.begin(), How[S]);
                S = static_cast<std::size_t>(Prev[S]);
            }
            Par = static_cast<int>(Plan.size());
            return true;
        }
        for (char M : Order) {
            int Dr = 0, Dc = 0;
            MoveOf(M, Dr, Dc);
            const int Nr = R + Dr, Nc = Col + Dc;
            if (Nr < 0 || Nr > Home || Nc < 0 || Nc >= Width) continue;
            const int Nt = (T + 1) % Width;
            if (Busy(C, Nr, Nc, static_cast<std::uint64_t>(Nt))) continue;
            const std::size_t K = Key(Nr, Nc, Nt);
            if (Prev[K] == -2) {
                Prev[K] = static_cast<std::int64_t>(Queue[Head]);
                How[K] = M;
                Queue.push_back(K);
            }
        }
    }
    return false;
}

struct Result {
    Error Err = Error::None;
    int Ticks = 0, HitTick = 0, Row = 0, Col = 0;
    Verdict V = Verdict::Swamped;
};

// Par < 0 means the channel cannot be crossed.
inline Result Play(const Channel& C, int Par, const std::string& Moves) {
    Result R;
    const int Home = static_cast<int>(C.Lanes.size()) + 1;
    int Row = Home, Col = C.Start, Hit = 0;
    std::uint64_t T = 0;
    for (char M : Moves) {
        ++T;
        int Dr = 0, Dc = 0;
        if (MoveOf(M, Dr, Dc) < 0) { R.Err = Error::Letter; return R; }
        if (Row == 0 && Col == C.Dock) { R.Err = Error::Dock; return R; }
        const int Nr = Row + Dr, Nc = Col + Dc;
        if (Nr < 0 || Nr > Home || Nc < 0 || Nc >= Width) { R.Err = Error::Leaves; return R; }
        Row = Nr;
        Col = Nc;
        if (Busy(C, Row, Col, T)) {
            Hit = static_cast<int>(T);
            break;
        }
    }
    R.Ticks = Hit ? Hit : static_cast<int>(Moves.size());
    R.HitTick = Hit;
    R.Row = Row;
    R.Col = Col;
    R.V = (!Hit && Row == 0 && Col == C.Dock) ? ((Par >= 0 && R.Ticks <= Par) ? Verdict::Swift : Verdict::Safe)
                                               : Verdict::Swamped;
    return R;
}

inline const char* VerdictName(Verdict V) {
    return V == Verdict::Swift ? "swift" : V == Verdict::Safe ? "safe" : "swamped";
}
inline const char* ErrorName(Error E) {
    return E == Error::Letter ? "letter" : E == Error::Dock ? "dock" : E == Error::Leaves ? "leaves" : "none";
}

}  // namespace ChannelDash
}  // namespace DaedalusDiskSaver
