// SPDX-License-Identifier: MIT
// Generates hofstadter_hammers_golden.txt from the Java HofstadterHammers.
// javac -cp daedalus-core/target/classes GenHofstadterGolden.java && java -cp daedalus-core/target/classes;. GenHofstadterGolden > hofstadter_hammers_golden.txt
import com.daedalus.world.forge.HofstadterHammers;

public final class GenHofstadterGolden {
    public static void main(String[] args) {
        int dense = 3000;
        int[] q = HofstadterHammers.qSequence(HofstadterHammers.MAX_N);
        int[] a = HofstadterHammers.conwaySequence(HofstadterHammers.MAX_N);
        StringBuilder sb = new StringBuilder();
        sb.append("# Hofstadter Hammers golden vectors from HofstadterHammers.java\n");
        sb.append("# M max_n | Q n value | C n value (dense 1..").append(dense).append(", then sampled to MAX_N)\n");
        sb.append("M ").append(HofstadterHammers.MAX_N).append('\n');
        for (int n = 1; n <= HofstadterHammers.MAX_N; n++) {
            boolean pick = n <= dense || n % 99991 == 0 || n == HofstadterHammers.MAX_N
                || Integer.bitCount(n) == 1 || Integer.bitCount(n + 1) == 1 || Integer.bitCount(n - 1) == 1;
            if (pick) {
                sb.append("Q ").append(n).append(' ').append(q[n]).append('\n');
                sb.append("C ").append(n).append(' ').append(a[n]).append('\n');
            }
        }
        if (HofstadterHammers.q(10) != q[10] || HofstadterHammers.conway(10) != a[10]) {
            throw new IllegalStateException("single-index API mismatch");
        }
        System.out.print(sb);
    }
}
