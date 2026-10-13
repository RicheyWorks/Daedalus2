"""Validate authored Sudoku wire fixtures; does not run Java/native/network code."""
import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FIXTURES = ROOT / "sudoku-wire-fixtures.json"
EVIDENCE = ROOT / "sudoku-source-evidence.json"
INT32_MAX = 2**31 - 1
SAFE_INTEGER_MAX = 2**53 - 1
REQUIRED_BOARD = {
    "gameId", "playerId", "difficulty", "chaosMode", "mirrorMode", "solved",
    "lives", "score", "hintCount", "moveCount", "elapsedSeconds",
    "timeLimitSeconds", "secondsLeft", "timeUp", "cells",
}
REQUIRED_CELL = {
    "value", "isGiven", "lastModified", "moveSource", "pencilMarks",
    "conflicts", "hintStrength", "strategy", "isEditable", "playerId", "displayColor",
}


def integer(value, low, high):
    return type(value) is int and low <= value <= high


def secret_property(value):
    if isinstance(value, dict):
        return any(key.casefold() in ("solution", "solvedgrid") or secret_property(item)
                   for key, item in value.items())
    if isinstance(value, list):
        return any(secret_property(item) for item in value)
    return False


def native_policy_accepts(board, policy):
    """Proposed DTO policy; performs no Sudoku legality, generation or scoring."""
    encoded = json.dumps(board, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    if len(encoded) > policy["maxResponseBytes"] or secret_property(board):
        return False
    if not isinstance(board, dict) or not REQUIRED_BOARD <= board.keys():
        return False
    if (not isinstance(board["gameId"], str)
            or not 1 <= len(board["gameId"]) <= policy["maxGameIdCharacters"]
            or board["gameId"] != policy["expectedGameId"]
            or board["playerId"] != policy["expectedPlayerId"]):
        return False
    if not integer(board["difficulty"], 1, 5):
        return False
    if any(type(board[key]) is not bool for key in
           ("chaosMode", "mirrorMode", "solved", "timeUp")):
        return False
    if board["solved"] and board["timeUp"]:
        return False
    if any(not integer(board[key], 0, INT32_MAX) for key in
           ("lives", "score", "hintCount", "moveCount")):
        return False
    if any(not integer(board[key], 0, SAFE_INTEGER_MAX) for key in
           ("elapsedSeconds", "timeLimitSeconds", "secondsLeft")):
        return False
    if board["secondsLeft"] > board["timeLimitSeconds"]:
        return False
    cells = board["cells"]
    if not isinstance(cells, list) or len(cells) != 9:
        return False
    for row in cells:
        if not isinstance(row, list) or len(row) != 9:
            return False
        for cell in row:
            if not isinstance(cell, dict) or not REQUIRED_CELL <= cell.keys():
                return False
            if not integer(cell["value"], 0, 9):
                return False
            if any(type(cell[key]) is not bool for key in ("isGiven", "isEditable")):
                return False
            if cell["isGiven"] and cell["value"] == 0:
                return False
            if not integer(cell["lastModified"], 0, SAFE_INTEGER_MAX):
                return False
            if not integer(cell["hintStrength"], 0, 3):
                return False
            for key in ("pencilMarks", "conflicts"):
                items = cell[key]
                if (not isinstance(items, list) or len(items) > 9
                        or any(not integer(value, 1, 9) for value in items)):
                    return False
            if not isinstance(cell["moveSource"], str) or len(cell["moveSource"]) > 32:
                return False
            if cell["strategy"] is not None and (
                    not isinstance(cell["strategy"], str) or len(cell["strategy"]) > 64):
                return False
            if cell["playerId"] is not None and (
                    not isinstance(cell["playerId"], str) or len(cell["playerId"]) > 256):
                return False
            if not isinstance(cell["displayColor"], str) or len(cell["displayColor"]) > 64:
                return False
    return True


def patch(board, operation):
    parts = [part.replace("~1", "/").replace("~0", "~")
             for part in operation["path"].split("/")[1:]]
    cursor = board
    for part in parts[:-1]:
        cursor = cursor[int(part)] if isinstance(cursor, list) else cursor[part]
    key = int(parts[-1]) if isinstance(cursor, list) else parts[-1]
    if operation["op"] == "remove":
        del cursor[key]
    elif operation["op"] in ("replace", "add"):
        cursor[key] = copy.deepcopy(operation["value"])
    else:
        raise AssertionError("Unsupported authored patch")


def main():
    fixtures = json.loads(FIXTURES.read_text(encoding="utf-8"))
    evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert fixtures["meta"]["synthetic"] is True
    assert fixtures["meta"]["sourceCommit"] == evidence["sourceCommit"]
    assert REQUIRED_BOARD == set(evidence["boardFields"])
    assert REQUIRED_CELL == set(evidence["cellFields"])
    assert not any("solution" in key.casefold() or "solvedgrid" in key.casefold()
                   for key in evidence["boardFields"])
    assert all(check["passed"] is True for check in evidence["sourceChecks"])
    policy = fixtures["policy"]
    for name, board in fixtures["boards"].items():
        assert native_policy_accepts(board, policy), "Invalid authored base " + name
        assert not secret_property(board)
    matrix = fixtures["boardValidationCases"]
    ids = [case["id"] for case in matrix]
    assert len(ids) == len(set(ids))
    for case in matrix:
        board = copy.deepcopy(fixtures["boards"][case["base"]])
        for operation in case["patches"]:
            patch(board, operation)
        actual = native_policy_accepts(board, policy)
        assert actual == case["expectAccepted"], (
            case["id"] + " expected " + str(case["expectAccepted"]) + ", got " + str(actual))
    for item in fixtures["wsCommands"]:
        message = item["message"]
        assert "from" not in message
        assert message["type"] in ("move", "undo", "redo", "sync")
        if message["type"] == "move":
            move = message["payload"]
            assert set(move) == {"row", "col", "oldVal", "newVal"}
            assert all(integer(move[key], 0, 8) for key in ("row", "col"))
            assert all(integer(move[key], 0, 9) for key in ("oldVal", "newVal"))
    print(f"Fixture policy matrix: {len(matrix)}/{len(matrix)} passed")
    print(f"Pinned source assertions recorded: {len(evidence['sourceChecks'])}")
    print("Java tests, native adapter tests and network acceptance were not run.")


if __name__ == "__main__":
    main()

