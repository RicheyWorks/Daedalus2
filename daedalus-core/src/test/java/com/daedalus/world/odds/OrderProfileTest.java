package com.daedalus.world.odds;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.daedalus.world.tactics.TacticalOrders.Verb;
import org.junit.jupiter.api.Test;

class OrderProfileTest {

    @Test
    void everyVerbHasAProfile() {
        for (Verb v : Verb.values()) {
            assertTrue(OrderProfile.of(v).startDelay() >= 0);
        }
    }

    @Test
    void verbsMeanWhatTheContractSays() {
        assertFalse(OrderProfile.of(Verb.HOLD).attacks());
        assertTrue(OrderProfile.of(Verb.ATTACK).attacks());
        assertTrue(OrderProfile.of(Verb.FLANK).startDelay() > 0);
        assertTrue(OrderProfile.of(Verb.DEFEND).incomingMultiplier() < 1);
        assertTrue(OrderProfile.of(Verb.RETREAT).leaves());
        assertTrue(OrderProfile.of(Verb.REINFORCE).startDelay() > OrderProfile.of(Verb.FLANK).startDelay());
        assertEquals(OrderProfile.of(Verb.ATTACK), OrderProfile.fighting());
    }

    @Test
    void validation() {
        assertThrows(IllegalArgumentException.class, () -> new OrderProfile(true, false, -1, 1, 1));
        assertThrows(IllegalArgumentException.class, () -> new OrderProfile(true, false, 0, -1, 1));
        assertThrows(IllegalArgumentException.class, () -> new OrderProfile(true, false, 0, 1, 11));
    }
}