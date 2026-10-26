// SPDX-License-Identifier: MIT
#include "JavaArcade/DaedalusJavaArcadeProtocol.h"
#include <iostream>

namespace JA = daedalus::java_arcade;
static unsigned Checks = 0;
static unsigned Failures = 0;
static void Check(bool Good, const char* What)
{
    ++Checks;
    if (!Good) { ++Failures; std::cerr << "FAILED: " << What << '\n'; }
}
static JA::SudokuView Board(const std::string& Id = "saved-board")
{
    JA::SudokuView V;
    V.GameId = Id;
    V.Owner = "player-one";
    V.Difficulty = 3;
    V.Lives = 2;
    V.ElapsedSeconds = 123;
    V.Values[0] = 8;
    V.Givens[0] = true;
    V.Values[80] = 1;
    V.PencilMasks[40] = (1 << 2) | (1 << 7);
    return V;
}
static void Refused(const std::vector<JA::SudokuView>& Boards, const std::string& Owner, const char* What)
{
    JA::SudokuSavedGame Existing;
    Existing.GameId = "previous-valid-list";
    Existing.FilledCells = 17;
    std::vector<JA::SudokuSavedGame> Output{Existing};
    Check(!JA::ProjectSavedSudokuGames(Boards, Owner, Output), What);
    Check(Output.size() == 1 && Output[0].GameId == Existing.GameId
        && Output[0].FilledCells == 17, "refused list retains previous metadata atomically");
}
int main()
{
    Check(JA::PayloadFits(JA::SessionGuard::MaxPayloadBytes + 1, JA::SudokuSavedListMaxPayloadBytes),
        "list response budget accommodates multiple boards beyond the single-board cap");
    Check(JA::PayloadFits(JA::SudokuSavedListMaxPayloadBytes, JA::SudokuSavedListMaxPayloadBytes),
        "aggregate response accepts its exact bound");
    Check(!JA::PayloadFits(JA::SudokuSavedListMaxPayloadBytes + 1, JA::SudokuSavedListMaxPayloadBytes)
        && !JA::PayloadFits(0, JA::SudokuSavedListMaxPayloadBytes), "empty and oversized list payloads refused");
    const JA::SudokuView Input = Board();
    std::vector<JA::SudokuView> Source{Input};
    std::vector<JA::SudokuSavedGame> Output;
    Check(JA::ProjectSavedSudokuGames(Source, Input.Owner, Output), "owned full board projects");
    Check(Output.size() == 1 && Output[0].GameId == Input.GameId, "metadata keeps explicit resume ID");
    Check(Output.size() == 1 && Output[0].Difficulty == 3 && Output[0].Lives == 2
        && Output[0].ElapsedSeconds == 123, "metadata carries authoritative difficulty lives and elapsed time");
    Check(Output.size() == 1 && Output[0].FilledCells == 2 && Output[0].GivensCount == 1,
        "filled cells count values while pencil marks do not count as filled");
    Check(Source.size() == 1 && Source[0].Values == Input.Values && Source[0].Givens == Input.Givens
        && Source[0].PencilMasks == Input.PencilMasks && Source[0].GameId == Input.GameId,
        "projection preserves source board");
    Check(JA::ProjectSavedSudokuGames({}, Input.Owner, Output) && Output.empty(), "successful empty list clears old metadata");

    Refused({}, "", "empty authenticated identity refused");
    Refused({}, std::string(129, 'x'), "oversized authenticated identity refused");
    Refused({}, std::string("player-one\0other", 16), "embedded nul identity refused");
    Refused({Input}, "another-player", "foreign board refused");
    auto Invalid = Input;
    Invalid.GameId = "foreign-later";
    Invalid.Owner = "another-player";
    Refused({Input, Invalid}, Input.Owner, "foreign later row refuses entire list");
    Refused({Input, Input}, Input.Owner, "duplicate game ID refused");
    Invalid = Input;
    Invalid.GameId = std::string("saved-board\0other", 17);
    Refused({Invalid}, Input.Owner, "embedded nul game ID refused");
    Invalid = Input;
    Invalid.GameId = "bad-cell-later";
    Invalid.Values[80] = 10;
    Refused({Input, Invalid}, Input.Owner, "invalid later board cell refused");
    Invalid = Input;
    Invalid.Givens[40] = true;
    Refused({Invalid}, Input.Owner, "blank given refused");
    Invalid = Input;
    Invalid.ElapsedSeconds = -1;
    Refused({Invalid}, Input.Owner, "invalid board clock refused");
    Invalid = Input;
    Invalid.PencilMasks[0] = 1;
    Refused({Invalid}, Input.Owner, "invalid pencil mark refused");
    Invalid = Input;
    Invalid.Solved = Invalid.TimeUp = true;
    Refused({Invalid}, Input.Owner, "contradictory terminal flags refused");

    std::vector<JA::SudokuView> Bounded;
    for (std::size_t I = 0; I < JA::SudokuSavedListLimit; ++I)
        Bounded.push_back(Board("board-" + std::to_string(I)));
    Check(JA::ProjectSavedSudokuGames(Bounded, Input.Owner, Output)
        && Output.size() == JA::SudokuSavedListLimit, "documented request limit accepted");
    Check(Output.size() == JA::SudokuSavedListLimit && Output.front().GameId == "board-0"
        && Output.back().GameId == "board-9", "service order retained without inventing chronology");
    Bounded.push_back(Board("overflow"));
    Refused(Bounded, Input.Owner, "oversized list refused without truncation");

    auto Won = Board("won");
    Won.Solved = true;
    auto Expired = Board("expired");
    Expired.TimeUp = true;
    Check(JA::ProjectSavedSudokuGames({Won, Expired}, Input.Owner, Output), "terminal saves remain discoverable");
    Check(Output.size() == 2 && Output[0].Solved && !Output[0].TimeUp
        && !Output[1].Solved && Output[1].TimeUp, "terminal status retained independently");
    std::cout << Checks - Failures << '/' << Checks << " saved Sudoku checks passed\n";
    return Failures == 0 ? 0 : 1;
}
