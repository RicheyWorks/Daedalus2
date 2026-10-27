// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.HashMap;
import java.util.Map;
import org.junit.jupiter.api.Test;

class DeckCrawlerTest {

    /** Naive map simulation, cells keyed by packed coordinates. */
    private static Map<Long, Integer> naive(String rule, int n, int[] ant) {
        Map<Long, Integer> m = new HashMap<>();
        int x = 0;
        int y = 0;
        int d = 0;
        int[] dx = {0, 1, 0, -1};
        int[] dy = {-1, 0, 1, 0};
        for (int k = 0; k < n; k++) {
            long key = ((long) x << 32) ^ (y & 0xffffffffL);
            int c = m.getOrDefault(key, 0);
            d = rule.charAt(c) == 'R' ? (d + 1) % 4 : (d + 3) % 4;
            int nc = (c + 1) % rule.length();
            if (nc == 0) {
                m.remove(key);
            } else {
                m.put(key, nc);
            }
            x += dx[d];
            y += dy[d];
        }
        ant[0] = x;
        ant[1] = y;
        ant[2] = d;
        return m;
    }

    @Test
    void matchesNaiveForSeveralRules() {
        for (String rule : new String[] {"RL", "LR", "RLR", "LLRR", "RRLL", "LRRRRRLLR"}) {
            for (int n : new int[] {0, 1, 7, 500, 3000}) {
                int[] ant = new int[3];
                Map<Long, Integer> m = naive(rule, n, ant);
                DeckCrawler c = new DeckCrawler(rule, 201);
                c.run(n);
                assertThat(c.painted()).as("%s n=%d", rule, n).isEqualTo(m.size());
                assertThat(c.x() - 100).isEqualTo(ant[0]);
                assertThat(c.y() - 100).isEqualTo(ant[1]);
                assertThat(c.dir()).isEqualTo(ant[2]);
                for (Map.Entry<Long, Integer> e : m.entrySet()) {
                    int px = (int) (e.getKey() >> 32) + 100;
                    int py = (int) (long) e.getKey() + 100;
                    assertThat(c.colour(px, py)).isEqualTo(e.getValue());
                }
            }
        }
    }

    @Test
    void reverseReturnsToCleanDeck() {
        for (String rule : new String[] {"RL", "RLR", "LLRR"}) {
            DeckCrawler c = new DeckCrawler(rule, 201);
            c.run(2000);
            byte[] mid = c.snapshot();
            c.run(500);
            for (int k = 0; k < 500; k++) {
                c.back();
            }
            assertThat(c.snapshot()).isEqualTo(mid);
            for (int k = 0; k < 2000; k++) {
                c.back();
            }
            assertThat(c.clean()).isTrue();
            assertThat(c.x()).isEqualTo(100);
            assertThat(c.y()).isEqualTo(100);
            assertThat(c.dir()).isZero();
        }
    }

    @Test
    void langtonHighwayDriftsTwoDiagonalEvery104() {
        DeckCrawler c = new DeckCrawler("RL", 401);
        c.run(11_000);
        int x0 = c.x();
        int y0 = c.y();
        int d0 = c.dir();
        int p0 = c.painted();
        c.run(104);
        assertThat(Math.abs(c.x() - x0)).isEqualTo(2);
        assertThat(Math.abs(c.y() - y0)).isEqualTo(2);
        assertThat(c.dir()).isEqualTo(d0);
        assertThat(c.painted() - p0).isEqualTo(12);
    }

    @Test
    void questAndBounds() {
        int[] ant = new int[3];
        int want = naive("RL", 1000, ant).size();
        assertThat(DeckCrawler.quest(1000, want)).isTrue();
        assertThat(DeckCrawler.quest(1000, want + 1)).isFalse();
        assertThat(DeckCrawler.QUEST_ID).isEqualTo("q_deck_crawler");
        assertThatThrownBy(() -> new DeckCrawler("RX", 9)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new DeckCrawler("R", 9)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new DeckCrawler("RL", 2)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new DeckCrawler("RL", 9).back()).isInstanceOf(IllegalStateException.class);
        assertThatThrownBy(() -> new DeckCrawler("RL", 3).run(100)).isInstanceOf(IllegalStateException.class);
    }
}