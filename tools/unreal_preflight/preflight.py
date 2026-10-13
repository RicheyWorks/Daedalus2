# SPDX-License-Identifier: MIT
"""Preflight for Unreal C++ and editor Python: catch, in the cloud, the mistakes that cost editor slots.

    python tools/unreal_preflight/preflight.py [paths...]     # default: the DaedalusLink plugin + tools/
    exit 0 = clean, 1 = errors (each printed as  ERROR path:line RULE  message)

Every rule comes from a real failure on 2026-10-12 (docs/AUTOMATION-LESSONS.md):
  P1 shadow     an actor member named like an AActor member (Layers, Tags, Owner...). UHT: "already defined".
  P2 category   an editor/Blueprint-exposed UPROPERTY with no Category. UHT error when built as a plugin package.
  P3 error-type bare `Error` used as a type. It clashes with UE's `class Error` (C2872 ambiguous symbol).
  P4 transient  a UPROPERTY TArray of components that the constructor fills. A saved copy from an older build
                overrides it on load, and indexing it crashed every editor launch. Mark it Transient.
  P5 py-bool    get/set_editor_property("b_...") in editor Python. Python names drop the b ("clean_water").
  P6 py-static  calling a static C++ helper from Python that is not a UFUNCTION (unreal.X.get(...)). Needs a
                UFUNCTION(BlueprintPure/Callable) wrapper, e.g. GetOrrery.
  P7 tarray-std a TArray of std:: types, or of a struct holding them (std::string, std::vector...). TArray moves
                its elements with memcpy, and MSVC's std::string points into its own buffer: moved copies dangle.
                Use std::vector for plain-C++ core types (2026-10-13, UDaedalusTactics::TakeRoster).
"""
import os
import re
import sys

ACTOR_MEMBERS = {"Layers", "Tags", "Owner", "Instigator", "Children", "RootComponent", "InputComponent", "Role",
                 "RemoteRole", "bHidden", "bReplicates", "NetDormancy", "SpawnCollisionHandlingMethod",
                 "CreationTime", "InitialLifeSpan", "CustomTimeDilation", "Layer"}
EXPOSED = ("EditAnywhere", "EditDefaultsOnly", "EditInstanceOnly", "VisibleAnywhere", "VisibleDefaultsOnly",
           "VisibleInstanceOnly", "BlueprintReadWrite", "BlueprintReadOnly", "BlueprintAssignable")

CLASS_RE = re.compile(r"class\s+(?:\w+_API\s+)?(\w+)\s*:\s*public\s+(\w+)")
MEMBER_RE = re.compile(r"^\s*(?:UPROPERTY\((?P<spec>[^)]*)\)\s*)?(?:const\s+)?[\w:<>,\s\*&]+?[\s\*&>](?P<name>\w+)\s*(?:=[^;]*)?;\s*(?://.*)?$")
UPROP_RE = re.compile(r"UPROPERTY\((?P<spec>[^)]*)\)")
ARRAY_RE = re.compile(r"UPROPERTY\((?P<spec>[^)]*)\)\s*TArray<\s*TObjectPtr<\s*(?P<type>U\w*Component)\s*>\s*>\s*(?P<name>\w+)\s*;")
ERROR_RE = re.compile(r"(?<![:\w])Error(?:\s+\w+\s*[,)=;]|::)")
PYBOOL_RE = re.compile(r"""[gs]et_editor_property\(\s*["']b_\w+""")
PYSTATIC_RE = re.compile(r"\bunreal\.Daedalus\w+\.(get)\(")
STRUCT_RE = re.compile(r"\b(?:struct|class)\s+(\w+)\s*(?::[^{;]*)?\{([^{}]*)\}\s*;")   # plain data structs (no nested braces)
TARRAY_RE = re.compile(r"\bTArray<\s*(?P<type>(?:\w+::)*\w+)\s*(?:<[^>]*>)?\s*>")


def std_holders(texts):
    """Names of structs/classes (in any scanned file) with a std:: container or string member."""
    bodies = [(m.group(1), m.group(2)) for t in texts for m in STRUCT_RE.finditer(t)]
    names = set()
    for name, body in bodies:
        if re.search(r"(?:^|[{;])\s*(?:const\s+)?std::(?:string|vector|map|unordered_map|set|function|array|deque|list)\b", body, re.M):
            names.add(name)
    # transitively: a struct with a member of a holder type is a holder too (FRow { RosterUnit U; })
    grew = True
    while grew:
        grew = False
        for name, body in bodies:
            if name in names:
                continue
            for h in list(names):
                if re.search(r"(?:^|[{;])\s*(?:const\s+)?(?:\w+::)*%s\s+\w+\s*[;={]" % re.escape(h), body, re.M):
                    names.add(name)
                    grew = True
                    break
    return names


def _actor_classes(text):
    """[(class name, base, body start, body end)] for classes that derive from an A-prefixed class."""
    out = []
    for m in CLASS_RE.finditer(text):
        if not m.group(2).startswith("A"):
            continue
        start = text.find("{", m.end())
        if start < 0:
            continue
        depth, i = 0, start
        while i < len(text):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    break
            i += 1
        out.append((m.group(1), m.group(2), start, i))
    return out


def _constructor_bodies(sources):
    """The bodies of every Class::Class(...) { ... } in the sources (default subobjects are made there)."""
    out = []
    for src in sources:
        for m in re.finditer(r"\b(\w+)::\1\s*\([^)]*\)\s*(?::[^{]*)?\{", src):
            depth, i = 0, m.end() - 1
            while i < len(src):
                if src[i] == "{":
                    depth += 1
                elif src[i] == "}":
                    depth -= 1
                    if depth == 0:
                        break
                i += 1
            out.append(src[m.end():i])
    return out


def line_of(text, pos):
    return text.count("\n", 0, pos) + 1


def check_cpp(path, text, errors, sources, holders=frozenset()):
    # P1: shadowed actor members
    for cls, base, s, e in _actor_classes(text):
        body = text[s:e]
        for ln in body.split("\n"):
            m = MEMBER_RE.match(ln)
            if m and m.group("name") in ACTOR_MEMBERS and "(" not in ln.split(m.group("name"))[0].replace("UPROPERTY(", ""):
                errors.append((path, line_of(text, s + body.find(ln)), "P1", "%s::%s shadows AActor::%s (UHT: already defined)"
                               % (cls, m.group("name"), m.group("name"))))
    # P2: exposed without Category
    for m in UPROP_RE.finditer(text):
        spec = m.group("spec")
        if any(x in spec for x in EXPOSED) and "Category" not in spec:
            errors.append((path, line_of(text, m.start()), "P2", "exposed UPROPERTY with no Category (UHT error in a plugin package)"))
    # P3: bare Error type (a file that declares its own enum Error inside a namespace uses it legitimately there)
    for m in ([] if re.search(r"\benum\s+(class\s+)?Error\b", text) else ERROR_RE.finditer(text)):
        before = text[max(0, m.start() - 2):m.start()]
        if before.endswith("::"):
            continue
        errors.append((path, line_of(text, m.start()), "P3", "bare `Error` as a type clashes with UE's class Error (C2872); qualify it"))
    # P4: component arrays filled by a constructor must be Transient
    for m in ARRAY_RE.finditer(text):
        name, spec = m.group("name"), m.group("spec")
        if "Transient" in spec:
            continue
        filled = any(re.search(r"\b%s\s*\.\s*Add\s*\(" % re.escape(name), body) for body in _constructor_bodies(sources))
        if filled:
            errors.append((path, line_of(text, m.start()), "P4", "%s is filled by the constructor; mark it UPROPERTY(Transient) "
                           "(a saved older copy overrides it on load)" % name))


    # P7: TArray of std:: types (directly, or a struct holding them)
    for m in TARRAY_RE.finditer(text):
        t = m.group("type")
        if t.startswith("std::") or t.split("::")[-1] in holders:
            errors.append((path, line_of(text, m.start()), "P7", "TArray<%s> moves elements with memcpy; %s holds std:: members "
                           "(dangling after a move on MSVC). Use std::vector" % (t, t)))


def check_py(path, text, errors):
    for m in PYBOOL_RE.finditer(text):
        errors.append((path, line_of(text, m.start()), "P5", "Python property names drop the b prefix (b_clean_water -> clean_water)"))
    for m in PYSTATIC_RE.finditer(text):
        errors.append((path, line_of(text, m.start()), "P6", "static C++ helpers are not visible to Python unless they are a UFUNCTION"))


def scan(paths):
    files = []
    for p in paths:
        if os.path.isfile(p):
            files.append(p)
            continue
        for root, dirs, names in os.walk(p):
            dirs[:] = [d for d in dirs if d not in ("Intermediate", "Binaries", "__pycache__", ".git", "fixtures")]
            files += [os.path.join(root, n) for n in names if n.endswith((".h", ".cpp", ".py"))]
    texts = {f: open(f, encoding="utf-8", errors="replace").read() for f in files}
    cpp_sources = [t for f, t in texts.items() if f.endswith(".cpp")]
    holders = std_holders([t for f, t in texts.items() if f.endswith((".h", ".cpp"))])
    errors = []
    for f, t in sorted(texts.items()):
        if f.endswith((".h", ".cpp")):
            check_cpp(f, t, errors, cpp_sources + [t], holders)
        elif f.endswith(".py") and "preflight" not in os.path.basename(f):
            check_py(f, t, errors)
    return errors


def main(argv):
    here = os.path.dirname(os.path.abspath(__file__))
    repo = os.path.abspath(os.path.join(here, "..", ".."))
    paths = argv or [os.path.join(repo, "engines", "unreal", "DaedalusLink"), os.path.join(repo, "tools")]
    errors = scan(paths)
    for path, line, rule, msg in errors:
        print("ERROR %s:%d %s  %s" % (os.path.relpath(path, repo), line, rule, msg))
    print("preflight: %d error(s) in %s" % (len(errors), ", ".join(os.path.relpath(p, repo) for p in paths)))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
