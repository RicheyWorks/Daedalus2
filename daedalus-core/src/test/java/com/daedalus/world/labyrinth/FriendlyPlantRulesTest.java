package com.daedalus.world.labyrinth;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;
import static com.daedalus.world.labyrinth.FriendlyPlantRules.*;
class FriendlyPlantRulesTest {
    @Test void playersAndAlliesAreNeverAttackTargets() {
        for(Target t:new Target[]{Target.PLAYER,Target.ALLY})
            for(boolean threat:new boolean[]{false,true}) for(boolean injury:new boolean[]{false,true}) for(boolean lost:new boolean[]{false,true})
                assertNotEquals(Action.DEFEND,choose(t,threat,injury,lost));
        assertEquals(Action.OFFER_AID,choose(Target.PLAYER,true,true,true));
        assertEquals(Action.GUIDE,choose(Target.PLAYER,false,false,true));
    }
    @Test void onlyActiveHostileThreatCanBeDefendedAgainst() {
        assertEquals(Action.DEFEND,choose(Target.HOSTILE,true,false,false));
        assertEquals(Action.NONE,choose(Target.HOSTILE,false,true,true));
        for(Target t:new Target[]{Target.NEUTRAL,Target.UNKNOWN}) assertEquals(Action.NONE,choose(t,true,true,true));
        assertThrows(IllegalArgumentException.class,()->choose(null,true,true,true));
    }
}
