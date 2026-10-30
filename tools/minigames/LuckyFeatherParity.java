// SPDX-License-Identifier: MIT
// Writes engines/unreal/core-test/luckyfeather_parity.txt from the Java core (the rules authority).
//   javac -d build -cp <daedalus-core classes> tools/minigames/LuckyFeatherParity.java
//   java -cp build:<daedalus-core classes> LuckyFeatherParity > engines/unreal/core-test/luckyfeather_parity.txt
import com.daedalus.world.battlefield.LuckyFeather;

public final class LuckyFeatherParity {
    private LuckyFeatherParity() {}

    public static void main(String[] args) {
        int[] flocks = {2, 5, 20, 50};
        double[] fit = {0.8, 1.0, 1.1, 1.5, 2.0};
        long seed = 1;
        System.out.println("# luckyfeather parity v1: N r i runs seed fix exact steps simfixed simsteps capped need50 need90");
        for (int n : flocks) {
            for (double r : fit) {
                int i = Math.max(1, n / 10);
                LuckyFeather m = LuckyFeather.of(new LuckyFeather.Settings(n, r, i, 1_000_000));
                int runs = 200;
                LuckyFeather.Result res = m.simulate(runs, seed);
                System.out.printf("case N=%d r=%s i=%d runs=%d seed=%d fix=%s exact=%s steps=%s simfixed=%d simsteps=%s"
                        + " capped=%d need50=%d need90=%d%n", n, Double.toString(r), i, runs, seed,
                        Double.toString(m.fixation()), Double.toString(m.exact()[i]), Double.toString(m.meanSteps()),
                        Math.round(res.fixed() * runs), Double.toString(res.meanSteps()), res.capped(),
                        m.carriersNeeded(0.5), m.carriersNeeded(0.9));
                seed++;
            }
        }
    }
}
