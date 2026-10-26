# Twin Doors plugin core test (G04)

Proves `Source/DaedalusLink/Public/DaedalusTwinDoorsCore.h`, the exception-free copy of prometheus'
`core-test/twin_doors` core used by `ADaedalusTwinDoors`, against the same contract fixture, with C++ exceptions OFF
as in an Unreal game target:

    cl /nologo /EHs-c- /D_HAS_EXCEPTIONS=0 /D_CRT_SECURE_NO_WARNINGS /std:c++17 /W4 /WX ^
       /I engines\unreal\DaedalusLink\Source\DaedalusLink\Public engines\unreal\core-test\twin_doors_plugin\twin_doors_plugin_test.cpp
    twin_doors_plugin_test docs\contracts\twin-doors-v1\riddles.twd

9 checks: byte parity with `riddles.twd` (10 riddles), the embedded question solves 2000 seeds x 2 difficulties,
all 8 worlds reachable, no-throw refusals (bad difficulty clamps, bad side answers nothing), the one-question /
one-door session, and the bell constants.