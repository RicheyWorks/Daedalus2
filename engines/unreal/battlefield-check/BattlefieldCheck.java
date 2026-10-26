// SPDX-License-Identifier: MIT
// Reactive Battlefield Ecology (ADR-061) Java side of the in-editor check.
//   javac -cp ../../../daedalus-core/target/classes BattlefieldCheck.java
//   java  -cp "../../../daedalus-core/target/classes;." BattlefieldCheck snap <out.dbe> [seed]
//   java  -cp "../../../daedalus-core/target/classes;." BattlefieldCheck apply <snap.dbe> <events.dbe>
// snap writes BattlefieldDemo.scene(seed) as DBE 1 and prints the Java answers at the sample points;
// apply reads the DBE-E 1 events Unreal wrote (UDaedalusEcology.FlushEvents) and shows Java applying them.
import com.daedalus.world.battlefield.BattlefieldDemo;
import com.daedalus.world.battlefield.BattlefieldEcology;
import com.daedalus.world.battlefield.Dbe;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.Locale;

public final class BattlefieldCheck {
    /** Same points battlefield_check_ue.py asks Unreal about. */
    static final double[][] POINTS = {{900, 1500}, {3900, 1500}, {2000, 1500}, {2500, 500}, {100, 100}};

    private BattlefieldCheck() { }

    public static void main(String[] a) throws Exception {
        if (a.length >= 2 && a[0].equals("snap")) {
            BattlefieldEcology e = BattlefieldDemo.scene(a.length > 2 ? Long.parseLong(a[2]) : 7);
            Files.writeString(Path.of(a[1]), Dbe.write(e));
            for (double[] p : POINTS) {
                System.out.printf(Locale.ROOT, "JAVA %.0f,%.0f veg=%s cover=%.3f conceal=%.3f burning=%b%n", p[0], p[1],
                        e.at(p[0], p[1]), e.coverAt(p[0], p[1]), e.at(p[0], p[1]).concealment(), e.burningAt(p[0], p[1]));
            }
        } else if (a.length >= 3 && a[0].equals("apply")) {
            BattlefieldEcology e = Dbe.read(Files.readString(Path.of(a[1])));
            List<Dbe.Event> ev = Dbe.readEvents(Files.readString(Path.of(a[2])));
            for (Dbe.Event x : ev) {
                System.out.printf(Locale.ROOT, "EVENT %s %.0f,%.0f r=%.0f burning_before=%b%n", x.kind(), x.x(), x.y(),
                        x.radiusCm(), e.burningAt(x.x(), x.y()));
            }
            int n = Dbe.apply(e, ev);
            for (Dbe.Event x : ev) {
                System.out.printf(Locale.ROOT, "APPLIED cells=%d burning_after=%b%n", n, e.burningAt(x.x(), x.y()));
            }
        } else {
            System.err.println("usage: BattlefieldCheck snap <out.dbe> [seed] | apply <snap.dbe> <events.dbe>");
            System.exit(2);
        }
    }
}