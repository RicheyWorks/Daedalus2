"""Headless test for uht_precheck: real module passes; planted faults are caught."""
import pathlib, sys, tempfile
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from uht_precheck import check

errs, warns, n = check()
assert not errs and n > 0, errs
with tempfile.TemporaryDirectory() as d:
    p = pathlib.Path(d)
    hdr = 'UCLASS()\nclass X_API AFoo : public AActor\n{\n\tGENERATED_BODY()\n};\n'
    (p / "A.h").write_text('#include "A.generated.h"\n' + hdr)
    (p / "B.h").write_text('#include "B.generated.h"\n#include "Other.h"\n' + hdr.replace("\tGENERATED_BODY()\n", ""))
    (p / "C.cpp").write_text('const TCHAR* GNames[2] = { TEXT("a"), TEXT("b") };\nnamespace { int32 GOk = 1; }\n')
    e, w, _ = check(p)
    joined = " | ".join(e)
    assert "duplicate UCLASS AFoo" in joined, e
    assert "B.h: last #include must be B.generated.h" in joined, e
    assert "B.h: 1 reflected class/struct but 0 GENERATED_BODY" in joined, e
    assert any("GNames" in x for x in w) and not any("GOk" in x for x in w), w
print("test_uht_precheck ALL PASS")
