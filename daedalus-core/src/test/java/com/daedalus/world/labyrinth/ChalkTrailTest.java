package com.daedalus.world.labyrinth;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class ChalkTrailTest {
    private static final ChalkTrail.Point A=new ChalkTrail.Point(1,2), B=new ChalkTrail.Point(2,2);
    @Test void markingConsumesOnceAndErasingDoesNotRefund() {
        var trail=new ChalkTrail(2,8);
        assertEquals(ChalkTrail.Result.ADDED,trail.mark(A));
        assertEquals(ChalkTrail.Result.ALREADY_MARKED,trail.mark(A));assertEquals(1,trail.charges());
        assertTrue(trail.erase(A));assertFalse(trail.erase(A));assertEquals(1,trail.charges());
        assertEquals(ChalkTrail.Result.ADDED,trail.mark(A));assertEquals(0,trail.charges());
        assertEquals(ChalkTrail.Result.OUT_OF_CHALK,trail.mark(B));
    }
    @Test void fullTrailRefusesWithoutSpendingAndSnapshotIsImmutable() {
        var trail=new ChalkTrail(2,1);trail.mark(A);var snapshot=trail.marks();
        assertEquals(ChalkTrail.Result.FULL,trail.mark(B));assertEquals(1,trail.charges());
        assertThrows(UnsupportedOperationException.class,()->snapshot.clear());
        trail.erase(A);assertEquals(1,snapshot.size());assertEquals(ChalkTrail.Result.ADDED,trail.mark(B));
    }
    @Test void boundariesAndIndependentPlayers() {
        assertThrows(IllegalArgumentException.class,()->new ChalkTrail(-1,10));
        assertThrows(IllegalArgumentException.class,()->new ChalkTrail(1,513));
        assertThrows(IllegalArgumentException.class,()->new ChalkTrail.Point(Integer.MIN_VALUE,0));
        var one=new ChalkTrail(1,1);var two=new ChalkTrail(1,1);one.mark(A);assertTrue(two.marks().isEmpty());
        assertThrows(IllegalArgumentException.class,()->one.mark(null));
    }
}
