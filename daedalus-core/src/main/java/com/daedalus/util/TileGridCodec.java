// SPDX-License-Identifier: MIT

package com.daedalus.util;

/**
 * Run-length codec for the rendered tile grid that the REST and STOMP surfaces ship as
 * {@code char[][]} (CLRS Ch. 32 territory — encoding a symbol stream compactly).
 *
 * <p>Wire format: {@code <rows>x<cols>:} followed by row-major runs, each written as an optional
 * decimal count followed by the glyph. A missing count means one. Because
 * {@link com.daedalus.model.TileType}'s glyphs ({@code # ' ' S G @ . o ?}) are never digits, the
 * stream parses without separators or escapes: read digits (if any) for the count, then take the
 * next character as the glyph.
 *
 * <p>Runs may span row boundaries, which is where most of the saving comes from — the solid border
 * rows of a maze collapse into single runs. Because a run of one is emitted as the bare glyph, the
 * encoding never expands the payload beyond the raw grid plus the short header.
 *
 * <p><b>What this does and doesn't buy you.</b> A rendered maze alternates between cells and walls
 * at every other column, which is close to the worst case for run-length coding, so expect a
 * modest saving rather than a dramatic one — the long runs live mainly in border and corridor
 * stretches. If the wire payload really matters, the bigger win is not compressing this grid but
 * not sending it: the rendered grid is {@code (2r+1) x (2c+1)}, roughly four times the cell count,
 * and the underlying maze is only two wall bits per cell. Send those and render client-side.
 */
public final class TileGridCodec {

    private TileGridCodec() {
    }

    /** Encode a rectangular glyph grid. */
    public static String encode(char[][] grid) {
        int rows = grid.length;
        int cols = rows == 0 ? 0 : grid[0].length;
        StringBuilder out = new StringBuilder(64);
        out.append(rows).append('x').append(cols).append(':');
        if (rows == 0 || cols == 0) {
            return out.toString();
        }

        char run = grid[0][0];
        int length = 0;
        for (int r = 0; r < rows; r++) {
            if (grid[r].length != cols) {
                throw new IllegalArgumentException(
                        "Grid must be rectangular; row " + r + " has " + grid[r].length + " columns, expected " + cols);
            }
            for (int c = 0; c < cols; c++) {
                char glyph = grid[r][c];
                if (glyph == run) {
                    length++;
                } else {
                    appendRun(out, run, length);
                    run = glyph;
                    length = 1;
                }
            }
        }
        appendRun(out, run, length);
        return out.toString();
    }

    /** Decode a string produced by {@link #encode}. */
    public static char[][] decode(String encoded) {
        int cursor = encoded.indexOf('x');
        int colon = encoded.indexOf(':');
        if (cursor < 0 || colon < cursor) {
            throw new IllegalArgumentException("Malformed tile grid header, expected <rows>x<cols>: — got: " + encoded);
        }
        int rows = parseInt(encoded.substring(0, cursor), encoded);
        int cols = parseInt(encoded.substring(cursor + 1, colon), encoded);

        char[][] grid = new char[rows][cols];
        int cell = 0;
        int total = rows * cols;
        int i = colon + 1;
        while (i < encoded.length()) {
            int count = 0;
            boolean hadDigits = false;
            while (i < encoded.length() && isDigit(encoded.charAt(i))) {
                count = count * 10 + (encoded.charAt(i) - '0');
                hadDigits = true;
                i++;
            }
            if (i >= encoded.length()) {
                throw new IllegalArgumentException("Malformed run: count with no glyph at end of input");
            }
            if (!hadDigits) {
                count = 1;
            }
            char glyph = encoded.charAt(i++);
            if (cell + count > total) {
                throw new IllegalArgumentException(
                        "Runs overflow the declared " + rows + "x" + cols + " grid");
            }
            for (int k = 0; k < count; k++) {
                grid[(cell + k) / cols][(cell + k) % cols] = glyph;
            }
            cell += count;
        }
        if (cell != total) {
            throw new IllegalArgumentException(
                    "Runs cover " + cell + " cells but the header declares " + total);
        }
        return grid;
    }

    private static void appendRun(StringBuilder out, char glyph, int length) {
        if (length <= 0) {
            return;
        }
        if (length > 1) {
            out.append(length);
        }
        out.append(glyph);
    }

    private static boolean isDigit(char c) {
        return c >= '0' && c <= '9';
    }

    private static int parseInt(String text, String whole) {
        if (text.isEmpty()) {
            throw new IllegalArgumentException("Malformed tile grid header in: " + whole);
        }
        for (int i = 0; i < text.length(); i++) {
            if (!isDigit(text.charAt(i))) {
                throw new IllegalArgumentException("Malformed tile grid header in: " + whole);
            }
        }
        return Integer.parseInt(text);
    }
}
