"""CLI: python -m world_census --bot-team <dir> --repo <Daedalus2> --unreal <UE project> --out <dir> [--xlsx MASTER.xlsx]"""
import argparse, os, glob, json
from . import config, sources, model, report


def main(argv=None):
    p = argparse.ArgumentParser(prog="world_census", description="Census of every world, realm and island.")
    p.add_argument("--bot-team", help="bot-team folder (art/QUEUE.md, art/, BOARD/competition.md)")
    p.add_argument("--repo", help="Daedalus2 repo (docs/REALMS.md, docs/realms, docs/islands)")
    p.add_argument("--unreal", help="Unreal project folder containing Content/")
    p.add_argument("--snapshot", help="folder with QUEUE.md, competition.md, REALMS.md, realms/, islands/, artfiles.txt, uassets.txt")
    p.add_argument("--config", help="JSON overriding DEFAULT_CONFIG (tags, folders, categories)")
    p.add_argument("--out", default="census_out")
    p.add_argument("--xlsx", help="workbook to add census sheets to (existing sheets kept)")
    p.add_argument("--from-json", help="skip collection; rebuild outputs from a census.json")
    a = p.parse_args(argv)
    cfg = config.load(a.config)
    os.makedirs(a.out, exist_ok=True)
    if a.from_json:
        c = json.load(open(a.from_json, encoding="utf-8"))
    else:
        if a.snapshot:
            s = a.snapshot
            src = dict(queue=sources.queue(f"{s}/QUEUE.md"),
                       art_files=sources.file_list(list_file=f"{s}/artfiles.txt"),
                       uassets=sources.file_list(list_file=f"{s}/uassets.txt", exts=(".uasset",)),
                       competition=sources.competition(f"{s}/competition.md"),
                       realms=sources.realms(f"{s}/REALMS.md", f"{s}/realms"),
                       island_docs=sources.island_docs(f"{s}/islands"),
                       registries=sources.registries(glob.glob(f"{s}/*.daew") + glob.glob(f"{s}/worlds.registry")))
        else:
            bt, rp = a.bot_team, a.repo
            regs = [os.path.join(dp, f) for dp, _, fs in os.walk(rp or ".") for f in fs
                    if (f == "worlds.registry" or f.endswith(".daew")) and ".git" not in dp] if rp else []
            src = dict(queue=sources.queue(os.path.join(bt, "art", "QUEUE.md")),
                       art_files=sources.file_list(os.path.join(bt, "art"), base=bt),
                       uassets=sources.file_list(os.path.join(a.unreal, "Content"), exts=(".uasset",), base=a.unreal) if a.unreal else [],
                       competition=sources.competition(os.path.join(bt, "BOARD", "competition.md")),
                       realms=sources.realms(os.path.join(rp, "docs", "REALMS.md"), os.path.join(rp, "docs", "realms")),
                       island_docs=sources.island_docs(os.path.join(rp, "docs", "islands")),
                       registries=sources.registries(regs))
        c = model.build(src, cfg)
        report.write_json(c, os.path.join(a.out, "census.json"))
    report.write_md(c, os.path.join(a.out, "CENSUS.md"))
    report.write_html(c, os.path.join(a.out, "census.html"))
    if a.xlsx:
        report.add_xlsx_sheets(c, a.xlsx)
    g = c["grand_total"]
    print(f"census: {g['total']} assets ({g['in_unreal']} in Unreal, {g['ready']} ready, {g['in_progress']} in progress, "
          f"{g['blender_only']} Blender-only) across {len(c['totals_by_world'])} worlds -> {a.out}")


if __name__ == "__main__":
    main()
