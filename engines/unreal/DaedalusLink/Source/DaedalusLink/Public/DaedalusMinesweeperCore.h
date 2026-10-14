// SPDX-License-Identifier: MIT
#pragma once

// Engine-free Retro rules. Reference: RicheyWorks/minesweeper-pro GameService
// at 63156079e141bca2b0cd3a0f297bb6595b28c2d0. See docs/GAME-PORTS.md.
#include <algorithm>
#include <cstdint>
#include <utility>
#include <vector>

namespace daedalus { namespace minesweeper {

enum class Outcome { Playing, Won, Lost };

struct Cell
{
    bool Mine = false;
    bool Revealed = false;
    bool Flagged = false;
    int Adjacent = 0;
};

class Board
{
public:
    static constexpr int MaxDimension = 32;

    // Invalid input leaves the existing game untouched. Mine indices are row-major.
    bool Load(int rows, int cols, const std::vector<int>& mines)
    {
        if (!ValidDimensions(rows, cols) || mines.empty() ||
            mines.size() >= static_cast<std::size_t>(rows * cols)) return false;
        std::vector<int> ordered = mines;
        std::sort(ordered.begin(), ordered.end());
        for (std::size_t i = 0; i < ordered.size(); ++i)
        {
            if (ordered[i] < 0 || ordered[i] >= rows * cols ||
                (i && ordered[i] == ordered[i - 1])) return false;
        }
        RowCount = rows;
        ColCount = cols;
        MineIndices = std::move(ordered);
        Cells.assign(static_cast<std::size_t>(rows * cols), Cell{});
        for (int index : MineIndices) Cells[static_cast<std::size_t>(index)].Mine = true;
        for (int row = 0; row < rows; ++row)
        {
            for (int col = 0; col < cols; ++col)
            {
                Cell& cell = Cells[static_cast<std::size_t>(row * cols + col)];
                if (cell.Mine) continue;
                Neighbours(row, col, [&](int index) {
                    if (Cells[static_cast<std::size_t>(index)].Mine) ++cell.Adjacent;
                });
            }
        }
        CurrentResult = Outcome::Playing;
        FinalScore = 0;
        return true;
    }

    // Generation happens at board creation, NOT on first reveal. Match the source's
    // protected 3x3 zone, falling back to only the chosen safe cell on dense boards.
    // The portable shuffle is deterministic across C++ libraries; it intentionally
    // replaces Java SecureRandom, whose board layouts cannot be seed-replayed.
    bool Generate(int rows, int cols, int mineCount, std::uint32_t seed,
                  int safeRow = 0, int safeCol = 0)
    {
        if (!ValidDimensions(rows, cols) || mineCount < 1 || mineCount >= rows * cols ||
            safeRow < 0 || safeRow >= rows || safeCol < 0 || safeCol >= cols) return false;
        std::vector<int> candidates;
        for (int row = 0; row < rows; ++row)
            for (int col = 0; col < cols; ++col)
                if (row < safeRow - 1 || row > safeRow + 1 ||
                    col < safeCol - 1 || col > safeCol + 1) candidates.push_back(row * cols + col);
        if (candidates.size() < static_cast<std::size_t>(mineCount))
        {
            candidates.clear();
            for (int index = 0; index < rows * cols; ++index)
                if (index != safeRow * cols + safeCol) candidates.push_back(index);
        }
        std::uint32_t rng = seed ? seed : 0x6d2b79f5u;
        for (std::size_t remaining = candidates.size(); remaining > 1; --remaining)
        {
            const std::uint32_t bound = static_cast<std::uint32_t>(remaining);
            const std::uint32_t threshold = (0u - bound) % bound;
            std::uint32_t value;
            do { value = Next(rng); } while (value < threshold);
            std::swap(candidates[remaining - 1], candidates[static_cast<std::size_t>(value % bound)]);
        }
        candidates.resize(static_cast<std::size_t>(mineCount));
        return Load(rows, cols, candidates);
    }

    const Cell* At(int row, int col) const
    {
        if (!InBounds(row, col)) return nullptr;
        return &Cells[static_cast<std::size_t>(row * ColCount + col)];
    }

    // Return whether an action changed the board. Invalid and terminal actions are no-ops.
    bool Reveal(int row, int col, std::int64_t elapsedMillis)
    {
        if (CurrentResult != Outcome::Playing || !InBounds(row, col)) return false;
        const int start = row * ColCount + col;
        Cell& first = Cells[static_cast<std::size_t>(start)];
        if (first.Revealed || first.Flagged) return false;
        first.Revealed = true;
        if (first.Mine)
        {
            CurrentResult = Outcome::Lost;
            FinalScore = 0;
            return true;
        }
        if (first.Adjacent == 0)
        {
            std::vector<int> queue{start};
            for (std::size_t next = 0; next < queue.size(); ++next)
            {
                const int index = queue[next];
                Neighbours(index / ColCount, index % ColCount, [&](int neighbourIndex) {
                    Cell& neighbour = Cells[static_cast<std::size_t>(neighbourIndex)];
                    if (neighbour.Revealed || neighbour.Flagged || neighbour.Mine) return;
                    neighbour.Revealed = true;
                    if (neighbour.Adjacent == 0) queue.push_back(neighbourIndex);
                });
            }
        }
        CheckVictory(elapsedMillis);
        return true;
    }

    bool ToggleFlag(int row, int col, std::int64_t elapsedMillis)
    {
        if (CurrentResult != Outcome::Playing || !InBounds(row, col)) return false;
        Cell& cell = Cells[static_cast<std::size_t>(row * ColCount + col)];
        if (cell.Revealed) return false;
        cell.Flagged = !cell.Flagged;
        CheckVictory(elapsedMillis);
        return true;
    }

    int Rows() const { return RowCount; }
    int Cols() const { return ColCount; }
    int MineCount() const { return static_cast<int>(MineIndices.size()); }
    int Score() const { return FinalScore; }
    Outcome Result() const { return CurrentResult; }
    const std::vector<int>& Layout() const { return MineIndices; }
    int RevealedCount() const
    {
        return static_cast<int>(std::count_if(Cells.begin(), Cells.end(),
            [](const Cell& cell) { return cell.Revealed; }));
    }
    int FlagCount() const
    {
        return static_cast<int>(std::count_if(Cells.begin(), Cells.end(),
            [](const Cell& cell) { return cell.Flagged; }));
    }

private:
    int RowCount = 0;
    int ColCount = 0;
    int FinalScore = 0;
    Outcome CurrentResult = Outcome::Playing;
    std::vector<Cell> Cells;
    std::vector<int> MineIndices;

    static bool ValidDimensions(int rows, int cols)
    {
        return rows > 0 && cols > 0 && rows <= MaxDimension && cols <= MaxDimension && rows * cols > 1;
    }
    bool InBounds(int row, int col) const
    {
        return row >= 0 && col >= 0 && row < RowCount && col < ColCount;
    }
    static std::uint32_t Next(std::uint32_t& rng)
    {
        rng ^= rng << 13;
        rng ^= rng >> 17;
        rng ^= rng << 5;
        return rng;
    }
    template <typename Function> void Neighbours(int row, int col, Function visit) const
    {
        for (int dr = -1; dr <= 1; ++dr)
            for (int dc = -1; dc <= 1; ++dc)
                if ((dr || dc) && InBounds(row + dr, col + dc)) visit((row + dr) * ColCount + col + dc);
    }
    void CheckVictory(std::int64_t elapsedMillis)
    {
        int safeHidden = 0;
        int correctFlags = 0;
        bool incorrectFlag = false;
        for (const Cell& cell : Cells)
        {
            if (!cell.Mine && !cell.Revealed) ++safeHidden;
            if (cell.Mine && cell.Flagged) ++correctFlags;
            if (!cell.Mine && cell.Flagged) incorrectFlag = true;
        }
        if (safeHidden == 0 || (correctFlags == MineCount() && correctFlags > 0 && !incorrectFlag))
        {
            CurrentResult = Outcome::Won;
            const std::int64_t penalty = std::max<std::int64_t>(0, elapsedMillis) / 500;
            const std::int64_t base = static_cast<std::int64_t>(MineCount()) * 150;
            FinalScore = static_cast<int>(std::max<std::int64_t>(0, base - penalty));
        }
    }
};

}} // namespace daedalus::minesweeper
