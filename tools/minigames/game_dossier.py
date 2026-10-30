#!/usr/bin/env python3
"""Game dossier: the PDF and Excel pair Richey asks for before a game's Blender items enter the Unreal queue.

    python tools/minigames/game_dossier.py <game> [--out DIR]

Reads docs/minigames/dossiers/<game>.json (mechanics, items, storyline, placement, blender_items) and writes
<game>.pdf and <game>.xlsx into DIR (default: the dossier folder next to the JSON; on Richey's PC the team uses
bot-team/GAMES/<game>/). The PDF is written by hand (no reportlab on the build machines): Helvetica, A4, wrapped
paragraphs, a heading per section, and a table per list. The workbook is written as OOXML by hand too (no openpyxl either) with one sheet per section:
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


# ---------------------------------------------------------------- XLSX (minimal OOXML writer)

def xml_escape(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;"))


def col_letter(i):
    out = ""
    i += 1
    while i:
        i, rem = divmod(i - 1, 26)
        out = chr(65 + rem) + out
    return out


def sheet_xml(rows):
    """One worksheet: inline strings, a bold first row (style 1), column widths from the longest cell."""
    widths = []
    for row in rows:
        for i, v in enumerate(row):
            if i >= len(widths):
                widths.append(0)
            widths[i] = max(widths[i], len(str(v)))
    cols = "".join('<col min="%d" max="%d" width="%d" customWidth="1"/>' % (i + 1, i + 1, min(80, max(12, w + 2)))
                   for i, w in enumerate(widths))
    body = []
    for r, row in enumerate(rows, 1):
        cells = "".join('<c r="%s%d"%s t="inlineStr"><is><t xml:space="preserve">%s</t></is></c>'
                        % (col_letter(i), r, ' s="1"' if r == 1 else "", xml_escape(v)) for i, v in enumerate(row))
        body.append('<row r="%d">%s</row>' % (r, cells))
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            '<cols>%s</cols><sheetData>%s</sheetData></worksheet>' % (cols, "".join(body)))


def write_xlsx(d, path):
    """A workbook with one sheet per section, written as OOXML by hand (no openpyxl on the build machines)."""
    import zipfile

    sheets = [("About", [[k, d.get(k, "")] for k in ("title", "id", "realm", "status", "summary")])]
    for key in SECTIONS:
        rows = d.get(key) or []
        name = {"placement": "Placement"}.get(key, TITLES[key].split(" (")[0])
        if rows and isinstance(rows[0], dict):
            cols = []
            for row in rows:
                for k in row:
                    if k not in cols:
                        cols.append(k)
            table = [cols] + [[row.get(c, "") for c in cols] for row in rows]
        else:
            table = [["text"]] + [[row] for row in rows]
        sheets.append((name, table))

    ns_r = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
    workbook = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="%s"><sheets>%s</sheets></workbook>'
                % (ns_r, "".join('<sheet name="%s" sheetId="%d" r:id="rId%d"/>' % (xml_escape(n), i, i) for i, (n, _) in enumerate(sheets, 1))))
    wb_rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
               '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">%s'
               '<Relationship Id="rId%d" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
               '</Relationships>'
               % ("".join('<Relationship Id="rId%d" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet%d.xml"/>' % (i, i)
                          for i in range(1, len(sheets) + 1)), len(sheets) + 1))
    styles = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
              '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
              '<fonts count="2"><font><sz val="11"/><name val="Calibri"/></font><font><b/><sz val="11"/><name val="Calibri"/></font></fonts>'
              '<fills count="2"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill></fills>'
              '<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>'
              '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
              '<cellXfs count="2"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>'
              '<xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0" applyFont="1"/></cellXfs>'
              '<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles></styleSheet>')
    content_types = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                     '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                     '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                     '<Default Extension="xml" ContentType="application/xml"/>'
                     '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
                     '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>%s</Types>'
                     % "".join('<Override PartName="/xl/worksheets/sheet%d.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>' % i
                               for i in range(1, len(sheets) + 1)))
    root_rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                 '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                 '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
                 '</Relationships>')
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", content_types)
        z.writestr("_rels/.rels", root_rels)
        z.writestr("xl/workbook.xml", workbook)
        z.writestr("xl/_rels/workbook.xml.rels", wb_rels)
        z.writestr("xl/styles.xml", styles)
        for i, (_, table) in enumerate(sheets, 1):
            z.writestr("xl/worksheets/sheet%d.xml" % i, sheet_xml(table))


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
