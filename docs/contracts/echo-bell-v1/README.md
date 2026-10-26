# EBG 1: Echo Bell gate peal (echo-bell-v1)

Text, LF line endings, invariant locale.

    EBG 1
    gate <seed> <difficulty 0-3> <crickets 0|1> <windowMs>
    bell <index> <ringMs> <hz %.3f> <gain %.3f> <depthCells> <echoMs>   (3 + difficulty lines)
    end

- RNG: SplitMix64 seeded with `seed ^ 0x45424731`. Per bell, draws in order: pentatonic degree
  {0,3,5,7,10}[u%5], octave u%2, gap 600+150*(u%5) ms, depth 2+(u%9).
- semis = degree + 12*octave, minus 12 if over 15; hz = round(146.832 * 2^(semis/12), 3). Max 360 Hz.
- gain 0.3 when the gap is 750 ms or less (passing note), else 0.6.
- echoMs = ringMs + 200 + 70*depthCells; depths may come from the maze (1-40 cells).
- windowMs = 140 - 20*difficulty, times 3/2 (integer) with crickets.
- The gate opens only with exactly one tap per echo, in ascending order, each within +/- windowMs.

`peals.ebg` = seeds {1, 42, -7, 0x5EEDCAFE, Long.MIN_VALUE} x difficulty 0-3, crickets on odd difficulty.
