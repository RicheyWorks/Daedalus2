import com.daedalus.world.forge.PadovanPlinths;
import java.io.PrintWriter;

public class GenPadovanGolden {
    public static void main(String[] args) throws Exception {
        try (PrintWriter w = new PrintWriter(args[0], "UTF-8")) {
            w.println("# Golden vectors for padovan_plinths.h, generated from Java com.daedalus.world.forge.PadovanPlinths (G526, PR #965)");
            w.println("# M max_index | T n P(n) | I v index_of(v) | S a b sum-or-OVERFLOW");
            int mx = PadovanPlinths.MAX_INDEX;
            w.println("M " + mx);
            for (int n = 0; n <= mx; n++) {
                w.println("T " + n + " " + PadovanPlinths.padovan(n));
            }
            for (long v = -3; v <= 5000; v++) {
                w.println("I " + v + " " + PadovanPlinths.indexOf(v));
            }
            for (int n = 0; n <= mx; n++) {
                long p = PadovanPlinths.padovan(n);
                w.println("I " + p + " " + PadovanPlinths.indexOf(p));
                w.println("I " + (p + 1) + " " + PadovanPlinths.indexOf(p + 1));
                w.println("I " + (p - 1) + " " + PadovanPlinths.indexOf(p - 1));
            }
            w.println("I " + Long.MAX_VALUE + " " + PadovanPlinths.indexOf(Long.MAX_VALUE));
            w.println("I " + Long.MIN_VALUE + " " + PadovanPlinths.indexOf(Long.MIN_VALUE));
            for (int a = 0; a <= mx; a += 3) {
                for (int b = a; b <= mx; b += 5) {
                    String s;
                    try {
                        s = Long.toString(PadovanPlinths.runSum(a, b));
                    } catch (ArithmeticException ex) {
                        s = "OVERFLOW";
                    }
                    w.println("S " + a + " " + b + " " + s);
                }
                String s;
                try {
                    s = Long.toString(PadovanPlinths.runSum(a, mx));
                } catch (ArithmeticException ex) {
                    s = "OVERFLOW";
                }
                w.println("S " + a + " " + mx + " " + s);
            }
        }
    }
}
