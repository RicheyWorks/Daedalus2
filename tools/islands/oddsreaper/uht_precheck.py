"""OddsReaper headless UHT pre-check for DaedalusLink (no Unreal, no compile).

Catches the cheap UnrealHeaderTool failures before an editor turn burns its
10 minutes on a rebuild: duplicate UCLASS/USTRUCT/UENUM type names across the
module, *.generated.h not being the last #include, a reflected type missing
GENERATED_BODY, and file-scope (non-static, non-namespaced) globals in .cpp
files that would collide in a unity build. Exit 1 on any hard error.
Usage: python tools/islands/oddsreaper/uht_precheck.py [--module PATH]
"""
import pathlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
MOD = ROOT / "engines/unreal/DaedalusLink/Source/DaedalusLink"
TYPE_RE = re.compile(r"^\s*(UCLASS|USTRUCT|UENUM|UINTERFACE)\s*\(.*?\)\s*\n\s*(?:class|struct|enum(?:\s+class)?)\s+(?:\w+_API\s+)?(\w+)", re.M)
INC_RE = re.compile(r'^\s*#include\s+[<"]([^>"]+)[>"]', re.M)
GLOBAL_RE = re.compile(r"^(?:const\s+)?(?:TCHAR|int32|float|FString|TArray<[^>]+>|bool)\s*\*?\s*(G\w+|\w+)\s*(?:\[[^\]]*\])?\s*=", re.M)


def check(mod=MOD):
    errors, warns, seen = [], [], {}
    for h in sorted(mod.rglob("*.h")):
        src = h.read_text(encoding="utf-8", errors="replace")
        types = TYPE_RE.findall(src)
        for kind, name in types:
            if name in seen:
                errors.append(f"duplicate {kind} {name}: {h.name} and {seen[name]}")
            seen[name] = h.name
        if types:
            incs = INC_RE.findall(src)
            gen = f"{h.stem}.generated.h"
            if not incs or incs[-1] != gen:
                errors.append(f"{h.name}: last #include must be {gen}")
            n_body = len(re.findall(r"GENERATED_(?:UCLASS_)?BODY\s*\(", src))
            n_types = sum(1 for k, _ in types if k != "UENUM")
            if n_body < n_types:
                errors.append(f"{h.name}: {n_types} reflected class/struct but {n_body} GENERATED_BODY")
    for c in sorted(mod.rglob("*.cpp")):
        src = c.read_text(encoding="utf-8", errors="replace")
        depth_ns, out = 0, []
        for line in src.splitlines():
            if re.match(r"^\s*namespace\b", line):
                depth_ns += 1
            if depth_ns == 0 and not line.startswith(("static", " ", "\t")):
                out.append(line)
            if depth_ns and line.strip() == "}":
                depth_ns -= 1
        for m in GLOBAL_RE.finditer("\n".join(out)):
            warns.append(f"{c.name}: file-scope global '{m.group(1)}' (unity-build collision risk; wrap in namespace or static)")
    return errors, warns, len(seen)


if __name__ == "__main__":
    mod = pathlib.Path(sys.argv[sys.argv.index("--module") + 1]) if "--module" in sys.argv else MOD
    errs, warns, n = check(mod)
    for w in warns:
        print("WARN", w)
    for e in errs:
        print("ERROR", e)
    print(f"UHT_PRECHECK types={n} errors={len(errs)} warns={len(warns)} -> {'OK' if not errs else 'FAIL'}")
    sys.exit(1 if errs else 0)
