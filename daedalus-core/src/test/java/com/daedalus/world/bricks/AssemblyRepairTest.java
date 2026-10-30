// SPDX-License-Identifier: MIT

package com.daedalus.world.bricks;

import com.daedalus.world.BlockCoordinate;
import com.daedalus.world.BlockType;
import com.daedalus.world.bricks.AssemblyRepair.Grade;
import com.daedalus.world.bricks.AssemblyRepair.Machine;
import com.daedalus.world.bricks.AssemblyRepair.Outcome;
import com.daedalus.world.bricks.AssemblyRepair.Piece;
import com.daedalus.world.bricks.AssemblyRepair.Receipt;
import com.daedalus.world.bricks.AssemblyRepair.Scatter;
import com.daedalus.world.bricks.AssemblyRepair.Session;
import com.daedalus.world.bricks.AssemblyRepair.Slot;
import org.junit.jupiter.api.Test;

import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * BRK01 Missing Piece Collector (G16): the scatter is seeded, stays on free baseplate cells, always leaves a
 * genuine piece for every slot, and the host-side session collects once, consumes once, grades like a
 * temper, re-bakes at the Kiln, and opens the airfield only when the plane is whole.
 */
class AssemblyRepairTest {

    private static BlockCoordinate beside(Piece p) {
        return new BlockCoordinate(p.at().x() + 1, p.at().y(), p.at().z());
    }

    /** Walk to each hinted piece, keep the best seating one of each slot's shape, fit it. */
    private static Session solve(Scatter s, Machine m) {
        Session run = new Session(s);
        for (Slot slot : m.slots()) {
            for (Piece p : run.hints(slot, BricksOps.spawn())) {
                assertThat(run.collect(p.id(), beside(p))).isEqualTo(Outcome.OK);
            }
            Piece best = null;
            for (int id : run.bag()) {
                Piece p = run.current(id);
                if (p.shape().equals(slot.shape()) && (best == null || p.wear() < best.wear())) {
                    best = p;
                }
            }
            assertThat(best).as("seed %d slot %s", s.seed(), slot).isNotNull();
            assertThat(run.fit(slot, best.id())).as("seed %d slot %s", s.seed(), slot).isEqualTo(Outcome.OK);
        }
        return run;
    }

    @Test
    void theScatterIsSeededAndDeterministic() {
        assertThat(AssemblyRepair.scatter(7)).isEqualTo(AssemblyRepair.scatter(7));
        assertThat(AssemblyRepair.scatter(7).pieces()).isNotEqualTo(AssemblyRepair.scatter(8).pieces());
    }

    @Test
    void piecesLieOnFreeUnprotectedBaseplateCellsAndTouchNoBuild() {
        for (long seed = 0; seed < 50; seed++) {
            Scatter s = AssemblyRepair.scatter(seed);
            Map<BlockCoordinate, BlockType> ground = BricksOps.plan(seed).cubes();
            Set<BlockCoordinate> cells = new HashSet<>();
            Set<Integer> ids = new HashSet<>();
            for (Piece p : s.pieces()) {
                assertThat(p.at().y()).isEqualTo(BricksOps.TOP_Y + 1);
                assertThat(BricksOps.protects(p.at())).isFalse();
                assertThat(ground).doesNotContainKey(p.at());
                assertThat(cells.add(p.at())).isTrue();
                assertThat(ids.add(p.id())).isTrue();
                assertThat(p.wear()).isBetween(0, 100);
            }
            assertThat(s.pieces().size()).isBetween(Slot.values().length + AssemblyRepair.DECOYS,
                    2 * Slot.values().length + AssemblyRepair.DECOYS);
        }
    }

    @Test
    void decoysNeverFitAnySlot() {
        for (String shape : AssemblyRepair.DECOY_SHAPES) {
            for (Slot slot : Slot.values()) {
                assertThat(shape).isNotEqualTo(slot.shape());
            }
        }
    }

    @Test
    void everySeedIsSolvableAndThePlaneOpensTheSkyGate() {
        for (long seed = 0; seed < 300; seed++) {
            Scatter s = AssemblyRepair.scatter(seed);
            Session run = solve(s, Machine.PLANE);
            Receipt r = run.receipt(Machine.PLANE);
            assertThat(r.restored()).isTrue();
            assertThat(r.skyGateOpen()).isTrue();
            assertThat(r.weakest().seats()).isTrue();
            assertThat(r.piecesUsed()).hasSize(Machine.PLANE.slots().size()).doesNotHaveDuplicates();
            assertThat(r.meanQuality()).isGreaterThanOrEqualTo(1000 - 10 * AssemblyRepair.GENUINE_MAX_WEAR);
            assertThat(run.airfieldOpen()).isTrue();
            assertThat(solve(s, Machine.HOVER_CART).receipt(Machine.HOVER_CART).restored()).isTrue();
        }
    }

    @Test
    void gradesFollowTheTemperBands() {
        BlockCoordinate at = new BlockCoordinate(60, 1, -100);
        assertThat(AssemblyRepair.grade(new Piece(0, "2x8", BlockType.BRICK_RED, 0, at), Slot.FUSELAGE)).isEqualTo(Grade.PERFECT);
        assertThat(AssemblyRepair.grade(new Piece(0, "2x8", BlockType.BRICK_RED, 15, at), Slot.FUSELAGE)).isEqualTo(Grade.PERFECT);
        assertThat(AssemblyRepair.grade(new Piece(0, "2x8", BlockType.BRICK_RED, 16, at), Slot.FUSELAGE)).isEqualTo(Grade.SNUG);
        assertThat(AssemblyRepair.grade(new Piece(0, "2x8", BlockType.BRICK_RED, 40, at), Slot.FUSELAGE)).isEqualTo(Grade.SNUG);
        assertThat(AssemblyRepair.grade(new Piece(0, "2x8", BlockType.BRICK_RED, 41, at), Slot.FUSELAGE)).isEqualTo(Grade.LOOSE);
        assertThat(AssemblyRepair.grade(new Piece(0, "2x8", BlockType.BRICK_RED, 70, at), Slot.FUSELAGE)).isEqualTo(Grade.LOOSE);
        assertThat(AssemblyRepair.grade(new Piece(0, "2x8", BlockType.BRICK_RED, 71, at), Slot.FUSELAGE)).isEqualTo(Grade.REJECT);
        assertThat(AssemblyRepair.grade(new Piece(0, "2x6", BlockType.BRICK_RED, 0, at), Slot.FUSELAGE)).isEqualTo(Grade.REJECT);
    }

    @Test
    void collectingNeedsReachAndHappensOnce() {
        Scatter s = AssemblyRepair.scatter(3);
        Piece p = s.pieces().get(0);
        Session run = new Session(s);
        assertThat(run.collect(9999, beside(p))).isEqualTo(Outcome.UNKNOWN_PIECE);
        BlockCoordinate far = new BlockCoordinate(p.at().x() + 4, p.at().y(), p.at().z());
        assertThat(run.collect(p.id(), far)).isEqualTo(Outcome.TOO_FAR);
        BlockCoordinate above = new BlockCoordinate(p.at().x(), p.at().y() + 3, p.at().z());
        assertThat(run.collect(p.id(), above)).isEqualTo(Outcome.TOO_FAR);
        BlockCoordinate edge = new BlockCoordinate(p.at().x() + 3, p.at().y(), p.at().z());
        assertThat(run.collect(p.id(), edge)).isEqualTo(Outcome.OK);
        assertThat(run.collect(p.id(), edge)).isEqualTo(Outcome.ALREADY_COLLECTED);
        assertThat(run.bag()).containsExactly(p.id());
    }

    @Test
    void fittingConsumesOncePerSlotAndRejectsKeepThePiece() {
        Scatter s = AssemblyRepair.scatter(11);
        Session run = new Session(s);
        Piece wing = run.hints(Slot.LEFT_WING, BricksOps.spawn()).get(0);
        assertThat(run.fit(Slot.LEFT_WING, wing.id())).isEqualTo(Outcome.NOT_COLLECTED);
        run.collect(wing.id(), beside(wing));
        assertThat(run.fit(Slot.FUSELAGE, wing.id())).isEqualTo(Outcome.REJECTED);
        assertThat(run.bag()).contains(wing.id());
        assertThat(run.receipt(Machine.PLANE).rejects()).isEqualTo(1);
        Outcome first = run.fit(Slot.LEFT_WING, wing.id());
        if (first == Outcome.OK) {
            assertThat(run.fit(Slot.RIGHT_WING, wing.id())).isEqualTo(Outcome.ALREADY_USED);
            assertThat(run.bag()).doesNotContain(wing.id());
            assertThat(run.fitted(Slot.LEFT_WING).pieceId()).isEqualTo(wing.id());
            Piece other = run.hints(Slot.RIGHT_WING, BricksOps.spawn()).get(0);
            run.collect(other.id(), beside(other));
            assertThat(run.fit(Slot.LEFT_WING, other.id())).isEqualTo(Outcome.SLOT_FILLED);
        } else {
            assertThat(first).isEqualTo(Outcome.REJECTED);          // a cracked spare
        }
    }

    @Test
    void theKilnRebakesOncePerPieceWithLimitedCharges() {
        Scatter s = AssemblyRepair.scatter(5);
        Session run = new Session(s);
        List<Piece> pieces = s.pieces();
        assertThat(run.rebake(pieces.get(0).id())).isEqualTo(Outcome.NOT_COLLECTED);
        for (int i = 0; i < 5; i++) {
            run.collect(pieces.get(i).id(), beside(pieces.get(i)));
        }
        Piece a = pieces.get(0);
        assertThat(run.rebake(a.id())).isEqualTo(Outcome.OK);
        assertThat(run.current(a.id()).wear()).isEqualTo(Math.max(0, a.wear() - AssemblyRepair.KILN_RESTORE));
        assertThat(run.rebake(a.id())).isEqualTo(Outcome.ALREADY_REBAKED);
        assertThat(run.rebake(pieces.get(1).id())).isEqualTo(Outcome.OK);
        assertThat(run.rebake(pieces.get(2).id())).isEqualTo(Outcome.OK);
        assertThat(run.rebake(pieces.get(3).id())).isEqualTo(Outcome.NO_KILN_CHARGES);
        assertThat(run.kilnUses()).isEqualTo(AssemblyRepair.KILN_CHARGES);
        assertThat(s.piece(a.id()).wear()).isEqualTo(a.wear());   // the scatter itself never changes
    }

    @Test
    void aRebakeCanSaveACrackedPiece() {
        BlockCoordinate at = new BlockCoordinate(60, 1, -100);
        Scatter s = new Scatter(0, List.of(new Piece(0, "1x4", BlockType.BRICK_BLUE, 90, at)));
        Session run = new Session(s);
        run.collect(0, at);
        assertThat(run.fit(Slot.PROPELLER, 0)).isEqualTo(Outcome.REJECTED);
        assertThat(run.rebake(0)).isEqualTo(Outcome.OK);
        assertThat(run.fit(Slot.PROPELLER, 0)).isEqualTo(Outcome.OK);
        assertThat(run.fitted(Slot.PROPELLER).grade()).isEqualTo(Grade.LOOSE);
        assertThat(run.rebake(0)).isEqualTo(Outcome.ALREADY_USED);
    }

    @Test
    void pocketBotHintsMatchShapeNearestFirstAndSkipTakenPieces() {
        Scatter s = AssemblyRepair.scatter(21);
        Session run = new Session(s);
        BlockCoordinate from = BricksOps.hangarBerth();
        List<Piece> hints = run.hints(Slot.FAN, from);
        assertThat(hints).isNotEmpty().allMatch(p -> p.shape().equals("2x2"));
        for (int i = 1; i < hints.size(); i++) {
            assertThat(AssemblyRepair.distance(hints.get(i - 1).at(), from))
                    .isLessThanOrEqualTo(AssemblyRepair.distance(hints.get(i).at(), from));
        }
        Piece first = hints.get(0);
        run.collect(first.id(), beside(first));
        assertThat(run.hints(Slot.SEAT, from)).doesNotContain(first);
    }

    @Test
    void theGateStaysShutUntilThePlaneIsWholeAndTheCartNeverOpensIt() {
        Scatter s = AssemblyRepair.scatter(42);
        Session cart = solve(s, Machine.HOVER_CART);
        assertThat(cart.receipt(Machine.HOVER_CART).restored()).isTrue();
        assertThat(cart.receipt(Machine.HOVER_CART).skyGateOpen()).isFalse();
        assertThat(cart.airfieldOpen()).isFalse();
        Receipt partial = cart.receipt(Machine.PLANE);
        assertThat(partial.restored()).isFalse();
        assertThat(partial.weakest()).isEqualTo(Grade.REJECT);
        assertThat(partial.piecesUsed()).isEmpty();
        assertThat(Machine.PLANE.slots()).hasSize(6);
        assertThat(Machine.HOVER_CART.slots()).hasSize(4);
    }
}
