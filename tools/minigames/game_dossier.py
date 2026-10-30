#!/usr/bin/env python3
"""Game dossier: the PDF and Excel pair Richey asks for before a game's Blender items enter the Unreal queue.

    python tools/minigames/game_dossier.py <game> [--out DIR]

Reads docs/minigames/dossiers/<game>.json (mechanics, items, storyline, placement, blender_items) and writes
<game>.pdf and <game>.xlsx into DIR (default: the dossier folder next to the JSON; on Richey's PC the team uses
bot-team/GAMES/<game>/). The PDF is written by hand (no reportlab on the build machines): Helvetica, A4, wrapped
paragraphs, a heading per section, and a table per list. The workbook (openpyxl) has one sheet per section:
Mechanics, Items, Storyline, plus Placement and Blender. No secrets go in either file; the JSON is the only input.
"""
import argparse
import json
import os
import sys
import textwrap
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
DOSSIERS = os.path.join(HERE, "..", "..", "docs", "minigames", "dossiers")
SECTIONS = ("mechanics", "items", "storyline", "placement", "blender_items")
TITLES = {"mechanics": "Mechanics", "items": "Items", "storyline": "Storyline", "placement": "Daedalus placement",
          "blender_items": "Blender items (for the Unreal queue)"}


# ---------------------------------------------------------------- PDF (minimal writer)

class Pdf:
    """A4 pages of Helvetica text; enough for a dossier, no dependencies."""
    W, H, MARGIN, LEADING = 595, 842, 56, 14

    def __init__(self):
        self.pages, self.cur, self.y = [], [], self.H - self.MARGIN

    @staticmethod
    def esc(s):
        return s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)").encode("latin-1", "replace").decode("latin-1")

    def line(self, text, size=10, bold=False, indent=0):
        if self.y < self.MARGIN + self.LEADING:
            self.pages.append(self.cur)
            self.cur, self.y = [], self.H - self.MARGIN
        font = "/F2" if bold else "/F1"
        self.cur.append("BT %s %d Tf %d %d Td (%s) Tj ET" % (font, size, self.MARGIN + indent, self.y, self.esc(text)))
        self.y -= self.LEADING if size <= 11 else size + 6

    def para(self, text, size=10, indent=0, width=92):
        for row in textwrap.wrap(text, width=width - indent // 6) or [""]:
            self.line(row, size, indent=indent)

    def gap(self, n=1):
        self.y -= self.LEADING * n

    def build(self):
        pages = self.pages + [self.cur]
        objs = []

        def add(body):
            objs.append(body)
            return len(objs)

        font1 = add("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>")
        font2 = add("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>")
        pages_id = len(objs) + 1 + 2 * len(pages)
        page_ids = []
        for content in pages:
            stream = zlib.compress("\n".join(content).encode("latin-1"))
            c = add(b"<< /Length %d /Filter /FlateDecode >>\nstream\n" % len(stream) + stream + b"\nendstream")
            p = add("<< /Type /Page /Parent %d 0 R /MediaBox [0 0 %d %d] /Contents %d 0 R "
                    "/Resources << /Font << /F1 %d 0 R /F2 %d 0 R >> >> >>" % (pages_id, self.W, self.H, c, font1, font2))
            page_ids.append(p)
        assert add("<< /Type /Pages /Kids [%s] /Count %d >>" % (" ".join("%d 0 R" % p for p in page_ids), len(page_ids))) == pages_id
        catalog = add("<< /Type /Catalog /Pages %d 0 R >>" % pages_id)
        out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        offsets = []
        for i, body in enumerate(objs, 1):
            offsets.append(len(out))
            out += b"%d 0 obj\n" % i
            out += body if isinstance(body, bytes) else body.encode("latin-1")
            out += b"\nendobj\n"
        xref = len(out)
        out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1)
        for o in offsets:
            out += b"%010d 00000 n \n" % o
        out += b"trailer\n<< /Size %d /Root %d 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objs) + 1, catalog, xref)
        return bytes(out)


def write_pdf(d, path):
    pdf = Pdf()
    pdf.line(d["title"], 20, bold=True)
    pdf.line("id %s  ·  realm %s  ·  %s" % (d["id"], d["realm"], d.get("status", "")), 9)
    pdf.gap()
    pdf.para(d["summary"])
    pdf.gap()
    for key in SECTIONS:
        rows = d.get(key) or []
        if not rows:
            continue
        pdf.line(TITLES[key], 13, bold=True)
        for row in rows:
            if isinstance(row, str):
                pdf.para("- " + row, indent=8)
            else:
                head = row.get("name") or row.get("beat") or row.get("item") or ""
                pdf.para("- " + head + (": " + row["text"] if row.get("text") else ""), indent=8)
                for k, v in row.items():
                    if k in ("name", "beat", "item", "text"):
                        continue
                    pdf.para("%s: %s" % (k, v), 9, indent=20)
        pdf.gap()
    pdf.line("Generated by tools/minigames/game_dossier.py from docs/minigames/dossiers/%s.json. No secrets." % d["id"], 8)
    with open(path, "wb") as fh:
        fh.write(pdf.build())


# ---------------------------------------------------------------- XLSX (openpyxl)

def write_xlsx(d, path):
    from openpyxl import Workbook
    from openpyxl.styles import Font

    wb = Workbook()
    wb.remove(wb.active)
    for key in SECTIONS:
        rows = d.get(key) or []
        ws = wb.create_sheet({"placement": "Placement"}.get(key, TITLES[key].split(" (")[0]))
        if rows and isinstance(rows[0], dict):
            cols = []
            for row in rows:
                for k in row:
                    if k not in cols:
                        cols.append(k)
            ws.append(cols)
            for row in rows:
                ws.append([str(row.get(c, "")) for c in cols])
        else:
            ws.append(["text"])
            for row in rows:
                ws.append([row])
        for cell in ws[1]:
            cell.font = Font(bold=True)
        for col in ws.columns:
            width = max(len(str(c.value or "")) for c in col)
            ws.column_dimensions[col[0].column_letter].width = min(80, max(12, width + 2))
    info = wb.create_sheet("About", 0)
    for k in ("title", "id", "realm", "status", "summary"):
        info.append([k, d.get(k, "")])
    info.column_dimensions["A"].width = 12
    info.column_dimensions["B"].width = 100
    wb.save(path)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("game")
    ap.add_argument("--out", default=None, help="output folder (default: the dossier folder)")
    a = ap.parse_args(argv)
    src = os.path.join(DOSSIERS, a.game + ".json")
    with open(src, encoding="utf-8") as fh:
        d = json.load(fh)
    out = a.out or DOSSIERS
    os.makedirs(out, exist_ok=True)
    pdf, xlsx = os.path.join(out, a.game + ".pdf"), os.path.join(out, a.game + ".xlsx")
    write_pdf(d, pdf)
    write_xlsx(d, xlsx)
    print("wrote %s and %s" % (os.path.normpath(pdf), os.path.normpath(xlsx)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
