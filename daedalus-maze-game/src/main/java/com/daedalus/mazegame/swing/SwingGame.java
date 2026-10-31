// SPDX-License-Identifier: MIT

package com.daedalus.mazegame.swing;

import com.daedalus.mazegame.BestScores;
import com.daedalus.mazegame.DailySeed;
import com.daedalus.mazegame.Difficulty;
import com.daedalus.mazegame.MazeFactory;
import com.daedalus.mazegame.MazeRun;
import com.daedalus.mazegame.Scoring;
import com.daedalus.mazegame.ShareCode;
import com.daedalus.mazegame.Skin;
import com.daedalus.model.Direction;
import com.daedalus.model.Point;

import java.awt.BorderLayout;
import java.awt.Color;
import java.awt.Dimension;
import java.awt.Font;
import java.awt.Graphics;
import java.awt.Graphics2D;
import java.awt.RenderingHints;
import java.awt.event.KeyAdapter;
import java.awt.event.KeyEvent;
import java.io.IOException;
import java.time.Clock;
import java.util.List;
import java.util.Locale;
import java.util.Optional;
import javax.swing.JFrame;
import javax.swing.JLabel;
import javax.swing.JOptionPane;
import javax.swing.JPanel;
import javax.swing.SwingUtilities;
import javax.swing.Timer;

/**
 * Swing window (JDK only, nothing to install). Arrows/WASD move, H hint, G ghost replay after a
 * win, K cycle skin, 1-4 difficulty, N new random seed, D daily, C enter share code, Esc quit.
 * Thin shell over {@link MazeRun}; excluded from coverage like the other launch-only hosts.
 */
public final class SwingGame extends JPanel {

    private static final long serialVersionUID = 1L;
    private static final int VIEW = 720;

    private final transient MazeFactory factory;
    private final transient BestScores best;
    private final JLabel hud = new JLabel(" ");
    private transient MazeRun run;
    private transient List<Point> trail = List.of();
    private transient List<Point> ghost = List.of();
    private int ghostStep;
    private Skin skin = Skin.LUMEN_SLATE;
    private long startNanos;
    private long finishMillis = -1;

    private SwingGame(long seed, Difficulty difficulty, MazeFactory factory, BestScores best) {
        this.factory = factory;
        this.best = best;
        setPreferredSize(new Dimension(VIEW, VIEW));
        setFocusable(true);
        addKeyListener(new KeyAdapter() {
            @Override
            public void keyPressed(KeyEvent e) {
                onKey(e);
            }
        });
        hud.setFont(new Font(Font.MONOSPACED, Font.PLAIN, 13));
        start(seed, difficulty);
        new Timer(100, e -> tick()).start();
    }

    public static void launch(long seed, Difficulty difficulty, MazeFactory factory) throws IOException {
        BestScores best = new BestScores(BestScores.defaultFile());
        SwingUtilities.invokeLater(() -> {
            SwingGame game = new SwingGame(seed, difficulty, factory, best);
            JFrame f = new JFrame("Labyrinth Run");
            f.setDefaultCloseOperation(JFrame.EXIT_ON_CLOSE);
            f.getContentPane().add(game, BorderLayout.CENTER);
            f.getContentPane().add(game.hud, BorderLayout.SOUTH);
            f.pack();
            f.setLocationRelativeTo(null);
            f.setVisible(true);
            game.requestFocusInWindow();
        });
    }

    private void start(long seed, Difficulty difficulty) {
        run = new MazeRun(seed, difficulty, factory);
        trail = List.of();
        ghost = List.of();
        ghostStep = 0;
        finishMillis = -1;
        startNanos = System.nanoTime();
        refresh();
    }

    private long elapsed() {
        return finishMillis >= 0 ? finishMillis : (System.nanoTime() - startNanos) / 1_000_000L;
    }

    private void tick() {
        if (!ghost.isEmpty() && ghostStep < ghost.size()) {
            ghostStep++;
        }
        refresh();
    }

    private void onKey(KeyEvent e) {
        switch (e.getKeyCode()) {
            case KeyEvent.VK_UP, KeyEvent.VK_W -> step(Direction.NORTH);
            case KeyEvent.VK_DOWN, KeyEvent.VK_S -> step(Direction.SOUTH);
            case KeyEvent.VK_LEFT, KeyEvent.VK_A -> step(Direction.WEST);
            case KeyEvent.VK_RIGHT -> step(Direction.EAST);
            case KeyEvent.VK_D -> {
                if (e.isShiftDown()) {
                    start(DailySeed.today(Clock.systemUTC()), run.difficulty());
                } else {
                    step(Direction.EAST);
                }
            }
            case KeyEvent.VK_H -> {
                if (!run.isWon()) {
                    trail = run.hint(5);
                }
            }
            case KeyEvent.VK_G -> {
                if (run.isWon()) {
                    ghost = run.ghost("tremaux");
                    ghostStep = 0;
                }
            }
            case KeyEvent.VK_K -> skin = skin.next();
            case KeyEvent.VK_1 -> start(run.seed(), Difficulty.EASY);
            case KeyEvent.VK_2 -> start(run.seed(), Difficulty.NORMAL);
            case KeyEvent.VK_3 -> start(run.seed(), Difficulty.HARD);
            case KeyEvent.VK_4 -> start(run.seed(), Difficulty.BRUTAL);
            case KeyEvent.VK_N -> start(System.nanoTime() & 0xFFFFFFFL, run.difficulty());
            case KeyEvent.VK_C -> askCode();
            case KeyEvent.VK_ESCAPE -> System.exit(0);
            default -> { }
        }
        refresh();
    }

    private void askCode() {
        String text = JOptionPane.showInputDialog(this, "Share code (e.g. LR-H-1KQ3Z)", run.shareCode().encode());
        if (text == null || text.isBlank()) {
            return;
        }
        try {
            ShareCode sc = ShareCode.parse(text);
            start(sc.seed(), sc.difficulty());
        } catch (IllegalArgumentException ex) {
            JOptionPane.showMessageDialog(this, ex.getMessage());
        }
    }

    private void step(Direction d) {
        if (run.move(d)) {
            trail = List.of();
            if (run.isWon() && finishMillis < 0) {
                finishMillis = elapsed();
                try {
                    best.record(run.shareCode().encode(), run.score(finishMillis), run.stars(finishMillis), run.moves(),
                            finishMillis);
                } catch (IOException ex) {
                    hud.setText("Could not save best score: " + ex.getMessage());
                }
            }
        }
    }

    private void refresh() {
        long ms = elapsed();
        Optional<Integer> b = best.best(run.shareCode().encode());
        String status = run.isWon()
                ? String.format(Locale.ROOT, "ESCAPED %d star(s) score %d  [G ghost]", run.stars(ms), run.score(ms))
                : "[H hint  K skin  1-4 tier  N new  Shift+D daily  C code]";
        hud.setText(String.format(Locale.ROOT, " %s  %s  moves %d/%d  %.1fs/%.1fs  best %s  %s  %s", run.shareCode(),
                run.difficulty(), run.moves(), run.par(), ms / 1000.0, Scoring.parMillis(run.par()) / 1000.0,
                b.map(String::valueOf).orElse("-"), skin.label(), status));
        repaint();
    }

    @Override
    protected void paintComponent(Graphics g0) {
        super.paintComponent(g0);
        Graphics2D g = (Graphics2D) g0;
        g.setRenderingHint(RenderingHints.KEY_ANTIALIASING, RenderingHints.VALUE_ANTIALIAS_ON);
        int n = run.size();
        int cell = Math.max(4, Math.min(getWidth(), getHeight()) / (n + 1));
        int ox = (getWidth() - cell * n) / 2;
        int oy = (getHeight() - cell * n) / 2;
        g.setColor(new Color(skin.fog()));
        g.fillRect(0, 0, getWidth(), getHeight());
        for (int r = 0; r < n; r++) {
            for (int c = 0; c < n; c++) {
                if (!run.isVisible(r, c)) {
                    continue;
                }
                int x = ox + c * cell;
                int y = oy + r * cell;
                g.setColor(new Color(skin.floor()));
                g.fillRect(x, y, cell, cell);
                g.setColor(new Color(skin.wall()));
                if (!run.isOpen(r, c, Direction.NORTH)) {
                    g.drawLine(x, y, x + cell, y);
                }
                if (!run.isOpen(r, c, Direction.WEST)) {
                    g.drawLine(x, y, x, y + cell);
                }
                if (!run.isOpen(r, c, Direction.EAST)) {
                    g.drawLine(x + cell, y, x + cell, y + cell);
                }
                if (!run.isOpen(r, c, Direction.SOUTH)) {
                    g.drawLine(x, y + cell, x + cell, y + cell);
                }
            }
        }
        g.setColor(new Color(skin.hint()));
        for (Point p : trail) {
            g.fillOval(ox + p.col() * cell + cell / 3, oy + p.row() * cell + cell / 3, cell / 3 + 1, cell / 3 + 1);
        }
        for (int i = 0; i < Math.min(ghostStep, ghost.size()); i++) {
            Point p = ghost.get(i);
            g.fillRect(ox + p.col() * cell + cell / 4, oy + p.row() * cell + cell / 4, cell / 2, cell / 2);
        }
        Point exit = run.exit();
        if (run.isVisible(exit.row(), exit.col())) {
            g.setColor(new Color(skin.exit()));
            g.fillRect(ox + exit.col() * cell + 2, oy + exit.row() * cell + 2, cell - 3, cell - 3);
        }
        Point me = run.position();
        g.setColor(new Color(skin.runner()));
        g.fillOval(ox + me.col() * cell + 2, oy + me.row() * cell + 2, cell - 3, cell - 3);
    }
}
