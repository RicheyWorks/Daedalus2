# Echo Bell sound-cue sheet (EBG 1, echo-bell-v1)

Generated from `peals.ebg` (Daedalus2 main, Java core is the source of truth). All times in ms from gate start.

## Fixed rules for the actor

- Bell: soft struck bronze, fundamental = `hz` column, no bright overtones above ~2 kHz emphasised; decay ~1.5 s.
- Gain: 0.6 normal bell, 0.3 passing note (gap from previous bell <= 750 ms). Never above 0.6.
- Echo: same bell sample, played at `echoMs`, gain x0.5, low-passed (~1.2 kHz), slight reverb. Delay = 200 + 70 x depthCells.
- Timing window: +/- `windowMs` around each echo (140/120/100/80 by difficulty 0-3; x1.5 with Echo Crickets).
- Crickets assist: quiet cricket chirp loop (gain <= 0.2) ticking on each echo time.
- Pitch set: D3 146.832, F3 174.614, G3 195.998, A3 219.999, C4 261.625, D4 293.664, F4 349.228 Hz.

## Fixture peals (the first one is `sample.ebg`: seed 1, difficulty 0, no crickets)

### seed 1, difficulty 0, crickets 0: 3 bells, window +/- 140 ms

| Bell | ringMs | Hz | Gain | Depth cells | Echo delay ms | echoMs |
|---|---|---|---|---|---|---|
| 0 | 1200 | 146.832 | 0.600 | 2 | 340 | 1540 |
| 1 | 1800 | 261.625 | 0.300 | 4 | 480 | 2280 |
| 2 | 2850 | 293.664 | 0.600 | 5 | 550 | 3400 |

### seed 1, difficulty 1, crickets 1: 4 bells, window +/- 180 ms

| Bell | ringMs | Hz | Gain | Depth cells | Echo delay ms | echoMs |
|---|---|---|---|---|---|---|
| 0 | 1200 | 146.832 | 0.600 | 2 | 340 | 1540 |
| 1 | 1800 | 261.625 | 0.300 | 4 | 480 | 2280 |
| 2 | 2850 | 293.664 | 0.600 | 5 | 550 | 3400 |
| 3 | 3750 | 219.999 | 0.600 | 9 | 830 | 4580 |

### seed 1, difficulty 2, crickets 0: 5 bells, window +/- 100 ms

| Bell | ringMs | Hz | Gain | Depth cells | Echo delay ms | echoMs |
|---|---|---|---|---|---|---|
| 0 | 1200 | 146.832 | 0.600 | 2 | 340 | 1540 |
| 1 | 1800 | 261.625 | 0.300 | 4 | 480 | 2280 |
| 2 | 2850 | 293.664 | 0.600 | 5 | 550 | 3400 |
| 3 | 3750 | 219.999 | 0.600 | 9 | 830 | 4580 |
| 4 | 4950 | 219.999 | 0.600 | 5 | 550 | 5500 |

### seed 1, difficulty 3, crickets 1: 6 bells, window +/- 120 ms

| Bell | ringMs | Hz | Gain | Depth cells | Echo delay ms | echoMs |
|---|---|---|---|---|---|---|
| 0 | 1200 | 146.832 | 0.600 | 2 | 340 | 1540 |
| 1 | 1800 | 261.625 | 0.300 | 4 | 480 | 2280 |
| 2 | 2850 | 293.664 | 0.600 | 5 | 550 | 3400 |
| 3 | 3750 | 219.999 | 0.600 | 9 | 830 | 4580 |
| 4 | 4950 | 219.999 | 0.600 | 5 | 550 | 5500 |
| 5 | 5850 | 174.614 | 0.600 | 3 | 410 | 6260 |

### seed 42, difficulty 0, crickets 0: 3 bells, window +/- 140 ms

| Bell | ringMs | Hz | Gain | Depth cells | Echo delay ms | echoMs |
|---|---|---|---|---|---|---|
| 0 | 1200 | 219.999 | 0.600 | 9 | 830 | 2030 |
| 1 | 2100 | 219.999 | 0.600 | 2 | 340 | 2440 |
| 2 | 3300 | 293.664 | 0.600 | 6 | 620 | 3920 |

### seed 42, difficulty 1, crickets 1: 4 bells, window +/- 180 ms

| Bell | ringMs | Hz | Gain | Depth cells | Echo delay ms | echoMs |
|---|---|---|---|---|---|---|
| 0 | 1200 | 219.999 | 0.600 | 9 | 830 | 2030 |
| 1 | 2100 | 219.999 | 0.600 | 2 | 340 | 2440 |
| 2 | 3300 | 293.664 | 0.600 | 6 | 620 | 3920 |
| 3 | 4200 | 219.999 | 0.600 | 9 | 830 | 5030 |

### seed 42, difficulty 2, crickets 0: 5 bells, window +/- 100 ms

| Bell | ringMs | Hz | Gain | Depth cells | Echo delay ms | echoMs |
|---|---|---|---|---|---|---|
| 0 | 1200 | 219.999 | 0.600 | 9 | 830 | 2030 |
| 1 | 2100 | 219.999 | 0.600 | 2 | 340 | 2440 |
| 2 | 3300 | 293.664 | 0.600 | 6 | 620 | 3920 |
| 3 | 4200 | 219.999 | 0.600 | 9 | 830 | 5030 |
| 4 | 5400 | 219.999 | 0.600 | 2 | 340 | 5740 |

### seed 42, difficulty 3, crickets 1: 6 bells, window +/- 120 ms

| Bell | ringMs | Hz | Gain | Depth cells | Echo delay ms | echoMs |
|---|---|---|---|---|---|---|
| 0 | 1200 | 219.999 | 0.600 | 9 | 830 | 2030 |
| 1 | 2100 | 219.999 | 0.600 | 2 | 340 | 2440 |
| 2 | 3300 | 293.664 | 0.600 | 6 | 620 | 3920 |
| 3 | 4200 | 219.999 | 0.600 | 9 | 830 | 5030 |
| 4 | 5400 | 219.999 | 0.600 | 2 | 340 | 5740 |
| 5 | 6600 | 195.997 | 0.600 | 10 | 900 | 7500 |

### seed -7, difficulty 0, crickets 0: 3 bells, window +/- 140 ms

| Bell | ringMs | Hz | Gain | Depth cells | Echo delay ms | echoMs |
|---|---|---|---|---|---|---|
| 0 | 1200 | 293.664 | 0.600 | 2 | 340 | 1540 |
| 1 | 2100 | 219.999 | 0.600 | 2 | 340 | 2440 |
| 2 | 3150 | 195.997 | 0.600 | 7 | 690 | 3840 |

### seed -7, difficulty 1, crickets 1: 4 bells, window +/- 180 ms

| Bell | ringMs | Hz | Gain | Depth cells | Echo delay ms | echoMs |
|---|---|---|---|---|---|---|
| 0 | 1200 | 293.664 | 0.600 | 2 | 340 | 1540 |
| 1 | 2100 | 219.999 | 0.600 | 2 | 340 | 2440 |
| 2 | 3150 | 195.997 | 0.600 | 7 | 690 | 3840 |
| 3 | 4200 | 261.625 | 0.600 | 10 | 900 | 5100 |

### seed -7, difficulty 2, crickets 0: 5 bells, window +/- 100 ms

| Bell | ringMs | Hz | Gain | Depth cells | Echo delay ms | echoMs |
|---|---|---|---|---|---|---|
| 0 | 1200 | 293.664 | 0.600 | 2 | 340 | 1540 |
| 1 | 2100 | 219.999 | 0.600 | 2 | 340 | 2440 |
| 2 | 3150 | 195.997 | 0.600 | 7 | 690 | 3840 |
| 3 | 4200 | 261.625 | 0.600 | 10 | 900 | 5100 |
| 4 | 4950 | 349.227 | 0.300 | 3 | 410 | 5360 |

### seed -7, difficulty 3, crickets 1: 6 bells, window +/- 120 ms

| Bell | ringMs | Hz | Gain | Depth cells | Echo delay ms | echoMs |
|---|---|---|---|---|---|---|
| 0 | 1200 | 293.664 | 0.600 | 2 | 340 | 1540 |
| 1 | 2100 | 219.999 | 0.600 | 2 | 340 | 2440 |
| 2 | 3150 | 195.997 | 0.600 | 7 | 690 | 3840 |
| 3 | 4200 | 261.625 | 0.600 | 10 | 900 | 5100 |
| 4 | 4950 | 349.227 | 0.300 | 3 | 410 | 5360 |
| 5 | 5700 | 219.999 | 0.300 | 8 | 760 | 6460 |

### seed 1592642302, difficulty 0, crickets 0: 3 bells, window +/- 140 ms

| Bell | ringMs | Hz | Gain | Depth cells | Echo delay ms | echoMs |
|---|---|---|---|---|---|---|
| 0 | 750 | 219.999 | 0.300 | 8 | 760 | 1510 |
| 1 | 1950 | 349.227 | 0.600 | 10 | 900 | 2850 |
| 2 | 3150 | 174.614 | 0.600 | 2 | 340 | 3490 |

### seed 1592642302, difficulty 1, crickets 1: 4 bells, window +/- 180 ms

| Bell | ringMs | Hz | Gain | Depth cells | Echo delay ms | echoMs |
|---|---|---|---|---|---|---|
| 0 | 750 | 219.999 | 0.300 | 8 | 760 | 1510 |
| 1 | 1950 | 349.227 | 0.600 | 10 | 900 | 2850 |
| 2 | 3150 | 174.614 | 0.600 | 2 | 340 | 3490 |
| 3 | 4050 | 146.832 | 0.600 | 10 | 900 | 4950 |

### seed 1592642302, difficulty 2, crickets 0: 5 bells, window +/- 100 ms

| Bell | ringMs | Hz | Gain | Depth cells | Echo delay ms | echoMs |
|---|---|---|---|---|---|---|
| 0 | 750 | 219.999 | 0.300 | 8 | 760 | 1510 |
| 1 | 1950 | 349.227 | 0.600 | 10 | 900 | 2850 |
| 2 | 3150 | 174.614 | 0.600 | 2 | 340 | 3490 |
| 3 | 4050 | 146.832 | 0.600 | 10 | 900 | 4950 |
| 4 | 4800 | 195.997 | 0.300 | 7 | 690 | 5490 |

### seed 1592642302, difficulty 3, crickets 1: 6 bells, window +/- 120 ms

| Bell | ringMs | Hz | Gain | Depth cells | Echo delay ms | echoMs |
|---|---|---|---|---|---|---|
| 0 | 750 | 219.999 | 0.300 | 8 | 760 | 1510 |
| 1 | 1950 | 349.227 | 0.600 | 10 | 900 | 2850 |
| 2 | 3150 | 174.614 | 0.600 | 2 | 340 | 3490 |
| 3 | 4050 | 146.832 | 0.600 | 10 | 900 | 4950 |
| 4 | 4800 | 195.997 | 0.300 | 7 | 690 | 5490 |
| 5 | 5850 | 146.832 | 0.600 | 2 | 340 | 6190 |

### seed -9223372036854775808, difficulty 0, crickets 0: 3 bells, window +/- 140 ms

| Bell | ringMs | Hz | Gain | Depth cells | Echo delay ms | echoMs |
|---|---|---|---|---|---|---|
| 0 | 600 | 219.999 | 0.300 | 9 | 830 | 1430 |
| 1 | 1800 | 219.999 | 0.600 | 3 | 410 | 2210 |
| 2 | 2700 | 349.227 | 0.600 | 2 | 340 | 3040 |

### seed -9223372036854775808, difficulty 1, crickets 1: 4 bells, window +/- 180 ms

| Bell | ringMs | Hz | Gain | Depth cells | Echo delay ms | echoMs |
|---|---|---|---|---|---|---|
| 0 | 600 | 219.999 | 0.300 | 9 | 830 | 1430 |
| 1 | 1800 | 219.999 | 0.600 | 3 | 410 | 2210 |
| 2 | 2700 | 349.227 | 0.600 | 2 | 340 | 3040 |
| 3 | 3450 | 146.832 | 0.300 | 6 | 620 | 4070 |

### seed -9223372036854775808, difficulty 2, crickets 0: 5 bells, window +/- 100 ms

| Bell | ringMs | Hz | Gain | Depth cells | Echo delay ms | echoMs |
|---|---|---|---|---|---|---|
| 0 | 600 | 219.999 | 0.300 | 9 | 830 | 1430 |
| 1 | 1800 | 219.999 | 0.600 | 3 | 410 | 2210 |
| 2 | 2700 | 349.227 | 0.600 | 2 | 340 | 3040 |
| 3 | 3450 | 146.832 | 0.300 | 6 | 620 | 4070 |
| 4 | 4650 | 174.614 | 0.600 | 6 | 620 | 5270 |

### seed -9223372036854775808, difficulty 3, crickets 1: 6 bells, window +/- 120 ms

| Bell | ringMs | Hz | Gain | Depth cells | Echo delay ms | echoMs |
|---|---|---|---|---|---|---|
| 0 | 600 | 219.999 | 0.300 | 9 | 830 | 1430 |
| 1 | 1800 | 219.999 | 0.600 | 3 | 410 | 2210 |
| 2 | 2700 | 349.227 | 0.600 | 2 | 340 | 3040 |
| 3 | 3450 | 146.832 | 0.300 | 6 | 620 | 4070 |
| 4 | 4650 | 174.614 | 0.600 | 6 | 620 | 5270 |
| 5 | 5550 | 349.227 | 0.600 | 10 | 900 | 6450 |
