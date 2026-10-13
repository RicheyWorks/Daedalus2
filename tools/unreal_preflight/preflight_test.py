# SPDX-License-Identifier: MIT
"""Each preflight rule says no to its own canary, and a clean file passes. n/m last; exit 1 on a failure."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import preflight  # noqa: E402

F = os.path.join(HERE, "fixtures")
results = []


def check(name, ok, detail=""):
    results.append(bool(ok))
    print("%-4s  %s %s" % ("ok" if ok else "FAIL", name, detail if not ok else ""))


def rules(*files):
    return sorted({r for _, _, r, _ in preflight.scan([os.path.join(F, f) for f in files])})


check("P1: a member named Layers on an actor is caught", rules("bad_shadow.h") == ["P1"], rules("bad_shadow.h"))
check("P2: an exposed UPROPERTY with no Category is caught", rules("bad_category.h") == ["P2"], rules("bad_category.h"))
check("P3: bare Error as a type is caught (parameter and case label)",
      rules("bad_error.cpp") == ["P3"] and len(preflight.scan([os.path.join(F, "bad_error.cpp")])) == 2)
check("P4: a constructor-filled component array without Transient is caught",
      rules("bad_transient.h", "bad_transient.cpp") == ["P4"], rules("bad_transient.h", "bad_transient.cpp"))
check("P4: ...but only when a constructor fills it", rules("bad_transient.h") == [], rules("bad_transient.h"))
check("P7: TArray of std::string, of a std::-holding struct, and of a struct holding one (transitively) are caught",
      [e[2] for e in preflight.scan([os.path.join(F, "bad_tarray.h")])] == ["P7", "P7", "P7"], preflight.scan([os.path.join(F, "bad_tarray.h")]))
check("P5 + P6: b_ property names and non-UFUNCTION statics in Python are caught", rules("bad_py.py") == ["P5", "P6"],
      rules("bad_py.py"))
check("P3: the enum's own header, inside its namespace, is not flagged", rules("ok_enum_home.h") == [], rules("ok_enum_home.h"))
check("a clean header passes (Category set, Transient array, Name is not an actor member, qualified Error)",
      rules("good.h") == [], preflight.scan([os.path.join(F, "good.h")]))
n = sum(results)
print("%d/%d" % (n, len(results)))
sys.exit(0 if n == len(results) else 1)
