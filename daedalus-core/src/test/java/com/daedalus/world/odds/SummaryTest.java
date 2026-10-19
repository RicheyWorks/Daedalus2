package com.daedalus.world.odds;

import static org.junit.jupiter.api.Assertions.assertEquals;

import org.junit.jupiter.api.Test;

class SummaryTest {

    @Test
    void oneToHundred() {
        double[] v = new double[100];
        for (int i = 0; i < 100; i++) {
            v[99 - i] = i + 1;          // reversed: the summary sorts a copy
        }
        Summary s = Summary.of(v, 100);
        assertEquals(100, s.n());
        assertEquals(50.5, s.mean(), 1e-12);
        assertEquals(841.6666666666666, s.variance(), 1e-9);
        assertEquals(1, s.min());
        assertEquals(50, s.p50());
        assertEquals(90, s.p90());
        assertEquals(99, s.p99());
        assertEquals(100, s.max());
        assertEquals(100.0, v[0], 0.0);   // input untouched
    }

    @Test
    void usesOnlyTheFrontCount() {
        double[] v = {3, 1, 2, 999, 999};
        Summary s = Summary.of(v, 3);
        assertEquals(3, s.n());
        assertEquals(2.0, s.mean(), 1e-12);
        assertEquals(3, s.max());
    }

    @Test
    void emptyAndSingle() {
        assertEquals(Summary.EMPTY, Summary.of(new double[0], 0));
        Summary one = Summary.of(new double[] {7}, 1);
        assertEquals(0.0, one.variance());
        assertEquals(7.0, one.p99());
        assertEquals("n=0 mean=0.000 sd=0.000 p50=0.000 p90=0.000 p99=0.000", Summary.EMPTY.encode());
    }
}