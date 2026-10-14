#!/usr/bin/env python3
"""Extract and EXECUTE pinned Java GameService rule bodies without Spring/JavaFX.

Reads git objects from an existing source checkout; never changes it. Infrastructure
is replaced by no-op seams. Score uses a controlled clock with epoch-aligned start;
the arithmetic and branches are extracted unchanged. RNG bit parity is not claimed.
"""
import argparse
import hashlib
import pathlib
import re
import subprocess
import tempfile

COMMIT = "63156079e141bca2b0cd3a0f297bb6595b28c2d0"
BLOB = "30e6e58ff5d0d3795bb64a209c82342ed227f605"
SOURCE_PATH = "src/main/java/com/xai/minesweeper/service/GameService.java"
METHODS = ("initializeCells", "calculateAdjacentMines", "countAdjacentMines", "isValidCell",
           "revealCell", "handleMineHit", "revealNeighborsBFS", "toggleFlag",
           "validateAndGetCell", "predictGameOutcome", "calculateScore")


def method(source, name):
    match = re.search(r"(?m)^    (?:public|private) [^\n]+\b" + re.escape(name) + r"\(", source)
    if not match:
        raise ValueError("missing source method " + name)
    start = source.index("{", match.start())
    depth, mode, escape = 0, "code", False
    i = start
    while i < len(source):
        char, nxt = source[i], source[i:i + 2]
        if mode == "line":
            if char == "\n":
                mode = "code"
        elif mode == "comment":
            if nxt == "*/":
                mode = "code"
                i += 1
        elif mode in ("string", "char"):
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == ('"' if mode == "string" else "'"):
                mode = "code"
        elif nxt == "//":
            mode = "line"
            i += 1
        elif nxt == "/*":
            mode = "comment"
            i += 1
        elif char == '"':
            mode = "string"
        elif char == "'":
            mode = "char"
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return source[match.start():i + 1]
        i += 1
    raise ValueError("unclosed source method " + name)


HARNESS = r'''
import java.time.*;
import java.util.*;
public class MinesweeperSourceOracle {
    private Board board;
    private long oracleNowMillis;
    private final Analytics analyticsService = new Analytics();
    private final Solver aiSolverService = new Solver();
    private final Leaderboard leaderboardService = new Leaderboard();
    private Board getBoard(String id) { return board; }
    private void validateStateHash(Board b) {}
    private void logEvent(Board b, String message, int x, int y) {}
    private void updateBoardState(Board b) {}
    private void broadcastGameUpdate(Board b, String message, List<String> players) {}
    private List<String> getPlayers(String id) { return Collections.emptyList(); }
    static class Analytics { void trackLiveMove(String a, String b, String c, int x, int y) {} }
    static class Solver { String getNextMove(Board b, double risk) { return ""; } }
    static class Leaderboard { void onGameEnd(Board b) {} }
    static class GameCell {
        int x, y, adjacent; boolean mine, revealed, flagged;
        void setGameId(String value) {}
        void setX(int value) { x = value; } int getX() { return x; }
        void setY(int value) { y = value; } int getY() { return y; }
        void setMine(boolean value) { mine = value; } boolean isMine() { return mine; }
        void setRevealed(boolean value) { revealed = value; } boolean isRevealed() { return revealed; }
        void setFlagged(boolean value) { flagged = value; } boolean isFlagged() { return flagged; }
        void setAdjacentMines(int value) { adjacent = value; } int getAdjacentMines() { return adjacent; }
        void setPenciled(boolean value) {} void setPencilProbability(double value) {}
    }
    static class Board {
        int rows, cols, mines, score, lives;
        boolean gameOver, won, challenge, shield;
        List<GameCell> cells;
        int getRows() { return rows; } int getCols() { return cols; }
        int getNumMines() { return mines; } int getLives() { return lives; }
        void setLives(int value) { lives = value; }
        boolean isGameOver() { return gameOver; } void setGameOver(boolean value) { gameOver = value; }
        boolean hasWon() { return won; } void setWon(boolean value) { won = value; }
        void setScore(int value) { score = value; }
        boolean isChallengeMode() { return challenge; } boolean isShielded() { return shield; }
        String getGameId() { return "fixture"; } String getPlayerId() { return "fixture-player"; }
        String getUniverse() { return "prime"; }
        LocalDateTime getStartTime() { return LocalDateTime.ofEpochSecond(0, 0, ZoneOffset.UTC); }
        List<GameCell> getCells() { return cells; }
        void invalidateCellMap() {}
        GameCell getCell(int x, int y) { return cells.get(x * cols + y); }
    }
    // SOURCE_METHODS
    private String state() {
        StringBuilder out = new StringBuilder();
        int revealed = 0, flags = 0;
        for (GameCell c : board.cells) {
            if (c.revealed) revealed++;
            if (c.flagged) flags++;
            out.append(c.mine ? 1 : 0).append(c.revealed ? 1 : 0)
                .append(c.flagged ? 1 : 0).append(c.adjacent);
        }
        return (board.won ? "Won" : board.gameOver ? "Lost" : "Playing") + " "
            + board.score + " " + revealed + " " + flags + " " + out;
    }
    private void start(String name, int rows, int cols, int[] mines) {
        board = new Board(); board.rows = rows; board.cols = cols; board.mines = mines.length;
        board.cells = initializeCells(rows, cols, "fixture");
        for (int index : mines) board.cells.get(index).setMine(true);
        calculateAdjacentMines(board);
        StringBuilder line = new StringBuilder("case " + name + " " + rows + " " + cols + " " + mines.length);
        for (int index : mines) line.append(" ").append(index);
        System.out.println(line); System.out.println("state " + state());
    }
    private void action(String verb, int row, int col, long elapsed) {
        String before = state(); oracleNowMillis = elapsed;
        try {
            if (verb.equals("reveal")) revealCell("fixture", row, col);
            else toggleFlag("fixture", row, col);
        } catch (IllegalArgumentException expectedBoundsRejection) {
            // C++ exposes false rather than Java's exception, but rejected state is identical.
        }
        String after = state();
        System.out.println("action " + verb + " " + row + " " + col + " " + elapsed + " "
            + (before.equals(after) ? 0 : 1) + " " + after);
    }
    public static void main(String[] args) {
        MinesweeperSourceOracle o = new MinesweeperSourceOracle();
        // SOURCE_CASES
    }
}
'''

# Inputs only: expected snapshots are produced by executing the original Java branches.
CASES = [
    ("flood_flag_barrier", 4, 4, [15], [("flag", 0, 0, 0), ("reveal", 0, 1, 0),
        ("reveal", 0, 0, 0), ("flag", 3, 3, 2500), ("flag", 0, 0, 2500),
        ("reveal", 0, 0, 3000), ("flag", 3, 3, 3000)]),
    ("all_safe_revealed", 3, 3, [0, 8], [("reveal", r, c, 1000) for r in range(3) for c in range(3)
        if r * 3 + c not in (0, 8)] + [("reveal", 0, 0, 2000)]),
    ("incorrect_flag_blocks_win", 3, 3, [0, 8], [("flag", 0, 1, 0), ("flag", 0, 0, 0),
        ("flag", 2, 2, 499), ("flag", 0, 1, 500), ("flag", 0, 0, 900)]),
    ("mine_loss", 3, 3, [0], [("reveal", 0, 0, 0), ("reveal", 2, 2, 0),
        ("flag", 0, 0, 0), ("reveal", -1, 0, 0)]),
    ("score_499ms", 2, 2, [0], [("flag", 0, 0, 499)]),
    ("score_500ms", 2, 2, [0], [("flag", 0, 0, 500)]),
    ("score_clamped_zero", 2, 2, [0], [("flag", 0, 0, 75000)]),
    ("score_negative_time", 2, 2, [0], [("flag", 0, 0, -500)]),
    ("dense_safe_win", 2, 2, [0, 1, 2], [("reveal", 1, 1, 1000), ("flag", 0, 0, 1000)]),
    ("invalid_and_noop", 3, 3, [0, 8], [("reveal", -1, 0, 0), ("flag", 3, 0, 0),
        ("reveal", 1, 1, 0), ("reveal", 1, 1, 0), ("flag", 1, 1, 0),
        ("flag", 0, 0, 0), ("reveal", 0, 0, 0), ("flag", 0, 0, 0)]),
    ("non_square_edges", 2, 5, [0, 9], [("reveal", 0, 2, 1500),
        ("flag", 0, 0, 1500), ("flag", 1, 4, 1500)]),
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-repo", required=True, help="read-only original Minesweeper checkout")
    parser.add_argument("--output", type=pathlib.Path, default=pathlib.Path(__file__).with_name("minesweeper_parity.txt"))
    args = parser.parse_args()
    raw = subprocess.check_output(["git", "--git-dir", str(pathlib.Path(args.source_repo) / ".git"),
                                   "show", "HEAD:" + SOURCE_PATH])
    actual = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
    if actual != BLOB:
        raise SystemExit("Refusing unverified source blob: " + actual + "; expected " + BLOB)
    source = raw.decode("utf-8")
    bodies = "\n\n".join(method(source, name) for name in METHODS)
    if bodies.count("System.currentTimeMillis()") != 2:
        raise SystemExit("Controlled-clock seam no longer matches pinned source")
    bodies = bodies.replace("System.currentTimeMillis()", "oracleNowMillis")
    invocations = []
    for name, rows, cols, mines, actions in CASES:
        invocations.append('o.start("%s", %d, %d, new int[]{%s});' % (name, rows, cols, ",".join(map(str, mines))))
        for verb, row, col, elapsed in actions:
            invocations.append('o.action("%s", %d, %d, %dL);' % (verb, row, col, elapsed))
    java = HARNESS.replace("// SOURCE_METHODS", bodies).replace("// SOURCE_CASES", "\n        ".join(invocations))
    with tempfile.TemporaryDirectory(prefix="daedalus-minesweeper-oracle-") as temporary:
        directory = pathlib.Path(temporary)
        java_path = directory / "MinesweeperSourceOracle.java"
        java_path.write_text(java, encoding="utf-8")
        subprocess.run(["javac", "-encoding", "UTF-8", str(java_path)], check=True)
        result = subprocess.check_output(["java", "-cp", str(directory), "MinesweeperSourceOracle"], text=True)
    header = ("# Executed Java source oracle, not hand-written expected rule logic.\n"
              "# Source RicheyWorks/minesweeper-pro commit " + COMMIT + "\n"
              "# GameService.java blob " + BLOB + "\n"
              "# Fixed layouts, challenge=false, shield=false, controlled epoch-aligned clock.\n"
              "# cell encoding per row-major cell: mine,revealed,flagged,adjacent (four digits).\n")
    args.output.write_text(header + result, encoding="utf-8", newline="\n")
    print("Executed " + str(len(METHODS)) + " extracted Java methods; " + str(len(CASES))
          + " fixtures and " + str(sum(len(case[4]) for case in CASES)) + " actions written to " + str(args.output))


if __name__ == "__main__":
    main()
