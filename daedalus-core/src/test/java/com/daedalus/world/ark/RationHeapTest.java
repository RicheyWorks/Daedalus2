// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.ArrayList;
import java.util.List;
import java.util.NoSuchElementException;
import java.util.SplittableRandom;
import org.junit.jupiter.api.Test;

class RationHeapTest {

    /** Brute force: index of the waiting entry served next (lowest need, then earliest). */
    private static int bruteNext(List<long[]> waiting) {
        int best = 0;
        for (int i = 1; i < waiting.size(); i++) {
            long[] a = waiting.get(i);
            long[] b = waiting.get(best);
            if (a[0] < b[0] || a[0] == b[0] && a[1] < b[1]) {
                best = i;
            }
        }
        return best;
    }

    @Test
    void randomIssueServeRaiseMatchesBruteForce() {
        SplittableRandom rnd = new SplittableRandom(511L);
        RationHeap h = new RationHeap();
        List<long[]> ref = new ArrayList<>();
        List<RationHeap.Ticket> handles = new ArrayList<>();
        long seq = 0;
        for (int step = 0; step < 5000; step++) {
            int op = rnd.nextInt(10);
            if (op < 5 || ref.isEmpty()) {
                long need = rnd.nextInt(50);
                handles.add(h.issue(need, "c" + seq));
                ref.add(new long[] {need, seq++});
            } else if (op < 8) {
                int i = bruteNext(ref);
                RationHeap.Served t = h.serve();
                assertThat(t.need()).isEqualTo(ref.get(i)[0]);
                assertThat(t.name()).isEqualTo("c" + ref.get(i)[1]);
                assertThat(handles.get((int) ref.get(i)[1]).waiting()).isFalse();
                ref.remove(i);
            } else {
                int i = rnd.nextInt(ref.size());
                long[] e = ref.get(i);
                long lower = e[0] - rnd.nextInt(30);
                h.raise(handles.get((int) e[1]), lower);
                e[0] = lower;
            }
            assertThat(h.size()).isEqualTo(ref.size());
            if (!ref.isEmpty()) {
                assertThat(h.peek().name()).isEqualTo("c" + ref.get(bruteNext(ref))[1]);
            }
        }
    }

    @Test
    void mergeCombinesQueuesAndMovesHandles() {
        RationHeap a = new RationHeap();
        RationHeap b = new RationHeap();
        a.issue(5, "Ada");
        a.issue(9, "Bo");
        RationHeap.Ticket cy = b.issue(7, "Cy");
        b.issue(3, "Di");
        a.merge(b);
        assertThat(b.isEmpty()).isTrue();
        assertThat(a.size()).isEqualTo(4);
        a.raise(cy, 1);
        List<String> order = new ArrayList<>();
        while (!a.isEmpty()) {
            order.add(a.serve().name());
        }
        assertThat(order).containsExactly("Cy", "Di", "Ada", "Bo");
        assertThatThrownBy(() -> b.raise(cy, 0)).isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void tiesGoToTheEarlierTicketAndSignReads() {
        RationHeap h = new RationHeap();
        assertThat(h.hatchSign()).contains("hatch closed");
        h.issue(4, "first");
        h.issue(4, "second");
        RationHeap.Ticket third = h.issue(6, "third");
        h.raise(third, 4);
        assertThat(h.hatchSign()).contains("3 waiting").contains("next up first");
        assertThat(h.serve().name()).isEqualTo("first");
        assertThat(h.serve().name()).isEqualTo("second");
        assertThat(h.serve().name()).isEqualTo("third");
        assertThatThrownBy(h::serve).isInstanceOf(NoSuchElementException.class);
        assertThatThrownBy(() -> h.raise(third, 1)).isInstanceOf(IllegalArgumentException.class);
        RationHeap g = new RationHeap();
        RationHeap.Ticket t = g.issue(2, "x");
        assertThatThrownBy(() -> g.raise(t, 3)).isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void questReplaysHatchOrders() {
        List<String> orders = List.of("issue Ada 5", "issue Bo 2", "issue Cy 8", "serve", "issue Di 6");
        assertThat(RationHeap.QUEST_ID).isEqualTo("q_ration_heap");
        assertThat(RationHeap.quest(orders, "Ada")).isTrue();
        assertThat(RationHeap.quest(orders, "Bo")).isFalse();
        assertThat(RationHeap.quest(List.of("serve"), "Ada")).isFalse();
        assertThat(RationHeap.quest(List.of("bake bread"), "Ada")).isFalse();
    }
}