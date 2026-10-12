"""Read-only collectors. Each returns plain dicts/lists; nothing is ever written to sources."""
import os, re, glob

ASSET_EXT = (".glb", ".blend", ".fbx")
STATUSES = ["SHIPPED", "SHIPPING", "READY", "DOING", "TODO", "BLOCKED", "REJECTED"]


def _norm(p):
    return p.replace("\\", "/")


def _read(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError:
        return None


def md_tables(text):
    """Yield (heading, header_cells, rows) for each markdown table."""
    heading, header, rows = "", None, []
    for ln in (text or "").splitlines() + [""]:
        s = ln.strip()
        if s.startswith("#"):
            heading = s.lstrip("#").strip()
        if s.startswith("|"):
            cells = [c.strip() for c in s.strip("|").split("|")]
            if header is None:
                header = cells
            elif not set("".join(cells)) <= set("-: "):
                rows.append(cells)
        elif header is not None:
            yield heading, header, rows
            header, rows = None, []


def queue(path):
    out = []
    for _, hdr, rows in md_tables(_read(path)):
        if len(hdr) < 5 or "Asset" not in hdr[1]:
            continue
        for r in rows:
            r += [""] * (6 - len(r))
            st = (r[4].split() or [""])[0].rstrip(":").upper()
            out.append({"id": r[0], "name": r[1], "kind": r[2], "size": r[3],
                        "status": st if st in STATUSES else (st or "UNKNOWN"), "status_raw": r[4], "notes": r[5]})
    return out


def file_list(root=None, list_file=None, exts=ASSET_EXT, base=None):
    """Files under root (relative paths), or read a pre-made list (one path per line)."""
    if list_file:
        lines = (_read(list_file) or "").splitlines()
    else:
        lines = []
        for dp, _, fs in os.walk(root or ""):
            for f in fs:
                lines.append(os.path.relpath(os.path.join(dp, f), base or os.path.dirname(root)))
    return [_norm(l.strip()) for l in lines if l.strip().lower().endswith(exts)]


def competition(path):
    text = _read(path) or ""
    grid, tracker = {}, []
    for head, hdr, rows in md_tables(text):
        if hdr[:2] == ["Bot", "ARK_ORIGIN x,y,z"]:
            grid = {r[0]: r[1] for r in rows if len(r) > 1}
        elif hdr and hdr[0] == "Bot" and "Island" in hdr and "Drinkable water" in hdr:
            tracker = [dict(zip(hdr, r)) for r in rows]
    return {"grid": grid, "island_tracker": tracker}


def realms(realms_md, realm_dir):
    out = []
    for _, hdr, rows in md_tables(_read(realms_md)):
        if hdr and hdr[0] == "Realm":
            for r in rows:
                d = dict(zip(hdr, r))
                d["Realm"] = re.sub(r"\*", "", d.get("Realm", ""))
                out.append(d)
    for f in sorted(glob.glob(os.path.join(realm_dir or "", "*.md"))):
        t = _read(f) or ""
        title = (t.splitlines() or [os.path.basename(f)])[0].lstrip("# ").strip()
        out.append({"Realm": title, "Status": "PROPOSAL", "Feels like": "", "What's in it": t[:400].replace("\n", " "),
                    "doc": _norm(f)})
    return out


KEYS = {"water": r"water|spring|well|cistern|still", "livestock": r"livestock|goat|hen|pen|herd|cattle|buffalo",
        "herbs": r"herb|tonic|brew|combo", "mechanic": r"mechanic|breed|combo|stack"}


def island_docs(doc_dir):
    out = []
    for f in sorted(glob.glob(os.path.join(doc_dir or "", "*.md"))):
        t = _read(f) or ""
        lo = t.lower()
        row = {"doc": os.path.basename(f), "title": (t.splitlines() or [""])[0].lstrip("# ").strip(), "chars": len(t)}
        for k, rx in KEYS.items():
            m = re.search(r"[^\n]*(" + rx + r")[^\n]*", lo)
            row[k] = (m.group(0).strip()[:160] if m else "")
        out.append(row)
    return out


def registries(paths):
    return [{"path": _norm(p), "text": (_read(p) or "")[:2000]} for p in paths]
